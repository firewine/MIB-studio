#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import tarfile
import zipfile
from pathlib import Path


SECRET_PATTERNS = [
    re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(rb"(?i)api[_-]?key\\s*[:=]\\s*['\\\"]?[A-Za-z0-9_-]{16,}"),
    re.compile(rb"(?i)bearer\\s+[A-Za-z0-9._-]{20,}"),
]


def scan_bytes(name: str, data: bytes) -> list[str]:
    return [f"{name}: pattern {idx}" for idx, pattern in enumerate(SECRET_PATTERNS) if pattern.search(data)]


def scan_path(path: Path) -> list[str]:
    findings: list[str] = []
    if path.is_dir():
        for item in path.rglob("*"):
            if item.is_file():
                findings.extend(scan_bytes(str(item), item.read_bytes()))
    elif zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                findings.extend(scan_bytes(name, archive.read(name)))
    elif tarfile.is_tarfile(path):
        findings.extend(scan_tar_bytes(str(path), path.read_bytes()))
    else:
        findings.extend(scan_bytes(str(path), path.read_bytes()))
    return findings


def scan_tar_bytes(name: str, data: bytes) -> list[str]:
    findings: list[str] = []
    try:
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                extracted = archive.extractfile(member)
                if extracted is None:
                    continue
                member_data = extracted.read()
                member_name = f"{name}:{member.name}"
                findings.extend(scan_bytes(member_name, member_data))
                if member.name.endswith(".tar") or member.name.endswith("/layer.tar"):
                    findings.extend(scan_tar_bytes(member_name, member_data))
    except tarfile.TarError:
        findings.extend(scan_bytes(name, data))
    return findings


def artifact_names(path: Path) -> set[str]:
    if path.is_dir():
        return {str(item.relative_to(path)) for item in path.rglob("*") if item.is_file()}
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            return set(archive.namelist())
    if tarfile.is_tarfile(path):
        with tarfile.open(path) as archive:
            return {member.name for member in archive.getmembers() if member.isfile()}
    return set()


def artifact_read(path: Path, name: str) -> bytes | None:
    if path.is_dir():
        target = path / name
        return target.read_bytes() if target.exists() and target.is_file() else None
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            try:
                return archive.read(name)
            except KeyError:
                return None
    if tarfile.is_tarfile(path):
        with tarfile.open(path) as archive:
            member = archive.extractfile(name)
            return member.read() if member else None
    return None


def validate_manifest(path: Path) -> list[str]:
    from jsonschema import Draft7Validator

    names = artifact_names(path)
    if not names:
        return []
    manifest_name = "manifest.json"
    if manifest_name not in names:
        return [f"{path}: missing manifest.json"]
    manifest_bytes = artifact_read(path, manifest_name)
    if manifest_bytes is None:
        return [f"{path}: cannot read manifest.json"]
    try:
        manifest = json.loads(manifest_bytes)
    except json.JSONDecodeError as exc:
        return [f"manifest.json: invalid JSON: {exc}"]

    schema = json.loads(Path("schemas/export_manifest.schema.json").read_text())
    errors = [f"manifest.json: {error.message}" for error in Draft7Validator(schema).iter_errors(manifest)]
    for item in manifest.get("files", []):
        file_path = item.get("path")
        if not isinstance(file_path, str):
            continue
        data = artifact_read(path, file_path)
        if item.get("required") and data is None:
            errors.append(f"manifest.json: required file missing: {file_path}")
            continue
        expected_sha = item.get("sha256")
        if data is not None and isinstance(expected_sha, str) and len(expected_sha) == 64:
            actual_sha = hashlib.sha256(data).hexdigest()
            if actual_sha != expected_sha:
                errors.append(f"manifest.json: sha256 mismatch for {file_path}")
    return errors


def validate_sbom(path: Path) -> list[str]:
    data = json.loads(path.read_text())
    errors: list[str] = []
    if data.get("bomFormat") != "CycloneDX":
        errors.append(f"{path}: SBOM bomFormat must be CycloneDX")
    if "components" not in data or not isinstance(data["components"], list):
        errors.append(f"{path}: SBOM components list missing")
    return errors


def validate_cve_report(path: Path) -> list[str]:
    data = json.loads(path.read_text())
    findings = data.get("findings", data.get("vulnerabilities", []))
    if not isinstance(findings, list):
        return [f"{path}: CVE findings/vulnerabilities must be a list"]
    blocked = []
    for finding in findings:
        severity = str(finding.get("severity", "")).lower()
        fix_state = str(finding.get("fix_state", finding.get("fixState", ""))).lower()
        if severity in {"critical", "high"} and fix_state not in {"not-fixed", "will-not-fix", "wont-fix", "accepted-risk"}:
            blocked.append(finding.get("id") or finding.get("vulnerability_id") or severity)
    return [f"{path}: blocking high/critical CVEs: {blocked}"] if blocked else []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact")
    parser.add_argument("--sbom")
    parser.add_argument("--cve-report")
    parser.add_argument("--require-docker-evidence", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        fake_secret = b"api_" + b"key=" + b"sk-" + b"testvalue" + b"123456789012345"
        assert scan_bytes("bad", fake_secret)
        assert not scan_bytes("good", b"contract_sha256=0" * 4)
        print("export secret scan self-test OK")
        return 0

    if not args.artifact:
        raise SystemExit("--artifact is required unless --self-test is set")
    artifact = Path(args.artifact)
    findings = scan_path(artifact)
    findings.extend(validate_manifest(artifact))
    if args.require_docker_evidence:
        if not args.sbom or not Path(args.sbom).is_file():
            findings.append("--require-docker-evidence needs --sbom file")
        if not args.cve_report or not Path(args.cve_report).is_file():
            findings.append("--require-docker-evidence needs --cve-report file")
    for evidence in [args.sbom, args.cve_report]:
        if evidence:
            evidence_path = Path(evidence)
            if not evidence_path.is_file():
                findings.append(f"evidence file missing: {evidence}")
                continue
            try:
                json.loads(evidence_path.read_text())
            except json.JSONDecodeError as exc:
                findings.append(f"evidence file must be JSON: {evidence}: {exc}")
                continue
            if evidence == args.sbom:
                findings.extend(validate_sbom(evidence_path))
            if evidence == args.cve_report:
                findings.extend(validate_cve_report(evidence_path))
    if findings:
        print("\n".join(findings))
        return 1
    print("export artifact secret scan OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

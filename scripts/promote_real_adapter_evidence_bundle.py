#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def load_verifier_module() -> Any:
    try:
        import verify_real_adapter_evidence_bundle as module

        return module
    except ModuleNotFoundError:
        path = Path(__file__).with_name("verify_real_adapter_evidence_bundle.py")
        spec = importlib.util.spec_from_file_location("verify_real_adapter_evidence_bundle", path)
        if spec is None or spec.loader is None:
            raise
        module = importlib.util.module_from_spec(spec)
        sys.modules["verify_real_adapter_evidence_bundle"] = module
        spec.loader.exec_module(module)
        return module


verifier = load_verifier_module()

SCHEMA_VERSION = "mib_real_adapter_evidence_bundle_promotion.v1"
GO_DECISION = "GO_REAL_ADAPTER_EVIDENCE_BUNDLE"
NOT_GO_DECISION = "NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE"
ARCHIVE_METADATA_FILES = {
    "manifest": "real_adapter_evidence_bundle_manifest.json",
    "verification": "real_adapter_evidence_bundle_verification.json",
}


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json_object(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, "missing"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(value, dict):
        return None, "expected JSON object"
    return value, None


def expected_decision(value: str) -> str:
    return GO_DECISION if value == "GO" else NOT_GO_DECISION


def fixed_bundle_files() -> dict[str, str]:
    return dict(verifier.FILES)


def reset_fixed_files(target_dir: Path) -> None:
    for filename in fixed_bundle_files().values():
        candidate = target_dir / filename
        if candidate.exists():
            candidate.unlink()


def file_row(logical_name: str, filename: str, source: Path, target: Path, *, copied: bool) -> dict[str, Any]:
    return {
        "logical_name": logical_name,
        "filename": filename,
        "source_path": str(source),
        "target_path": str(target),
        "source_present": source.is_file(),
        "target_present": target.is_file(),
        "copied": copied,
        "source_sha256": sha256_file(source) if source.is_file() else None,
        "target_sha256": sha256_file(target) if target.is_file() else None,
        "source_size_bytes": source.stat().st_size if source.is_file() else None,
        "target_size_bytes": target.stat().st_size if target.is_file() else None,
    }


def copy_fixed_files(bundle_dir: Path, target_dir: Path) -> list[dict[str, Any]]:
    target_dir.mkdir(parents=True, exist_ok=True)
    reset_fixed_files(target_dir)
    rows: list[dict[str, Any]] = []
    for logical_name, filename in fixed_bundle_files().items():
        source = bundle_dir / filename
        target = target_dir / filename
        if not source.is_file():
            rows.append(file_row(logical_name, filename, source, target, copied=False))
            continue
        shutil.copy2(source, target)
        rows.append(file_row(logical_name, filename, source, target, copied=True))
    return rows


def add_expected(report: dict[str, Any], expected: str) -> dict[str, Any]:
    result = dict(report)
    result["expected_decision"] = expected
    result["decision_matches_expected"] = result.get("decision") == expected
    result["verification_ok"] = result["decision_matches_expected"]
    return result


def archive_metadata_report(bundle_dir: Path, source_verification: dict[str, Any]) -> dict[str, Any]:
    manifest_path = bundle_dir / ARCHIVE_METADATA_FILES["manifest"]
    verification_path = bundle_dir / ARCHIVE_METADATA_FILES["verification"]
    manifest, manifest_error = read_json_object(manifest_path)
    verification, verification_error = read_json_object(verification_path)
    failures: list[str] = []
    if manifest_error:
        failures.append(f"manifest:{manifest_error}")
    if verification_error:
        failures.append(f"verification:{verification_error}")
    if manifest:
        if manifest.get("schema_version") != "mib_real_adapter_evidence_bundle_manifest.v1":
            failures.append("manifest:schema_version")
        summary = manifest.get("verification_summary")
        if not isinstance(summary, dict):
            failures.append("manifest:verification_summary")
            summary = {}
        if summary.get("decision") != source_verification.get("decision"):
            failures.append("manifest:verification_summary.decision")
        if summary.get("release_bundle_ready") != source_verification.get("release_bundle_ready"):
            failures.append("manifest:verification_summary.release_bundle_ready")
        if summary.get("blockers") != source_verification.get("blockers"):
            failures.append("manifest:verification_summary.blockers")
        rows = manifest.get("files")
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            failures.append("manifest:files")
            rows = []
        by_filename = {row.get("filename"): row for row in rows if isinstance(row.get("filename"), str)}
        for filename in fixed_bundle_files().values():
            source = bundle_dir / filename
            row = by_filename.get(filename)
            if row is None:
                failures.append(f"manifest:files.{filename}.missing")
                continue
            if source.is_file():
                if row.get("present") is not True:
                    failures.append(f"manifest:files.{filename}.present")
                if row.get("sha256") != sha256_file(source):
                    failures.append(f"manifest:files.{filename}.sha256")
            elif row.get("present") is True:
                failures.append(f"manifest:files.{filename}.unexpected_present")
    if verification:
        if verification.get("schema_version") != verifier.SCHEMA_VERSION:
            failures.append("verification:schema_version")
        for key in ["decision", "release_bundle_ready", "m6_rc_claimed_go", "blockers"]:
            if verification.get(key) != source_verification.get(key):
                failures.append(f"verification:{key}")
        for key in ["expected_decision", "decision_matches_expected", "verification_ok"]:
            if key in verification and verification.get(key) != source_verification.get(key):
                failures.append(f"verification:{key}")
    return {
        "checked": True,
        "ok": not failures,
        "manifest_path": str(manifest_path),
        "verification_path": str(verification_path),
        "manifest_sha256": sha256_file(manifest_path) if manifest_path.is_file() else None,
        "verification_sha256": sha256_file(verification_path) if verification_path.is_file() else None,
        "failures": failures,
    }


def assert_safe_archive_member(member: tarfile.TarInfo, destination: Path) -> None:
    name = member.name
    target = (destination / name).resolve()
    try:
        target.relative_to(destination.resolve())
    except ValueError as exc:
        raise ValueError(f"unsafe archive member path: {name}") from exc
    if Path(name).is_absolute() or ".." in Path(name).parts:
        raise ValueError(f"unsafe archive member path: {name}")
    if not (member.isfile() or member.isdir()):
        raise ValueError(f"unsafe archive member type: {name}")


def extract_bundle_archive(archive_path: Path, extraction_root: Path) -> Path:
    bundle_dir = extraction_root / "bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(archive_path, "r:gz") as archive:
            for member in archive.getmembers():
                assert_safe_archive_member(member, bundle_dir)
                target = bundle_dir / member.name
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise ValueError(f"unsafe archive member has no file content: {member.name}")
                with source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
    except tarfile.TarError as exc:
        raise ValueError(f"invalid bundle archive: {archive_path}") from exc
    return bundle_dir


def promote_bundle_dir(args: argparse.Namespace, bundle_dir: Path, *, bundle_archive: Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    target_dir = Path(args.target_dir)
    if bundle_archive is None and bundle_dir.resolve() == target_dir.resolve():
        raise ValueError("--bundle-dir and --target-dir must be different")

    expected = expected_decision(args.expected_decision)
    source_verification = add_expected(verifier.verify_bundle(bundle_dir), expected)
    archive_metadata = archive_metadata_report(bundle_dir, source_verification) if bundle_archive else {"checked": False, "ok": True}
    archive_metadata_ok = archive_metadata.get("ok") is True
    source_is_go = (
        source_verification.get("decision") == GO_DECISION
        and source_verification.get("release_bundle_ready") is True
        and archive_metadata_ok
    )
    copy_allowed = expected == GO_DECISION and source_is_go and not args.dry_run

    copied_files: list[dict[str, Any]] = []
    target_verification: dict[str, Any] | None = None
    final_verification = source_verification
    if not archive_metadata_ok:
        final_verification = dict(source_verification)
        blockers = list(final_verification.get("blockers", []))
        if "archive_metadata_not_verified" not in blockers:
            blockers.append("archive_metadata_not_verified")
        final_verification.update(
            {
                "decision": NOT_GO_DECISION,
                "release_bundle_ready": False,
                "verification_ok": False,
                "decision_matches_expected": False,
                "blockers": blockers,
                "archive_metadata": archive_metadata,
            }
        )
    if copy_allowed:
        copied_files = copy_fixed_files(bundle_dir, target_dir)
        target_verification = add_expected(verifier.verify_bundle(target_dir), expected)
        final_verification = target_verification

    promoted = copy_allowed and final_verification.get("decision") == GO_DECISION and final_verification.get("verification_ok") is True
    if args.dry_run:
        reason = "dry_run"
    elif expected != GO_DECISION:
        reason = "expected_decision_is_not_go"
    elif not archive_metadata_ok:
        reason = "archive_metadata_not_verified"
    elif not source_is_go:
        reason = "source_bundle_not_go"
    elif not promoted:
        reason = "target_verification_not_go"
    else:
        reason = "promoted"

    promotion_ok = final_verification.get("verification_ok") is True if args.dry_run or expected != GO_DECISION else promoted
    if not archive_metadata_ok:
        promotion_ok = False

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "date": now_utc(),
        "bundle_dir": str(bundle_dir),
        "bundle_archive": str(bundle_archive) if bundle_archive else None,
        "bundle_archive_sha256": sha256_file(bundle_archive) if bundle_archive and bundle_archive.is_file() else None,
        "target_dir": str(target_dir),
        "dry_run": bool(args.dry_run),
        "expected_decision": expected,
        "copy_allowed": copy_allowed,
        "promoted": promoted,
        "promotion_ok": promotion_ok,
        "reason": reason,
        "archive_metadata": archive_metadata,
        "verification_output": args.verification_output,
        "promotion_manifest_output": args.promotion_manifest_output,
        "copied_files": copied_files,
        "source_verification_summary": {
            "decision": source_verification.get("decision"),
            "verification_ok": source_verification.get("verification_ok"),
            "release_bundle_ready": source_verification.get("release_bundle_ready"),
            "blockers": source_verification.get("blockers", []),
        },
        "target_verification_summary": {
            "decision": target_verification.get("decision") if target_verification else None,
            "verification_ok": target_verification.get("verification_ok") if target_verification else None,
            "release_bundle_ready": target_verification.get("release_bundle_ready") if target_verification else None,
            "blockers": target_verification.get("blockers", []) if target_verification else [],
        },
    }
    return manifest, final_verification


def promote_bundle(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    bundle_archive = getattr(args, "bundle_archive", None)
    if bundle_archive:
        archive_path = Path(bundle_archive)
        with tempfile.TemporaryDirectory(prefix="mib-real-adapter-bundle-") as temp_root:
            bundle_dir = extract_bundle_archive(archive_path, Path(temp_root))
            archive_args = argparse.Namespace(**vars(args))
            archive_args.bundle_dir = str(bundle_dir)
            return promote_bundle_dir(archive_args, bundle_dir, bundle_archive=archive_path)
    return promote_bundle_dir(args, Path(args.bundle_dir))


def write_json(path: str | Path, value: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote a verified real-adapter evidence bundle into canonical review artifacts.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--bundle-dir")
    source.add_argument("--bundle-archive", help="tar.gz archive produced by build_real_adapter_evidence_bundle.py --archive-output")
    parser.add_argument("--target-dir", default="artifacts/review")
    parser.add_argument("--expected-decision", choices=["GO", "NOT_GO"], default="GO")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verification-output", default="artifacts/review/real_adapter_evidence_bundle_verification.json")
    parser.add_argument("--promotion-manifest-output", default="artifacts/review/real_adapter_evidence_bundle_promotion.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest, verification = promote_bundle(args)
    write_json(args.verification_output, verification)
    write_json(args.promotion_manifest_output, manifest)
    print(
        json.dumps(
            {
                "promotion_manifest_output": args.promotion_manifest_output,
                "verification_output": args.verification_output,
                "decision": verification["decision"],
                "promoted": manifest["promoted"],
                "promotion_ok": manifest["promotion_ok"],
            },
            sort_keys=True,
        )
    )
    return 0 if manifest["promotion_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

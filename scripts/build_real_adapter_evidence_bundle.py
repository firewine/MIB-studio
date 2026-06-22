#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
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


SCHEMA_VERSION = "mib_real_adapter_evidence_bundle_manifest.v1"


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fixed_bundle_files() -> dict[str, str]:
    return dict(verifier.FILES)


def reset_fixed_bundle_files(bundle_dir: Path) -> None:
    for filename in fixed_bundle_files().values():
        candidate = bundle_dir / filename
        if candidate.exists():
            candidate.unlink()


def copy_bundle_files(source_dir: Path, bundle_dir: Path) -> list[dict[str, Any]]:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    reset_fixed_bundle_files(bundle_dir)
    rows: list[dict[str, Any]] = []
    for logical_name, filename in fixed_bundle_files().items():
        source = source_dir / filename
        target = bundle_dir / filename
        if source.is_file():
            if source.resolve() != target.resolve():
                shutil.copy2(source, target)
            stat = target.stat()
            rows.append(
                {
                    "logical_name": logical_name,
                    "filename": filename,
                    "source_path": str(source),
                    "bundle_path": str(target),
                    "present": True,
                    "copied": source.resolve() != target.resolve(),
                    "sha256": sha256_file(target),
                    "size_bytes": stat.st_size,
                }
            )
        else:
            rows.append(
                {
                    "logical_name": logical_name,
                    "filename": filename,
                    "source_path": str(source),
                    "bundle_path": str(target),
                    "present": False,
                    "copied": False,
                    "sha256": None,
                    "size_bytes": None,
                }
            )
    return rows


def expected_decision(value: str) -> str:
    return "GO_REAL_ADAPTER_EVIDENCE_BUNDLE" if value == "GO" else "NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE"


def build_bundle(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    source_dir = Path(args.source_dir)
    bundle_dir = Path(args.bundle_dir)
    if source_dir.resolve() == bundle_dir.resolve():
        raise ValueError("--source-dir and --bundle-dir must be different to avoid deleting source evidence")
    file_rows = copy_bundle_files(source_dir, bundle_dir)
    verification = verifier.verify_bundle(bundle_dir)
    expected = expected_decision(args.expected_decision)
    verification["expected_decision"] = expected
    verification["decision_matches_expected"] = verification["decision"] == expected
    verification["verification_ok"] = verification["decision_matches_expected"]
    missing = [row["logical_name"] for row in file_rows if not row["present"]]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "date": now_utc(),
        "source_dir": str(source_dir),
        "bundle_dir": str(bundle_dir),
        "expected_decision": expected,
        "decision_matches_expected": verification["decision_matches_expected"],
        "verification_output": args.verification_output,
        "files": file_rows,
        "missing_files": missing,
        "verification_summary": {
            "decision": verification["decision"],
            "release_bundle_ready": verification["release_bundle_ready"],
            "m6_rc_claimed_go": verification["m6_rc_claimed_go"],
            "blockers": verification["blockers"],
        },
    }
    return manifest, verification


def write_json(path: str | Path, value: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assemble and verify a portable real-adapter evidence bundle.")
    parser.add_argument("--source-dir", default="artifacts/review")
    parser.add_argument("--bundle-dir", default="artifacts/review/real_adapter_evidence_bundle")
    parser.add_argument("--expected-decision", choices=["GO", "NOT_GO"], default="NOT_GO")
    parser.add_argument("--verification-output", default="artifacts/review/real_adapter_evidence_bundle_verification.json")
    parser.add_argument("--manifest-output", default="artifacts/review/real_adapter_evidence_bundle_manifest.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest, verification = build_bundle(args)
    write_json(args.verification_output, verification)
    write_json(args.manifest_output, manifest)
    print(
        json.dumps(
            {
                "manifest_output": args.manifest_output,
                "verification_output": args.verification_output,
                "decision": verification["decision"],
                "verification_ok": verification["verification_ok"],
            },
            sort_keys=True,
        )
    )
    return 0 if verification["verification_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

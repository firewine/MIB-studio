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

SCHEMA_VERSION = "mib_real_adapter_evidence_bundle_promotion.v1"
GO_DECISION = "GO_REAL_ADAPTER_EVIDENCE_BUNDLE"
NOT_GO_DECISION = "NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE"


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def promote_bundle(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    bundle_dir = Path(args.bundle_dir)
    target_dir = Path(args.target_dir)
    if bundle_dir.resolve() == target_dir.resolve():
        raise ValueError("--bundle-dir and --target-dir must be different")

    expected = expected_decision(args.expected_decision)
    source_verification = add_expected(verifier.verify_bundle(bundle_dir), expected)
    source_is_go = source_verification.get("decision") == GO_DECISION and source_verification.get("release_bundle_ready") is True
    copy_allowed = expected == GO_DECISION and source_is_go and not args.dry_run

    copied_files: list[dict[str, Any]] = []
    target_verification: dict[str, Any] | None = None
    final_verification = source_verification
    if copy_allowed:
        copied_files = copy_fixed_files(bundle_dir, target_dir)
        target_verification = add_expected(verifier.verify_bundle(target_dir), expected)
        final_verification = target_verification

    promoted = copy_allowed and final_verification.get("decision") == GO_DECISION and final_verification.get("verification_ok") is True
    if args.dry_run:
        reason = "dry_run"
    elif expected != GO_DECISION:
        reason = "expected_decision_is_not_go"
    elif not source_is_go:
        reason = "source_bundle_not_go"
    elif not promoted:
        reason = "target_verification_not_go"
    else:
        reason = "promoted"

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "date": now_utc(),
        "bundle_dir": str(bundle_dir),
        "target_dir": str(target_dir),
        "dry_run": bool(args.dry_run),
        "expected_decision": expected,
        "copy_allowed": copy_allowed,
        "promoted": promoted,
        "promotion_ok": final_verification.get("verification_ok") is True if args.dry_run or expected != GO_DECISION else promoted,
        "reason": reason,
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


def write_json(path: str | Path, value: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote a verified real-adapter evidence bundle into canonical review artifacts.")
    parser.add_argument("--bundle-dir", required=True)
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

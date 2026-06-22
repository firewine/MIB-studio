#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def load_script_module(filename: str, module_name: str) -> Any:
    try:
        return __import__(module_name)
    except ModuleNotFoundError:
        path = Path(__file__).with_name(filename)
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module


promotion = load_script_module("promote_real_adapter_evidence_bundle.py", "promote_real_adapter_evidence_bundle")
readiness = load_script_module("verify_v0_release_readiness.py", "verify_v0_release_readiness")


SCHEMA_VERSION = "mib_v0_release_closeout_from_bundle.v1"


NEXT_ACTIONS = {
    "archive_metadata_not_verified": (
        "Rebuild the transferred archive with scripts/build_real_adapter_evidence_bundle.py "
        "--archive-output so it includes real_adapter_evidence_bundle_manifest.json and "
        "real_adapter_evidence_bundle_verification.json."
    ),
    "source_bundle_not_go": (
        "Rerun the external CUDA host flow until the evidence bundle verifier returns "
        "GO_REAL_ADAPTER_EVIDENCE_BUNDLE."
    ),
    "target_verification_not_go": (
        "Inspect copied bundle files under artifacts/review and rerun real-adapter bundle "
        "verification before retrying closeout."
    ),
    "m6_review_docs_not_current": (
        "After accepted live no-fake endpoint evidence review, update docs/reviews/M6/SIGNOFF_MATRIX.md "
        "and docs/reviews/M6/CTO_DECISION.md to GO in this same release workstation checkout."
    ),
    "real_trained_adapter_no_fake_endpoint": (
        "Run the external CUDA host handoff to produce a real trained lora_adapter, matching Docker "
        "image, and live no-fake endpoint evidence."
    ),
}


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def write_json(path: str | Path, value: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def output_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def optional_input_path(root: Path, value: str | None) -> str | None:
    if value is None:
        return None
    return str(output_path(root, value))


def readiness_report(root: Path, expected_decision: str) -> dict[str, Any]:
    report = readiness.evaluate(root)
    report["expected_decision"] = expected_decision
    report["decision_matches_expected"] = report["decision"] == expected_decision
    report["verification_ok"] = report["decision_matches_expected"] and (
        expected_decision == "GO" or not report["unexpected_blockers"]
    )
    return report


def unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def closeout_blocking_reasons(
    status: str, promotion_manifest: dict[str, Any], v0_report: dict[str, Any]
) -> list[str]:
    reasons: list[str] = []
    if status == "GO_V0_RELEASE_CLOSEOUT":
        return reasons

    promotion_reason = promotion_manifest.get("reason")
    if promotion_manifest.get("promotion_ok") is not True and isinstance(promotion_reason, str):
        reasons.append(promotion_reason)

    if status == "NOT_GO_V0_READINESS":
        blockers = v0_report.get("blockers", [])
        if isinstance(blockers, list):
            reasons.extend(str(blocker) for blocker in blockers if isinstance(blocker, str))

    return unique(reasons)


def operator_next_actions(blocking_reasons: list[str]) -> list[str]:
    actions = [NEXT_ACTIONS[reason] for reason in blocking_reasons if reason in NEXT_ACTIONS]
    if not actions and blocking_reasons:
        actions.append("Inspect the closeout summary, promotion manifest, bundle verification, and v0 readiness audit.")
    return actions


def closeout(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    root = Path(args.root).resolve()
    target_dir = Path(args.target_dir)
    if not target_dir.is_absolute():
        target_dir = root / target_dir

    promotion_args = argparse.Namespace(
        bundle_dir=optional_input_path(root, args.bundle_dir),
        bundle_archive=optional_input_path(root, args.bundle_archive),
        target_dir=str(target_dir),
        expected_decision=args.expected_bundle_decision,
        dry_run=args.dry_run,
        verification_output=args.bundle_verification_output,
        promotion_manifest_output=args.promotion_manifest_output,
    )
    promotion_manifest, bundle_verification = promotion.promote_bundle(promotion_args)
    write_json(output_path(root, args.bundle_verification_output), bundle_verification)

    expected_readiness = args.expected_readiness_decision
    if args.dry_run and expected_readiness == "GO":
        expected_readiness = "NOT_GO"
    v0_report = readiness_report(root, expected_readiness)

    bundle_ok = promotion_manifest.get("promotion_ok") is True
    v0_ok = v0_report.get("verification_ok") is True
    v0_go = v0_report.get("decision") == "GO" and v0_report.get("release_ready") is True
    if args.dry_run:
        status = "DRY_RUN_V0_RELEASE_CLOSEOUT"
        closeout_ok = bundle_ok and v0_ok
    elif not bundle_ok:
        status = "NOT_GO_BUNDLE_PROMOTION"
        closeout_ok = False
    elif v0_go and v0_ok:
        status = "GO_V0_RELEASE_CLOSEOUT"
        closeout_ok = True
    else:
        status = "NOT_GO_V0_READINESS"
        closeout_ok = False

    blocking_reasons = closeout_blocking_reasons(status, promotion_manifest, v0_report)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "date": now_utc(),
        "root": str(root),
        "target_dir": str(target_dir),
        "bundle_dir": args.bundle_dir,
        "bundle_archive": args.bundle_archive,
        "resolved_bundle_dir": promotion_args.bundle_dir,
        "resolved_bundle_archive": promotion_args.bundle_archive,
        "dry_run": bool(args.dry_run),
        "expected_bundle_decision": promotion.expected_decision(args.expected_bundle_decision),
        "expected_readiness_decision": expected_readiness,
        "status": status,
        "closeout_ok": closeout_ok,
        "release_claimed_go": status == "GO_V0_RELEASE_CLOSEOUT",
        "blocking_reasons": blocking_reasons,
        "operator_next_actions": operator_next_actions(blocking_reasons),
        "promotion_manifest_output": args.promotion_manifest_output,
        "bundle_verification_output": args.bundle_verification_output,
        "readiness_output": args.readiness_output,
        "promotion_summary": {
            "promoted": promotion_manifest.get("promoted"),
            "promotion_ok": promotion_manifest.get("promotion_ok"),
            "reason": promotion_manifest.get("reason"),
            "source_decision": promotion_manifest.get("source_verification_summary", {}).get("decision"),
            "target_decision": promotion_manifest.get("target_verification_summary", {}).get("decision"),
        },
        "readiness_summary": {
            "decision": v0_report.get("decision"),
            "release_ready": v0_report.get("release_ready"),
            "verification_ok": v0_report.get("verification_ok"),
            "blockers": v0_report.get("blockers", []),
            "unexpected_blockers": v0_report.get("unexpected_blockers", []),
        },
    }
    return summary, promotion_manifest, bundle_verification, v0_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote a real-adapter evidence bundle and run v0 release readiness closeout.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--bundle-dir")
    source.add_argument("--bundle-archive")
    parser.add_argument("--root", default=".")
    parser.add_argument("--target-dir", default="artifacts/review")
    parser.add_argument("--expected-bundle-decision", choices=["GO", "NOT_GO"], default="GO")
    parser.add_argument("--expected-readiness-decision", choices=["GO", "NOT_GO"], default="GO")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--bundle-verification-output", default="artifacts/review/real_adapter_evidence_bundle_verification.json")
    parser.add_argument("--promotion-manifest-output", default="artifacts/review/real_adapter_evidence_bundle_promotion.json")
    parser.add_argument("--readiness-output", default="artifacts/review/v0_release_readiness_audit.json")
    parser.add_argument("--summary-output", default="artifacts/review/v0_release_closeout_from_bundle.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    summary, promotion_manifest, bundle_verification, v0_report = closeout(args)
    write_json(output_path(root, args.bundle_verification_output), bundle_verification)
    write_json(output_path(root, args.promotion_manifest_output), promotion_manifest)
    write_json(output_path(root, args.readiness_output), v0_report)
    write_json(output_path(root, args.summary_output), summary)
    print(
        json.dumps(
            {
                "summary_output": args.summary_output,
                "status": summary["status"],
                "closeout_ok": summary["closeout_ok"],
                "release_claimed_go": summary["release_claimed_go"],
                "readiness_decision": summary["readiness_summary"]["decision"],
            },
            sort_keys=True,
        )
    )
    return 0 if summary["closeout_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

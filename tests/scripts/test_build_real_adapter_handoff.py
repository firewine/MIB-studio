from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


handoff = load_module("scripts/build_real_adapter_handoff.py", "build_real_adapter_handoff")


def write_json(path: Path, value: dict[str, object]) -> Path:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path


def args_for(tmp_path: Path, *, candidate_scan: dict[str, object], prereq: dict[str, object]) -> SimpleNamespace:
    scan_path = write_json(tmp_path / "candidate_scan.json", candidate_scan)
    prereq_path = write_json(tmp_path / "prereq.json", prereq)
    readiness_path = write_json(
        tmp_path / "readiness.json",
        {
            "decision": "NOT_GO",
            "release_ready": False,
            "blockers": ["real_trained_adapter_no_fake_endpoint"],
            "unexpected_blockers": [],
        },
    )
    return SimpleNamespace(
        candidate_scan=str(scan_path),
        prereq_audit=str(prereq_path),
        readiness_audit=str(readiness_path),
        adapter_root="/tmp/mib-real-adapter",
        base_model="microsoft/Phi-3.5-mini-instruct",
        image="mib-export:test",
        agent_id="finance.router.v1",
        model_cache_dir="/tmp/mib-strict-model-cache/model_cache",
        python="./.venv/bin/python",
        adapter_intake_json_output="artifacts/review/real_adapter_artifact_intake.json",
        endpoint_output="artifacts/review/real_trained_adapter_endpoint_evidence.md",
        endpoint_json_output="artifacts/review/real_trained_adapter_endpoint_evidence.json",
        m6_json_output="artifacts/review/m6_rc_evidence_verification.json",
        gate_json_output="artifacts/review/m6_real_adapter_rc_gate_run.json",
        json_output=str(tmp_path / "handoff.json"),
        markdown_output=str(tmp_path / "handoff.md"),
    )


def test_handoff_reports_waiting_state_without_claiming_go(tmp_path: Path) -> None:
    args = args_for(
        tmp_path,
        candidate_scan={
            "decision": "NO_GO_CANDIDATES_FOUND",
            "roots": ["/repo"],
            "candidate_count": 2,
            "go_candidate_count": 0,
            "fixture_like_candidate_count": 2,
            "candidates": [],
        },
        prereq={
            "status": "NOT_READY_PRECHECK_FAILED",
            "decision": "NOT_READY",
            "preflight": [
                {"id": "fake_backend_env_absent", "ok": True},
                {"id": "bearer_token_ready", "ok": True},
                {"id": "adapter_dir_present", "ok": False},
                {"id": "docker_image_available", "ok": False},
                {"id": "host_cuda_visible", "ok": False},
            ],
        },
    )

    report = handoff.build_handoff(args)
    markdown = handoff.render_markdown(report)

    assert report["decision"] == "WAITING_FOR_REAL_ADAPTER_INPUTS"
    assert report["m6_rc_claimed_go"] is False
    assert report["release_claimed_go"] is False
    assert report["current_state"]["missing_prereq_ids"] == [
        "adapter_dir_present",
        "docker_image_available",
        "host_cuda_visible",
    ]
    assert any(row["id"] == "rc_gate_live" for row in report["command_sequence"])
    assert "M6-RC remains NOT_GO" in markdown
    assert "MIB_RUNTIME_ALLOW_FAKE_BACKEND" in markdown


def test_handoff_preserves_go_candidate_runner_command(tmp_path: Path) -> None:
    rc_command = [
        "./.venv/bin/python",
        "scripts/run_m6_real_adapter_rc_gate.py",
        "--adapter-dir",
        "/real/run/adapter",
        "--adapter-manifest",
        "/real/run/manifest.json",
    ]
    args = args_for(
        tmp_path,
        candidate_scan={
            "decision": "GO_CANDIDATES_FOUND",
            "roots": ["/real"],
            "candidate_count": 1,
            "go_candidate_count": 1,
            "fixture_like_candidate_count": 0,
            "candidates": [
                {
                    "go": True,
                    "adapter_dir": "/real/run/adapter",
                    "rc_gate_command": rc_command,
                }
            ],
        },
        prereq={
            "status": "READY_TO_RUN",
            "decision": "READY",
            "preflight": [
                {"id": "fake_backend_env_absent", "ok": True},
                {"id": "bearer_token_ready", "ok": True},
                {"id": "adapter_dir_present", "ok": True},
                {"id": "docker_image_available", "ok": True},
                {"id": "host_cuda_visible", "ok": True},
            ],
        },
    )

    report = handoff.build_handoff(args)

    assert report["decision"] == "READY_FOR_LIVE_M6_RC_GATE"
    assert report["go_candidate_commands"][0]["argv"] == rc_command
    assert report["go_candidate_commands"][0]["env"]["MIB_RUNTIME_BEARER_TOKEN"].startswith("<set-32")

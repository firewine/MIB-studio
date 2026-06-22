from __future__ import annotations

import importlib.util
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


finder = load_module("scripts/find_real_adapter_candidates.py", "find_real_adapter_candidates")
intake = load_module("scripts/verify_real_adapter_artifact.py", "verify_real_adapter_artifact_for_finder_test")


def args_for(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        root=[str(root)],
        base_model="microsoft/Phi-3.5-mini-instruct",
        image="mib-export:test",
        agent_id="finance.router.v1",
        model_cache_dir="/tmp/mib-strict-model-cache/model_cache",
        adapter_intake_json_output="artifacts/review/real_adapter_artifact_intake.json",
        endpoint_output="artifacts/review/real_trained_adapter_endpoint_evidence.md",
        endpoint_json_output="artifacts/review/real_trained_adapter_endpoint_evidence.json",
        m6_json_output="artifacts/review/m6_rc_evidence_verification.json",
        gate_json_output="artifacts/review/m6_real_adapter_rc_gate_run.json",
    )


def test_finder_reports_go_candidate_and_runner_command(tmp_path: Path) -> None:
    adapter_dir, manifest_path = intake.write_self_test_adapter(tmp_path / "candidate")

    report = finder.scan(args_for(tmp_path))

    assert report["go_candidate_count"] == 1
    row = report["candidates"][0]
    assert row["adapter_dir"] == str(adapter_dir.resolve())
    assert row["manifest_path"] == str(manifest_path.resolve())
    assert row["status"] == "GO_REAL_ADAPTER_ARTIFACT_INTAKE"
    assert "rc_gate_command" in row
    command = row["rc_gate_command"]
    assert "--adapter-dir" in command
    assert str(adapter_dir.resolve()) in command
    assert "--adapter-manifest" in command
    assert str(manifest_path.resolve()) in command


def test_finder_rejects_fixture_sized_candidate(tmp_path: Path) -> None:
    adapter_dir = tmp_path / "fixture" / "adapter"
    adapter_dir.mkdir(parents=True)
    (adapter_dir / "adapter.safetensors").write_bytes(b"fake adapter")
    (adapter_dir / "adapter_config.json").write_text('{"peft_type":"LORA"}\n', encoding="utf-8")
    (adapter_dir.parent / "manifest.json").write_text("{}\n", encoding="utf-8")

    report = finder.scan(args_for(tmp_path))

    assert report["candidate_count"] == 1
    assert report["go_candidate_count"] == 0
    assert report["fixture_like_candidate_count"] == 1
    row = report["candidates"][0]
    assert row["status"] == "NOT_GO_REAL_ADAPTER_ARTIFACT_INTAKE"
    assert "rc_gate_command" not in row


def test_finder_reports_missing_roots_without_failing_scan(tmp_path: Path) -> None:
    report = finder.scan(args_for(tmp_path / "missing"))

    assert report["candidate_count"] == 0
    assert report["go_candidate_count"] == 0
    assert report["scan_errors"]
    assert report["scan_errors"][0]["error"] == "root does not exist"

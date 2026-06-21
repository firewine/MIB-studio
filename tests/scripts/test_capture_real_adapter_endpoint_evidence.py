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


capture = load_module("scripts/capture_real_adapter_endpoint_evidence.py", "capture_real_adapter_endpoint_evidence")
verify = load_module("scripts/verify_m6_rc_evidence.py", "verify_m6_rc_evidence")


def test_docker_run_command_uses_readonly_cache_and_no_fake_backend(tmp_path: Path) -> None:
    cache = tmp_path / "model-cache"
    cache.mkdir()
    token = "x" * 32

    command = capture.docker_run_command(
        image="mib-export:test",
        name="mib-real-adapter-test",
        port=18084,
        model_cache_dir=cache,
        token=token,
    )

    joined = " ".join(command)
    assert "--gpus all" in joined
    assert f"{cache.resolve()}:/models:ro" in command
    assert "MIB_MODEL_CACHE_DIR=/models" in command
    assert f"MIB_RUNTIME_BEARER_TOKEN={token}" in command
    assert "MIB_RUNTIME_ALLOW_FAKE_BACKEND" not in joined


def test_docker_run_command_rejects_short_token(tmp_path: Path) -> None:
    cache = tmp_path / "model-cache"
    cache.mkdir()

    try:
        capture.docker_run_command(
            image="mib-export:test",
            name="mib-real-adapter-test",
            port=18084,
            model_cache_dir=cache,
            token="short",
        )
    except ValueError as exc:
        assert "at least 32" in str(exc)
    else:
        raise AssertionError("short token must fail")


def test_live_report_rejects_non_sha256_adapter_intake_hashes(tmp_path: Path) -> None:
    cache = tmp_path / "model-cache"
    cache.mkdir()
    intake = tmp_path / "adapter-intake.json"
    intake.write_text(
        json.dumps(
            {
                "status": "GO_REAL_ADAPTER_ARTIFACT_INTAKE",
                "adapter_sha256": "A" * 64,
                "artifact_manifest_sha256": "b" * 64,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    args = SimpleNamespace(
        adapter_intake_report=str(intake),
        agent_id="agent.v1",
        container_name="unused",
        host_port=18084,
        image="mib-export:test",
        input_text="finance_income income calculation",
        keep_container=False,
        model_cache_dir=str(cache),
        timeout_seconds=1,
        token="x" * 32,
    )

    try:
        capture.live_report(args)
    except SystemExit as exc:
        assert "lowercase SHA-256 adapter_sha256" in str(exc)
    else:
        raise AssertionError("non-lowercase adapter hash must fail")


def test_rendered_self_test_evidence_contains_markers_but_verifier_rejects_it(tmp_path: Path) -> None:
    output = tmp_path / "self-test-evidence.md"
    report = capture.self_test_report()
    output.write_text(capture.render_markdown(report), encoding="utf-8")
    output.with_suffix(".json").write_text(
        json.dumps(capture.normalize_report(report), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    text = output.read_text(encoding="utf-8")

    assert "Decision: `GO_REAL_TRAINED_ADAPTER_ENDPOINT`" in text
    assert "MIB_RUNTIME_ALLOW_FAKE_BACKEND: absent" in text
    assert "/agents/{agent_id}/run: 200" in text
    assert "/v1/chat/completions: 200" in text
    assert "real_trained_adapter: true" in text
    assert "adapter_intake_verified: true" in text
    assert "self_test: true" in text

    result = verify.real_endpoint_check(str(output))
    assert result["present"] is True
    assert result["self_test"] is True
    assert result["ok"] is False
    assert result["source"] == "self_test"


def test_output_equivalence_requires_openai_content_to_match_native_output() -> None:
    native = capture.EndpointResult(
        status=200,
        text="",
        body={
            "output": {
                "route": "finance_income",
                "task_type": "provide_advice",
                "requires_calculation": True,
                "requires_human_review": False,
                "confidence": 0.94,
            }
        },
    )
    openai = capture.EndpointResult(
        status=200,
        text="",
        body={"choices": [{"message": {"content": '{"confidence": 0.94, "requires_calculation": true, "requires_human_review": false, "route": "finance_income", "task_type": "provide_advice"}'}}]},
    )

    equal, payload = capture.verify_endpoint_outputs(native, openai)

    assert equal is True
    assert payload["native_output"] == payload["openai_output"]


def test_m6_verifier_requires_adapter_intake_marker(tmp_path: Path) -> None:
    evidence = tmp_path / "endpoint.md"
    evidence.write_text(
        """# Real Trained Adapter Endpoint Evidence

Decision: `GO_REAL_TRAINED_ADAPTER_ENDPOINT`

```yaml
MIB_RUNTIME_ALLOW_FAKE_BACKEND: absent
/agents/{agent_id}/run: 200
/v1/chat/completions: 200
real_trained_adapter: true
self_test: false
```
""",
        encoding="utf-8",
    )

    result = verify.real_endpoint_check(str(evidence))

    assert result["ok"] is False
    assert "structured endpoint JSON sidecar" in result["missing_markers"]
    assert "adapter_intake_verified: true" in result["missing_markers"]


def test_m6_verifier_rejects_markdown_only_endpoint_evidence_even_with_all_markers(tmp_path: Path) -> None:
    evidence = tmp_path / "endpoint.md"
    evidence.write_text(
        """# Real Trained Adapter Endpoint Evidence

Decision: `GO_REAL_TRAINED_ADAPTER_ENDPOINT`

```yaml
MIB_RUNTIME_ALLOW_FAKE_BACKEND: absent
/agents/{agent_id}/run: 200
/v1/chat/completions: 200
real_trained_adapter: true
adapter_intake_verified: true
self_test: false
```
""",
        encoding="utf-8",
    )

    result = verify.real_endpoint_check(str(evidence))

    assert result["ok"] is False
    assert result["source"] == "markdown_only"
    assert result["missing_markers"] == ["structured endpoint JSON sidecar"]


def test_m6_verifier_accepts_structured_live_endpoint_json(tmp_path: Path) -> None:
    evidence = tmp_path / "endpoint.md"
    evidence.write_text("structured sidecar owns this evidence\n", encoding="utf-8")
    report = capture.normalize_report(capture.self_test_report())
    report.update({"self_test": False, "source": "live_docker_capture"})
    evidence.with_suffix(".json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    result = verify.real_endpoint_check(str(evidence))

    assert result["ok"] is True
    assert result["source"] == "live_docker_capture"


def test_m6_verifier_rejects_structured_endpoint_json_without_readonly_mount(tmp_path: Path) -> None:
    evidence = tmp_path / "endpoint.md"
    evidence.write_text("structured sidecar owns this evidence\n", encoding="utf-8")
    report = capture.normalize_report(capture.self_test_report())
    report.update(
        {
            "readonly_model_cache_mount": False,
            "self_test": False,
            "source": "live_docker_capture",
        }
    )
    evidence.with_suffix(".json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    result = verify.real_endpoint_check(str(evidence))

    assert result["ok"] is False
    assert "readonly_model_cache_mount" in result["missing_markers"]

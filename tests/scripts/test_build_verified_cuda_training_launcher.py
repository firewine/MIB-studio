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


launcher = load_module("scripts/build_verified_cuda_training_launcher.py", "build_verified_cuda_training_launcher")


def args_for(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        python="./.venv/bin/python",
        verifier_script="scripts/verify_external_cuda_operator_packet.py",
        packet_json="artifacts/review/external_cuda_operator_packet.json",
        verification_output="artifacts/review/external_cuda_operator_packet_verification.json",
        training_handoff_shell="artifacts/review/real_adapter_cuda_training_handoff.sh",
        json_output=str(tmp_path / "launcher.json"),
        markdown_output=str(tmp_path / "launcher.md"),
        shell_output=str(tmp_path / "launcher.sh"),
    )


def test_launcher_runs_packet_verifier_before_training_handoff(tmp_path: Path) -> None:
    result = launcher.build_launcher(args_for(tmp_path))
    markdown = launcher.render_markdown(result)
    shell = launcher.render_shell(result)

    assert result["schema_version"] == launcher.SCHEMA_VERSION
    assert result["status"] == launcher.STATUS
    assert result["release_claimed_go"] is False
    assert result["m6_rc_claimed_go"] is False
    assert [row["id"] for row in result["command_sequence"]] == [
        "verify_external_cuda_operator_packet",
        "run_real_adapter_cuda_training_handoff",
    ]
    assert result["inputs"]["expected_verifier_decision"] == launcher.VERIFIER_DECISION
    assert "scripts/verify_external_cuda_operator_packet.py" in shell
    assert "GO" in shell
    assert "artifacts/review/real_adapter_cuda_training_handoff.sh" in shell
    assert shell.index("== verify_external_cuda_operator_packet ==") < shell.index("== run_real_adapter_cuda_training_handoff ==")
    assert "MIB_RUNTIME_ALLOW_FAKE_BACKEND must be unset" in shell
    assert "operator packet verifier is missing" in shell
    assert "operator packet JSON is missing" in shell
    assert "CUDA training handoff shell is missing" in shell
    assert "release_claimed_go: false" in markdown
    assert "copied evidence bundles" in markdown


def test_main_writes_launcher_artifacts(tmp_path: Path, monkeypatch) -> None:
    args = args_for(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_verified_cuda_training_launcher.py",
            "--json-output",
            args.json_output,
            "--markdown-output",
            args.markdown_output,
            "--shell-output",
            args.shell_output,
        ],
    )

    assert launcher.main() == 0
    assert Path(args.json_output).is_file()
    assert Path(args.markdown_output).is_file()
    assert Path(args.shell_output).is_file()
    assert "verify_external_cuda_operator_packet" in Path(args.shell_output).read_text(encoding="utf-8")

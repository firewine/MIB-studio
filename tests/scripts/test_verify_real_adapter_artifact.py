from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from safetensors.numpy import save_file


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


verify_adapter_module = load_module("scripts/verify_real_adapter_artifact.py", "verify_real_adapter_artifact")


def test_real_adapter_intake_rejects_fixture_sized_adapter(tmp_path: Path) -> None:
    adapter_dir = tmp_path / "run" / "adapter"
    adapter_dir.mkdir(parents=True)
    (adapter_dir / "adapter.safetensors").write_bytes(b"fake adapter")
    (adapter_dir / "adapter_config.json").write_text('{"format":"lora_adapter"}\n', encoding="utf-8")

    report = verify_adapter_module.verify_adapter(
        adapter_dir=adapter_dir,
        expected_base_model="microsoft/Phi-3.5-mini-instruct",
    )

    assert report["status"] == "NOT_GO_REAL_ADAPTER_ARTIFACT_INTAKE"
    assert any("fixture-sized" in error for error in report["errors"])
    assert any("peft_type must be LORA" in error for error in report["errors"])


def test_real_adapter_intake_accepts_real_like_peft_lora_with_manifest(tmp_path: Path) -> None:
    adapter_dir = tmp_path / "run" / "adapter"
    adapter_dir.mkdir(parents=True)
    save_file(
        {
            "base_model.model.layers.0.self_attn.q_proj.lora_A.weight": np.ones((64, 64), dtype=np.float32),
            "base_model.model.layers.0.self_attn.q_proj.lora_B.weight": np.ones((64, 64), dtype=np.float32),
        },
        adapter_dir / "adapter.safetensors",
    )
    (adapter_dir / "adapter_config.json").write_text(
        json.dumps(
            {
                "base_model_name_or_path": "microsoft/Phi-3.5-mini-instruct",
                "lora_alpha": 16,
                "peft_type": "LORA",
                "r": 8,
                "target_modules": ["q_proj"],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    rows = verify_adapter_module.adapter_file_rows(adapter_dir)
    adapter_sha = verify_adapter_module.sha256_text(verify_adapter_module.canonical_json(rows))
    manifest = {
        "adapter_format": "lora_adapter",
        "adapter_sha256": adapter_sha,
        "files": rows,
        "trainer_backend": "llamafactory",
    }
    manifest_path = adapter_dir.parent / "manifest.json"
    manifest_path.write_text(verify_adapter_module.canonical_json(manifest) + "\n", encoding="utf-8")

    report = verify_adapter_module.verify_adapter(
        adapter_dir=adapter_dir,
        expected_base_model="microsoft/Phi-3.5-mini-instruct",
        manifest_path=manifest_path,
    )

    assert report["status"] == "GO_REAL_ADAPTER_ARTIFACT_INTAKE"
    assert report["errors"] == []
    assert report["safetensors"]["lora_key_count"] == 2
    assert report["config"]["base_model"] == "microsoft/Phi-3.5-mini-instruct"


def test_real_adapter_intake_rejects_base_model_mismatch(tmp_path: Path) -> None:
    adapter_dir, manifest_path = verify_adapter_module.write_self_test_adapter(tmp_path)

    report = verify_adapter_module.verify_adapter(
        adapter_dir=adapter_dir,
        expected_base_model="google/gemma-2b-it",
        manifest_path=manifest_path,
    )

    assert report["status"] == "NOT_GO_REAL_ADAPTER_ARTIFACT_INTAKE"
    assert any("does not match expected" in error for error in report["errors"])

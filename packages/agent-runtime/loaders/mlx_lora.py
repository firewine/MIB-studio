from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agents.router_inference import run_router_inference


@dataclass
class MlxLoraAdapter:
    adapter_dir: Path
    model_cache_dir: Path
    fake_backend: bool = False
    invocation_count: int = 0
    model: Any = None
    tokenizer: Any = None

    def infer(self, *, input_payload: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
        self.invocation_count += 1
        if self.fake_backend:
            return run_router_inference(input_payload=input_payload, contract=contract, adapter={"backend": "mlx_lm"})
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("MLX_BACKEND_NOT_LOADED")
        prompt = json.dumps(input_payload, sort_keys=True)
        response = self.model.generate(prompt, temp=0)
        return json.loads(str(response)[str(response).rfind("{") :])


def load_mlx_lora(adapter_dir: Path, contract: dict[str, Any], *, model_cache_dir: Path) -> MlxLoraAdapter:
    _require_files(adapter_dir, ["adapters.npz", "adapter_config.json"])
    if os.environ.get("MIB_RUNTIME_ALLOW_FAKE_BACKEND") == "1":
        return MlxLoraAdapter(adapter_dir=adapter_dir, model_cache_dir=model_cache_dir, fake_backend=True)
    try:
        from mlx_lm import load
    except Exception as exc:
        raise RuntimeError("MLX_BACKEND_UNAVAILABLE") from exc
    model, tokenizer = load(str(model_cache_dir), adapter_path=str(adapter_dir))
    return MlxLoraAdapter(adapter_dir=adapter_dir, model_cache_dir=model_cache_dir, model=model, tokenizer=tokenizer)


def _require_files(adapter_dir: Path, names: list[str]) -> None:
    missing = [name for name in names if not (adapter_dir / name).is_file()]
    if missing:
        raise RuntimeError(f"EXPORT_ADAPTER_FORMAT_MISMATCH: missing {','.join(missing)}")

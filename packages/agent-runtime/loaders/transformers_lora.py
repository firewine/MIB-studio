from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agents.router_inference import run_router_inference


@dataclass
class TransformersLoraAdapter:
    adapter_dir: Path
    model_cache_dir: Path
    fake_backend: bool = False
    invocation_count: int = 0
    tokenizer: Any = None
    model: Any = None

    def infer(self, *, input_payload: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
        self.invocation_count += 1
        if self.fake_backend:
            return run_router_inference(input_payload=input_payload, contract=contract, adapter={"backend": "transformers"})
        if self.tokenizer is None or self.model is None:
            raise RuntimeError("TRANSFORMERS_BACKEND_NOT_LOADED")
        prompt = json.dumps(input_payload, sort_keys=True)
        encoded = self.tokenizer(prompt, return_tensors="pt")
        generated = self.model.generate(**encoded, max_new_tokens=128, do_sample=False)
        text = self.tokenizer.decode(generated[0], skip_special_tokens=True)
        return json.loads(text[text.rfind("{") :])


def load_transformers_lora(adapter_dir: Path, contract: dict[str, Any], *, model_cache_dir: Path) -> TransformersLoraAdapter:
    _require_files(adapter_dir, ["adapter.safetensors", "adapter_config.json"])
    if os.environ.get("MIB_RUNTIME_ALLOW_FAKE_BACKEND") == "1":
        return TransformersLoraAdapter(adapter_dir=adapter_dir, model_cache_dir=model_cache_dir, fake_backend=True)
    try:
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except Exception as exc:
        raise RuntimeError("TRANSFORMERS_BACKEND_UNAVAILABLE") from exc
    tokenizer = AutoTokenizer.from_pretrained(model_cache_dir, local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(model_cache_dir, local_files_only=True, trust_remote_code=False)
    return TransformersLoraAdapter(
        adapter_dir=adapter_dir,
        model_cache_dir=model_cache_dir,
        tokenizer=tokenizer,
        model=PeftModel.from_pretrained(model, adapter_dir),
    )


def _require_files(adapter_dir: Path, names: list[str]) -> None:
    missing = [name for name in names if not (adapter_dir / name).is_file()]
    if missing:
        raise RuntimeError(f"EXPORT_ADAPTER_FORMAT_MISMATCH: missing {','.join(missing)}")

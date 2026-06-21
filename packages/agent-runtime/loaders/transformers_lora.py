from __future__ import annotations

from pathlib import Path


def load_transformers_lora(adapter_dir: Path, contract: dict) -> dict:
    return {
        "backend": "transformers",
        "adapter_dir": str(adapter_dir),
        "base_model": contract["adapter"]["base_model"],
    }

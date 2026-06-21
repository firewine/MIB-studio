from __future__ import annotations

from pathlib import Path


def load_mlx_lora(adapter_dir: Path, contract: dict) -> dict:
    return {
        "backend": "mlx_lm",
        "adapter_dir": str(adapter_dir),
        "base_model": contract["adapter"]["base_model"],
    }

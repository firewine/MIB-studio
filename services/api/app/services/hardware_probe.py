from __future__ import annotations

import os
import platform
import socket
import hashlib
from dataclasses import dataclass
from typing import Any

from services.api.app.schemas.hardware import HardwareScanRequest


@dataclass(frozen=True)
class LocalProbe:
    machine_id: str
    os_name: str
    cpu: str | None
    ram_gb: float
    gpu_vendor: str
    gpu_name: str | None
    vram_gb: float | None
    unified_ram_gb: float | None
    cuda_status: str | None
    mlx_status: str | None


@dataclass(frozen=True)
class GateDecision:
    capability_gate: str
    backend_recommendation: str
    training_enabled: bool
    reason_code: str
    reason_message: str
    allowed_backends: list[str]
    unlock_requirements: list[str]
    risk: str


def collect_local_probe() -> LocalProbe:
    vendor = env_text("MIB_HW_GPU_VENDOR") or inferred_gpu_vendor()
    ram_gb = env_float("MIB_HW_RAM_GB") or system_ram_gb()
    unified_ram = env_float("MIB_HW_UNIFIED_RAM_GB")
    if vendor == "apple" and unified_ram is None:
        unified_ram = ram_gb
    return LocalProbe(
        machine_id=env_text("MIB_HW_MACHINE_ID") or machine_id(),
        os_name=env_text("MIB_HW_OS") or f"{platform.system()} {platform.release()}",
        cpu=env_text("MIB_HW_CPU") or platform.processor() or platform.machine() or None,
        ram_gb=ram_gb,
        gpu_vendor=vendor,
        gpu_name=env_text("MIB_HW_GPU_NAME") or ("Apple Silicon" if vendor == "apple" else None),
        vram_gb=env_float("MIB_HW_VRAM_GB"),
        unified_ram_gb=unified_ram,
        cuda_status=env_text("MIB_HW_CUDA_STATUS") or ("ok" if vendor == "nvidia" else "na"),
        mlx_status=env_text("MIB_HW_MLX_STATUS") or ("ok" if vendor == "apple" else "na"),
    )


def inferred_gpu_vendor() -> str:
    if platform.system() == "Darwin" and platform.machine().lower().startswith("arm"):
        return "apple"
    return "none"


def decide_gate(probe: LocalProbe, target_backend: str) -> GateDecision:
    if target_backend == "cuda" and probe.gpu_vendor != "nvidia":
        return disabled("G0", "unsupported", "UNSUPPORTED_VENDOR", "CUDA requires NVIDIA GPU.", ["Use target_backend=auto."])
    if target_backend == "mlx" and probe.gpu_vendor != "apple":
        return disabled("G0", "unsupported", "UNSUPPORTED_VENDOR", "MLX requires Apple Silicon.", ["Use target_backend=auto."])
    if probe.gpu_vendor == "nvidia":
        return nvidia_gate(probe)
    if probe.gpu_vendor == "apple":
        return apple_gate(probe)
    if probe.gpu_vendor == "none":
        return disabled("G0", "cpu", "NO_GPU", "No supported training GPU was detected.", ["Use BYO Cloud Teacher or add NVIDIA/Apple Silicon hardware."])
    return disabled("G0", "unsupported", "UNSUPPORTED_VENDOR", "This GPU vendor is not supported for v0 training.", ["Use NVIDIA CUDA or Apple Silicon MLX hardware."])


def nvidia_gate(probe: LocalProbe) -> GateDecision:
    if probe.cuda_status != "ok":
        return disabled("G0", "cpu", "MISSING_DRIVER", "CUDA driver or runtime is missing.", ["Install working NVIDIA CUDA drivers."])
    vram = probe.vram_gb or 0.0
    if vram >= 24:
        return enabled("G2", "cuda", ["cuda"], "low")
    if vram >= 12:
        return enabled("G1", "cuda", ["cuda"], "medium")
    return disabled("G0", "cpu", "LOW_VRAM", "NVIDIA VRAM is below the 12GB v0 training minimum.", ["Use an NVIDIA GPU with at least 12GB VRAM."])


def apple_gate(probe: LocalProbe) -> GateDecision:
    if probe.mlx_status != "ok":
        return disabled("G0", "cpu", "MISSING_DRIVER", "MLX runtime is unavailable.", ["Install MLX on Apple Silicon."])
    unified_ram = probe.unified_ram_gb or probe.ram_gb
    if unified_ram >= 32:
        return enabled("G2", "mlx", ["mlx"], "low")
    if unified_ram >= 16:
        return enabled("G1", "mlx", ["mlx"], "medium")
    return disabled("G0", "cpu", "LOW_VRAM", "Apple unified RAM is below the 16GB v0 training minimum.", ["Use Apple Silicon with at least 16GB unified RAM."])


def enabled(gate: str, recommendation: str, allowed_backends: list[str], risk: str) -> GateDecision:
    return GateDecision(gate, recommendation, True, "NONE", "Training is enabled for this hardware gate.", allowed_backends, [], risk)


def disabled(gate: str, recommendation: str, reason: str, message: str, requirements: list[str]) -> GateDecision:
    return GateDecision(gate, recommendation, False, reason, message, [], requirements, "high")


def dry_run_payload(probe: LocalProbe, decision: GateDecision, payload: HardwareScanRequest) -> dict[str, Any]:
    memory = probe.vram_gb if probe.gpu_vendor == "nvidia" else probe.unified_ram_gb
    return {
        "gate": decision.capability_gate,
        "gpu_vendor": probe.gpu_vendor,
        "vram_gb": probe.vram_gb,
        "unified_ram_gb": probe.unified_ram_gb,
        "cuda": probe.cuda_status == "ok",
        "mlx": probe.mlx_status == "ok",
        "training_enabled": decision.training_enabled,
        "training_disabled_reason_code": decision.reason_code,
        "training_disabled_reason_message": decision.reason_message,
        "allowed_backends": decision.allowed_backends,
        "backend_recommendation": decision.backend_recommendation,
        "unlock_requirements": decision.unlock_requirements,
        "model": "google/gemma-2b-it",
        "seq_len": 1024,
        "batch": 1,
        "grad_accum": 16 if decision.capability_gate == "G2" else 8,
        "lora_rank": 16 if decision.capability_gate == "G2" else 8,
        "vram_peak_gb": round(memory * 0.72, 2) if memory else None,
        "tokens_per_sec": 0.0 if payload.dry_run else None,
        "est_minutes_per_1k": 25 if decision.training_enabled else None,
        "risk": decision.risk,
        "failure_details": None if decision.training_enabled else {"code": decision.reason_code, "message": decision.reason_message},
    }


def env_text(name: str) -> str | None:
    value = os.environ.get(name)
    return value if value else None


def env_float(name: str) -> float | None:
    value = env_text(name)
    return float(value) if value is not None else None


def system_ram_gb() -> float:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return round((pages * page_size) / (1024**3), 2)
    except (AttributeError, OSError, ValueError):
        return 16.0


def machine_id() -> str:
    seed = f"{socket.gethostname()}:{platform.platform()}:{platform.machine()}"
    return sha256_text(seed)[:32]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

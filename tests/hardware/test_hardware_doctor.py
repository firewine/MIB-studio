from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config

from services.api.app.core.config import Settings
from services.api.app.main import create_app
from services.shared.db.models import HardwareProfile, Job
from services.shared.db.session import create_sqlite_engine, session_factory


HW_ENV = [
    "MIB_HW_MACHINE_ID",
    "MIB_HW_OS",
    "MIB_HW_CPU",
    "MIB_HW_RAM_GB",
    "MIB_HW_GPU_VENDOR",
    "MIB_HW_GPU_NAME",
    "MIB_HW_VRAM_GB",
    "MIB_HW_UNIFIED_RAM_GB",
    "MIB_HW_CUDA_STATUS",
    "MIB_HW_MLX_STATUS",
]


def alembic_config(db_path: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def prepare_database(tmp_path: Path) -> str:
    tmp_path.mkdir(parents=True, exist_ok=True)
    db_path = tmp_path / "hardware.db"
    command.upgrade(alembic_config(db_path), "head")
    return f"sqlite:///{db_path}"


def auth_headers(token: str = "test-token", idempotency_key: str | None = None) -> dict[str, str]:
    headers = {"host": "127.0.0.1:8910", "authorization": f"Bearer {token}"}
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def client_for(database_url: str) -> httpx.AsyncClient:
    settings = Settings(app_env="production", dev_auth="bootstrap", bootstrap_token="test-token", database_url=database_url)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings)),
        base_url="http://127.0.0.1:8910",
    )


def set_probe(monkeypatch: pytest.MonkeyPatch, **values: str) -> None:
    for name in HW_ENV:
        monkeypatch.delenv(name, raising=False)
    defaults = {
        "MIB_HW_MACHINE_ID": "test-machine",
        "MIB_HW_OS": "Linux test",
        "MIB_HW_CPU": "Test CPU",
        "MIB_HW_RAM_GB": "32",
    }
    defaults.update(values)
    for name, value in defaults.items():
        monkeypatch.setenv(name, value)


async def post_scan(client: httpx.AsyncClient, *, idempotency_key: str | None = None, target_backend: str = "auto") -> httpx.Response:
    return await asyncio.wait_for(
        client.post(
            "/hardware-doctor/scan",
            json={"dry_run": True, "target_backend": target_backend},
            headers=auth_headers(idempotency_key=idempotency_key),
        ),
        timeout=10,
    )


async def get_result(client: httpx.AsyncClient) -> httpx.Response:
    return await asyncio.wait_for(client.get("/hardware-doctor/result", headers=auth_headers()), timeout=10)


@pytest.mark.asyncio
async def test_hardware_doctor_empty_result_returns_404(tmp_path: Path) -> None:
    async with client_for(prepare_database(tmp_path)) as client:
        response = await get_result(client)

    assert response.status_code == 404
    assert response.json()["error_code"] == "HARDWARE_PROFILE_NOT_FOUND"


@pytest.mark.asyncio
async def test_hardware_doctor_g0_cpu_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    set_probe(monkeypatch, MIB_HW_GPU_VENDOR="none")
    database_url = prepare_database(tmp_path)

    async with client_for(database_url) as client:
        accepted = await post_scan(client)
        result = await get_result(client)

    assert accepted.status_code == 202
    assert accepted.json()["status"] == "SUCCEEDED"
    assert accepted.json()["type"] == "hardware_scan"
    assert accepted.json()["created_resource_type"] == "hardware_scan"

    profile = result.json()
    assert profile["capability_gate"] == "G0"
    assert profile["gpu_vendor"] == "none"
    assert profile["backend_recommendation"] == "cpu"
    assert profile["training_enabled"] is False
    assert profile["training_disabled_reason_code"] == "NO_GPU"
    assert profile["allowed_backends"] == []
    assert profile["dry_run_result_json"]["risk"] == "high"

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    with factory() as session:
        assert session.query(Job).filter_by(type="hardware_scan").count() == 1
        assert session.query(HardwareProfile).count() == 1
    engine.dispose()


@pytest.mark.asyncio
async def test_hardware_doctor_g1_nvidia_supported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    set_probe(
        monkeypatch,
        MIB_HW_GPU_VENDOR="nvidia",
        MIB_HW_GPU_NAME="RTX Test 16GB",
        MIB_HW_VRAM_GB="16",
        MIB_HW_CUDA_STATUS="ok",
    )

    async with client_for(prepare_database(tmp_path)) as client:
        await post_scan(client)
        result = await get_result(client)

    profile = result.json()
    assert profile["capability_gate"] == "G1"
    assert profile["backend_recommendation"] == "cuda"
    assert profile["training_enabled"] is True
    assert profile["training_disabled_reason_code"] == "NONE"
    assert profile["allowed_backends"] == ["cuda"]


@pytest.mark.asyncio
async def test_hardware_doctor_g2_nvidia_supported_and_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    set_probe(
        monkeypatch,
        MIB_HW_GPU_VENDOR="nvidia",
        MIB_HW_GPU_NAME="RTX Test 24GB",
        MIB_HW_VRAM_GB="24",
        MIB_HW_CUDA_STATUS="ok",
    )

    async with client_for(prepare_database(tmp_path)) as client:
        first = await post_scan(client, idempotency_key="scan-key")
        replay = await post_scan(client, idempotency_key="scan-key")
        result = await get_result(client)

    assert replay.json()["job_id"] == first.json()["job_id"]
    assert replay.json()["idempotency_replayed"] is True
    profile = result.json()
    assert profile["capability_gate"] == "G2"
    assert profile["dry_run_result_json"]["lora_rank"] == 16


@pytest.mark.asyncio
async def test_hardware_doctor_training_disabled_reason_codes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    set_probe(
        monkeypatch,
        MIB_HW_GPU_VENDOR="nvidia",
        MIB_HW_GPU_NAME="RTX Test 8GB",
        MIB_HW_VRAM_GB="8",
        MIB_HW_CUDA_STATUS="ok",
    )
    async with client_for(prepare_database(tmp_path)) as client:
        await post_scan(client)
        low_vram = await get_result(client)
    assert low_vram.json()["training_disabled_reason_code"] == "LOW_VRAM"

    set_probe(monkeypatch, MIB_HW_GPU_VENDOR="amd", MIB_HW_GPU_NAME="AMD Test GPU")
    async with client_for(prepare_database(tmp_path / "unsupported")) as client:
        await post_scan(client)
        unsupported = await get_result(client)
    assert unsupported.json()["training_disabled_reason_code"] == "UNSUPPORTED_VENDOR"
    assert unsupported.json()["backend_recommendation"] == "unsupported"


@pytest.mark.asyncio
async def test_hardware_doctor_idempotency_conflict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    set_probe(monkeypatch, MIB_HW_GPU_VENDOR="none")

    async with client_for(prepare_database(tmp_path)) as client:
        first = await post_scan(client, idempotency_key="same-key", target_backend="auto")
        conflict = await post_scan(client, idempotency_key="same-key", target_backend="cuda")

    assert first.status_code == 202
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == "IDEMPOTENCY_CONFLICT"

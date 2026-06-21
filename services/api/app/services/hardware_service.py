from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.core.errors import APIError
from services.api.app.schemas.hardware import HardwareProfileRead, HardwareScanRequest, JobAcceptedResponse
from services.api.app.services.hardware_probe import GateDecision, LocalProbe, collect_local_probe, decide_gate, dry_run_payload
from services.shared.db.models import HardwareProfile, Job, JobResource


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def new_id() -> str:
    return uuid.uuid4().hex


class HardwareService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def submit_scan(
        self,
        payload: HardwareScanRequest,
        *,
        idempotency_key: str | None,
        trace_id: str,
    ) -> JobAcceptedResponse:
        body_hash = sha256_text(canonical_json(payload.model_dump()))
        if idempotency_key:
            existing = self._job_by_idempotency_key(idempotency_key)
            if existing is not None:
                if existing.idempotency_body_sha256 != body_hash:
                    raise APIError(
                        "IDEMPOTENCY_CONFLICT",
                        "Idempotency-Key was already used with a different hardware scan request.",
                        status_code=409,
                        details={"idempotency_key": idempotency_key},
                    )
                return self._accepted_response(existing, idempotency_replayed=True)

        now = utc_now()
        probe = collect_local_probe()
        decision = decide_gate(probe, payload.target_backend)
        profile = self._create_profile(probe, decision, payload, created_at=now)
        job = Job(
            id=new_id(),
            project_id=None,
            type="hardware_scan",
            resource_class="cpu_shared",
            status="SUCCEEDED",
            priority=0,
            params_json=canonical_json(payload.model_dump()),
            idempotency_key=idempotency_key,
            idempotency_body_sha256=body_hash if idempotency_key else None,
            idempotency_expires_at=(datetime.now(UTC) + timedelta(hours=24)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            if idempotency_key
            else None,
            attempt_count=0,
            trace_id=trace_id,
            created_at=now,
            started_at=now,
            ended_at=now,
        )
        self.session.add(job)
        self.session.flush()
        self.session.add(
            JobResource(
                job_id=job.id,
                resource_type="hardware_profile",
                resource_id=profile.id,
                is_current=1,
                created_at=now,
            )
        )
        self.session.flush()
        return self._accepted_response(job, idempotency_replayed=False)

    def latest(self) -> HardwareProfileRead:
        profile = self.session.scalars(select(HardwareProfile).order_by(HardwareProfile.created_at.desc()).limit(1)).first()
        if profile is None:
            raise APIError("HARDWARE_PROFILE_NOT_FOUND", "No hardware scan result exists.", status_code=404)
        return self._read_profile(profile)

    def _job_by_idempotency_key(self, idempotency_key: str) -> Job | None:
        statement = select(Job).where(Job.project_id.is_(None), Job.idempotency_key == idempotency_key).limit(1)
        return self.session.scalars(statement).first()

    def _create_profile(
        self,
        probe: LocalProbe,
        decision: GateDecision,
        payload: HardwareScanRequest,
        *,
        created_at: str,
    ) -> HardwareProfile:
        dry_run = dry_run_payload(probe, decision, payload)
        profile = HardwareProfile(
            id=new_id(),
            machine_id=probe.machine_id,
            os=probe.os_name,
            cpu=probe.cpu,
            ram_gb=probe.ram_gb,
            gpu_vendor=probe.gpu_vendor,
            gpu_name=probe.gpu_name,
            vram_gb=probe.vram_gb,
            unified_ram_gb=probe.unified_ram_gb,
            cuda_status=probe.cuda_status,
            mlx_status=probe.mlx_status,
            capability_gate=decision.capability_gate,
            dry_run_result_json=canonical_json(dry_run),
            created_at=created_at,
        )
        self.session.add(profile)
        self.session.flush()
        return profile

    def _accepted_response(self, job: Job, *, idempotency_replayed: bool) -> JobAcceptedResponse:
        resource = self.session.get(JobResource, job.id)
        return JobAcceptedResponse(
            job_id=job.id,
            status=job.status,  # type: ignore[arg-type]
            type=job.type,
            events_url=f"/jobs/{job.id}/events",
            created_resource_type="hardware_scan",
            created_resource_id=resource.resource_id if resource is not None else None,
            idempotency_replayed=idempotency_replayed,
        )

    def _read_profile(self, profile: HardwareProfile) -> HardwareProfileRead:
        dry_run = json.loads(profile.dry_run_result_json)
        return HardwareProfileRead(
            id=profile.id,
            machine_id=profile.machine_id,
            os=profile.os,
            cpu=profile.cpu,
            gpu_vendor=profile.gpu_vendor,  # type: ignore[arg-type]
            gpu_name=profile.gpu_name,
            vram_gb=profile.vram_gb,
            unified_ram_gb=profile.unified_ram_gb,
            ram_gb=profile.ram_gb,
            cuda_status=profile.cuda_status,  # type: ignore[arg-type]
            mlx_status=profile.mlx_status,  # type: ignore[arg-type]
            capability_gate=profile.capability_gate,  # type: ignore[arg-type]
            backend_recommendation=dry_run["backend_recommendation"],
            training_enabled=bool(dry_run["training_enabled"]),
            training_disabled_reason_code=dry_run["training_disabled_reason_code"],
            training_disabled_reason_message=dry_run["training_disabled_reason_message"],
            allowed_backends=dry_run["allowed_backends"],
            unlock_requirements=dry_run["unlock_requirements"],
            dry_run_result_json=dry_run,
            created_at=profile.created_at,
        )

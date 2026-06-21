# M0 BE/API Review

Decision: GO
Reviewer: Codex BE/API Agent
Date: 2026-06-21
Scope: FastAPI routes, DTOs, auth/CORS, idempotency, Job queue, worker handoff, Hardware Doctor submit.

## Blocking Issues

None.

## Non-Blocking Issues

- CORS preflight is middleware-only, Host/Origin checked before Bearer bypass, and side-effect free.
- `HardwareScanRequest` maps to `Job(type='hardware_scan', project_id=NULL, resource_class='cpu_shared')`.
- `EvalParams.target` reuses `BenchmarkTargetConfig`.
- Retry/resume response contract includes `child_job_id`; child job rebinding is explicit for FE and BE.
- Benchmark submit uses `resource_class='gpu_exclusive'`, preserving the one-running-GPU-job invariant.

## Missing Tests

None blocking for M0. Endpoint and job-store tests are listed in `IMPLEMENTATION_GUIDE §5`.

## Spec Updates Required

None.

## Assumptions

Local Daemon does not expose exported runtime `/agents/{agent_id}/run`.

# M0 Architecture/Code Quality Review

Decision: GO
Reviewer: Codex Architecture/Code Quality Agent
Date: 2026-06-21
Scope: API boundaries, local daemon vs exported runtime, project lifecycle, AgentPackage contract, god-file prevention, layering.

## Blocking Issues

None.

## Non-Blocking Issues

- P2: Frontend feature import checker intentionally forbids all `../` parent-relative imports. M1 FE code must use `@/features/{feature}/...` aliases or same-folder `./...` imports; this is now documented in `IMPLEMENTATION_GUIDE §3.2`.
- Local Daemon package/playground/export APIs are canonicalized.
- Exported runtime `/agents/{agent_id}/run` is separated from Local Daemon API.
- `teacher_synthetic` is only `Job.type='dataset_gen'` with `generation_mode='teacher_synthetic'`.
- Project delete is soft archive; hard purge is out of v0 API scope.
- Agent contract uses `export_compatibility`; M6 export manifest hash is produced after export.
- Day-0 `check_file_size.py` enforces per-kind hard budgets, including `job_loop.py` under the worker loop/store budget.
- Day-0 `check_import_boundaries.py` enforces backend route/service/shared/package dependency direction and frontend page/component/hook/schema/lib boundaries.

## Missing Tests

None blocking for M0. Import boundary and file-size checks are required by `IMPLEMENTATION_GUIDE §3` and pass in Day-0 scaffold verify-only.

## Spec Updates Required

None.

## Assumptions

Alembic migration files are exempt from god-file line limits because they are generated DDL.

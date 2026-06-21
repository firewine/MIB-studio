# M0 DB Review

Decision: GO
Reviewer: Codex DB Agent
Date: 2026-06-21
Scope: SQLite schema, FK/CHECK/index strategy, idempotency, job lifecycle, benchmark/eval storage, teacher approval reservation.

## Blocking Issues

None.

## Non-Blocking Issues

- Canonical SQLite DDL/index block executes successfully in SQLite: 19 tables, 60 total SQLite indexes, 27 explicit MIB-defined indexes.
- Retry/resume now uses child Job rows consistently.
- Benchmark cardinality is locked to one selected base/model_run per Benchmark; Phi uses a separate Benchmark.
- Benchmark jobs are `gpu_exclusive`, so the DB partial unique index protects train/eval/benchmark GPU occupancy.
- `audit_event.event_type` includes `job_reconcile`; reconcile audit insertion is compatible with the DDL.
- `model_run.method` is aligned with API DTO values: `qlora` and `mlx_lora`.

## Missing Tests

None blocking for M0. DB invariant tests are listed in `IMPLEMENTATION_GUIDE §6`.

## Spec Updates Required

None.

## Assumptions

`AgentPackage` stores package identity/contract metadata; concrete export files and hashes are represented by `ExportArtifact` rows. Day-0 Alembic file is a skeleton; full `upgrade/downgrade` ops are implemented in M1-002 from the locked canonical DDL.

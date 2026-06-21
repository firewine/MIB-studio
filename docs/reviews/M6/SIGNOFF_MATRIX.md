# M6 Sign-Off Matrix

| Milestone | FE | DB | BE/API | LLM/Training | Eval/QC | Security | Arch/Code | DevEx | CTO | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| M6 Export / v0 RC | GO | GO | GO | NO_GO | GO | NO_GO | GO | NO_GO | NO_GO | NOT_GO |

## Validation Evidence

- M6-001 zip export implementation: `31971d7 feat: implement m6 zip export`.
- M6-002 docker export implementation: `b6873f5 feat: implement m6 docker export`.
- FE v6 mockup implementation/evidence: `d7a68bf feat: apply fe v6 route contract mockup`, `dd48a42 docs: close out fe v6 mockup`, `artifacts/review/fe_v6_evidence.md`.
- Real Docker runtime remediation: `caf9c0f fix: remediate docker runtime evidence blockers`, `artifacts/review/docker_runtime_remediation_evidence.md`.
- Strict Phi cache and fixture endpoint path evidence: `efecb80 docs: record phi strict cache runtime evidence`, `artifacts/review/phi_strict_cache_runtime_evidence.md`.
- Real adapter blocker evidence: `fee0795 docs: record real adapter inference blocker`, `artifacts/review/real_adapter_inference_evidence.md`.
- Docker runtime real backend dependency packaging: `7b1d6a8 fix: package docker real backend dependencies`, `artifacts/review/docker_real_backend_deps_evidence.md`.
- Adapter structural validation: `c1ab4da fix: validate exported adapter artifacts`, `artifacts/review/export_adapter_validation_evidence.md`.
- Adapter lineage validation: `f8256ad fix: verify exported adapter lineage`, `artifacts/review/export_adapter_lineage_evidence.md`.
- Exported adapter-load guard: `8b44eeb test: guard exported adapter loading`, `artifacts/review/exported_adapter_load_guard_evidence.md`.
- M1 smoke recertification: `9f86de1 docs: record m1 smoke recertification`, `artifacts/review/m1_smoke_recertification_evidence.md`.

## Current Blocking P1 Theme

- Real trained CUDA `lora_adapter` no-fake Docker endpoint evidence is missing.
  Existing endpoint-path evidence used fixture adapter files with
  `MIB_RUNTIME_ALLOW_FAKE_BACKEND=1`, which is not RC GO evidence.

## Status Legend

- `GO`: no P0/P1 blocker remains for the discipline's M6 evidence scope.
- `NO_GO`: at least one P0/P1 blocker remains.
- `NOT_GO`: RC cannot be approved because release candidate rules require all
  agents GO without WAIVED.

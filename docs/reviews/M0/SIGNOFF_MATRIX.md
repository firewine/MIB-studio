# M0 Sign-Off Matrix

| Milestone | FE | DB | BE/API | LLM/Training | Eval/QC | Security | Arch/Code | DevEx | CTO | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| M0 | GO | GO | GO | GO | GO | GO | GO | GO | GO | GO |

## Validation Evidence

- Markdown relative links: PASS, 23 markdown files checked.
- Canonical SQLite schema: PASS, 19 tables and 60 total SQLite indexes execute in SQLite; 27 indexes are explicit MIB-defined indexes.
- JSON artifacts: PASS, 12 JSON files parse (`schemas/*.json`, `.vscode/*.json`, `package.json`).
- Fixture JSONL: PASS, `router_20.jsonl` and `gold_eval.finance.v1.jsonl` parse with 20 rows each.
- Requirements exact-pin policy: PASS; package lines are exact `==` pins and resolver directive lines are allowed.
- Model catalog scaffold verification: PASS with `--allow-day0-placeholders`.
- Model catalog strict verification: PASS; `google/gemma-2b-it` and `microsoft/Phi-3.5-mini-instruct` both have pinned HF commit SHA, file SHA256/size metadata, and required weight shards.
- Model catalog strict report: PASS, `catalog_sha256=5d77b1acef66ca73afcef6e8b772be91b10001d5b5275b62fe67e0fd64dffab1`, `errors=[]`.
- PyYAML-free Day-0 model catalog fallback parser: PASS; `python3.11` bootstrap verify-only can parse the filled strict catalog without installed requirements.
- Strict verifier placeholder enforcement: PASS; strict mode rejects `M1_DAY0_FILL` anywhere in `presets/model_catalog.yaml`.
- Day-0 bootstrap: PASS for `cuda` and `mlx` scaffold verify-only profiles; local toolchain mismatches are recorded non-strictly in `artifacts/review/toolchain_report.json` as allowed by scaffold verify-only mode.
- Profile-specific pip-audit wiring: PASS; GitHub security workflow runs CUDA and MLX audits with installed `pip-audit`, while local `--verify-only --skip-install` writes an explicit skip artifact when `pip-audit` is unavailable.
- OpenAPI/generated DTO focused re-review: GO; 48/48 operationIds are represented in `apps/desktop/src/lib/generated.ts`.
- OpenAPI JSON parse: PASS after DTO/query/retry parity patch.
- M6 export contract scope: PASS for M0; actual adapter inference remains M6 acceptance, not M0 evidence.
- M6 export contract re-review: GO_EXPORT_CONTRACT; base-model external cache, NativeRunResponse, MLX adapter shape, and M0/M6 scope split are locked.
- File-size/god-file budget: PASS, no hard-limit violations.
- Import boundary report: PASS, no backend or frontend layer violations.
- Export secret scan self-test: PASS.

## Open P1 Themes

- None.

## Status Legend

- `GO`: no P0/P1 blocker remains for the discipline's M0 document/scaffold contract.

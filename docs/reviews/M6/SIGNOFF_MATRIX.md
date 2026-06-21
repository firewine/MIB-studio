# M6 Sign-Off Matrix

| Milestone | FE | DB | BE/API | LLM/Training | Eval/QC | Security | Arch/Code | DevEx | CTO | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| M6 Export / v0 RC | NO_GO | GO | GO | GO | GO | NO_GO | GO | NO_GO | NO_GO | NOT_GO |

## Validation Evidence

- M6-001 zip export implementation: `31971d7 feat: implement m6 zip export`.
- M6-002 docker export implementation: `b6873f5 feat: implement m6 docker export`.
- Zip export and runtime tests: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export -q` passed with 9 tests.
- Dockerfile security test: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest packages/agent-runtime/tests/test_docker_export_security.py -q` passed.
- Export secret scan self-test: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/scan_export_artifact.py --self-test` passed.
- Import boundary report: `artifacts/review/import_boundary_report.json`.
- File-size report: `artifacts/review/file_size_report.json`.
- Model manifest verification: `artifacts/security/model_manifest_verification.json`.

## Blocking P1 Themes

- FE v6 mockup implementation and FE RC evidence are not complete.
- Real digest-pinned Docker image build/save/run smoke evidence is not complete.

## Status Legend

- `GO`: no P0/P1 blocker remains for the discipline's M6 evidence scope.
- `NO_GO`: at least one P0/P1 blocker remains.
- `NOT_GO`: RC cannot be approved because release candidate rules require all agents GO without WAIVED.

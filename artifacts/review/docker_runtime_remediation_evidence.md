# Docker Runtime Remediation Evidence

Date: 2026-06-22
Gate: `mib-studio-docker-runtime-evidence-remediation`
Decision: `PARTIAL_GO_FOR_REMEDIATION`

## Scope

This evidence records the focused remediation after the real Docker evidence run
found two product blockers:

- the exported image could not import `agents.run`
- the export scanner treated a saved Docker image tar `manifest.json` as the MIB
  export manifest object

This evidence does not mark M6-RC as GO. Success endpoint smoke remains blocked
until the strict external model cache is provided.

## Code Changes Verified

- `packages/agent-runtime/templates/docker/Dockerfile.cuda` now sets
  `PYTHONPATH=/app/runtime`, making `python -m uvicorn agents.run:app`
  importable from the existing `/app` working directory.
- `scripts/scan_export_artifact.py` now treats Docker image tar
  `manifest.json` lists as Docker image manifests and validates config/layer
  entries separately from the MIB export manifest schema.
- `tests/export/test_docker_export_security.py` now validates context tar
  contents in default mode and Docker image tar contents in real-build mode.
- `apps/desktop/src/main.mjs` restores the exact `Route contract` smoke text
  expected by `scripts/bootstrap_dev.sh --phase m1-smoke --skip-install`.

## Real Docker Build And Save

Command:

```text
MIB_DOCKER_EXPORT_REAL_BUILD=1
MIB_DOCKER_BASE_IMAGE_WITH_DIGEST=getbeta-backend@sha256:95792b6d22c23bd9b95e91b1e53365ebaa31b12847a242fdac63e8f4434034f1
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export/test_docker_export_security.py -q
```

Result:

- Status: passed
- Export image: `mib-export-71aff545aa454ed096e3c29c59e6b862:latest`
- Image id/digest: `sha256:e2f277654c63252103f57f82c316170a8bf0bea53369aab2b7b2c2f1715d653a`
- Image size: `300860909` bytes
- Saved image tar path:
  `/tmp/pytest-of-firewine/pytest-187/test_docker_export_worker_writ0/.mib-home/projects/b61e65e451eb42b4bfb21d8a81b3c2a7/exports/71aff545aa454ed096e3c29c59e6b862/eval_runner_project_v1-docker-context.tar`
- Saved image tar sha256:
  `85177428100113153e0073414627663a593c3a3561feeffe642e3a6b8d12931e`
- Saved image tar size: `287M`
- Tar shape: OCI/Docker image tar with `manifest.json`, `index.json`,
  `oci-layout`, and `blobs/sha256/*` layer/config entries.

The same command failed inside the default sandbox with Docker socket permission
denied and passed when rerun with Docker daemon access.

## Image Tar Scan

Command:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/scan_export_artifact.py \
  --artifact <saved-image-tar> \
  --sbom <evidence/sbom.cdx.json> \
  --cve-report <evidence/cve_report.json> \
  --require-docker-evidence
```

Result:

```text
export artifact secret scan OK
```

`evidence/cve_report.json` recorded:

```json
{"artifact_sha256":"85177428100113153e0073414627663a593c3a3561feeffe642e3a6b8d12931e","findings":[],"real_build":true,"schema_version":"mib_cve_report.v1"}
```

## Container Runtime Check

Command shape:

```text
docker run -d --name mib-docker-evidence-71aff \
  -p 127.0.0.1:18081:8000 \
  -v /tmp/mib-docker-evidence/model_cache:/models:ro \
  -e MIB_MODEL_CACHE_DIR=/models \
  -e MIB_RUNTIME_BEARER_TOKEN=<redacted-32-char-test-token> \
  mib-export-71aff545aa454ed096e3c29c59e6b862:latest
```

Observed:

- Container id: `d625a60a0edf37a9d08e5d5883b1b0913b44f0b5e353fd4837452fc3c98a91c5`
- Status during check: `Up ... (health: starting)`
- Port binding: `127.0.0.1:18081->8000/tcp`
- `docker exec mib-docker-evidence-71aff python -c "import agents.run; print('agents.run import ok')"` returned `agents.run import ok`.
- Uvicorn started and bound `0.0.0.0:8000`.
- `GET /healthz` returned HTTP 500.
- Runtime log root cause: `RuntimeError: MODEL_CACHE_MISSING: config.json`.
- Temporary evidence container was removed with `docker rm -f mib-docker-evidence-71aff`.

Interpretation:

- The previous `ModuleNotFoundError: No module named 'agents'` blocker is fixed.
- The runtime now reaches strict model cache validation.
- Endpoint success transcripts for `/healthz`, `/agents/{agent_id}/run`, and
  `/v1/chat/completions` remain blocked until the required Gemma cache is
  present under the read-only `MIB_MODEL_CACHE_DIR` mount.

## Verification Commands

Passed:

- `python3 -m json.tool .codex/tasks/current.json`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest packages/agent-runtime/tests/test_docker_export_security.py -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export/test_docker_export_security.py -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/scan_export_artifact.py --self-test`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/check_file_size.py --config rules/code_shape.json --json-output artifacts/review/file_size_report.json --fail-on-hard-limit`
- `COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install`
- `MIB_DOCKER_EXPORT_REAL_BUILD=1 MIB_DOCKER_BASE_IMAGE_WITH_DIGEST=getbeta-backend@sha256:95792b6d22c23bd9b95e91b1e53365ebaa31b12847a242fdac63e8f4434034f1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export/test_docker_export_security.py -q` with Docker daemon access
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/scan_export_artifact.py --artifact <saved-image-tar> --sbom <sbom> --cve-report <cve-report> --require-docker-evidence`

Known remaining blocker:

- strict external model cache is absent, so successful runtime endpoint
  transcripts cannot be collected yet.

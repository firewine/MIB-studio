# Phi Strict Cache Runtime Evidence

Date: 2026-06-22
Gate: `mib-studio-phi-strict-cache-runtime-evidence`
Decision: `PARTIAL_GO_ENDPOINT_PATH_WITH_FIXTURE_ADAPTER`

## Scope

This evidence tested the second locked v0 base model,
`microsoft/Phi-3.5-mini-instruct`, after Gemma endpoint evidence was blocked by
gated unauthenticated access.

No product code was changed. Phi model files were materialized outside the repo
under `/tmp/mib-strict-model-cache-phi`. Base-model weights were not committed,
bundled into the exported image, or copied into any repo path.

Important limitation:

- Endpoint success below used `MIB_RUNTIME_ALLOW_FAKE_BACKEND=1` because the
  test fixture AgentPackage contains a fixture adapter file, not a real trained
  PEFT adapter.
- This proves strict model cache validation, Docker image startup, auth,
  native endpoint wiring, OpenAI-compatible endpoint wiring, and verifier path.
- It does not prove real trained adapter inference, so this evidence does not
  make M6-RC GO by itself.

## Strict Catalog And Access

Catalog verification:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/verify_model_catalog.py --catalog presets/model_catalog.yaml --no-download --json-output artifacts/security/model_manifest_strict_report.json
```

Result:

```json
{"catalog_sha256":"5d77b1acef66ca73afcef6e8b772be91b10001d5b5275b62fe67e0fd64dffab1","errors":[],"model_count":2,"no_download":true}
```

Phi pinned config HEAD request returned HTTP 200 with
`x-repo-commit: 2fe192450127e6a83f7441aef6e3ca586c338b77`.

Required cache subdir:

```text
microsoft__Phi-3.5-mini-instruct@2fe192450127e6a83f7441aef6e3ca586c338b77
```

Required files:

| Path | Size bytes | SHA256 |
| --- | ---: | --- |
| `config.json` | 3451 | `224de4f6a15b9d2a89695ec04b7f7ab2dd93a008a506979925e5a88cb5804974` |
| `tokenizer.json` | 1844408 | `9e2ae3d66819f163cdcfedba5078f3a3af8118c2712491ed60912f77886bda6f` |
| `tokenizer_config.json` | 3984 | `92a6e3f894075fda19f47d8755c6ce65b2a974716307d13ae5d79196011ebb44` |
| `model-00001-of-00002.safetensors` | 4972489328 | `c5214cdb995ed3dd716add8d9efbfe016b76bb2f1c4c1e6c1c6a95497d7a8837` |
| `model-00002-of-00002.safetensors` | 2669692552 | `41246eed2b75b66526339c5d32d6f7acdefe0bd24180f97c74303f4656877344` |

## Cache Materialization

Command:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -c '<ensure_model microsoft/Phi-3.5-mini-instruct cuda runtime_evidence>'
```

Output:

```json
{"cache_dir":"/tmp/mib-strict-model-cache-phi/model_cache/microsoft__Phi-3.5-mini-instruct@2fe192450127e6a83f7441aef6e3ca586c338b77","downloaded_files":["config.json","tokenizer.json","tokenizer_config.json","model-00001-of-00002.safetensors","model-00002-of-00002.safetensors"],"required_files":["config.json","tokenizer.json","tokenizer_config.json","model-00001-of-00002.safetensors","model-00002-of-00002.safetensors"],"status":"ok"}
```

Offline cache-hit verification:

```json
{"cache_dir":"/tmp/mib-strict-model-cache-phi/model_cache/microsoft__Phi-3.5-mini-instruct@2fe192450127e6a83f7441aef6e3ca586c338b77","downloaded_files":[],"required_files":["config.json","tokenizer.json","tokenizer_config.json","model-00001-of-00002.safetensors","model-00002-of-00002.safetensors"],"status":"ok"}
```

## Phi Docker Export

A temporary product-path fixture package was adjusted in a temp DB to use
`microsoft/Phi-3.5-mini-instruct`, then exported through
`run_docker_export_job` with:

```text
MIB_DOCKER_EXPORT_REAL_BUILD=1
MIB_DOCKER_BASE_IMAGE_WITH_DIGEST=getbeta-backend@sha256:95792b6d22c23bd9b95e91b1e53365ebaa31b12847a242fdac63e8f4434034f1
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python /tmp/mib_phi_docker_export_evidence.py
```

Result:

- Image: `mib-export-989c1bbe5246469a8a9839cf4c5340ef:latest`
- Image digest: `sha256:08237b312c16d9a19abf4cc9c1495fbc82f00f6be8bfe67e7c00b3350dc97146`
- Export id: `989c1bbe5246469a8a9839cf4c5340ef`
- Agent id: `eval_runner_project.v1`
- Artifact sha256: `aa4fd63ac9a12e4960779f4a878f3617614755e3dd58d8ec85318f9d0dcabd03`
- Manifest sha256: `ba2bd6667ac5aa04e0f5227427cda21626b4258bbf2ec2d1a97151ec34a6a28c`
- Artifact path:
  `/tmp/mib-phi-docker-export-_vgqfd4g/.mib-home/projects/f057829908224162825bea3e144201f0/exports/989c1bbe5246469a8a9839cf4c5340ef/eval_runner_project_v1-docker-context.tar`
- Manifest path:
  `/tmp/mib-phi-docker-export-_vgqfd4g/.mib-home/projects/f057829908224162825bea3e144201f0/exports/989c1bbe5246469a8a9839cf4c5340ef/docker_context/manifest.json`

The manifest records:

```json
{"base_model":{"id":"microsoft/Phi-3.5-mini-instruct","cache_subdir":"microsoft__Phi-3.5-mini-instruct@2fe192450127e6a83f7441aef6e3ca586c338b77"}}
```

Secret/SBOM/CVE scan:

```text
export artifact secret scan OK
```

`cve_report.json` recorded:

```json
{"artifact_sha256":"aa4fd63ac9a12e4960779f4a878f3617614755e3dd58d8ec85318f9d0dcabd03","findings":[],"real_build":true,"schema_version":"mib_cve_report.v1"}
```

## Docker Runtime Endpoint Evidence

Run command shape:

```text
docker run -d --name mib-phi-evidence-989c \
  -p 127.0.0.1:18082:8000 \
  -v /tmp/mib-strict-model-cache-phi/model_cache:/models:ro \
  -e MIB_MODEL_CACHE_DIR=/models \
  -e MIB_RUNTIME_ALLOW_FAKE_BACKEND=1 \
  -e MIB_RUNTIME_BEARER_TOKEN=<redacted-32-char-test-token> \
  mib-export-989c1bbe5246469a8a9839cf4c5340ef:latest
```

Read-only mount verification:

```json
[{"Type":"bind","Source":"/tmp/mib-strict-model-cache-phi/model_cache","Destination":"/models","Mode":"ro","RW":false,"Propagation":"rprivate"}]
```

Health transcript:

```text
HTTP/1.1 200 OK

{"ok":true}
```

Native endpoint transcript:

```text
HTTP/1.1 200 OK

{"output":{"route":"finance_income","task_type":"provide_advice","requires_calculation":true,"requires_human_review":false,"confidence":0.94},"verifier_status":"PASS","verifier_errors":[],"fallback_required":false,"fallback_used":false}
```

OpenAI-compatible endpoint transcript:

```text
HTTP/1.1 200 OK

{"id":"mib-exported-runtime","object":"chat.completion","choices":[{"index":0,"message":{"role":"assistant","content":"{\"confidence\": 0.94, \"requires_calculation\": true, \"requires_human_review\": false, \"route\": \"finance_income\", \"task_type\": \"provide_advice\"}"},"finish_reason":"stop"}]}
```

Container logs:

```text
Uvicorn running on http://0.0.0.0:8000
GET /healthz HTTP/1.1" 200 OK
POST /agents/eval_runner_project.v1/run HTTP/1.1" 200 OK
POST /v1/chat/completions HTTP/1.1" 200 OK
```

Temporary container cleanup:

```text
docker rm -f mib-phi-evidence-989c
```

## Remaining Work Before M6-RC GO

This gate proves a strict cache and endpoint path can pass with the accessible
locked Phi model. It does not close M6-RC because the endpoint run used the
fixture adapter path with `MIB_RUNTIME_ALLOW_FAKE_BACKEND=1`.

Next required gate:

- produce or identify a real trained CUDA `lora_adapter` AgentPackage for a
  locked v0 base model, or explicitly define the release acceptance policy for
  fixture-adapter Docker endpoint evidence
- rerun Docker endpoint transcripts without fake backend if real adapter
  evidence is required
- only then rerun M6-RC sign-off

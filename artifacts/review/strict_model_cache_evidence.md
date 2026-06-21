# Strict Model Cache Evidence

Date: 2026-06-22
Gate: `mib-studio-strict-model-cache-runtime-evidence`
Decision: `NOT_GO_MODEL_CACHE_ACCESS_BLOCKED`

## Scope

This evidence gate checked whether the exported Docker runtime can proceed from
the previous import-path remediation to successful endpoint transcripts with a
real strict external Gemma model cache.

No product code was changed. No model weights were added to git, the export
artifact, or the Docker image. No fake cache files were created.

## Strict Catalog Requirement

Catalog verification command:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/verify_model_catalog.py --catalog presets/model_catalog.yaml --no-download --json-output artifacts/security/model_manifest_strict_report.json
```

Result:

```json
{"catalog_sha256":"5d77b1acef66ca73afcef6e8b772be91b10001d5b5275b62fe67e0fd64dffab1","errors":[],"model_count":2,"no_download":true}
```

Required Gemma cache subdir:

```text
google__gemma-2b-it@96988410cbdaeb8d5093d1ebdc5a8fb563e02bad
```

Required files:

| Path | Size bytes | SHA256 |
| --- | ---: | --- |
| `config.json` | 627 | `4d8c4b061fad0e3f51df4f8501873531a4d9fc5b70a7b09e2231d18a12ad7d27` |
| `tokenizer.json` | 17518497 | `c15eb04bc5ad609fb26533e8525302c5640a945e5f67f65b7c849900acda7d99` |
| `tokenizer_config.json` | 34173 | `ae20b2c4b2b35bdcfaf096a71bab88b836b8e9ef2b8bf976ab54705f4e884b5b` |
| `model-00001-of-00002.safetensors` | 4945242264 | `561656f892a2a1ca0837ca529c5ce820a72b40f4f563b1cd0a1acc0b3899c30c` |
| `model-00002-of-00002.safetensors` | 67121608 | `20fe2ee66bf1361241a6c522091a5e0328fc6c1703f93734889fa381fcf8760c` |

## Local Cache Discovery

Searched:

- `/home/firewine/.cache/huggingface`
- `/home/firewine/MIB-studio`
- `/tmp`

Findings:

- `/home/firewine/.cache/huggingface` does not exist.
- No directory named `google__gemma-2b-it@96988410cbdaeb8d5093d1ebdc5a8fb563e02bad` was found.
- Only test fixture caches with subdir
  `google__gemma-2b-it@0000000000000000000000000000000000000000`
  were found under `/tmp`; these are 7-byte fake fixture files and are not
  valid strict cache evidence.
- `/tmp/mib-strict-model-cache` contains only an empty lock file created by the
  offline cache check.

Disk capacity is sufficient for the required Gemma files:

```text
/tmp: 1.7T available
/home/firewine/MIB-studio: 1.7T available
```

## Credential And Access Check

Credential presence check, without printing secret values:

```text
HF_TOKEN=unset
HUGGING_FACE_HUB_TOKEN=unset
HUGGINGFACE_TOKEN=unset
hf_cache_token_file=absent
hf_legacy_token_file=absent
netrc=absent
```

Sandbox network check:

```text
curl: (6) Could not resolve host: huggingface.co
```

Rerun with network access, using a HEAD request only:

```text
curl -sS -I -L --max-time 30 https://huggingface.co/google/gemma-2b-it/resolve/96988410cbdaeb8d5093d1ebdc5a8fb563e02bad/config.json
```

Observed response:

```text
HTTP/2 401
x-error-code: GatedRepo
x-error-message: Access to model google/gemma-2b-it is restricted. You must have access to it and be authenticated to access it. Please log in.
www-authenticate: Bearer realm="Authentication required", charset="UTF-8"
```

Interpretation:

- The Gemma model repo is gated.
- This environment has no HF token or local HF credential file.
- The runtime evidence cannot honestly proceed to endpoint success until an
  authenticated HF account with accepted Gemma terms is available, or an
  already materialized strict cache is supplied externally.

## Model Cache Service Check

Command:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. MIB_OFFLINE=1 ./.venv/bin/python -c '<ensure_model google/gemma-2b-it cuda runtime_evidence>'
```

Result:

```json
{
  "code": "MODEL_CACHE_MISS_OFFLINE",
  "details": {
    "hf_commit_sha": "96988410cbdaeb8d5093d1ebdc5a8fb563e02bad",
    "missing_files": [
      "config.json",
      "tokenizer.json",
      "tokenizer_config.json",
      "model-00001-of-00002.safetensors",
      "model-00002-of-00002.safetensors"
    ],
    "model_id": "google/gemma-2b-it"
  },
  "message": "Model cache is missing required files while offline mode is enabled.",
  "status": "error"
}
```

## Docker Endpoint Evidence Status

The remediated Docker image is still available locally:

```text
mib-export-71aff545aa454ed096e3c29c59e6b862:latest e2f277654c63 1.3GB
```

Endpoint transcripts were not rerun as success evidence in this gate because the
required strict cache does not exist. The previous remediation evidence already
proved that the container starts, `agents.run` imports, and `/healthz` reaches
strict cache validation before failing with `MODEL_CACHE_MISSING`.

## Required External Action

One of the following is required before the next runtime evidence gate can
produce successful endpoint transcripts:

1. Set `HF_TOKEN`, `HUGGING_FACE_HUB_TOKEN`, or `HUGGINGFACE_TOKEN` for an HF
   account that has accepted the `google/gemma-2b-it` terms, then run the model
   cache service to materialize the strict cache outside the repo.
2. Provide a pre-existing cache root containing:
   `google__gemma-2b-it@96988410cbdaeb8d5093d1ebdc5a8fb563e02bad`
   with all required files matching the strict catalog hashes and sizes.

After that, rerun the exported Docker image with:

```text
-v <cache-root>:/models:ro -e MIB_MODEL_CACHE_DIR=/models
```

and capture successful `/healthz`, `/agents/{agent_id}/run`, and
`/v1/chat/completions` transcripts before reopening M6-RC sign-off.

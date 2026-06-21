# 개발환경 명세 (DEV_ENVIRONMENT_SPEC) — MIB Studio

> 상위: [MIB Studio 개발 계획서 v0.3](../foundation/MIB_Studio_Dev_Plan_v0.3.md)  
> 상태: v0.3 · M0 environment lock  
> 목적: IDE와 로컬 개발 환경을 하나로 고정해, 주니어 개발자가 같은 명령·같은 interpreter·같은 dependency 파일로 개발하도록 만든다.  
> 관련: [IMPLEMENTATION_GUIDE](./IMPLEMENTATION_GUIDE.md) · [ARCHITECTURE](./ARCHITECTURE.md) · [SECURITY_SPEC](./SECURITY_SPEC.md)

---

## 36.0 CTO 결정: venv vs Docker

```text
Decision:
  Daily development = local `.venv`.
  App runtime packaging = bundled/embedded Python 3.11 venv.
  Docker = export artifact build/run verification only.

Not allowed:
  - Docker를 M1~M5 앱 개발 기본 환경으로 삼지 않는다.
  - 시스템 Python site-packages에 의존하지 않는다.
  - Conda를 v0 표준 개발환경으로 쓰지 않는다.
  - requirements 없는 `pip install ...` 수동 설치 절차를 문서화하지 않는다.
```

이유:

```text
- Tauri desktop app은 host OS keychain, localhost daemon, GPU/Metal/CUDA 접근이 필요하다.
- Docker는 macOS Metal/MLX와 Windows/WSL2 CUDA 개발 경로를 한 번에 표준화하지 못한다.
- IDE는 `.venv` interpreter를 가장 안정적으로 인식한다.
- Docker는 M6 export 결과물과 CI smoke 검증에는 필요하지만, 앱 자체 실행 전제는 아니다.
```

## 36.1 필수 개발 도구 버전

M0에서 major/minor line을 잠그고, exact patch는 M1 Day-0 파일에 기록한다.

| 도구 | 기준 |
|---|---|
| Python | 3.11.x only |
| Node.js | 20 LTS |
| pnpm | 9.x via Corepack |
| Rust | stable channel, `rust-toolchain.toml`로 pin |
| Tauri | 2.x |
| SQLite | 3.40+ |
| CUDA path | CUDA 12.1 + NVIDIA driver 535~560, Linux/Windows WSL2 |
| Apple path | macOS 14+, Apple Silicon, MLX/mlx-lm |

Python 3.12는 v0 표준이 아니다. Hardware Doctor가 3.12를 감지하면 "unsupported for development/training"으로 표시한다.

## 36.2 Day-0 환경 파일

M1 착수 전 아래 파일이 실제 repository root에 있어야 한다.

```text
.python-version                 # 3.11.x exact patch
.node-version                   # 20.x exact patch
rust-toolchain.toml             # stable channel exact date/toolchain
requirements.txt                # CUDA/LLaMA-Factory path, exact pins
requirements-mlx.txt            # Apple Silicon/MLX path, exact pins
requirements-dev.txt            # pytest/ruff/mypy/pip-audit/detect-secrets tooling
package.json
pnpm-lock.yaml
.env.example                    # secrets forbidden
.vscode/settings.json
.vscode/extensions.json
.vscode/tasks.json
.vscode/launch.json
scripts/bootstrap_dev.sh
scripts/bootstrap_dev.ps1
```

Nonstandard dependency lock filenames are not used in v0. pip/IDE/보안 도구가 바로 읽을 수 있도록 `requirements*.txt`를 canonical dependency files로 사용한다.

## 36.3 requirements 파일 정책

공통 규칙:

```text
- 모든 package는 exact pin(`==`)을 사용한다.
- range specifier(`>=`, `~=`, `*`)는 금지한다.
- CUDA 전용 package와 MLX 전용 package를 한 파일에 섞지 않는다.
- dev tool은 runtime requirements에 넣지 않고 `requirements-dev.txt`에 둔다.
- `pip-audit`는 profile별 runtime file 하나와 `requirements-dev.txt`만 대상으로 실행한다. CUDA와 MLX runtime files를 한 번에 resolve/audit하지 않는다.
```

파일 책임:

| 파일 | 설치 대상 | 포함 |
|---|---|---|
| `requirements.txt` | NVIDIA/Linux/WSL2 개발자 | FastAPI, SQLAlchemy, Pydantic, torch cu121, transformers, peft, trl, accelerate, bitsandbytes, LLaMA-Factory |
| `requirements-mlx.txt` | macOS Apple Silicon 개발자 | FastAPI, SQLAlchemy, Pydantic, mlx, mlx-lm, transformers, tokenizer/runtime deps |
| `requirements-dev.txt` | 모든 개발자 | pytest, pytest-asyncio, ruff, mypy/pyright support, pip-audit, detect-secrets, jsonschema |

`requirements.txt`와 `requirements-mlx.txt` 둘 다 API/DB/worker 공통 runtime dependency를 포함한다. 둘을 동시에 설치·resolve·audit하지 않는다. CI와 로컬 보안 검사는 profile별로 분리한다:

```text
cuda audit: pip-audit -r requirements.txt -r requirements-dev.txt
mlx audit:  pip-audit -r requirements-mlx.txt -r requirements-dev.txt
```

### 36.3.1 Day-0 requirements templates

아래 템플릿은 M1 Day-0에 repository root 파일로 그대로 생성한다. 보안 audit이나 upstream yanked package 때문에 patch pin을 바꿔야 하면 ADR과 DevEx/Security sign-off가 필요하다. `--extra-index-url`과 주석을 제외한 package line은 모두 `==` exact pin이어야 한다.

`requirements.txt` (CUDA/LLaMA-Factory):

```text
--extra-index-url https://download.pytorch.org/whl/cu121
fastapi==0.115.12
uvicorn==0.34.2
sse-starlette==2.2.1
pydantic==2.10.6
pydantic-settings==2.8.1
SQLAlchemy==2.0.40
alembic==1.15.2
httpx==0.28.1
keyring==25.6.0
orjson==3.10.16
PyYAML==6.0.2
jsonschema==4.23.0
numpy==1.26.4
torch==2.4.1+cu121
torchaudio==2.4.1+cu121
torchvision==0.19.1+cu121
transformers==4.56.2
accelerate==1.11.0
datasets==4.0.0
peft==0.18.0
trl==0.24.0
bitsandbytes==0.49.2
sentencepiece==0.2.0
safetensors==0.4.5
protobuf==5.29.3
tiktoken==0.8.0
llamafactory==0.9.5
```

`requirements-mlx.txt` (Apple Silicon/MLX):

```text
fastapi==0.115.12
uvicorn==0.34.2
sse-starlette==2.2.1
pydantic==2.10.6
pydantic-settings==2.8.1
SQLAlchemy==2.0.40
alembic==1.15.2
httpx==0.28.1
keyring==25.6.0
orjson==3.10.16
PyYAML==6.0.2
jsonschema==4.23.0
numpy==1.26.4
mlx==0.31.2
mlx-lm==0.31.3
transformers==5.0.0
datasets==4.0.0
sentencepiece==0.2.0
protobuf==5.29.3
tqdm==4.67.1
```

`requirements-dev.txt`:

```text
pytest==8.3.5
pytest-asyncio==0.25.3
pytest-cov==6.0.0
ruff==0.11.2
mypy==1.15.0
pyright==1.1.396
pip-audit==2.8.0
detect-secrets==1.5.0
build==1.2.2.post1
jsonschema==4.23.0
sentence-transformers==3.3.1
types-PyYAML==6.0.12.20241230
```

## 36.4 로컬 셋업 명령

NVIDIA/Linux 또는 Windows WSL2:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
corepack enable
corepack pnpm install
# after M1-007 creates src-tauri/vite scaffold:
# corepack pnpm tauri dev
```

macOS Apple Silicon:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-mlx.txt -r requirements-dev.txt
corepack enable
corepack pnpm install
# after M1-007 creates src-tauri/vite scaffold:
# corepack pnpm tauri dev
```

Windows 네이티브는 UI/daemon smoke까지만 허용하고, NVIDIA 학습 개발은 WSL2를 권장 경로로 둔다.

## 36.5 IDE 설정 계약

VS Code Day-0 settings:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "ruff.nativeServer": "on",
  "python.analysis.typeCheckingMode": "basic",
  "typescript.tsdk": "node_modules/typescript/lib",
  "editor.formatOnSave": true
}
```

PyCharm:

```text
- Project interpreter: `<repo>/.venv/bin/python`.
- Mark `services`, `packages`, and `apps/desktop/src` as source roots when needed.
- Do not configure Docker interpreter for M1~M5 app development.
```

macOS/Windows path differences are allowed in IDE metadata and PowerShell bootstrap implementation. Source imports, test selectors, and docs use repo-relative paths; Windows tasks may invoke `.venv\\Scripts\\python.exe`.

VS Code required tasks:

```json
[
  { "label": "bootstrap: scaffold (cuda)", "type": "shell", "command": "scripts/bootstrap_dev.sh --profile cuda --phase scaffold", "windows": { "command": "powershell -ExecutionPolicy Bypass -File scripts/bootstrap_dev.ps1 -Profile cuda -Phase scaffold" } },
  { "label": "bootstrap: scaffold (mlx)", "type": "shell", "command": "scripts/bootstrap_dev.sh --profile mlx --phase scaffold", "windows": { "command": "powershell -ExecutionPolicy Bypass -File scripts/bootstrap_dev.ps1 -Profile mlx -Phase scaffold" } },
  { "label": "bootstrap: m1-smoke (cuda)", "type": "shell", "command": "scripts/bootstrap_dev.sh --profile cuda --phase m1-smoke", "windows": { "command": "powershell -ExecutionPolicy Bypass -File scripts/bootstrap_dev.ps1 -Profile cuda -Phase m1-smoke" } },
  { "label": "bootstrap: m1-smoke (mlx)", "type": "shell", "command": "scripts/bootstrap_dev.sh --profile mlx --phase m1-smoke", "windows": { "command": "powershell -ExecutionPolicy Bypass -File scripts/bootstrap_dev.ps1 -Profile mlx -Phase m1-smoke" } },
  { "label": "api: test", "type": "shell", "command": ". .venv/bin/activate && pytest services packages", "windows": { "command": ".venv\\Scripts\\python -m pytest services packages" } },
  { "label": "ui: test", "type": "shell", "command": "corepack pnpm test" },
  { "label": "tauri: dev", "type": "shell", "command": "corepack pnpm tauri dev", "problemMatcher": [], "detail": "Available after M1-007 creates the Tauri/Vite scaffold." },
  { "label": "security: audit (cuda)", "type": "shell", "command": ". .venv/bin/activate && pip-audit -r requirements.txt -r requirements-dev.txt", "windows": { "command": ".venv\\Scripts\\python -m pip_audit -r requirements.txt -r requirements-dev.txt" } },
  { "label": "security: audit (mlx)", "type": "shell", "command": ". .venv/bin/activate && pip-audit -r requirements-mlx.txt -r requirements-dev.txt", "windows": { "command": ".venv\\Scripts\\python -m pip_audit -r requirements-mlx.txt -r requirements-dev.txt" } }
]
```

VS Code launch configs:

```text
- `API daemon`: run `services/api/app/main.py` with `${workspaceFolder}/.venv/bin/python`.
- `Worker loop`: run `services/worker/worker/main.py` with `${workspaceFolder}/.venv/bin/python`.
- `Tauri dev`: delegates to task `tauri: dev`.
- Windows variants use `${workspaceFolder}\\.venv\\Scripts\\python.exe`.
```

## 36.6 Day-0 bootstrap script contract

`scripts/bootstrap_dev.sh` and `scripts/bootstrap_dev.ps1` must implement the same steps.

Inputs:

```text
--profile cuda | mlx
--phase scaffold | m1-smoke
--skip-install
--verify-only
```

Behavior:

```text
1. Verify Python 3.11, Node from `.node-version`, pnpm 9, Rust from `rust-toolchain.toml`, SQLite 3.40+. In `--phase scaffold --verify-only`, mismatches are recorded in `artifacts/review/toolchain_report.json`; normal bootstrap and `m1-smoke` fail on mismatch.
2. Create `.venv` if missing.
3. Install `requirements-dev.txt` plus exactly one runtime file:
   - cuda → `requirements.txt`
   - mlx  → `requirements-mlx.txt`
4. Run `corepack enable` and `corepack pnpm install`.
5. Verify Day-0 file manifest exists, including `requirements*.txt`, version files, `.env.example`, VS Code files, and bootstrap scripts.
6. Verify requirements exact pins and profile-specific dependency separation.
7. Verify `presets/model_catalog.yaml` in strict mode. Current M0 GO bootstrap/CI rejects every `M1_DAY0_FILL`; `--allow-day0-placeholders` is reserved for local pre-M0 template experiments only and must never be used as PR or M1 evidence.
8. Run markdown link check and SQLite schema extraction check.
9. Run profile-specific security audit only:
   - cuda → `pip-audit -r requirements.txt -r requirements-dev.txt`
   - mlx  → `pip-audit -r requirements-mlx.txt -r requirements-dev.txt`
   In `--verify-only --skip-install`, if `pip-audit` is not installed, write `artifacts/security/pip_audit_{profile}.json` with `status=skipped`; this proves wiring only and does not replace CI/non-skip audit evidence.
10. If `--phase scaffold`, stop after generated artifact/security/schema checks.
11. Always write machine-readable local review artifacts:
    - `artifacts/review/toolchain_report.json`
    - `artifacts/security/model_manifest_verification.json`
    - `artifacts/security/pip_audit_{profile}.json`
    - `artifacts/review/file_size_report.json`
    - `artifacts/review/import_boundary_report.json`
12. If `--phase m1-smoke`, require the M1 API/security scaffold files and `tests/smoke/test_m1_smoke.py`, then run the smoke test. Missing M1 smoke files exits with code 5. This phase is expected only after M1-001/M1-002/M1-004/M1-006 are implemented.
```

Exit codes:

```text
0 = success
1 = missing tool/version mismatch
2 = dependency install failure
3 = generated artifact drift
4 = security audit failure
5 = M1 smoke failure
```

## 36.7 환경 변수와 secrets

`.env.example` may contain:

```text
MIB_HOME=.mib-home
MIB_LOG_LEVEL=info
MIB_DEV_AUTH=bootstrap
HF_TOKEN=                       # optional placeholder only; real value goes in ignored .env
```

`.env` is local-only and ignored by Git. It may contain `HF_TOKEN` (or `HUGGING_FACE_HUB_TOKEN`/`HUGGINGFACE_TOKEN`) only for Day-0 gated Hugging Face model catalog fill. The app runtime must not read teacher/API/provider credentials from `.env`.

금지:

```text
- API key, app bearer token, teacher credential, production secret을 `.env`에 넣지 않는다.
- Real token values must never be written to `.env.example`, docs, logs, Git history, issue comments, or chat.
- Production bearer token을 파일에 저장하지 않는다.
- IDE run configuration에 secret을 저장하지 않는다.
```

## 36.8 Docker 사용 범위

Docker allowed:

```text
- M6 Docker export artifact build.
- Exported `/agents/{agent_id}/run` smoke test.
- Optional CI job that runs exported image.
```

Docker not allowed:

```text
- M1~M5 기본 개발환경.
- Local daemon/worker 실행 전제.
- Credential/keychain/e2e UX 테스트의 기본 runner.
```

Docker가 없어도 M1~M5 개발과 zip export는 성공해야 한다.

## 36.9 DevEx Acceptance Tests

Day-0 scaffold verification은 M1 API 구현 전에도 아래를 통과해야 한다.

```text
test_requirements_files_exist
test_requirements_exact_pins_no_ranges
test_no_nonstandard_dependency_lock_references
test_python_version_is_311
test_vscode_interpreter_points_to_venv
test_vscode_tasks_have_posix_and_windows_commands
test_env_example_has_no_secret_values
test_bootstrap_scaffold_does_not_call_healthz_or_presets_or_hardware_scan
test_profile_specific_audit_commands_do_not_mix_cuda_and_mlx
```

Post M1-001/M1-002/M1-004/M1-006 smoke는 M1 구현 후에만 아래를 통과해야 한다.

```text
test_m1_smoke_file_exists_and_bootstrap_runs_it
test_docker_not_required_for_post_m1_smoke
test_healthz_presets_hardware_scan_smoke
```

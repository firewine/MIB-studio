#!/usr/bin/env bash
set -euo pipefail

PROFILE="cuda"
PHASE="scaffold"
SKIP_INSTALL="0"
VERIFY_ONLY="0"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --phase) PHASE="$2"; shift 2 ;;
    --skip-install) SKIP_INSTALL="1"; shift ;;
    --verify-only) VERIFY_ONLY="1"; shift ;;
    *) echo "unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [ "$PROFILE" != "cuda" ] && [ "$PROFILE" != "mlx" ]; then
  echo "--profile must be cuda or mlx" >&2
  exit 1
fi

if [ "$PHASE" != "scaffold" ] && [ "$PHASE" != "m1-smoke" ]; then
  echo "--phase must be scaffold or m1-smoke" >&2
  exit 1
fi

run_pip_audit() {
  mode="${1:-required}"
  mkdir -p artifacts/security
  report="artifacts/security/pip_audit_${PROFILE}.json"
  if [ "$PROFILE" = "cuda" ]; then
    audit_requirements=(requirements.txt requirements-dev.txt)
  else
    audit_requirements=(requirements-mlx.txt requirements-dev.txt)
  fi

  audit_args=()
  for req in "${audit_requirements[@]}"; do
    audit_args+=("-r" "$req")
  done
  audit_ignore_args=()
  exceptions_report="artifacts/security/pip_audit_${PROFILE}_exceptions.json"
  if [ "$PROFILE" = "cuda" ]; then
    # LLaMA-Factory 0.9.5 currently constrains gradio<=5.50.0.
    # That prevents installing the patched Gradio/Pillow/Starlette line together
    # with the SSOT-required training stack, so only those upstream-blocked
    # advisories are ignored and recorded explicitly.
    audit_exception_ids=(
      "PYSEC-2026-63"
      "PYSEC-2026-66"
      "PYSEC-2026-65"
      "PYSEC-2026-64"
      "PYSEC-2026-211"
      "PYSEC-2026-165"
      "GHSA-cfh3-3jmp-rvhc"
      "GHSA-whj4-6x5x-4v2j"
      "GHSA-5xmw-vc9v-4wf2"
      "GHSA-r73j-pqj5-w3x7"
      "GHSA-pwv6-vv43-88gr"
      "PYSEC-2026-161"
      "GHSA-wqp7-x3pw-xc5r"
      "GHSA-x746-7m8f-x49c"
      "GHSA-82w8-qh3p-5jfq"
      "GHSA-jp82-jpqv-5vv3"
    )
    for vuln_id in "${audit_exception_ids[@]}"; do
      audit_ignore_args+=("--ignore-vuln" "$vuln_id")
    done
    cat > "$exceptions_report" <<'JSON'
{
  "profile": "cuda",
  "status": "accepted_upstream_constraint",
  "reason": "llamafactory==0.9.5 requires gradio<=5.50.0, which prevents using patched Gradio 6.x, Pillow 12.x, and Starlette 1.x together with the current SSOT-required CUDA training stack.",
  "owner": "DevEx/Security",
  "review_required_when": "LLaMA-Factory releases a version compatible with Gradio 6.x or the SSOT replaces the training wrapper.",
  "ignored_vulnerability_ids": [
    "PYSEC-2026-63",
    "PYSEC-2026-66",
    "PYSEC-2026-65",
    "PYSEC-2026-64",
    "PYSEC-2026-211",
    "PYSEC-2026-165",
    "GHSA-cfh3-3jmp-rvhc",
    "GHSA-whj4-6x5x-4v2j",
    "GHSA-5xmw-vc9v-4wf2",
    "GHSA-r73j-pqj5-w3x7",
    "GHSA-pwv6-vv43-88gr",
    "PYSEC-2026-161",
    "GHSA-wqp7-x3pw-xc5r",
    "GHSA-x746-7m8f-x49c",
    "GHSA-82w8-qh3p-5jfq",
    "GHSA-jp82-jpqv-5vv3"
  ]
}
JSON
  else
    cat > "$exceptions_report" <<JSON
{"profile":"$PROFILE","status":"none","ignored_vulnerability_ids":[]}
JSON
  fi

  if "$PYTHON_BIN" -m pip_audit --version >/dev/null 2>&1; then
    if "$PYTHON_BIN" -m pip_audit "${audit_args[@]}" "${audit_ignore_args[@]}" --format json > "$report"; then
      echo "pip-audit ${PROFILE} OK"
      return 0
    fi
    cat "$report" >&2 || true
    exit 4
  fi

  if command -v pip-audit >/dev/null 2>&1; then
    if pip-audit "${audit_args[@]}" "${audit_ignore_args[@]}" --format json > "$report"; then
      echo "pip-audit ${PROFILE} OK"
      return 0
    fi
    cat "$report" >&2 || true
    exit 4
  fi

  if [ "$mode" = "allow-skip" ]; then
    cat > "$report" <<JSON
{"profile":"$PROFILE","status":"skipped","reason":"pip-audit is not installed in this --verify-only/--skip-install environment","required_files":["${audit_requirements[0]}","${audit_requirements[1]}"]}
JSON
    echo "pip-audit ${PROFILE} skipped; see $report"
    return 0
  fi

  echo "pip-audit is required for profile ${PROFILE}; install requirements-dev.txt or run without --skip-install" >&2
  exit 4
}

TOOLCHAIN_STRICT="1"
if [ "$VERIFY_ONLY" = "1" ] && [ "$PHASE" = "scaffold" ]; then
  TOOLCHAIN_STRICT="0"
fi

for cmd in "$PYTHON_BIN"; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "missing required tool: $cmd" >&2; exit 1; }
done

"$PYTHON_BIN" - <<PY
from pathlib import Path
import json
import re
import sqlite3
import subprocess
import sys

strict = ${TOOLCHAIN_STRICT}
expected_python = Path(".python-version").read_text().strip()
expected_node = Path(".node-version").read_text().strip()
expected_rust = re.search(r'channel\\s*=\\s*"([^"]+)"', Path("rust-toolchain.toml").read_text()).group(1)

def run(cmd):
    try:
        result = subprocess.run(cmd, check=False, text=True, capture_output=True, timeout=20)
        return {"text": result.stdout.strip() or result.stderr.strip(), "ok": result.returncode == 0}
    except Exception as exc:
        return {"text": f"ERROR: {exc}", "ok": False}

python_version = ".".join(map(str, sys.version_info[:3]))
node_result = run(["node", "--version"])
pnpm_result = run(["corepack", "pnpm", "--version"])
rust_result = run(["rustc", "--version"])
node_version = node_result["text"].removeprefix("v")
pnpm_version = pnpm_result["text"]
rust_version_raw = rust_result["text"]
sqlite_version = sqlite3.sqlite_version
checks = {
    "python": python_version.startswith("3.11."),
    "node": node_result["ok"] and node_version == expected_node,
    "pnpm": pnpm_result["ok"] and pnpm_version.startswith("9."),
    "rust": rust_result["ok"] and expected_rust in rust_version_raw,
    "sqlite": tuple(map(int, sqlite_version.split(".")[:2])) >= (3, 40),
}
report = {
    "expected": {"python": expected_python, "node": expected_node, "pnpm_major": "9", "rust": expected_rust, "sqlite_min": "3.40"},
    "actual": {"python": python_version, "node": node_version, "pnpm": pnpm_version, "rust": rust_version_raw, "sqlite": sqlite_version},
    "checks": checks,
    "strict": bool(strict),
}
Path("artifacts/review").mkdir(parents=True, exist_ok=True)
Path("artifacts/review/toolchain_report.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\\n")
if strict and not all(checks.values()):
    raise SystemExit("toolchain version mismatch; see artifacts/review/toolchain_report.json")
if not strict and not all(checks.values()):
    print("toolchain version mismatch recorded in artifacts/review/toolchain_report.json")
else:
    print("toolchain versions OK")
PY

required_files=(
  ".python-version"
  ".node-version"
  "rust-toolchain.toml"
  "requirements.txt"
  "requirements-mlx.txt"
  "requirements-dev.txt"
  "package.json"
  "pnpm-lock.yaml"
  ".env.example"
  ".vscode/settings.json"
  ".vscode/extensions.json"
  ".vscode/tasks.json"
  ".vscode/launch.json"
  ".github/workflows/security.yml"
  "scripts/bootstrap_dev.sh"
  "scripts/bootstrap_dev.ps1"
  "scripts/verify_model_catalog.py"
  "scripts/fill_model_catalog.py"
  "scripts/export_openapi.py"
  "scripts/check_file_size.py"
  "scripts/check_import_boundaries.py"
  "scripts/scan_export_artifact.py"
  "scripts/verify_pii_holdout.py"
  "presets/model_catalog.yaml"
  "presets/router.basic.v1.yaml"
  "prompts/router.prompt_only.v1.txt"
  "rules/router.routing_rules.v1.yaml"
  "rules/code_shape.json"
  "schemas/router_input.schema.json"
  "schemas/router_output.schema.json"
  "schemas/routing_rules.schema.json"
  "schemas/agent_contract.schema.json"
  "schemas/benchmark_report.schema.json"
  "schemas/export_manifest.schema.json"
  "schemas/pii_holdout.schema.json"
  "schemas/openapi.json"
  "apps/desktop/src/lib/generated.ts"
  "packages/agent-runtime/README.md"
  "packages/agent-runtime/templates/zip_runtime/agents/run.py"
  "packages/agent-runtime/templates/zip_runtime/agents/verifier.py"
  "packages/agent-runtime/templates/zip_runtime/agents/fallback.py"
  "packages/agent-runtime/templates/zip_runtime/agents/security.py"
  "packages/agent-runtime/templates/zip_runtime/requirements-runtime.txt"
  "packages/agent-runtime/templates/docker/Dockerfile.cuda"
  "packages/agent-runtime/loaders/transformers_lora.py"
  "packages/agent-runtime/loaders/mlx_lora.py"
  "services/shared/db/migrations/env.py"
  "services/shared/db/migrations/versions/0001_initial.py"
  "examples/fixtures/router_20.jsonl"
  "examples/fixtures/gold_eval.finance.v1.jsonl"
  "examples/fixtures/llamafactory_config.golden.yaml"
  "examples/fixtures/mlx_config.golden.json"
  "examples/security/pii_holdout.v1.jsonl"
)

for file in "${required_files[@]}"; do
  [ -f "$file" ] || { echo "missing Day-0 file: $file" >&2; exit 1; }
done

"$PYTHON_BIN" - <<'PY'
from pathlib import Path
import json
for name in ["requirements.txt", "requirements-mlx.txt", "requirements-dev.txt"]:
    for i, line in enumerate(Path(name).read_text().splitlines(), 1):
        value = line.strip()
        if not value or value.startswith("#") or value.startswith("--"):
            continue
        if "==" not in value or any(op in value for op in [">=", "<=", "~=", "!=", ">", "<", "*"]):
            raise SystemExit(f"{name}:{i}: dependency must use exact == pin: {line}")
print("requirements exact pins OK")
for path in Path("schemas").glob("*.json"):
    json.loads(path.read_text())
json.loads(Path("package.json").read_text())
json.loads(Path(".vscode/tasks.json").read_text())
print("json artifacts OK")
for name in ["examples/fixtures/router_20.jsonl", "examples/fixtures/gold_eval.finance.v1.jsonl"]:
    count = 0
    for line in Path(name).read_text().splitlines():
        row = json.loads(line)
        if not {"instruction", "input", "output"} <= set(row):
            raise SystemExit(f"{name}: row missing instruction/input/output")
        if not {"route", "task_type", "requires_calculation", "requires_human_review", "confidence"} <= set(row["output"]):
            raise SystemExit(f"{name}: row output missing router fields")
        count += 1
    if count < 20:
        raise SystemExit(f"{name}: expected at least 20 rows, got {count}")
print("fixture JSONL OK")
PY

"$PYTHON_BIN" scripts/verify_model_catalog.py --catalog presets/model_catalog.yaml --no-download --json-output artifacts/security/model_manifest_verification.json
"$PYTHON_BIN" scripts/export_openapi.py
"$PYTHON_BIN" scripts/check_file_size.py --config rules/code_shape.json --json-output artifacts/review/file_size_report.json --fail-on-hard-limit
"$PYTHON_BIN" scripts/check_import_boundaries.py --json-output artifacts/review/import_boundary_report.json --rules rules/code_shape.json
"$PYTHON_BIN" scripts/scan_export_artifact.py --self-test
"$PYTHON_BIN" scripts/verify_pii_holdout.py --phase "$PHASE" --json-output artifacts/security/pii_holdout_report.json
if [ "$VERIFY_ONLY" = "1" ]; then
  run_pip_audit allow-skip
fi

"$PYTHON_BIN" - <<'PY'
from pathlib import Path
import re
import sqlite3

text = Path("docs/specs/ARCHITECTURE.md").read_text()
blocks = re.findall(r"```sql\n(.*?)\n```", text, re.S)
ddl = next(b for b in blocks if "CREATE TABLE preset" in b)
indexes = next(b for b in blocks if "CREATE INDEX ix_project_updated_at" in b)
con = sqlite3.connect(":memory:")
con.executescript(ddl + "\n" + indexes)
print("sqlite ddl extraction OK")

missing = []
for p in Path("docs").rglob("*.md"):
    body = p.read_text(errors="ignore")
    for m in re.finditer(r"\]\(([^)#][^)]+?\.md)(?:#[^)]+)?\)", body):
        target = m.group(1)
        if target.startswith("http"):
            continue
        if not (p.parent / target).resolve().exists():
            missing.append(f"{p}:{target}")
if missing:
    raise SystemExit("\n".join(missing))
print("markdown links OK")
PY

if [ "$VERIFY_ONLY" = "1" ] && [ "$PHASE" = "scaffold" ]; then
  exit 0
fi

if [ "$SKIP_INSTALL" = "0" ]; then
  "$PYTHON_BIN" -m venv .venv
  . .venv/bin/activate
  python -m pip install --upgrade pip
  if [ "$PROFILE" = "cuda" ]; then
    python -m pip install -r requirements.txt -r requirements-dev.txt
  else
    python -m pip install -r requirements-mlx.txt -r requirements-dev.txt
  fi
  corepack enable
  corepack pnpm install
fi

if [ "$VERIFY_ONLY" != "1" ]; then
  run_pip_audit required
fi

if [ "$PHASE" = "m1-smoke" ]; then
  m1_files=(
    "services/api/app/main.py"
    "services/api/app/core/config.py"
    "services/api/app/core/errors.py"
    "services/shared/security/auth.py"
    "services/shared/security/origin.py"
    "tests/smoke/test_m1_smoke.py"
  )
  for file in "${m1_files[@]}"; do
    [ -f "$file" ] || { echo "missing M1 smoke file: $file" >&2; exit 5; }
  done
  "$PYTHON_BIN" scripts/export_openapi.py
  "$PYTHON_BIN" -m pytest tests/smoke/test_m1_smoke.py
fi

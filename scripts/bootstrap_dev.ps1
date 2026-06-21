param(
  [ValidateSet("cuda", "mlx")]
  [string]$Profile = "cuda",
  [ValidateSet("scaffold", "m1-smoke")]
  [string]$Phase = "scaffold",
  [switch]$SkipInstall,
  [switch]$VerifyOnly
)

function Invoke-RepoPython {
  param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
  )
  if (-not $script:PythonCommand) {
    Write-Error "Python 3.11 command has not been initialized"
    exit 1
  }
  $cmdArgs = @()
  $cmdArgs += $script:PythonArgs
  $cmdArgs += $Arguments
  & $script:PythonCommand @cmdArgs
}

function Invoke-ProfilePipAudit {
  param(
    [ValidateSet("required", "allow-skip")]
    [string]$Mode = "required"
  )
  New-Item -ItemType Directory -Force -Path "artifacts/security" | Out-Null
  $report = "artifacts/security/pip_audit_$Profile.json"
  if ($Profile -eq "cuda") {
    $auditRequirements = @("requirements.txt", "requirements-dev.txt")
  } else {
    $auditRequirements = @("requirements-mlx.txt", "requirements-dev.txt")
  }
  $auditArgs = @()
  foreach ($req in $auditRequirements) {
    $auditArgs += @("-r", $req)
  }

  $pythonAuditAvailable = $false
  try {
    $null = Invoke-RepoPython -m pip_audit --version 2>$null
    $pythonAuditAvailable = ($LASTEXITCODE -eq 0)
  } catch {
    $pythonAuditAvailable = $false
  }

  if ($pythonAuditAvailable) {
    Invoke-RepoPython -m pip_audit @auditArgs --format json | Set-Content $report
    if ($LASTEXITCODE -ne 0) {
      Get-Content $report -ErrorAction SilentlyContinue | Write-Error
      exit 4
    }
    Write-Output "pip-audit $Profile OK"
    return
  }

  if (Get-Command pip-audit -ErrorAction SilentlyContinue) {
    & pip-audit @auditArgs --format json | Set-Content $report
    if ($LASTEXITCODE -ne 0) {
      Get-Content $report -ErrorAction SilentlyContinue | Write-Error
      exit 4
    }
    Write-Output "pip-audit $Profile OK"
    return
  }

  if ($Mode -eq "allow-skip") {
    [ordered]@{
      profile = $Profile
      status = "skipped"
      reason = "pip-audit is not installed in this -VerifyOnly/-SkipInstall environment"
      required_files = $auditRequirements
    } | ConvertTo-Json -Depth 4 | Set-Content $report
    Write-Output "pip-audit $Profile skipped; see $report"
    return
  }

  Write-Error "pip-audit is required for profile $Profile; install requirements-dev.txt or run without -SkipInstall"
  exit 4
}

$requiredFiles = @(
  ".python-version",
  ".node-version",
  "rust-toolchain.toml",
  "requirements.txt",
  "requirements-mlx.txt",
  "requirements-dev.txt",
  "package.json",
  "pnpm-lock.yaml",
  ".env.example",
  ".vscode/settings.json",
  ".vscode/extensions.json",
  ".vscode/tasks.json",
  ".vscode/launch.json",
  ".github/workflows/security.yml",
  "scripts/bootstrap_dev.sh",
  "scripts/bootstrap_dev.ps1",
  "scripts/verify_model_catalog.py",
  "scripts/fill_model_catalog.py",
  "scripts/export_openapi.py",
  "scripts/check_file_size.py",
  "scripts/check_import_boundaries.py",
  "scripts/scan_export_artifact.py",
  "scripts/verify_pii_holdout.py",
  "presets/model_catalog.yaml",
  "presets/router.basic.v1.yaml",
  "prompts/router.prompt_only.v1.txt",
  "rules/router.routing_rules.v1.yaml",
  "rules/code_shape.json",
  "schemas/router_input.schema.json",
  "schemas/router_output.schema.json",
  "schemas/routing_rules.schema.json",
  "schemas/agent_contract.schema.json",
  "schemas/benchmark_report.schema.json",
  "schemas/export_manifest.schema.json",
  "schemas/pii_holdout.schema.json",
  "schemas/openapi.json",
  "apps/desktop/src/lib/generated.ts",
  "packages/agent-runtime/README.md",
  "packages/agent-runtime/templates/zip_runtime/agents/run.py",
  "packages/agent-runtime/templates/zip_runtime/agents/verifier.py",
  "packages/agent-runtime/templates/zip_runtime/agents/fallback.py",
  "packages/agent-runtime/templates/zip_runtime/agents/security.py",
  "packages/agent-runtime/templates/zip_runtime/requirements-runtime.txt",
  "packages/agent-runtime/templates/docker/Dockerfile.cuda",
  "packages/agent-runtime/loaders/transformers_lora.py",
  "packages/agent-runtime/loaders/mlx_lora.py",
  "services/shared/db/migrations/env.py",
  "services/shared/db/migrations/versions/0001_initial.py",
  "examples/fixtures/router_20.jsonl",
  "examples/fixtures/gold_eval.finance.v1.jsonl",
  "examples/fixtures/llamafactory_config.golden.yaml",
  "examples/fixtures/mlx_config.golden.json",
  "examples/security/pii_holdout.v1.jsonl"
)

foreach ($file in $requiredFiles) {
  if (-not (Test-Path $file)) {
    Write-Error "missing Day-0 file: $file"
    exit 1
  }
}

$toolchainStrict = -not ($VerifyOnly -and $Phase -eq "scaffold")
$toolErrors = @()
foreach ($cmd in @("node", "corepack", "sqlite3", "rustc")) {
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
    $toolErrors += "missing required tool: $cmd"
  }
}
$script:PythonCommand = $null
$script:PythonArgs = @()
$pythonVersion = ""
if (Get-Command py -ErrorAction SilentlyContinue) {
  $script:PythonCommand = "py"
  $script:PythonArgs = @("-3.11")
  $pythonVersion = (& py -3.11 --version 2>&1) -join ""
} elseif (Get-Command python3.11 -ErrorAction SilentlyContinue) {
  $script:PythonCommand = "python3.11"
  $pythonVersion = (& python3.11 --version 2>&1) -join ""
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  $candidateVersion = (& python --version 2>&1) -join ""
  if ($candidateVersion.StartsWith("Python 3.11.")) {
    $script:PythonCommand = "python"
    $pythonVersion = $candidateVersion
  } else {
    $toolErrors += "Python command is not 3.11: $candidateVersion"
  }
} else {
  $toolErrors += "missing required tool: Python 3.11"
}
$nodeVersion = ((& node --version 2>&1) -join "").TrimStart("v")
$pnpmVersion = ((& corepack pnpm --version 2>&1) -join "")
$rustVersion = ((& rustc --version 2>&1) -join "")
$rustOk = ($LASTEXITCODE -eq 0)
$sqliteVersion = ((& sqlite3 --version 2>&1) -join "").Split(" ")[0]
$expectedNode = (Get-Content ".node-version").Trim()
$expectedRust = ((Get-Content "rust-toolchain.toml") | Select-String 'channel = "([^"]+)"').Matches.Groups[1].Value
$checks = [ordered]@{
  python = $pythonVersion.StartsWith("Python 3.11.")
  node = ($nodeVersion -eq $expectedNode)
  pnpm = $pnpmVersion.StartsWith("9.")
  rust = ($rustOk -and $rustVersion.Contains($expectedRust))
  sqlite = ([version]$sqliteVersion -ge [version]"3.40.0")
}
$toolReport = [ordered]@{
  expected = [ordered]@{ python = "3.11.x"; node = $expectedNode; pnpm_major = "9"; rust = $expectedRust; sqlite_min = "3.40" }
  actual = [ordered]@{ python = $pythonVersion; node = $nodeVersion; pnpm = $pnpmVersion; rust = $rustVersion; sqlite = $sqliteVersion }
  checks = $checks
  strict = $toolchainStrict
  errors = $toolErrors
}
New-Item -ItemType Directory -Force -Path "artifacts/review" | Out-Null
$toolReport | ConvertTo-Json -Depth 8 | Set-Content "artifacts/review/toolchain_report.json"
if ($toolErrors.Count -gt 0 -or ($checks.Values -contains $false)) {
  if ($toolchainStrict) {
    Write-Error "toolchain version mismatch; see artifacts/review/toolchain_report.json"
    exit 1
  }
  Write-Output "toolchain version mismatch recorded in artifacts/review/toolchain_report.json"
} else {
  Write-Output "toolchain versions OK"
}

$pinCheck = @'
from pathlib import Path
for name in ["requirements.txt", "requirements-mlx.txt", "requirements-dev.txt"]:
    for i, line in enumerate(Path(name).read_text().splitlines(), 1):
        value = line.strip()
        if not value or value.startswith("#") or value.startswith("--"):
            continue
        if "==" not in value or any(op in value for op in [">=", "<=", "~=", "!=", ">", "<", "*"]):
            raise SystemExit(f"{name}:{i}: dependency must use exact == pin: {line}")
print("requirements exact pins OK")
import json
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
'@
$pinCheck | Invoke-RepoPython -

Invoke-RepoPython scripts/verify_model_catalog.py --catalog presets/model_catalog.yaml --no-download --json-output artifacts/security/model_manifest_verification.json
Invoke-RepoPython scripts/export_openapi.py
Invoke-RepoPython scripts/check_file_size.py --config rules/code_shape.json --json-output artifacts/review/file_size_report.json --fail-on-hard-limit
Invoke-RepoPython scripts/check_import_boundaries.py --json-output artifacts/review/import_boundary_report.json --rules rules/code_shape.json
Invoke-RepoPython scripts/scan_export_artifact.py --self-test
Invoke-RepoPython scripts/verify_pii_holdout.py --phase $Phase --json-output artifacts/security/pii_holdout_report.json
if ($VerifyOnly) {
  Invoke-ProfilePipAudit -Mode "allow-skip"
}

$docChecks = @'
from pathlib import Path
import json
import re
import sqlite3

for path in Path("schemas").glob("*.json"):
    json.loads(path.read_text())
json.loads(Path("package.json").read_text())
json.loads(Path(".vscode/tasks.json").read_text())
print("json artifacts OK")

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
'@
$docChecks | Invoke-RepoPython -

if ($VerifyOnly -and $Phase -eq "scaffold") {
  exit 0
}

if (-not $SkipInstall) {
  Invoke-RepoPython -m venv .venv
  $venvPython = ".\.venv\Scripts\python"
  if (-not (Test-Path $venvPython)) {
    $venvPython = "./.venv/bin/python"
  }
  & $venvPython -m pip install --upgrade pip
  if ($Profile -eq "cuda") {
    & $venvPython -m pip install -r requirements.txt -r requirements-dev.txt
  } else {
    & $venvPython -m pip install -r requirements-mlx.txt -r requirements-dev.txt
  }
  $script:PythonCommand = $venvPython
  $script:PythonArgs = @()
  corepack enable
  corepack pnpm install
}

if (-not $VerifyOnly) {
  Invoke-ProfilePipAudit -Mode "required"
}

if ($Phase -eq "m1-smoke") {
  $m1Files = @(
    "services/api/app/main.py",
    "services/api/app/core/config.py",
    "services/api/app/core/errors.py",
    "services/shared/security/auth.py",
    "services/shared/security/origin.py",
    "tests/smoke/test_m1_smoke.py"
  )
  foreach ($file in $m1Files) {
    if (-not (Test-Path $file)) {
      Write-Error "missing M1 smoke file: $file"
      exit 5
    }
  }
  Invoke-RepoPython scripts/export_openapi.py
  Invoke-RepoPython -m pytest tests/smoke/test_m1_smoke.py
}

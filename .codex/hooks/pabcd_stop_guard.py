#!/usr/bin/env python3
import json
import os
import posixpath
import subprocess
import sys
from pathlib import Path


def repo_root(cwd: str | None = None) -> Path:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd or os.getcwd(),
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=10,
        ).strip()
        return Path(out).resolve()
    except Exception:
        return Path(cwd or os.getcwd()).resolve()


ROOT = repo_root()
STATE_PATH = ROOT / ".codex" / "pabcd-state.json"
COMPLETION_LOG = "docs/plans/2026-05-09_COMPLETION_LOG.md"
LIVE_DOC_PREFIXES = (
    "docs/plans/",
    "docs/issues/",
    "docs/verification/",
    "docs/guides/",
)
LIVE_DOC_EXACT = {"docs/CONTEXT.md", "docs/WORKING.md", COMPLETION_LOG}
REFERENCE_ONLY_PREFIXES = (
    "docs/archive/",
    "_code_backup_unused/",
)
HOME = Path.home()
REFERENCE_ONLY_ABSOLUTE_PREFIXES = (
    "/tmp/",
    "/private/tmp/",
    "/var/folders/",
    f"{HOME / 'Downloads'}/",
    f"{HOME / 'Desktop'}/",
)
NO_IMPLEMENT_GATES = {"1", "2", "2R", "3", "4", "5R", "6"}
SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".sql", ".yml", ".yaml", ".toml", ".json"}


def emit_block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def run(args: list[str], cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )


def load_payload() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception as exc:
        emit_block(f"Unable to parse .codex/pabcd-state.json: {exc}")
    return {}


def changed_paths(cwd: Path) -> list[str]:
    result = run(["git", "status", "--porcelain", "--untracked-files=all"], cwd, timeout=30)
    if result.returncode != 0:
        emit_block("Unable to inspect git status.\n\n" + result.stdout[-4000:])
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path:
            paths.append(path)
    return sorted(set(paths))


def current_branch(cwd: Path) -> str:
    result = run(["git", "branch", "--show-current"], cwd, timeout=30)
    return result.stdout.strip() if result.returncode == 0 else ""


def current_head(cwd: Path) -> str:
    result = run(["git", "rev-parse", "--short", "HEAD"], cwd, timeout=30)
    return result.stdout.strip() if result.returncode == 0 else ""


def normalize_state_path(value: object) -> str:
    raw = str(value).strip().replace("\\", "/")
    if not raw:
        return ""
    trailing = raw.endswith("/")
    if raw.startswith("/"):
        try:
            resolved = Path(raw).resolve()
            trailing = trailing or resolved.is_dir()
            raw = resolved.relative_to(ROOT.resolve()).as_posix()
        except Exception:
            return ""
    else:
        trailing = trailing or (ROOT / raw).is_dir()
    norm = posixpath.normpath(raw)
    if norm in {".", ".."} or norm.startswith("../"):
        return ""
    if trailing and not norm.endswith("/"):
        norm += "/"
    return norm


def normalize_path(path: str) -> str:
    return normalize_state_path(path).rstrip("/")


def state_path_set(state: dict, key: str) -> set[str]:
    value = state.get(key) or []
    return {item for item in (normalize_state_path(item) for item in value) if item}


def matches_path(path: str, entries: set[str]) -> bool:
    if not entries:
        return False
    norm = normalize_path(path)
    for item in entries:
        if item.endswith("/"):
            if norm.startswith(item.rstrip("/") + "/"):
                return True
        elif norm == item:
            return True
    return False


def is_edit_allowed(path: str, allowed: set[str]) -> bool:
    if not allowed:
        return True
    return matches_path(path, allowed)


def gate_changed_paths(paths: list[str], state: dict) -> list[str]:
    frozen = state_path_set(state, "approved_existing_changed_paths")
    return [path for path in paths if not matches_path(path, frozen)]


def is_live_doc(path: str) -> bool:
    return path in LIVE_DOC_EXACT or path.startswith(LIVE_DOC_PREFIXES)


def is_reference_only(path: str) -> bool:
    return path.startswith(REFERENCE_ONLY_PREFIXES)


def has_changed_path(path: str, changed: list[str]) -> bool:
    return path in changed or any(item.endswith("/") and path.startswith(item) for item in changed)


def state_list(state: dict, key: str) -> list[str]:
    value = state.get(key) or []
    return [str(item) for item in value if str(item).strip()]


def line_count(path: Path) -> int:
    try:
        return len(path.read_text(errors="ignore").splitlines())
    except Exception:
        return 0


def run_required_commands(state: dict, cwd: Path) -> list[str]:
    if not state.get("run_required_commands"):
        return []
    failures: list[str] = []
    for command in state.get("required_commands", []):
        result = subprocess.run(
            command,
            cwd=str(cwd),
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=240,
        )
        if result.returncode != 0:
            failures.append(f"$ {command}\n{result.stdout[-6000:]}")
    return failures


def main() -> None:
    payload = load_payload()
    if payload.get("stop_hook_active"):
        return

    state = load_state()
    if not state.get("active"):
        return

    cwd = Path(payload.get("cwd") or os.getcwd())
    current_root = repo_root(str(cwd))
    if ROOT != current_root:
        emit_block(f"PABCD gate is active, but Codex is not operating inside {ROOT}.")

    branch = current_branch(ROOT)
    head = current_head(ROOT)
    expected_branch = state.get("branch")
    expected_head = state.get("head")
    baseline_errors: list[str] = []
    if state.get("workspace_root") and Path(state["workspace_root"]).resolve() != ROOT:
        baseline_errors.append(f"workspace_root does not match {ROOT}")
    if expected_branch and expected_branch != branch:
        baseline_errors.append(f"branch drift: expected {expected_branch}, got {branch}")
    if expected_head and expected_head != head:
        baseline_errors.append(f"HEAD drift: expected {expected_head}, got {head}")
    if baseline_errors:
        emit_block("PABCD baseline drift detected:\n\n" + "\n".join(f"- {e}" for e in baseline_errors))

    changed = changed_paths(ROOT)
    if not changed:
        return
    gate_changed = gate_changed_paths(changed, state)

    gate = str(state.get("gate", "")).upper()
    allowed = state_path_set(state, "allowed_edit_paths")
    approved_docs = state_path_set(state, "approved_doc_paths")
    blocked = state_path_set(state, "blocked_edit_paths")
    approved_deferrals = state_list(state, "approved_deferred_items")
    unapproved_deferrals = state_list(state, "deferred_followups")
    violations: list[str] = []

    for path in gate_changed:
        if matches_path(path, blocked):
            violations.append(f"{path} is explicitly blocked")
        if is_reference_only(path):
            violations.append(f"{path} is reference-only under this protocol")
        if path.startswith("docs/") and not is_live_doc(path):
            violations.append(f"{path} is not an approved live documentation target")
        if path.startswith("docs/") and approved_docs and not matches_path(path, approved_docs):
            violations.append(f"{path} is outside approved_doc_paths")
        if gate in NO_IMPLEMENT_GATES and not path.startswith("docs/") and not path.startswith(".codex/"):
            violations.append(f"{path} changed during Gate {gate}, which is not an implementation gate")
        if not is_edit_allowed(path, allowed) and not matches_path(path, approved_docs):
            violations.append(f"{path} is outside allowed_edit_paths")

    if gate in {"5", "7"} and not state.get("explicit_user_approval"):
        violations.append(f"Gate {gate} requires explicit_user_approval before code changes")

    if state.get("require_completion_log") and gate in {"5", "7"}:
        if COMPLETION_LOG not in gate_changed:
            violations.append(f"{COMPLETION_LOG} must be updated before closeout")

    if gate == "7":
        if not state.get("all_required_teams_go"):
            violations.append("Gate 7 closeout requires all_required_teams_go=true")
        if state.get("phase_completion_required", True):
            if not state.get("phase_complete"):
                violations.append("Gate 7 means phase completion: set phase_complete=true only when the phase is fully reflected in live code and live docs")
            if unapproved_deferrals and not state.get("deferred_split_approved_by_user"):
                violations.append(
                    "Gate 7 cannot leave deferred follow-up slices without explicit user approval: "
                    + "; ".join(unapproved_deferrals)
                )
            if approved_deferrals and not state.get("deferred_split_approved_by_user"):
                violations.append("approved_deferred_items require deferred_split_approved_by_user=true")
        if state.get("require_live_docs_reflected", True):
            if not approved_docs:
                violations.append("Gate 7 requires approved_doc_paths so live docs updates are explicit")
            for doc_path in approved_docs:
                if not has_changed_path(doc_path, gate_changed):
                    violations.append(f"Gate 7 requires live doc update in approved_doc_paths: {doc_path}")
        for output_path in state_list(state, "reference_only_outputs"):
            if output_path.startswith(REFERENCE_ONLY_ABSOLUTE_PREFIXES):
                violations.append(f"Gate 7 cannot close with reference-only temp output as authority: {output_path}")

    if not state.get("allow_god_files"):
        for path in gate_changed:
            candidate = ROOT / path
            if candidate.suffix in SOURCE_EXTS and candidate.exists() and line_count(candidate) >= 1000:
                violations.append(f"{path} has {line_count(candidate)} lines; Gate protocol blocks 1,000+ line touched source files")

    failures = run_required_commands(state, ROOT)
    if failures:
        violations.append("Required verification failed:\n\n" + "\n\n".join(failures))

    if violations:
        emit_block("PABCD gate violation detected:\n\n" + "\n".join(f"- {v}" for v in violations))


if __name__ == "__main__":
    main()

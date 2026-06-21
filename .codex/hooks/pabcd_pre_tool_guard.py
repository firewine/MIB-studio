#!/usr/bin/env python3
import json
import os
import re
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
HOME = Path.home()
REMOTE_PIPE_PATTERN = r"\b(" + "cu" + "rl|w" + "get" + r")\b.*\|\s*(" + "s" + "h|ba" + "sh" + r")\b"


DENY_ALWAYS = [
    (r"\bgit\s+add\s+(\.|-A)(\s|$)", "Use explicit file paths for bulk staging."),
    (r"\bgit\s+push\s+--force\b", "Force push is blocked."),
    (r"\brm\s+-rf\b", "rm recursive force is blocked."),
    (REMOTE_PIPE_PATTERN, "Remote pipe execution is blocked."),
]


NO_IMPLEMENT_GATES = {"1", "2", "2R", "3", "4", "5R", "6"}
REFERENCE_ONLY_WRITE_PATTERNS = [
    rf"\b(tee|cp|mv)\b.*\s(/tmp|/private/tmp|/var/folders|{re.escape(str(HOME / 'Downloads'))}|{re.escape(str(HOME / 'Desktop'))})/",
    rf">\s*(/tmp|/private/tmp|/var/folders|{re.escape(str(HOME / 'Downloads'))}|{re.escape(str(HOME / 'Desktop'))})/",
]


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


def command_from_payload() -> str:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return ""
    tool_input = payload.get("tool_input") or {}
    return (
        tool_input.get("command")
        or tool_input.get("cmd")
        or payload.get("command")
        or payload.get("cmd")
        or ""
    )


def write_like_command(command: str) -> bool:
    write_like = [
        r"\bapply_patch\b",
        r"\bpython\d*(\.\d+)?\b.*\b(open|write|Path\().*['\"]w",
        r"\btee\s+",
        r"\bsed\s+-i\b",
    ]
    return any(re.search(pattern, command) for pattern in write_like)


def main() -> None:
    command = command_from_payload()
    if not command:
        return

    for pattern, reason in DENY_ALWAYS:
        if re.search(pattern, command):
            deny(reason)

    state = load_json(STATE_PATH)
    if not state.get("active"):
        return

    current_root = repo_root()
    if current_root != ROOT:
        deny(f"PABCD gate is active, but the command is not running in {ROOT}.")

    gate = str(state.get("gate", "")).upper()
    if re.search(r"\bgit\s+commit\b|\bgit\s+push\b", command):
        if not (gate == "7" and state.get("commit_push_approved")):
            deny("git commit/push is allowed only in Gate 7 when commit_push_approved is true.")

    if gate == "7" and any(re.search(pattern, command) for pattern in REFERENCE_ONLY_WRITE_PATTERNS):
        deny("Gate 7 must apply final code/docs to the live workspace, not temp, Downloads, Desktop, or other reference-only paths.")

    if gate in NO_IMPLEMENT_GATES and write_like_command(command):
        deny(f"Gate {gate} is not an implementation gate. Do not write files unless the gate explicitly approved doc edits.")


if __name__ == "__main__":
    main()

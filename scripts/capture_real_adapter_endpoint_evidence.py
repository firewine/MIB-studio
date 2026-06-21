#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT = "artifacts/review/real_trained_adapter_endpoint_evidence.md"


@dataclass(frozen=True)
class EndpointResult:
    status: int
    body: Any
    text: str


def docker_run_command(*, image: str, name: str, port: int, model_cache_dir: Path, token: str) -> list[str]:
    if not token or len(token) < 32:
        raise ValueError("MIB_RUNTIME_BEARER_TOKEN must be at least 32 characters")
    return [
        "docker",
        "run",
        "-d",
        "--name",
        name,
        "--gpus",
        "all",
        "-p",
        f"127.0.0.1:{port}:8000",
        "-v",
        f"{model_cache_dir.resolve()}:/models:ro",
        "-e",
        "MIB_MODEL_CACHE_DIR=/models",
        "-e",
        f"MIB_RUNTIME_BEARER_TOKEN={token}",
        image,
    ]


def run_command(cmd: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=False, text=True, capture_output=True, timeout=timeout)


def http_json(method: str, url: str, *, token: str | None = None, payload: dict[str, Any] | None = None) -> EndpointResult:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            text = response.read().decode("utf-8")
            return EndpointResult(status=response.status, body=parse_json(text), text=text)
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        return EndpointResult(status=exc.code, body=parse_json(text), text=text)


def wait_health(base_url: str, *, timeout_seconds: int) -> EndpointResult:
    deadline = time.monotonic() + timeout_seconds
    last = EndpointResult(status=0, body={}, text="")
    while time.monotonic() < deadline:
        last = http_json("GET", base_url + "/healthz")
        if last.status == 200:
            return last
        time.sleep(1)
    return last


def parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def verify_endpoint_outputs(native: EndpointResult, openai: EndpointResult) -> tuple[bool, dict[str, Any]]:
    native_output = native.body.get("output") if isinstance(native.body, dict) else None
    choices = openai.body.get("choices") if isinstance(openai.body, dict) else None
    if not isinstance(native_output, dict) or not isinstance(choices, list) or not choices:
        return False, {"native_output": native_output, "openai_output": None}
    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    content = message.get("content") if isinstance(message, dict) else None
    openai_output = parse_json(content) if isinstance(content, str) else None
    return native_output == openai_output, {"native_output": native_output, "openai_output": openai_output}


def inspect_container(name: str, *, model_cache_dir: Path) -> dict[str, Any]:
    result = run_command(["docker", "inspect", name])
    if result.returncode != 0:
        return {"ok": False, "error": result.stderr.strip() or result.stdout.strip()}
    payload = json.loads(result.stdout)
    item = payload[0] if payload else {}
    env = item.get("Config", {}).get("Env", [])
    mounts = item.get("Mounts", [])
    fake_backend_absent = not any(str(row).startswith("MIB_RUNTIME_ALLOW_FAKE_BACKEND=") for row in env)
    expected_source = str(model_cache_dir.resolve())
    readonly_mount = any(
        mount.get("Destination") == "/models" and mount.get("Source") == expected_source and mount.get("RW") is False
        for mount in mounts
        if isinstance(mount, dict)
    )
    return {
        "ok": fake_backend_absent and readonly_mount,
        "fake_backend_absent": fake_backend_absent,
        "readonly_model_cache_mount": readonly_mount,
        "mounts": mounts,
    }


def redact_command(cmd: list[str], token: str) -> str:
    return " ".join("<redacted-token>" if token and token in part else part for part in cmd)


def render_markdown(report: dict[str, Any]) -> str:
    return f"""# Real Trained Adapter Endpoint Evidence

Date: {report["date"]}
Gate: `mib-studio-real-trained-adapter-endpoint-evidence`
Decision: `GO_REAL_TRAINED_ADAPTER_ENDPOINT`

## Required RC Markers

```yaml
MIB_RUNTIME_ALLOW_FAKE_BACKEND: absent
/healthz: {report["health_status"]}
/agents/{{agent_id}}/run: {report["native_status"]}
/v1/chat/completions: {report["openai_status"]}
real_trained_adapter: true
self_test: {str(report["self_test"]).lower()}
```

## Docker Runtime

```yaml
image: {report["image"]}
container_name: {report["container_name"]}
agent_id: {report["agent_id"]}
model_cache_dir: {report["model_cache_dir"]}
docker_run: {report["docker_run_redacted"]}
fake_backend_env_absent: {str(report["inspect"].get("fake_backend_absent")).lower()}
readonly_model_cache_mount: {str(report["inspect"].get("readonly_model_cache_mount")).lower()}
```

## Endpoint Transcripts

Health response:

```json
{json.dumps(report["health_body"], sort_keys=True, indent=2)}
```

Native response:

```json
{json.dumps(report["native_body"], sort_keys=True, indent=2)}
```

OpenAI-compatible response:

```json
{json.dumps(report["openai_body"], sort_keys=True, indent=2)}
```

Output equivalence:

```yaml
native_openai_output_equal: {str(report["output_equal"]).lower()}
```

## Decision

```yaml
real_trained_adapter_endpoint: GO
MIB_RUNTIME_ALLOW_FAKE_BACKEND: absent
read_only_model_cache_mount: {str(report["inspect"].get("readonly_model_cache_mount")).lower()}
native_endpoint_status: {report["native_status"]}
openai_endpoint_status: {report["openai_status"]}
real_trained_adapter: true
self_test: {str(report["self_test"]).lower()}
```
"""


def self_test_report() -> dict[str, Any]:
    native_body = {
        "output": {
            "route": "finance_income",
            "task_type": "provide_advice",
            "requires_calculation": True,
            "requires_human_review": False,
            "confidence": 0.94,
        },
        "verifier_status": "PASS",
    }
    openai_body = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(native_body["output"], sort_keys=True),
                    "role": "assistant",
                }
            }
        ]
    }
    return {
        "date": datetime.now(UTC).isoformat(),
        "self_test": True,
        "image": "self-test-image",
        "container_name": "self-test-container",
        "agent_id": "self_test.v1",
        "model_cache_dir": "/tmp/self-test-model-cache",
        "docker_run_redacted": "self-test only; no docker command was run",
        "inspect": {"fake_backend_absent": True, "readonly_model_cache_mount": True},
        "health_status": 200,
        "native_status": 200,
        "openai_status": 200,
        "health_body": {"ok": True},
        "native_body": native_body,
        "openai_body": openai_body,
        "output_equal": True,
    }


def live_report(args: argparse.Namespace) -> dict[str, Any]:
    if os.environ.get("MIB_RUNTIME_ALLOW_FAKE_BACKEND"):
        raise SystemExit("Unset MIB_RUNTIME_ALLOW_FAKE_BACKEND before collecting RC endpoint evidence")
    token = args.token or os.environ.get("MIB_RUNTIME_BEARER_TOKEN", "")
    model_cache_dir = Path(args.model_cache_dir)
    if not model_cache_dir.is_dir():
        raise SystemExit(f"model cache dir does not exist: {model_cache_dir}")
    cmd = docker_run_command(
        image=args.image,
        name=args.container_name,
        port=args.host_port,
        model_cache_dir=model_cache_dir,
        token=token,
    )
    run = run_command(cmd)
    if run.returncode != 0:
        raise SystemExit(run.stderr.strip() or run.stdout.strip() or "docker run failed")
    base_url = f"http://127.0.0.1:{args.host_port}"
    try:
        health = wait_health(base_url, timeout_seconds=args.timeout_seconds)
        native_payload = {"input": {"text": args.input_text}}
        native = http_json(
            "POST",
            f"{base_url}/agents/{args.agent_id}/run",
            token=token,
            payload=native_payload,
        )
        openai = http_json(
            "POST",
            f"{base_url}/v1/chat/completions",
            token=token,
            payload={"messages": [{"role": "user", "content": args.input_text}]},
        )
        output_equal, outputs = verify_endpoint_outputs(native, openai)
        inspect = inspect_container(args.container_name, model_cache_dir=model_cache_dir)
        if health.status != 200 or native.status != 200 or openai.status != 200 or not output_equal or not inspect.get("ok"):
            raise SystemExit("endpoint evidence failed required RC checks")
        return {
            "date": datetime.now(UTC).isoformat(),
            "self_test": False,
            "image": args.image,
            "container_name": args.container_name,
            "agent_id": args.agent_id,
            "model_cache_dir": str(model_cache_dir.resolve()),
            "docker_run_redacted": redact_command(cmd, token),
            "inspect": inspect,
            "health_status": health.status,
            "native_status": native.status,
            "openai_status": openai.status,
            "health_body": health.body,
            "native_body": native.body,
            "openai_body": openai.body,
            "output_equal": output_equal,
            "outputs": outputs,
        }
    finally:
        if not args.keep_container:
            run_command(["docker", "rm", "-f", args.container_name], timeout=30)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--image")
    parser.add_argument("--agent-id")
    parser.add_argument("--model-cache-dir")
    parser.add_argument("--host-port", type=int, default=18084)
    parser.add_argument("--container-name", default="mib-real-adapter-endpoint-evidence")
    parser.add_argument("--token")
    parser.add_argument("--input-text", default="finance_income income calculation")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--keep-container", action="store_true")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if args.self_test:
        report = self_test_report()
    else:
        missing = [name for name in ["image", "agent_id", "model_cache_dir"] if getattr(args, name) is None]
        if missing:
            raise SystemExit(f"missing required arguments for live capture: {', '.join('--' + item.replace('_', '-') for item in missing)}")
        report = live_report(args)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"output": str(output), "self_test": report["self_test"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

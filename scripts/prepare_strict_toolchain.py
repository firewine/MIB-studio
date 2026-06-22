#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOOLCHAIN_ROOT = Path("/tmp/mib-toolchain")
DEFAULT_COREPACK_HOME = Path("/tmp/corepack")
DEFAULT_JSON_OUTPUT = Path("/tmp/mib-strict-toolchain-preparation.json")
LINUX_X64 = "linux-x64"
RUST_TARGET = "x86_64-unknown-linux-gnu"
Runner = Callable[[list[str], dict[str, str]], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class Pins:
    node: str
    rust: str
    pnpm: str


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def write_json(path: str | Path, value: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def read_pins(repo_root: Path = REPO_ROOT) -> Pins:
    node = (repo_root / ".node-version").read_text(encoding="utf-8").strip()
    rust_text = (repo_root / "rust-toolchain.toml").read_text(encoding="utf-8")
    rust_match = re.search(r'channel\s*=\s*"([^"]+)"', rust_text)
    if rust_match is None:
        raise SystemExit("rust-toolchain.toml is missing toolchain.channel")
    package = json.loads((repo_root / "package.json").read_text(encoding="utf-8"))
    package_manager = package.get("packageManager", "")
    pnpm_match = re.fullmatch(r"pnpm@([^@\s]+)", package_manager)
    if pnpm_match is None:
        raise SystemExit("package.json packageManager must be pnpm@<version>")
    return Pins(node=node, rust=rust_match.group(1), pnpm=pnpm_match.group(1))


def node_urls(version: str) -> dict[str, str]:
    basename = f"node-v{version}-{LINUX_X64}.tar.xz"
    base = f"https://nodejs.org/dist/v{version}"
    return {"archive": f"{base}/{basename}", "checksums": f"{base}/SHASUMS256.txt", "archive_name": basename}


def rust_urls(version: str) -> dict[str, str]:
    basename = f"rust-{version}-{RUST_TARGET}.tar.xz"
    base = "https://static.rust-lang.org/dist"
    return {"archive": f"{base}/{basename}", "checksums": f"{base}/{basename}.sha256", "archive_name": basename}


def target_paths(pins: Pins, toolchain_root: Path, corepack_home: Path) -> dict[str, Any]:
    node_dir = toolchain_root / f"node-v{pins.node}-{LINUX_X64}"
    rust_dir = toolchain_root / f"rust-{pins.rust}-{RUST_TARGET}"
    pnpm_cjs = corepack_home / "v1" / "pnpm" / pins.pnpm / "bin" / "pnpm.cjs"
    return {
        "node_dir": node_dir,
        "node_bin": node_dir / "bin" / "node",
        "corepack_bin": node_dir / "bin" / "corepack",
        "rust_dir": rust_dir,
        "rustc_bin": rust_dir / "rustc" / "bin" / "rustc",
        "cargo_bin": rust_dir / "cargo" / "bin" / "cargo",
        "pnpm_cjs": pnpm_cjs,
    }


def build_report(repo_root: Path, toolchain_root: Path, corepack_home: Path, *, dry_run: bool) -> dict[str, Any]:
    pins = read_pins(repo_root)
    paths = target_paths(pins, toolchain_root, corepack_home)
    node = node_urls(pins.node)
    rust = rust_urls(pins.rust)
    node_present = paths["node_bin"].is_file()
    rust_present = paths["rustc_bin"].is_file() and paths["cargo_bin"].is_file()
    pnpm_present = paths["pnpm_cjs"].is_file()
    actions = [
        {
            "id": "node_linux_x64",
            "status": "present" if node_present else "would_download_extract" if dry_run else "pending",
            "version": pins.node,
            "archive_url": node["archive"],
            "checksum_url": node["checksums"],
            "install_dir": str(paths["node_dir"]),
            "required_binary": str(paths["node_bin"]),
        },
        {
            "id": "rust_x86_64_unknown_linux_gnu",
            "status": "present" if rust_present else "would_download_extract" if dry_run else "pending",
            "version": pins.rust,
            "archive_url": rust["archive"],
            "checksum_url": rust["checksums"],
            "install_dir": str(paths["rust_dir"]),
            "required_binaries": [str(paths["rustc_bin"]), str(paths["cargo_bin"])],
        },
        {
            "id": "pnpm_corepack",
            "status": "present" if pnpm_present else "would_corepack_prepare" if dry_run else "pending",
            "version": pins.pnpm,
            "package_manager": f"pnpm@{pins.pnpm}",
            "corepack_home": str(corepack_home),
            "required_file": str(paths["pnpm_cjs"]),
            "node_path_prefix": str(paths["node_dir"] / "bin"),
        },
    ]
    ready = node_present and rust_present and pnpm_present
    return {
        "schema_version": "mib_strict_toolchain_preparation.v1",
        "date": now_utc(),
        "status": "READY_STRICT_TOOLCHAIN" if ready else "DRY_RUN_NOT_APPLIED" if dry_run else "NOT_READY_STRICT_TOOLCHAIN",
        "dry_run": dry_run,
        "repo_root": str(repo_root),
        "toolchain_root": str(toolchain_root),
        "corepack_home": str(corepack_home),
        "pins": {"node": pins.node, "rust": pins.rust, "pnpm": pins.pnpm},
        "bootstrap_alignment": {
            "script": "scripts/bootstrap_dev.sh",
            "env": {
                "MIB_TOOLCHAIN_ROOT": str(toolchain_root),
                "COREPACK_HOME": str(corepack_home),
                "COREPACK_DEFAULT_TO_LATEST": "0",
            },
            "node_path_expected_by_bootstrap": str(paths["node_dir"] / "bin"),
            "rust_paths_expected_by_bootstrap": [str(paths["rustc_bin"].parent), str(paths["cargo_bin"].parent)],
        },
        "actions": actions,
        "next_verification_command": "COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install",
        "release_claimed_go": False,
        "m6_rc_claimed_go": False,
    }


def read_expected_sha256(checksum_path: Path, archive_name: str) -> str:
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1].lstrip("*") == archive_name:
            return parts[0]
    if checksum_path.name.endswith(".sha256"):
        first = checksum_path.read_text(encoding="utf-8").strip().split()[0]
        if re.fullmatch(r"[0-9a-fA-F]{64}", first):
            return first.lower()
    raise RuntimeError(f"checksum for {archive_name} not found in {checksum_path}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as response:
        with output.open("wb") as handle:
            shutil.copyfileobj(response, handle)


def ensure_archive(urls: dict[str, str], download_dir: Path) -> Path:
    archive = download_dir / urls["archive_name"]
    checksums = download_dir / f"{urls['archive_name']}.checksums"
    if not archive.is_file():
        download(urls["archive"], archive)
    if not checksums.is_file():
        download(urls["checksums"], checksums)
    expected = read_expected_sha256(checksums, urls["archive_name"])
    actual = sha256_file(archive)
    if actual != expected:
        raise RuntimeError(f"sha256 mismatch for {archive}: expected {expected}, got {actual}")
    return archive


def extract_archive(archive: Path, toolchain_root: Path, target_dir: Path) -> None:
    if target_dir.exists():
        return
    toolchain_root.mkdir(parents=True, exist_ok=True)
    root = toolchain_root.resolve()
    with tarfile.open(archive, "r:xz") as tar:
        for member in tar.getmembers():
            destination = (toolchain_root / member.name).resolve()
            if not destination.is_relative_to(root):
                raise RuntimeError(f"refusing to extract archive member outside toolchain root: {member.name}")
        tar.extractall(toolchain_root)
    if not target_dir.exists():
        raise RuntimeError(f"archive did not create expected directory: {target_dir}")


def run_command(command: list[str], env: dict[str, str], runner: Runner | None = None) -> None:
    selected_runner = runner or (lambda cmd, command_env: subprocess.run(cmd, check=False, text=True, capture_output=True, env=command_env))
    result = selected_runner(command, env)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}\n{detail}")


def prepare(repo_root: Path, toolchain_root: Path, corepack_home: Path, download_dir: Path) -> dict[str, Any]:
    pins = read_pins(repo_root)
    paths = target_paths(pins, toolchain_root, corepack_home)
    if not paths["node_bin"].is_file():
        archive = ensure_archive(node_urls(pins.node), download_dir)
        extract_archive(archive, toolchain_root, paths["node_dir"])
    if not paths["rustc_bin"].is_file() or not paths["cargo_bin"].is_file():
        archive = ensure_archive(rust_urls(pins.rust), download_dir)
        extract_archive(archive, toolchain_root, paths["rust_dir"])
    if not paths["pnpm_cjs"].is_file():
        env = dict(os.environ)
        env["PATH"] = f"{paths['node_dir'] / 'bin'}:{env.get('PATH', '')}"
        env["COREPACK_HOME"] = str(corepack_home)
        env["COREPACK_DEFAULT_TO_LATEST"] = "0"
        run_command([str(paths["corepack_bin"]), "prepare", f"pnpm@{pins.pnpm}", "--activate"], env)
    return build_report(repo_root, toolchain_root, corepack_home, dry_run=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare the strict Node/Rust/pnpm toolchain expected by scripts/bootstrap_dev.sh.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--toolchain-root", default=str(DEFAULT_TOOLCHAIN_ROOT))
    parser.add_argument("--corepack-home", default=str(DEFAULT_COREPACK_HOME))
    parser.add_argument("--download-dir", default="/tmp/mib-toolchain-downloads")
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--dry-run", action="store_true", help="Write the preparation plan without downloading or extracting anything.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    toolchain_root = Path(args.toolchain_root).resolve()
    corepack_home = Path(args.corepack_home).resolve()
    if args.dry_run:
        report = build_report(repo_root, toolchain_root, corepack_home, dry_run=True)
    else:
        report = prepare(repo_root, toolchain_root, corepack_home, Path(args.download_dir).resolve())
    write_json(args.json_output, report)
    print(json.dumps({"json_output": args.json_output, "status": report["status"], "dry_run": report["dry_run"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

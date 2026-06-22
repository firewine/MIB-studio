from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


toolchain = load_module("scripts/prepare_strict_toolchain.py", "prepare_strict_toolchain")


def write_repo(root: Path) -> None:
    (root / ".node-version").write_text("20.18.1\n", encoding="utf-8")
    (root / "rust-toolchain.toml").write_text('[toolchain]\nchannel = "1.83.0"\n', encoding="utf-8")
    (root / "package.json").write_text(json.dumps({"packageManager": "pnpm@9.15.0"}), encoding="utf-8")


def test_reads_pins_from_repository_files(tmp_path: Path) -> None:
    write_repo(tmp_path)

    pins = toolchain.read_pins(tmp_path)

    assert pins.node == "20.18.1"
    assert pins.rust == "1.83.0"
    assert pins.pnpm == "9.15.0"


def test_dry_run_report_uses_official_archives_and_bootstrap_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    write_repo(repo)

    report = toolchain.build_report(repo, tmp_path / "toolchain", tmp_path / "corepack", dry_run=True)

    assert report["status"] == "DRY_RUN_NOT_APPLIED"
    assert report["dry_run"] is True
    assert report["pins"] == {"node": "20.18.1", "rust": "1.83.0", "pnpm": "9.15.0"}
    assert report["release_claimed_go"] is False
    assert report["m6_rc_claimed_go"] is False
    assert report["actions"][0]["archive_url"] == "https://nodejs.org/dist/v20.18.1/node-v20.18.1-linux-x64.tar.xz"
    assert report["actions"][0]["checksum_url"] == "https://nodejs.org/dist/v20.18.1/SHASUMS256.txt"
    assert report["actions"][1]["archive_url"] == "https://static.rust-lang.org/dist/rust-1.83.0-x86_64-unknown-linux-gnu.tar.xz"
    assert report["actions"][2]["package_manager"] == "pnpm@9.15.0"
    assert report["bootstrap_alignment"]["env"]["MIB_TOOLCHAIN_ROOT"] == str((tmp_path / "toolchain").resolve())
    assert "bootstrap_dev.sh --phase m1-smoke --skip-install" in report["next_verification_command"]


def test_report_detects_existing_toolchain_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    toolchain_root = tmp_path / "toolchain"
    corepack_home = tmp_path / "corepack"
    repo.mkdir()
    write_repo(repo)

    paths = toolchain.target_paths(toolchain.read_pins(repo), toolchain_root, corepack_home)
    paths["node_bin"].parent.mkdir(parents=True)
    paths["node_bin"].write_text("#!/bin/sh\n", encoding="utf-8")
    paths["rustc_bin"].parent.mkdir(parents=True)
    paths["rustc_bin"].write_text("#!/bin/sh\n", encoding="utf-8")
    paths["cargo_bin"].parent.mkdir(parents=True)
    paths["cargo_bin"].write_text("#!/bin/sh\n", encoding="utf-8")
    paths["pnpm_cjs"].parent.mkdir(parents=True)
    paths["pnpm_cjs"].write_text("console.log('9.15.0')\n", encoding="utf-8")

    report = toolchain.build_report(repo, toolchain_root, corepack_home, dry_run=True)

    assert report["status"] == "READY_STRICT_TOOLCHAIN"
    assert [row["status"] for row in report["actions"]] == ["present", "present", "present"]


def test_checksum_parser_supports_node_shasums_and_rust_sha256_files(tmp_path: Path) -> None:
    node = tmp_path / "SHASUMS256.txt"
    rust = tmp_path / "rust.sha256"
    node.write_text("a" * 64 + "  node-v20.18.1-linux-x64.tar.xz\n", encoding="utf-8")
    rust.write_text("b" * 64 + "  rust-1.83.0-x86_64-unknown-linux-gnu.tar.xz\n", encoding="utf-8")

    assert toolchain.read_expected_sha256(node, "node-v20.18.1-linux-x64.tar.xz") == "a" * 64
    assert toolchain.read_expected_sha256(rust, "rust-1.83.0-x86_64-unknown-linux-gnu.tar.xz") == "b" * 64


def test_command_failure_raises_actionable_error() -> None:
    def runner(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 7, stdout="", stderr="corepack failed")

    with pytest.raises(RuntimeError, match="corepack failed"):
        toolchain.run_command(["corepack", "prepare", "pnpm@9.15.0"], {}, runner=runner)


def test_extract_archive_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "bad.tar.xz"
    payload = tmp_path / "payload.txt"
    payload.write_text("bad", encoding="utf-8")
    with tarfile.open(archive, "w:xz") as tar:
        tar.add(payload, arcname="../outside.txt")

    with pytest.raises(RuntimeError, match="outside toolchain root"):
        toolchain.extract_archive(archive, tmp_path / "toolchain", tmp_path / "toolchain" / "unused")

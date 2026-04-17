"""CLI smoke tests: every subcommand exits 0 on reasonable input.

Uses ``subprocess.run`` with ``python -m searchfcr`` so we test the real
entrypoint and not just the Python function.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_cli(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    # Ensure the searchfcr package on the worktree is importable even when
    # pytest's CWD differs from the repo root.
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    # Make child processes' stdout/stderr decodable on Windows CP-1252 consoles.
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return subprocess.run(
        [sys.executable, "-m", "searchfcr", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
    )


def test_cli_help():
    r = _run_cli("--help")
    assert r.returncode == 0
    assert "searchfcr" in r.stdout.lower()


def test_cli_version():
    r = _run_cli("--version")
    assert r.returncode == 0
    assert "searchfcr" in r.stdout.lower()


def test_cli_list_models():
    r = _run_cli("list-models")
    assert r.returncode == 0, r.stderr
    # The clean names should all be there.
    for name in ("M1", "M2", "M3", "M4", "M4star", "HungarianD", "HungarianPD"):
        assert name in r.stdout


def test_cli_list_bids():
    r = _run_cli("list-bids")
    assert r.returncode == 0, r.stderr
    for b in ("p", "inv_d", "p_over_d", "p_over_d2", "p_exp_decay"):
        assert b in r.stdout


def test_cli_generate_stdout():
    r = _run_cli(
        "generate",
        "--n", "8",
        "--r", "2",
        "--L", "10",
        "--seed", "42",
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["n_nodes"] == 8
    assert data["n_robots"] == 2


def test_cli_generate_and_run(tmp_path: Path):
    inst_path = tmp_path / "inst.json"
    r = _run_cli(
        "generate",
        "--n", "10",
        "--r", "2",
        "--L", "10",
        "--seed", "42",
        "--max-opt-dist", "5.0",
        "-o", str(inst_path),
    )
    assert r.returncode == 0, r.stderr
    assert inst_path.is_file()

    r2 = _run_cli(
        "run",
        "--instance", str(inst_path),
        "--model", "M4star",
        "--energy", "10.0",
    )
    assert r2.returncode == 0, r2.stderr
    assert "model" in r2.stdout.lower()
    assert "fcr" in r2.stdout.lower()


def test_cli_bench_small():
    # Tiny trial count so the test stays fast.
    r = _run_cli("bench", "--suite", "default", "--trials", "5", timeout=180)
    assert r.returncode == 0, r.stderr
    assert "SEARCHFCR BENCHMARK" in r.stdout


def test_cli_sweep_tiny(tmp_path: Path):
    out = tmp_path / "sweep.csv"
    r = _run_cli(
        "sweep",
        "--param", "energy",
        "--range", "10,12",
        "--step", "2",
        "--n", "8",
        "--r", "2",
        "--trials", "3",
        "--models", "M3,M4star",
        "--output", str(out),
        timeout=180,
    )
    assert r.returncode == 0, r.stderr
    assert out.is_file()

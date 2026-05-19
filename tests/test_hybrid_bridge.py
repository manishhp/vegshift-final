"""Smoke tests for the hybrid integration layer."""

from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys

PROJECT_ROOT = pathlib.Path(__file__).parent.parent


def test_hybrid_step_files_exist() -> None:
    assert (PROJECT_ROOT / "pipeline" / "step18_hybrid_bridge.py").is_file()
    assert (PROJECT_ROOT / "pipeline" / "step19_py_dssat_runner.py").is_file()
    assert (PROJECT_ROOT / "run_hybrid.py").is_file()


def test_hybrid_runner_defines_steps() -> None:
    spec = importlib.util.spec_from_file_location("run_hybrid", PROJECT_ROOT / "run_hybrid.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert hasattr(module, "STEPS")
    assert len(module.STEPS) == 2


def test_hybrid_runner_dry_run_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "run_hybrid.py"), "--dry-run"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"dry-run failed:\n{result.stderr}"
    assert "dry-run complete" in result.stdout

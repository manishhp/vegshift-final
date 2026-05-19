"""Tests for Phase 0 Task 3: run_vegshift.py orchestrator."""
import importlib.util
import pathlib
import subprocess
import sys

PROJECT_ROOT = pathlib.Path(__file__).parent.parent

def test_runner_file_exists():
    assert (PROJECT_ROOT / "run_vegshift.py").is_file()

def test_runner_defines_steps_list():
    spec = importlib.util.spec_from_file_location(
        "run_vegshift", PROJECT_ROOT / "run_vegshift.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "STEPS")
    # step0, step0b, step1, step1b, steps 2-14 = 17 entries
    assert len(mod.STEPS) == 17, f"Expected 17 steps, got {len(mod.STEPS)}"

def test_runner_dry_run_exits_zero():
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "run_vegshift.py"), "--dry-run"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"dry-run failed:\n{result.stderr}"
    assert "dry-run complete" in result.stdout

def test_runner_step_scripts_listed():
    spec = importlib.util.spec_from_file_location(
        "run_vegshift", PROJECT_ROOT / "run_vegshift.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for label, script in mod.STEPS:
        assert script.startswith("pipeline/"), f"Bad path: {script}"
        assert script.endswith(".py"), f"Not a .py: {script}"

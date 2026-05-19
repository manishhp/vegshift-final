"""Tests for Phase 0 Task 1: project directory structure."""
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).parent.parent

REQUIRED_DIRS = [
    "pipeline", "data/raw", "data/raw/gaez", "data/processed",
    "data/output", "models/tft", "models/baselines", "tests",
]

def test_required_directories_exist():
    for d in REQUIRED_DIRS:
        full = PROJECT_ROOT / d
        assert full.is_dir(), f"Missing directory: {d}"

def test_pipeline_init_exists():
    assert (PROJECT_ROOT / "pipeline/__init__.py").is_file()

def test_tests_init_exists():
    assert (PROJECT_ROOT / "tests/__init__.py").is_file()

def test_agents_md_present():
    assert (PROJECT_ROOT / "AGENTS.md").is_file()

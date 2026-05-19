"""Tests for Phase 0 Task 2: requirements.txt."""
import pathlib
import re

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
REQ_FILE = PROJECT_ROOT / "requirements.txt"

REQUIRED_PACKAGES = [
    "pandas", "numpy", "scipy", "scikit-learn", "joblib",
    "torch", "pytorch-lightning", "pytorch-forecasting",
    "rasterio", "shap", "plotly", "dash", "pytest",
]

def test_requirements_file_exists():
    assert REQ_FILE.is_file()

def test_requirements_has_all_packages():
    if not REQ_FILE.is_file():
        return
    content = REQ_FILE.read_text()
    lines = [l.strip().lower() for l in content.splitlines()
             if l.strip() and not l.strip().startswith("#")]
    for pkg in REQUIRED_PACKAGES:
        found = any(l.startswith(pkg.lower()) for l in lines)
        assert found, f"Package '{pkg}' not in requirements.txt"

def test_all_packages_have_version_pin():
    if not REQ_FILE.is_file():
        return
    content = REQ_FILE.read_text()
    for line in [l.strip() for l in content.splitlines()
                 if l.strip() and not l.strip().startswith("#")]:
        assert re.search(r"[><=!]", line), f"No version constraint: '{line}'"

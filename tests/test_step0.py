"""Tests for Step 0: master index generation."""
import importlib.util
import os
import pathlib

import pandas as pd
import pytest

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
STEP0_PATH   = PROJECT_ROOT / "pipeline" / "step0_master_index.py"
OUTPUT_PATH  = PROJECT_ROOT / "data" / "processed" / "master_index.csv"

EXPECTED_CITIES = [
    "Delhi", "Mumbai", "Chennai", "Kolkata", "Bangalore",
    "Hyderabad", "Ahmedabad", "Jaipur", "Lucknow", "Pune",
]
EXPECTED_YEARS   = list(range(2000, 2025))
EXPECTED_COLUMNS = {"city", "year", "lat", "lon", "primary_crop",
                    "koppen_baseline", "risk_category"}
CONTROL_CITIES   = {"Pune", "Kolkata", "Mumbai"}
AT_RISK_CITIES   = {"Delhi", "Jaipur", "Ahmedabad", "Lucknow",
                    "Hyderabad", "Chennai", "Bangalore"}


def run_step0():
    spec = importlib.util.spec_from_file_location("step0", STEP0_PATH)
    mod  = importlib.util.module_from_spec(spec)
    orig = os.getcwd()
    os.chdir(PROJECT_ROOT)
    try:
        spec.loader.exec_module(mod)
    finally:
        os.chdir(orig)
    return pd.read_csv(OUTPUT_PATH)


@pytest.fixture(scope="module")
def master_df():
    if not STEP0_PATH.is_file():
        pytest.skip("step0_master_index.py not yet implemented")
    return run_step0()


def test_step0_script_exists():
    assert STEP0_PATH.is_file()

def test_output_file_created(master_df):
    assert OUTPUT_PATH.is_file()

def test_row_count(master_df):
    assert len(master_df) == 250, f"Got {len(master_df)}"

def test_column_names(master_df):
    assert not (EXPECTED_COLUMNS - set(master_df.columns))

def test_all_cities_present(master_df):
    assert not (set(EXPECTED_CITIES) - set(master_df["city"].unique()))

def test_all_years_present(master_df):
    assert not (set(EXPECTED_YEARS) - set(master_df["year"].unique()))

def test_each_city_has_25_rows(master_df):
    bad = master_df.groupby("city").size()
    assert (bad == 25).all(), f"Bad counts:\n{bad[bad != 25]}"

def test_no_duplicate_city_year_pairs(master_df):
    assert master_df.duplicated(subset=["city", "year"]).sum() == 0

def test_lat_lon_are_numeric(master_df):
    assert pd.api.types.is_float_dtype(master_df["lat"])
    assert pd.api.types.is_float_dtype(master_df["lon"])

def test_lat_in_india_range(master_df):
    assert master_df["lat"].between(8.0, 37.0).all()

def test_lon_in_india_range(master_df):
    assert master_df["lon"].between(68.0, 97.0).all()

def test_control_cities_have_correct_risk(master_df):
    ctrl = master_df[master_df["city"].isin(CONTROL_CITIES)]
    assert (ctrl["risk_category"] == "control").all()

def test_at_risk_cities_have_correct_risk(master_df):
    risk = master_df[master_df["city"].isin(AT_RISK_CITIES)]
    assert (risk["risk_category"] == "at_risk").all()

def test_delhi_coordinates(master_df):
    d = master_df[master_df["city"] == "Delhi"].iloc[0]
    assert abs(d["lat"] - 28.6139) < 0.001
    assert abs(d["lon"] - 77.2090) < 0.001

def test_primary_crop_no_nulls(master_df):
    assert master_df["primary_crop"].notna().all()

def test_koppen_baseline_no_nulls(master_df):
    assert master_df["koppen_baseline"].notna().all()

def test_year_dtype_is_integer(master_df):
    assert pd.api.types.is_integer_dtype(master_df["year"])

def test_known_koppen_values(master_df):
    checks = {"Delhi": "BSh", "Jaipur": "BWh", "Kolkata": "Am",
              "Chennai": "Aw", "Lucknow": "Cwa"}
    for city, zone in checks.items():
        row = master_df[master_df["city"] == city].iloc[0]
        assert row["koppen_baseline"] == zone, f"{city}: expected {zone}"

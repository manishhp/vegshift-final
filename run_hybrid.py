"""Hybrid integration runner for TFT -> DSSAT -> pyDSSAT."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

CITY_META = {
    "Delhi":     {"lat": 28.6139, "lon": 77.2090},
    "Jaipur":    {"lat": 26.9124, "lon": 75.7873},
    "Ahmedabad": {"lat": 23.0225, "lon": 72.5714},
    "Lucknow":   {"lat": 26.8467, "lon": 80.9462},
    "Hyderabad": {"lat": 17.3850, "lon": 78.4867},
    "Chennai":   {"lat": 13.0827, "lon": 80.2707},
    "Bangalore": {"lat": 12.9716, "lon": 77.5946},
    "Pune":      {"lat": 18.5204, "lon": 73.8567},
    "Kolkata":   {"lat": 22.5726, "lon": 88.3639},
    "Mumbai":    {"lat": 19.0760, "lon": 72.8777},
}

CROPS = [
    "wheat", "mustard", "rice", "cotton", "sugarcane", "groundnut", 
    "sorghum", "ragi", "chickpea", "lentil", "maize", "sunflower", 
    "bajra", "barley"
]

STEPS = [
    ("Step 18 - Climate->DSSAT Bridge", "pipeline/step18_hybrid_bridge.py"),
    ("Step 19 - pyDSSAT Runner", "pipeline/step19_py_dssat_runner.py"),
]


def main(dry_run: bool = False) -> None:
    print("VegShift Hybrid Integration")
    print("=" * 60)

    # 1. Load the preprocessed climate dataset
    climate_path = PROJECT_ROOT / "data" / "processed" / "kaggle_climate.csv"
    if not dry_run and not climate_path.exists():
        print(f"Error: {climate_path} does not exist. Run step0 and step0b first.")
        sys.exit(1)

    if not dry_run:
        df = pd.read_csv(climate_path)

    # 2. Iterate over cities and run DSSAT integrations
    for city, meta in CITY_META.items():
        print(f"\nProcessing city: {city}")
        print("-" * 60)

        temp_csv = PROJECT_ROOT / "data" / "processed" / f"temp_{city.lower()}_daily.csv"
        out_wth = PROJECT_ROOT / "data" / "output" / f"{city.lower()}.WTH"

        # Step 18 Bridge Command (once per city)
        bridge_cmd = [
            sys.executable,
            "pipeline/step18_hybrid_bridge.py",
            "--forecast", str(temp_csv),
            "--out", str(out_wth),
            "--station", city,
            "--lat", str(meta["lat"]),
            "--lon", str(meta["lon"]),
        ]

        if dry_run:
            print(f"  [dry-run] step18 would execute: {' '.join(bridge_cmd)}")
        else:
            # Extract city climate records to temp file
            city_df = df[df["city"] == city]
            city_df.to_csv(temp_csv, index=False)

            # Run Step 18
            print(f"Running Step 18 (Climate->DSSAT Bridge) for {city}...")
            res = subprocess.run(bridge_cmd)
            if res.returncode != 0:
                print(f"ERROR: Step 18 failed for {city}. Halting.")
                if temp_csv.exists():
                    os.remove(temp_csv)
                sys.exit(1)

            # Cleanup temp CSV
            if temp_csv.exists():
                os.remove(temp_csv)

        # Run Step 19 Runner Command for each crop
        for crop in CROPS:
            manifest = PROJECT_ROOT / "data" / "output" / "dssat_runs" / f"{city.lower()}_{crop}_manifest.json"
            runner_cmd = [
                sys.executable,
                "pipeline/step19_py_dssat_runner.py",
                "--weather", str(out_wth),
                "--crop", crop,
                "--manifest", str(manifest),
            ]

            if dry_run:
                print(f"  [dry-run] step19 would execute: {' '.join(runner_cmd)}")
            else:
                res = subprocess.run(runner_cmd)
                if res.returncode != 0:
                    print(f"ERROR: Step 19 failed for {crop} in {city}. Halting.")
                    sys.exit(1)

    if dry_run:
        print("\n[dry-run complete] All hybrid steps listed. No scripts executed.")
    else:
        print("\nHybrid integration complete. All DSSAT simulations successfully finished.")


if __name__ == "__main__":
    main("--dry-run" in sys.argv)

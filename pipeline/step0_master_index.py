"""
Step 0 — Master Index
Output: data/processed/master_index.csv  (250 rows x 7 cols)
No external data required.
"""
import itertools
import pathlib

import pandas as pd

CITY_META = {
    "Delhi":     {"lat": 28.6139, "lon": 77.2090, "primary_crop": "Wheat",
                  "koppen_baseline": "BSh", "risk_category": "at_risk"},
    "Jaipur":    {"lat": 26.9124, "lon": 75.7873, "primary_crop": "Mustard",
                  "koppen_baseline": "BWh", "risk_category": "at_risk"},
    "Ahmedabad": {"lat": 23.0225, "lon": 72.5714, "primary_crop": "Cotton",
                  "koppen_baseline": "BSh", "risk_category": "at_risk"},
    "Lucknow":   {"lat": 26.8467, "lon": 80.9462, "primary_crop": "Sugarcane",
                  "koppen_baseline": "Cwa", "risk_category": "at_risk"},
    "Hyderabad": {"lat": 17.3850, "lon": 78.4867, "primary_crop": "Groundnut",
                  "koppen_baseline": "BSh", "risk_category": "at_risk"},
    "Chennai":   {"lat": 13.0827, "lon": 80.2707, "primary_crop": "Rice",
                  "koppen_baseline": "Aw",  "risk_category": "at_risk"},
    "Bangalore": {"lat": 12.9716, "lon": 77.5946, "primary_crop": "Ragi",
                  "koppen_baseline": "Aw",  "risk_category": "at_risk"},
    "Pune":      {"lat": 18.5204, "lon": 73.8567, "primary_crop": "Sorghum",
                  "koppen_baseline": "BSh", "risk_category": "control"},
    "Kolkata":   {"lat": 22.5726, "lon": 88.3639, "primary_crop": "Rice/Jute",
                  "koppen_baseline": "Am",  "risk_category": "control"},
    "Mumbai":    {"lat": 19.0760, "lon": 72.8777, "primary_crop": "Rice",
                  "koppen_baseline": "Am",  "risk_category": "control"},
}

CITIES = list(CITY_META.keys())
YEARS  = list(range(2000, 2025))


def build_master_index() -> pd.DataFrame:
    rows = []
    for city, year in itertools.product(CITIES, YEARS):
        meta = CITY_META[city]
        rows.append({
            "city":            city,
            "year":            year,
            "lat":             meta["lat"],
            "lon":             meta["lon"],
            "primary_crop":    meta["primary_crop"],
            "koppen_baseline": meta["koppen_baseline"],
            "risk_category":   meta["risk_category"],
        })
    df = pd.DataFrame(rows)
    df["year"] = df["year"].astype(int)
    return df


def main() -> None:
    out_dir = pathlib.Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)
    master = build_master_index()
    out_path = out_dir / "master_index.csv"
    master.to_csv(out_path, index=False)
    print(f"Master index: {master.shape}")
    print(f"Cities: {master['city'].nunique()}")
    print(f"Years:  {master['year'].nunique()}")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()

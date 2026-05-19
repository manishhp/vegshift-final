"""Bridge TFT forecasts into DSSAT weather files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.forecast_to_dssat import normalize_columns, write_wth


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert climate forecasts to DSSAT weather files.")
    parser.add_argument("--forecast", required=True, help="Forecast CSV or Parquet")
    parser.add_argument("--out", required=True, help="Output .WTH file")
    parser.add_argument("--station", default="STATION")
    parser.add_argument("--lat", type=float)
    parser.add_argument("--lon", type=float)
    parser.add_argument("--elev", type=float)
    parser.add_argument("--manifest", default="data/output/hybrid_bridge_manifest.json")
    args = parser.parse_args()

    forecast_path = Path(args.forecast)
    if forecast_path.suffix.lower() in {".parquet", ".pq"}:
        df = pd.read_parquet(forecast_path)
    else:
        df = pd.read_csv(forecast_path)

    cleaned = normalize_columns(df)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_wth(cleaned, out_path, station=args.station, lat=args.lat, lon=args.lon, elev=args.elev)

    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "forecast": str(forecast_path),
        "weather_file": str(out_path),
        "records": len(cleaned),
        "station": args.station,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} and {manifest_path}")


if __name__ == "__main__":
    main()

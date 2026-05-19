"""Convert TFT forecast CSV/Parquet into a DSSAT .WTH weather file.

Usage:
    python forecast_to_dssat.py --input forecast.csv --out weather.WTH --station "MyStation"

The input may contain a `date` column (ISO yyyy-mm-dd) or `year`,`month`,`day` columns.
Expected climate columns (any subset): `srad`/`solar_radiation`, `tmax`, `tmin`, `rain`/`precipitation`.
If `srad` is missing it will be filled with a reasonable default.
"""
from __future__ import annotations

import argparse
import datetime as dt
import math
from pathlib import Path
import pandas as pd


DEFAULT_SRAD = 18.0


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # date handling
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    elif {"year", "month", "day"}.issubset(df.columns):
        df["date"] = pd.to_datetime(df[["year", "month", "day"]])
    else:
        raise ValueError("Input must contain a 'date' column or year/month/day columns")

    # unify names
    if "precipitation" in df.columns and "rain" not in df.columns:
        df["rain"] = df["precipitation"]
    if "solar_radiation" in df.columns and "srad" not in df.columns:
        df["srad"] = df["solar_radiation"]

    for col in ("srad", "tmax", "tmin", "rain"):
        if col not in df.columns:
            df[col] = pd.NA

    # fill SRAD with default if missing
    df["srad"] = df["srad"].fillna(DEFAULT_SRAD)

    # ensure numeric
    df["tmax"] = pd.to_numeric(df["tmax"], errors="coerce")
    df["tmin"] = pd.to_numeric(df["tmin"], errors="coerce")
    df["rain"] = pd.to_numeric(df["rain"], errors="coerce").fillna(0.0)
    df["srad"] = pd.to_numeric(df["srad"], errors="coerce").fillna(DEFAULT_SRAD)

    return df[["date", "srad", "tmax", "tmin", "rain"]].sort_values("date")


def write_wth(df: pd.DataFrame, outpath: Path, station: str = "STATION", lat: float | None = None, lon: float | None = None, elev: float | None = None):
    """Write a simple DSSAT .WTH file. This produces a conservative header and daily lines.

    Format (minimal):
    *WEATHER : STATION
    @DATE  SRAD  TMAX  TMIN  RAIN
    20250101  18.2  34.1  24.2  12.4
    """
    outpath = Path(outpath)
    with outpath.open("w", encoding="utf8") as fh:
        fh.write(f"*WEATHER : {station}\n")
        insi_lat_lon = "" if lat is None or lon is None else f"{lat:.3f} {lon:.3f}"
        elev_str = "" if elev is None else f" {elev:.0f}m"
        fh.write(f"@INSI {insi_lat_lon}{elev_str}\n")
        fh.write("@DATE  SRAD  TMAX  TMIN  RAIN\n")

        for _, row in df.iterrows():
            d = row["date"]
            if isinstance(d, (dt.datetime, dt.date)):
                datestr = d.strftime("%Y%m%d")
            else:
                datestr = pd.to_datetime(d).strftime("%Y%m%d")

            # ensure sensible ranges
            srad = float(row["srad"]) if not pd.isna(row["srad"]) else DEFAULT_SRAD
            tmax = float(row["tmax"]) if not pd.isna(row["tmax"]) else (srad / 2.0 + 20.0)
            tmin = float(row["tmin"]) if not pd.isna(row["tmin"]) else max(tmax - 10.0, -50.0)
            rain = float(row["rain"]) if not pd.isna(row["rain"]) else 0.0

            fh.write(f"{datestr}  {srad:5.2f}  {tmax:5.2f}  {tmin:5.2f}  {rain:5.2f}\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert forecast CSV to DSSAT .WTH weather file")
    parser.add_argument("--input", required=True, help="Input CSV/Parquet with forecast (date, tmax, tmin, rain, srad)")
    parser.add_argument("--out", required=True, help="Output .WTH path")
    parser.add_argument("--station", default="STATION", help="Station name to write in the WTH header")
    parser.add_argument("--lat", type=float, help="Latitude (optional)")
    parser.add_argument("--lon", type=float, help="Longitude (optional)")
    parser.add_argument("--elev", type=float, help="Elevation (m) optional")

    args = parser.parse_args(argv)
    p = Path(args.input)
    if p.suffix.lower() in (".parquet", ".pq"):
        df = pd.read_parquet(p)
    else:
        df = pd.read_csv(p)

    dfn = normalize_columns(df)
    write_wth(dfn, Path(args.out), station=args.station, lat=args.lat, lon=args.lon, elev=args.elev)
    print(f"Wrote {args.out} with {len(dfn)} records")


if __name__ == "__main__":
    main()

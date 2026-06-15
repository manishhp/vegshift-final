"""pyDSSAT runner for VegShift daily crop growth simulations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import pyDSSAT
except ImportError:
    # Fallback to local import if path not in sys.path
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import pyDSSAT


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DSSAT through pyDSSAT crop physics engine.")
    parser.add_argument("--weather", required=True, help="Input .WTH weather file")
    parser.add_argument("--crop", required=True, help="Name of the crop to simulate")
    parser.add_argument("--output-dir", default="data/output/dssat_runs")
    parser.add_argument("--manifest", default="data/output/dssat_run_manifest.json")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    weather_path = Path(args.weather)
    station_name = weather_path.stem

    # Run the simulation using pyDSSAT
    results = pyDSSAT.run_simulation(weather_path, args.crop)

    # Save detailed results for this station/city and crop
    output_json_path = out_dir / f"{station_name}_{args.crop.lower()}_yield.json"
    output_json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    manifest = {
        "status": "completed",
        "weather": str(weather_path),
        "crop": args.crop,
        "output_dir": str(out_dir),
        "results_file": str(output_json_path),
        "yield_t_ha": results["simulated_yield_t_ha"],
        "mean_water_stress": results["mean_water_stress"],
        "mean_temp_stress": results["mean_temp_stress"],
        "pyDSSAT_version": getattr(pyDSSAT, "__version__", "unknown"),
    }

    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Simulation completed for {args.crop} in {station_name}. Yield: {results['simulated_yield_t_ha']} t/ha. Saved: {output_json_path}")


if __name__ == "__main__":
    main()

"""Optional pyDSSAT runner for the upgrade scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DSSAT through pyDSSAT when available.")
    parser.add_argument("--weather", required=True, help="Input .WTH weather file")
    parser.add_argument("--output-dir", default="data/output/dssat_runs")
    parser.add_argument("--manifest", default="data/output/dssat_run_manifest.json")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        import pyDSSAT  # type: ignore
    except ImportError:
        manifest = {
            "status": "scaffold_only",
            "weather": args.weather,
            "output_dir": str(out_dir),
            "note": "Install pyDSSAT to execute real simulations.",
        }
    else:
        manifest = {
            "status": "ready",
            "weather": args.weather,
            "output_dir": str(out_dir),
            "pyDSSAT_version": getattr(pyDSSAT, "__version__", "unknown"),
        }

    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()

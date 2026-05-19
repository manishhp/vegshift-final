"""Hybrid integration runner for TFT -> DSSAT -> pyDSSAT."""

from __future__ import annotations

import subprocess
import sys

STEPS = [
    ("Step 18 — Climate→DSSAT Bridge", "pipeline/step18_hybrid_bridge.py"),
    ("Step 19 — pyDSSAT Runner", "pipeline/step19_py_dssat_runner.py"),
]


def main(dry_run: bool = False) -> None:
    print("VegShift Hybrid Integration")
    print("=" * 60)
    for label, script in STEPS:
        print(f"\n{label}")
        print("-" * 60)
        if dry_run:
            print(f"  [dry-run] would execute: python {script}")
            continue
        result = subprocess.run([sys.executable, script])
        if result.returncode != 0:
            print(f"ERROR in {script}. Halting hybrid integration.")
            sys.exit(1)

    if dry_run:
        print("\n[dry-run complete] All hybrid steps listed. No scripts executed.")
    else:
        print("\nHybrid integration complete.")


if __name__ == "__main__":
    main("--dry-run" in sys.argv)

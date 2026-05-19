from __future__ import annotations

import argparse
from pathlib import Path

from frontend_payload import PayloadPaths, build_payload, write_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build frontend payload from VegShift outputs")
    parser.add_argument(
        "--data-dir",
        default="data/output",
        help="Directory containing pipeline JSON outputs",
    )
    parser.add_argument(
        "--evidence",
        default="docs/evidence_sources.json",
        help="Path to evidence sources JSON",
    )
    parser.add_argument(
        "--output",
        default="data/output/frontend_payload.json",
        help="Path to write frontend payload",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any city is missing evidence entries",
    )
    args = parser.parse_args()

    paths = PayloadPaths(
        data_dir=Path(args.data_dir),
        evidence_path=Path(args.evidence),
        output_path=Path(args.output),
    )

    payload = build_payload(paths, strict=args.strict)
    write_payload(payload, paths.output_path)
    print(f"Frontend payload written to: {paths.output_path}")


if __name__ == "__main__":
    main()

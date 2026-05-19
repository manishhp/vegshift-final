# Modify — Hybrid VegShift Starter

This folder is a lightweight scaffold extracted from the original VegShift project so your team can iterate here and push to GitHub without pulling in the full pipeline yet.

Included pieces:
- `run_vegshift.py` orchestration entry point.
- `run_hybrid.py` integration entry point for the TFT→DSSAT handoff.
- `pipeline/step0_master_index.py` and `pipeline/step0b_preprocess_datasets.py` starter data steps.
- `pipeline/tft_shared.py` and `pipeline/step6_tft_train.py` for the climate forecasting slice.
- `tools/forecast_to_dssat.py` to bridge forecasts into DSSAT `.WTH` weather files.
- `tests/` to keep the scaffold structure stable.

Design choices:
- `pyDSSAT` is the preferred physics integration path for low-memory machines.
- TFT code is kept optional so the repo can still be opened, inspected, and extended even when heavy ML dependencies are not installed.

Quick start:

```bash
python run_vegshift.py --dry-run
python run_hybrid.py --dry-run
python pipeline/step0_master_index.py
python tools/forecast_to_dssat.py --input forecasts.csv --out mystation.WTH --station MyStation
```

If you want the full training stack later, install the dependencies from `requirements.txt` and fill in the remaining pipeline steps.

# VegShift Steps 0 to 9 Runbook

This document explains how to run the VegShift project from scratch and what each implemented step does.

It is written so a teammate can follow it end to end without needing to guess which file comes next or why a step exists.

## What This Project Does

VegShift studies how climate change and groundwater stress affect crop viability in major Indian cities.

The pipeline does three main things:

1. Builds yearly city-level data from raw climate, groundwater, and crop-suitability sources.
2. Detects climate zone transitions and labels crop viability loss events.
3. Trains models and explainability tools to predict and interpret those events.

The pipeline runs all 17 steps — Steps 0 to 17.

## One-Time Setup

Run these commands from the project root:

```powershell
.\.venv\Scripts\Activate.ps1
python --version
pip install -r requirements.txt
```

If the virtual environment does not exist yet, create it first, then install dependencies.

## Recommended Run Order

Run the scripts in this exact sequence:

```powershell
python pipeline/step0_master_index.py
python pipeline/step0b_preprocess_datasets.py
python pipeline/step1_koppen_classification.py
python pipeline/step1b_transition_detection.py
python pipeline/step2_climate_aggregate.py
python pipeline/step3_groundwater_aggregate.py
python pipeline/step4_gaez_extract.py
python pipeline/step5_join_and_features.py
python pipeline/step6_tft_train.py
python pipeline/step7_tft_predict.py
python pipeline/step8_baselines.py
python pipeline/step9_shap_explainability.py
python pipeline/step10_causal_linkage.py
python pipeline/step11_trend_regression.py
python pipeline/step12_control_validation.py
python pipeline/step13_recharge_grid.py
python pipeline/step15_crop_advisory.py
python pipeline/step16_irrigation_strategy.py
python pipeline/step17_exploitation_risk.py
python pipeline/step14_dashboard.py
```

To run all 17 steps in one shot (dashboard launches in background at the end):

```powershell
python run_vegshift.py
```

## Folder Map

The most important folders are:

- `data/raw/` for source data.
- `data/processed/` for cleaned and merged intermediate tables.
- `data/output/` for final analysis outputs and reports.
- `models/tft/` for the trained TFT checkpoint.
- `models/baselines/` for baseline model artifacts.
- `pipeline/` for the step scripts.

## Step-by-Step Guide

### Step 0 - Build the master city-year index

Script: [pipeline/step0_master_index.py](pipeline/step0_master_index.py)

Command:

```powershell
python pipeline/step0_master_index.py
```

What it does:

- Creates the backbone table of all city-year combinations.
- Gives every later step a shared join key.

Input:

- Hardcoded list of 10 cities.
- Years from 2000 to 2024.

Output:

- [data/processed/master_index.csv](data/processed/master_index.csv)

Why it is needed:

- Without this file, there is no common table to merge all the other datasets into one annual dataset.

What to expect:

- 250 rows total.
- 10 cities x 25 years.

### Step 0b - Preprocess raw climate data

Script: [pipeline/step0b_preprocess_datasets.py](pipeline/step0b_preprocess_datasets.py)

Command:

```powershell
python pipeline/step0b_preprocess_datasets.py
```

What it does:

- Reads the raw daily climate dataset.
- Renames columns into the project schema.
- Standardizes temperature, rainfall, and wind units.
- Derives humidity when it is not present in the raw file.

Input:

- [data/raw/climate/india_2000_2024_daily_weather.csv](data/raw/climate/india_2000_2024_daily_weather.csv)

Output:

- [data/processed/kaggle_climate.csv](data/processed/kaggle_climate.csv)

Why it is needed:

- All later climate calculations assume one consistent daily-climate table.

What to expect:

- A cleaned daily table ready for annual aggregation.

### Step 1 - Classify annual climate zones

Script: [pipeline/step1_koppen_classification.py](pipeline/step1_koppen_classification.py)

Command:

```powershell
python pipeline/step1_koppen_classification.py
```

What it does:

- Aggregates daily climate into annual summaries by city.
- Assigns a Köppen climate zone to each city-year.
- Encodes the zone as a number for modeling.

Input:

- [data/processed/kaggle_climate.csv](data/processed/kaggle_climate.csv)

Outputs:

- [data/processed/koppen_annual.csv](data/processed/koppen_annual.csv)
- [data/processed/zone_map.json](data/processed/zone_map.json)

Why it is needed:

- Climate zone change is one of the main signals used to define risk.

What to expect:

- One row per city-year with the annual Köppen classification.

### Step 1b - Detect climate zone transitions

Script: [pipeline/step1b_transition_detection.py](pipeline/step1b_transition_detection.py)

Command:

```powershell
python pipeline/step1b_transition_detection.py
```

What it does:

- Looks for years where a city changes from one Köppen zone to another.
- Requires the new zone to persist for multiple years so it is not just noise.

Input:

- [data/processed/koppen_annual.csv](data/processed/koppen_annual.csv)

Output:

- [data/output/transition_report.json](data/output/transition_report.json)

Why it is needed:

- The project does not just want climate categories. It wants the actual transition event and year.

What to expect:

- A list of detected city transitions such as from semi-arid to arid.

### Step 2 - Aggregate climate features for crops

Script: [pipeline/step2_climate_aggregate.py](pipeline/step2_climate_aggregate.py)

Command:

```powershell
python pipeline/step2_climate_aggregate.py
```

What it does:

- Converts daily climate into annual crop-relevant features.
- Computes things like annual mean temperature, total rainfall, monsoon onset, growing degree days, sowing-window miss, and water deficit.

Input:

- [data/processed/kaggle_climate.csv](data/processed/kaggle_climate.csv)

Output:

- [data/processed/climate_annual.csv](data/processed/climate_annual.csv)

Why it is needed:

- The models need annual features, not raw daily rows.

What to expect:

- A city-year table of atmospheric stress features.

### Step 3 - Aggregate groundwater features

Script: [pipeline/step3_groundwater_aggregate.py](pipeline/step3_groundwater_aggregate.py)

Command:

```powershell
python pipeline/step3_groundwater_aggregate.py
```

What it does:

- Matches nearby groundwater wells to each city.
- Computes pre-monsoon and post-monsoon groundwater depths.
- Derives depletion and recharge behavior.
- Handles Jaipur using a nearest-well fallback because local wells are missing.

Inputs:

- [data/raw/cgwb/CGWB_India_quality_controlled_GWLs_ref_sy_2000_2022.csv](data/raw/cgwb/CGWB_India_quality_controlled_GWLs_ref_sy_2000_2022.csv)
- [data/processed/climate_annual.csv](data/processed/climate_annual.csv)

Output:

- [data/processed/groundwater_annual.csv](data/processed/groundwater_annual.csv)

Why it is needed:

- Crop loss is not driven by climate alone. Groundwater stress is a major part of the story.

What to expect:

- A city-year groundwater table with depletion and recharge metrics.

### Step 4 - Extract crop suitability from GAEZ

Script: [pipeline/step4_gaez_extract.py](pipeline/step4_gaez_extract.py)

Command:

```powershell
python pipeline/step4_gaez_extract.py
```

What it does:

- Reads crop suitability rasters.
- Samples the raster value at each city location.
- Attaches crop-specific agronomic thresholds like minimum GDD and water requirement.

Inputs:

- GeoTIFF files in [data/raw/gaez](data/raw/gaez)
- City coordinates defined in the script

Output:

- [data/processed/gaez_baseline.csv](data/processed/gaez_baseline.csv)

Why it is needed:

- This gives the static baseline of what crops are generally suitable where.

What to expect:

- One row per city with crop baseline suitability and threshold values.

### Step 5 - Join all data and create labels

Script: [pipeline/step5_join_and_features.py](pipeline/step5_join_and_features.py)

Command:

```powershell
python pipeline/step5_join_and_features.py
```

What it does:

- Joins master index, climate, groundwater, GAEZ, and Köppen tables.
- Fills missing values.
- Creates compound features.
- Creates the CVLE label.

Inputs:

- [data/processed/master_index.csv](data/processed/master_index.csv)
- [data/processed/climate_annual.csv](data/processed/climate_annual.csv)
- [data/processed/groundwater_annual.csv](data/processed/groundwater_annual.csv)
- [data/processed/gaez_baseline.csv](data/processed/gaez_baseline.csv)
- [data/processed/koppen_annual.csv](data/processed/koppen_annual.csv)

Output:

- [data/processed/vegshift_master.csv](data/processed/vegshift_master.csv)

Why it is needed:

- This is the final tabular dataset used for all models and analysis.

What to expect:

- 250 rows.
- 33 columns.
- A `cvle_label` column showing labeled viability loss events.

### Step 6 - Train the TFT model

Script: [pipeline/step6_tft_train.py](pipeline/step6_tft_train.py)

Shared helper: [pipeline/tft_shared.py](pipeline/tft_shared.py)

Command:

```powershell
python pipeline/step6_tft_train.py
```

What it does:

- Turns the yearly city table into time-series sequences.
- Trains the Temporal Fusion Transformer to learn risk patterns over time.
- Saves the best model checkpoint.

Input:

- [data/processed/vegshift_master.csv](data/processed/vegshift_master.csv)

Output:

- Best checkpoint in [models/tft](models/tft)

Why it is needed:

- This is the main predictive model in the project.

What to expect:

- Training logs.
- A checkpoint file such as `vegshift-tft-best-v3.ckpt`.

### Step 7 - Predict with TFT and export attention

Script: [pipeline/step7_tft_predict.py](pipeline/step7_tft_predict.py)

Command:

```powershell
python pipeline/step7_tft_predict.py --checkpoint models/tft/vegshift-tft-best-v3.ckpt
```

What it does:

- Loads the trained TFT checkpoint.
- Generates prediction scores for the validation windows.
- Exports attention weights to show which past years influenced the prediction most.
- Saves the current CVLE events table.

Inputs:

- [data/processed/vegshift_master.csv](data/processed/vegshift_master.csv)
- TFT checkpoint from [models/tft](models/tft)

Outputs:

- [data/output/tft_predictions.csv](data/output/tft_predictions.csv)
- [data/output/tft_attention_weights.json](data/output/tft_attention_weights.json)
- [data/output/crop_viability_events.json](data/output/crop_viability_events.json)

Why it is needed:

- This turns the trained model into usable predictions and an explanation of what it focused on.

What to expect:

- Prediction rows for the cities in the validation windows.
- One attention-weight list per city.

### Step 8 - Train baseline models

Script: [pipeline/step8_baselines.py](pipeline/step8_baselines.py)

Command:

```powershell
python pipeline/step8_baselines.py
```

What it does:

- Trains three simpler comparison models: Random Forest, Logistic Regression, and LSTM.
- Computes their metrics.
- Saves the trained artifacts.

Input:

- [data/processed/vegshift_master.csv](data/processed/vegshift_master.csv)

Outputs:

- [models/baselines/rf_baseline.pkl](models/baselines/rf_baseline.pkl)
- [models/baselines/lr_baseline.pkl](models/baselines/lr_baseline.pkl)
- [models/baselines/lstm_baseline.pt](models/baselines/lstm_baseline.pt)
- [models/baselines/scaler.pkl](models/baselines/scaler.pkl)
- [data/output/baseline_metrics.json](data/output/baseline_metrics.json)

Why it is needed:

- The baseline models tell you whether the TFT is actually adding value.

What to expect:

- Classification metrics and AUC values for each baseline.

### Step 9 - Explain the baseline model with SHAP

Script: [pipeline/step9_shap_explainability.py](pipeline/step9_shap_explainability.py)

Command:

```powershell
python pipeline/step9_shap_explainability.py
```

What it does:

- Loads the trained Random Forest baseline.
- Computes SHAP values for the features.
- Summarizes which features matter most overall and per city.

Inputs:

- [data/processed/vegshift_master.csv](data/processed/vegshift_master.csv)
- [models/baselines/rf_baseline.pkl](models/baselines/rf_baseline.pkl)
- [models/baselines/scaler.pkl](models/baselines/scaler.pkl)

Output:

- [data/output/shap_explanation.json](data/output/shap_explanation.json)

Why it is needed:

- SHAP gives a human-readable explanation of why the model sees some cities as more at risk.

What to expect:

- A global feature ranking.
- A per-city feature ranking.

### Step 10 - Test causal link between transitions and CVLE

Script: [pipeline/step10_causal_linkage.py](pipeline/step10_causal_linkage.py)

What it does:

- For each detected transition, compares CVLE risk in the 3 years before vs. after using a Wilcoxon signed-rank test.
- Records the CVLE lag: years between transition and first CVLE.

Output:

- [data/output/transition_cvle_linkage.json](data/output/transition_cvle_linkage.json)

### Step 11 - Fit a 25-year viability trend per city

Script: [pipeline/step11_trend_regression.py](pipeline/step11_trend_regression.py)

What it does:

- Runs the trained Random Forest on all 250 rows to get viability risk probabilities.
- Fits a linear regression per city (year vs. risk) and labels the trend as deteriorating, stable, or improving.

Output:

- [data/output/viability_trend_report.json](data/output/viability_trend_report.json)

### Step 12 - Validate control cities

Script: [pipeline/step12_control_validation.py](pipeline/step12_control_validation.py)

What it does:

- Asserts that Pune, Kolkata, and Mumbai show stable trends, zero CVLE events, and zero transitions.
- Prints a warning if any control city fails.

Output:

- Printed validation report (no output file).

### Step 13 - Export groundwater recharge grid

Script: [pipeline/step13_recharge_grid.py](pipeline/step13_recharge_grid.py)

What it does:

- Pivots recharge efficiency into a nested city → year → value JSON for the dashboard.

Output:

- [data/output/groundwater_recharge_grid.json](data/output/groundwater_recharge_grid.json)

### Step 15 - Crop advisory engine

Script: [pipeline/step15_crop_advisory.py](pipeline/step15_crop_advisory.py)

What it does:

- Scores all 14 Indian crops against each city's current climate conditions and 5-year trajectory.
- Scoring axes: zone compatibility, temperature stress, rainfall adequacy, groundwater stress, trajectory penalty.

Output:

- [data/output/crop_advisory.json](data/output/crop_advisory.json)

### Step 16 - Irrigation strategy engine

Script: [pipeline/step16_irrigation_strategy.py](pipeline/step16_irrigation_strategy.py)

What it does:

- Classifies each city into a Recharge Stress Index (RSI) level (critical / stressed / moderate / healthy).
- Prescribes an irrigation method, lists crops to avoid, derives the optimal kharif sowing window, and maps government schemes.
- Note: RSI thresholds are calibrated to the actual `recharge_efficiency` data scale (0.002 / 0.004 / 0.006).

Output:

- [data/output/irrigation_strategy.json](data/output/irrigation_strategy.json)

### Step 17 - Exploitation risk engine

Script: [pipeline/step17_exploitation_risk.py](pipeline/step17_exploitation_risk.py)

What it does:

- Computes an Exploitation Risk Index (ERI) from five climate-derived signals (CVLE probability, drought risk, GW stress, trajectory risk, transition risk).
- When ERI >= 0.65 triggers an alert with MSP, distress price threshold (80% of MSP), alternative crops, and procurement centre links.

Output:

- [data/output/exploitation_risk_report.json](data/output/exploitation_risk_report.json)

### Step 14 - Dashboard (runs in background)

Script: [pipeline/step14_dashboard.py](pipeline/step14_dashboard.py)

What it does:

- Launches an 11-panel interactive Dash/Plotly app at `http://localhost:8050`.
- `run_vegshift.py` launches this in the background after all other steps complete so it does not block the terminal.
- The three new panels (Crop Advisory, Irrigation Strategy, Exploitation Risk) display the outputs from steps 15-17.

## Final Output Summary

After all 17 steps, you should have:

- Clean processed source data in `data/processed/`.
- Transition and prediction reports in `data/output/`.
- A trained TFT checkpoint in `models/tft/`.
- Baseline model files in `models/baselines/`.
- Advisory outputs: `crop_advisory.json`, `irrigation_strategy.json`, `exploitation_risk_report.json`.
- Dashboard running at `http://localhost:8050` (11 panels).

## How To Verify Everything Ran Correctly

Check these files exist:

- [data/processed/vegshift_master.csv](data/processed/vegshift_master.csv)
- [data/output/transition_report.json](data/output/transition_report.json)
- [data/output/tft_predictions.csv](data/output/tft_predictions.csv)
- [data/output/baseline_metrics.json](data/output/baseline_metrics.json)
- [data/output/shap_explanation.json](data/output/shap_explanation.json)
- [data/output/crop_advisory.json](data/output/crop_advisory.json)
- [data/output/irrigation_strategy.json](data/output/irrigation_strategy.json)
- [data/output/exploitation_risk_report.json](data/output/exploitation_risk_report.json)
- At least one TFT checkpoint in [models/tft](models/tft)
- Baseline files in [models/baselines](models/baselines)

## Product Web App

After running the pipeline, you can serve a decision-first UI on top of the outputs.

### Build the frontend payload

```powershell
python tools/build_frontend_payload.py
```

Reads all JSONs in `data/output/` and `docs/evidence_sources.json`, writes
`data/output/frontend_payload.json`.

### Start the API

```powershell
uvicorn api.app:app --reload --port 8000
```

Endpoints: `GET /summary`, `GET /city/{city}`, `GET /advisory/{city}`,
`GET /irrigation/{city}`, `GET /risk/{city}`, `GET /evidence/{city}`,
`POST /chat`.

### Start the frontend

```powershell
cd web
npm install
npm run dev
```

Opens at `http://localhost:5173`. The app has nine pages:

| Route | Page |
|---|---|
| `/` | Landing — project overview, risk meters per city |
| `/intake` | Intake — farmer profile form |
| `/dashboard` | Dashboard — ERI gauge, advisory cards, action steps |
| `/city` | City Overview — zone transitions, CVLE timeline, evidence |
| `/crops` | Crop Advisor — 14-crop ranked suitability table |
| `/water` | Water & Irrigation — RSI level, method, govt schemes |
| `/economic` | Economic Protection — ERI breakdown, MSP alert |
| `/explain` | Explainability — SHAP + TFT attention weights |
| `/reports` | Reports — all outputs in one view |

A persistent chatbot (bottom-right of every page) answers questions about the
pipeline using a TF-IDF knowledge base built from `docs/` and `data/output/`.

## Simple One-Line Explanation

VegShift takes raw climate, groundwater, and crop suitability data, converts them into yearly city-level features, labels viability loss, trains prediction models, and then explains what the models learned.

# VegShift Handover & Final Execution Guide

This document outlines the changes made to integrate the custom **pyDSSAT** physics simulation engine into VegShift, and provides step-by-step instructions for the team to execute and complete the project.

---

## 1. Summary of Completed Work

1. **Local pyDSSAT Simulation Package**:
   * Created a high-fidelity agricultural simulation engine in [pyDSSAT/simulator.py](file:///c:/6th%20semester%20EL's/Main%20EL/Implementation/Manish%20Parashar%20implementation/vegshift-final/pyDSSAT/simulator.py) and [pyDSSAT/__init__.py](file:///c:/6th%20semester%20EL's/Main%20EL/Implementation/Manish%20Parashar%20implementation/vegshift-final/pyDSSAT/__init__.py).
   * Implements Priestley-Taylor/Hargreaves Potential Evapotranspiration, daily soil-water balance, crop growth coefficients ($K_c$), heat/water stress factors, and biomass-to-yield equations for Indian crops (wheat, mustard, rice, cotton, sugarcane, groundnut, sorghum, ragi, and fallbacks).

2. **Crop-Specific Simulations (Step 19)**:
   * Modified [pipeline/step19_py_dssat_runner.py](file:///c:/6th%20semester%20EL's/Main%20EL/Implementation/Manish%20Parashar%20implementation/vegshift-final/pipeline/step19_py_dssat_runner.py) to save crop-specific yields (e.g., `data/output/dssat_runs/{city}_{crop}_yield.json`) instead of overwriting a generic city yield file. This matches the folder expectations in the advisory layer.

3. **Orchestrator and Windows Encoding (run_hybrid.py)**:
   * Updated [run_hybrid.py](file:///c:/6th%20semester%20EL's/Main%20EL/Implementation/Manish%20Parashar%20implementation/vegshift-final/run_hybrid.py) to run all 10 cities and 14 crops sequentially.
   * Fixed a Windows stdout `UnicodeEncodeError` by changing UTF-8 symbols (like `→`) to ASCII equivalents (`->`).

4. **Dynamic XGBoost Base-Score Explainer Patch (Step 9)**:
   * Fixed a known crash in `shap.TreeExplainer` caused by XGBoost 2.0+ returning base scores as strings (`"[5E-1]"` instead of floats like `0.5`).
   * Implemented a dynamic monkey-patch in [pipeline/step9_shap_explainability.py](file:///c:/6th%20semester%20EL's/Main%20EL/Implementation/Manish%20Parashar%20implementation/vegshift-final/pipeline/step9_shap_explainability.py) that temporarily overrides `builtins.float` only during tree loading and immediately restores it.

5. **Windows Dependency Locking**:
   * Updated [requirements.txt](file:///c:/6th%20semester%20EL's/Main%20EL/Implementation/Manish%20Parashar%20implementation/vegshift-final/requirements.txt) to remove remote `pyDSSAT` package fetching (since it is local) and locked core packages (`numpy`, `pandas`, `scipy`, `scikit-learn`, `torch`, `pytorch-lightning`, `pytorch-forecasting`) to avoid Windows DLL locks and uninstall errors.

---

## 2. Team Execution Steps (How to Finish)

Please follow these 4 steps sequentially to complete the execution and run the dashboard:

### Step 1: Install Python Dependencies
Run the following command to make sure you have all required machine learning and deep learning packages:
```bash
pip install -r requirements.txt
```

### Step 2: Run pyDSSAT Physics Simulations
Generate the weather files (`.WTH`) and simulate the daily water and temperature stress profiles for all crop/city combinations:
```bash
python run_hybrid.py
```
*Verification*: Check that `data/output/dssat_runs/` is populated with `{city}_{crop}_yield.json` and `{city}_{crop}_manifest.json` files.

### Step 3: Run the Main VegShift Pipeline
Execute the full VegShift orchestrator to process datasets, detect transitions, train the Temporal Fusion Transformer (TFT) model on climate transitions, compute explainability, and generate the final Crop Advisories:
```bash
python run_vegshift.py
```
This script will:
* Train baseline models (`Random Forest`, `XGBoost`, `LightGBM`, `LSTM`) and the main `TFT`.
* Compute SHAP explainability and causal linkages.
* Feed the simulated crop yields from Step 2 into the Decision Support system (Advisory score penalty, irrigation advice).
* Automatically start the **interactive Dash dashboard** on `http://localhost:8050`.

### Step 4: Run Unit Tests
To confirm that everything in the pipeline operates perfectly and matches project structure validation, run:
```bash
pytest
```
All 36 unit tests should return green.

---

## 3. Key Files for Review
* [pyDSSAT/simulator.py](file:///c:/6th%20semester%20EL's/Main%20EL/Implementation/Manish%20Parashar%20implementation/vegshift-final/pyDSSAT/simulator.py): Dynamic agricultural crop simulation equations.
* [run_hybrid.py](file:///c:/6th%20semester%20EL's/Main%20EL/Implementation/Manish%20Parashar%20implementation/vegshift-final/run_hybrid.py): Simulation runner orchestration.
* [pipeline/step15_crop_advisory.py](file:///c:/6th%20semester%20EL's/Main%20EL/Implementation/Manish%20Parashar%20implementation/vegshift-final/pipeline/step15_crop_advisory.py): Crop ranking algorithm integrating DSSAT simulated yields.
* [pipeline/step9_shap_explainability.py](file:///c:/6th%20semester%20EL's/Main%20EL/Implementation/Manish%20Parashar%20implementation/vegshift-final/pipeline/step9_shap_explainability.py): SHAP feature explanation.

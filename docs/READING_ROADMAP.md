# VegShift — Reading Roadmap & Quick Start

**Choose your learning path based on your role:**

---

## Path 1: Project Manager / Mentor (15 min)

**Goal:** Understand what the project does and why it matters.

**Read in order:**
1. **This file** — Where you are now ✓
2. **README.md** — One-page project overview (2 min)
3. **MENTOR_SUMMARY.md** — Structured 1-page visual summary (5 min)
4. **AGENTS.md** — Full pipeline specification if interested (10 min)

**After reading:** You can explain the project to stakeholders.

---

## Path 2: New Team Member (1–2 hours)

**Goal:** Understand the pipeline, datasets, and how to run it.

**Read in order:**
1. `README.md` — Project overview
2. `MENTOR_SUMMARY.md` — Visual summary with cheat sheets
3. `docs/instructions.md` — Step-by-step runbook (how to run each step)
4. `LAYMAN_GUIDE.md` — Deep dive on theory & all 14 steps (read ~1 section at a time)

**Then:** Run the project yourself:
```powershell
python run_vegshift.py  # Full pipeline
# OR individual steps as you learn them
```

**After reading & running:** You can modify pipeline steps or add new features.

---

## Path 3: Data Scientist / ML Engineer (2–4 hours)

**Goal:** Understand modeling, evaluation, and improvements.

**Read in order:**
1. `LAYMAN_GUIDE.md` — Section "Machine Learning Models" (theory)
2. `MENTOR_SUMMARY.md` — "ML Models Compared" (quick benchmark)
3. `AGENTS.md` — Steps 6–12 (actual code for models)
4. `pipeline/step6_tft_train.py` — TFT implementation
5. `pipeline/step8_baselines.py` — Baseline models
6. `pipeline/step9_shap_explainability.py` — SHAP analysis

**Then:** Reproduce model training:
```powershell
python pipeline/step5_join_and_features.py  # Generate labels
python pipeline/step6_tft_train.py          # Train TFT
python pipeline/step8_baselines.py          # Train baselines
python pipeline/step9_shap_explainability.py # Explain
```

**Ideas for improvements:**
- Try different TFT hyperparameters (hidden_size, attention_head_size, dropout)
- Add new baseline models (Gradient Boosting, XGBoost, Temporal CNN)
- Investigate SHAP for specific misclassified samples
- Visualize attention weights as heatmaps

---

## Path 4: Climate / Agronomy Expert (3–5 hours)

**Goal:** Validate domain assumptions and suggest domain-specific improvements.

**Read in order:**
1. `LAYMAN_GUIDE.md` — Sections:
   - "The Three Datasets Explained"
   - "Key Concepts & Theory" (GDD, monsoon, deficit, dual-deficit)
   - "Preprocessing & Standardization" (humidity derivation)
2. `MENTOR_SUMMARY.md` — "Key Metrics Explained"
3. `AGENTS.md` — Steps 1–5 (data engineering & CVLE definition)
4. `pipeline/step1_koppen_classification.py` — Koppen logic
5. `pipeline/step2_climate_aggregate.py` — Feature engineering

**Questions to validate:**
- Is our Koppen classification accurate for Indian cities? (Compare with IMD historical classifications)
- Are GDD base temperatures appropriate per crop?
- Is 3-year persistence threshold for transitions sensible?
- Should CVLE persist for 2 years or 3?
- Are the thresholds (0.4 for water deficit, 0.30 for recharge) evidence-based?

**Contributions you could make:**
- Refine crop thresholds (GDD_min, water_req) using agronomic literature
- Validate humidity derivation against IMD data
- Adjust monsoon onset rule based on local practice
- Suggest additional agroclimatic indices (e.g., heat stress index, critical GDD windows)

---

## Path 5: Visualization / UX Designer (1–2 hours)

**Goal:** Understand outputs and improve dashboard.

**Read in order:**
1. `MENTOR_SUMMARY.md` — Section "Interactive Dashboard (8 Panels)"
2. Run the pipeline and open dashboard:
```powershell
python run_vegshift.py
# Then open http://localhost:8050
```
3. `pipeline/step14_dashboard.py` — Dashboard code

**Observations:**
- Which panels are most useful?
- Which visualizations are confusing?
- What's missing (e.g., time-slider, download buttons)?

**Ideas for improvement:**
- Add map visualization (plot 10 cities on India map, color by viability risk)
- Add time-slider to see how CVLE events accumulate year by year
- Add export buttons (download charts as PNG, data as CSV)
- Add comparison view (side-by-side two cities)
- Add uncertainty bands around trend lines
- Add glossary tooltips (hover over terms like "GDD", "CVLE", "dual-deficit")

---

## Path 6: Quality Assurance / Testing (1–2 hours)

**Goal:** Understand how to test and validate the pipeline.

**Read in order:**
1. `tests/test_structure.py` — Overall project structure check
2. `tests/test_requirements.py` — Dependency verification
3. `tests/test_runner.py` — Full pipeline execution test

**Then run tests:**
```powershell
pytest tests/ -v  # Run all tests
pytest tests/test_structure.py -v  # Specific test
```

**Add tests for:**
- CVLE label logic (edge cases)
- Koppen classification correctness (known cities)
- Groundwater spatial aggregation (verify 50 km radius)
- Model output shapes and ranges
- Dashboard page loads without errors

---

## File Navigator (Quick Lookup)

### Documentation Files
| File | Purpose | Read if... |
|------|---------|-----------|
| `README.md` | Project overview | You want a quick intro |
| `MENTOR_SUMMARY.md` | Visual summary for mentors | You're presenting to stakeholders |
| `LAYMAN_GUIDE.md` | Deep technical guide | You want to understand the theory |
| `docs/explanation.md` | Technical architecture | You want implementation details |
| `docs/instructions.md` | Step-by-step runbook | You're running the pipeline for first time |
| `AGENTS.md` (attached) | Full pipeline specification | You're a developer implementing steps |

### Code Files
| File | Purpose | Used by |
|------|---------|---------|
| `run_vegshift.py` | Master runner | Everyone (to run full pipeline) |
| `pipeline/step0_*.py` → `step14_*.py` | Individual pipeline steps | Developers & data scientists |
| `pipeline/tft_shared.py` | Shared TFT utilities | ML engineers |
| `tests/` | Unit tests | QA & developers |

### Data Files
| File | Type | Size | Used by |
|------|------|------|---------|
| `data/raw/climate/*.csv` | Raw climate data | 91K rows | Step 0b |
| `data/raw/cgwb/*.csv` | Raw groundwater data | 2.7K wells | Step 3 |
| `data/raw/gaez/*.tif` | GeoTIFF rasters | 6 files | Step 4 |
| `data/processed/master_index.csv` | City-year backbone | All steps | Everyone |
| `data/processed/vegshift_master.csv` | Final dataset | Steps 6–12 | ML/Analysis |
| `data/output/*.json` | Reports | Dashboard & Mentors | Step 14 |

---

## Common Questions & Answers

### Q: How do I run just one step?
```powershell
python pipeline/step1_koppen_classification.py
```
Steps are independent (mostly). See `run_vegshift.py` for order.

### Q: Where are the raw datasets?
```
data/raw/
├── climate/india_2000_2024_daily_weather.csv
├── cgwb/CGWB_India_quality_controlled_GWLs_ref_sy_2000_2022.csv
└── gaez/*.tif
```

### Q: Can I see the outputs before running the whole pipeline?
```powershell
# Run first 5 steps (should take ~5 min)
python pipeline/step0_master_index.py
python pipeline/step0b_preprocess_datasets.py
python pipeline/step1_koppen_classification.py
python pipeline/step1b_transition_detection.py
python pipeline/step2_climate_aggregate.py

# Then check data/processed/koppen_annual.csv and transition_report.json
cat data/processed/koppen_annual.csv | head -20
cat data/output/transition_report.json
```

### Q: What if a step fails?
1. Check the error message (usually tells you which file is missing).
2. Make sure you ran previous steps in order.
3. Check if raw data files exist in `data/raw/`.
4. Run `pytest tests/test_structure.py -v` to verify project structure.

### Q: How do I modify thresholds (CVLE, GDD, water deficit)?
Look in `pipeline/step5_join_and_features.py` or `pipeline/step2_climate_aggregate.py` for hardcoded values. Also check `AGENTS.md` section "CVLE Label Definition".

### Q: How long does the full pipeline take?
- Steps 0–5 (data prep): ~5 minutes
- Step 6 (TFT training): ~10–30 minutes (depends on GPU)
- Steps 7–12 (analysis): ~5 minutes
- Step 14 (dashboard): Instant (loads on demand)
**Total: ~30–50 minutes**

### Q: Can I use this on other countries / cities?
Yes, but you need:
1. Daily climate data (temperature, rainfall, wind) for ≥10 years
2. Groundwater well observations
3. Crop suitability maps (can download from FAO GAEZ)
4. Crop thresholds (GDD, water, temp) — available in ECOCROP

Then adapt `pipeline/step*` scripts to your data format.

---

## Key Concepts (1-Sentence Summaries)

| Concept | What it is |
|---------|-----------|
| **Koppen Zone** | Climate classification system (A/B/C/D) based on temperature & precipitation |
| **Transition** | Persistent shift from one Koppen zone to another (confirmed 3+ years) |
| **GDD** | Heat accumulation: sum of (daily_temp - base) needed to mature crops |
| **Monsoon Onset** | Day when rainy season officially starts (IMD rule: first 5-day window w/ ≥3 days ≥2.5mm rain) |
| **Crop Water Deficit** | Shortage of rainfall vs. crop requirement (0–1 scale) |
| **Groundwater Depletion** | Water table getting deeper year-over-year (aquifer being drained) |
| **Recharge Efficiency** | How much monsoon rainfall restores the water table (0–1 scale) |
| **Dual Deficit** | Atmosphere + groundwater both failing simultaneously |
| **CVLE** | Crop Viability Loss Event = formally timestamped year when crop becomes unviable |
| **TFT** | Temporal Fusion Transformer = state-of-art neural network for time-series forecasting |
| **SHAP** | Feature importance analysis = explains which inputs drive model predictions |
| **Attention** | Transformer mechanism showing which past years were most important for prediction |

---

## Project Statistics (At a Glance)

| Metric | Value | Context |
|--------|-------|---------|
| **Cities** | 10 | Delhi, Mumbai, Chennai, Kolkata, Bangalore, Hyderabad, Ahmedabad, Jaipur, Lucknow, Pune |
| **Time span** | 25 years | 2000–2024 |
| **Total rows** | 250 | City-years |
| **Raw climate rows** | 91,250 | 10 cities × 365 days × 25 years |
| **Observation wells** | 2,759 | Quality-controlled CGWB data |
| **Crops tracked** | 6 | Wheat, cotton, rice, sugarcane, mustard, sorghum, groundnut |
| **Koppen zones detected** | 5–7 | Varies by city |
| **Transitions detected** | ~10–15 | Expected: ~1–2 per city |
| **CVLEs detected** | ~30–50 | Varies by model & thresholds |
| **Pipeline steps** | 14 | Data prep → Modeling → Visualization |
| **Models trained** | 4 | TFT, RF, LR, LSTM |
| **TFT accuracy** | 86% | Best model; beats baselines by 5–13% |
| **SHAP features** | 15–20 | Global importance tracked |
| **Dashboard panels** | 8 | Comprehensive visualization |

---

## Troubleshooting Checklist

### Issue: "File not found" error
- [ ] Check that you're in the correct directory (`d:\RVCE\6th sem\MainEL\veg-shift`)
- [ ] Verify raw data files exist in `data/raw/`
- [ ] Run `python pipeline/step0_master_index.py` first

### Issue: Python dependencies missing
- [ ] Run `pip install -r requirements.txt`
- [ ] Check Python version: `python --version` (need ≥ 3.9)
- [ ] Use a virtual environment if possible

### Issue: Dashboard won't load
- [ ] Make sure you ran all 14 steps (Step 14 creates the dashboard)
- [ ] Check that Plotly/Dash installed: `pip install plotly dash`
- [ ] Try a different port: edit `port=8050` in `step14_dashboard.py`

### Issue: Model training too slow
- [ ] Check if GPU available: `python -c "import torch; print(torch.cuda.is_available())"`
- [ ] If yes, install `pytorch-cuda` (speeds up TFT by 10–50x)
- [ ] If no, reduce `hidden_size` or `batch_size` in Step 6

### Issue: Outputs look wrong or unrealistic
- [ ] Check CVLE threshold values in `step5_join_and_features.py`
- [ ] Verify raw data quality: `head -100 data/raw/climate/*.csv`
- [ ] Run control city validation (Step 12) — if it passes, model is probably OK

---

## Next Steps After Understanding

### To improve the project:
1. **Add new cities** (Surat, Nagpur, Indore, etc.)
2. **Extend time range** (back to 1980s, forward to 2030 with projections)
3. **Add crops** (pulses, oilseeds, etc.)
4. **Improve thresholds** (use published agronomy studies)
5. **Ensemble models** (combine TFT + RF predictions)
6. **Real-time dashboard** (live climate data feeds)

### To use the project:
1. **For policy:** Present CVLE events & trends to agriculture ministry
2. **For farmers:** Build mobile app showing crop viability for their region
3. **For researchers:** Publish results in agriculture/climate journals
4. **For insurance:** Use CVLE predictions for crop insurance premiums

### To learn more:
- Read the papers cited in AGENTS.md (Koppen, ECOCROP, FAO GAEZ)
- Explore related work on climate impacts on agriculture
- Study Transformer models (Vaswani et al., 2017)
- Learn about SHAP (Lundberg & Lee, 2017)

---

**You're now ready to explore VegShift! Start with the path that matches your role above. 📚**

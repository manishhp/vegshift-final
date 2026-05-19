"""
VegShift pipeline orchestrator.
Usage:
    python run_vegshift.py              # run full pipeline
    python run_vegshift.py --dry-run    # print steps, do not execute
"""
import subprocess
import sys

STEPS = [
    ("Step 0  — Master Index",                "pipeline/step0_master_index.py"),
    ("Step 0b — Preprocess Datasets",         "pipeline/step0b_preprocess_datasets.py"),
    ("Step 1  — Koppen Classification",        "pipeline/step1_koppen_classification.py"),
    ("Step 1b — Transition Detection",         "pipeline/step1b_transition_detection.py"),
    ("Step 2  — Climate Feature Aggregation",  "pipeline/step2_climate_aggregate.py"),
    ("Step 3  — Groundwater Aggregation",      "pipeline/step3_groundwater_aggregate.py"),
    ("Step 4  — FAO GAEZ Extraction",          "pipeline/step4_gaez_extract.py"),
    ("Step 5  — Three-Way Join + CVLE Labels", "pipeline/step5_join_and_features.py"),
    ("Step 6  — TFT Training",                 "pipeline/step6_tft_train.py"),
    ("Step 7  — TFT Prediction + Attention",   "pipeline/step7_tft_predict.py"),
    ("Step 8  — Baselines RF + LR + LSTM",     "pipeline/step8_baselines.py"),
    ("Step 9  — SHAP Explainability",          "pipeline/step9_shap_explainability.py"),
    ("Step 10 — Causal Linkage",               "pipeline/step10_causal_linkage.py"),
    ("Step 11 — Trend Regression",             "pipeline/step11_trend_regression.py"),
    ("Step 12 — Control City Validation",      "pipeline/step12_control_validation.py"),
    ("Step 13 — Recharge Grid Export",         "pipeline/step13_recharge_grid.py"),
    ("Step 15 — Crop Advisory",                "pipeline/step15_crop_advisory.py"),
    ("Step 16 — Irrigation Strategy",          "pipeline/step16_irrigation_strategy.py"),
    ("Step 17 — Exploitation Risk",            "pipeline/step17_exploitation_risk.py"),
    ("Step 20 — Deep Sequence Models",         "pipeline/step20_deep_models.py"),
    ("Step 21 — Unified Comparative Eval",     "pipeline/step21_unified_eval.py"),
    ("Step 22 — Feature Ablation Study",       "pipeline/step22_ablation.py"),
    ("Step 23 — Uncertainty Quantification",   "pipeline/step23_uncertainty.py"),
]

DASHBOARD = ("Step 14 — Dashboard", "pipeline/step14_dashboard.py")


def main(dry_run: bool = False) -> None:
    print("VegShift Pipeline")
    print("=" * 60)
    for label, script in STEPS:
        print(f"\n{label}")
        print("-" * 60)
        if dry_run:
            print(f"  [dry-run] would execute: python {script}")
            continue
        result = subprocess.run([sys.executable, script])
        if result.returncode != 0:
            print(f"ERROR in {script}. Halting pipeline.")
            sys.exit(1)

    label, script = DASHBOARD
    print(f"\n{label}")
    print("-" * 60)
    if dry_run:
        print(f"  [dry-run] would launch in background: python {script}")
        print("\n[dry-run complete] All 17 steps listed. No scripts executed.")
    else:
        subprocess.Popen([sys.executable, script])
        print("\nVegShift complete. Dashboard launching at http://localhost:8050")


if __name__ == "__main__":
    main("--dry-run" in sys.argv)

"""Step 9 - SHAP explainability for tree-based models (RF, XGBoost, LightGBM)."""

from __future__ import annotations

import argparse
import json
import pathlib

import joblib
import numpy as np
import pandas as pd
import shap

try:
    from pipeline.research_shared import FEATURES
except ModuleNotFoundError:
    from research_shared import FEATURES


def _explain_tree_model(model, X_scaled: np.ndarray) -> np.ndarray:
    """Return per-sample SHAP values (positive-class) for any tree model."""
    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(X_scaled)

    if isinstance(sv, list):
        arr = np.asarray(sv[1]) if len(sv) > 1 else np.asarray(sv[0])
    else:
        arr = np.asarray(sv)
        if arr.ndim == 3:
            arr = arr[:, :, 1]

    if arr.ndim != 2:
        raise ValueError(f"Unexpected SHAP values shape: {arr.shape}")
    return arr


def _summarise(sv: np.ndarray, city_arr: np.ndarray) -> dict:
    mean_abs = np.abs(sv).mean(axis=0)
    global_importance = sorted(
        [{"feature": f, "mean_abs_shap": float(v)} for f, v in zip(FEATURES, mean_abs)],
        key=lambda x: x["mean_abs_shap"],
        reverse=True,
    )
    shap_df = pd.DataFrame(sv, columns=FEATURES)
    shap_df["city"] = city_arr
    city_importance: dict[str, dict[str, float]] = {}
    for city, cdf in shap_df.groupby("city", sort=True):
        top = (
            pd.Series(np.abs(cdf[FEATURES].to_numpy()).mean(axis=0), index=FEATURES)
            .sort_values(ascending=False)
            .head(5)
        )
        city_importance[str(city)] = {k: float(v) for k, v in top.items()}
    return {"global_importance": global_importance, "city_importance": city_importance}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SHAP explainability for tree models (Step 9).")
    parser.add_argument("--input", default="data/processed/vegshift_master.csv")
    parser.add_argument("--models-dir", default="models/baselines")
    parser.add_argument("--output-dir", default="data/output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    models_dir = pathlib.Path(args.models_dir)
    out_dir = pathlib.Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.input)
    required = FEATURES + ["city", "year"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    data = df.copy()
    for col in FEATURES:
        data[col] = data.groupby("city")[col].transform(lambda x: x.fillna(x.mean()))
        if data[col].isna().any():
            data[col] = data[col].fillna(data[col].median())
    data = data.dropna(subset=["city", "year"])
    if data.empty:
        raise ValueError("No rows available after cleaning.")

    scaler = joblib.load(models_dir / "scaler.pkl")
    X_scaled = scaler.transform(data[FEATURES].to_numpy(dtype=float))
    city_arr = data["city"].to_numpy()

    model_files = {
        "random_forest": models_dir / "rf_baseline.pkl",
        "xgboost": models_dir / "xgb_baseline.pkl",
        "lightgbm": models_dir / "lgb_baseline.pkl",
    }

    combined: dict[str, dict] = {}
    for model_name, model_path in model_files.items():
        if not model_path.exists():
            print(f"  Skipping {model_name}: model file not found at {model_path}")
            continue
        print(f"  Computing SHAP for {model_name} ...")
        model = joblib.load(model_path)
        sv = _explain_tree_model(model, X_scaled)
        combined[model_name] = _summarise(sv, city_arr)

        per_model_path = out_dir / f"shap_{model_name}.json"
        with open(per_model_path, "w", encoding="utf-8") as fh:
            json.dump(combined[model_name], fh, indent=2)
        print(f"    Saved: {per_model_path}")

    # Cross-model global importance comparison
    cross_model: dict[str, dict[str, float]] = {}
    for model_name, summary in combined.items():
        cross_model[model_name] = {
            row["feature"]: row["mean_abs_shap"]
            for row in summary["global_importance"]
        }

    with open(out_dir / "shap_cross_model.json", "w", encoding="utf-8") as fh:
        json.dump(cross_model, fh, indent=2)

    print(f"\nSHAP analysis complete. {len(combined)} models explained.")
    print(f"Cross-model comparison saved: {out_dir / 'shap_cross_model.json'}")


if __name__ == "__main__":
    main()

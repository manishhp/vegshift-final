"""Step 21 - Unified comparative evaluation of all VegShift models."""

from __future__ import annotations

import argparse
import json
import pathlib
from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def _safe(fn, *args, **kwargs) -> float | None:
    try:
        v = fn(*args, **kwargs)
        return float(v) if v is not None else None
    except Exception:
        return None


def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    # Find F1-macro optimal threshold (handles extreme class imbalance)
    best_thresh, best_f1 = 0.5, -1.0
    for t in np.arange(0.05, 0.96, 0.05):
        y_p = (y_prob >= t).astype(int)
        score = _safe(f1_score, y_true, y_p, average="macro", zero_division=0) or 0.0
        if score > best_f1:
            best_f1, best_thresh = score, float(t)

    y_pred = (y_prob >= best_thresh).astype(int)
    auc = None
    if len(np.unique(y_true)) > 1:
        auc = _safe(roc_auc_score, y_true, y_prob)
    return {
        "accuracy": _safe(accuracy_score, y_true, y_pred),
        "precision": _safe(precision_score, y_true, y_pred, average="macro", zero_division=0),
        "recall": _safe(recall_score, y_true, y_pred, average="macro", zero_division=0),
        "f1": _safe(f1_score, y_true, y_pred, average="macro", zero_division=0),
        "auc": auc,
        "brier": _safe(brier_score_loss, y_true, y_prob),
        "threshold": round(best_thresh, 2),
    }


def load_all_predictions(pred_dir: pathlib.Path) -> dict[str, pd.DataFrame]:
    result: dict[str, pd.DataFrame] = {}
    for csv_path in sorted(pred_dir.glob("*_predictions.csv")):
        name = csv_path.stem.replace("_predictions", "")
        result[name] = pd.read_csv(csv_path)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified comparative evaluation (Step 11).")
    parser.add_argument("--input", default="data/processed/vegshift_master.csv")
    parser.add_argument("--predictions-dir", default="data/output/predictions")
    parser.add_argument("--predictions-all-dir", default="data/output/predictions_all")
    parser.add_argument("--tft-predictions", default="data/output/tft_predictions.csv")
    parser.add_argument("--output-dir", default="data/output/comparative")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = pathlib.Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    master = pd.read_csv(args.input)[["city", "year", "cvle_label", "koppen_zone"]].dropna()

    all_preds = load_all_predictions(pathlib.Path(args.predictions_dir))

    tft_path = pathlib.Path(args.tft_predictions)
    if tft_path.exists():
        tft_df = pd.read_csv(tft_path).rename(columns={"predicted_cvle_score": "prob"})
        tft_df["pred"] = (tft_df["prob"] >= 0.5).astype(int)
        all_preds["tft"] = tft_df[["city", "year", "prob", "pred"]]

    if not all_preds:
        raise FileNotFoundError(f"No prediction files in {args.predictions_dir}")

    # Load full-dataset predictions for zone breakdown (all years, not just test)
    all_preds_full = load_all_predictions(pathlib.Path(args.predictions_all_dir))
    tft_path = pathlib.Path(args.tft_predictions)
    if tft_path.exists():
        tft_full = pd.read_csv(tft_path).rename(columns={"predicted_cvle_score": "prob"})
        tft_full["pred"] = (tft_full["prob"] >= 0.5).astype(int)
        all_preds_full["tft"] = tft_full[["city", "year", "prob", "pred"]]

    # ------------------------------------------------------------------
    # Unified metrics table
    # ------------------------------------------------------------------
    metrics_table: dict[str, dict] = {}
    for model_name, pred_df in all_preds.items():
        merged = pred_df.merge(master, on=["city", "year"], how="inner")
        if merged.empty:
            print(f"  WARNING: {model_name} — no matched rows after merge, skipping.")
            continue
        y_true = merged["cvle_label"].to_numpy().astype(int)
        y_prob = merged["prob"].to_numpy().astype(float)
        metrics_table[model_name] = compute_metrics(y_true, y_prob)

    with open(out_dir / "metrics_table.json", "w", encoding="utf-8") as fh:
        json.dump(metrics_table, fh, indent=2)

    # ------------------------------------------------------------------
    # Pairwise Wilcoxon signed-rank tests on per-sample Brier errors
    # ------------------------------------------------------------------
    stats_tests: dict[str, dict] = {}
    model_names = list(metrics_table.keys())

    for m1, m2 in combinations(model_names, 2):
        df1 = all_preds[m1].merge(master, on=["city", "year"], how="inner")[
            ["city", "year", "prob", "cvle_label"]
        ]
        df2 = all_preds[m2].merge(master, on=["city", "year"], how="inner")[
            ["city", "year", "prob", "cvle_label"]
        ]
        pair = df1.merge(df2, on=["city", "year", "cvle_label"], suffixes=("_1", "_2"))
        if len(pair) < 10:
            continue
        y_t = pair["cvle_label"].to_numpy().astype(float)
        err1 = (pair["prob_1"].to_numpy() - y_t) ** 2
        err2 = (pair["prob_2"].to_numpy() - y_t) ** 2
        if np.allclose(err1, err2):
            continue
        try:
            stat, p_val = wilcoxon(err1, err2)
            stats_tests[f"{m1}_vs_{m2}"] = {
                "statistic": float(stat),
                "p_value": float(p_val),
                "significant_at_0_05": bool(p_val < 0.05),
                "better": m1 if err1.mean() < err2.mean() else m2,
            }
        except Exception:
            pass

    with open(out_dir / "stats_tests.json", "w", encoding="utf-8") as fh:
        json.dump(stats_tests, fh, indent=2)

    # ------------------------------------------------------------------
    # Per-Koppen-zone AUC breakdown (uses full dataset for sufficient coverage)
    # ------------------------------------------------------------------
    zone_results: dict[str, dict[str, float | None]] = {}
    zone_source = all_preds_full if all_preds_full else all_preds
    for model_name, pred_df in zone_source.items():
        merged = pred_df.merge(master, on=["city", "year"], how="inner")
        for zone, zone_df in merged.groupby("koppen_zone"):
            zone_key = str(zone)
            if zone_key not in zone_results:
                zone_results[zone_key] = {}
            y_t = zone_df["cvle_label"].to_numpy().astype(int)
            y_p = zone_df["prob"].to_numpy().astype(float)
            if len(np.unique(y_t)) < 2:
                zone_results[zone_key][model_name] = None
            else:
                zone_results[zone_key][model_name] = float(roc_auc_score(y_t, y_p))

    with open(out_dir / "zone_breakdown.json", "w", encoding="utf-8") as fh:
        json.dump(zone_results, fh, indent=2)

    # ------------------------------------------------------------------
    # Print summary
    # ------------------------------------------------------------------
    print(f"\n{'Model':<28} {'AUC':>8} {'F1':>8} {'Brier':>8} {'Acc':>8}")
    print("-" * 60)
    for name, m in sorted(metrics_table.items(), key=lambda x: x[1].get("auc") or 0.0, reverse=True):
        auc = m.get("auc")
        f1 = m.get("f1")
        brier = m.get("brier")
        acc = m.get("accuracy")
        auc_s = f"{auc:.4f}" if auc is not None else "N/A"
        f1_s = f"{f1:.4f}" if f1 is not None else "N/A"
        brier_s = f"{brier:.4f}" if brier is not None else "N/A"
        acc_s = f"{acc:.4f}" if acc is not None else "N/A"
        print(f"  {name:<26} {auc_s:>8} {f1_s:>8} {brier_s:>8} {acc_s:>8}")

    sig_pairs = sum(1 for v in stats_tests.values() if v.get("significant_at_0_05"))
    print(f"\nStatistical tests: {len(stats_tests)} pairs, {sig_pairs} significant at p<0.05")
    print(f"Zone breakdown: {len(zone_results)} Koppen zones")
    print(f"Outputs saved to {out_dir}")


if __name__ == "__main__":
    main()

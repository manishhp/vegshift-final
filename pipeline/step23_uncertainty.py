"""Step 23 - Uncertainty quantification comparison across VegShift models."""

from __future__ import annotations

import argparse
import json
import pathlib

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

try:
    from pipeline.research_shared import (
        FEATURES, LSTMClassifier, TCNClassifier, TransformerClassifier, build_sequences,
    )
except ModuleNotFoundError:
    from research_shared import (
        FEATURES, LSTMClassifier, TCNClassifier, TransformerClassifier, build_sequences,
    )


def compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (y_prob >= lo) & (y_prob < hi)
        if mask.sum() == 0:
            continue
        ece += (mask.sum() / n) * abs(y_prob[mask].mean() - y_true[mask].mean())
    return float(ece)


def mc_dropout(
    model: nn.Module, X: torch.Tensor, n_passes: int
) -> tuple[np.ndarray, np.ndarray]:
    """Run MC dropout: set train mode (keeps dropout active), run n_passes."""
    model.train()
    preds = []
    with torch.no_grad():
        for _ in range(n_passes):
            preds.append(model(X).cpu().numpy())
    arr = np.stack(preds, axis=0)  # (n_passes, N)
    return arr.mean(axis=0), arr.std(axis=0)


def rf_tree_variance(rf_model, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    tree_probs = np.array([t.predict_proba(X)[:, 1] for t in rf_model.estimators_])
    return tree_probs.mean(axis=0), tree_probs.std(axis=0)


def _interval_width_90(std: np.ndarray) -> float:
    # 90% interval width under normal approximation: 2 * 1.645 * std
    return float(np.mean(std) * 2 * 1.645)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Uncertainty quantification (Step 13).")
    parser.add_argument("--input", default="data/processed/vegshift_master.csv")
    parser.add_argument("--models-dir", default="models/baselines")
    parser.add_argument("--deep-models-dir", default="models/deep_models")
    parser.add_argument("--tft-predictions", default="data/output/tft_predictions.csv")
    parser.add_argument("--output", default="data/output/uncertainty_metrics.json")
    parser.add_argument("--seq-len", type=int, default=5)
    parser.add_argument("--mc-passes", type=int, default=50)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    models_dir = pathlib.Path(args.models_dir)
    deep_dir = pathlib.Path(args.deep_models_dir)

    df = pd.read_csv(args.input)
    model_df = df.dropna(subset=FEATURES + ["cvle_label", "year", "city"]).copy()
    y = model_df["cvle_label"].to_numpy(dtype=int)
    cities = model_df["city"].to_numpy()
    years = model_df["year"].to_numpy()

    scaler_path = models_dir / "scaler.pkl"
    if not scaler_path.exists():
        raise FileNotFoundError(f"Scaler not found at {scaler_path}. Run step 8 first.")
    scaler = joblib.load(scaler_path)
    X_scaled = scaler.transform(model_df[FEATURES].to_numpy(dtype=float))

    test_mask_flat = years >= 2022
    X_test_flat = X_scaled[test_mask_flat]
    y_test_flat = y[test_mask_flat]

    X_seq, y_seq, year_seq, _ = build_sequences(X_scaled, y, cities, years, args.seq_len)
    seq_test = year_seq >= 2022
    X_seq_test_t = torch.tensor(X_seq[seq_test])
    y_seq_test = y_seq[seq_test].astype(int)

    results: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Random Forest — tree-level variance
    # ------------------------------------------------------------------
    rf_path = models_dir / "rf_baseline.pkl"
    if rf_path.exists() and len(y_test_flat) > 0:
        rf = joblib.load(rf_path)
        rf_mean, rf_std = rf_tree_variance(rf, X_test_flat)
        results["random_forest"] = {
            "ece": compute_ece(y_test_flat, rf_mean),
            "brier": float(np.mean((rf_mean - y_test_flat) ** 2)),
            "mean_std": float(rf_std.mean()),
            "interval_width_90pct": _interval_width_90(rf_std),
            "method": "tree_variance",
        }
        print(f"  RF: ECE={results['random_forest']['ece']:.4f}")

    # ------------------------------------------------------------------
    # LSTM — MC dropout
    # ------------------------------------------------------------------
    lstm_hparams_path = models_dir / "lstm_hparams.json"
    lstm_weights_path = models_dir / "lstm_baseline.pt"
    if lstm_weights_path.exists() and len(y_seq_test) > 0:
        n_features = len(FEATURES)
        if lstm_hparams_path.exists():
            with open(lstm_hparams_path) as fh:
                n_features = json.load(fh).get("n_features", n_features)
        lstm = LSTMClassifier(n_features=n_features)
        lstm.load_state_dict(torch.load(lstm_weights_path, map_location="cpu"))
        lstm_mean, lstm_std = mc_dropout(lstm, X_seq_test_t, args.mc_passes)
        results["lstm"] = {
            "ece": compute_ece(y_seq_test, lstm_mean),
            "brier": float(np.mean((lstm_mean - y_seq_test) ** 2)),
            "mean_std": float(lstm_std.mean()),
            "interval_width_90pct": _interval_width_90(lstm_std),
            "method": "mc_dropout",
            "n_passes": args.mc_passes,
        }
        print(f"  LSTM: ECE={results['lstm']['ece']:.4f}")

    # ------------------------------------------------------------------
    # TCN + Transformer — MC dropout (uses saved hparams from step10)
    # ------------------------------------------------------------------
    hparams_path = deep_dir / "hparams.json"
    if hparams_path.exists() and len(y_seq_test) > 0:
        with open(hparams_path) as fh:
            hparams = json.load(fh)

        tcn_path = deep_dir / "tcn.pt"
        if tcn_path.exists():
            tcn = TCNClassifier(
                n_features=hparams["n_features"],
                num_channels=hparams["tcn"]["num_channels"],
                num_layers=hparams["tcn"]["num_layers"],
                dropout=hparams["tcn"]["dropout"],
            )
            tcn.load_state_dict(torch.load(tcn_path, map_location="cpu"))
            tcn_mean, tcn_std = mc_dropout(tcn, X_seq_test_t, args.mc_passes)
            results["tcn"] = {
                "ece": compute_ece(y_seq_test, tcn_mean),
                "brier": float(np.mean((tcn_mean - y_seq_test) ** 2)),
                "mean_std": float(tcn_std.mean()),
                "interval_width_90pct": _interval_width_90(tcn_std),
                "method": "mc_dropout",
                "n_passes": args.mc_passes,
            }
            print(f"  TCN: ECE={results['tcn']['ece']:.4f}")

        tr_path = deep_dir / "transformer.pt"
        if tr_path.exists():
            tr = TransformerClassifier(
                n_features=hparams["n_features"],
                d_model=hparams["transformer"]["d_model"],
                nhead=hparams["transformer"]["nhead"],
                num_layers=hparams["transformer"]["num_layers"],
                dropout=hparams["transformer"]["dropout"],
            )
            tr.load_state_dict(torch.load(tr_path, map_location="cpu"))
            tr_mean, tr_std = mc_dropout(tr, X_seq_test_t, args.mc_passes)
            results["transformer"] = {
                "ece": compute_ece(y_seq_test, tr_mean),
                "brier": float(np.mean((tr_mean - y_seq_test) ** 2)),
                "mean_std": float(tr_std.mean()),
                "interval_width_90pct": _interval_width_90(tr_std),
                "method": "mc_dropout",
                "n_passes": args.mc_passes,
            }
            print(f"  Transformer: ECE={results['transformer']['ece']:.4f}")

    # ------------------------------------------------------------------
    # TFT — ECE from saved median predictions (quantile intervals need step7 re-run)
    # ------------------------------------------------------------------
    tft_path = pathlib.Path(args.tft_predictions)
    if tft_path.exists():
        tft_df = pd.read_csv(tft_path)
        merged = tft_df.merge(
            model_df[["city", "year", "cvle_label"]], on=["city", "year"], how="inner"
        )
        if not merged.empty:
            y_tft = merged["cvle_label"].to_numpy().astype(int)
            p_tft = merged["predicted_cvle_score"].to_numpy().astype(float)
            results["tft"] = {
                "ece": compute_ece(y_tft, p_tft),
                "brier": float(np.mean((p_tft - y_tft) ** 2)),
                "mean_std": None,
                "interval_width_90pct": None,
                "method": "quantile_median_only",
                "note": "Full quantile intervals available by re-running step7 with mode='quantiles'",
            }
            print(f"  TFT: ECE={results['tft']['ece']:.4f}")

    pathlib.Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nUncertainty metrics saved: {args.output}")


if __name__ == "__main__":
    main()

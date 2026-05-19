"""Step 20 - Train TCN and Vanilla Transformer models for CVLE prediction."""

from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import StandardScaler

try:
    from pipeline.research_shared import (
        FEATURES, TCNClassifier, TransformerClassifier, build_sequences, save_predictions,
    )
except ModuleNotFoundError:
    from research_shared import (
        FEATURES, TCNClassifier, TransformerClassifier, build_sequences, save_predictions,
    )


def safe_auc(y_true: np.ndarray, y_prob: np.ndarray) -> float | None:
    if len(np.unique(y_true)) < 2:
        return None
    return float(roc_auc_score(y_true, y_prob))


def _train(model: nn.Module, X_t: torch.Tensor, y_t: torch.Tensor, epochs: int, lr: float = 1e-3) -> None:
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.BCELoss()
    model.train()
    for _ in range(epochs):
        optimizer.zero_grad()
        loss_fn(model(X_t), y_t).backward()
        optimizer.step()


def _eval(model: nn.Module, X_t: torch.Tensor) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    with torch.no_grad():
        prob = model(X_t).cpu().numpy()
    return prob, (prob >= 0.5).astype(int)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train deep sequence models for VegShift (Step 10).")
    parser.add_argument("--input", default="data/processed/vegshift_master.csv")
    parser.add_argument("--output-dir", default="models/deep_models")
    parser.add_argument("--metrics-output", default="data/output/deep_model_metrics.json")
    parser.add_argument("--predictions-dir", default="data/output/predictions")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--seq-len", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--tcn-channels", type=int, default=64)
    parser.add_argument("--tcn-layers", type=int, default=4)
    parser.add_argument("--transformer-d-model", type=int, default=64)
    parser.add_argument("--transformer-heads", type=int, default=4)
    parser.add_argument("--transformer-layers", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    df = pd.read_csv(args.input)
    missing = [c for c in FEATURES + ["cvle_label", "year", "city"] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    model_df = df.dropna(subset=FEATURES + ["cvle_label", "year", "city"]).copy()
    X = model_df[FEATURES].to_numpy(dtype=float)
    y = model_df["cvle_label"].to_numpy(dtype=int)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_seq, y_seq, year_seq, city_seq = build_sequences(
        X_scaled, y.astype(float), model_df["city"].to_numpy(), model_df["year"].to_numpy(), args.seq_len
    )

    train_mask = year_seq <= 2018
    test_mask = year_seq >= 2022
    if train_mask.sum() == 0 or test_mask.sum() == 0:
        raise ValueError("Train/test split empty. Check year range in data.")

    X_train_t = torch.tensor(X_seq[train_mask])
    y_train_t = torch.tensor(y_seq[train_mask])
    X_test_t = torch.tensor(X_seq[test_mask])
    y_test = y_seq[test_mask].astype(int)
    n_features = X_seq.shape[2]

    out_dir = pathlib.Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pred_dir = pathlib.Path(args.predictions_dir)
    metrics: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # TCN
    # ------------------------------------------------------------------
    tcn = TCNClassifier(
        n_features=n_features,
        num_channels=args.tcn_channels,
        num_layers=args.tcn_layers,
        dropout=args.dropout,
    )
    _train(tcn, X_train_t, y_train_t, args.epochs)
    tcn_prob, tcn_pred = _eval(tcn, X_test_t)
    metrics["tcn"] = {
        "classification_report": classification_report(y_test, tcn_pred, output_dict=True, zero_division=0),
        "auc": safe_auc(y_test, tcn_prob),
        "seq_len": args.seq_len,
    }
    save_predictions("tcn", city_seq[test_mask], year_seq[test_mask], tcn_prob, tcn_pred, pred_dir)
    torch.save(tcn.state_dict(), out_dir / "tcn.pt")

    # ------------------------------------------------------------------
    # Vanilla Transformer
    # ------------------------------------------------------------------
    transformer = TransformerClassifier(
        n_features=n_features,
        d_model=args.transformer_d_model,
        nhead=args.transformer_heads,
        num_layers=args.transformer_layers,
        dropout=args.dropout,
    )
    _train(transformer, X_train_t, y_train_t, args.epochs)
    tr_prob, tr_pred = _eval(transformer, X_test_t)
    metrics["transformer"] = {
        "classification_report": classification_report(y_test, tr_pred, output_dict=True, zero_division=0),
        "auc": safe_auc(y_test, tr_prob),
        "seq_len": args.seq_len,
    }
    save_predictions("transformer", city_seq[test_mask], year_seq[test_mask], tr_prob, tr_pred, pred_dir)
    torch.save(transformer.state_dict(), out_dir / "transformer.pt")

    # Save hyperparams so step13 can reconstruct these models
    hparams = {
        "n_features": n_features,
        "seq_len": args.seq_len,
        "tcn": {
            "num_channels": args.tcn_channels,
            "num_layers": args.tcn_layers,
            "dropout": args.dropout,
        },
        "transformer": {
            "d_model": args.transformer_d_model,
            "nhead": args.transformer_heads,
            "num_layers": args.transformer_layers,
            "dropout": args.dropout,
        },
    }
    with open(out_dir / "hparams.json", "w", encoding="utf-8") as fh:
        json.dump(hparams, fh, indent=2)

    pathlib.Path(args.metrics_output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.metrics_output, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)

    print("Deep models saved to", args.output_dir)
    for name, m in metrics.items():
        print(f"  {name} AUC: {m.get('auc')}")


if __name__ == "__main__":
    main()

"""Step 22 - Feature group ablation study across RF, XGBoost, and LSTM."""

from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

try:
    from pipeline.research_shared import FEATURE_GROUPS, LSTMClassifier, build_sequences
except ModuleNotFoundError:
    from research_shared import FEATURE_GROUPS, LSTMClassifier, build_sequences


def safe_auc(y_true: np.ndarray, y_prob: np.ndarray) -> float | None:
    if len(np.unique(y_true)) < 2:
        return None
    return float(roc_auc_score(y_true, y_prob))


def _train_rf(X_train: np.ndarray, y_train: np.ndarray, seed: int) -> np.ndarray:
    rf = RandomForestClassifier(
        n_estimators=200, max_depth=6, class_weight="balanced", random_state=seed
    )
    rf.fit(X_train, y_train)
    return rf


def _train_xgb(X_train: np.ndarray, y_train: np.ndarray, seed: int):
    scale_pw = float((y_train == 0).sum()) / max(1.0, float((y_train == 1).sum()))
    model = xgb.XGBClassifier(
        n_estimators=200, max_depth=6, learning_rate=0.05,
        scale_pos_weight=scale_pw, eval_metric="logloss",
        random_state=seed, verbosity=0,
    )
    model.fit(X_train, y_train)
    return model


def _train_lstm(
    X_seq: np.ndarray,
    y_seq: np.ndarray,
    year_seq: np.ndarray,
    n_features: int,
    epochs: int,
    seed: int,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    torch.manual_seed(seed)
    train_mask = year_seq <= 2018
    test_mask = year_seq >= 2022
    if train_mask.sum() == 0 or test_mask.sum() == 0:
        return None, None

    model = LSTMClassifier(n_features=n_features)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.BCELoss()

    X_t = torch.tensor(X_seq[train_mask])
    y_t = torch.tensor(y_seq[train_mask])
    model.train()
    for _ in range(epochs):
        opt.zero_grad()
        loss_fn(model(X_t), y_t).backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        prob = model(torch.tensor(X_seq[test_mask])).cpu().numpy()
    return prob, y_seq[test_mask].astype(int)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Feature group ablation study (Step 12).")
    parser.add_argument("--input", default="data/processed/vegshift_master.csv")
    parser.add_argument("--output", default="data/output/ablation_results.json")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--seq-len", type=int, default=5)
    parser.add_argument("--lstm-epochs", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    np.random.seed(args.seed)

    df = pd.read_csv(args.input)
    all_feats = FEATURE_GROUPS["all"]
    model_df = df.dropna(subset=all_feats + ["cvle_label", "year", "city"]).copy()
    y = model_df["cvle_label"].to_numpy(dtype=int)
    cities = model_df["city"].to_numpy()
    years = model_df["year"].to_numpy()

    train_mask = years <= 2018
    test_mask = years >= 2022

    results: dict[str, dict[str, float | None]] = {}

    for group_name, features in FEATURE_GROUPS.items():
        available = [f for f in features if f in model_df.columns]
        if not available:
            print(f"  Skipping {group_name}: no features present in data.")
            continue

        X_raw = model_df[available].to_numpy(dtype=float)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_raw)
        y_train = y[train_mask]
        y_test = y[test_mask]

        group_res: dict[str, float | None] = {}

        # RF
        rf = _train_rf(X_scaled[train_mask], y_train, args.seed)
        group_res["random_forest"] = safe_auc(y_test, rf.predict_proba(X_scaled[test_mask])[:, 1])

        # XGB
        xgb_m = _train_xgb(X_scaled[train_mask], y_train, args.seed)
        group_res["xgboost"] = safe_auc(y_test, xgb_m.predict_proba(X_scaled[test_mask])[:, 1])

        # LSTM
        X_seq, y_seq, year_seq, _ = build_sequences(
            X_scaled, y.astype(float), cities, years, args.seq_len
        )
        lstm_prob, lstm_y_test = _train_lstm(
            X_seq, y_seq, year_seq, n_features=len(available),
            epochs=args.lstm_epochs, seed=args.seed,
        )
        if lstm_prob is not None:
            group_res["lstm"] = safe_auc(lstm_y_test, lstm_prob)
        else:
            group_res["lstm"] = None

        results[group_name] = group_res
        print(
            f"  {group_name:<16} RF={group_res['random_forest']!s:<8} "
            f"XGB={group_res['xgboost']!s:<8} LSTM={group_res['lstm']!s}"
        )

    pathlib.Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nAblation results saved: {args.output}")


if __name__ == "__main__":
    main()

"""Step 8 - Train baseline models (RF, LR, XGBoost, LightGBM, LSTM) for CVLE prediction."""

from __future__ import annotations

import argparse
import json
import pathlib

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import StandardScaler

try:
    from pipeline.research_shared import (
        FEATURES, LSTMClassifier, build_sequences, save_predictions,
    )
except ModuleNotFoundError:
    from research_shared import (
        FEATURES, LSTMClassifier, build_sequences, save_predictions,
    )


def safe_auc(y_true: np.ndarray, y_prob: np.ndarray) -> float | None:
    if len(np.unique(y_true)) < 2:
        return None
    return float(roc_auc_score(y_true, y_prob))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train VegShift baseline models (Step 8).")
    parser.add_argument("--input", default="data/processed/vegshift_master.csv")
    parser.add_argument("--output-dir", default="models/baselines")
    parser.add_argument("--metrics-output", default="data/output/baseline_metrics.json")
    parser.add_argument("--predictions-dir", default="data/output/predictions")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--seq-len", type=int, default=5)
    parser.add_argument("--lstm-epochs", type=int, default=30)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    df = pd.read_csv(args.input)
    missing_cols = [c for c in FEATURES + ["cvle_label", "year", "city"] if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    model_df = df.dropna(subset=FEATURES + ["cvle_label", "year", "city"]).copy()
    X = model_df[FEATURES].to_numpy(dtype=float)
    y = model_df["cvle_label"].to_numpy(dtype=int)
    cities_arr = model_df["city"].to_numpy()
    years_arr = model_df["year"].to_numpy()

    train_mask = years_arr <= 2018
    test_mask = years_arr >= 2022
    if train_mask.sum() == 0 or test_mask.sum() == 0:
        raise ValueError("Train/test year split produced empty set. Check year values in input data.")

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X[train_mask])
    X_test = scaler.transform(X[test_mask])
    y_train = y[train_mask]
    y_test = y[test_mask]
    cities_test = cities_arr[test_mask]
    years_test = years_arr[test_mask]

    pred_dir = pathlib.Path(args.predictions_dir)
    pred_dir_all = pred_dir.parent / "predictions_all"
    metrics: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Random Forest
    # ------------------------------------------------------------------
    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=args.seed,
    )
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)
    rf_prob = rf.predict_proba(X_test)[:, 1]
    metrics["random_forest"] = {
        "classification_report": classification_report(y_test, rf_pred, output_dict=True, zero_division=0),
        "auc": safe_auc(y_test, rf_prob),
    }
    save_predictions("random_forest", cities_test, years_test, rf_prob, rf_pred, pred_dir)
    rf_prob_all = rf.predict_proba(scaler.transform(X))[:, 1]
    save_predictions("random_forest", cities_arr, years_arr, rf_prob_all, (rf_prob_all >= 0.5).astype(int), pred_dir_all)

    # ------------------------------------------------------------------
    # Logistic Regression
    # ------------------------------------------------------------------
    lr = LogisticRegression(class_weight="balanced", max_iter=2000, random_state=args.seed)
    lr.fit(X_train, y_train)
    lr_pred = lr.predict(X_test)
    lr_prob = lr.predict_proba(X_test)[:, 1]
    metrics["logistic_regression"] = {
        "classification_report": classification_report(y_test, lr_pred, output_dict=True, zero_division=0),
        "auc": safe_auc(y_test, lr_prob),
    }
    save_predictions("logistic_regression", cities_test, years_test, lr_prob, lr_pred, pred_dir)
    lr_prob_all = lr.predict_proba(scaler.transform(X))[:, 1]
    save_predictions("logistic_regression", cities_arr, years_arr, lr_prob_all, (lr_prob_all >= 0.5).astype(int), pred_dir_all)

    # ------------------------------------------------------------------
    # XGBoost
    # ------------------------------------------------------------------
    scale_pw = float((y_train == 0).sum()) / max(1.0, float((y_train == 1).sum()))
    xgb_model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pw,
        eval_metric="logloss",
        random_state=args.seed,
        verbosity=0,
    )
    xgb_model.fit(X_train, y_train)
    xgb_pred = xgb_model.predict(X_test)
    xgb_prob = xgb_model.predict_proba(X_test)[:, 1]
    metrics["xgboost"] = {
        "classification_report": classification_report(y_test, xgb_pred, output_dict=True, zero_division=0),
        "auc": safe_auc(y_test, xgb_prob),
    }
    save_predictions("xgboost", cities_test, years_test, xgb_prob, xgb_pred, pred_dir)
    xgb_prob_all = xgb_model.predict_proba(scaler.transform(X))[:, 1]
    save_predictions("xgboost", cities_arr, years_arr, xgb_prob_all, (xgb_prob_all >= 0.5).astype(int), pred_dir_all)

    # ------------------------------------------------------------------
    # LightGBM
    # ------------------------------------------------------------------
    lgb_model = lgb.LGBMClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        class_weight="balanced",
        random_state=args.seed,
        verbose=-1,
    )
    lgb_model.fit(X_train, y_train)
    lgb_pred = lgb_model.predict(X_test)
    lgb_prob = lgb_model.predict_proba(X_test)[:, 1]
    metrics["lightgbm"] = {
        "classification_report": classification_report(y_test, lgb_pred, output_dict=True, zero_division=0),
        "auc": safe_auc(y_test, lgb_prob),
    }
    save_predictions("lightgbm", cities_test, years_test, lgb_prob, lgb_pred, pred_dir)
    lgb_prob_all = lgb_model.predict_proba(scaler.transform(X))[:, 1]
    save_predictions("lightgbm", cities_arr, years_arr, lgb_prob_all, (lgb_prob_all >= 0.5).astype(int), pred_dir_all)

    # ------------------------------------------------------------------
    # LSTM
    # ------------------------------------------------------------------
    X_all_scaled = scaler.transform(X)
    X_seq, y_seq, year_seq, city_seq = build_sequences(
        X_all_scaled, y.astype(float), cities_arr, years_arr, seq_len=args.seq_len
    )

    lstm_train_mask = year_seq <= 2018
    lstm_test_mask = year_seq >= 2022
    if lstm_train_mask.sum() == 0 or lstm_test_mask.sum() == 0:
        raise ValueError("LSTM sequence year split produced empty set. Check sequence length and year coverage.")

    X_seq_train = torch.tensor(X_seq[lstm_train_mask])
    y_seq_train = torch.tensor(y_seq[lstm_train_mask])
    X_seq_test = torch.tensor(X_seq[lstm_test_mask])
    y_seq_test = y_seq[lstm_test_mask]

    lstm = LSTMClassifier(n_features=X_seq.shape[2])
    optimizer = torch.optim.Adam(lstm.parameters(), lr=1e-3)
    loss_fn = nn.BCELoss()

    lstm.train()
    for _ in range(args.lstm_epochs):
        optimizer.zero_grad()
        loss = loss_fn(lstm(X_seq_train), y_seq_train)
        loss.backward()
        optimizer.step()

    lstm.eval()
    with torch.no_grad():
        lstm_prob = lstm(X_seq_test).cpu().numpy()
        lstm_pred = (lstm_prob >= 0.5).astype(int)

    metrics["lstm"] = {
        "classification_report": classification_report(
            y_seq_test.astype(int), lstm_pred, output_dict=True, zero_division=0
        ),
        "auc": safe_auc(y_seq_test.astype(int), lstm_prob),
        "seq_len": args.seq_len,
    }
    save_predictions("lstm", city_seq[lstm_test_mask], year_seq[lstm_test_mask], lstm_prob, lstm_pred, pred_dir)
    lstm.eval()
    with torch.no_grad():
        X_seq_all_t = torch.tensor(X_seq)
        lstm_prob_all = lstm(X_seq_all_t).cpu().numpy()
    save_predictions("lstm", city_seq, year_seq, lstm_prob_all, (lstm_prob_all >= 0.5).astype(int), pred_dir_all)

    # ------------------------------------------------------------------
    # Persist models
    # ------------------------------------------------------------------
    out_dir = pathlib.Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.metrics_output).parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(rf, out_dir / "rf_baseline.pkl")
    joblib.dump(lr, out_dir / "lr_baseline.pkl")
    joblib.dump(xgb_model, out_dir / "xgb_baseline.pkl")
    joblib.dump(lgb_model, out_dir / "lgb_baseline.pkl")
    joblib.dump(scaler, out_dir / "scaler.pkl")
    torch.save(lstm.state_dict(), out_dir / "lstm_baseline.pt")

    with open(out_dir / "lstm_hparams.json", "w", encoding="utf-8") as fh:
        json.dump({"n_features": int(X_seq.shape[2]), "seq_len": args.seq_len}, fh)

    with open(args.metrics_output, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)

    print("Baseline models saved to", args.output_dir)
    for name, m in metrics.items():
        print(f"  {name} AUC: {m.get('auc')}")


if __name__ == "__main__":
    main()

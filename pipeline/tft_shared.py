"""Shared TFT helpers for VegShift step 6 and step 7."""

from __future__ import annotations

import pandas as pd
from pytorch_forecasting import TimeSeriesDataSet


FILL_CITY_COLS = [
    "pre_monsoon_depth_mbgl",
    "post_monsoon_depth_mbgl",
    "depletion_rate",
    "recharge_efficiency",
    "monsoon_onset_doy",
    "sowing_window_miss",
    "gdd_accumulation",
]


def load_and_prepare(path: str) -> pd.DataFrame:
    """Load VegShift master data and apply the TFT-ready typing/fill rules."""
    df = pd.read_csv(path)
    df = df.sort_values(["city", "year"]).reset_index(drop=True)

    df["time_idx"] = df.groupby("city").cumcount()
    df["city"] = df["city"].astype(str)
    df["crop"] = df["crop"].astype(str)
    df["koppen_zone"] = df["koppen_zone"].astype(str)
    df["cvle_label"] = df["cvle_label"].astype(float)

    import numpy as np
    df["cycle_sin_5yr"] = np.sin(2 * np.pi * df["year"] / 5.0)
    df["cycle_cos_5yr"] = np.cos(2 * np.pi * df["year"] / 5.0)

    for col in FILL_CITY_COLS:
        if col in df.columns:
            df[col] = df.groupby("city")[col].transform(lambda x: x.fillna(x.mean()))
            if df[col].isna().any():
                df[col] = df[col].fillna(df[col].median())

    return df


def build_datasets(df: pd.DataFrame, encoder_len: int, pred_len: int) -> tuple[TimeSeriesDataSet, TimeSeriesDataSet]:
    """Build the training and prediction datasets with the same feature schema."""
    time_varying_known_reals = [
        "temp_mean",
        "temp_max",
        "rainfall_annual",
        "wind_speed",
        "humidity",
        "n_dry_months",
        "monsoon_onset_doy",
        "sowing_window_miss",
        "gdd_accumulation",
        "crop_water_deficit",
        "pre_monsoon_depth_mbgl",
        "depletion_rate",
        "recharge_efficiency",
        "dual_deficit",
        "gdd_adequate",
        "koppen_zone_enc",
        "cycle_sin_5yr",
        "cycle_cos_5yr",
    ]

    time_varying_known_cats = ["koppen_zone"]
    static_cats = ["city", "crop"]
    static_reals = ["gaez_baseline_class", "gdd_min", "water_req", "sow_doy", "max_temp"]

    train_df = df[df["time_idx"] <= 18].copy()
    val_df = df.copy()  # predict on full range so test window (2022-2024) is covered

    training = TimeSeriesDataSet(
        train_df,
        time_idx="time_idx",
        target="cvle_label",
        group_ids=["city"],
        min_encoder_length=max(2, encoder_len // 2),
        max_encoder_length=encoder_len,
        min_prediction_length=1,
        max_prediction_length=pred_len,
        static_categoricals=static_cats,
        static_reals=static_reals,
        time_varying_known_categoricals=time_varying_known_cats,
        time_varying_known_reals=time_varying_known_reals,
        time_varying_unknown_reals=["cvle_label"],
        add_relative_time_idx=True,
        add_target_scales=True,
        add_encoder_length=True,
    )

    validation = TimeSeriesDataSet.from_dataset(
        training,
        val_df,
        predict=True,
        stop_randomization=True,
    )

    return training, validation
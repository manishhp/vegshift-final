"""Shared model classes and utilities for the VegShift comparative research study."""

from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
import torch
import torch.nn as nn


FEATURES: list[str] = [
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
    "gaez_baseline_class",
    "koppen_zone_enc",
]

FEATURE_GROUPS: dict[str, list[str]] = {
    "climate": ["temp_mean", "temp_max", "rainfall_annual", "wind_speed", "humidity", "n_dry_months"],
    "phenology": ["monsoon_onset_doy", "sowing_window_miss", "gdd_accumulation", "gdd_adequate"],
    "hydrology": [
        "pre_monsoon_depth_mbgl", "depletion_rate", "recharge_efficiency",
        "crop_water_deficit", "dual_deficit",
    ],
    "static_context": ["gaez_baseline_class", "koppen_zone_enc"],
    "all": FEATURES,
}


# ---------------------------------------------------------------------------
# Sequence builder
# ---------------------------------------------------------------------------

def build_sequences(
    X_scaled: np.ndarray,
    y: np.ndarray,
    cities: np.ndarray,
    years: np.ndarray,
    seq_len: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Build sliding-window sequences and return (X_seq, y_seq, year_seq, city_seq)."""
    X_l: list[np.ndarray] = []
    y_l: list[float] = []
    year_l: list[int] = []
    city_l: list[str] = []

    for city in np.unique(cities):
        idx = np.where(cities == city)[0]
        order = np.argsort(years[idx])
        idx = idx[order]
        X_c = X_scaled[idx]
        y_c = y[idx]
        yrs_c = years[idx]
        for i in range(seq_len, len(X_c)):
            X_l.append(X_c[i - seq_len : i])
            y_l.append(float(y_c[i]))
            year_l.append(int(yrs_c[i]))
            city_l.append(str(city))

    return (
        np.asarray(X_l, dtype=np.float32),
        np.asarray(y_l, dtype=np.float32),
        np.asarray(year_l, dtype=np.int32),
        np.asarray(city_l),
    )


def save_predictions(
    model_name: str,
    city: np.ndarray,
    year: np.ndarray,
    prob: np.ndarray,
    pred: np.ndarray,
    out_dir: pathlib.Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {"city": city, "year": year, "prob": prob.astype(float), "pred": pred.astype(int)}
    ).to_csv(out_dir / f"{model_name}_predictions.csv", index=False)


# ---------------------------------------------------------------------------
# LSTM
# ---------------------------------------------------------------------------

class LSTMClassifier(nn.Module):
    def __init__(
        self,
        n_features: int,
        hidden_size: int = 64,
        layers: int = 2,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden_size,
            num_layers=layers,
            batch_first=True,
            dropout=dropout,
        )
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _, (h_n, _) = self.lstm(x)
        return torch.sigmoid(self.fc(h_n[-1])).squeeze(-1)


# ---------------------------------------------------------------------------
# TCN
# ---------------------------------------------------------------------------

class _CausalConv1d(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, kernel_size: int, dilation: int) -> None:
        super().__init__()
        self._pad = (kernel_size - 1) * dilation
        self.conv = nn.Conv1d(in_ch, out_ch, kernel_size, padding=self._pad, dilation=dilation)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(x)[:, :, : x.size(2)]


class _TCNBlock(nn.Module):
    def __init__(
        self, in_ch: int, out_ch: int, kernel_size: int, dilation: int, dropout: float
    ) -> None:
        super().__init__()
        self.net = nn.Sequential(
            _CausalConv1d(in_ch, out_ch, kernel_size, dilation),
            nn.ReLU(),
            nn.Dropout(dropout),
            _CausalConv1d(out_ch, out_ch, kernel_size, dilation),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.residual: nn.Module = nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return nn.functional.relu(self.net(x) + self.residual(x))


class TCNClassifier(nn.Module):
    def __init__(
        self,
        n_features: int,
        num_channels: int = 64,
        num_layers: int = 4,
        kernel_size: int = 3,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        in_ch = n_features
        for i in range(num_layers):
            layers.append(_TCNBlock(in_ch, num_channels, kernel_size, 2 ** i, dropout))
            in_ch = num_channels
        self.network = nn.Sequential(*layers)
        self.fc = nn.Linear(num_channels, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, features) → (batch, features, seq_len)
        out = self.network(x.transpose(1, 2))
        return torch.sigmoid(self.fc(out[:, :, -1])).squeeze(-1)


# ---------------------------------------------------------------------------
# Vanilla Transformer
# ---------------------------------------------------------------------------

class _PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 512, dropout: float = 0.1) -> None:
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len).unsqueeze(1).float()
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term[: d_model // 2])
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(x + self.pe[:, : x.size(1)])


class TransformerClassifier(nn.Module):
    def __init__(
        self,
        n_features: int,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 2,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.input_proj = nn.Linear(n_features, d_model)
        self.pos_enc = _PositionalEncoding(d_model, dropout=dropout)
        enc_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(enc_layer, num_layers=num_layers)
        self.fc = nn.Linear(d_model, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.pos_enc(self.input_proj(x))
        return torch.sigmoid(self.fc(self.transformer(x)[:, -1, :])).squeeze(-1)

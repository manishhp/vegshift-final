"""
Step 6 - Temporal Fusion Transformer (TFT) training for CVLE prediction.

Input:
  data/processed/vegshift_master.csv

Output:
  models/tft/vegshift-tft-best.ckpt
"""

from __future__ import annotations

import argparse
import pathlib

from lightning.pytorch import Trainer, seed_everything
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
from pytorch_forecasting import TemporalFusionTransformer
from pytorch_forecasting.metrics import QuantileLoss

try:
    from pipeline.tft_shared import build_datasets, load_and_prepare
except ModuleNotFoundError:
    from tft_shared import build_datasets, load_and_prepare

def train_tft(args: argparse.Namespace) -> pathlib.Path:
    seed_everything(args.seed, workers=True)

    df = load_and_prepare(args.input)
    training, validation = build_datasets(df, args.encoder_len, args.pred_len)

    train_loader = training.to_dataloader(train=True, batch_size=args.batch_size, num_workers=0)
    val_loader = validation.to_dataloader(train=False, batch_size=args.batch_size, num_workers=0)

    tft = TemporalFusionTransformer.from_dataset(
        training,
        learning_rate=args.learning_rate,
        hidden_size=args.hidden_size,
        attention_head_size=args.attention_heads,
        dropout=args.dropout,
        hidden_continuous_size=args.hidden_continuous,
        output_size=7,
        loss=QuantileLoss(),
        log_interval=10,
        reduce_on_plateau_patience=3,
    )

    n_params = sum(p.numel() for p in tft.parameters())
    print(f"TFT parameters: {n_params/1e3:.1f}k")

    out_dir = pathlib.Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_cb = ModelCheckpoint(
        dirpath=str(out_dir),
        filename="vegshift-tft-best",
        monitor="val_loss",
        mode="min",
        save_top_k=1,
    )

    trainer = Trainer(
        max_epochs=args.max_epochs,
        accelerator="auto",
        gradient_clip_val=0.1,
        callbacks=[
            EarlyStopping(monitor="val_loss", patience=args.early_stop_patience, mode="min"),
            checkpoint_cb,
        ],
        enable_progress_bar=True,
    )

    trainer.fit(tft, train_dataloaders=train_loader, val_dataloaders=val_loader)

    best_path = checkpoint_cb.best_model_path
    if not best_path:
        raise RuntimeError("Training completed but no checkpoint was saved.")

    print(f"TFT training complete. Best checkpoint: {best_path}")
    return pathlib.Path(best_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train TFT model for VegShift (Step 6).")
    parser.add_argument("--input", default="data/processed/vegshift_master.csv")
    parser.add_argument("--output-dir", default="models/tft")

    parser.add_argument("--max-epochs", type=int, default=50)
    parser.add_argument("--early-stop-patience", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=16)

    parser.add_argument("--encoder-len", type=int, default=5)
    parser.add_argument("--pred-len", type=int, default=3)

    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--attention-heads", type=int, default=4)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--hidden-continuous", type=int, default=32)

    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_tft(args)


if __name__ == "__main__":
    main()

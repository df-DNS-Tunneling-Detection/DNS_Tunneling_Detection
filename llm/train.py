"""Fine-tune DistilBERT for DNS tunneling detection.

Usage:
    python train.py --data ../data/raw/sample.csv
    python train.py --data ../data/raw/CIRA-CIC-DoHBrw-2020/
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

ROOT = Path(__file__).resolve().parent
MODELS_DIR = ROOT / "models"
DATA_DIR = ROOT.parent / "data"

MODEL_NAME = "distilbert-base-uncased"
MAX_LENGTH = 128
LABEL2ID = {"benign": 0, "tunneling": 1}
ID2LABEL = {0: "benign", 1: "tunneling"}


def load_data(path: str) -> pd.DataFrame:
    """Load CSV with 'query' and 'label' columns."""
    path = Path(path)
    if path.is_dir():
        dfs = [pd.read_csv(f) for f in sorted(path.glob("*.csv"))]
        df = pd.concat(dfs, ignore_index=True)
    else:
        df = pd.read_csv(path)

    df = df.dropna(subset=["query", "label"])
    df["query"] = df["query"].astype(str)
    df["label"] = df["label"].astype(int)
    return df


class DNSDataset(torch.utils.data.Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        item = {k: v[idx] for k, v in self.encodings.items()}
        item["labels"] = self.labels[idx]
        return item


def compute_metrics(eval_pred):
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "precision": precision_score(labels, preds),
        "recall": recall_score(labels, preds),
        "f1": f1_score(labels, preds),
    }


def main():
    parser = argparse.ArgumentParser(description="Fine-tune DistilBERT for DNS tunneling detection.")
    parser.add_argument("--data", default=str(DATA_DIR / "raw" / "sample.csv"),
                        help="Path to CSV or directory of CSVs with 'query' and 'label' columns.")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=MAX_LENGTH)
    parser.add_argument("--output-dir", default=str(MODELS_DIR / "distilbert"))
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    # Load data
    print(f"Loading data from {args.data} ...")
    df = load_data(args.data)
    print(f"  Total: {len(df):,} samples | benign: {(df['label'] == 0).sum():,} | tunneling: {(df['label'] == 1).sum():,}")

    # Split: 80% train, 10% val, 10% test
    train_df, temp_df = train_test_split(df, test_size=0.2, stratify=df["label"], random_state=42)
    val_df, test_df = train_test_split(temp_df, test_size=0.5, stratify=temp_df["label"], random_state=42)
    print(f"  Train: {len(train_df):,} | Val: {len(val_df):,} | Test: {len(test_df):,}")

    # Save test split for evaluate.py
    test_out = ROOT / "test_split.csv"
    test_df.to_csv(test_out, index=False)
    print(f"  Saved test split to {test_out}")

    # Tokenize
    print("Tokenizing ...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    def tokenize(texts):
        return tokenizer(texts.tolist(), padding="max_length", truncation=True,
                         max_length=args.max_length, return_tensors="pt")

    train_enc = tokenize(train_df["query"])
    val_enc = tokenize(val_df["query"])
    test_enc = tokenize(test_df["query"])

    train_ds = DNSDataset(train_enc, torch.tensor(train_df["label"].values))
    val_ds = DNSDataset(val_enc, torch.tensor(val_df["label"].values))
    test_ds = DNSDataset(test_enc, torch.tensor(test_df["label"].values))

    # Model
    print(f"Loading {MODEL_NAME} ...")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=2,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )

    # Training
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size * 2,
        learning_rate=args.lr,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        logging_steps=100,
        fp16=(device == "cuda"),
        report_to="none",
        seed=42,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        compute_metrics=compute_metrics,
    )

    print("\nTraining ...")
    trainer.train()

    # Evaluate on test set
    print("\nTest set results:")
    test_results = trainer.evaluate(test_ds)
    for k, v in test_results.items():
        print(f"  {k}: {v:.4f}")

    # Save
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"\nModel saved to {args.output_dir}")


if __name__ == "__main__":
    main()

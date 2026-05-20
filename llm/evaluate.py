"""Evaluate the fine-tuned DistilBERT and compare with classical ML models.

Usage:
    python evaluate.py
    python evaluate.py --model-dir models/distilbert --test-csv test_split.csv
"""

import argparse
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import torch
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
FIGURES_DIR = ROOT / "figures"
CLASSICAL_MODELS = PARENT / "models"
CLASSICAL_TEST = PARENT / "data" / "processed" / "test_split.csv"


def load_test_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.dropna(subset=["query", "label"])
    df["query"] = df["query"].astype(str)
    df["label"] = df["label"].astype(int)
    return df


def evaluate_distilbert(model_dir: str, test_df: pd.DataFrame):
    """Run DistilBERT predictions on test set."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(device)
    model.eval()

    texts = test_df["query"].tolist()
    labels = test_df["label"].values

    all_probs = []
    batch_size = 64
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        enc = tokenizer(batch, padding=True, truncation=True, max_length=128, return_tensors="pt").to(device)
        with torch.no_grad():
            logits = model(**enc).logits
            probs = torch.softmax(logits, dim=-1)[:, 1].cpu().numpy()
        all_probs.extend(probs)

    probs = np.array(all_probs)
    preds = (probs >= 0.5).astype(int)
    return labels, preds, probs


def evaluate_classical(test_csv: str):
    """Run classical ML predictions on test set."""
    df = pd.read_csv(test_csv)
    y = df["label"].astype(int).values
    X = df.drop(columns=["label"])

    rf = joblib.load(CLASSICAL_MODELS / "rf.pkl")
    xgb = joblib.load(CLASSICAL_MODELS / "xgb.pkl")

    rf_preds = rf.predict(X)
    rf_probs = rf.predict_proba(X)[:, 1]

    xgb_preds = xgb.predict(X)
    xgb_probs = xgb.predict_proba(X)[:, 1]

    return y, rf_preds, rf_probs, xgb_preds, xgb_probs


def compute_metrics(y_true, y_pred, y_prob):
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred),
        "recall": recall_score(y_true, y_pred),
        "f1": f1_score(y_true, y_pred),
        "roc_auc": roc_auc_score(y_true, y_prob),
    }


def plot_confusion(y_true, y_pred, name: str):
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ConfusionMatrixDisplay(cm, display_labels=["benign", "tunneling"]).plot(
        ax=ax, colorbar=False, cmap="Blues"
    )
    ax.set_title(f"Confusion Matrix — {name}")
    fig.tight_layout()
    out = FIGURES_DIR / f"confusion_{name.lower().replace(' ', '_')}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Saved {out}")


def plot_roc_comparison(curves: dict):
    fig, ax = plt.subplots(figsize=(6, 5))
    for name, (fpr, tpr, auc) in curves.items():
        ax.plot(fpr, tpr, label=f"{name} (AUC = {auc:.4f})")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.3)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC — Model Comparison")
    ax.legend(loc="lower right")
    fig.tight_layout()
    out = FIGURES_DIR / "roc_comparison_all.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Saved {out}")


def plot_pr_comparison(pr_curves: dict):
    fig, ax = plt.subplots(figsize=(6, 5))
    for name, (prec, rec, auc_val) in pr_curves.items():
        ax.plot(rec, prec, label=f"{name} (PR-AUC = {auc_val:.4f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall — Model Comparison")
    ax.legend(loc="lower left")
    fig.tight_layout()
    out = FIGURES_DIR / "pr_comparison_all.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Saved {out}")


def plot_metric_bars(all_metrics: dict):
    df = pd.DataFrame(all_metrics).T
    metrics_to_plot = ["accuracy", "precision", "recall", "f1", "roc_auc"]

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(metrics_to_plot))
    width = 0.25
    colors = ["#4c72b0", "#dd8452", "#55a868"]

    for i, (model_name, _) in enumerate(all_metrics.items()):
        vals = [df.loc[model_name, m] for m in metrics_to_plot]
        ax.bar(x + i * width, vals, width, label=model_name, color=colors[i % len(colors)])

    ax.set_xticks(x + width)
    ax.set_xticklabels([m.replace("_", "-").upper() for m in metrics_to_plot])
    ax.set_ylim(0.9, 1.01)
    ax.set_ylabel("Score")
    ax.set_title("Model Comparison — All Metrics")
    ax.legend()
    fig.tight_layout()
    out = FIGURES_DIR / "metric_comparison_bars.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Saved {out}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate DistilBERT vs classical ML.")
    parser.add_argument("--model-dir", default=str(ROOT / "models" / "distilbert"))
    parser.add_argument("--test-csv", default=str(ROOT / "test_split.csv"))
    parser.add_argument("--classical-test", default=str(CLASSICAL_TEST))
    args = parser.parse_args()

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Load test data
    test_df = load_test_data(args.test_csv)
    print(f"Test set: {len(test_df):,} samples")

    # DistilBERT
    print("\n[DistilBERT]")
    db_labels, db_preds, db_probs = evaluate_distilbert(args.model_dir, test_df)
    db_metrics = compute_metrics(db_labels, db_preds, db_probs)
    print(classification_report(db_labels, db_preds, target_names=["benign", "tunneling"]))
    plot_confusion(db_labels, db_preds, "DistilBERT")

    # Classical ML
    print("\n[Classical ML — Random Forest & XGBoost]")
    try:
        cl_labels, rf_preds, rf_probs, xgb_preds, xgb_probs = evaluate_classical(args.classical_test)
        rf_metrics = compute_metrics(cl_labels, rf_preds, rf_probs)
        xgb_metrics = compute_metrics(cl_labels, xgb_preds, xgb_probs)
        print(f"  RF  F1={rf_metrics['f1']:.4f}  AUC={rf_metrics['roc_auc']:.4f}")
        print(f"  XGB F1={xgb_metrics['f1']:.4f}  AUC={xgb_metrics['roc_auc']:.4f}")
        plot_confusion(cl_labels, rf_preds, "Random Forest")
        plot_confusion(cl_labels, xgb_preds, "XGBoost")
    except FileNotFoundError:
        print("  Classical models/test split not found. Run src/train.py first.")
        rf_metrics, xgb_metrics = None, None

    # ROC comparison
    curves = {}
    fpr, tpr, _ = roc_curve(db_labels, db_probs)
    curves["DistilBERT"] = (fpr, tpr, db_metrics["roc_auc"])

    if rf_metrics:
        fpr, tpr, _ = roc_curve(cl_labels, rf_probs)
        curves["Random Forest"] = (fpr, tpr, rf_metrics["roc_auc"])
        fpr, tpr, _ = roc_curve(cl_labels, xgb_probs)
        curves["XGBoost"] = (fpr, tpr, xgb_metrics["roc_auc"])

    plot_roc_comparison(curves)

    # PR-AUC comparison
    pr_curves = {}
    prec, rec, _ = precision_recall_curve(db_labels, db_probs)
    pr_auc = np.trapz(prec, rec)
    pr_curves["DistilBERT"] = (prec, rec, pr_auc)

    if rf_metrics:
        prec, rec, _ = precision_recall_curve(cl_labels, rf_probs)
        pr_curves["Random Forest"] = (prec, rec, np.trapz(prec, rec))
        prec, rec, _ = precision_recall_curve(cl_labels, xgb_probs)
        pr_curves["XGBoost"] = (prec, rec, np.trapz(prec, rec))

    plot_pr_comparison(pr_curves)

    # Metric bar chart
    all_metrics = {"DistilBERT": db_metrics}
    if rf_metrics:
        all_metrics["Random Forest"] = rf_metrics
        all_metrics["XGBoost"] = xgb_metrics
    plot_metric_bars(all_metrics)

    # Summary table
    summary = pd.DataFrame(all_metrics).T
    summary = summary.round(4)
    out = ROOT / "metrics_comparison.csv"
    summary.to_csv(out)
    print(f"\nSummary saved to {out}")
    print(summary)


if __name__ == "__main__":
    main()

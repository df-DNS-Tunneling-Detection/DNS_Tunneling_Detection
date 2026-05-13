"""Evaluate the trained models and generate report figures.

Usage:
    python -m src.evaluate
"""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"
PROCESSED_DIR = ROOT / "data" / "processed"
FIGURES_DIR = ROOT / "reports" / "figures"


def _ensure_dirs() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def load_test_split() -> tuple[pd.DataFrame, pd.Series]:
    path = PROCESSED_DIR / "test_split.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python -m src.train` first."
        )
    df = pd.read_csv(path)
    y = df["label"].astype(int)
    X = df.drop(columns=["label"])
    return X, y


def plot_confusion(y_true, y_pred, model_name: str) -> None:
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ConfusionMatrixDisplay(
        cm, display_labels=["benign", "tunneling"]
    ).plot(ax=ax, colorbar=False, cmap="Blues")
    ax.set_title(f"Confusion matrix — {model_name}")
    fig.tight_layout()
    out = FIGURES_DIR / f"confusion_matrix_{model_name.lower()}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  saved {out}")


def plot_roc(curves: dict[str, tuple[np.ndarray, np.ndarray, float]]) -> None:
    fig, ax = plt.subplots(figsize=(5, 4.5))
    for name, (fpr, tpr, auc) in curves.items():
        ax.plot(fpr, tpr, label=f"{name} (AUC = {auc:.3f})")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("ROC — model comparison")
    ax.legend(loc="lower right")
    fig.tight_layout()
    out = FIGURES_DIR / "roc_comparison.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  saved {out}")


def plot_feature_importance(model, feature_names, model_name: str) -> None:
    importances = getattr(model, "feature_importances_", None)
    if importances is None:
        return
    order = np.argsort(importances)[::-1]
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.barplot(
        x=importances[order],
        y=np.array(feature_names)[order],
        ax=ax,
        palette="viridis",
    )
    ax.set_xlabel("Importance")
    ax.set_title(f"Feature importance — {model_name}")
    fig.tight_layout()
    out = FIGURES_DIR / f"feature_importance_{model_name.lower()}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  saved {out}")


def evaluate_model(name: str, model, X_test, y_test) -> dict[str, float]:
    y_pred = model.predict(X_test)
    y_prob = (
        model.predict_proba(X_test)[:, 1]
        if hasattr(model, "predict_proba")
        else y_pred
    )

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_test, y_prob),
    }
    print(f"\n[{name}]")
    for k, v in metrics.items():
        print(f"  {k:10s}: {v:.4f}")
    print(classification_report(y_test, y_pred, target_names=["benign", "tunneling"]))

    plot_confusion(y_test, y_pred, name)
    plot_feature_importance(model, X_test.columns, name)

    fpr, tpr, _ = roc_curve(y_test, y_prob)
    metrics["_roc"] = (fpr, tpr, metrics["roc_auc"])
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate trained DNS detectors.")
    parser.add_argument(
        "--models-dir",
        default=str(MODELS_DIR),
        help="Directory containing rf.pkl and xgb.pkl.",
    )
    args = parser.parse_args()
    models_dir = Path(args.models_dir)

    _ensure_dirs()
    X_test, y_test = load_test_split()

    rf = joblib.load(models_dir / "rf.pkl")
    xgb = joblib.load(models_dir / "xgb.pkl")

    rf_metrics = evaluate_model("RF", rf, X_test, y_test)
    xgb_metrics = evaluate_model("XGB", xgb, X_test, y_test)

    plot_roc(
        {
            "Random Forest": rf_metrics["_roc"],
            "XGBoost": xgb_metrics["_roc"],
        }
    )

    # Summary table
    summary = pd.DataFrame(
        {
            "Random Forest": {k: v for k, v in rf_metrics.items() if not k.startswith("_")},
            "XGBoost": {k: v for k, v in xgb_metrics.items() if not k.startswith("_")},
        }
    ).T
    out = ROOT / "reports" / "metrics.csv"
    summary.to_csv(out)
    print(f"\nMetrics summary written to {out}")
    print(summary.round(4))


if __name__ == "__main__":
    main()

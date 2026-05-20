# MLP — DNS Tunneling Detection

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/df-DNS-Tunneling-Detection/DNS_Tunneling_Detection/blob/main/deep_learning/04_mlp_e2e.ipynb)

Trains a **Multi-Layer Perceptron (MLP)** on tabular flow features for binary classification: **benign vs tunneling**. Compares against Random Forest and XGBoost on the same data.

Click the badge above to open the end-to-end notebook directly in Colab — no clone or install needed.

---

## Table of Contents

- [Overview](#overview)
- [How to Run](#how-to-run)
- [Notebook Sections](#notebook-sections)
- [Hyperparameters](#hyperparameters)
- [Expected Results](#expected-results)

---

## Overview

```
CIC-DoHBrw-2020 dataset (tabular flow features)
    │
    ├── load + preprocess (label encoding, train/test split)
    │
    ├── train 3 models:
    │   ├── MLP (sklearn MLPClassifier)
    │   ├── Random Forest
    │   └── XGBoost
    │
    └── evaluate all 3:
        - Accuracy, Precision, Recall, F1, ROC-AUC
        - Confusion matrices
        - ROC curves (overlaid)
        - PR curves (overlaid)
        - Metric comparison bar chart
        - Feature importance (RF + XGBoost)
```

**Why MLP?**
- Neural network baseline on tabular data — complements tree-based models
- No GPU required (sklearn MLPClassifier runs on CPU)
- Same features as RF/XGBoost for fair comparison
- Good for the project defense: shows deep learning knowledge on non-image/non-text data

---

## How to Run

### Option A — Colab (recommended)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/df-DNS-Tunneling-Detection/DNS_Tunneling_Detection/blob/main/deep_learning/04_mlp_e2e.ipynb)

1. Click the badge
2. Click **Runtime → Run all**

The notebook clones the repo, installs dependencies, loads data, trains all models, and produces all plots — fully self-contained.

### Option B — Local

```bash
git clone https://github.com/df-DNS-Tunneling-Detection/DNS_Tunneling_Detection.git
cd DNS_Tunneling_Detection/deep_learning
pip install -r requirements.txt

# Open and run the notebook
jupyter notebook 04_mlp_e2e.ipynb
```

---

## Notebook Sections

| # | Section | What happens |
|---|---------|-------------|
| 1 | Setup | Clone repo, install dependencies |
| 2 | Load Data | Read CSV, show class counts |
| 3 | Preprocessing | Label encoding, train/test split |
| 4 | MLP Training | Train MLPClassifier on flow features |
| 5 | RF + XGBoost | Train classical models for comparison |
| 6 | Evaluation | Metrics, classification reports |
| 7 | Confusion Matrices | Per-model confusion matrix plots |
| 8 | ROC Curves | All 3 models overlaid |
| 9 | PR Curves | Precision-recall comparison |
| 10 | Metric Bars | Side-by-side bar chart |
| 11 | Feature Importance | RF + XGBoost feature importance |
| 12 | Inference Demo | Classify sample queries live |

---

## Hyperparameters

### MLP (sklearn MLPClassifier)

| Parameter | Value | Notes |
|-----------|-------|-------|
| hidden_layer_sizes | (128, 64, 32) | 3 hidden layers |
| activation | relu | Standard for tabular data |
| solver | adam | Adaptive learning rate |
| max_iter | 500 | Enough for convergence |
| random_state | 42 | Reproducibility |

### RF / XGBoost

Standard defaults with `random_state=42` — see `src/train.py` for details.

---

## Expected Results

On the CIC-DoHBrw-2020 dataset:

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|-------|----------|-----------|--------|----|---------|
| MLP | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.99 |
| Random Forest | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.99 |
| XGBoost | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.99 |

All three models achieve similar performance on this dataset because the flow features are highly discriminative. The MLP validates that the signal is learnable by a neural network, not just tree ensembles.

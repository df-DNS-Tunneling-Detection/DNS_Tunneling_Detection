# DistilBERT — DNS Tunneling Detection

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/df-DNS-Tunneling-Detection/DNS_Tunneling_Detection/blob/main/llm/04_distilbert_e2e.ipynb)

Fine-tunes `distilbert-base-uncased` on raw DNS query strings for binary classification: **benign vs tunneling**. No hand-crafted features needed — the model learns directly from raw text.

Click the badge above to open the end-to-end notebook directly in Colab — no clone or install needed. Just enable T4 GPU and run all cells.

---

## Table of Contents

- [Overview](#overview)
- [Option A — Colab Notebook (Recommended)](#option-a--colab-notebook-recommended)
- [Option B — Python Scripts on Colab](#option-b--python-scripts-on-colab)
- [Hyperparameters](#hyperparameters)
- [Files](#files)
- [Expected Results](#expected-results)

---

## Overview

```
Raw DNS query strings (270K samples)
    │
    ├── tokenize with DistilBERT tokenizer (max_length=128)
    │
    ├── 80% train / 10% val / 10% test (stratified, random_state=42)
    │
    ├── fine-tune DistilBERTForSequenceClassification
    │   - 3 epochs, lr=2e-5, batch_size=64
    │   - fp16 on T4 GPU, ~30-60 min
    │
    └── evaluate vs Random Forest & XGBoost
        - F1, ROC-AUC, PR-AUC, Precision, Recall
        - confusion matrices, ROC curves, PR curves
        - side-by-side metric comparison
```

**Why DistilBERT?**
- 66M params — small enough for free Colab T4, big enough to learn DNS patterns
- No feature engineering required (raw query text in, prediction out)
- Pretrained on English text, already understands character-level patterns
- Built-in sequence classification head for binary tasks

---

## Option A — Colab Notebook (Recommended)

The notebook `04_distilbert_e2e.ipynb` runs the entire pipeline end-to-end in a single file. Best for the project defense and presentations.

### Step 1 — Open Colab

Click the **Open in Colab** badge at the top of this README (or in the main project README). The notebook opens directly in Colab — no need to upload anything.

Alternatively:
1. Go to [colab.google.com](https://colab.google.com)
2. Click **File → Upload notebook**
3. Upload `llm/04_distilbert_e2e.ipynb`

### Step 2 — Enable GPU

1. Click **Runtime → Change runtime type**
2. Set **Hardware accelerator** to **T4 GPU**
3. Click **Save**

### Step 3 — Upload Your Dataset

1. Click the **folder icon** in the left sidebar (file browser)
2. Right-click in the file panel → **New folder** → name it `data`
3. Inside `data/`, create another folder called `raw`
4. Right-click `raw` → **Upload** → select your CSV file (e.g. `sample.csv` or your 270K CIC dataset)

Your file structure in Colab should look like:

```
/content/
├── data/
│   └── raw/
│       └── your-dataset.csv
└── llm/
    └── 04_distilbert_e2e.ipynb
```

### Step 4 — Update the DATA_PATH cell

In the **Configuration** cell, change:

```python
DATA_PATH = Path("../data/raw/sample.csv")
```

to:

```python
DATA_PATH = Path("../data/raw/your-dataset.csv")
```

Replace `your-dataset.csv` with your actual filename.

### Step 5 — Run All Cells

1. Click **Runtime → Run all** (or press `Ctrl+F9`)
2. Wait for training to complete (~30-60 min on T4 for 270K samples)
3. All figures are saved to `llm/figures/` and the model to `llm/models/distilbert/`

### What the notebook does (16 sections):

| # | Section | What happens |
|---|---------|-------------|
| 1 | Configuration | Set model, hyperparams, paths |
| 2 | Load Data | Read CSV, show class counts |
| 3 | EDA | Class balance, length/entropy distributions, sample queries |
| 4 | Split | 80/10/10 stratified train/val/test |
| 5 | Tokenization | DistilBERT tokenizer on raw queries |
| 6 | Load Model | `distilbert-base-uncased` with classification head |
| 7 | Fine-Tuning | 3 epochs with epoch-level validation |
| 8 | Save Model | Model + tokenizer to disk |
| 9 | DistilBERT Eval | Test metrics, classification report, confusion matrix |
| 10 | Classical ML | Train RF + XGBoost on same data |
| 11 | Comparison | Side-by-side metric table + bar chart |
| 12 | ROC Curves | All 3 models overlaid on one plot |
| 13 | PR Curves | Precision-recall for all 3 models |
| 14 | Feature Importance | Classical ML feature importance plots |
| 15 | Inference Demo | Classify 8 sample queries live |
| 16 | Summary | Final comparison table |

---

## Option B — Python Scripts on Colab

Use the standalone `.py` scripts for command-line workflow, hyperparameter sweeps, or automation.

### Step 1 — Open a Colab Terminal

1. Go to [colab.google.com](https://colab.google.com)
2. Create a **new notebook**
3. Enable GPU: **Runtime → Change runtime type → T4 GPU**

### Step 2 — Clone the Repository

```python
!git clone https://github.com/df-DNS-Tunneling-Detection/DNS_Tunneling_Detection.git
%cd DNS_Tunneling_Detection/llm
```

### Step 3 — Install Dependencies

```python
!pip install -r requirements.txt
```

### Step 4 — Upload Your Dataset

Upload your CSV to `data/raw/` in the cloned repo:

```python
from google.colab import files
import os

os.makedirs("../data/raw", exist_ok=True)
print("Upload your CSV file (must have 'query' and 'label' columns):")
uploaded = files.upload()

for filename in uploaded.keys():
    os.rename(filename, f"../data/raw/{filename}")
    print(f"Saved to ../data/raw/{filename}")
```

Or use the synthetic sample for a smoke test:

```python
!python ../src/generate_sample.py
```

### Step 5 — Train

Basic training:

```python
!python train.py --data ../data/raw/your-dataset.csv
```

With custom hyperparameters:

```python
!python train.py \
    --data ../data/raw/your-dataset.csv \
    --epochs 5 \
    --batch-size 64 \
    --lr 3e-5 \
    --max-length 128
```

Full options:

| Flag | Default | Description |
|------|---------|-------------|
| `--data` | `../data/raw/sample.csv` | Path to CSV or directory of CSVs |
| `--epochs` | `3` | Number of training epochs |
| `--batch-size` | `32` | Per-device batch size |
| `--lr` | `2e-5` | Learning rate |
| `--max-length` | `128` | Max tokenization length |
| `--output-dir` | `models/distilbert` | Where to save model |

### Step 6 — Evaluate

```python
!python evaluate.py
```

This will:
- Load the fine-tuned DistilBERT
- Load the classical RF + XGBoost models (from `../models/`)
- Run all three on the same test set
- Print metrics, classification reports
- Save comparison plots to `figures/`
- Save `metrics_comparison.csv`

### Step 7 — Predict on New Queries

Single query:

```python
!python predict.py "aXk1bG9yZW0gaXBzdW0gZG9sb3Igc2l0.tunnel.evil.com"
```

Multiple queries from a file:

```python
!python predict.py --queries queries.txt
```

Batch prediction from CSV:

```python
!python predict.py --csv ../data/raw/sample.csv
```

### Step 8 — Download Results

```python
from google.colab import files

# Download the trained model
!zip -r distilbert_model.zip models/distilbert/
files.download("distilbert_model.zip")

# Download evaluation figures
!zip -r figures.zip figures/
files.download("figures.zip")

# Download metrics
files.download("metrics_comparison.csv")
```

---

## Hyperparameters

### Recommended settings by dataset size

| Dataset Size | Epochs | Batch Size | Learning Rate | Est. Time (T4) |
|-------------|--------|------------|---------------|----------------|
| < 10K | 5 | 16 | 2e-5 | ~2 min |
| 10K - 100K | 3 | 32 | 2e-5 | ~15 min |
| 100K - 500K | 3 | 64 | 2e-5 | ~45 min |
| > 500K | 2 | 64 | 3e-5 | ~60 min |

### What each hyperparameter does

- **epochs**: How many times the model sees the full training data. More epochs = longer training, risk of overfitting.
- **batch-size**: Samples processed per gradient step. Larger = faster training, more GPU memory. T4 handles batch_size=64 easily.
- **lr (learning rate)**: Step size for weight updates. 2e-5 is the standard for BERT fine-tuning. Too high = unstable, too low = slow.
- **max-length**: Tokenization cutoff. DNS queries are usually < 253 chars, so 128 tokens is sufficient.

---

## Files

| File | Purpose |
|------|---------|
| `train.py` | Fine-tune DistilBERT, save model + tokenizer + test split |
| `evaluate.py` | Full evaluation + comparison with classical ML (RF, XGBoost) |
| `predict.py` | Inference on new queries (CLI, file, or CSV input) |
| `04_distilbert_e2e.ipynb` | End-to-end notebook (all 16 steps, for defense/presentation) |
| `requirements.txt` | Python dependencies |
| `README.md` | This file |

### Generated after running

| Path | Contents |
|------|----------|
| `models/distilbert/` | Fine-tuned model + tokenizer (safetensors + config) |
| `test_split.csv` | Test split for consistent evaluation |
| `metrics_comparison.csv` | Side-by-side metrics for all 3 models |
| `figures/*.png` | All evaluation plots (confusion, ROC, PR, bars, feature importance) |

---

## Expected Results

On the synthetic `sample.csv` (4K samples), all models score ~1.0 because the data is cleanly separable.

On real CIC datasets (270K samples), expected results:

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|-------|----------|-----------|--------|----|---------|
| DistilBERT | ≥ 0.98 | ≥ 0.98 | ≥ 0.98 | ≥ 0.98 | ≥ 0.99 |
| Random Forest | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.99 |
| XGBoost | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.99 |

The DistilBERT model may show a slight edge on harder cases (queries that mimic benign patterns) because it learns character-level patterns directly, rather than relying on the 11 hand-crafted features.

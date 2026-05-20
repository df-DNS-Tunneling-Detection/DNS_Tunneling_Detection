<h1 align="center">DNS Tunneling Detection</h1>

<p align="center">
  A machine-learning pipeline that flags DNS tunneling traffic from query metadata.<br/>
  Random Forest &amp; XGBoost on hand-crafted statistical features.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="python">
  <img src="https://img.shields.io/badge/sklearn-1.3%2B-orange.svg" alt="scikit-learn">
  <img src="https://img.shields.io/badge/xgboost-2.0%2B-success.svg" alt="xgboost">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey.svg" alt="license">
  <img src="https://img.shields.io/badge/status-research-yellow.svg" alt="status">
</p>

<p align="center">
  <a href="https://colab.research.google.com/github/df-DNS-Tunneling-Detection/DNS_Tunneling_Detection/blob/main/notebooks/colab_demo.ipynb">
    <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab">
  </a>
</p>

> **Try it instantly — no install needed.** Click the *Open in Colab* badge above to run the full pipeline (data → features → training → metrics → plots) in your browser. The notebook is fully self-contained: every function is embedded, so you don't even need to clone the repo.

---

## Table of Contents

- [Background](#background)
- [Approach](#approach)
- [Results](#results)
- [Repository Layout](#repository-layout)
- [Quick Start](#quick-start)
- [Datasets](#datasets)
- [Feature Set](#feature-set)
- [Reproducing the Results](#reproducing-the-results)
- [Notebooks](#notebooks)
- [Deep Learning Extension (MLP)](#deep-learning-extension-mlp)
- [Limitations](#limitations)
- [References](#references)
- [License](#license)

---

## Background

DNS is one of the most permissive protocols on the modern Internet — port 53 is open almost everywhere, and few organisations deeply inspect query text. Attackers abuse this trust by **encoding payload bytes into the subdomain portion of DNS queries**, building a covert command-and-control or data-exfiltration channel that is hard to distinguish from regular name resolution. This technique is called **DNS tunneling**, and is the backbone of tools such as `iodine`, `dnscat2`, and `dns2tcp`.

Signature-based defences (Suricata / Snort rules against known C2 domains) are brittle: any change to the encoding or destination defeats them. A **statistical learning** approach is more robust — it captures the *shape* of tunneled traffic rather than the bytes of a particular tool.

This project trains two classical-ML detectors (Random Forest and XGBoost) on a compact set of metadata features extracted from individual DNS queries.

## Approach

```text
            ┌──────────────────────┐
   queries  │   src/preprocess.py  │   load CIC datasets, normalise labels
            └──────────┬───────────┘
                       │
            ┌──────────▼───────────┐
            │   src/features.py    │   entropy, length, n-grams, char ratios
            └──────────┬───────────┘
                       │
            ┌──────────▼───────────┐
            │     src/train.py     │   RandomForest + XGBoost (5-fold CV)
            └──────────┬───────────┘
                       │
            ┌──────────▼───────────┐
            │   src/evaluate.py    │   metrics, confusion matrix, ROC, importances
            └──────────────────────┘
```

The pipeline is **dataset-agnostic**: it works on any CSV with a query/text column and a binary label column, and equally well on the pre-extracted feature CSVs published with the CIC datasets.

## Results

Expected metrics on **CIRA-CIC-DoHBrw-2020** (after running `python -m src.evaluate`):

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|:------|:--------:|:---------:|:------:|:--:|:-------:|
| Random Forest | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.99 |
| XGBoost | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.99 |

> Fill in the exact numbers from your run — `reports/metrics.csv` is written automatically.

Figures saved by `evaluate.py` (in `reports/figures/`):

- `confusion_matrix_rf.png`, `confusion_matrix_xgb.png`
- `roc_comparison.png`
- `feature_importance_rf.png`, `feature_importance_xgb.png`

## Repository Layout

```
dns-tunneling/
├── src/                       # production code (classical ML)
│   ├── preprocess.py          # dataset loading + label normalisation
│   ├── features.py            # 11 metadata features per query
│   ├── train.py               # cross-validation, fit, persist models
│   ├── predict.py             # score data with a pretrained .pkl (Scenario 2A)
│   ├── evaluate.py            # metrics + figures
│   └── generate_sample.py     # synthetic data for smoke tests
├── deep_learning/             # MLP deep learning pipeline
│   ├── 04_mlp_e2e.ipynb       # end-to-end notebook for defense
│   ├── requirements.txt       # deep learning dependencies
│   └── README.md              # detailed MLP setup guide
├── notebooks/
│   ├── colab_demo.ipynb       # self-contained Colab notebook (one-click run)
│   ├── 01_eda.ipynb           # class balance, length & entropy distributions
│   ├── 02_feature_engineering.ipynb
│   └── 03_modeling.ipynb      # end-to-end demo for the defense
├── data/
│   ├── raw/                   # downloaded CSVs (gitignored)
│   └── processed/             # engineered feature matrix
├── models/                    # rf.pkl, xgb.pkl (pretrained, shipped in repo)
├── reports/
│   ├── figures/               # plots saved by evaluate.py
│   ├── metrics.csv            # final metric table
│   └── report.md              # written report
├── requirements.txt
├── .gitignore
└── README.md
```

## Quick Start

Two ways to run, two options each. Pick whichever fits your environment.

### Scenario 1 — Google Colab (zero setup)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/df-DNS-Tunneling-Detection/DNS_Tunneling_Detection/blob/main/notebooks/colab_demo.ipynb)

Click the badge, then in section 3 of the notebook pick **one** option:

| Option | Time | What it does |
|---|---|---|
| **1A — Use pretrained models** *(fastest)* | ~10 s | Downloads `rf.pkl` and `xgb.pkl` from this repo, scores the held-out test split, shows metrics + plots. |
| **1B — Train from scratch** | ~1 min | Fits Random Forest + XGBoost on the bundled CIC sample with 5-fold CV, then evaluates. |

### Scenario 2 — Run locally

```powershell
git clone https://github.com/df-DNS-Tunneling-Detection/DNS_Tunneling_Detection.git
cd DNS_Tunneling_Detection

python -m venv .venv
.venv\Scripts\Activate.ps1               # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Then pick **one** option:

#### Option 2A — Use the pretrained models *(fastest)*

```powershell
python -m src.predict --model models/rf.pkl
python -m src.predict --model models/xgb.pkl
```

`predict.py` loads the shipped `.pkl`, scores `data/sample/test_split.csv`, and prints accuracy / F1 / ROC-AUC. Pass `--data path/to/your.csv` to score a different CSV.

#### Option 2B — Train from scratch

```powershell
python -m src.train --data data/sample/doh_sample.csv
python -m src.evaluate
```

`train.py` does 5-fold CV on Random Forest and XGBoost, saves new `.pkl` files into `models/`, then `evaluate.py` writes confusion-matrix, ROC, and feature-importance PNGs into `reports/figures/`.

---

## Datasets

### Bundled sample (10 000 rows, ~4.5 MB)

A balanced, stratified sample from **CIRA-CIC-DoHBrw-2020** ships in this repo at [`data/sample/doh_sample.csv`](data/sample/doh_sample.csv). 5 000 benign + 5 000 malicious DoH flows, with all 33 flow-level features and the original `Label` column. Big enough to train and produce meaningful metrics; small enough for git.

```powershell
python -m src.train --data data/sample/doh_sample.csv
python -m src.evaluate
```

### Full datasets (download separately)

Both supported datasets are released by the **Canadian Institute for Cybersecurity** and require free registration to download.

| Dataset | Description | Link |
|---|---|---|
| **CIRA-CIC-DoHBrw-2020** | DoH (DNS-over-HTTPS) traffic from regular browsers and from `dns2tcp`, `DNSCat2`, `Iodine`. ~270 K flows after extraction. | [link](https://www.unb.ca/cic/datasets/dohbrw-2020.html) |
| **CIC-Bell-DNS-2021** | DNS-based malicious domain classification (benign / malware / phishing / spam). | [link](https://www.unb.ca/cic/datasets/dns-2021.html) |

Place the downloaded CSV files under `data/raw/` — the directory is gitignored. The loader auto-detects the format:

```powershell
# CIC-DoHBrw-2020 (uses Label column)
python -m src.train --data data/raw/CICDoHBrw2020/

# CIC-Bell-DNS-2021 (filename-encoded labels)
python -m src.train --data data/raw/CICBellDNS2021/CSVs/
```

If you cannot access the CIC datasets, `src/generate_sample.py` produces a synthetic stand-in (2 000 benign + 2 000 base32-style tunneling queries).

## Feature Set

Each query is reduced to **11 numeric features** by `src/features.py`:

| Feature | Type | Intuition |
|---|---|---|
| `query_length` | int | Tunneled queries carry payload → longer |
| `subdomain_length` | int | Payload lives in the subdomain |
| `entropy` | float | Shannon entropy of characters; encoded payloads ≈ uniform |
| `bigram_entropy` | float | Captures higher-order randomness |
| `digit_ratio` | float | Base32/64 encodings are digit-heavy |
| `uppercase_ratio` | float | Mixed-case alphabets in encoded text |
| `unique_char_count` | int | Larger character set → more random |
| `vowel_consonant_ratio` | float | Natural names have English-like vowel rates |
| `label_count` | int | Many short labels can indicate chunked exfiltration |
| `longest_label_length` | int | DNS allows up to 63 chars per label; tunnels often max it out |
| `non_alphanum_ratio` | float | Encoding padding / separators |

Shannon entropy is computed as $H(X) = -\sum_i p_i \log_2 p_i$ over the empirical character distribution of the query.

## Reproducing the Results

```powershell
# Train both models with 5-fold cross-validation
python -m src.train --data data/raw/CIRA-CIC-DoHBrw-2020/

# Evaluate on the held-out test split and write figures + metrics.csv
python -m src.evaluate
```

The exact 80 / 20 train / test split is reproducible — `random_state=42` is fixed in `src/preprocess.py`.

## Notebooks

The notebooks are designed to be **run top-to-bottom** for the project defense:

| Notebook | What it shows |
|---|---|
| [`notebooks/colab_demo.ipynb`](notebooks/colab_demo.ipynb) | **Self-contained Colab notebook** — everything in one file, no clone required. Best entry point. [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/df-DNS-Tunneling-Detection/DNS_Tunneling_Detection/blob/main/notebooks/colab_demo.ipynb) |
| [`notebooks/01_eda.ipynb`](notebooks/01_eda.ipynb) | Class balance, query length distribution, entropy distribution, sample queries per class |
| [`notebooks/02_feature_engineering.ipynb`](notebooks/02_feature_engineering.ipynb) | Walks through every feature on benign vs tunneling examples, plots per-class distributions, correlation heatmap |
| [`notebooks/03_modeling.ipynb`](notebooks/03_modeling.ipynb) | **Demo notebook (local)** — full pipeline end-to-end: load → features → cross-validate → fit → confusion matrices → ROC → feature importance |
| [`deep_learning/04_mlp_e2e.ipynb`](deep_learning/04_mlp_e2e.ipynb) | **MLP end-to-end** — load data → train MLP + RF + XGBoost → evaluate → compare → ROC/PR curves → inference demo. [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/df-DNS-Tunneling-Detection/DNS_Tunneling_Detection/blob/main/deep_learning/04_mlp_e2e.ipynb) |

## Deep Learning Extension (MLP)

In addition to the classical ML pipeline (Random Forest + XGBoost on hand-crafted features), this project includes a **Multi-Layer Perceptron (MLP) deep learning pipeline** that trains a neural network on the same tabular flow features.

### Why MLP?

| Aspect | Classical ML (RF/XGBoost) | MLP |
|--------|--------------------------|-----|
| Input | Hand-crafted flow features | Same flow features |
| Feature engineering | Required | Same features used |
| Model type | Tree ensemble | Neural network |
| Interpretability | High (feature importance) | Medium (weight analysis) |
| Deployment | CPU-friendly | CPU-friendly |

### Quick Start — MLP

**Notebook (recommended for defense)**

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/df-DNS-Tunneling-Detection/DNS_Tunneling_Detection/blob/main/deep_learning/04_mlp_e2e.ipynb)

Click the badge to open the MLP notebook directly in Colab. Then:
1. Click **Runtime → Run all**

The notebook trains an MLP alongside RF and XGBoost, evaluates all three, and produces comparison plots (ROC, PR, confusion matrices, metric bars).

### MLP Results

Expected metrics on the CIC dataset:

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|-------|----------|-----------|--------|----|---------|
| MLP | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.99 |
| Random Forest | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.99 |
| XGBoost | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.97 | ≥ 0.99 |

Full setup guide: see [`deep_learning/README.md`](deep_learning/README.md)
---

## Limitations

### Classical ML (RF / XGBoost)

- We use **only single-query metadata**. Flow-level features (rate, periodicity, fan-out) would catch slower / stealthier tunnels.
- We assume a vantage point with access to **query text** (resolver logs, on-host telemetry, or unencrypted DNS). For DoH the network observer needs TLS interception or endpoint visibility.
- An attacker who **shapes payloads to mimic benign distributions** (e.g. Markov-generated subdomains trained on Alexa-Top-1M) is harder to flag.
- The CIC datasets contain a small number of tunneling tools; generalisation to unseen tools is the right thing to measure for a follow-up.

### MLP (Deep Learning)

- **Same feature set** — uses the same hand-crafted features as classical ML, so it inherits the same feature-quality ceiling.
- **Less interpretable** — unlike RF/XGBoost feature importance, MLP weights are harder to explain intuitively.
- **Hyperparameter sensitive** — learning rate, hidden layer sizes, and regularization need tuning for best results.
- **No GPU advantage on tabular data** — unlike NLP/vision, MLP on tabular features does not benefit significantly from GPU acceleration.

## References

1. Canadian Institute for Cybersecurity. *CIRA-CIC-DoHBrw-2020*. https://www.unb.ca/cic/datasets/dohbrw-2020.html
2. Canadian Institute for Cybersecurity. *CIC-Bell-DNS-2021*. https://www.unb.ca/cic/datasets/dns-2021.html
3. Aiello, M., Mongelli, M., & Papaleo, G. (2013). *Basic classifiers for DNS tunneling detection.*
4. Yu, B., Pan, J., Hu, J., Nascimento, A., & De Cock, M. (2018). *Character level based detection of DNS tunneling.*

## License

This project is released under the MIT License — see `LICENSE` for details.

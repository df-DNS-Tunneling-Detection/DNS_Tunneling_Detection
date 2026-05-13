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
├── src/                       # production code
│   ├── preprocess.py          # dataset loading + label normalisation
│   ├── features.py            # 11 metadata features per query
│   ├── train.py               # cross-validation, fit, persist models
│   ├── evaluate.py            # metrics + figures
│   └── generate_sample.py     # synthetic data for smoke tests
├── notebooks/
│   ├── 01_eda.ipynb           # class balance, length & entropy distributions
│   ├── 02_feature_engineering.ipynb
│   └── 03_modeling.ipynb      # end-to-end demo for the defense
├── data/
│   ├── raw/                   # downloaded CSVs (gitignored)
│   └── processed/             # engineered feature matrix
├── models/                    # rf.pkl, xgb.pkl (gitignored)
├── reports/
│   ├── figures/               # plots saved by evaluate.py
│   ├── metrics.csv            # final metric table
│   └── report.md              # written report
├── requirements.txt
├── .gitignore
└── README.md
```

## Quick Start

```powershell
# 1. Clone and enter
git clone <repo-url> dns-tunneling
cd dns-tunneling

# 2. Create a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Smoke-test the pipeline with synthetic data
python -m src.generate_sample
python -m src.train --data data/raw/sample.csv
python -m src.evaluate
```

On Linux / macOS replace `.venv\Scripts\Activate.ps1` with `source .venv/bin/activate`.

## Datasets

Both supported datasets are released by the **Canadian Institute for Cybersecurity** and require free registration to download.

| Dataset | Description | Link |
|---|---|---|
| **CIRA-CIC-DoHBrw-2020** | DoH (DNS-over-HTTPS) traffic from regular browsers and from `dns2tcp`, `DNSCat2`, `Iodine`. Pre-extracted CSV features. | [link](https://www.unb.ca/cic/datasets/dohbrw-2020.html) |
| **CIC-Bell-DNS-2021** | Plaintext DNS traffic, benign vs. malicious. PCAP + CSV. | [link](https://www.unb.ca/cic/datasets/dns-2021.html) |

Place the downloaded CSV files anywhere under `data/raw/`. The loader auto-detects the label and query columns; for the CIC pre-extracted features it falls back to the numeric feature columns directly.

```powershell
python -m src.train --data data/raw/CIRA-CIC-DoHBrw-2020/
```

If you cannot access the CIC datasets, `src/generate_sample.py` produces a synthetic stand-in (2 000 benign + 2 000 base32-style tunneling queries) so every step of the pipeline still runs.

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

The three notebooks are designed to be **run top-to-bottom** for the project defense:

| Notebook | What it shows |
|---|---|
| `notebooks/01_eda.ipynb` | Class balance, query length distribution, entropy distribution, sample queries per class |
| `notebooks/02_feature_engineering.ipynb` | Walks through every feature on benign vs tunneling examples, plots per-class distributions, correlation heatmap |
| `notebooks/03_modeling.ipynb` | **Demo notebook** — full pipeline end-to-end: load → features → cross-validate → fit → confusion matrices → ROC → feature importance |

## Limitations

- We use **only single-query metadata**. Flow-level features (rate, periodicity, fan-out) would catch slower / stealthier tunnels.
- We assume a vantage point with access to **query text** (resolver logs, on-host telemetry, or unencrypted DNS). For DoH the network observer needs TLS interception or endpoint visibility.
- An attacker who **shapes payloads to mimic benign distributions** (e.g. Markov-generated subdomains trained on Alexa-Top-1M) is harder to flag.
- The CIC datasets contain a small number of tunneling tools; generalisation to unseen tools is the right thing to measure for a follow-up.

## References

1. Canadian Institute for Cybersecurity. *CIRA-CIC-DoHBrw-2020*. https://www.unb.ca/cic/datasets/dohbrw-2020.html
2. Canadian Institute for Cybersecurity. *CIC-Bell-DNS-2021*. https://www.unb.ca/cic/datasets/dns-2021.html
3. Aiello, M., Mongelli, M., & Papaleo, G. (2013). *Basic classifiers for DNS tunneling detection.*
4. Yu, B., Pan, J., Hu, J., Nascimento, A., & De Cock, M. (2018). *Character level based detection of DNS tunneling.*

## License

This project is released under the MIT License — see `LICENSE` for details.
#   D N S _ T u n n e l i n g _ D e t e c t i o n  
 
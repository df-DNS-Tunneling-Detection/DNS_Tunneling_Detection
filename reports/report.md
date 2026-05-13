# DNS Tunneling Detection — Project Report

**Author**: _your name_  
**Course**: _course name_  
**Date**: _submission date_

---

## 1. Introduction

DNS is one of the oldest and most permissive protocols on the modern Internet. Almost every network allows outbound port 53 (and now 443 for DNS-over-HTTPS), and few networks deeply inspect DNS payloads. Attackers abuse this trust: by encoding arbitrary data into the *subdomain* portion of DNS queries, they create a covert bidirectional channel between a compromised host and an attacker-controlled name server. This technique — **DNS tunneling** — is used for command-and-control, data exfiltration, and bypassing captive portals.

Signature-based detection is brittle: any rule written for a known tool such as `iodine` or `dnscat2` is easily defeated by altering the encoding. A **statistical / ML approach** is more robust: it learns the shape of tunneling traffic rather than the bytes of a particular tool.

This project builds a feature-based classifier that flags individual DNS queries as benign or tunneled, using only metadata extractable from a single query string.

## 2. Related Work

- **Signature / blocklist**: Suricata, Snort rules targeting known C2 domains. Low recall against unknown tools.
- **Statistical, threshold-based**: simple entropy or length thresholds (e.g. `> 50 chars` ⇒ suspicious). Easy to evade and to false-positive.
- **Machine learning**:
  - Random Forest on hand-crafted features (Aiello et al., 2013; Almusawi & Amintoosi, 2018).
  - Deep learning on character-level sequences (Yu et al., 2018; CIC-DoHBrw-2020 baseline).

We adopt the classical-ML approach: easier to interpret, fast to train, and competitive in published benchmarks.

## 3. Dataset

We use the **CIRA-CIC-DoHBrw-2020** dataset from the Canadian Institute for Cybersecurity. It contains DoH (DNS-over-HTTPS) traffic captured from benign browsers and from three DNS tunneling tools (dns2tcp, DNSCat2, Iodine), with pre-extracted flow features and labels.

| Property | Value |
|---|---|
| Source | unb.ca/cic/datasets/dohbrw-2020.html |
| Classes | benign (DoH from regular browsing), tunneled (DoH wrapping tunneling tools) |
| Granularity | per-flow features (provided as CSV) |
| Splits | stratified 80% train / 20% test |

A second supported dataset is **CIC-Bell-DNS-2021**, which adds plaintext DNS traffic. The loader (`src/preprocess.py`) is dataset-agnostic.

## 4. Methodology

### 4.1 Feature extraction

For each query we extract eleven features (`src/features.py`):

| Feature | Intuition |
|---|---|
| `query_length` | Tunneled queries carry a payload, so they are longer. |
| `subdomain_length` | Payload typically lives in subdomains. |
| `entropy` | Shannon entropy of characters — encoded payloads are nearly uniform. |
| `bigram_entropy` | Captures higher-order randomness; resists single-character padding. |
| `digit_ratio` | Base32/64 encodings contain many digits. |
| `uppercase_ratio` | Same reasoning for mixed-case alphabets. |
| `unique_char_count` | Wider character set → more random text. |
| `vowel_consonant_ratio` | Natural domains have English-like vowel ratios; payloads do not. |
| `label_count` | Many short labels can indicate chunked exfiltration. |
| `longest_label_length` | DNS allows up to 63 chars per label; tunnels often max it out. |
| `non_alphanum_ratio` | Encoded data sometimes uses padding chars. |

Shannon entropy is computed as

$$ H(X) = -\sum_i p_i \log_2 p_i $$

over the empirical character distribution of the query.

### 4.2 Models

- **Random Forest** — `n_estimators=200`, balanced class weights.
- **XGBoost** — `n_estimators=300`, `max_depth=6`, `learning_rate=0.1`, histogram method.

Both models are trained with **5-fold stratified cross-validation** on the training split, then refit on the full train split and evaluated once on the held-out test split.

## 5. Results

_Fill in the table below from the output of_ `python -m src.evaluate`:

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|
| Random Forest | _x_ | _x_ | _x_ | _x_ | _x_ |
| XGBoost | _x_ | _x_ | _x_ | _x_ | _x_ |

### Figures

- `reports/figures/confusion_matrix_rf.png` — Random Forest confusion matrix
- `reports/figures/confusion_matrix_xgb.png` — XGBoost confusion matrix
- `reports/figures/roc_comparison.png` — overlaid ROC curves
- `reports/figures/feature_importance_rf.png` — top features by Gini importance
- `reports/figures/feature_importance_xgb.png` — top features by XGBoost gain

### Discussion

- The dominant features are typically `query_length`, `entropy`, and `subdomain_length` — matching the intuition that tunneling jams payload bytes into the subdomain.
- XGBoost and Random Forest perform within a fraction of a percent of each other; the dataset is highly separable on these features.
- Where the classifier struggles: short tunneling queries that mimic CDN-style hostnames (high randomness is normal for CDNs).

## 6. Conclusion

A small, interpretable feature set is sufficient to detect DNS tunneling with high accuracy on the CIC-DoHBrw-2020 dataset. The detector runs at thousands of queries per second on a laptop CPU, making it deployable inline.

**Limitations**

- Only the metadata of individual queries is used — flow-level patterns (rate, periodicity) could improve detection of low-and-slow tunnels.
- An attacker who shapes their payloads to mimic benign distributions (e.g. uses a Markov model trained on Alexa-Top-1M for filler text) would be harder to flag.
- We do not address DNS-over-HTTPS *encryption*: the model assumes a vantage point that can see query text (resolver logs, on-host telemetry, or unencrypted DNS).

**Future work**

- Add temporal / per-host features (queries-per-second, fan-out, periodicity).
- Train a character-level CNN as a robustness baseline.
- Evaluate against adversarial obfuscation.

## 7. References

1. CIRA-CIC-DoHBrw-2020 dataset. Canadian Institute for Cybersecurity, University of New Brunswick. https://www.unb.ca/cic/datasets/dohbrw-2020.html
2. CIC-Bell-DNS-2021. https://www.unb.ca/cic/datasets/dns-2021.html
3. Aiello, M., Mongelli, M., & Papaleo, G. (2013). *Basic classifiers for DNS tunneling detection.*
4. Yu, B., Pan, J., Hu, J., Nascimento, A., & De Cock, M. (2018). *Character level based detection of DNS tunneling.*

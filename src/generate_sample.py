"""Generate a synthetic DNS-tunneling sample dataset.

This is *only* a smoke-test artifact so the notebooks and training pipeline
run end-to-end without the (registration-gated) CIC datasets. It is NOT a
substitute for a real dataset.

Output: data/raw/sample.csv with columns `query, label`.
  label = 0 -> benign
  label = 1 -> tunneling (base32/base64-ish high-entropy subdomains)
"""

from __future__ import annotations

import argparse
import random
import string
from pathlib import Path

import pandas as pd


BENIGN_TLDS = ["com", "net", "org", "io", "co", "edu", "gov"]
BENIGN_WORDS = [
    "google", "mail", "drive", "docs", "github", "stackoverflow", "amazon",
    "wikipedia", "twitter", "facebook", "instagram", "linkedin", "youtube",
    "reddit", "medium", "apple", "microsoft", "office", "outlook", "azure",
    "cloud", "api", "cdn", "static", "img", "assets", "login", "auth",
    "search", "news", "blog", "shop", "store", "pay", "checkout",
]
BENIGN_SUBS = ["", "www", "mail", "api", "cdn", "static", "auth", "m"]


def gen_benign(rng: random.Random) -> str:
    sub = rng.choice(BENIGN_SUBS)
    word = rng.choice(BENIGN_WORDS)
    tld = rng.choice(BENIGN_TLDS)
    parts = [p for p in (sub, word, tld) if p]
    return ".".join(parts)


def gen_tunneling(rng: random.Random) -> str:
    # 1-2 high-entropy labels of length 30-60, simulating base32 payloads.
    alphabet = string.ascii_lowercase + string.digits
    labels = []
    for _ in range(rng.randint(1, 2)):
        length = rng.randint(30, 60)
        labels.append("".join(rng.choices(alphabet, k=length)))
    domain = rng.choice(["tunnel", "c2", "exfil", "payload"]) + "." + rng.choice(
        ["evil", "attacker", "bad"]
    ) + "." + rng.choice(BENIGN_TLDS)
    return ".".join(labels + [domain])


def build_dataset(n_benign: int, n_malicious: int, seed: int = 0) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = [(gen_benign(rng), 0) for _ in range(n_benign)]
    rows += [(gen_tunneling(rng), 1) for _ in range(n_malicious)]
    rng.shuffle(rows)
    return pd.DataFrame(rows, columns=["query", "label"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-benign", type=int, default=2000)
    parser.add_argument("--n-malicious", type=int, default=2000)
    parser.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent.parent / "data" / "raw" / "sample.csv"),
    )
    args = parser.parse_args()

    df = build_dataset(args.n_benign, args.n_malicious)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Wrote {len(df)} rows to {out}")
    print(df.sample(5, random_state=1))


if __name__ == "__main__":
    main()

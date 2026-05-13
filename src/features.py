"""Feature extraction for DNS queries.

Each function operates on a single query string. `extract_features` applies
all of them to a pandas Series of queries and returns a feature DataFrame.
"""

from __future__ import annotations

import math
from collections import Counter

import numpy as np
import pandas as pd

VOWELS = set("aeiouAEIOU")


def shannon_entropy(s: str) -> float:
    """Shannon entropy of the characters in s (in bits)."""
    if not s:
        return 0.0
    counts = Counter(s)
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def query_length(s: str) -> int:
    return len(s) if s else 0


def subdomain_length(s: str) -> int:
    """Length of everything to the left of the registered domain.

    Approximation: total length minus the last two labels.
    """
    if not s:
        return 0
    parts = s.split(".")
    if len(parts) <= 2:
        return 0
    return sum(len(p) for p in parts[:-2]) + max(0, len(parts) - 3)


def digit_ratio(s: str) -> float:
    if not s:
        return 0.0
    return sum(ch.isdigit() for ch in s) / len(s)


def uppercase_ratio(s: str) -> float:
    if not s:
        return 0.0
    return sum(ch.isupper() for ch in s) / len(s)


def unique_char_count(s: str) -> int:
    return len(set(s)) if s else 0


def vowel_consonant_ratio(s: str) -> float:
    if not s:
        return 0.0
    letters = [ch for ch in s if ch.isalpha()]
    if not letters:
        return 0.0
    vowels = sum(ch in VOWELS for ch in letters)
    consonants = len(letters) - vowels
    if consonants == 0:
        return float(vowels)
    return vowels / consonants


def label_count(s: str) -> int:
    """Number of dot-separated labels."""
    if not s:
        return 0
    return s.count(".") + 1


def longest_label_length(s: str) -> int:
    if not s:
        return 0
    return max(len(p) for p in s.split("."))


def bigram_entropy(s: str) -> float:
    """Shannon entropy over character bigrams."""
    if not s or len(s) < 2:
        return 0.0
    bigrams = [s[i : i + 2] for i in range(len(s) - 1)]
    counts = Counter(bigrams)
    n = len(bigrams)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def non_alphanum_ratio(s: str) -> float:
    """Ratio of characters that are not letters, digits, or dots."""
    if not s:
        return 0.0
    return sum(not (ch.isalnum() or ch == ".") for ch in s) / len(s)


FEATURE_FUNCS = {
    "query_length": query_length,
    "subdomain_length": subdomain_length,
    "entropy": shannon_entropy,
    "bigram_entropy": bigram_entropy,
    "digit_ratio": digit_ratio,
    "uppercase_ratio": uppercase_ratio,
    "unique_char_count": unique_char_count,
    "vowel_consonant_ratio": vowel_consonant_ratio,
    "label_count": label_count,
    "longest_label_length": longest_label_length,
    "non_alphanum_ratio": non_alphanum_ratio,
}


def extract_features(queries: pd.Series) -> pd.DataFrame:
    """Apply every feature function to a Series of query strings.

    Returns a DataFrame with one column per feature, indexed like `queries`.
    """
    queries = queries.fillna("").astype(str)
    data = {name: queries.map(func) for name, func in FEATURE_FUNCS.items()}
    return pd.DataFrame(data, index=queries.index)


if __name__ == "__main__":
    samples = pd.Series(
        [
            "google.com",
            "mail.google.com",
            "aXk1bG9yZW0gaXBzdW0gZG9sb3Igc2l0.tunnel.evil.com",
            "c2VjcmV0LWRhdGEtZXhmaWx0cmF0aW9u.payload.attacker.io",
        ]
    )
    print(extract_features(samples))

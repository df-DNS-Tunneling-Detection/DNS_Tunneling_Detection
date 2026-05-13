"""Dataset loading and cleaning for the DNS tunneling project.

Handles two layouts:

  1. CSV files with raw query text + a binary label column (any CSV with
     `query` / `domain` / `name` text column works).
  2. CIC pre-extracted feature CSVs (CIRA-CIC-DoHBrw-2020 layout) where
     features are already numeric and a `Label` column marks benign / malicious.

The single public entry point is `load_dataset`, which returns a tuple of
(features_or_text_df, labels_series).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
from sklearn.model_selection import train_test_split


# Common column names used across DNS datasets for the raw query string.
_QUERY_CANDIDATES = ("query", "domain", "name", "qname", "Domain", "Query")

# Common label-column names; values are normalized below.
_LABEL_CANDIDATES = ("label", "Label", "class", "Class", "is_malicious", "Type")

# Strings that should be coerced to the positive (tunneling = 1) class.
_POSITIVE_TOKENS = {
    "1",
    "malicious",
    "malware",
    "tunneling",
    "tunnel",
    "doh-malicious",
    "doh_malicious",
    "attack",
    "evil",
    "true",
}


def _find_column(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for name in candidates:
        if name in df.columns:
            return name
    return None


def _normalize_labels(series: pd.Series) -> pd.Series:
    """Map various label encodings to {0, 1}."""
    if pd.api.types.is_numeric_dtype(series):
        return (series > 0).astype(int)
    lower = series.astype(str).str.strip().str.lower()
    return lower.isin(_POSITIVE_TOKENS).astype(int)


def load_csv_files(paths: Iterable[Path]) -> pd.DataFrame:
    """Read and concatenate one or more CSVs."""
    frames = []
    for p in paths:
        frames.append(pd.read_csv(p))
    if not frames:
        raise FileNotFoundError("No CSV files were provided.")
    return pd.concat(frames, ignore_index=True)


def load_cic_bell_dns_2021(directory: str | Path) -> tuple[pd.DataFrame, pd.Series]:
    """Loader for CIC-Bell-DNS-2021 (CSV_benign / CSV_malware / CSV_phishing / CSV_spam).

    Labels are encoded in the filename, not in a column. `benign` -> 0; everything
    else -> 1 (any malicious DNS).
    """
    directory = Path(directory)
    frames = []
    label_map = {
        "csv_benign": 0,
        "csv_malware": 1,
        "csv_phishing": 1,
        "csv_spam": 1,
    }
    for csv in sorted(directory.glob("CSV_*.csv")):
        key = csv.stem.lower()
        if key not in label_map:
            continue
        df = pd.read_csv(csv, low_memory=False)
        df["label"] = label_map[key]
        frames.append(df)
    if not frames:
        raise FileNotFoundError(f"No CSV_*.csv files found in {directory}.")
    return _split_features_labels(pd.concat(frames, ignore_index=True))


def _split_features_labels(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Internal helper: take a labeled DataFrame and return (features, labels)."""
    labels = df["label"].astype(int)
    df = df.drop(columns=["label"])
    # Prefer raw `Domain` (or similar) text column if present.
    query_col = _find_column(df, _QUERY_CANDIDATES)
    if query_col is not None:
        data = df[[query_col]].rename(columns={query_col: "query"}).fillna("")
        data["query"] = data["query"].astype(str).str.replace(r"^b'|'$", "", regex=True)
    else:
        data = df.select_dtypes(include="number").copy()
        if data.empty:
            raise ValueError(f"No usable features. Columns: {list(df.columns)}")
    keep = ~data.duplicated()
    return data[keep].reset_index(drop=True), labels[keep].reset_index(drop=True)


def load_dataset(
    path: str | Path,
    query_col: str | None = None,
    label_col: str | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    """Load a DNS dataset from a CSV file or a directory of CSVs.

    Parameters
    ----------
    path : str | Path
        Either a single CSV file or a directory containing CSV files.
    query_col : str, optional
        Column with raw query text. Auto-detected if not provided.
    label_col : str, optional
        Column with the class label. Auto-detected if not provided.

    Returns
    -------
    (data, labels)
        `data` is a DataFrame containing either the raw query column (if
        present) or the numeric pre-extracted features. `labels` is a 0/1
        Series aligned with `data`.
    """
    path = Path(path)
    if path.is_dir():
        # Auto-detect CIC-Bell-DNS-2021 layout (filename-encoded labels).
        if any(path.glob("CSV_benign.csv")) and any(path.glob("CSV_*.csv")):
            return load_cic_bell_dns_2021(path)
        files = sorted(path.glob("*.csv"))
        df = load_csv_files(files)
    else:
        df = pd.read_csv(path)

    df = df.dropna(how="all").reset_index(drop=True)

    label_col = label_col or _find_column(df, _LABEL_CANDIDATES)
    if label_col is None:
        raise ValueError(
            f"Could not find a label column. Looked for {_LABEL_CANDIDATES}. "
            f"Columns present: {list(df.columns)}"
        )
    labels = _normalize_labels(df[label_col])

    query_col = query_col or _find_column(df, _QUERY_CANDIDATES)
    if query_col is not None:
        data = df[[query_col]].rename(columns={query_col: "query"})
        data = data.fillna("")
        data["query"] = data["query"].astype(str)
    else:
        feature_df = df.drop(columns=[label_col])
        data = feature_df.select_dtypes(include="number").copy()
        if data.empty:
            raise ValueError(
                "No query column and no numeric features found. "
                f"Columns: {list(df.columns)}"
            )

    # Drop duplicates and re-align labels.
    keep = ~data.duplicated()
    data = data[keep].reset_index(drop=True)
    labels = labels[keep].reset_index(drop=True)

    # Median-impute NaNs in numeric features (CIC flow CSVs occasionally have
    # missing ResponseTime values for flows with no response).
    numeric_cols = data.select_dtypes(include="number").columns
    if len(numeric_cols):
        data[numeric_cols] = data[numeric_cols].fillna(data[numeric_cols].median(numeric_only=True))

    return data, labels


def split(
    data: pd.DataFrame,
    labels: pd.Series,
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Stratified 80/20 train/test split."""
    return train_test_split(
        data,
        labels,
        test_size=test_size,
        stratify=labels,
        random_state=random_state,
    )


if __name__ == "__main__":
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw")
    X, y = load_dataset(target)
    print(f"Loaded {len(X)} rows  |  positive: {int(y.sum())}  |  negative: {int((1 - y).sum())}")
    print(X.head())

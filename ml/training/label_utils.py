
"""Utilities for normalizing CICIDS2017 labels."""

import pandas as pd


def normalize_label(label: str) -> str:
    """Normalize known malformed CICIDS2017 Web Attack labels."""
    label = label.strip()

    # Match only the known Web Attack labels.
    if label.startswith("Web Attack") and "Brute Force" in label:
        return "Web Attack - Brute Force"

    if label.startswith("Web Attack") and "XSS" in label:
        return "Web Attack - XSS"

    if label.startswith("Web Attack") and "Sql Injection" in label:
        return "Web Attack - Sql Injection"

    return label


def normalize_labels(labels: pd.Series) -> pd.Series:
    """Normalize labels while preserving missing values."""
    return labels.astype("string").map(
        lambda value: normalize_label(value) if pd.notna(value) else pd.NA
    )

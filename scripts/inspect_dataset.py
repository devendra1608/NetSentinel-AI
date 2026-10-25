
from collections import Counter
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "ml" / "data" / "raw" / "CICIDS2017"
REPORT_DIR = ROOT_DIR / "docs" / "reports"
CHUNK_SIZE = 50_000

# Output files
SUMMARY_FILE = REPORT_DIR / "dataset_inspection_summary.json"
LABEL_FILE = REPORT_DIR / "label_distribution.csv"
QUALITY_FILE = REPORT_DIR / "column_quality.csv"
SCHEMA_FILE = REPORT_DIR / "schema_comparison.json"


def inspect_dataset():
    files = sorted(DATA_DIR.glob("*.csv"))

    if not files:
        raise FileNotFoundError(f"No CSV files found in: {DATA_DIR}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(files)} CSV files")
    print(f"Data directory: {DATA_DIR}")
    print(f"Chunk size: {CHUNK_SIZE:,}\n")

    reference_columns = None
    schema_results = []
    file_results = []
    global_labels = Counter()
    global_quality = Counter()
    global_rows = 0

    for file in files:
        print("=" * 78)
        print(f"FILE: {file.name}")

        file_rows = 0
        file_labels = Counter()
        file_quality = Counter()
        seen_hashes = set()
        duplicate_rows = 0
        columns = None
        label_column = None
        schema_warning = None

        for chunk in pd.read_csv(
            file,
            chunksize=CHUNK_SIZE,
            low_memory=False,
            encoding="utf-8-sig",
        ):
            # Remove accidental whitespace around column names.
            chunk.columns = chunk.columns.str.strip()

            if columns is None:
                columns = list(chunk.columns)
                label_column = next(
                    (col for col in columns if col.casefold() == "label"),
                    None,
                )

                if label_column is None:
                    raise ValueError(f"No Label column in {file.name}")

                if reference_columns is None:
                    reference_columns = columns.copy()
                elif columns != reference_columns:
                    schema_warning = (
                        "Column names or order differ from first CSV"
                    )

                print(f"Columns: {len(columns)}")
                if schema_warning:
                    print(f"WARNING: {schema_warning}")

            file_rows += len(chunk)

            # Count raw labels without silently modifying their spelling.
            labels = chunk[label_column].astype("string").str.strip()
            file_labels.update(labels.fillna("<MISSING LABEL>").value_counts().to_dict())

            # Per-column missing values.
            file_quality.update(
                {
                    f"missing::{col}": int(count)
                    for col, count in chunk.isna().sum().items()
                    if count
                }
            )

            # Convert numeric columns to a NumPy array for infinity checks.
            numeric = chunk.select_dtypes(include="number")
            if not numeric.empty:
                inf_counts = np.isinf(numeric.to_numpy()).sum(axis=0)
                for col, count in zip(numeric.columns, inf_counts):
                    if count:
                        file_quality[f"infinite::{col}"] += int(count)

            # Hash rows to count duplicates across chunks within this file.
            # Hashes are used for memory efficiency; this is not a
            # cross-file duplicate check.
            row_hashes = pd.util.hash_pandas_object(
                chunk,
                index=False,
                categorize=True,
            ).to_numpy()

            for row_hash in row_hashes:
                key = int(row_hash)
                if key in seen_hashes:
                    duplicate_rows += 1
                else:
                    seen_hashes.add(key)

        global_rows += file_rows
        global_labels.update(file_labels)
        global_quality.update(file_quality)

        print(f"Rows: {file_rows:,}")
        print(f"Duplicate rows within this file: {duplicate_rows:,}")
        print(f"Distinct raw labels: {len(file_labels)}")
        print("Labels:")
        for label, count in file_labels.most_common():
            print(f"  {label}: {count:,}")

        file_results.append(
            {
                "file": file.name,
                "rows": file_rows,
                "columns": len(columns or []),
                "duplicate_rows_within_file": duplicate_rows,
                "distinct_labels": len(file_labels),
                "schema_matches_reference": (
                    columns == reference_columns
                ),
            }
        )

        schema_results.append(
            {
                "file": file.name,
                "column_count": len(columns or []),
                "columns": columns or [],
                "matches_reference": columns == reference_columns,
                "warning": schema_warning,
            }
        )

    # Build a per-file and global label distribution table.
    label_rows = []
    for result in file_results:
        file_path = DATA_DIR / result["file"]
        counts = Counter()

        for chunk in pd.read_csv(
            file_path,
            chunksize=CHUNK_SIZE,
            low_memory=False,
            encoding="utf-8-sig",
        ):
            chunk.columns = chunk.columns.str.strip()
            label_col = next(
                col for col in chunk.columns
                if col.casefold() == "label"
            )
            counts.update(
                chunk[label_col].astype("string").str.strip()
                .fillna("<MISSING LABEL>").value_counts().to_dict()
            )

        for label, count in counts.items():
            label_rows.append(
                {
                    "file": result["file"],
                    "label": label,
                    "count": count,
                    "percentage_within_file": round(
                        100 * count / result["rows"], 6
                    ) if result["rows"] else 0,
                }
            )

    for label, count in global_labels.items():
        label_rows.append(
            {
                "file": "__GLOBAL__",
                "label": label,
                "count": count,
                "percentage_within_file": round(
                    100 * count / global_rows, 6
                ) if global_rows else 0,
            }
        )

    pd.DataFrame(label_rows).to_csv(
        LABEL_FILE, index=False, encoding="utf-8"
    )

    quality_rows = []
    for result in file_results:
        file_path = DATA_DIR / result["file"]
        local_quality = Counter()

        for chunk in pd.read_csv(
            file_path,
            chunksize=CHUNK_SIZE,
            low_memory=False,
            encoding="utf-8-sig",
        ):
            chunk.columns = chunk.columns.str.strip()

            for col, count in chunk.isna().sum().items():
                if count:
                    local_quality[f"missing::{col}"] += int(count)

            numeric = chunk.select_dtypes(include="number")
            if not numeric.empty:
                inf_counts = np.isinf(numeric.to_numpy()).sum(axis=0)
                for col, count in zip(numeric.columns, inf_counts):
                    if count:
                        local_quality[f"infinite::{col}"] += int(count)

        for metric, count in local_quality.items():
            kind, column = metric.split("::", 1)
            quality_rows.append(
                {
                    "file": result["file"],
                    "issue": kind,
                    "column": column,
                    "count": count,
                }
            )

    pd.DataFrame(
        quality_rows,
        columns=["file", "issue", "column", "count"],
    ).to_csv(QUALITY_FILE, index=False, encoding="utf-8")

    summary = {
        "dataset": "CICIDS2017",
        "files_inspected": len(files),
        "total_rows": global_rows,
        "total_distinct_raw_labels": len(global_labels),
        "reference_column_count": len(reference_columns or []),
        "all_schemas_match": all(
            result["matches_reference"] for result in schema_results
        ),
        "files": file_results,
        "global_labels": [
            {
                "label": label,
                "count": count,
                "percentage": round(100 * count / global_rows, 6),
            }
            for label, count in global_labels.most_common()
        ],
        "notes": [
            "Raw labels are preserved; no label normalization was applied.",
            "Duplicate counts are per file, not across different files.",
            "Duplicate detection uses 64-bit row hashes.",
        ],
    }

    SUMMARY_FILE.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    SCHEMA_FILE.write_text(
        json.dumps(schema_results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n" + "=" * 78)
    print("GLOBAL SUMMARY")
    print(f"Total rows: {global_rows:,}")
    print(f"Distinct raw labels: {len(global_labels)}")
    print(f"Reference columns: {len(reference_columns or [])}")
    print(
        "All schemas match: "
        + str(all(r["matches_reference"] for r in schema_results))
    )

    print("\nGenerated reports:")
    print(f"  {SUMMARY_FILE.relative_to(ROOT_DIR)}")
    print(f"  {LABEL_FILE.relative_to(ROOT_DIR)}")
    print(f"  {QUALITY_FILE.relative_to(ROOT_DIR)}")
    print(f"  {SCHEMA_FILE.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    inspect_dataset()

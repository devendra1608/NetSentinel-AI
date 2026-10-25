
from pathlib import Path

import duckdb
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "ml" / "data" / "raw" / "CICIDS2017"
REPORT_DIR = ROOT_DIR / "docs" / "reports"
OUTPUT_FILE = REPORT_DIR / "duplicate_report.csv"
DB_FILE = REPORT_DIR / "duplicate_check.duckdb"

MEMORY_LIMIT = "2GB"


def main():
    files = sorted(DATA_DIR.glob("*.csv"))

    if not files:
        raise FileNotFoundError(f"No CSV files found in {DATA_DIR}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    temp_dir = REPORT_DIR / "duckdb_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    results = []

    con = duckdb.connect(str(DB_FILE))

    try:
        con.execute(f"SET memory_limit = '{MEMORY_LIMIT}'")
        con.execute("SET threads = 2")
        con.execute(
            "SET temp_directory = ?",
            [str(temp_dir)],
        )

        for file in files:
            print(f"\nChecking exact duplicates: {file.name}")

            # Parameterize the path rather than interpolating it into SQL.
            con.execute(
                """
                CREATE OR REPLACE TEMP TABLE current_file AS
                SELECT *
                FROM read_csv(
                    ?,
                    header = true,
                    all_varchar = true,
                    sample_size = -1
                )
                """,
                [str(file)],
            )

            total_rows = con.execute(
                "SELECT COUNT(*) FROM current_file"
            ).fetchone()[0]

            # DISTINCT compares complete rows, not row hashes.
            distinct_rows = con.execute(
                "SELECT COUNT(*) FROM (SELECT DISTINCT * FROM current_file)"
            ).fetchone()[0]

            duplicate_rows = total_rows - distinct_rows

            results.append(
                {
                    "file": file.name,
                    "total_rows": total_rows,
                    "distinct_rows": distinct_rows,
                    "duplicate_rows": duplicate_rows,
                    "duplicate_percentage": (
                        round(100 * duplicate_rows / total_rows, 4)
                        if total_rows else 0.0
                    ),
                    "method": "Exact full-row comparison within file",
                }
            )

            print(f"  Total rows:      {total_rows:,}")
            print(f"  Distinct rows:   {distinct_rows:,}")
            print(f"  Duplicate rows:  {duplicate_rows:,}")

            con.execute("DROP TABLE current_file")

    finally:
        con.close()

    report = pd.DataFrame(results)
    report.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

    print("\n" + "=" * 65)
    print("DUPLICATE CHECK SUMMARY")
    print(f"Files checked: {len(results)}")
    print(f"Total rows: {report['total_rows'].sum():,}")
    print(f"Duplicate rows within files: {report['duplicate_rows'].sum():,}")
    print(f"\nReport saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

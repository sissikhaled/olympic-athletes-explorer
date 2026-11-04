"""Phase 1: read-only profiling of the raw Olympic CSV files.

Prints, for every CSV in the given folder: shape, dtypes, missing values,
unique counts, duplicate rows and a few sample values per column.
Nothing is modified; the output feeds docs/data_preparation.md.

Usage:  python -I scripts/profile_raw.py data/raw/olympics
"""
import sys
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)
pd.set_option("display.max_colwidth", 60)


def profile(path: Path) -> None:
    # utf-8-sig strips the byte-order mark found at the start of some files
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    print(f"\n{'=' * 100}\n{path.name}: {len(df):,} rows x {df.shape[1]} columns")
    print(f"exact duplicate rows: {df.duplicated().sum():,}")
    rows = []
    for col in df.columns:
        s = df[col]
        blank = (s.str.strip() == "").sum()
        rows.append({
            "column": col,
            "blank": blank,
            "blank_%": round(100 * blank / len(df), 1),
            "unique": s.nunique(),
            "examples": " | ".join(s[s.str.strip() != ""].drop_duplicates().head(4).str.slice(0, 40)),
        })
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    folder = Path(sys.argv[1])
    for csv in sorted(folder.glob("*.csv")):
        profile(csv)

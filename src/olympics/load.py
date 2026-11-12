"""Read the raw source files exactly as delivered (all columns as text).

Reading everything as `str` with `keep_default_na=False` means pandas does not
guess types or silently turn text such as "NA" or "None" into missing values.
Type conversion happens explicitly in `clean.py`.
"""
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_OLYMPICS = PROJECT_ROOT / "data" / "raw" / "olympics"
RAW_WORLDBANK = PROJECT_ROOT / "data" / "raw" / "worldbank"
REFERENCE = PROJECT_ROOT / "data" / "reference"
PROCESSED = PROJECT_ROOT / "data" / "processed"

OLYMPIC_FILES = {
    "bio": "Olympic_Athlete_Biography.csv",
    "events": "Olympic_Athlete_Event_Details.csv",
    "results": "Olympic_Event_Results.csv",
    "games": "Olympic_Games_Summary.csv",
    "tally": "Olympic_Medal_Tally_History.csv",
    "countries": "Olympic_Country_Profiles.csv",
}


def read_raw_csv(path: Path) -> pd.DataFrame:
    # utf-8-sig removes the byte-order mark at the start of the event-details file
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)


def load_olympics(folder: Path = RAW_OLYMPICS) -> dict[str, pd.DataFrame]:
    return {key: read_raw_csv(folder / name) for key, name in OLYMPIC_FILES.items()}


def load_worldbank(folder: Path = RAW_WORLDBANK) -> dict[str, pd.DataFrame]:
    return {
        "population": pd.read_csv(folder / "population.csv", keep_default_na=False, na_values=[""]),
        "gdp_usd": pd.read_csv(folder / "gdp_usd.csv", keep_default_na=False, na_values=[""]),
    }

"""Download World Bank population and GDP indicators into data/raw/worldbank/.

Source: World Bank Open Data API v2 (https://datahelpdesk.worldbank.org/knowledgebase/articles/889392),
license CC BY 4.0. The API needs no key. Run once; the app never calls the API itself.

Indicators
    SP.POP.TOTL      Population, total
    NY.GDP.MKTP.CD   GDP, current US$

Output: one tidy CSV per indicator with columns
    iso3, country, year, value

Usage:  python scripts/fetch_worldbank.py
"""
from pathlib import Path

import pandas as pd
import requests

INDICATORS = {
    "SP.POP.TOTL": "population",
    "NY.GDP.MKTP.CD": "gdp_usd",
}
API = "https://api.worldbank.org/v2/country/all/indicator/{code}"
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "worldbank"


def fetch(code: str) -> pd.DataFrame:
    params = {"format": "json", "date": "1960:2024", "per_page": 20000, "page": 1}
    rows = []
    while True:
        resp = requests.get(API.format(code=code), params=params, timeout=60)
        resp.raise_for_status()
        meta, data = resp.json()
        rows.extend(data or [])
        if params["page"] >= meta["pages"]:
            break
        params["page"] += 1
    return pd.DataFrame(
        {
            "iso3": r["countryiso3code"],
            "country": r["country"]["value"],
            "year": int(r["date"]),
            "value": r["value"],
        }
        for r in rows
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for code, name in INDICATORS.items():
        df = fetch(code)
        path = OUT / f"{name}.csv"
        df.to_csv(path, index=False)
        print(f"{code:16s} -> {path.name}: {len(df):,} rows, "
              f"{df.value.notna().sum():,} with values, years {df.year.min()}-{df.year.max()}")


if __name__ == "__main__":
    main()

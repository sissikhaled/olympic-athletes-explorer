"""Build data/reference/noc_to_iso3.csv: Olympic NOC code -> ISO 3166 alpha-3.

Needed to (a) join World Bank population/GDP and (b) draw countries on a
world map. Olympic codes often differ from ISO codes (GER/DEU, NED/NLD, ...).

Method, recorded per row in `match_method`:
  name_auto  - country names match after normalisation (accents, case, punctuation)
  manual     - hand-checked entry in MANUAL below
  historic   - former state / special team, deliberately NOT mapped (decision D9)
  no_wb_data - real territory, but the World Bank has no series for it

The output is committed; re-run only if the source data changes.
Usage:  python scripts/build_noc_mapping.py
"""
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pandas as pd  # noqa: E402

from olympics.load import REFERENCE, load_olympics, load_worldbank  # noqa: E402

# Names differ between the IOC list and the World Bank list -> hand-checked
MANUAL = {
    "PRK": "PRK", "COD": "COD", "EGY": "EGY", "FSM": "FSM", "GBR": "GBR", "HKG": "HKG",
    "KGZ": "KGZ", "LAO": "LAO", "NRU": "NRU", "CHN": "CHN", "KOR": "KOR", "MDA": "MDA",
    "LCA": "LCA", "SVK": "SVK", "SOM": "SOM", "VEN": "VEN", "YEM": "YEM",
    "CGO": "COG",  # Republic of the Congo
    "IRI": "IRN", "KSA": "SAU", "PLE": "PSE", "PUR": "PRI", "SKN": "KNA", "VIN": "VCT",
    "BAH": "BHS", "GAM": "GMB", "TAN": "TZA", "ISV": "VIR",
}

# Former states and special teams: kept as they competed (D9), never mapped
HISTORIC = {
    "ANZ", "BOH", "CRT", "TCH", "GDR", "FRG", "URS", "EUN", "YUG", "SCG", "UAR", "WIF",
    "RHO", "SAA", "MAL", "NBO", "NFL", "YAR", "YMD", "VNM", "AHO", "COR",
    "IOA", "AIN", "EOR", "MIX", "ROC", "UNK", "IFR",
}

# Real territories the World Bank does not publish data for
NO_WB_DATA = {"TPE", "COK"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", s)


def main() -> None:
    countries = load_olympics()["countries"].apply(lambda s: s.str.strip())
    countries = countries[~((countries.noc == "ROC") & (countries.country == "ROC"))]
    countries = pd.concat([countries, pd.DataFrame([{"noc": "IFR", "country": "International Federation Representative"}])])
    wb = load_worldbank()["population"].dropna(subset=["iso3"]).drop_duplicates("iso3")
    by_name = dict(zip(wb.country.map(norm), wb.iso3))
    wb_name = dict(zip(wb.iso3, wb.country))

    rows = []
    for noc, country in zip(countries.noc, countries.country):
        if noc in HISTORIC:
            iso3, method = None, "historic"
        elif noc in NO_WB_DATA:
            iso3, method = None, "no_wb_data"
        elif noc in MANUAL:
            iso3, method = MANUAL[noc], "manual"
        elif norm(country) in by_name:
            iso3, method = by_name[norm(country)], "name_auto"
        else:
            iso3, method = None, "UNRESOLVED"
        rows.append({"noc": noc, "country": country, "iso3": iso3,
                     "worldbank_name": wb_name.get(iso3), "match_method": method})

    out = pd.DataFrame(rows).sort_values("noc")
    unresolved = out[out.match_method == "UNRESOLVED"]
    if len(unresolved):
        print(unresolved.to_string(index=False))
        raise SystemExit("Unresolved NOCs: add them to MANUAL, HISTORIC or NO_WB_DATA")
    dupes = out.dropna(subset=["iso3"])
    dupes = dupes[dupes.iso3.duplicated(keep=False)]
    if len(dupes):
        print(dupes.to_string(index=False))
        raise SystemExit("Two NOCs mapped to the same ISO3")

    REFERENCE.mkdir(parents=True, exist_ok=True)
    out.to_csv(REFERENCE / "noc_to_iso3.csv", index=False)
    print(out.match_method.value_counts().to_string())
    print(f"-> {REFERENCE / 'noc_to_iso3.csv'}")


if __name__ == "__main__":
    main()

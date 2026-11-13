"""Load the processed tables once and apply the global filters.

The filter panel writes its state into a `dcc.Store` as a plain dict (see
`DEFAULT_FILTERS`). Charts call `filter_athletes(...)` / `filter_country_games(...)`
with that dict. The `ignore` argument implements the filter-to-tab matrix from
docs/analytical_questions.md §4.1, e.g. the Gender tab ignores the Sex filter
and the Countries tab highlights countries instead of filtering them.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"
REFERENCE = Path(__file__).resolve().parents[1] / "data" / "reference"
# Historic teams NOT folded into a successor: mixed teams and one-off joint teams
NOT_A_PREDECESSOR = {"ANZ", "COR", "CRT", "WIF"}

YEAR_MIN, YEAR_MAX = 1896, 2022

DEFAULT_FILTERS = {
    "years": [YEAR_MIN, YEAR_MAX],
    "season": "Both",            # Both | Summer | Winter
    "sex": "All",                # All | Female | Male
    "sports": [],                # empty = all
    "hide_minor": True,          # hide sports with < 100 athletes
    "countries": [],             # NOC codes; empty = all
}


@lru_cache(maxsize=None)
def table(name: str) -> pd.DataFrame:
    """Read data/processed/<name>.parquet once per process."""
    return pd.read_parquet(PROCESSED / f"{name}.parquet")


@lru_cache(maxsize=1)
def lineage() -> dict[str, str]:
    """Historic team -> present-day successor NOC (URS, EUN, ROC -> RUS; FRG, GDR, SAA -> GER; ...).

    Built from the map-placement table (decision D15): a historic team is folded into the
    present-day NOC whose country it is drawn at. Used where a long-run comparison per
    country reads better with predecessors combined (specialisation heatmap); everywhere
    else teams stay as they competed.
    """
    place = pd.read_csv(REFERENCE / "noc_map_location.csv")
    c = table("countries")
    present = c[c.match_method != "historic"].dropna(subset=["iso3"]).drop_duplicates("iso3")
    noc_of = dict(zip(present.iso3, present.noc))
    out = {}
    for r in place.itertuples():
        succ = noc_of.get(r.place_iso3)
        if succ and succ != r.noc and r.noc not in NOT_A_PREDECESSOR:
            out[r.noc] = succ
    return out


def games_years() -> list[int]:
    return sorted(table("games").year.unique().tolist())


def sport_options(season: str = "Both", hide_minor: bool = True) -> list[dict]:
    s = table("sports")
    if season != "Both":
        s = s[s.season == season]
    if hide_minor:
        s = s[~s.is_minor]
    s = s.sort_values("sport")
    return [{"label": f"{r.sport}" + ("" if r.is_current else " (discontinued)"), "value": r.sport}
            for r in s.itertuples()]


def country_options() -> list[dict]:
    """Countries that ever took part, labelled 'Country name (NOC)'."""
    cg = table("country_games")
    nocs = cg[cg.n_athletes > 0][["noc", "country"]].drop_duplicates("noc").sort_values("country")
    return [{"label": f"{r.country} ({r.noc})", "value": r.noc} for r in nocs.itertuples()]


def _mask(df: pd.DataFrame, f: dict, ignore: tuple[str, ...]) -> pd.Series:
    m = pd.Series(True, index=df.index)
    if "years" not in ignore:
        lo, hi = f["years"]
        m &= df.year.between(lo, hi)
    if "season" not in ignore and f["season"] != "Both":
        m &= df.season == f["season"]
    if "sex" not in ignore and f["sex"] != "All" and "sex" in df:
        m &= df.sex == f["sex"]
    if "sports" not in ignore and "sport" in df:
        if f["sports"]:
            m &= df.sport.isin(f["sports"])
        elif f["hide_minor"] and "is_minor" in df:
            m &= ~df.is_minor
    if "countries" not in ignore and f["countries"]:
        m &= df.noc.isin(f["countries"])
    return m


def filter_athletes(f: dict, ignore: tuple[str, ...] = ()) -> pd.DataFrame:
    """athlete_games (one row per athlete x Games x sport) with the filters applied.

    Cached: one filter change makes several charts ask for the same rows. Callers treat
    the result as read-only (they derive new frames with [], assign, merge ...).
    """
    return _filter_athletes_cached(json.dumps(f, sort_keys=True), tuple(sorted(ignore)))


@lru_cache(maxsize=32)
def _filter_athletes_cached(f_json: str, ignore: tuple[str, ...]) -> pd.DataFrame:
    df = table("athlete_games")
    return df[_mask(df, json.loads(f_json), ignore)]


def filter_events(f: dict, ignore: tuple[str, ...] = ()) -> pd.DataFrame:
    """athlete_events with the filters applied (sex via a join on athlete_id)."""
    df = table("athlete_events")
    m = _mask(df, f, ignore + ("sex",))
    if "sex" not in ignore and f["sex"] != "All":
        athletes = table("athletes")
        ids = athletes.loc[athletes.sex == f["sex"], "athlete_id"]
        m &= df.athlete_id.isin(ids)
    if "sports" not in ignore and not f["sports"] and f["hide_minor"]:
        minor = table("sports").query("is_minor").sport
        m &= ~df.sport.isin(minor)
    return df[m]


def filter_country_games(f: dict, ignore: tuple[str, ...] = ("countries",)) -> pd.DataFrame:
    """country_games filtered by years and season. Countries are highlighted
    rather than filtered by default (Countries-tab rule). Sex and sport do not
    apply: the official tally has neither breakdown."""
    df = table("country_games")
    return df[_mask(df, f, ignore + ("sex", "sports"))]


def summary(f: dict) -> dict:
    """Headline counts for the current filter, used by the filter panel and KPI tiles."""
    a = filter_athletes(f)
    return {
        "athletes": a.athlete_id.nunique(),
        "games": a.edition_id.nunique(),
        "countries": a.noc.nunique(),
        "sports": a.sport.nunique(),
    }

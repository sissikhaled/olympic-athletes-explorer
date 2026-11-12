"""Cleaning: fix types, remove invalid rows, apply decisions D1-D12.

Every function takes raw text DataFrames and returns typed, cleaned DataFrames.
Each step that changes row counts or values is recorded in a `PrepLog`, which
is written to data/processed/prep_log.csv and summarised in
docs/data_preparation.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- constants
INTERCALATED_1906_ID = 4          # D2: not recognised by the IOC
EQUESTRIAN_1956_ID = 48           # D3: merged into ...
SUMMER_1956_ID = 14               # ... the Melbourne 1956 Summer Games
ART_SPORT = "Art Competitions"    # D1: excluded everywhere
MEDALS = ["Gold", "Silver", "Bronze"]
MEDAL_DTYPE = pd.CategoricalDtype(MEDALS, ordered=True)

# Physique plausibility (documented in docs/data_preparation.md)
HEIGHT_RANGE_CM = (120, 230)
WEIGHT_RANGE_KG = (25, 220)
MIN_BMI = 12.0                    # below this a weight is a data-entry error
                                  # (single case: 169 cm / 30 kg)

STATUS_CODES = {
    "AC": "Also competed (no rank)",
    "DNS": "Did not start",
    "DNF": "Did not finish",
    "DQ": "Disqualified",
    "DNQ": "Did not qualify",
    "NP": "Not placed",
    "HC": "Hors concours",
    "HM": "Honourable mention",
    "NM": "No mark",
    "NH": "No height",
    "TNK": "Team not known",
    "MNK": "Mark not known",
    "NVL": "No valid lift",
    "EL": "Eliminated",
}


# ---------------------------------------------------------------- logging
@dataclass
class PrepLog:
    """Collects one entry per preparation step: what was done and its effect."""

    entries: list[dict] = field(default_factory=list)

    def add(self, table: str, step: str, before: int, after: int, note: str = "") -> None:
        self.entries.append(
            {"table": table, "step": step, "rows_before": before,
             "rows_after": after, "rows_removed": before - after, "note": note}
        )

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.entries)


# ---------------------------------------------------------------- helpers
def strip_all(df: pd.DataFrame) -> pd.DataFrame:
    """Trim whitespace in every text column (e.g. the leading space in `country`)."""
    return df.apply(lambda s: s.str.strip().str.replace(r"\s{2,}", " ", regex=True))


def parse_weight(value: str) -> tuple[float, bool]:
    """Return (weight_kg, is_approx).

    '70'      -> (70.0, False)
    '77,5'    -> (77.5, False)   decimal comma
    '80-82'   -> (81.0, True)    range: midpoint (D4)
    '124, 131'-> (127.5, True)   two recorded weights: mean (D4)
    ''        -> (nan, False)
    """
    v = value.strip()
    if not v:
        return np.nan, False
    if re.fullmatch(r"\d+(?:[.,]\d+)?", v):
        return float(v.replace(",", ".")), False
    nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", v)]
    if 2 <= len(nums) <= 3:
        return float(np.mean(nums)), True
    return np.nan, False


def parse_born(born: pd.Series) -> pd.DataFrame:
    """Vectorised birth-date parsing. Returns birth_date, birth_year, birth_is_year_only.

    '4 April 1949' -> exact date
    '1879'         -> year only (D5: age becomes approximate)
    free text like '(c 1880)' or a place name -> missing
    """
    b = born.fillna("").str.strip()
    date = pd.to_datetime(b, format="%d %B %Y", errors="coerce")
    year_only = date.isna() & b.str.fullmatch(r"\d{4}")
    year = date.dt.year.astype("float").where(date.notna(), pd.to_numeric(b.where(year_only), errors="coerce"))
    return pd.DataFrame({"birth_date": date, "birth_year": year, "birth_is_year_only": year_only})


def _parse_games_date(text: str, year: int) -> pd.Timestamp | None:
    """Games dates lack a year ('6 April'), except Tokyo 2020 ('23 July 2021')."""
    text = text.strip()
    if not text or text.startswith("—"):
        return None
    if not re.search(r"\d{4}", text):
        text = f"{text} {year}"
    d = pd.to_datetime(text, format="%d %B %Y", errors="coerce")
    return None if pd.isna(d) else d


# ---------------------------------------------------------------- games
def clean_games(raw: pd.DataFrame, events_raw: pd.DataFrame, log: PrepLog) -> pd.DataFrame:
    g = strip_all(raw)
    n0 = len(g)
    g["edition_id"] = g.edition_id.astype(int)
    g["year"] = g.year.astype(int)

    g = g[g.isHeld == ""]
    log.add("games", "Remove Games cancelled by war (D10)", n0, len(g), "1916, 1940 x2, 1944 x2")
    n1 = len(g)
    with_data = set(events_raw.edition_id.astype(int))
    g = g[g.edition_id.isin(with_data)]
    log.add("games", "Remove future Games with no athlete data (D10)", n1, len(g), "2024, 2026, 2028, 2032")
    n2 = len(g)
    g = g[g.edition_id.isin([INTERCALATED_1906_ID, EQUESTRIAN_1956_ID]) == False]  # noqa: E712
    log.add("games", "Drop 1906 Intercalated (D2); fold 1956 Equestrian into 1956 Summer (D3)", n2, len(g))

    g["season"] = g.edition.str.extract(r"(Summer|Winter)")[0]
    # Start date: official start, else first day of the competition window
    starts = []
    for _, row in g.iterrows():
        d = _parse_games_date(row.start_date, row.year)
        if d is None:
            first = row.competition_date.split("–")[0].strip()
            month = row.competition_date.split("–")[-1].strip().split(" ")[-1]
            if first.isdigit():               # '6 – 13 April' -> '6 April'
                first = f"{first} {month}"
            d = _parse_games_date(first, row.year)
        starts.append(d)
    g["start_date"] = pd.to_datetime(starts)
    g["end_date"] = [_parse_games_date(e, y) for e, y in zip(g.end_date, g.year)]
    g["end_date"] = pd.to_datetime(g.end_date)
    g = g.rename(columns={"country_noc": "host_noc", "edition": "games"})
    cols = ["edition_id", "games", "year", "season", "city", "host_noc", "start_date", "end_date"]
    return g[cols].sort_values(["year", "season"]).reset_index(drop=True)


# ---------------------------------------------------------------- countries
def clean_countries(raw: pd.DataFrame, log: PrepLog) -> pd.DataFrame:
    c = strip_all(raw)
    n0 = len(c)
    # 'ROC' appears twice (as 'ROC' and 'Russian Olympic Committee'): keep the descriptive one
    c = c[~((c.noc == "ROC") & (c.country == "ROC"))]
    c = pd.concat([c, pd.DataFrame([{"noc": "IFR", "country": "International Federation Representative"}])])
    log.add("countries", "Deduplicate ROC; add IFR (found only in biographies)", n0, len(c))
    return c.rename(columns={"noc": "noc", "country": "country"}).reset_index(drop=True)


# ---------------------------------------------------------------- athletes
def clean_athletes(raw: pd.DataFrame, log: PrepLog) -> pd.DataFrame:
    a = strip_all(raw)
    n0 = len(a)
    a["athlete_id"] = a.athlete_id.astype(int)
    a["sex"] = a.sex.astype("category")

    a = pd.concat([a, parse_born(a.born)], axis=1)
    n_free_text = ((a.born != "") & a.birth_year.isna()).sum()

    a["height_cm"] = pd.to_numeric(a.height.replace("", np.nan), errors="coerce")
    w = a.weight.map(parse_weight)
    a["weight_kg"] = [x[0] for x in w]
    a["weight_is_approx"] = [x[1] for x in w]

    # Plausibility: out-of-range values -> missing (never delete the athlete)
    bad_h = ~a.height_cm.between(*HEIGHT_RANGE_CM) & a.height_cm.notna()
    bad_w = ~a.weight_kg.between(*WEIGHT_RANGE_KG) & a.weight_kg.notna()
    a.loc[bad_h, "height_cm"] = np.nan
    a.loc[bad_w, "weight_kg"] = np.nan
    bmi = a.weight_kg / (a.height_cm / 100) ** 2
    bad_bmi = bmi < MIN_BMI
    a.loc[bad_bmi, "weight_kg"] = np.nan

    log.add("athletes", "Parse birth dates (D5)", n0, n0,
            f"exact: {a.birth_date.notna().sum():,}; year only: {a.birth_is_year_only.sum():,}; "
            f"free text -> missing: {n_free_text:,}; blank: {(a.born == '').sum():,}")
    log.add("athletes", "Parse weights (D4)", n0, n0,
            f"approximate (range / two values) -> mean: {a.weight_is_approx.sum():,}")
    log.add("athletes", "Physique plausibility -> missing", n0, n0,
            f"height outside {HEIGHT_RANGE_CM}: {bad_h.sum()}; weight outside {WEIGHT_RANGE_KG}: "
            f"{bad_w.sum()}; BMI < {MIN_BMI}: {bad_bmi.sum()}")

    a = a.rename(columns={"country_noc": "bio_noc"})
    cols = ["athlete_id", "name", "sex", "birth_date", "birth_year", "birth_is_year_only",
            "height_cm", "weight_kg", "weight_is_approx", "bio_noc"]
    return a[cols]


# ---------------------------------------------------------------- athlete-event rows
def _result_status(pos: pd.Series) -> pd.Series:
    """Classify Olympedia's `pos` text.

    '3' / '=6'          -> 'Ranked'           (final placing, '=' means tie)
    '3 h8 r1/2'         -> 'Eliminated in heats/rounds'
    'DNS', 'DNF', ...   -> code description (STATUS_CODES)
    """
    p = pos.str.strip().str.lstrip("'=").str.strip()
    first = p.str.split().str[0].fillna("")
    status = pd.Series("Other", index=pos.index)
    status[p.str.fullmatch(r"\d+")] = "Ranked"
    status[first.str.fullmatch(r"\d+") & ~p.str.fullmatch(r"\d+")] = "Eliminated in heats/rounds"
    for code, label in STATUS_CODES.items():
        status[first == code] = label
    return status


def clean_athlete_events(raw: pd.DataFrame, athlete_ids: set[int], log: PrepLog) -> pd.DataFrame:
    e = strip_all(raw)
    n = len(e)
    e = e.drop_duplicates()
    log.add("athlete_events", "Drop exact duplicate rows (D8)", n, len(e))

    n = len(e)
    e = e[e.sport != ART_SPORT]
    log.add("athlete_events", "Exclude Art Competitions (D1)", n, len(e))

    e["edition_id"] = e.edition_id.astype(int)
    n = len(e)
    e = e[e.edition_id != INTERCALATED_1906_ID]
    log.add("athlete_events", "Drop 1906 Intercalated Games (D2)", n, len(e))

    moved = (e.edition_id == EQUESTRIAN_1956_ID).sum()
    e.loc[e.edition_id == EQUESTRIAN_1956_ID, "edition_id"] = SUMMER_1956_ID
    log.add("athlete_events", "Merge 1956 Equestrian into 1956 Summer (D3)", len(e), len(e),
            f"{moved} rows re-assigned")

    e["athlete_id"] = e.athlete_id.astype(int)
    n = len(e)
    e = e[e.athlete_id.isin(athlete_ids)]
    log.add("athlete_events", "Drop rows whose athlete has no biography", n, len(e),
            "no sex/physique available for these athletes")

    e["result_id"] = e.result_id.astype(int)
    e["medal"] = e.medal.replace("", np.nan).astype(MEDAL_DTYPE)
    e["is_team_event"] = e.isTeamSport.eq("True")
    # one event has inconsistent flags across rows: use the majority per event
    e["is_team_event"] = e.groupby("result_id").is_team_event.transform(lambda s: s.mean() >= 0.5)

    gender = e.event.str.extract(r",\s*(Men|Women|Mixed|Open|Boys)\s*$")[0]
    e["event_gender"] = gender.replace({"Boys": "Men"}).fillna("Open").astype("category")
    e["result_status"] = _result_status(e.pos).astype("category")
    e["final_place"] = pd.to_numeric(
        e.pos.str.strip().str.lstrip("'=").where(e.result_status.eq("Ranked")), errors="coerce"
    ).astype("Int16")

    e = e.rename(columns={"country_noc": "noc", "athlete": "name"})
    cols = ["athlete_id", "edition_id", "noc", "sport", "event", "result_id", "event_gender",
            "is_team_event", "pos", "result_status", "final_place", "medal"]
    return e[cols].reset_index(drop=True)


# ---------------------------------------------------------------- official tally
def clean_tally(raw: pd.DataFrame, art_medals: pd.DataFrame, log: PrepLog) -> pd.DataFrame:
    """Official medal table with D2, D3 and D7 applied.

    art_medals: Art Competitions medals once per event, columns
                edition_id, noc, Gold, Silver, Bronze (from raw athlete events).
    """
    t = strip_all(raw)
    n = len(t)
    for col in ["edition_id", "year", "gold", "silver", "bronze", "total"]:
        t[col] = t[col].astype(int)
    t = t[t.edition_id != INTERCALATED_1906_ID]
    log.add("medal_tally", "Drop 1906 Intercalated (D2)", n, len(t))

    n = len(t)
    t.loc[t.edition_id == EQUESTRIAN_1956_ID, "edition_id"] = SUMMER_1956_ID
    t = (t.rename(columns={"country_noc": "noc"})
          .groupby(["edition_id", "noc"], as_index=False)[["gold", "silver", "bronze"]].sum())
    log.add("medal_tally", "Merge 1956 Equestrian rows into 1956 Summer (D3)", n, len(t),
            "medals summed per country")

    a = art_medals.rename(columns={"Gold": "art_g", "Silver": "art_s", "Bronze": "art_b"})
    t = t.merge(a, on=["edition_id", "noc"], how="left").fillna({"art_g": 0, "art_s": 0, "art_b": 0})
    removed = int(a[["art_g", "art_s", "art_b"]].to_numpy().sum())
    for col, art in [("gold", "art_g"), ("silver", "art_s"), ("bronze", "art_b")]:
        t[col] = (t[col] - t[art]).clip(lower=0).astype(int)
    t = t.drop(columns=["art_g", "art_s", "art_b"])
    t["total"] = t.gold + t.silver + t.bronze
    n = len(t)
    t = t[t.total > 0]
    log.add("medal_tally", "Subtract Art Competitions medals (D7)", n, len(t),
            f"{removed} art medals removed; countries left with 0 medals dropped")
    return t.reset_index(drop=True)

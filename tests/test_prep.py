"""Unit tests for the data-preparation rules (small hand-made inputs)
plus integrity checks on the processed output tables."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from olympics import aggregate, clean, features  # noqa: E402

PROCESSED = ROOT / "data" / "processed"


# ---------------------------------------------------------------- parsing rules
@pytest.mark.parametrize("raw, expected, approx", [
    ("70", 70.0, False),
    ("77,5", 77.5, False),       # decimal comma
    ("80-82", 81.0, True),       # range -> midpoint (D4)
    ("124, 131", 127.5, True),   # two recorded weights -> mean (D4)
])
def test_parse_weight(raw, expected, approx):
    assert clean.parse_weight(raw) == (expected, approx)


def test_parse_weight_blank_is_missing():
    value, approx = clean.parse_weight("")
    assert np.isnan(value) and not approx


def test_parse_born_formats():
    out = clean.parse_born(pd.Series(["4 April 1949", "1879", "(c 1880)", ""]))
    assert out.birth_date.iloc[0] == pd.Timestamp("1949-04-04")
    assert out.birth_year.tolist()[:2] == [1949.0, 1879.0]
    assert out.birth_is_year_only.tolist() == [False, True, False, False]
    assert out.birth_year.iloc[2:].isna().all()          # free text and blank -> missing


def test_age_exact_respects_birthday():
    birth = pd.Series(pd.to_datetime(["2000-08-10", "2000-08-01"]))
    start = pd.Series(pd.to_datetime(["2020-08-05", "2020-08-05"]))
    age, approx = features.age_at_games(birth, birth.dt.year.astype(float), start, start.dt.year)
    assert age.tolist() == [19, 20]                       # birthday not yet / already reached
    assert not approx.any()


def test_age_year_only_is_flagged_approx():
    age, approx = features.age_at_games(pd.Series([pd.NaT]), pd.Series([1990.0]),
                                        pd.Series(pd.to_datetime(["2016-08-05"])), pd.Series([2016]))
    assert age.iloc[0] == 26 and approx.iloc[0]


def test_result_status_classification():
    s = clean._result_status(pd.Series(["3", "=6", "3 h8 r1/2", "DNS", "AC h3 r1/2", "'=6"]))
    assert s.tolist() == ["Ranked", "Ranked", "Eliminated in heats/rounds", "Did not start",
                          "Also competed (no rank)", "Ranked"]


# ---------------------------------------------------------------- medal counting
def _events(rows):
    df = pd.DataFrame(rows, columns=["edition_id", "result_id", "noc", "medal", "sport", "event"])
    df["medal"] = df.medal.astype(clean.MEDAL_DTYPE)
    return df


def test_team_medal_counted_once_per_event():
    relay = [(1, 10, "USA", "Gold", "Swimming", "4x100 m")] * 4
    m = aggregate.medal_pivot(aggregate.medals_once_per_event(_events(relay)), ["noc"])
    assert m.loc[0, "gold"] == 1 and m.loc[0, "total"] == 1


def test_tied_medals_kept_for_each_country():
    tie = [(1, 11, "GRE", "Bronze", "Athletics", "Pole Vault"),
           (1, 11, "USA", "Bronze", "Athletics", "Pole Vault")]
    m = aggregate.medal_pivot(aggregate.medals_once_per_event(_events(tie)), ["noc"])
    assert m.bronze.tolist() == [1, 1]


# ---------------------------------------------------------------- processed outputs
needs_data = pytest.mark.skipif(not (PROCESSED / "athlete_games.parquet").exists(),
                                reason="run scripts/prepare_data.py first")


@needs_data
def test_no_art_competitions_or_1906():
    ev = pd.read_parquet(PROCESSED / "athlete_events.parquet")
    assert clean.ART_SPORT not in set(ev.sport)
    assert clean.INTERCALATED_1906_ID not in set(ev.edition_id)
    assert clean.EQUESTRIAN_1956_ID not in set(ev.edition_id)


@needs_data
def test_athlete_games_unique_key_and_ranges():
    ag = pd.read_parquet(PROCESSED / "athlete_games.parquet")
    assert not ag.duplicated(["athlete_id", "edition_id", "sport", "noc"]).any()
    assert ag.age.dropna().between(10, 80).all()
    assert ag.height_cm.dropna().between(*clean.HEIGHT_RANGE_CM).all()
    assert (ag.bmi.dropna() >= clean.MIN_BMI).all()


@needs_data
def test_known_facts():
    cg = pd.read_parquet(PROCESSED / "country_games.parquet")
    usa84 = cg[(cg.year == 1984) & (cg.season == "Summer") & (cg.noc == "USA")].iloc[0]
    assert (usa84.gold, usa84.total) == (83, 174)
    ag = pd.read_parquet(PROCESSED / "athlete_games.parquet")
    assert ag[ag.name == "Michael Phelps"].n_gold.sum() == 23


@needs_data
def test_mapping_targets_exist_in_worldbank():
    m = pd.read_csv(ROOT / "data" / "reference" / "noc_to_iso3.csv", keep_default_na=False, na_values=[""])
    assert not m.noc.duplicated().any()
    assert not m.iso3.dropna().duplicated().any()
    assert set(m.match_method) <= {"name_auto", "manual", "historic", "no_wb_data"}

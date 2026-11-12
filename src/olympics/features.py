"""Derived variables: things the raw data does not contain directly but the
analysis needs (age at the Games, BMI, era, host flag, career length, ...).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Historical eras used as a categorical grouping across the dashboard.
ERA_BINS = [1895, 1915, 1939, 1991, 2030]
ERA_LABELS = [
    "Early Games (1896–1912)",
    "Interwar (1920–1936)",
    "Cold War (1948–1988)",
    "Modern (1992–2022)",
]

# Sports with fewer distinct athletes than this are flagged as "minor" so the
# sport filter and sport comparisons are not cluttered by one-off events
# (e.g. Ballooning, Aeronautics).
MINOR_SPORT_MAX_ATHLETES = 100


def add_era(year: pd.Series) -> pd.Series:
    return pd.cut(year, bins=ERA_BINS, labels=ERA_LABELS)


def age_at_games(birth_date: pd.Series, birth_year: pd.Series, games_start: pd.Series,
                 games_year: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Age in completed years on the opening day of the Games.

    Exact birth date -> exact age.
    Year-only birth  -> games_year - birth_year (approximate, ±1 year; D5).
    Returns (age, age_is_approx).
    """
    exact = (
        games_start.dt.year - birth_date.dt.year
        - ((games_start.dt.month < birth_date.dt.month)
           | ((games_start.dt.month == birth_date.dt.month) & (games_start.dt.day < birth_date.dt.day)))
    )
    approx = games_year - birth_year
    use_exact = birth_date.notna() & games_start.notna()
    age = exact.where(use_exact, approx)
    is_approx = ~use_exact & age.notna()
    return age.astype("Float64"), is_approx


def bmi(height_cm: pd.Series, weight_kg: pd.Series) -> pd.Series:
    return (weight_kg / (height_cm / 100) ** 2).round(1)


def build_athlete_games(events: pd.DataFrame, athletes: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """One row per athlete x Games x sport x NOC.

    This is the table for *athlete-level* analysis (physique, age, gender,
    sport profiles): a swimmer entered in 6 events counts once, not 6 times.
    Medal columns count the athlete's own medals (relay gold counts for each
    swimmer), which is the right unit for athlete-level questions.
    """
    medals = pd.get_dummies(events.medal).astype(int)
    ev = pd.concat([events[["athlete_id", "edition_id", "noc", "sport", "result_id"]], medals], axis=1)
    ev["started"] = events.result_status.ne("Did not start")
    ag = (ev.groupby(["athlete_id", "edition_id", "noc", "sport"], observed=True)
            .agg(n_events=("result_id", "nunique"), n_gold=("Gold", "sum"),
                 n_silver=("Silver", "sum"), n_bronze=("Bronze", "sum"), started=("started", "max"))
            .reset_index())
    # D16: an athlete takes part in a Games (in a sport) only if they started at least one event.
    # Entries that were all "Did not start" (e.g. Revithi and Melpomene, 1896) are not participations.
    dns_only_removed = int((~ag.started).sum())
    ag = ag[ag.started].drop(columns="started")
    ag["n_medals"] = ag.n_gold + ag.n_silver + ag.n_bronze
    ag["is_medalist"] = ag.n_medals > 0

    ag = ag.merge(games[["edition_id", "games", "year", "season", "start_date", "host_noc"]], on="edition_id")
    ag = ag.merge(athletes[["athlete_id", "name", "sex", "birth_date", "birth_year",
                            "height_cm", "weight_kg", "weight_is_approx"]], on="athlete_id")

    ag["age"], ag["age_is_approx"] = age_at_games(ag.birth_date, ag.birth_year, ag.start_date, ag.year)
    ag["bmi"] = bmi(ag.height_cm, ag.weight_kg)
    ag["is_host"] = ag.noc == ag.host_noc
    ag["decade"] = (ag.year // 10 * 10).astype(int)
    ag["era"] = add_era(ag.year)
    ag["is_female"] = ag.sex == "Female"

    # Career features, computed per athlete over all their Games
    career = ag.groupby("athlete_id").agg(
        n_games=("edition_id", "nunique"), first_year=("year", "min"), last_year=("year", "max"),
        career_medals=("n_medals", "sum"))
    career["career_span_years"] = career.last_year - career.first_year
    ag = ag.merge(career, on="athlete_id")

    ag = ag.drop(columns=["start_date", "birth_date", "host_noc"])
    ag.attrs["dns_only_removed"] = dns_only_removed      # read by prepare_data for the step log
    return ag


def build_sports(athlete_games: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """Sport dimension table: season, first/last appearance, size, status."""
    last_by_season = games.groupby("season").year.max()
    s = (athlete_games.groupby("sport")
         .agg(season=("season", lambda x: x.mode().iat[0]),
              first_year=("year", "min"), last_year=("year", "max"),
              n_editions=("edition_id", "nunique"), n_athletes=("athlete_id", "nunique"))
         .reset_index())
    # 'Current' = on the programme of the latest Games of its season (2020 / 2022)
    s["is_current"] = s.last_year == s.season.map(last_by_season)
    s["is_minor"] = s.n_athletes < MINOR_SPORT_MAX_ATHLETES
    return s


def athlete_count_per_edition(athlete_games: pd.DataFrame) -> pd.DataFrame:
    """Distinct athletes per Games x sex (an athlete in 2 sports counts once)."""
    return (athlete_games.drop_duplicates(["athlete_id", "edition_id"])
            .groupby(["edition_id", "games", "year", "season", "sex"], observed=True)
            .size().rename("n_athletes").reset_index())

"""Aggregations and integration with World Bank data.

Medal counting rule (project decision): a team medal counts ONCE per country
per event, as in official medal tables. A relay gold won by 4 swimmers is one
gold for the country.
"""
from __future__ import annotations

import pandas as pd

from .clean import ART_SPORT, MEDALS

EVENT_MEDAL_KEY = ["edition_id", "result_id", "noc", "medal"]


def medals_once_per_event(events: pd.DataFrame) -> pd.DataFrame:
    """One row per (Games, event, country, medal): team medals collapsed.

    Ties are preserved: two countries sharing a bronze each get one.
    """
    m = events.dropna(subset=["medal"])
    return m.drop_duplicates(EVENT_MEDAL_KEY)[EVENT_MEDAL_KEY + ["sport", "event"]].reset_index(drop=True)


def medal_pivot(medal_rows: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    p = (medal_rows.assign(medal=medal_rows.medal.astype(str))
         .pivot_table(index=by, columns="medal", values="result_id", aggfunc="count", fill_value=0)
         .reindex(columns=MEDALS, fill_value=0).reset_index())
    p.columns.name = None
    p = p.rename(columns={m: m.lower() for m in MEDALS})
    p["total"] = p.gold + p.silver + p.bronze
    return p


def art_medals_by_country(raw_events: pd.DataFrame) -> pd.DataFrame:
    """Art Competitions medals once per event (input to decision D7)."""
    e = raw_events.apply(lambda s: s.str.strip()).drop_duplicates()
    e = e[(e.sport == ART_SPORT) & (e.medal != "")]
    e = e.drop_duplicates(["edition_id", "result_id", "country_noc", "medal"])
    p = (e.pivot_table(index=["edition_id", "country_noc"], columns="medal", values="result_id",
                       aggfunc="count", fill_value=0)
          .reindex(columns=MEDALS, fill_value=0).reset_index()
          .rename(columns={"country_noc": "noc"}))
    p.columns.name = None
    p["edition_id"] = p.edition_id.astype(int)
    return p


def medals_by_sport(events: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """Country x Games x sport medal counts (derived, once per event)."""
    rows = medals_once_per_event(events)
    p = medal_pivot(rows, ["edition_id", "noc", "sport"])
    return p.merge(games[["edition_id", "year", "season"]], on="edition_id")


def validate_tally(tally: pd.DataFrame, events: pd.DataFrame) -> dict:
    """Compare official tally (after D2/D3/D7) with counts derived from athlete rows."""
    derived = medal_pivot(medals_once_per_event(events), ["edition_id", "noc"])
    c = tally.merge(derived, on=["edition_id", "noc"], how="outer", suffixes=("_tally", "_derived"),
                    indicator=True)
    both = c[c._merge == "both"]
    exact = ((both.gold_tally == both.gold_derived) & (both.silver_tally == both.silver_derived)
             & (both.bronze_tally == both.bronze_derived)).sum()
    return {
        "rows_in_both": len(both), "exact_match": int(exact),
        "exact_match_pct": float(round(100 * exact / len(both), 1)),
        "tally_only": int((c._merge == "left_only").sum()),
        "derived_only": int((c._merge == "right_only").sum()),
        "tally_total": int(tally.total.sum()), "derived_total": int(derived.total.sum()),
    }


def worldbank_long(wb: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """population + gdp_usd per (iso3, year); aggregates without ISO3 are dropped."""
    pop = wb["population"].dropna(subset=["iso3"]).rename(columns={"value": "population"})
    gdp = wb["gdp_usd"].dropna(subset=["iso3"]).rename(columns={"value": "gdp_usd"})
    return pop[["iso3", "year", "population"]].merge(gdp[["iso3", "year", "gdp_usd"]],
                                                     on=["iso3", "year"], how="outer")


def country_games(tally: pd.DataFrame, athlete_games: pd.DataFrame, games: pd.DataFrame,
                  countries: pd.DataFrame, noc_map: pd.DataFrame, wb: pd.DataFrame) -> pd.DataFrame:
    """One row per country x Games: delegation size, official medals, economy.

    Includes countries that took part but won nothing (total = 0), so maps and
    per-capita views show them instead of leaving gaps.
    """
    team = (athlete_games.drop_duplicates(["athlete_id", "edition_id", "noc"])
            .groupby(["edition_id", "noc"])
            .agg(n_athletes=("athlete_id", "size"), n_female=("is_female", "sum"))
            .reset_index())
    cg = team.merge(tally, on=["edition_id", "noc"], how="outer")
    for col in ["gold", "silver", "bronze", "total", "n_athletes", "n_female"]:
        cg[col] = cg[col].fillna(0).astype(int)
    cg = cg.merge(games[["edition_id", "games", "year", "season", "host_noc"]], on="edition_id")
    cg["is_host"] = cg.noc == cg.host_noc
    cg = cg.drop(columns="host_noc")
    cg = cg.merge(countries, on="noc", how="left").merge(noc_map[["noc", "iso3"]], on="noc", how="left")

    # World Bank values for the Games year (1960+ only; D9 historic NOCs have no ISO3)
    cg = cg.merge(wb, on=["iso3", "year"], how="left")
    cg["medals_per_million"] = (cg.total / (cg.population / 1e6)).round(3)
    cg["medals_per_100bn_gdp"] = (cg.total / (cg.gdp_usd / 1e11)).round(3)
    cg["gdp_per_capita"] = (cg.gdp_usd / cg.population).round(0)
    # Rank within each Games by gold, then silver, then bronze (official ordering)
    cg = cg.sort_values(["edition_id", "gold", "silver", "bronze"], ascending=[True, False, False, False])
    cg["rank"] = cg.groupby("edition_id").cumcount() + 1
    cg.loc[cg.total == 0, "rank"] = pd.NA
    cg["rank"] = cg["rank"].astype("Int16")
    return cg.reset_index(drop=True)


def sport_profiles(athlete_games: pd.DataFrame) -> pd.DataFrame:
    """Per sport: size and physique summary (used by the sport similarity map).

    Computed on one row per athlete x sport (latest Games) so long careers do not
    dominate. Physique columns use only athletes with known values; n_physique
    shows how many that is.
    """
    one = (athlete_games.sort_values("year")
           .drop_duplicates(["athlete_id", "sport"], keep="last"))
    g = one.groupby("sport")
    prof = pd.DataFrame({
        "n_athletes": g.athlete_id.size(),
        "n_physique": g.height_cm.count(),
        "pct_female": (g.is_female.mean() * 100).round(1),
        "height_mean": g.height_cm.mean().round(1),
        "weight_mean": g.weight_kg.mean().round(1),
        "bmi_mean": g.bmi.mean().round(1),
        "age_mean": g.age.mean().astype(float).round(1),
        "height_sd": g.height_cm.std().round(1),
        "weight_sd": g.weight_kg.std().round(1),
        "age_sd": g.age.std().astype(float).round(1),
    }).reset_index()
    return prof

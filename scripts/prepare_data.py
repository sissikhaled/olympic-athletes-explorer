"""Raw data -> processed parquet tables used by the dashboard. One command:

    python scripts/prepare_data.py

Inputs : data/raw/olympics/*.csv, data/raw/worldbank/*.csv, data/reference/noc_to_iso3.csv
Outputs: data/processed/*.parquet, prep_log.csv, validation.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pandas as pd  # noqa: E402

from olympics import aggregate, clean, features  # noqa: E402
from olympics.load import PROCESSED, REFERENCE, load_olympics, load_worldbank  # noqa: E402


def main() -> None:
    raw = load_olympics()
    wb_raw = load_worldbank()
    noc_map = pd.read_csv(REFERENCE / "noc_to_iso3.csv", keep_default_na=False, na_values=[""])
    log = clean.PrepLog()

    # 1. Cleaning ----------------------------------------------------------
    games = clean.clean_games(raw["games"], raw["events"], log)
    countries = clean.clean_countries(raw["countries"], log)
    athletes = clean.clean_athletes(raw["bio"], log)
    events = clean.clean_athlete_events(raw["events"], set(athletes.athlete_id), log)
    art = aggregate.art_medals_by_country(raw["events"])
    tally = clean.clean_tally(raw["tally"], art, log)

    # 2. Derived variables -------------------------------------------------
    athlete_games = features.build_athlete_games(events, athletes, games)
    log.add("athlete_games", "Collapse athlete-event rows to athlete x Games x sport", len(events),
            len(athlete_games), "one row per athlete per sport per Games")
    sports = features.build_sports(athlete_games, games)
    athlete_games = athlete_games.merge(sports[["sport", "is_current", "is_minor"]], on="sport")
    events = events.merge(games[["edition_id", "year", "season"]], on="edition_id")

    # 3. Integration and aggregates ---------------------------------------
    wb = aggregate.worldbank_long(wb_raw)
    country_games = aggregate.country_games(tally, athlete_games, games, countries, noc_map, wb)
    medals_sport = aggregate.medals_by_sport(events, games)
    profiles = aggregate.sport_profiles(athlete_games).merge(sports, on=["sport", "n_athletes"])
    participation = features.athlete_count_per_edition(athlete_games)
    validation = aggregate.validate_tally(tally, events)

    # 4. Write -------------------------------------------------------------
    PROCESSED.mkdir(parents=True, exist_ok=True)
    athletes_out = athletes.drop(columns=["birth_date"])
    outputs = {
        "games": games, "countries": countries.merge(noc_map[["noc", "iso3", "match_method"]], on="noc", how="left"),
        "athletes": athletes_out, "athlete_events": events, "athlete_games": athlete_games,
        "sports": sports, "country_games": country_games, "medals_by_sport": medals_sport,
        "sport_profiles": profiles, "participation": participation,
    }
    for name, df in outputs.items():
        df.to_parquet(PROCESSED / f"{name}.parquet", index=False)
    log.to_frame().to_csv(PROCESSED / "prep_log.csv", index=False)
    (PROCESSED / "validation.json").write_text(json.dumps(validation, indent=2))

    # 5. Report ------------------------------------------------------------
    pd.set_option("display.width", 220)
    pd.set_option("display.max_colwidth", 80)
    print(log.to_frame().to_string(index=False))
    print("\nMedal tally validation:", validation)
    print("\nOutputs:")
    for name, df in outputs.items():
        size = (PROCESSED / f"{name}.parquet").stat().st_size / 1e6
        print(f"  {name:16s} {len(df):>8,} rows x {df.shape[1]:>2} cols  {size:5.1f} MB")


if __name__ == "__main__":
    main()

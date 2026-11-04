"""Phase 1: targeted, read-only data-quality checks on the raw Olympic files.

Usage:  python -I scripts/profile_checks.py data/raw/olympics
"""
import re
import sys
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)
pd.set_option("display.max_rows", 200)

RAW = Path(sys.argv[1])


def read(name):
    return pd.read_csv(RAW / name, encoding="utf-8-sig", dtype=str, keep_default_na=False)


def h(title):
    print(f"\n{'-' * 90}\n## {title}")


bio = read("Olympic_Athlete_Biography.csv")
ev = read("Olympic_Athlete_Event_Details.csv")
res = read("Olympic_Event_Results.csv")
games = read("Olympic_Games_Summary.csv")
tally = read("Olympic_Medal_Tally_History.csv")
ctry = read("Olympic_Country_Profiles.csv")

# ---------------------------------------------------------------- biography
h("BIO: height / weight formats")
for col in ["height", "weight"]:
    s = bio[col]
    nonblank = s[s.str.strip() != ""]
    numeric = pd.to_numeric(nonblank, errors="coerce")
    print(f"{col}: non-blank={len(nonblank):,}, non-numeric={numeric.isna().sum():,}")
    print("  non-numeric examples:", nonblank[numeric.isna()].value_counts().head(10).to_dict())
    print("  numeric describe:", numeric.describe().round(1).to_dict())
    print("  smallest:", sorted(numeric.dropna().unique())[:8], " largest:", sorted(numeric.dropna().unique())[-8:])

h("BIO: height blank vs weight blank (same rows?)")
print(pd.crosstab(bio.height.str.strip() == "", bio.weight.str.strip() == "", rownames=["height blank"], colnames=["weight blank"]))

h("BIO: 'born' formats")
born = bio.born.str.strip()
full = pd.to_datetime(born, format="%d %B %Y", errors="coerce")
print(f"parse as 'D Month YYYY': {full.notna().sum():,} / {(born != '').sum():,} non-blank")
unparsed = born[(born != "") & full.isna()]
pattern = unparsed.str.replace(r"\d", "9", regex=True).str.replace(r"[A-Za-z]+", "W", regex=True)
print("unparsed pattern counts:", pattern.value_counts().head(10).to_dict())
print("unparsed examples:", unparsed.drop_duplicates().head(12).tolist())
print("birth year range (parsed):", full.dt.year.min(), "-", full.dt.year.max())

h("BIO: country text vs NOC")
print("country values with leading/trailing spaces:", (bio.country != bio.country.str.strip()).sum())
multi = bio.assign(c=bio.country.str.strip()).groupby("country_noc").c.nunique().sort_values(ascending=False)
print("NOCs with >1 country spelling (top 10):", multi.head(10).to_dict())
print("example spellings for GER:", bio.loc[bio.country_noc == "GER", "country"].str.strip().value_counts().head(5).to_dict())

h("BIO: duplicate names (different athlete_id, same name + born)")
d = bio[bio.duplicated(["name", "born"], keep=False) & (bio.born != "")]
print(f"rows: {len(d):,}; example:\n", d.sort_values("name").head(6)[["athlete_id", "name", "born", "country_noc"]].to_string(index=False))

# ---------------------------------------------------------------- event details
h("EVENTS: exact duplicates")
dups = ev[ev.duplicated(keep=False)]
print(f"duplicate rows: {ev.duplicated().sum():,}; example:\n", dups.head(4).to_string(index=False))

h("EVENTS: editions (Summer/Winter, 1906, years)")
ed = ev.edition.str.extract(r"(?P<year>\d{4}) (?P<season>.+)")
print(ed.season.value_counts().to_dict())
print("editions:", sorted(ev.edition.unique()))

h("EVENTS: sports list (count of athlete-event rows)")
print(ev.sport.value_counts().to_string())

h("EVENTS: medal values")
print(ev.medal.replace("", "<blank>").value_counts().to_dict())

h("EVENTS: pos codes (non-numeric leading token)")
lead = ev.pos.str.strip().str.split().str[0].fillna("")
print(lead[~lead.str.fullmatch(r"=?\d+")].value_counts().head(25).to_dict())

h("EVENTS: isTeamSport vs medals - how many athletes share one medal?")
med = ev[ev.medal != ""]
grp = med.groupby(["edition_id", "result_id", "country_noc", "medal"]).size()
print("athletes per (edition, event, NOC, medal):", grp.describe().round(2).to_dict())
team = med[med.isTeamSport == "True"]
print("team-sport medal rows:", len(team), "| distinct team medals:", team.groupby(["edition_id", "result_id", "country_noc", "medal"]).ngroups)
# events marked non-team but several medallists from same NOC + medal (pairs, relays?)
nt = med[med.isTeamSport == "False"].groupby(["edition_id", "result_id", "country_noc", "medal"]).size()
print("non-team groups with >1 athlete:", (nt > 1).sum(), "examples:")
ex = nt[nt > 1].head(5).reset_index()
print(ex.merge(ev[["result_id", "event"]].drop_duplicates(), on="result_id").to_string(index=False))

h("EVENTS: event names - gender suffix")
suffix = ev.event.str.extract(r",\s*(Men|Women|Mixed|Open)\s*$")[0].fillna("<other>")
print(suffix.value_counts().to_dict())
print("examples of <other>:", ev.event[suffix == "<other>"].drop_duplicates().head(10).tolist())

h("EVENTS: art competitions / non-sport entries")
print(ev[ev.sport.str.contains("Art", case=False)].sport.value_counts().to_dict())

# ---------------------------------------------------------------- joins
h("JOINS: key coverage")
bio_ids, ev_ids = set(bio.athlete_id), set(ev.athlete_id)
print(f"event athlete_ids missing from bio: {len(ev_ids - bio_ids)} -> {sorted(ev_ids - bio_ids)[:10]}")
print(f"bio athlete_ids with no events: {len(bio_ids - ev_ids)}")
print(f"event result_ids missing from results: {len(set(ev.result_id) - set(res.result_id))}")
print(f"event edition_ids missing from games: {len(set(ev.edition_id) - set(games.edition_id))}")
noc_all = set(ev.country_noc) | set(bio.country_noc) | set(tally.country_noc)
print(f"NOCs used but not in country profiles: {sorted(noc_all - set(ctry.noc))}")
print("duplicate NOC in country profiles:", ctry[ctry.noc.duplicated(keep=False)].to_dict("records"))
print("athletes whose bio NOC differs from at least one event NOC:",
      ev.merge(bio[["athlete_id", "country_noc"]], on="athlete_id", suffixes=("_ev", "_bio"))
        .query("country_noc_ev != country_noc_bio").athlete_id.nunique())

# ---------------------------------------------------------------- games
h("GAMES summary table")
print(games[["edition", "edition_id", "year", "city", "country_noc", "start_date", "end_date", "competition_date", "isHeld"]].to_string(index=False))

# ---------------------------------------------------------------- tally validation
h("TALLY vs once-per-event medal counts from event details")
dedup = ev.drop_duplicates()
m = dedup[dedup.medal != ""].drop_duplicates(["edition_id", "result_id", "country_noc", "medal"])
mine = m.pivot_table(index=["edition_id", "country_noc"], columns="medal", values="result_id", aggfunc="count", fill_value=0).reset_index()
t = tally.astype({"gold": int, "silver": int, "bronze": int})
cmp_ = t.merge(mine, on=["edition_id", "country_noc"], how="outer", indicator=True)
print(cmp_._merge.value_counts().to_dict())
both = cmp_[cmp_._merge == "both"]
exact = ((both.gold == both.Gold) & (both.silver == both.Silver) & (both.bronze == both.Bronze))
print(f"rows matching exactly: {exact.sum()} / {len(both)}")
both = both.assign(diff=(both.gold - both.Gold).abs() + (both.silver - both.Silver).abs() + (both.bronze - both.Bronze).abs())
print("largest mismatches:\n", both.sort_values("diff", ascending=False).head(10)[["edition", "country_noc", "gold", "Gold", "silver", "Silver", "bronze", "Bronze"]].to_string(index=False))

# ---------------------------------------------------------------- results
h("RESULTS: date + participants formats")
print("result_participants pattern:", res.result_participants.str.replace(r"\d+", "9", regex=True).value_counts().head(5).to_dict())
print("result_format 'na' share:", round((res.result_format == "na").mean() * 100, 1), "%")

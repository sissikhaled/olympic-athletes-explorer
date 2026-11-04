# Data Preparation Log

This document records every decision made while turning the raw data into the tables the dashboard uses. Phase 1 (this section) is **profiling only**: nothing has been changed yet.

Reproduce the numbers below with:
```bash
python -I scripts/profile_raw.py data/raw/olympics
python -I scripts/profile_checks.py data/raw/olympics
```

---

## 1. Sources

### 1.1 Olympic data (primary)
*126 Years of Historical Olympic Dataset*, Muhammad Ehsan, Kaggle. The data was scraped from Olympedia.org and covers Athens 1896 to Beijing 2022. Files are dated 27 Aug 2024.

| File | Rows | Cols | Grain (one row = …) | Key |
|---|---:|---:|---|---|
| `Olympic_Athlete_Biography.csv` | 155,861 | 10 | one athlete | `athlete_id` |
| `Olympic_Athlete_Event_Details.csv` | 316,834 | 11 | one athlete in one event at one Games | `athlete_id` + `result_id` |
| `Olympic_Event_Results.csv` | 7,394 | 12 | one event at one Games (text descriptions) | `result_id` |
| `Olympic_Games_Summary.csv` | 64 | 11 | one Games edition (incl. cancelled + future) | `edition_id` |
| `Olympic_Medal_Tally_History.csv` | 1,807 | 9 | one country at one Games (official medal table) | `edition_id` + `country_noc` |
| `Olympic_Country_Profiles.csv` | 235 | 2 | one NOC code → country name | `noc` |

`wc -l` shows 20,791 lines for the results file because its text fields contain line breaks. pandas correctly reads 7,394 records.

### 1.2 World Bank Open Data (secondary, for integration)
Fetched by `scripts/fetch_worldbank.py` from the public API v2 (CC BY 4.0) into `data/raw/worldbank/`.

| File | Indicator | Rows | With values | Years |
|---|---|---:|---:|---|
| `population.csv` | `SP.POP.TOTL` | 17,290 | 17,195 | 1960–2024 |
| `gdp_usd.csv` | `NY.GDP.MKTP.CD` (current US$) | 17,290 | 14,577 | 1960–2024 |

These files include regional and income-group aggregates (e.g. "Africa Eastern and Southern", "High income"), so the joins must use individual ISO3 country codes only.

---

## 2. Profiling findings

### 2.1 Athlete biography
| Column | Finding | Implication |
|---|---|---|
| `sex` | Only `Male` / `Female`, no blanks | Clean |
| `height`, `weight` | 32.6 % blank, **always together** (a row has both or neither) | A missing-data pattern, not random |
| `height` | All numeric (cm), range 127–226 | Plausible, no outliers to remove |
| `weight` | 961 values are **ranges** like `80-82`; numeric range 25–198 kg | Needs a rule (midpoint or missing) |
| `born` | 2.6 % blank. 149,211 parse as `D Month YYYY`. **2,267 are year only** (`1879`). About 330 are free text (`(c 1880)`, place names) | Age can only be exact for full dates |
| `born` | Parsed years range 1828–2009 | Plausible |
| `country` | Every value has a leading space. The column mixes in multi-country histories (`Germany  West Germany`) | Use `country_noc` instead and trim text |
| duplicates | 0 exact. 5 name+birth-date pairs have different IDs (e.g. two "Erik Larsson, 14 May 1888, SWE") | Possibly the same person twice; can't be verified, so left as is |
| `description`, `special_notes` | 61–65 % blank free text | Not used in charts (maybe in an athlete-detail tooltip) |

### 2.2 Athlete event details (main fact table)
| Finding | Detail | Implication |
|---|---|---|
| **1,208 exact duplicate rows** | e.g. the same 1932 Art Competitions entry repeated | Drop |
| UTF-8 byte-order mark at file start | First column read as `﻿edition` | Read with `utf-8-sig` |
| Editions | 55 editions with athlete data: Summer, Winter, **1956 Equestrian Olympics** (Stockholm, 300 rows), **1906 Intercalated Games** (only 23 rows) | Decide how to treat these two |
| `medal` | 85.9 % blank (= no medal); otherwise Gold 15,072 / Silver 14,676 / Bronze 14,939 athlete-rows | Blank → "No medal"; ordered category |
| `pos` | Mixed text: ranks (`3`, `=6`), heats (`3 h8 r1/2`), status codes `AC` (11,150), `DNS` 8,647, `DNF` 8,132, `DQ` 2,023, `HC`, `HM`, … | Parse a numeric final place plus a status category |
| `isTeamSport` | `True`/`False`. 29,388 team medal rows collapse to 5,141 team medals | Basis of once-per-event counting |
| Event gender | Suffix `, Men` 210,592 · `, Women` 85,746 · `, Open` 16,308 · `, Mixed` 3,753 · `, Boys` 435 (early 1900s) | Derive `event_gender` |
| Sex vs event | 3 women in "Men" events, 8 men in "Women" events | Tiny; keep, and document |
| Sports | 112 distinct, many historic one-offs (Ballooning, Tug-of-War, Firefighting, Aeronautics: 1 row) | Sport filter needs grouping or a minimum size |
| **Art Competitions** | 3,621 rows, 147 medal rows, 1912–1948. Most of the "athletes" aged > 60 are artists (251 cases) | Not athletic, which skews physique and age views |

### 2.3 Joins between tables
| Check | Result |
|---|---|
| Event athlete IDs missing from biography | 6 (out of 155,867) |
| Biography athletes with no events | 0 |
| Event `result_id`s missing from results file | 3 |
| Event editions missing from Games file | 0 |
| NOCs not in country profiles | `IFR` only |
| Duplicate NOC in country profiles | `ROC` appears twice ("ROC" and "Russian Olympic Committee") |
| Athletes whose bio NOC ≠ an event NOC | 2,177 (athletes who changed nationality), so use the **event** NOC for medals and participation |

### 2.4 Games summary
* 64 rows: 55 held Games plus **5 cancelled by war** (1916, 1940 ×2, 1944 ×2, flagged `Not held due to war`) plus **4 future** (2024, 2026, 2028, 2032, no athlete data).
* `start_date`/`end_date` have no year except Tokyo 2020 (`23 July 2021`, postponed), so the year must be taken from the `year` column. The exception is 2020, where the actual dates are in 2021.
* Host city and host NOC are present, which makes a host-country flag possible.

### 2.5 Medal tally validation (once-per-event counting)
Counting medals from event details once per (Games, event, NOC, medal):

| | Rows |
|---|---:|
| Country–Games rows in both | 1,785 |
| …matching the official tally **exactly** | **1,744 (97.7 %)** |
| In tally only | 22 (mostly **1906**, which has almost no athlete data, plus `MIX` mixed-nation teams 1896–1924) |
| In event details only | 4 |

Total medals: tally 6,753 G / 6,725 S / 7,176 B vs derived 6,629 / 6,585 / 7,036. The remaining gaps come from mixed-nation teams (`MIX` in the tally; the athletes are listed under their own NOCs in event details), 1906, and small Olympedia corrections (e.g. USA 1904). **The official tally includes Art Competitions medals** (excluding them lowers the exact matches to 1,683).

### 2.6 Coverage of physical attributes over time
Share of athlete-Games participations with a known height:

| 1890s–1940s | 1950s | 1960s–2010s | 2020s |
|---|---|---|---|
| 6–15 % | 30 % | 83–98 % | **44 %** |

Physique analysis is reliable from 1960 to 2016. Earlier decades and the 2020/2022 Games have thin samples, so any physique chart must show its sample size.

### 2.7 Age at Games (approximate, from birth year)
* Median 25, IQR 22–29, min 11 (e.g. 1896 gymnast, 2020 table tennis: real cases), max 98 (Art Competitions).
* 78 participations above age 70: Art Competitions plus Shooting, Equestrian, Sailing. These are plausible, so no age outliers are removed (to be confirmed).

---

## 3. Decisions (agreed 2026-11-04, applied in Phase 2)

| # | Issue | Decision | Rationale |
|---|---|---|---|
| D1 | Art Competitions (§2.2) | **Excluded everywhere**, including medal totals | Entrants are not athletes. Including them would distort the age and physique analyses |
| D2 | 1906 Intercalated Games | **Dropped** | Not recognised by the IOC; only 23 athlete rows |
| D3 | 1956 Equestrian (Stockholm) | **Merged into 1956 Summer Olympics** | Officially part of the Melbourne 1956 Games |
| D4 | Weight ranges (`80-82`) | **Midpoint** (81), flagged `weight_is_approx` | Keeps 961 data points; error ≤ 1 kg |
| D5 | Year-only birth dates | **Age = Games year − birth year**, flagged `age_is_approx`; free-text births → missing | Error ≤ 1 year |
| D6 | Country medal totals | **Official tally** for country totals; **once-per-event counts** from athlete data for per-sport views | The tally is authoritative; only athlete data has sports |
| D7 | Consequence of D1 + D6 | Art Competitions medals (counted once per event) are **subtracted from the official tally** | Keeps totals consistent with D1. Affects 1912–1948 only |
| D8 | Exact duplicate event rows (1,208) | Dropped | Scraping artefacts |
| D9 | Historical / special NOCs (URS, GDR, EUN, ROC, IOA, …) | Kept as they competed (project decision). Not mapped to World Bank, so excluded from per-capita/GDP views only | Historically accurate |
| D10 | Cancelled (war) and future Games | Removed from analysis tables. War gaps shown as annotations on timelines | No athlete data |
| D11 | Low physique coverage before 1960 and for 2020/2022 (§2.6) | Kept; every physique chart shows sample size *n* | Transparency over silent filtering |
| D12 | Nationality | Event-level NOC used for participation/medals, not bio NOC | 2,177 athletes changed nationality |

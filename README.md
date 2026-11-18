# Olympic Athletes Explorer: 126 Years of Olympic History

An interactive dashboard for exploring athlete-level Olympic results from **Athens 1896 to Beijing 2022**:
150,588 athletes, 53 Games, 230 teams, combined with World Bank population and GDP. Built with
**Plotly + Dash** for a university data-visualization course (assignment brief: [REQUIREMENTS.md](REQUIREMENTS.md);
how each requirement is met: [docs/requirements_checklist.md](docs/requirements_checklist.md)).

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Then open **http://127.0.0.1:8050**. The cleaned data is included in the repository, so no download is needed
to run the dashboard. Tested with Python 3.13 on macOS; a fresh clone installs in about 15 seconds.

Options: `PORT=8051 python app.py` uses another port; `DASH_DEBUG=1 python app.py` enables hot reload.

## What the dashboard answers

The dashboard investigates **five analytical questions** (one per analytical tab, two on Countries & Medals); the
Overview tab describes the data. Each question is stated as a heading, and each chart card names what it shows,
its chart type and its category in the [FT Visual Vocabulary](https://ft-interactive.github.io/visual-vocabulary/)
(seven of the nine categories are used).

| Tab | Analytical question | Charts (evidence) |
|---|---|---|
| **Overview** | (descriptive: what is in the data; visuals only) | treemap of sports and events, searchable athlete table + career card |
| **Countries & Medals** | **Q1** What drives a country's Olympic success: size, wealth or specialisation?<br>**Q2** Do hosts win more at home? | Q1: medal map (proportional symbols / choropleth, play mode), medals vs GDP bubble scatter, specialisation heatmap · Q2: host dumbbell |
| **Physiques** | **Q3** How do athletes' bodies differ between sports, how have they changed, and do medallists stand out? | median + IQR trend, height × weight density, split violin |
| **Gender** | **Q4** How did women gain their place at the Games, over time, across sports and across countries? | annotated share line, sport timeline, spine chart |
| **Sport Comparison** | **Q5** Which sports select for similar athletes? | PCA similarity map with loadings, violins |

15 chart forms. Full design rationale (why each form fits its question, interactions, colour system,
and the simplification review that removed six charts): [docs/analytical_questions.md](docs/analytical_questions.md).

### Interacting
* **Navigation:** the tabs are icons in a translucent bar floating at the top right, next to Filters (Olympic rings, medal, runner,
  ♀♂, ball); hover one for its name, and a highlight slides to the active one. On a phone the bar floats at the
  bottom. The title scrolls away with the page, so the charts get almost the whole screen.
* **Filters** (years, season, sex, sports, countries): press **Filters** at the top right; the panel grows out
  of the button and collapses back into it. Filters apply to every tab; a badge on the button counts the active
  ones, and the **Showing:** bar at the top of the page lists them. A tab where a filter does not apply says so
  under its question.
* **Linked views:** click a country in any Countries chart to select it everywhere; click a sport in the treemap
  to list its athletes, or on the gender timeline to add it to the share line; click or lasso sports on the
  similarity map to compare them.
* **Hover** for exact values and sample sizes, **zoom/pan** on every chart (double-click resets), **search**
  athletes by name (accents optional), **▶ play** the medal map through history.

A 10-minute presentation walkthrough with verified talking points: [docs/demo_script.md](docs/demo_script.md).

## Data sources

| Source | What it gives us | Link | License |
|---|---|---|---|
| **126 Years of Historical Olympic Dataset**, Muhammad Ehsan (Kaggle), scraped from [Olympedia.org](https://www.olympedia.org); files dated 27 Aug 2024 | Athlete biographies, athlete-event results, event descriptions, Games, medal tallies, NOC names (6 CSVs) | https://www.kaggle.com/datasets/muhammadehsan02/126-years-of-historical-olympic-dataset | CC BY 4.0 |
| **World Bank Open Data** | Population (`SP.POP.TOTL`), GDP in current US$ (`NY.GDP.MKTP.CD`), 1960–2024 | https://data.worldbank.org | CC BY 4.0 |

Both licences allow redistribution with attribution, so the processed tables are committed. The sources are
also shown in the dashboard (**About & sources** and the page footer).

## Data preparation

One command rebuilds every table the dashboard uses from the raw files (about 5 seconds; the output is
bit-identical to the committed files):

```bash
# 1. download the Kaggle CSVs into data/raw/olympics/   (free Kaggle login)
python scripts/fetch_worldbank.py   # 2. World Bank population + GDP into data/raw/worldbank/
python scripts/prepare_data.py      # 3. raw CSV -> data/processed/*.parquet
```

Highlights (full log with row counts and 16 numbered decisions: [docs/data_preparation.md](docs/data_preparation.md)):
* **Cleaning:** 1,208 duplicate rows removed; Art Competitions and the unofficial 1906 Games excluded; 1956
  Equestrian merged into Melbourne 1956; athletes who never started an event not counted as participants.
* **Missing / erroneous values:** weight ranges (`80-82`) and double weights resolved to a flagged mean;
  year-only birth dates give a flagged approximate age; implausible values set to missing; coverage gaps
  (physique data before 1960) shown as sample sizes instead of hidden.
* **Derived variables:** age on the opening day, BMI, era, host flag, career length, result status, event
  gender, specialisation index, medals per capita / per GDP, sport profiles.
* **Integration:** a hand-checked Olympic-code → ISO3 table joins World Bank data (historic teams such as the
  USSR are kept as they competed).
* **Validation:** medal counts derived from athlete results match the official medal table exactly for 97.7 % of
  country-Games rows; known facts (USA 1984 = 83 golds, Phelps = 23 golds, Rio 2016 = 306 events) are tested.

## Tests and quality checks

```bash
python -m pytest                        # 615 tests, ~35 s
python scripts/benchmark_callbacks.py   # server time per filter change, per tab
```
The suite covers the cleaning rules, every chart builder, linked-view logic, and a sweep of every chart against
17 awkward filter combinations (single Games, war years, one tiny country, …), checking that nothing fails and
that empty charts explain why.

## Project structure

```
├── app.py                 entry point: python app.py
├── requirements.txt       pinned dependencies
├── REQUIREMENTS.md        assignment brief (reference)
├── assets/               style.css (page styling, animations) and icons/ (rail icons, SVG)
├── data/
│   ├── raw/               downloaded data (not in git)
│   ├── reference/         hand-made lookup tables: NOC → ISO3, map placement of historic teams
│   └── processed/         cleaned parquet tables used by the app (+ step log, validation report)
├── scripts/               fetch_worldbank · prepare_data · build_noc_mapping · profile_* · benchmark
├── src/olympics/          load · clean · features · aggregate (the data pipeline)
├── dashboard/
│   ├── theme.py           validated colours, Plotly template, empty-state figure
│   ├── data_access.py     loads tables once, applies the global filters (cached)
│   ├── components.py      chart card, controls, data grid, per-tab callback helper
│   ├── layout.py          header, floating icon bar, Filters button + panel, filter bar, tabs, About dialog
│   ├── callbacks.py       filter panel → filter store, reset, summary, filter bar, badge
│   └── tabs/              overview · countries · physiques · gender · sports
├── docs/
│   ├── project_plan.md          phases and progress
│   ├── data_preparation.md      profiling findings, decisions D1–D16, step log, data dictionary
│   ├── analytical_questions.md  questions, chart choices, FT coverage, interactions, colours
│   ├── requirements_checklist.md
│   └── demo_script.md
└── tests/                 pytest suite
```

## Known limitations
* Height and weight are sparse before 1960 (6–30 % of athletes) and at 2020/2022 (44 %); charts report *n*.
* Population and GDP exist from 1960 and only for present-day countries; historic teams have no per-capita values.
* Per-sport medal counts come from athlete results and can differ slightly from the official table (mixed-nation
  teams, later corrections).

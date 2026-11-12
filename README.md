# Olympic Athletes Explorer: 126 Years of Olympic History

An interactive dashboard (Plotly + Dash) for exploring athlete-level Olympic results from Athens 1896 to Beijing 2022, built for a university data-visualization course. See [REQUIREMENTS.md](REQUIREMENTS.md) for the assignment brief.

> Status: **Phase 3, dashboard design complete** ([docs/analytical_questions.md](docs/analytical_questions.md)). The full plan and progress are in [docs/project_plan.md](docs/project_plan.md). Sections marked _TBD_ are filled in during later phases.

## Data sources

| Source | What it gives us | Link | License |
|---|---|---|---|
| **126 Years of Historical Olympic Dataset**, Muhammad Ehsan (Kaggle), scraped from [Olympedia.org](https://www.olympedia.org). Files dated 27 Aug 2024 | Athlete biographies, athlete-event results, event descriptions, Games, medal tallies, NOC names (6 CSVs) | https://www.kaggle.com/datasets/muhammadehsan02/126-years-of-historical-olympic-dataset | CC BY 4.0 (Attribution 4.0 International) |
| **World Bank Open Data** | Population (`SP.POP.TOTL`), GDP current US$ (`NY.GDP.MKTP.CD`), 1960 onwards | https://data.worldbank.org | CC BY 4.0 |

### Getting the raw data
1. Download the Kaggle dataset (a free Kaggle login is needed) and unzip **all CSV files** into `data/raw/olympics/`.
2. Fetch World Bank data (no key needed, internet required once): `python scripts/fetch_worldbank.py`

### Rebuilding the processed data (optional)
The cleaned tables in `data/processed/` are committed, so this step is only needed to reproduce them:
```bash
python scripts/prepare_data.py   # raw CSV -> data/processed/*.parquet (~5 s)
python -m pytest                 # checks the cleaning rules and outputs
```
Every cleaning decision is documented in [docs/data_preparation.md](docs/data_preparation.md).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running
_TBD (Phase 4)._ The target is a single command, `python app.py`, then open http://127.0.0.1:8050.

## Project structure

```
├── REQUIREMENTS.md      assignment brief (reference)
├── app.py               dashboard entry point            (Phase 4)
├── data/
│   ├── raw/             downloaded data, not in git
│   ├── reference/       hand-made lookup tables (NOC → ISO3)
│   └── processed/       cleaned parquet files used by the app
├── scripts/             fetch + prepare pipeline commands
├── src/olympics/        data loading, cleaning, features, aggregation
├── dashboard/           layout, theme, one module per tab
├── docs/                data-preparation log, analytical questions, demo script
└── tests/               pytest tests
```

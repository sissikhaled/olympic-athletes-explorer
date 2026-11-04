# Olympic Athletes Explorer: 126 Years of Olympic History

An interactive dashboard (Plotly + Dash) for exploring athlete-level Olympic results from Athens 1896 to Beijing 2022, built for a university data-visualization course. See [REQUIREMENTS.md](REQUIREMENTS.md) for the assignment brief.

> Status: **Phase 0, project setup.** Sections marked _TBD_ are filled in during later phases.

## Data sources

| Source | What it gives us | Link | License |
|---|---|---|---|
| **126 Years of Historical Olympic Dataset**, Muhammad Ehsan (Kaggle), derived from [Olympedia.org](https://www.olympedia.org) | Athlete bios, event results, Games, medal tallies | _TBD: Kaggle URL (confirmed in Phase 1)_ | _TBD_ |
| **World Bank Open Data** | Population (`SP.POP.TOTL`), GDP current US$ (`NY.GDP.MKTP.CD`), 1960 onwards | https://data.worldbank.org | CC BY 4.0 |

### Getting the raw data
1. Download the Kaggle dataset (a free Kaggle login is needed) and unzip **all CSV files** into `data/raw/olympics/`.
2. World Bank data is fetched by a script: _TBD (Phase 1)_.

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

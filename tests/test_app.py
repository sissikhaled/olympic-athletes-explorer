"""Smoke tests for the Dash app: layout builds, IDs are unique, filters work."""
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.skipif(not (ROOT / "data" / "processed" / "athlete_games.parquet").exists(),
                                reason="run scripts/prepare_data.py first")


def _ids(component, found=None):
    found = [] if found is None else found
    cid = getattr(component, "id", None)
    if cid is not None:
        found.append(cid)
    children = getattr(component, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            _ids(c, found)
    elif children is not None and hasattr(children, "to_plotly_json"):
        _ids(children, found)
    return found


def test_app_imports_and_layout_builds():
    import app
    layout = app.serve_layout()
    ids = _ids(layout)
    dupes = [i for i, n in Counter(ids).items() if n > 1]
    assert not dupes, f"duplicate component ids: {dupes}"
    for required in ["filters", "flt-years", "flt-season", "flt-sex", "flt-sports", "flt-countries", "tabs"]:
        assert required in ids


def test_every_tab_has_its_questions():
    from dashboard.layout import TABS
    import json
    expected = {"overview": ["Q1.1", "Q1.2", "Q1.3", "Q1.4"],
                "countries": [f"Q2.{i}" for i in range(1, 7)],
                "physiques": [f"Q3.{i}" for i in range(1, 5)],
                "gender": [f"Q4.{i}" for i in range(1, 5)],
                "sports": [f"Q5.{i}" for i in range(1, 4)]}
    for tab in TABS:
        text = json.dumps(tab.layout().to_plotly_json(), default=str)
        for q in expected[tab.TAB_ID]:
            assert q in text, f"{q} missing on tab {tab.TAB_ID}"


def test_filters_narrow_the_data():
    from dashboard import data_access as da
    base = da.summary(da.DEFAULT_FILTERS)
    winter = da.summary({**da.DEFAULT_FILTERS, "season": "Winter"})
    women_2000s = da.summary({**da.DEFAULT_FILTERS, "sex": "Female", "years": [2000, 2022]})
    assert 0 < winter["athletes"] < base["athletes"]
    assert 0 < women_2000s["athletes"] < base["athletes"]
    a = da.filter_athletes({**da.DEFAULT_FILTERS, "countries": ["NOR"], "season": "Winter"})
    assert set(a.noc) == {"NOR"} and set(a.season) == {"Winter"}


def test_impossible_filter_returns_empty_not_error():
    from dashboard import data_access as da
    f = {**da.DEFAULT_FILTERS, "years": [1916, 1918]}   # no Games held (war)
    assert da.summary(f)["athletes"] == 0
    assert da.filter_country_games(f).empty


def test_ignore_rules_from_filter_matrix():
    from dashboard import data_access as da
    f = {**da.DEFAULT_FILTERS, "sex": "Female", "countries": ["USA"]}
    assert set(da.filter_athletes(f, ignore=("sex",)).sex) == {"Female", "Male"}
    assert da.filter_country_games(f).noc.nunique() > 1        # countries highlighted, not filtered


def test_global_callbacks():
    from dashboard import callbacks as cb
    store = cb.update_filter_store([1960, 2016], "Summer", "All", None, True, None)
    assert store == {"years": [1960, 2016], "season": "Summer", "sex": "All", "sports": [],
                     "hide_minor": True, "countries": []}
    options, value = cb.update_sport_options("Winter", True, ["Swimming", "Biathlon"])
    assert value == ["Biathlon"]                                # Summer sport dropped
    assert all("Swimming" != o["value"] for o in options)

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


def test_one_analytical_question_per_tab():
    """Analytical tabs state one question (Q1-Q4); the Overview is descriptive; charts have plain titles."""
    from dashboard.layout import TABS
    import json
    import re
    expected = {"overview": None, "countries": "Q1", "physiques": "Q2", "gender": "Q3", "sports": "Q4"}
    for tab in TABS:
        text = json.dumps(tab.layout().to_plotly_json(), default=str)
        found = set(re.findall(r"\bQ\d(?:\.\d)?\b", text))
        want = expected[tab.TAB_ID]
        assert found == ({want} if want else set()), f"{tab.TAB_ID}: {found}"


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


def test_failing_chart_shows_message_instead_of_breaking(monkeypatch):
    """The safety net in tab_callback: an exception becomes an explanatory empty chart."""
    import dash
    from dash import Input, Output
    from dashboard import components

    registered = {}
    monkeypatch.setattr(dash, "callback", lambda *deps, **kw: (lambda fn: registered.setdefault("fn", fn)))

    @components.tab_callback("demo", Output("demo-graph", "figure"), Input("filters", "data"))
    def broken(f):
        raise ValueError("boom")

    fig = registered["fn"]({"x": 1}, "demo")                 # Dash passes (filters, active tab)
    assert "could not be drawn" in fig.layout.annotations[0].text
    assert broken.__name__ == "broken"                       # original function returned unchanged


def test_filter_bar_names_filters_and_tab_exceptions():
    from dashboard import callbacks as cb
    from dashboard import data_access as da
    chips = cb.filter_chips({**da.DEFAULT_FILTERS, "season": "Winter", "sex": "Female", "countries": ["NOR", "SWE"]})
    assert chips == ["1896–2022", "Winter Games", "Women only", "2 countries"]
    bar = str(cb.show_filter_bar(da.DEFAULT_FILTERS, "gender"))
    assert "Sex filter does not apply" in bar and "(filtered)" not in bar


def test_filter_panel_is_hidden_until_the_button_is_pressed():
    import app
    from dashboard import callbacks as cb
    ids = _ids(app.serve_layout())
    assert "filter-open" in ids and "filter-panel" in ids
    assert cb.panel_class("filter-open", "filter-panel") == "filter-panel open"
    assert cb.panel_class("filter-open", "filter-panel open") == "filter-panel"
    assert cb.panel_class("filter-close", "filter-panel open") == "filter-panel"
    assert cb.panel_class("filter-close", "filter-panel") == "filter-panel"


def test_filter_badge_counts_active_filters():
    from dashboard import callbacks as cb
    from dashboard import data_access as da
    assert cb.active_filter_count(da.DEFAULT_FILTERS) == 0
    assert cb.active_filter_count({**da.DEFAULT_FILTERS, "season": "Winter", "countries": ["NOR"]}) == 2
    assert cb.show_filter_count(da.DEFAULT_FILTERS)[1].endswith("d-none")

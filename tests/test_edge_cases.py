"""Phase 6 robustness sweep: every chart builder x a set of awkward filter combinations.

A chart may legitimately be empty for a filter, but it must never raise. Each
case returns a Plotly figure (or rows) - an empty state is fine, an exception is not.
"""
import sys
from pathlib import Path

import plotly.graph_objects as go
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "processed" / "athlete_games.parquet").exists(),
                                reason="run scripts/prepare_data.py first")

from dashboard import data_access as da  # noqa: E402
from dashboard.tabs import countries as co, gender as ge, overview as ov, physiques as ph, sports as sp  # noqa: E402

D = da.DEFAULT_FILTERS
FILTERS = {
    "default": D,
    "one_games_2016": {**D, "years": [2016, 2016], "season": "Summer"},
    "one_year_both_seasons_1924": {**D, "years": [1924, 1924]},
    "first_games_1896": {**D, "years": [1896, 1896]},
    "winter_only": {**D, "season": "Winter"},
    "women_only": {**D, "sex": "Female"},
    "early_men": {**D, "sex": "Male", "years": [1896, 1912]},
    "small_country_jam": {**D, "countries": ["JAM"]},
    "historic_country_urs": {**D, "countries": ["URS"]},
    "tiny_team_nru": {**D, "countries": ["NRU"]},
    "two_sports": {**D, "sports": ["Swimming", "Judo"]},
    "single_minor_sport": {**D, "sports": ["Aeronautics"], "hide_minor": False},
    "show_minor": {**D, "hide_minor": False},
    "no_games_war": {**D, "years": [1916, 1918]},
    "summer_in_winter_year": {**D, "years": [2022, 2022], "season": "Summer"},
    "winter_women_1924": {**D, "years": [1924, 1924], "season": "Winter", "sex": "Female"},
    "everything_narrow": {**D, "years": [1952, 1956], "season": "Winter", "sex": "Female",
                          "countries": ["NOR", "FIN"], "sports": ["Cross Country Skiing"]},
}


def _first_focus(f):
    opts = ph.sport_options(f)
    return opts[0]["value"] if opts else None


def builders(f):
    focus = _first_focus(f)
    eds = co.scatter_games_options(f)[1]
    colors = sp.compare_colors([s for s in sp.DEFAULT_COMPARE])
    yield "ov.treemap", lambda: ov.fig_treemap(f)
    yield "ov.search", lambda: ov.search_athletes(f, "a")
    yield "ov.search_sport", lambda: ov.search_athletes(f, None, sport="Swimming")
    for metric in ("total", "per_million", "per_gdp"):
        for mode in ("range", "games"):
            yield f"co.map_{metric}_{mode}", lambda m=metric, md=mode: co.fig_map(f, m, md)
    yield "co.scatter", lambda: co.fig_scatter(f, eds)
    yield "co.heat_count", lambda: co.fig_heatmap(f, "count")
    yield "co.heat_index", lambda: co.fig_heatmap(f, "index")
    yield "co.host", lambda: co.fig_host(f)
    for measure in ph.MEASURES:
        yield f"ph.trend_{measure}", lambda m=measure: ph.fig_trend(f, m, focus)
        yield f"ph.violin_{measure}", lambda m=measure: ph.fig_violin(f, m, focus)
    yield "ph.density", lambda: ph.fig_density(f, focus)
    yield "ph.density_nofocus", lambda: ph.fig_density(f, None)
    yield "ge.share", lambda: ge.fig_share(f)
    yield "ge.share_sport", lambda: ge.fig_share(f, "Boxing")
    yield "ge.timeline", lambda: ge.fig_timeline(f)
    yield "ge.timeline_sport", lambda: ge.fig_timeline(f, "Boxing")
    yield "ge.spine", lambda: ge.fig_spine(f)
    yield "sp.pca", lambda: sp.fig_pca(f, colors)
    yield "sp.dist", lambda: sp.fig_dist(f, colors)


CASES = [(fname, bname, fn) for fname, f in FILTERS.items() for bname, fn in builders(f)]


@pytest.mark.parametrize("fname,bname,fn", CASES, ids=[f"{a}-{b}" for a, b, _ in CASES])
def test_builder_never_raises(fname, bname, fn):
    out = fn()
    if isinstance(out, go.Figure):
        out.to_json()                     # must also serialise for the browser
    assert out is not None


def _message(fig):
    return " ".join(a.text or "" for a in fig.layout.annotations) if len(fig.data) == 0 else ""


@pytest.mark.parametrize("fname", list(FILTERS))
def test_empty_state_messages_are_meaningful(fname):
    for bname, fn in builders(FILTERS[fname]):
        out = fn()
        if isinstance(out, go.Figure):
            assert "None" not in _message(out), f"{bname}: {_message(out)}"


def test_no_games_is_reported_as_no_games_not_missing_gdp():
    fig = co.fig_map(FILTERS["no_games_war"], "per_million", "range")
    assert "1960" not in _message(fig) and "No athletes" in _message(fig)

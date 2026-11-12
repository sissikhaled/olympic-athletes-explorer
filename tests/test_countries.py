"""Tests for the Countries & Medals tab (Q2.1-Q2.6)."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "processed" / "athlete_games.parquet").exists(),
                                reason="run scripts/prepare_data.py first")

from dashboard import data_access as da  # noqa: E402
from dashboard.tabs import countries as co  # noqa: E402

F = da.DEFAULT_FILTERS


# ---------------------------------------------------------------- selection logic
def test_click_toggles_selection():
    assert co.toggle([], "USA") == ["USA"]
    assert co.toggle(["USA", "CHN"], "USA") == ["CHN"]
    assert co.noc_from_click({"points": [{"customdata": "URS"}]}) == "URS"
    assert co.noc_from_click({"points": [{"customdata": ["GDR", "East Germany"]}]}) == "GDR"   # Sankey node
    assert co.noc_from_click({"points": [{"customdata": ["", "USSR → Unified Team"]}]}) is None  # Sankey link
    assert co.noc_from_click(None) is None


def test_selection_colours_follow_order_and_cap():
    c = co.selection_colors(["USA", "CHN", "GBR", "FRA", "ITA"])
    assert len(set(list(c.values())[:4])) == 4 and c["ITA"] != c["USA"]


# ---------------------------------------------------------------- Q2.1 map
def test_map_places_historic_teams_and_keeps_them_separate():
    d = co.map_totals(da.filter_country_games(F))
    urs, rus = d.set_index("noc").loc["URS"], d.set_index("noc").loc["RUS"]
    assert urs.map_iso3 == "RUS" and rus.map_iso3 == "RUS"          # same place, two circles (D15)
    assert urs.total > 1000


def test_map_rates_need_1960_or_later():
    fig = co.fig_map({**F, "years": [1896, 1956]}, "per_million")
    assert len(fig.data) == 0                                         # explanatory empty state
    d = co.map_rates(da.filter_country_games(F), "per_million")
    assert d.iso3.notna().all() and (d.rate >= 0).all()


def test_map_play_mode_has_one_frame_per_games():
    fig = co.fig_map({**F, "season": "Winter"}, "total", "games")
    assert len(fig.frames) == 24 and fig.layout.sliders


# ---------------------------------------------------------------- Q2.2 bump
def test_bump_only_shows_top_ten_and_breaks_lines():
    fig = co.fig_bump(F)
    ys = np.concatenate([np.array(t.y, dtype=float) for t in fig.data])
    assert np.nanmax(ys) <= 10 and np.isnan(ys).any()                 # gaps when outside the top 10
    assert "Summer" in fig.layout.title.text                          # Both -> Summer, with a note


def test_bump_highlights_selection():
    _, highlight, _ = co.bump_data({**F, "countries": ["URS", "XXX"]})
    assert highlight == ["URS"]                                       # unknown / never-top-10 codes dropped
    _, default, _ = co.bump_data(F)
    assert default == ["USA", "URS", "GBR", "CHN"]                    # most Summer golds, 1896-2022


# ---------------------------------------------------------------- Q2.3 scatter
def test_scatter_trend_and_ratio():
    d = co.scatter_data(61)                                           # Tokyo 2020
    slope, _ = d.attrs["fit"]
    assert slope > 0                                                  # richer countries win more
    assert np.isclose(np.exp(np.log(d.ratio).mean()), 1, atol=0.05)   # residuals centred on the line


# ---------------------------------------------------------------- Q2.4 heatmap
def test_heatmap_index_definition():
    z, counts = co.heatmap_matrix(F, "index")
    usa = counts.loc["USA"]
    m = co.heatmap_matrix(F, "count")[1]
    assert z.shape == counts.shape and z.shape[0] <= co.HEATMAP_ROWS
    assert (z.loc["USA"] >= 0).all() and m.values.sum() > 0 and usa.sum() > 0


def test_heatmap_keeps_selected_countries():
    z, _ = co.heatmap_matrix({**F, "countries": ["JAM"]}, "count")
    assert z.index[0] == "JAM"


# ---------------------------------------------------------------- Q2.5 hosts
def test_host_advantage_is_visible():
    d, _ = co.host_data(F)
    assert (d.home > d.usual).mean() > 0.8
    assert "2008 Beijing · CHN" in set(d.label)


# ---------------------------------------------------------------- Q2.6 Sankey
def test_team_switches_contain_known_flows():
    s = co.team_switches(F).set_index(["prev", "noc"]).athletes
    assert s[("URS", "EUN")] > 100 and s[("FRG", "GER")] > 100
    assert (s.index.get_level_values(0) != s.index.get_level_values(1)).all()


def test_sankey_hides_small_flows_and_reports_them():
    fig = co.fig_sankey(F, 10)
    assert min(fig.data[0].link.value) >= 10 and "hidden" in fig.layout.title.text


def test_all_charts_survive_empty_filters():
    none = {**F, "years": [1916, 1918]}
    for fig in (co.fig_map(none), co.fig_bump(none), co.fig_heatmap(none), co.fig_host(none),
                co.fig_sankey(none), co.fig_scatter(none, None)):
        assert len(fig.data) == 0

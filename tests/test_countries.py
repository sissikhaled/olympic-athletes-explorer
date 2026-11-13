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
# ---------------------------------------------------------------- Q2.2 scatter
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


def test_heatmap_combines_historic_teams_with_successors():
    z, counts = co.heatmap_matrix(F, "count")
    assert not {"URS", "GDR", "FRG", "EUN", "ROC"} & set(z.index)     # folded into RUS / GER
    m = co.da.table("medals_by_sport")
    gym = m[(m.sport == "Artistic Gymnastics") & m.noc.isin(["URS", "EUN", "ROC", "RUS"])].total.sum()
    assert counts.loc["RUS", "Artistic Gymnastics"] == gym
    assert set(co.predecessors("GER")) == {"GDR", "FRG", "SAA"}
    z, _ = co.heatmap_matrix({**F, "countries": ["URS"]}, "count")
    assert z.index[0] == "RUS"                                          # selecting the USSR shows Russia's row
    fig = co.fig_heatmap(F, "count")
    assert "RUS*" in fig.data[0].y and "predecessor" in fig.layout.annotations[0].text


def test_lineage_keeps_mixed_teams_apart():
    lin = co.da.lineage()
    assert lin["URS"] == "RUS" and lin["GDR"] == "GER" and lin["TCH"] == "CZE"
    assert "ANZ" not in lin and "WIF" not in lin and "COR" not in lin


# ---------------------------------------------------------------- Q2.3 hosts
def test_host_advantage_is_visible():
    d, _ = co.host_data(F)
    assert (d.home > d.usual).mean() > 0.8
    assert "2008 Beijing · CHN" in set(d.label)


# ---------------------------------------------------------------- Q2.6 Sankey
def test_all_charts_survive_empty_filters():
    none = {**F, "years": [1916, 1918]}
    for fig in (co.fig_map(none), co.fig_heatmap(none), co.fig_host(none), co.fig_scatter(none, None)):
        assert len(fig.data) == 0

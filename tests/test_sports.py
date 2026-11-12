"""Tests for the Sport Comparison tab (Q5.1-Q5.3)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "processed" / "athlete_games.parquet").exists(),
                                reason="run scripts/prepare_data.py first")

from dashboard import data_access as da  # noqa: E402
from dashboard.tabs import sports as sp  # noqa: E402

F = da.DEFAULT_FILTERS


def test_profiles_need_measured_athletes_and_ignore_sport_filter():
    p = sp.profiles({**F, "sports": ["Judo"]})                 # sidebar sport filter ignored
    assert len(p) > 40 and (p.n_measured >= sp.MIN_MEASURED).all()
    assert p.female.between(0, 100).all()


def test_pca_axes_are_interpretable():
    m, load, var = sp.pca_map(F)
    assert sum(var) > 60                                          # two axes keep most of the differences
    assert load.loc["weight", "x"] > 0 and load.loc["age", "y"] > 0.8
    assert m.loc["Basketball", "x"] > 0 > m.loc["Rhythmic Gymnastics", "x"]   # big vs small
    assert m.loc["Equestrian Dressage", "y"] > m.loc["Swimming", "y"]          # older vs younger
    assert "heavier" in sp.axis_name(load.x, var[0], 1) and "older" in sp.axis_name(load.y, var[1], 2)


def test_sex_filter_drops_share_of_women():
    assert "female" not in sp.feature_list({**F, "sex": "Female"})
    m, load, _ = sp.pca_map({**F, "sex": "Male"})
    assert "female" not in load.index and len(m) > 20


def test_selection_rules():
    valid = {"A", "B", "C", "D", "E"}
    assert sp.update_selection(["A", "B", "C", "D"], valid, "click", click_sport="E")[0] == ["B", "C", "D", "E"]
    assert sp.update_selection(["A", "B"], valid, "click", click_sport="B") == (["A"], "Pick at least 2 sports to compare.")
    assert sp.update_selection(["A"], valid, "lasso", lasso_sports=["E", "D", "C", "B", "A"])[0] == ["E", "D", "C", "B"]
    assert sp.update_selection(["A", "X"], valid, None)[0] == ["A"]          # unknown sports dropped


def test_radar_uses_standard_scores():
    fig = sp.fig_radar(F, sp.compare_colors(["Basketball", "Artistic Gymnastics"]))
    bb = next(t for t in fig.data if t.name == "Basketball")
    height_z = bb.customdata[0][1]
    assert height_z > 1                                           # basketball well above average height
    assert all(0 <= r <= 6 for r in bb.r)
    assert fig.data[0].name == "average sport" and set(fig.data[0].r) == {3}


def test_distributions_per_measure():
    fig = sp.fig_dist(F, sp.compare_colors(["Basketball", "Weightlifting"]))
    violins = [t for t in fig.data if t.type == "violin"]
    assert len(violins) == 6                                      # 2 sports x 3 measures


def test_colour_follows_the_sport_not_its_position():
    c1 = sp.compare_colors(["Basketball", "Judo", "Rowing", "Swimming"])
    c2 = sp.compare_colors(["Judo", "Rowing", "Swimming", "Bobsleigh"], c1)   # Basketball dropped
    assert all(c2[s] == c1[s] for s in ["Judo", "Rowing", "Swimming"])     # survivors keep their colour
    assert c2["Bobsleigh"] == c1["Basketball"]                              # newcomer takes the freed one
    assert len(set(c2.values())) == 4


def test_empty_states():
    none = {**F, "years": [1916, 1918]}
    for fig in (sp.fig_pca(none, {}), sp.fig_radar(none, {"Judo": "#2a78d6"}), sp.fig_dist(none, {"Judo": "#2a78d6"})):
        assert len(fig.data) == 0

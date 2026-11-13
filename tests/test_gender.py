"""Tests for the Gender tab (Q4.1-Q4.4) and decision D16 (DNS-only athletes)."""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "processed" / "athlete_games.parquet").exists(),
                                reason="run scripts/prepare_data.py first")

from dashboard import data_access as da  # noqa: E402
from dashboard.tabs import gender as ge  # noqa: E402

F = da.DEFAULT_FILTERS


def test_d16_dns_only_athletes_are_not_participants():
    ag = da.table("athlete_games")
    assert not ag[(ag.year == 1896) & ag.is_female].shape[0]          # Revithi & Melpomene did not start
    assert ag[ag.is_female & (ag.sport == "Athletics")].year.min() == 1928


def test_share_line_matches_known_levels_and_ignores_sex_filter():
    g = ge.share_by_games({**F, "sex": "Male"}).set_index(["season", "year"]).share
    assert g[("Summer", 1900)] < 3 and 45 < g[("Summer", 2020)] < 50
    assert g[("Winter", 1924)] > 0


def test_every_milestone_is_backed_by_the_data():
    g = ge.share_by_games(F)
    held = set(zip(g.season, g.year))
    for season, year, _ in ge.MILESTONES:
        assert (season, year) in held
    w = da.table("athlete_games").query("is_female")
    assert w[w.sport == "Boxing"].year.min() == 2012
    assert w[w.sport == "Ski Jumping"].year.min() == 2014


def test_timeline_orders_sports_by_when_women_entered():
    t = ge.timeline_data(F)
    entered = t.women_from.dropna().tolist()
    assert entered == sorted(entered)                               # earliest entry at the top
    assert t.women_from.isna().tolist() == sorted(t.women_from.isna().tolist())   # never-with-women last
    row = t.set_index("sport")
    assert row.loc["Boxing", "women_from"] == 2012
    assert row.loc["Ski Jumping", "women_from"] == 2014
    assert pd.isna(row.loc["Nordic Combined", "women_from"])        # still men only in 2022
    assert row.loc["Artistic Swimming", "women_only"]
    assert "Tug-Of-War" not in row.index and t.attrs["dropped"] > 0   # discontinued sports hidden


def test_timeline_labels_extremes_in_words():
    fig = ge.fig_timeline(F, "Boxing")
    status = dict(zip(fig.data[-1].customdata, fig.data[-1].text))
    assert status["Nordic Combined"] == "men only" and status["Rhythmic Gymnastics"] == "women only"
    assert status["Athletics"].endswith("%")
    assert "<b>Boxing</b>" in fig.layout.yaxis.categoryarray


def test_timeline_click_parsing():
    assert ge.sport_from_timeline_click({"points": [{"customdata": "Boxing", "y": "Boxing"}]}) == "Boxing"
    assert ge.sport_from_timeline_click({"points": [{"y": "<b>Judo</b>"}]}) == "Judo"
    assert ge.sport_from_timeline_click(None) is None


def test_spine_shares_add_up_and_sorted_by_imbalance():
    s = ge.spine_data(F)
    assert len(s) == ge.TOP_COUNTRIES
    assert ((s.women_pct + s.men_pct - 100).abs() < 1e-9).all()
    gap = (s.women_pct - 50).abs().tolist()
    assert gap == sorted(gap, reverse=True)


def test_followed_sport_adds_a_line():
    fig = ge.fig_share(F, "Boxing")
    assert [t.name for t in fig.data] == ["Summer", "Winter", "Boxing"]


def test_empty_states():
    none = {**F, "years": [1916, 1918]}
    for fig in (ge.fig_share(none), ge.fig_timeline(none), ge.fig_spine(none)):
        assert len(fig.data) == 0

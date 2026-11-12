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


def test_heatmap_blank_when_small_and_ordered_by_first_women():
    share, w, n = ge.heatmap_data(F)
    assert share.notna().values.sum() > 0
    assert ((n >= ge.MIN_CELL) | share.isna()).all().all()          # every shown cell has enough athletes
    assert ((share >= 0) & (share <= 100) | share.isna()).all().all()
    assert share.index[-1] in {"Polo", "Roller Hockey", "Rugby", "Tug-Of-War", "Military Ski Patrol"}


def test_heatmap_click_parsing():
    assert ge.sport_from_heat_click({"points": [{"customdata": [3, 10, "Boxing"], "y": "Boxing"}]}) == "Boxing"
    assert ge.sport_from_heat_click({"points": [{"y": "<b>Judo</b>"}]}) == "Judo"
    assert ge.sport_from_heat_click(None) is None


def test_spine_shares_add_up_and_sorted_by_imbalance():
    s = ge.spine_data(F)
    assert len(s) == ge.TOP_COUNTRIES
    assert ((s.women_pct + s.men_pct - 100).abs() < 1e-9).all()
    gap = (s.women_pct - 50).abs().tolist()
    assert gap == sorted(gap, reverse=True)


def test_pyramid_percentages_per_sex_sum_to_100():
    p = ge.pyramid_data(F)
    assert (p.sum().round(6) == 100).all()
    assert p.attrs["median"]["Female"] <= p.attrs["median"]["Male"]


def test_followed_sport_adds_a_line():
    fig = ge.fig_share(F, "Boxing")
    assert [t.name for t in fig.data] == ["Summer", "Winter", "Boxing"]


def test_empty_states():
    none = {**F, "years": [1916, 1918]}
    for fig in (ge.fig_share(none), ge.fig_heatmap(none), ge.fig_spine(none), ge.fig_pyramid(none)):
        assert len(fig.data) == 0

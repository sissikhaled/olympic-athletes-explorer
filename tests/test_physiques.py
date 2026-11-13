"""Tests for the Physiques tab (Q3.1-Q3.4)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "processed" / "athlete_games.parquet").exists(),
                                reason="run scripts/prepare_data.py first")

from dashboard import data_access as da  # noqa: E402
from dashboard.tabs import physiques as ph  # noqa: E402

F = da.DEFAULT_FILTERS


def test_counting_unit_body_once_per_sport_age_per_games():
    h = ph.physique_frame(F, "height_cm")
    assert not h.duplicated(["athlete_id", "sport"]).any()
    a = ph.physique_frame(F, "age")
    assert a.duplicated(["athlete_id", "sport"]).any()          # multi-Games athletes appear per Games


def test_density_is_light_and_overlays_the_focus_sport():
    fig = ph.fig_density(F, "Basketball")
    assert len(fig.to_json()) < 600_000                           # contour + one sport, no hidden layer
    assert fig.data[0].type == "contour"
    names = [t.name for t in fig.data[1:]]
    assert names and all(n.startswith("Basketball") for n in names)


def test_trend_drops_thin_games_and_reports_n():
    t = ph.trend_stats(F, "height_cm", "Basketball")
    assert (t.n >= ph.MIN_N_TREND).all()
    men = t[t.sex == "Male"].set_index("year")["median"]
    assert men.loc[2016] > men.loc[1960]                         # basketball players got taller


def test_swimming_medallists_are_taller():
    d = ph.physique_frame(F, "height_cm")
    m = d[(d.sport == "Swimming") & (d.sex == "Male")].groupby("is_medalist").value.median()
    assert m[True] > m[False]


def test_focus_sport_options_need_measured_athletes():
    opts = {o["value"] for o in ph.sport_options(F)}
    assert "Basketball" in opts and "Military Ski Patrol" not in opts


def test_empty_states():
    none = {**F, "years": [1916, 1918]}
    for fig in (ph.fig_density(none, "Basketball"),
                ph.fig_trend(none, "height_cm", "Basketball"), ph.fig_violin(none, "age", "Basketball")):
        assert len(fig.data) == 0


def test_focus_sport_stays_valid_when_filters_change():
    opts, value = ph.update_focus_sport({**F, "season": "Winter"}, "Basketball")
    assert value in {o["value"] for o in opts} and value != "Basketball"
    opts, value = ph.update_focus_sport(F, "Rowing")
    assert value == "Rowing"

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


def test_boxes_sorted_by_median_and_respect_minimum_n():
    s = ph.box_stats(F, "height_cm")
    assert (s.n >= ph.MIN_N).all()
    order = s.drop_duplicates("sport").sort_values("order").sport.tolist()
    assert order[0] == "Artistic Gymnastics" and order[-1] == "Basketball"
    assert ((s.q1 <= s["median"]) & (s["median"] <= s.q3) & (s.lo <= s.q1) & (s.q3 <= s.hi)).all()


def test_box_click_and_focus_highlight():
    assert ph.sport_from_box_click({"points": [{"y": "Rowing", "x": 190}]}) == "Rowing"
    fig = ph.fig_boxes(F, "height_cm", "Rowing")
    assert any("<b>Rowing</b>" in t for t in fig.layout.yaxis.ticktext)
    assert fig.layout.height > 1000                             # one row per sport


def test_sex_filter_leaves_one_box_per_sport():
    fig = ph.fig_boxes({**F, "sex": "Female"}, "height_cm", None)
    assert [t.name for t in fig.data] == ["Women"]


def test_density_payload_and_selection():
    fig = ph.fig_density(F, "Basketball")
    assert len(fig.to_json()) < 2_500_000                        # server-side contour keeps it light
    d = ph.density_frame(F)
    tall = d[d.height_cm > 215]
    # the shape Dash really sends: positions in the all-athletes layer, no customdata
    sel = {"points": [{"curveNumber": ph.SELECT_LAYER, "pointIndex": int(i)} for i in tall.index]
                     + [{"curveNumber": 2, "pointIndex": 0}]}          # focus-sport points are ignored
    rows, info = ph.selection_rows(F, sel)
    assert len(rows) == tall.athlete_id.nunique() and "Basketball" in info
    assert ph.density_frame(F).equals(d)                               # order is reproducible
    assert ph.selection_rows(F, None)[0] == []


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
    for fig in (ph.fig_boxes(none, "height_cm", None), ph.fig_density(none, "Basketball"),
                ph.fig_trend(none, "height_cm", "Basketball"), ph.fig_violin(none, "age", "Basketball")):
        assert len(fig.data) == 0

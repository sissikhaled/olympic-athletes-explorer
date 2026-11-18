"""Tests for the Overview tab builders (KPIs, treemap, athlete search)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "processed" / "athlete_games.parquet").exists(),
                                reason="run scripts/prepare_data.py first")

from dashboard import data_access as da  # noqa: E402
from dashboard.tabs import overview as ov  # noqa: E402

F = da.DEFAULT_FILTERS
RIO = {**F, "years": [2016, 2016], "season": "Summer"}


def test_filters_match_official_rio_2016():
    """Known facts: 306 medal events and 207 teams (205 NOCs + Refugee team + Independent athletes)."""
    assert da.filter_events(RIO).result_id.nunique() == 306
    assert da.filter_athletes(RIO).noc.nunique() == 207


def test_overview_is_visuals_only():
    import json
    text = json.dumps(ov.layout().to_plotly_json(), default=str)
    assert "kpi" not in text and "How to read" not in text and "tab-intro" not in text


def test_treemap_hierarchy_is_consistent():
    n = ov.treemap_frame(F)
    assert set(n.level) == {"season", "sport", "event"}
    ids = set(n.id)
    assert all(p == "" or p in ids for p in n.parent)   # every parent exists
    sports = n[n.level == "sport"].set_index("id").value
    events = n[n.level == "event"].groupby("parent").value.sum()
    assert (sports == events.reindex(sports.index)).all()  # branchvalues="total" holds


def test_treemap_click_selects_sport():
    assert ov.sport_from_click({"points": [{"id": "Winter/Biathlon"}]}) == "Biathlon"
    assert ov.sport_from_click({"points": [{"id": "Winter/Biathlon/Relay, Men"}]}) == "Biathlon"
    assert ov.sport_from_click({"points": [{"id": "Summer"}]}) is None
    assert ov.sport_from_click(None) is None


def test_search_is_accent_insensitive_and_ranked():
    rows, _ = ov.search_athletes(F, "comaneci")
    assert rows[0]["name"] == "Nadia Comăneci"
    rows, _ = ov.search_athletes(F, None)
    assert rows[0]["name"] == "Michael Phelps" and rows[0]["medals"] == 28
    medals = [r["medals"] for r in rows]
    assert medals == sorted(medals, reverse=True)


def test_search_respects_filters_and_handles_no_match():
    rows, _ = ov.search_athletes({**F, "season": "Winter"}, "phelps")
    assert rows == []
    rows, info = ov.search_athletes(F, "zzzz-no-such-athlete")
    assert rows == [] and "No athlete" in info


def test_empty_filters_give_placeholder_figures():
    none = {**F, "years": [1916, 1918]}
    fig = ov.fig_treemap(none)
    assert len(fig.data) == 0 and fig.layout.annotations


def test_treemap_click_narrows_the_athlete_table():
    rows, info = ov.search_athletes(F, None, sport="Swimming")
    assert rows[0]["name"] == "Michael Phelps" and "Swimming athletes" in info
    rows, _ = ov.search_athletes(F, None, sport="Biathlon")
    assert all("Biathlon" in r["sports"] for r in rows)
    rows, _, info = ov.update_athlete_table(F, "phelps", {"points": [{"id": "Winter/Biathlon"}]})
    assert rows == [] and "Biathlon" in info


def test_treemap_puts_each_sport_under_its_own_season():
    n = ov.treemap_frame(F)
    sports = n[n.level == "sport"]
    assert not sports.label.duplicated().any()                       # one tile per sport
    skating = sports.set_index("label").loc["Figure Skating"]
    assert skating.parent == "Winter" and "1908 and 1920 Summer Games" in skating.note
    assert sports.set_index("label").loc["Ice Hockey"].parent == "Winter"
    assert n[n.level == "season"].value.sum() == len(da.filter_events(F))   # nothing dropped

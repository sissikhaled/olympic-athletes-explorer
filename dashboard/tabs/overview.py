"""Tab 1, Overview: the programme treemap and the athlete search (descriptive, visuals only)

Chart builders are plain functions (filters in, figure/rows out) so they can
be tested without a browser; the @callback functions only wire them to the page.
"""
from __future__ import annotations

import unicodedata
from functools import lru_cache

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, html
import dash_bootstrap_components as dbc

from .. import data_access as da
from ..components import tab_callback, chart_card, data_grid, medal_badges
from ..theme import SEASON_COLORS, TEXT_PRIMARY, empty_figure, tint

TAB_ID = "overview"
LABEL = "Overview"



# ====================================================================== layout
def layout():
    """Visuals only: the programme treemap and the athlete search (no KPI cards, no prose)."""
    return html.Div([
        chart_card("ov-treemap", "Sports and events by number of athletes", "Treemap", "Part to whole",
                   height=640),
        dbc.Card(dbc.CardBody([
            dbc.Input(id="ov-search", placeholder="Search athletes by name, e.g. phelps or comaneci…",
                      type="search", debounce=True, className="mb-2"),
            html.Div(id="ov-search-info", className="small text-secondary mb-2"),
            data_grid("ov-athlete-table", page_size=10, row_selection="single"),
            html.Div(id="ov-athlete-card", className="mt-3"),
        ]), className="chart-card"),
    ], className="pt-2")


# ====================================================================== treemap
def treemap_frame(f: dict) -> pd.DataFrame:
    """Nodes for Season -> Sport -> Event, valued by athlete entries.

    Each sport sits under its OWN season (sports table), not the season of the Games:
    figure skating (1908, 1920) and ice hockey (1920) were held at Summer Games before the
    Winter Games began in 1924, but they are Winter sports. Those entries stay counted, under
    Winter, and the hover says so."""
    e = da.filter_events(f)
    if e.empty:
        return pd.DataFrame()
    sport_season = da.table("sports").set_index("sport").season
    e = e.assign(games_season=e.season, season=e.sport.map(sport_season).fillna(e.season))
    leaf = e.groupby(["season", "sport", "event"], observed=True).size().rename("value").reset_index()
    sport = leaf.groupby(["season", "sport"], as_index=False).value.sum()
    # entries of a sport at Games of the other season, e.g. figure skating at the 1908 Summer Games
    other = e[e.games_season != e.season]
    def _years(g):
        y = [str(v) for v in sorted(set(g.year))]
        return y[0] if len(y) == 1 else ", ".join(y[:-1]) + " and " + y[-1]
    note = {sp: f"incl. {len(g):,} entries at the {_years(g)} {g.games_season.iloc[0]} Games, "
                "before the Winter Games began" for sp, g in other.groupby("sport")}
    season = leaf.groupby("season", as_index=False).value.sum()
    nodes = pd.concat([
        season.assign(id=season.season, label=season.season, parent="", level="season", note=""),
        sport.assign(id=sport.season + "/" + sport.sport, label=sport.sport, parent=sport.season,
                     level="sport", note=sport.sport.map(lambda sp: note.get(sp, ""))),
        leaf.assign(id=leaf.season + "/" + leaf.sport + "/" + leaf.event,
                    label=leaf.event, parent=leaf.season + "/" + leaf.sport, level="event", note=""),
    ], ignore_index=True)
    return nodes


def fig_treemap(f: dict) -> go.Figure:
    n = treemap_frame(f)
    if n.empty:
        return empty_figure()
    # Full season colour only on the two top tiles; sports and events get light tints,
    # so the large areas stay calm and the dark text stays readable
    base = n.season.map(SEASON_COLORS)
    amount = n.level.map({"season": 0.0, "sport": 0.55, "event": 0.72})
    colors = [tint(c, a) for c, a in zip(base, amount)]
    total = n.loc[n.level == "season", "value"].sum()
    fig = go.Figure(go.Treemap(
        ids=n.id, labels=n.label, parents=n.parent, values=n.value, branchvalues="total",
        maxdepth=2, marker=dict(colors=colors, line=dict(width=1, color="white")),
        textfont=dict(color=TEXT_PRIMARY), insidetextfont=dict(color=TEXT_PRIMARY),
        texttemplate="<b>%{label}</b><br>%{value:,}",
        customdata=np.stack([(n.value / total * 100).round(1),
                             n.note.map(lambda t: f"<br><i>{t}</i>" if t else "")], axis=1),
        hovertemplate="<b>%{label}</b><br>%{value:,} athlete entries<br>%{customdata[0]}% of all entries"
                      "<br>part of %{parent}%{customdata[1]}<extra></extra>",
        pathbar=dict(visible=True, thickness=22),
        tiling=dict(pad=2),
    ))
    fig.update_layout(margin=dict(l=4, r=4, t=4, b=4))
    return fig


def sport_from_click(click) -> str | None:
    """Treemap click -> sport name, or None for the root/season level."""
    if not click or not click.get("points"):
        return None
    node = click["points"][0].get("id", "")
    parts = node.split("/")
    # Plotly reports the clicked node; clicking the path bar (zoom out) reports the parent
    return parts[1] if len(parts) >= 2 else None


# ====================================================================== athlete search
def _fold(s: str) -> str:
    """Lower-case and strip accents so 'comaneci' finds 'Comăneci'."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


@lru_cache(maxsize=1)
def _folded_names() -> pd.Series:
    ag = da.table("athlete_games")
    return pd.Series([_fold(n) for n in ag.name], index=ag.index)


NUM = {"type": "numericColumn", "filter": False, "minWidth": 84, "flex": 1}
GRID_COLUMNS = [
    {"field": "name", "headerName": "Athlete", "minWidth": 190, "flex": 3},
    {"field": "noc", "headerName": "Team", "minWidth": 90, "flex": 1},
    {"field": "sports", "headerName": "Sport(s)", "minWidth": 170, "flex": 3},
    {"field": "years", "headerName": "Years", "minWidth": 110, "flex": 1.5},
    {"field": "n_games", "headerName": "Games", **NUM},
    {"field": "gold", "headerName": "Gold", **NUM},
    {"field": "silver", "headerName": "Silver", **NUM},
    {"field": "bronze", "headerName": "Bronze", **NUM},
    {"field": "medals", "headerName": "Total", "sort": "desc", **{**NUM, "minWidth": 100}},
]


def search_athletes(f: dict, query: str | None, limit: int = 500,
                    sport: str | None = None) -> tuple[list[dict], str]:
    a = da.filter_athletes(f)
    if sport:
        a = a[a.sport == sport]
    q = (query or "").strip()
    if q:
        a = a[_folded_names().loc[a.index].str.contains(_fold(q), regex=False)]
    if a.empty:
        where = f" in {sport}" if sport else ""
        return [], (f"No athlete named “{q}”{where} in the current filters." if q
                    else "No athletes match the filters.")
    # 1) fast numeric aggregation for every athlete, 2) text columns only for the rows shown
    g = (a.groupby("athlete_id")
          .agg(first=("year", "min"), last=("year", "max"), n_games=("edition_id", "nunique"),
               gold=("n_gold", "sum"), silver=("n_silver", "sum"), bronze=("n_bronze", "sum")))
    g["medals"] = g.gold + g.silver + g.bronze
    g = g.sort_values(["medals", "gold", "n_games"], ascending=False)
    n = len(g)
    shown = g.head(limit).reset_index()
    rows = a[a.athlete_id.isin(shown.athlete_id)]
    text = rows.groupby("athlete_id").agg(name=("name", "first"),
                                          noc=("noc", lambda s: " / ".join(dict.fromkeys(s))),
                                          sports=("sport", lambda s: ", ".join(dict.fromkeys(s))))
    shown = shown.merge(text, on="athlete_id")
    shown["years"] = shown["first"].astype(str).where(
        shown["first"] == shown["last"], shown["first"].astype(str) + "–" + shown["last"].astype(str))
    scope = f"{sport} athletes" if sport else "athletes"
    if q:
        info = (f"1 {scope[:-1]} matches “{q}”" if n == 1 else f"{n:,} {scope} match “{q}”") + " in the current filters."
    else:
        info = f"Most decorated of {n:,} {scope} in the current filters (medals counted within the filters)."
    if sport:
        info += " Click the treemap's top bar to show all sports again."
    if n > limit:
        info += f" Showing the top {limit}."
    return shown.drop(columns=["first", "last"]).to_dict("records"), info


def athlete_card(athlete_id: int) -> html.Div:
    """Full career of one athlete (ignores the filters on purpose)."""
    bio = da.table("athletes").set_index("athlete_id").loc[athlete_id]
    ev = da.table("athlete_events")
    ev = ev[ev.athlete_id == athlete_id].merge(da.table("games")[["edition_id", "games"]], on="edition_id")
    facts = [f"{'Woman' if bio.sex == 'Female' else 'Man'}"]
    if pd.notna(bio.birth_year):
        facts.append(f"born {int(bio.birth_year)}")
    if pd.notna(bio.height_cm):
        facts.append(f"{bio.height_cm:.0f} cm")
    if pd.notna(bio.weight_kg):
        facts.append(f"{bio.weight_kg:.0f} kg" + (" (approx.)" if bio.weight_is_approx else ""))
    rows = []
    for (year, games), grp in ev.sort_values(["year", "season"]).groupby(["year", "games"], sort=False):
        counts = grp.medal.value_counts().reindex(["Gold", "Silver", "Bronze"], fill_value=0).to_dict()
        events = "; ".join(f"{r.event}" + (f" ({r.medal})" if pd.notna(r.medal) else "")
                           for r in grp.sort_values("medal").itertuples())
        rows.append(html.Tr([html.Td(games, className="text-nowrap fw-semibold"),
                             html.Td(" / ".join(dict.fromkeys(grp.noc))),
                             html.Td(" / ".join(dict.fromkeys(grp.sport))),
                             html.Td(events, className="small"),
                             html.Td(medal_badges(counts))]))
    return dbc.Card(dbc.CardBody([
        html.Div([html.Span(bio["name"], className="fw-bold fs-6 me-2"),
                  html.Span(" · ".join(facts), className="text-secondary small")]),
        html.Div("Full career, regardless of the filters.", className="small text-secondary mb-2"),
        dbc.Table([html.Thead(html.Tr([html.Th("Games"), html.Th("Team"), html.Th("Sport"),
                                       html.Th("Events (medal)"), html.Th("Medals")])),
                   html.Tbody(rows)], size="sm", hover=True, responsive=True, className="mb-0"),
    ]), className="athlete-card")


# ====================================================================== callbacks
@tab_callback(TAB_ID, Output("ov-treemap", "figure"), Input("filters", "data"))
def update_treemap(f):
    return fig_treemap(f)


@tab_callback(TAB_ID, Output("ov-athlete-table", "rowData"), Output("ov-athlete-table", "columnDefs"),
          Output("ov-search-info", "children"),
          Input("filters", "data"), Input("ov-search", "value"), Input("ov-treemap", "clickData"))
def update_athlete_table(f, query, click=None):
    rows, info = search_athletes(f, query, sport=sport_from_click(click))
    return rows, GRID_COLUMNS, info


@callback(Output("ov-athlete-card", "children"), Input("ov-athlete-table", "selectedRows"))
def show_athlete(selected):
    if not selected:
        return None
    return athlete_card(int(selected[0]["athlete_id"]))

"""Tab 1, Overview: the programme treemap and the athlete search (descriptive, visuals only)

Chart builders are plain functions (filters in, figure/rows out) so they can
be tested without a browser; the @callback functions only wire them to the page.
"""
from __future__ import annotations

import json
import unicodedata
from functools import lru_cache

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, clientside_callback, html
from dash.exceptions import PreventUpdate
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
            data_grid("ov-athlete-table", page_size=10, row_selection="single", columns=GRID_COLUMNS,
                      server_side=True),
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
DEFAULT_ORDER = ["medals", "gold", "n_games"]          # "most decorated first"
TEXT_FILTER_COLUMNS = {"name", "noc", "sports", "years"}


def athlete_table(f: dict, query: str | None = None, sport: str | None = None) -> tuple[pd.DataFrame, str]:
    """EVERY athlete matching the filters, search and treemap sport, one row each (cached per input).

    The grid then pages, sorts and filters this whole table on the server (page_rows), so a sort
    by year or team covers all matching athletes, not only the most decorated ones."""
    table, info = _athlete_table_cached(json.dumps(f, sort_keys=True), (query or "").strip(), sport or "")
    return table, info


def _joined(a: pd.DataFrame, col: str, sep: str) -> pd.Series:
    """Unique values per athlete in order of appearance, joined. Most athletes have exactly one
    team and one sport: those are copied directly, and only the rest are joined (fast)."""
    d = a[["athlete_id", col]].drop_duplicates()
    many = d.athlete_id.duplicated(keep=False)
    one = d[~many].set_index("athlete_id")[col]
    several = d[many].groupby("athlete_id", sort=False)[col].agg(sep.join)
    return pd.concat([one, several])


@lru_cache(maxsize=8)
def _athlete_table_cached(f_json: str, q: str, sport: str) -> tuple[pd.DataFrame, str]:
    f = json.loads(f_json)
    a = da.filter_athletes(f)
    if sport:
        a = a[a.sport == sport]
    if q:
        a = a[_folded_names().loc[a.index].str.contains(_fold(q), regex=False)]
    if a.empty:
        where = f" in {sport}" if sport else ""
        return pd.DataFrame(columns=["athlete_id"]), (
            f"No athlete named “{q}”{where} in the current filters." if q else "No athletes match the filters.")
    g = (a.groupby("athlete_id")
          .agg(name=("name", "first"), first=("year", "min"), last=("year", "max"),
               n_games=("edition_id", "nunique"), gold=("n_gold", "sum"), silver=("n_silver", "sum"),
               bronze=("n_bronze", "sum")))
    g["medals"] = g.gold + g.silver + g.bronze
    g["noc"] = _joined(a, "noc", " / ")
    g["sports"] = _joined(a, "sport", ", ")
    g["years"] = g["first"].astype(str).where(g["first"] == g["last"],
                                              g["first"].astype(str) + "–" + g["last"].astype(str))
    g = g.sort_values(DEFAULT_ORDER, ascending=False).reset_index()
    n = len(g)
    scope = f"{sport} athletes" if sport else "athletes"
    if q:
        info = (f"1 {scope[:-1]} matches “{q}”" if n == 1 else f"{n:,} {scope} match “{q}”") + " in the current filters."
    else:
        info = f"{n:,} {scope} in the current filters; sort or filter any column (medals counted within the filters)."
    if sport:
        info += " Click the treemap's top bar to show all sports again."
    return g, info


def _apply_text_filter(df: pd.DataFrame, col: str, model: dict) -> pd.DataFrame:
    """AG Grid text filter model (contains / equals / startsWith / ..., or two joined by AND / OR)."""
    if "conditions" in model:
        masks = [_text_mask(df[col], c) for c in model["conditions"]]
        if not masks:
            return df
        m = masks[0]
        for other in masks[1:]:
            m = (m & other) if model.get("operator", "AND") == "AND" else (m | other)
        return df[m]
    return df[_text_mask(df[col], model)]


def _text_mask(col: pd.Series, cond: dict) -> pd.Series:
    kind, value = cond.get("type", "contains"), _fold(str(cond.get("filter") or ""))
    text = col.astype(str).map(_fold)
    if kind == "blank":
        return text == ""
    if kind == "notBlank":
        return text != ""
    if not value:
        return pd.Series(True, index=col.index)
    return {"contains": text.str.contains(value, regex=False),
            "notContains": ~text.str.contains(value, regex=False),
            "equals": text == value, "notEqual": text != value,
            "startsWith": text.str.startswith(value), "endsWith": text.str.endswith(value)}.get(
        kind, text.str.contains(value, regex=False))


def page_rows(table: pd.DataFrame, request: dict | None) -> dict:
    """One page for AG Grid's infinite row model: filter, sort, then slice [startRow, endRow)."""
    request = request or {}
    df = table
    for col, model in (request.get("filterModel") or {}).items():
        if col in TEXT_FILTER_COLUMNS and col in df:
            df = _apply_text_filter(df, col, model)
    keys, asc = [], []
    for s in request.get("sortModel") or []:
        col, up = s.get("colId"), s.get("sort") == "asc"
        if col == "years":                     # by number: oldest first career start, or latest last Games
            keys += ["first", "last"] if up else ["last", "first"]
            asc += [up, up]
        elif col in df:
            keys.append(col)
            asc.append(up)
    if keys:
        df = df.sort_values(keys + ["athlete_id"], ascending=asc + [True], kind="stable")
    start, end = int(request.get("startRow", 0)), int(request.get("endRow", 10))
    rows = df.iloc[start:end].drop(columns=["first", "last"], errors="ignore")
    return {"rowData": rows.to_dict("records"), "rowCount": len(df)}


def search_athletes(f: dict, query: str | None, limit: int = 500,
                    sport: str | None = None) -> tuple[list[dict], str]:
    """The `limit` most decorated matching athletes (default order); used by tests and scripts."""
    table, info = athlete_table(f, query, sport)
    if table.empty:
        return [], info
    return page_rows(table, {"startRow": 0, "endRow": limit})["rowData"], info


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


@tab_callback(TAB_ID, Output("ov-search-info", "children"),
          Input("filters", "data"), Input("ov-search", "value"), Input("ov-treemap", "clickData"))
def update_athlete_info(f, query, click=None):
    return athlete_table(f, query, sport_from_click(click))[1]


@callback(Output("ov-athlete-table", "getRowsResponse"), Input("ov-athlete-table", "getRowsRequest"),
          State("filters", "data"), State("ov-search", "value"), State("ov-treemap", "clickData"))
def serve_athlete_rows(request, f, query, click):
    """The grid asks for one page at a time; sorting and filtering run here over all matching athletes."""
    if not request:
        raise PreventUpdate
    table, _ = athlete_table(f, query, sport_from_click(click))
    if table.empty:
        return {"rowData": [], "rowCount": 0}
    return page_rows(table, request)


# When the filters, search or treemap sport change, the grid drops its cached pages and asks again
clientside_callback(
    """function(f, q, click) {
        if (window.dash_ag_grid && dash_ag_grid.getApiAsync) {
            dash_ag_grid.getApiAsync("ov-athlete-table").then(api => {
                api.purgeInfiniteCache();
                api.deselectAll && api.deselectAll();
            });
        }
        return window.dash_clientside.no_update;
    }""",
    Output("ov-athlete-table", "id"), Input("filters", "data"), Input("ov-search", "value"),
    Input("ov-treemap", "clickData"), prevent_initial_call=True)


@callback(Output("ov-athlete-card", "children"), Input("ov-athlete-table", "selectedRows"))
def show_athlete(selected):
    if not selected:
        return None
    return athlete_card(int(selected[0]["athlete_id"]))

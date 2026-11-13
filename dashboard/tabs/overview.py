"""Tab 1, Overview: what is in the data? (Q1.1-Q1.4)

Chart builders are plain functions (filters in, figure/rows out) so they can
be tested without a browser; the @callback functions only wire them to the page.
"""
from __future__ import annotations

import unicodedata
from functools import lru_cache

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, html
import dash_bootstrap_components as dbc
from plotly.subplots import make_subplots

from .. import data_access as da
from ..components import tab_callback, chart_card, data_grid, medal_badges, tab_intro
from ..theme import (SEASON_COLORS, SEX_COLORS, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY,
                     empty_figure, tint)

TAB_ID = "overview"
LABEL = "Overview"

KPIS = [("kpi-athletes", "Athletes"), ("kpi-countries", "Countries"), ("kpi-sports", "Sports"),
        ("kpi-events", "Events contested"), ("kpi-medals", "Medals awarded")]

SEX_LABEL = {"Female": "Women", "Male": "Men"}
# Games cancelled by war (decision D10): shown as gaps, not silently bridged
CANCELLED = {"Summer": {1916: "WWI", 1940: "WWII", 1944: "WWII"}, "Winter": {1940: "WWII", 1944: "WWII"}}


# ====================================================================== layout
def kpi_tile(id_: str, label: str) -> dbc.Col:
    return dbc.Col(html.Div([html.Div("–", id=id_, className="kpi-value"),
                             html.Div(label, className="kpi-label"),
                             html.Div("", id=f"{id_}-delta", className="kpi-delta")],
                            className="kpi-tile"), xs=6, md=True)


def layout():
    return html.Div([
        tab_intro("What is in the data?",
                  "126 years of Olympic athletes at a glance: how big the Games are, how they grew, "
                  "how the programme is built, and a search for any individual athlete."),
        html.Div([html.Div([html.Span("Q1.1", className="q-id"),
                            html.Span("How big are the Games in the current selection?", className="q-text")]),
                  html.Div(id="kpi-context", className="chart-name")],
                 className="card-head mb-2"),
        dbc.Row([kpi_tile(i, l) for i, l in KPIS], className="g-2 mb-3"),
        dbc.Row([
            dbc.Col(chart_card(
                "ov-participation", "Q1.2", "How has participation grown, and how was it split between women and men?",
                "Stacked area", "Change v Time · Part to whole",
                "Total height = distinct athletes at each Games; the bands show the women/men split. "
                "Summer and Winter have their own scales. Gray labels mark Games cancelled by war.",
                height=400), lg=7),
            dbc.Col(chart_card(
                "ov-treemap", "Q1.3", "Which sports and events attract the most athletes?",
                "Treemap", "Part to whole",
                "Area = athlete entries (one athlete in one event). Click a sport to zoom into its events "
                "and to show only that sport in Q1.2; click the top bar to zoom back out.",
                height=400), lg=5),
        ], className="g-3 mb-3"),
        dbc.Card(dbc.CardBody([
            html.Div([html.Div([html.Span("Q1.4", className="q-id"),
                                html.Span("Who is a specific athlete, and what did they achieve?",
                                          className="q-text")]),
                      html.Span("Searchable table", className="chart-name")], className="card-head"),
            dbc.Input(id="ov-search", placeholder="Search by name, e.g. 'phelps' or 'comaneci' (accents optional)…",
                      type="search", debounce=True, className="mb-2"),
            html.Div(id="ov-search-info", className="small text-secondary mb-2"),
            data_grid("ov-athlete-table", page_size=10, row_selection="single"),
            html.Div(id="ov-athlete-card", className="mt-3"),
            html.Div([html.Span("How to read: ", className="fw-semibold"),
                      "Without a search the table lists the most decorated athletes in the current filters. "
                      "Click a row to open the athlete's full career."], className="how-to-read"),
        ]), className="chart-card"),
    ])


# ====================================================================== Q1.1 KPIs
def kpi_values(f: dict) -> dict:
    a = da.filter_athletes(f)
    e = da.filter_events(f)
    medals = e.dropna(subset=["medal"]).drop_duplicates(["result_id", "noc", "medal"])
    return {"athletes": a.athlete_id.nunique(), "countries": a.noc.nunique(), "sports": a.sport.nunique(),
            "events": e.result_id.nunique(), "medals": len(medals), "editions": a.edition_id.nunique()}


def previous_games_filters(f: dict) -> tuple[dict, str] | None:
    """If the filter covers exactly one Games, return filters for the previous
    Games of the same season (for 'change vs previous Games' on the tiles)."""
    a = da.filter_athletes(f)
    if a.edition_id.nunique() != 1:
        return None
    row = a.iloc[0]
    games = da.table("games")
    prev = games[(games.season == row.season) & (games.year < row.year)].sort_values("year")
    if prev.empty:
        return None
    py = int(prev.year.iloc[-1])
    return {**f, "years": [py, py], "season": row.season}, f"{py} {row.season}"


def _delta_text(now: int, before: int, label: str) -> str:
    if before == 0:
        return ""
    pct = (now - before) / before * 100
    arrow = "▲" if pct > 0 else ("▼" if pct < 0 else "=")
    return f"{arrow} {abs(pct):.0f}% vs {label}"


# ====================================================================== Q1.2 participation
def participation_data(f: dict, sport: str | None = None) -> pd.DataFrame:
    """Distinct athletes per Games x sex (an athlete in two sports counts once)."""
    a = da.filter_athletes(f)
    if sport:
        a = a[a.sport == sport]
    return (a.drop_duplicates(["athlete_id", "edition_id"])
             .groupby(["season", "year", "sex"], observed=True).size().rename("n").reset_index())


def _segments(years: list[int], gaps: list[int]) -> list[list[int]]:
    """Split Games years into uninterrupted runs, breaking at cancelled Games."""
    runs, cur = [], []
    for y in years:
        if cur and any(cur[-1] < g < y for g in gaps):
            runs.append(cur)
            cur = []
        cur.append(y)
    return runs + ([cur] if cur else [])


def fig_participation(f: dict, sport: str | None = None) -> go.Figure:
    d = participation_data(f, sport)
    if d.empty:
        return empty_figure()
    seasons = [s for s in ["Summer", "Winter"] if s in set(d.season)]
    fig = make_subplots(rows=1, cols=len(seasons), horizontal_spacing=0.08,
                        column_widths=[0.6, 0.4] if len(seasons) == 2 else None)
    for col, season in enumerate(seasons, start=1):
        s = d[d.season == season].pivot_table(index="year", columns="sex", values="n", fill_value=0)
        years = list(s.index)
        gaps = [y for y in CANCELLED[season] if years[0] < y < years[-1]]
        total = s.sum(axis=1).astype(float)
        # War gaps: a labelled gray band, and the area is broken there (not bridged, not dropped to 0)
        for y in gaps:
            fig.add_vrect(x0=y - 1.6, x1=y + 1.6, fillcolor="#efeeea", line_width=0, layer="below",
                          row=1, col=col)
        for war in dict.fromkeys(CANCELLED[season][y] for y in gaps):     # one label per war
            war_years = [y for y in gaps if CANCELLED[season][y] == war]
            fig.add_annotation(x=sum(war_years) / len(war_years), y=1,
                               yref=f"y{'' if col == 1 else col} domain", text=war,
                               showarrow=False, yanchor="top", font=dict(size=10, color=TEXT_MUTED),
                               row=1, col=col)
        for i, run in enumerate(_segments(years, gaps)):
            part = s.loc[run]
            for sex in ["Female", "Male"]:
                if sex not in part:
                    continue
                share = (part[sex].astype(float) / total.loc[run] * 100).round(1)
                fig.add_trace(go.Scatter(
                    # a lone Games has no area to fill, so it is drawn as markers
                    x=run, y=part[sex], name=SEX_LABEL[sex], stackgroup=f"{season}-{i}",
                    mode="lines" if len(run) > 1 else "lines+markers", marker=dict(size=10),
                    line=dict(width=1.2, color=SEX_COLORS[sex]), fillcolor=SEX_COLORS[sex],
                    legendgroup=sex, showlegend=(col == 1 and i == 0), customdata=share,
                    hovertemplate=f"<b>%{{x}} {season}</b><br>{SEX_LABEL[sex]}: %{{y:,}} "
                                  "(%{customdata}%)<extra></extra>"),
                    row=1, col=col)
        fig.add_annotation(x=0.02, y=0.97, xref=f"x{'' if col == 1 else col} domain",
                           yref=f"y{'' if col == 1 else col} domain", text=f"<b>{season}</b>",
                           showarrow=False, xanchor="left", yanchor="top",
                           font=dict(size=12, color=TEXT_SECONDARY))
    fig.update_yaxes(rangemode="tozero")
    fig.update_yaxes(title_text="Athletes", row=1, col=1)
    fig.update_xaxes(showgrid=False)
    fig.update_layout(hovermode="x unified", margin=dict(t=40, l=56),
                      legend=dict(y=1.08, x=0, traceorder="normal"))
    if sport:
        fig.update_layout(title=dict(text=f"Showing: <b>{sport}</b> (click the treemap's top bar to reset)",
                                     font=dict(size=12, color=TEXT_SECONDARY), x=1, xanchor="right", y=0.99))
    return fig


# ====================================================================== Q1.3 treemap
def treemap_frame(f: dict) -> pd.DataFrame:
    """Nodes for Season -> Sport -> Event, valued by athlete entries."""
    e = da.filter_events(f)
    leaf = e.groupby(["season", "sport", "event"], observed=True).size().rename("value").reset_index()
    if leaf.empty:
        return leaf
    sport = leaf.groupby(["season", "sport"], as_index=False).value.sum()
    season = leaf.groupby("season", as_index=False).value.sum()
    nodes = pd.concat([
        season.assign(id=season.season, label=season.season, parent="", level="season"),
        sport.assign(id=sport.season + "/" + sport.sport, label=sport.sport, parent=sport.season,
                     level="sport"),
        leaf.assign(id=leaf.season + "/" + leaf.sport + "/" + leaf.event,
                    label=leaf.event, parent=leaf.season + "/" + leaf.sport, level="event"),
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
        customdata=(n.value / total * 100).round(1),
        hovertemplate="<b>%{label}</b><br>%{value:,} athlete entries<br>%{customdata}% of all entries"
                      "<br>part of %{parent}<extra></extra>",
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


# ====================================================================== Q1.4 athlete search
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


def search_athletes(f: dict, query: str | None, limit: int = 500) -> tuple[list[dict], str]:
    a = da.filter_athletes(f)
    q = (query or "").strip()
    if q:
        a = a[_folded_names().loc[a.index].str.contains(_fold(q), regex=False)]
    if a.empty:
        return [], (f"No athlete named “{q}” in the current filters." if q else "No athletes match the filters.")
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
    if q:
        info = (f"1 athlete matches “{q}”" if n == 1 else f"{n:,} athletes match “{q}”") + " in the current filters."
    else:
        info = f"Most decorated of {n:,} athletes in the current filters (medals counted within the filters)."
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
        html.Div("Full career, regardless of the sidebar filters.", className="small text-secondary mb-2"),
        dbc.Table([html.Thead(html.Tr([html.Th("Games"), html.Th("Team"), html.Th("Sport"),
                                       html.Th("Events (medal)"), html.Th("Medals")])),
                   html.Tbody(rows)], size="sm", hover=True, responsive=True, className="mb-0"),
    ]), className="athlete-card")


# ====================================================================== callbacks
@tab_callback(TAB_ID, [Output(i, "children") for i, _ in KPIS]
          + [Output(f"{i}-delta", "children") for i, _ in KPIS]
          + [Output("kpi-context", "children")],
          Input("filters", "data"))
def update_kpis(f):
    v = kpi_values(f)
    keys = ["athletes", "countries", "sports", "events", "medals"]
    values = [f"{v[k]:,}" for k in keys]
    prev = previous_games_filters(f) if v["editions"] == 1 else None
    if prev:
        pv = kpi_values(prev[0])
        deltas = [_delta_text(v[k], pv[k], prev[1]) for k in keys]
    else:
        deltas = [""] * len(keys)
    lo, hi = f["years"]
    context = f"{v['editions']} Games · {lo}–{hi}" + ("" if f["season"] == "Both" else f" · {f['season']}")
    return values + deltas + [context]


@tab_callback(TAB_ID, Output("ov-participation", "figure"), Input("filters", "data"), Input("ov-treemap", "clickData"))
def update_participation(f, click):
    return fig_participation(f, sport_from_click(click))


@tab_callback(TAB_ID, Output("ov-treemap", "figure"), Input("filters", "data"))
def update_treemap(f):
    return fig_treemap(f)


@tab_callback(TAB_ID, Output("ov-athlete-table", "rowData"), Output("ov-athlete-table", "columnDefs"),
          Output("ov-search-info", "children"),
          Input("filters", "data"), Input("ov-search", "value"))
def update_athlete_table(f, query):
    rows, info = search_athletes(f, query)
    return rows, GRID_COLUMNS, info


@callback(Output("ov-athlete-card", "children"), Input("ov-athlete-table", "selectedRows"))
def show_athlete(selected):
    if not selected:
        return None
    return athlete_card(int(selected[0]["athlete_id"]))

"""Tab 3, Athlete Physiques: what body does each sport select for? (Q3.1-Q3.4)

Counting unit: height, weight and BMI barely change during a career, so each
athlete counts ONCE per sport (their latest Games in the filter). Age does
change, so for age every Games participation counts.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html
import dash_bootstrap_components as dbc

from .. import data_access as da
from ..components import chart_card, data_grid, data_note, segmented, tab_intro
from ..theme import (DEEMPHASIS, MEDAL_COLORS, SEX_COLORS, TEXT_MUTED, TEXT_SECONDARY, empty_figure,
                     tint)

TAB_ID = "physiques"
LABEL = "Physiques"

MEASURES = {"height_cm": "Height (cm)", "weight_kg": "Weight (kg)", "bmi": "BMI", "age": "Age (years)"}
UNITS = {"height_cm": "cm", "weight_kg": "kg", "bmi": "", "age": "years"}
SEX_LABEL = {"Female": "Women", "Male": "Men"}
MIN_N = 30                 # smallest group drawn as a box / violin
MIN_N_TREND = 8            # smallest Games sample drawn on the trend chart
DEFAULT_SPORT = "Basketball"


# ====================================================================== layout
def layout():
    controls = dbc.Row([
        dbc.Col([html.Span("Measure", className="small text-secondary me-2"),
                 segmented("ph-measure", list(MEASURES), "height_cm", MEASURES)],
                className="d-flex align-items-center", width="auto"),
        dbc.Col([html.Span("Focus sport", className="small text-secondary me-2"),
                 # options filled at build time: Dash 4 clears a value that is not among the options
                 dcc.Dropdown(id="ph-sport", value=DEFAULT_SPORT, clearable=False, style={"minWidth": 220},
                              options=sport_options(da.DEFAULT_FILTERS))],
                className="d-flex align-items-center", width="auto"),
    ], className="g-3 mb-2 align-items-center")
    return html.Div([
        tab_intro("What body does each sport select for?",
                  "Height, weight, BMI and age compared across sports, over time, and between medallists "
                  "and the rest of the field. Pick a measure, then click a sport in Q3.1 (or use the focus "
                  "sport menu) to drive Q3.2–Q3.4."),
        controls,
        chart_card("ph-boxes", "Q3.1", "How do body measures differ between sports, for women and men?",
                   "Box plots, ordered by median", "Distribution · Ranking",
                   "One row per sport, sorted by median; box = middle 50 % of athletes, line = median, "
                   "whiskers = typical range. n = athletes measured. Click a row to focus that sport.",
                   height=None),
        dbc.Row([
            dbc.Col(chart_card("ph-density", "Q3.2", "Where does a sport sit in the overall height × weight space?",
                               "2D density + overlay", "Correlation · Distribution",
                               "Gray contours = where all athletes are; coloured dots = the focus sport. Use "
                               "box or lasso select (toolbar) to list the athletes inside.",
                               height=460, selectable=True), lg=6),
            dbc.Col(chart_card("ph-trend", "Q3.3", "Have athletes in the focus sport changed over the decades?",
                               "Trend with interquartile band", "Change v Time (fan)",
                               "Line = median per Games, band = middle 50 %; dashed gray = all sports. "
                               "Games with fewer than 8 measured athletes are left out; hover shows n.",
                               height=460), lg=6),
        ], className="g-3 my-1"),
        dbc.Row([
            dbc.Col(chart_card("ph-violin", "Q3.4", "Do medallists differ physically from other competitors?",
                               "Split violin", "Distribution",
                               "Left (gold) half = athletes who won a medal at that Games; right (gray) half = "
                               "everyone else in the focus sport. Lines mark the medians.",
                               height=420), lg=6),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.Div([html.Div([html.Span("Selection", className="q-id"),
                                    html.Span("Athletes inside the box/lasso selection", className="q-text")]),
                          html.Span("Linked table", className="chart-name")], className="card-head"),
                html.Div(id="ph-selection-info", className="small text-secondary mb-2"),
                data_grid("ph-selection-table", page_size=10),
            ]), className="chart-card"), lg=6),
        ], className="g-3 my-1"),
        data_note("Height and weight are known for 93 % of athletes from 1960–2016, but for only 6–30 % before "
                  "1960 and 44 % at 2020/2022. Every chart reports how many athletes it is based on."),
    ])


# ====================================================================== data helper
def physique_frame(f: dict, measure: str) -> pd.DataFrame:
    """Rows with a known value of `measure`, at the right counting unit (see module doc)."""
    a = da.filter_athletes(f)
    if measure != "age":
        a = a.sort_values("year").drop_duplicates(["athlete_id", "sport"], keep="last")
    a = a.dropna(subset=[measure])
    return a.assign(value=a[measure].astype(float))


def sport_options(f: dict) -> list[dict]:
    a = da.filter_athletes(f)
    counts = a.dropna(subset=["height_cm"]).groupby("sport").athlete_id.nunique()
    return [{"label": f"{s} ({n:,} measured)", "value": s} for s, n in counts.sort_index().items() if n >= MIN_N]


# ====================================================================== Q3.1 boxes
def box_stats(f: dict, measure: str) -> pd.DataFrame:
    """Quartiles and Tukey whiskers per sport x sex (pre-computed: fast, no 100k points sent)."""
    d = physique_frame(f, measure)
    if d.empty:
        return pd.DataFrame(columns=["sport", "sex", "n", "q1", "median", "q3", "lo", "hi", "order"])

    def stats(v: pd.Series) -> pd.Series:
        q1, med, q3 = v.quantile([0.25, 0.5, 0.75])
        iqr = q3 - q1
        return pd.Series({"n": len(v), "q1": q1, "median": med, "q3": q3,
                          "lo": v[v >= q1 - 1.5 * iqr].min(), "hi": v[v <= q3 + 1.5 * iqr].max()})

    s = d.groupby(["sport", "sex"], observed=True).value.apply(stats).unstack().reset_index()
    s = s[s.n >= MIN_N]
    order = d[d.sport.isin(s.sport)].groupby("sport").value.median().sort_values()
    s["order"] = s.sport.map({sp: i for i, sp in enumerate(order.index)})
    return s.sort_values(["order", "sex"])


def fig_boxes(f: dict, measure: str, focus: str | None) -> go.Figure:
    s = box_stats(f, measure)
    if s.empty:
        return empty_figure("Too few measured athletes for these filters",
                            f"A box needs at least {MIN_N} athletes with a known value.")
    sports = list(dict.fromkeys(s.sort_values("order").sport))
    n_by_sport = s.groupby("sport").n.sum()
    ticktext = [(f"<b>{sp}</b>" if sp == focus else sp) + f"  <span style='color:{TEXT_MUTED}'>"
                f"n={int(n_by_sport[sp]):,}</span>" for sp in sports]
    fig = go.Figure()
    unit = UNITS[measure]
    for sex in ["Female", "Male"]:
        g = s[s.sex == sex]
        if g.empty:
            continue
        fig.add_trace(go.Box(
            y=g.sport, q1=g.q1, median=g["median"], q3=g.q3, lowerfence=g.lo, upperfence=g.hi,
            orientation="h", name=SEX_LABEL[sex], offsetgroup=sex, boxpoints=False,
            marker_color=SEX_COLORS[sex], fillcolor=tint(SEX_COLORS[sex], 0.55),
            line=dict(color=SEX_COLORS[sex], width=1.2), whiskerwidth=0.4,
            hoverinfo="x+y+name"))
    if focus in sports:
        fig.add_hrect(y0=sports.index(focus) - 0.5, y1=sports.index(focus) + 0.5, fillcolor="#eef4fc",
                      line_width=0, layer="below")
    fig.update_layout(boxmode="group", boxgroupgap=0.25, boxgap=0.15, height=max(360, 26 * len(sports) + 90),
                      margin=dict(l=10, t=70, r=20, b=40), hovermode="closest",
                      legend=dict(yref="container", y=0.995, yanchor="top", x=0, xanchor="left"))
    fig.update_yaxes(categoryorder="array", categoryarray=sports, tickvals=sports, ticktext=ticktext,
                     automargin=True, showgrid=False, tickfont=dict(size=11.5))
    # no axis title: the measure is named by the active button and the tick unit
    fig.update_xaxes(side="top", ticksuffix=f" {unit}" if unit else "")
    return fig


def sport_from_box_click(click) -> str | None:
    if not click or not click.get("points"):
        return None
    return click["points"][0].get("y")


# ====================================================================== Q3.2 density
SELECT_LAYER = 1     # trace index of the all-athletes layer in fig_density


def density_frame(f: dict) -> pd.DataFrame:
    """Row order is deterministic (stable sort + reset index): selections are resolved by
    position (pointIndex) in this frame, see selection_rows."""
    a = da.filter_athletes(f)
    a = a.sort_values(["year", "athlete_id"], kind="stable").drop_duplicates(["athlete_id", "sport"], keep="last")
    return a.dropna(subset=["height_cm", "weight_kg"]).reset_index(drop=True)


def fig_density(f: dict, focus: str | None) -> go.Figure:
    d = density_frame(f)
    if len(d) < MIN_N:
        return empty_figure("Too few athletes with height and weight")
    # Density grid computed here (1 cm x 1 kg bins, lightly smoothed) and sent as a small contour,
    # instead of shipping 100k raw points twice to the browser.
    xb = np.arange(np.floor(d.height_cm.min()) - 2, np.ceil(d.height_cm.max()) + 3, 2.0)
    yb = np.arange(np.floor(d.weight_kg.min()) - 2, np.ceil(d.weight_kg.max()) + 3, 2.0)
    h, _, _ = np.histogram2d(d.weight_kg, d.height_cm, bins=[yb, xb])
    k = np.array([1, 2, 1]) / 4
    h = np.apply_along_axis(lambda r: np.convolve(r, k, "same"), 0, h)
    h = np.apply_along_axis(lambda r: np.convolve(r, k, "same"), 1, h)
    fig = go.Figure()
    fig.add_trace(go.Contour(
        x=(xb[:-1] + xb[1:]) / 2, y=(yb[:-1] + yb[1:]) / 2, z=np.sqrt(h), ncontours=12, showscale=False,
        hoverinfo="skip", colorscale=[[0, "rgba(255,255,255,0)"], [0.12, "#ecebe7"], [1, "#9a9993"]],
        contours=dict(coloring="fill", showlines=True, start=0.6), line=dict(width=0.5, color="#c9c8c2")))
    # every athlete as a near-invisible point, so box/lasso selection can pick them up;
    # whole cm / kg as 16-bit integers keeps the payload small
    fig.add_trace(go.Scattergl(
        x=d.height_cm.round().astype("int16").to_numpy(), y=d.weight_kg.round().astype("int16").to_numpy(),
        mode="markers", name="All athletes", customdata=d.athlete_id.astype("int32").to_numpy(),
        marker=dict(size=4, color=DEEMPHASIS, opacity=0), hoverinfo="skip", showlegend=False,
        selected=dict(marker=dict(opacity=0)), unselected=dict(marker=dict(opacity=0))))
    sport = d[d.sport == focus]
    for sex in ["Female", "Male"]:
        g = sport[sport.sex == sex]
        if g.empty:
            continue
        fig.add_trace(go.Scattergl(
            x=g.height_cm, y=g.weight_kg, mode="markers", name=f"{focus}: {SEX_LABEL[sex]} (n={len(g):,})",
            customdata=g.athlete_id, text=g.name,
            marker=dict(size=5, color=SEX_COLORS[sex], opacity=0.55, line=dict(width=0)),
            hovertemplate="<b>%{text}</b><br>%{x:.0f} cm · %{y:.0f} kg<extra></extra>"))
    fig.update_xaxes(title_text="Height (cm)", range=[d.height_cm.quantile(0.001) - 3, d.height_cm.quantile(0.999) + 3])
    fig.update_yaxes(title_text="Weight (kg)", range=[d.weight_kg.quantile(0.001) - 3, d.weight_kg.quantile(0.999) + 5])
    fig.update_layout(dragmode="select", hovermode="closest", margin=dict(t=40),
                      legend=dict(y=1.0, yanchor="bottom", x=0, font=dict(size=11)),
                      title=dict(text=f"{len(d):,} athletes with height and weight", x=1, xanchor="right",
                                 y=0.99, font=dict(size=11, color=TEXT_MUTED)))
    return fig


_NUM = {"type": "numericColumn", "filter": False, "flex": 1}
SELECTION_COLUMNS = [      # sized for a half-width card
    {"field": "name", "headerName": "Athlete", "minWidth": 140, "flex": 3},
    {"field": "noc", "headerName": "Team", "minWidth": 66, "flex": 1, "filter": False},
    {"field": "sport", "headerName": "Sport", "minWidth": 110, "flex": 2},
    {"field": "year", "headerName": "Year", "minWidth": 66, **_NUM},
    {"field": "height_cm", "headerName": "cm", "minWidth": 58, **_NUM},
    {"field": "weight_kg", "headerName": "kg", "minWidth": 58, **_NUM},
    {"field": "n_medals", "headerName": "Medals", "minWidth": 76, **_NUM},
]


def selection_rows(f: dict, selected) -> tuple[list[dict], str]:
    if not selected or not selected.get("points"):
        return [], "Draw a box or lasso on Q3.2 to list the athletes inside it."
    # Dash drops customdata sent as a binary (typed) array, so points are resolved by their
    # position in the all-athletes layer, which is built from the same filters.
    d = density_frame(f)
    idx = [p["pointIndex"] for p in selected["points"]
           if p.get("curveNumber") == SELECT_LAYER and p.get("pointIndex") is not None
           and p["pointIndex"] < len(d)]
    d = d.iloc[sorted(set(idx))].sort_values("year").drop_duplicates("athlete_id", keep="last")
    if d.empty:
        return [], "No athletes in the selection."
    top = d.sport.value_counts().head(5)
    info = (f"{len(d):,} athletes selected · most common sports: "
            + ", ".join(f"{s} {n:,}" for s, n in top.items()))
    rows = d.sort_values(["n_medals", "height_cm"], ascending=False)[
        ["athlete_id", "name", "noc", "sport", "year", "height_cm", "weight_kg", "n_medals"]]
    return rows.head(1000).to_dict("records"), info


# ====================================================================== Q3.3 trend
def trend_stats(f: dict, measure: str, sport: str | None) -> pd.DataFrame:
    d = physique_frame(f, measure)
    if sport:
        d = d[d.sport == sport]
    g = (d.groupby(["year", "season", "sex"], observed=True).value
          .agg(n="size", median="median", q1=lambda v: v.quantile(0.25), q3=lambda v: v.quantile(0.75))
          .reset_index())
    return g[g.n >= MIN_N_TREND]


def fig_trend(f: dict, measure: str, focus: str | None) -> go.Figure:
    t = trend_stats(f, measure, focus)
    if t.empty:
        return empty_figure(f"Too few measured athletes in {focus}" if focus else "No data")
    # reference = all sports of the same season only (Summer and Winter alternated before 1994)
    ref = trend_stats({**f, "season": t.season.mode().iat[0]}, measure, None)
    fig = go.Figure()
    unit = UNITS[measure]
    for sex in ["Female", "Male"]:
        g = t[t.sex == sex].sort_values("year")
        r = ref[ref.sex == sex].sort_values("year")
        if g.empty:
            continue
        color = SEX_COLORS[sex]
        fig.add_trace(go.Scatter(x=r.year, y=r["median"], mode="lines", name=f"All sports: {SEX_LABEL[sex]}",
                                 line=dict(color=tint(color, 0.35), width=1.2, dash="dash"),
                                 hovertemplate=f"All sports, {SEX_LABEL[sex].lower()}: %{{y:.1f}} {unit}<extra></extra>",
                                 legendgroup=sex, showlegend=False))
        fig.add_trace(go.Scatter(x=list(g.year) + list(g.year[::-1]), y=list(g.q3) + list(g.q1[::-1]),
                                 fill="toself", fillcolor=tint(color, 0.75), line=dict(width=0),
                                 hoverinfo="skip", showlegend=False, legendgroup=sex))
        fig.add_trace(go.Scatter(
            x=g.year, y=g["median"], mode="lines+markers", name=SEX_LABEL[sex], legendgroup=sex,
            line=dict(color=color, width=2.2), marker=dict(size=6, color=color),
            customdata=np.stack([g.n, g.q1, g.q3], axis=1),
            hovertemplate=f"<b>%{{x}} · {SEX_LABEL[sex]}</b><br>median %{{y:.1f}} {unit}<br>"
                          f"middle 50 %: %{{customdata[1]:.1f}}–%{{customdata[2]:.1f}}<br>n = %{{customdata[0]}}<extra></extra>"))
    fig.update_yaxes(title_text=MEASURES[measure])
    fig.update_layout(hovermode="closest", margin=dict(t=40),
                      legend=dict(y=1.0, yanchor="bottom", x=0),
                      title=dict(text=f"{focus} · dashed = all sports", x=1, xanchor="right", y=0.99,
                                 font=dict(size=11, color=TEXT_MUTED)))
    return fig


# ====================================================================== Q3.4 split violin
def fig_violin(f: dict, measure: str, focus: str | None) -> go.Figure:
    d = physique_frame(f, measure)
    d = d[d.sport == focus]
    if len(d) < MIN_N:
        return empty_figure(f"Too few measured athletes in {focus}")
    fig = go.Figure()
    unit = UNITS[measure]
    sexes = [s for s in ["Female", "Male"] if (d.sex == s).sum() >= MIN_N]
    for is_med, side, color, label in [(True, "negative", MEDAL_COLORS["Gold"], "Medallists"),
                                       (False, "positive", DEEMPHASIS, "Everyone else")]:
        g = d[(d.is_medalist == is_med) & d.sex.isin(sexes)]
        if g.empty:
            continue
        fig.add_trace(go.Violin(
            x=g.sex.map(SEX_LABEL), y=g.value, side=side, name=label, legendgroup=label,
            line=dict(color=color, width=1.2), fillcolor=tint(color, 0.45), meanline=dict(visible=False),
            box=dict(visible=False), points=False, spanmode="hard", scalemode="width", width=0.9,
            hoveron="kde", hoverinfo="skip"))
        for sex in sexes:          # median markers + n, as hoverable points
            v = g[g.sex == sex].value
            if len(v):
                fig.add_trace(go.Scatter(
                    x=[SEX_LABEL[sex]], y=[v.median()], mode="markers", showlegend=False,
                    marker=dict(symbol="line-ew-open", size=26, color=color, line=dict(width=2.5)),
                    hovertemplate=f"<b>{label}, {SEX_LABEL[sex].lower()}</b><br>median %{{y:.1f}} {unit}"
                                  f"<br>n = {len(v):,}<extra></extra>"))
    fig.update_layout(violinmode="overlay", violingap=0.25, hovermode="closest", margin=dict(t=40),
                      legend=dict(y=1.0, yanchor="bottom", x=0),
                      title=dict(text=focus, x=1, xanchor="right", y=0.99, font=dict(size=11, color=TEXT_MUTED)))
    fig.update_yaxes(title_text=MEASURES[measure])
    fig.update_xaxes(showgrid=False)
    return fig


# ====================================================================== callbacks
@callback(Output("ph-sport", "options"), Output("ph-sport", "value"),
          Input("filters", "data"), Input("ph-boxes", "clickData"), State("ph-sport", "value"))
def update_focus_sport(f, click, current):
    """Focus sport: set by clicking a box row, or by the menu; kept valid when filters change."""
    options = sport_options(f)
    valid = [o["value"] for o in options]
    clicked = sport_from_box_click(click)
    if clicked in valid and clicked != current:
        return options, clicked
    if current in valid:
        return options, current          # sent back explicitly, never left to the component
    preferred = [s for s in (f["sports"] or []) if s in valid]
    return options, (preferred[0] if preferred else (DEFAULT_SPORT if DEFAULT_SPORT in valid else
                                                     (valid[0] if valid else None)))


@callback(Output("ph-boxes", "figure"), Input("filters", "data"), Input("ph-measure", "value"),
          Input("ph-sport", "value"))
def update_boxes(f, measure, sport):
    return fig_boxes(f, measure, sport)


@callback(Output("ph-density", "figure"), Input("filters", "data"), Input("ph-sport", "value"))
def update_density(f, sport):
    return fig_density(f, sport)


@callback(Output("ph-trend", "figure"), Input("filters", "data"), Input("ph-measure", "value"),
          Input("ph-sport", "value"))
def update_trend(f, measure, sport):
    return fig_trend(f, measure, sport)


@callback(Output("ph-violin", "figure"), Input("filters", "data"), Input("ph-measure", "value"),
          Input("ph-sport", "value"))
def update_violin(f, measure, sport):
    return fig_violin(f, measure, sport)


@callback(Output("ph-selection-table", "rowData"), Output("ph-selection-table", "columnDefs"),
          Output("ph-selection-info", "children"),
          Input("ph-density", "selectedData"), State("filters", "data"))
def update_selection(selected, f):
    rows, info = selection_rows(f, selected)
    return rows, SELECTION_COLUMNS, info

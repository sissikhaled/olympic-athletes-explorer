"""Tab 3, Athlete Physiques. Q3: how do athletes' bodies differ between sports, how have they changed, and do medallists stand out?

Counting unit: height, weight and BMI barely change during a career, so each
athlete counts ONCE per sport (their latest Games in the filter). Age does
change, so for age every Games participation counts.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html
import dash_bootstrap_components as dbc

from .. import data_access as da
from ..components import tab_callback, chart_card, data_note, segmented, tab_intro
from ..theme import DEEMPHASIS, MEDAL_COLORS, SEX_COLORS, TEXT_MUTED, empty_figure, tint

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
        tab_intro("How do athletes' bodies differ between sports, how have they changed, and do medallists "
                  "stand out?",
                  "Pick a measure and a focus sport; all three charts follow. The trend shows how the sport's "
                  "athletes changed over the decades, the cloud places them among all Olympians, and the violin "
                  "compares medallists with the rest of the field.", qid="Q3"),
        controls,
        chart_card("ph-trend", "Focus sport over the decades",
                   "Trend with interquartile band", "Change v Time (fan)",
                   "Line = median per Games, band = middle 50 % of athletes; dashed = all sports of the same "
                   "season. Games with fewer than 8 measured athletes are left out; hover shows n.",
                   height=440),
        dbc.Row([
            dbc.Col(chart_card("ph-density", "Focus sport among all Olympians (height × weight)",
                               "2D density + overlay", "Correlation · Distribution",
                               "Gray contours = where all athletes are in height × weight; coloured dots = the "
                               "focus sport's athletes (hover for names).",
                               height=460), lg=7),
            dbc.Col(chart_card("ph-violin", "Medallists vs the rest of the field",
                               "Split violin", "Distribution",
                               "Left (gold) half = athletes who won a medal at that Games; right (gray) half = "
                               "everyone else in the focus sport. Lines mark the medians.",
                               height=460), lg=5),
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


# ====================================================================== density (all Olympians)
def density_frame(f: dict) -> pd.DataFrame:
    """One row per athlete per sport (latest Games) with both height and weight."""
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
    fig.update_layout(hovermode="closest", margin=dict(t=40),
                      legend=dict(y=1.0, yanchor="bottom", x=0, font=dict(size=11)),
                      title=dict(text=f"{len(d):,} athletes with height and weight", x=1, xanchor="right",
                                 y=0.99, font=dict(size=11, color=TEXT_MUTED)))
    return fig


# ====================================================================== trend over the decades
def trend_stats(f: dict, measure: str, sport: str | None) -> pd.DataFrame:
    d = physique_frame(f, measure)
    if sport:
        d = d[d.sport == sport]
    g = (d.groupby(["year", "season", "sex"], observed=True).value
          .agg(n="size", median="median", q1=lambda v: v.quantile(0.25), q3=lambda v: v.quantile(0.75))
          .reset_index())
    return g[g.n >= MIN_N_TREND]


def fig_trend(f: dict, measure: str, focus: str | None) -> go.Figure:
    if not focus:
        return empty_figure("No sport to focus on",
                            f"No sport has {MIN_N}+ measured athletes in this selection.")
    t = trend_stats(f, measure, focus)
    if t.empty:
        return empty_figure(f"Too few measured athletes in {focus}",
                            f"Each Games needs {MIN_N_TREND}+ athletes with a known value.")
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


# ====================================================================== split violin (medallists)
def fig_violin(f: dict, measure: str, focus: str | None) -> go.Figure:
    if not focus:
        return empty_figure("No sport to focus on",
                            f"No sport has {MIN_N}+ measured athletes in this selection.")
    d = physique_frame(f, measure)
    d = d[d.sport == focus]
    if len(d) < MIN_N:
        return empty_figure(f"Too few measured athletes in {focus}",
                            f"A violin needs {MIN_N}+ athletes with a known value.")
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
@tab_callback(TAB_ID, Output("ph-sport", "options"), Output("ph-sport", "value"),
          Input("filters", "data"), State("ph-sport", "value"))
def update_focus_sport(f, current):
    """Focus sport: chosen in the menu; kept valid when the filters change."""
    options = sport_options(f)
    valid = [o["value"] for o in options]
    if current in valid:
        return options, current          # sent back explicitly, never left to the component
    preferred = [s for s in (f["sports"] or []) if s in valid]
    return options, (preferred[0] if preferred else (DEFAULT_SPORT if DEFAULT_SPORT in valid else
                                                     (valid[0] if valid else None)))


@tab_callback(TAB_ID, Output("ph-density", "figure"), Input("filters", "data"), Input("ph-sport", "value"))
def update_density(f, sport):
    return fig_density(f, sport)


@tab_callback(TAB_ID, Output("ph-trend", "figure"), Input("filters", "data"), Input("ph-measure", "value"),
          Input("ph-sport", "value"))
def update_trend(f, measure, sport):
    return fig_trend(f, measure, sport)


@tab_callback(TAB_ID, Output("ph-violin", "figure"), Input("filters", "data"), Input("ph-measure", "value"),
          Input("ph-sport", "value"))
def update_violin(f, measure, sport):
    return fig_violin(f, measure, sport)

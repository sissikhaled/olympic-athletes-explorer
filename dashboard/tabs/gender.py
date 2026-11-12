"""Tab 4, Gender Participation: how did women enter the Games? (Q4.1-Q4.4)

The sidebar's Sex filter is ignored here (this tab compares the sexes); all
other filters apply. Counts are distinct athletes who started at least one
event (decision D16).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, ctx, dcc, html
import dash_bootstrap_components as dbc

from .. import data_access as da
from ..components import chart_card, data_note, tab_intro
from ..theme import (SEASON_COLORS, SELECTION_COLORS, SEX_COLORS, TEXT_MUTED, TEXT_PRIMARY,
                     TEXT_SECONDARY, empty_figure)

TAB_ID = "gender"
LABEL = "Gender"
IGNORE = ("sex",)
SEX_LABEL = {"Female": "Women", "Male": "Men"}
TOP_COUNTRIES = 25
MIN_CELL = 10             # heatmap cells with fewer athletes are left blank
AGE_MIN, AGE_MAX = 12, 50  # pyramid range; older ages pooled into "50+"

# Milestones verified against the data (Phase 5d): (season, year, label)
MILESTONES = [
    ("Summer", 1900, "1900: first women compete"),
    ("Summer", 1928, "1928: women's athletics debuts"),
    ("Summer", 1976, "1976: women pass 20 %"),
    ("Summer", 2004, "2004: women pass 40 %"),
    ("Summer", 2012, "2012: women's boxing; every sport<br>on the programme includes women"),
    ("Winter", 1924, "1924: first women (figure skating)"),
    ("Winter", 2014, "2014: women's ski jumping"),
]
# label offsets (pixels) where default placement would collide
LABEL_OFFSETS = {("Summer", 2004): (-95, -14), ("Summer", 2012): (-40, -58), ("Winter", 2014): (10, 40)}
# female share 0 % = men only (aqua) ... 50 % = parity (gray) ... 100 % = women only (violet)
SHARE_SCALE = [[0.0, SEX_COLORS["Male"]], [0.5, "#ecebe7"], [1.0, SEX_COLORS["Female"]]]


# ====================================================================== layout
def layout():
    return html.Div([
        dcc.Store(id="ge-sport"),
        tab_intro("How did women enter the Games?",
                  "From the first women in 1900 (2 % of athletes) to 48 % in 2020: the overall trend, the sports "
                  "and countries behind it, and the age structure of women and men. The sidebar's Sex filter "
                  "does not apply here, because this tab compares the sexes."),
        html.Div([html.Span("Following sport: ", className="small text-secondary"),
                  html.Span("none: click a sport in Q4.2", id="ge-sport-label", className="small fw-semibold me-2"),
                  dbc.Button("Clear", id="ge-sport-clear", size="sm", color="link", className="p-0 align-baseline")],
                 className="mb-2"),
        chart_card("ge-share", "Q4.1", "How did women's share of athletes evolve?",
                   "Annotated line", "Change v Time",
                   "Share of women among all athletes at each Games, Summer and Winter. Dashed line = parity "
                   "(50 %). Labels mark milestones. A sport clicked in Q4.2 is added as a third line.",
                   height=420),
        chart_card("ge-heatmap", "Q4.2", "Which sports opened to women early or late, and which remain unbalanced?",
                   "XY-heatmap, diverging scale", "Correlation · Deviation",
                   "Each cell = one sport in one decade. Violet = mostly women, aqua = mostly men, gray = "
                   "balanced; blank = not held (or under 10 athletes). Sports are ordered by the decade women "
                   "first took part. Click a cell to follow that sport.", height=None),
        dbc.Row([
            dbc.Col(chart_card("ge-spine", "Q4.3", "Which countries send balanced teams?",
                               "Spine chart", "Deviation",
                               "Each row is one country's athletes: women extend left from the centre line, men "
                               "right. A balanced team reaches the dashed 50 % mark on both sides. 25 largest "
                               "teams in the selection, most unbalanced at the top.",
                               height=640), lg=6),
            dbc.Col(chart_card("ge-pyramid", "Q4.4", "Do female and male Olympians differ in age structure?",
                               "Population pyramid", "Distribution",
                               "Women to the left, men to the right; each bar is one year of age as % of that sex "
                               "(each Games counted). Lines mark the median ages.", height=640), lg=6),
        ], className="g-3 my-1"),
        data_note("Counts are distinct athletes who started at least one event; an athlete in two sports counts "
                  "once in totals and once in each sport."),
    ])


# ====================================================================== Q4.1 share line
def share_by_games(f: dict, sport: str | None = None) -> pd.DataFrame:
    a = da.filter_athletes(f, ignore=IGNORE)
    if sport:
        a = a[a.sport == sport]
    u = a.drop_duplicates(["athlete_id", "edition_id"])
    g = (u.groupby(["season", "year"]).agg(n=("athlete_id", "size"), women=("is_female", "sum"))
          .reset_index())
    g["share"] = g.women / g.n * 100
    return g


def fig_share(f: dict, sport: str | None = None) -> go.Figure:
    g = share_by_games(f)
    if g.empty:
        return empty_figure()
    fig = go.Figure()
    fig.add_hline(y=50, line=dict(color=TEXT_MUTED, dash="dash", width=1))
    fig.add_annotation(x=1, xref="paper", y=50, text="parity", showarrow=False, xanchor="right", yshift=8,
                       font=dict(size=10, color=TEXT_MUTED))
    for season in ["Summer", "Winter"]:
        s = g[g.season == season].sort_values("year")
        if s.empty:
            continue
        fig.add_trace(go.Scatter(
            x=s.year, y=s.share, name=season, mode="lines+markers",
            line=dict(color=SEASON_COLORS[season], width=2.4), marker=dict(size=6),
            customdata=np.stack([s.women, s.n], axis=1),
            hovertemplate=f"<b>%{{x}} {season}</b><br>%{{y:.1f}} % women<br>"
                          "%{customdata[0]:,} of %{customdata[1]:,} athletes<extra></extra>"))
        years = set(s.year)
        for ms, my, label in MILESTONES:
            if ms == season and my in years:
                y = float(s.loc[s.year == my, "share"].iloc[0])
                ax, ay = LABEL_OFFSETS.get((season, my), (0, -38 if season == "Summer" else 34))
                fig.add_annotation(x=my, y=y, text=label, showarrow=True, arrowhead=0, arrowwidth=1,
                                   arrowcolor=TEXT_MUTED, ax=ax, ay=ay, align="left",
                                   font=dict(size=10, color=TEXT_SECONDARY), bgcolor="rgba(252,252,251,0.85)")
    if sport:
        sp = share_by_games(f, sport).sort_values("year")
        if len(sp):
            fig.add_trace(go.Scatter(
                x=sp.year, y=sp.share, name=sport, mode="lines+markers",
                line=dict(color=SELECTION_COLORS[3], width=2, dash="dot"), marker=dict(size=5),
                customdata=np.stack([sp.women, sp.n], axis=1),
                hovertemplate=f"<b>%{{x}} · {sport}</b><br>%{{y:.1f}} % women<br>"
                              "%{customdata[0]:,} of %{customdata[1]:,} athletes<extra></extra>"))
    fig.update_yaxes(title_text="Women (% of athletes)", range=[0, 62], ticksuffix=" %")
    fig.update_layout(hovermode="closest", margin=dict(t=40),
                      legend=dict(y=1.0, yanchor="bottom", x=0))
    return fig


# ====================================================================== Q4.2 heatmap
def heatmap_data(f: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """female share %, women count, total count per sport x decade."""
    a = da.filter_athletes(f, ignore=IGNORE)
    u = a.drop_duplicates(["athlete_id", "edition_id", "sport"])
    g = u.groupby(["sport", "decade"]).agg(n=("athlete_id", "size"), women=("is_female", "sum")).reset_index()
    if g.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    n = g.pivot(index="sport", columns="decade", values="n")
    w = g.pivot(index="sport", columns="decade", values="women")
    share = (w / n * 100).where(n >= MIN_CELL)
    share = share.dropna(how="all")
    if share.empty:
        return share, share, share
    # order: decade women first took part (women-only-never last), then current share
    first = (w.loc[share.index] > 0).idxmax(axis=1).where((w.loc[share.index] > 0).any(axis=1), 9999)
    latest = share.ffill(axis=1).iloc[:, -1]
    order = pd.DataFrame({"first": first, "latest": -latest}).sort_values(["first", "latest"]).index
    return share.loc[order], w.loc[order, share.columns], n.loc[order, share.columns]


def fig_heatmap(f: dict, sport: str | None = None) -> go.Figure:
    share, w, n = heatmap_data(f)
    if share.empty:
        return empty_figure()
    labels = [f"{d}s" for d in share.columns]
    ylabels = [f"<b>{s}</b>" if s == sport else s for s in share.index]
    custom = np.dstack([w.fillna(0).values, n.fillna(0).values,
                        np.broadcast_to(np.array(share.index)[:, None], share.shape)])
    fig = go.Figure(go.Heatmap(
        z=share.values, x=labels, y=ylabels, zmin=0, zmax=100, colorscale=SHARE_SCALE, xgap=1, ygap=1,
        customdata=custom, hoverongaps=False,
        colorbar=dict(title=dict(text="women", font=dict(size=11)), ticksuffix=" %", thickness=12,
                      tickvals=[0, 25, 50, 75, 100], lenmode="pixels", len=220, y=1, yanchor="top"),
        hovertemplate="<b>%{customdata[2]}</b> · %{x}<br>%{z:.0f} % women<br>"
                      "%{customdata[0]:,} women of %{customdata[1]:,} athletes<extra></extra>"))
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(size=11), automargin=True)
    fig.update_xaxes(side="top", showgrid=False)
    fig.update_layout(height=max(360, 17 * len(share) + 90), margin=dict(t=50, l=10, r=10, b=10),
                      plot_bgcolor="#f5f4f1")
    return fig


def sport_from_heat_click(click) -> str | None:
    if not click or not click.get("points"):
        return None
    cd = click["points"][0].get("customdata")
    if isinstance(cd, list) and len(cd) >= 3:
        return cd[2]
    y = click["points"][0].get("y", "")
    return y.replace("<b>", "").replace("</b>", "") or None


# ====================================================================== Q4.3 spine chart
def spine_data(f: dict) -> pd.DataFrame:
    a = da.filter_athletes(f, ignore=IGNORE)
    u = a.drop_duplicates(["athlete_id", "noc"])
    g = u.groupby("noc").agg(n=("athlete_id", "size"), women=("is_female", "sum")).reset_index()
    g = g.nlargest(TOP_COUNTRIES, "n")
    g["women_pct"] = g.women / g.n * 100
    g["men_pct"] = 100 - g.women_pct
    names = da.table("countries").set_index("noc").country
    g["country"] = g.noc.map(names).fillna(g.noc)
    return g.sort_values("women_pct", key=lambda s: (s - 50).abs(), ascending=False)


def fig_spine(f: dict) -> go.Figure:
    g = spine_data(f)
    if g.empty:
        return empty_figure()
    labels = [f"{c if len(c) <= 20 else c[:18].rstrip() + '…'} ({n})" for c, n in zip(g.country, g.noc)]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=labels, x=-g.women_pct, orientation="h", name="Women",
                         marker=dict(color=SEX_COLORS["Female"]), customdata=np.stack([g.women, g.n], axis=1),
                         text=[f"{v:.0f}%" for v in g.women_pct], textposition="inside", insidetextanchor="start",
                         textfont=dict(color="white", size=10),
                         hovertemplate="<b>%{y}</b><br>Women: %{customdata[0]:,} of %{customdata[1]:,} "
                                       "(%{text})<extra></extra>"))
    fig.add_trace(go.Bar(y=labels, x=g.men_pct, orientation="h", name="Men",
                         marker=dict(color=SEX_COLORS["Male"]), customdata=np.stack([g.n - g.women, g.n], axis=1),
                         text=[f"{v:.0f}%" for v in g.men_pct], textposition="inside", insidetextanchor="end",
                         textfont=dict(color=TEXT_PRIMARY, size=10),
                         hovertemplate="<b>%{y}</b><br>Men: %{customdata[0]:,} of %{customdata[1]:,} "
                                       "(%{text})<extra></extra>"))
    for x in (-50, 50):
        fig.add_vline(x=x, line=dict(color=TEXT_MUTED, dash="dash", width=1))
    fig.add_vline(x=0, line=dict(color="white", width=2))
    fig.update_layout(barmode="relative", bargap=0.25, hovermode="closest", margin=dict(t=40),
                      legend=dict(y=1.0, yanchor="bottom", x=0))
    fig.update_xaxes(range=[-100, 100], tickvals=[-100, -50, 0, 50, 100],
                     ticktext=["100 %", "50 %", "0", "50 %", "100 %"], showgrid=False)
    fig.update_yaxes(autorange="reversed", automargin=True, tickfont=dict(size=11))
    return fig


# ====================================================================== Q4.4 pyramid
def pyramid_data(f: dict, sport: str | None = None) -> pd.DataFrame:
    a = da.filter_athletes(f, ignore=IGNORE)
    if sport:
        a = a[a.sport == sport]
    a = a.drop_duplicates(["athlete_id", "edition_id"]).dropna(subset=["age"])
    age = a.age.astype(float).clip(lower=AGE_MIN, upper=AGE_MAX).astype(int)
    t = pd.crosstab(age, a.sex)
    pct = t / t.sum() * 100
    pct.attrs["median"] = a.groupby("sex").age.median().astype(float).to_dict()
    pct.attrs["n"] = t.sum().to_dict()
    return pct


def fig_pyramid(f: dict, sport: str | None = None) -> go.Figure:
    p = pyramid_data(f, sport)
    if p.empty or len(p.columns) < 1:
        return empty_figure()
    ages = p.index.tolist()
    labels = [f"{a}+" if a == AGE_MAX else (f"≤{a}" if a == AGE_MIN else str(a)) for a in ages]
    fig = go.Figure()
    for sex, sign in [("Female", -1), ("Male", 1)]:
        if sex not in p:
            continue
        fig.add_trace(go.Bar(
            y=ages, x=sign * p[sex], orientation="h", name=f"{SEX_LABEL[sex]} (n={p.attrs['n'][sex]:,})",
            marker=dict(color=SEX_COLORS[sex]), customdata=np.stack([p[sex], labels], axis=1),
            hovertemplate=f"<b>{SEX_LABEL[sex]}, age %{{customdata[1]}}</b><br>%{{customdata[0]:.1f}} % of "
                          f"{SEX_LABEL[sex].lower()}<extra></extra>"))
        med = p.attrs["median"].get(sex)
        if med is not None:
            fig.add_hline(y=med, line=dict(color=SEX_COLORS[sex], width=1.5, dash="dot"))
            fig.add_annotation(x=0.01 if sign < 0 else 0.99, xref="x domain", y=med,
                               text=f"median {med:.0f}", showarrow=False, yshift=8,
                               xanchor="left" if sign < 0 else "right",
                               font=dict(size=10, color=SEX_COLORS[sex]))
    m = float(np.nanmax(p.values)) * 1.1
    fig.update_layout(barmode="relative", bargap=0.08, hovermode="closest", margin=dict(t=40),
                      legend=dict(y=1.0, yanchor="bottom", x=0),
                      title=dict(text=sport or "", x=1, xanchor="right", y=0.99,
                                 font=dict(size=11, color=TEXT_MUTED)))
    ticks = list(range(-int(m) // 2 * 2, int(m) + 1, 2))           # every 2 %, shown without sign
    fig.update_xaxes(range=[-m, m], tickvals=ticks, ticktext=[f"{abs(v)} %" if v else "0" for v in ticks],
                     showgrid=False)
    fig.update_yaxes(title_text="Age at the Games", tickvals=list(range(15, AGE_MAX + 1, 5)),
                     ticktext=[str(v) if v < AGE_MAX else f"{v}+" for v in range(15, AGE_MAX + 1, 5)])
    return fig


# ====================================================================== callbacks
@callback(Output("ge-sport", "data"), Output("ge-sport-label", "children"),
          Input("ge-heatmap", "clickData"), Input("ge-sport-clear", "n_clicks"), State("ge-sport", "data"),
          prevent_initial_call=True)
def follow_sport(click, _clear, current):
    """Click a heatmap cell to follow its sport; click it again (or Clear) to stop."""
    if ctx.triggered_id == "ge-sport-clear":
        return None, "none: click a sport in Q4.2"
    sport = sport_from_heat_click(click)
    if not sport or sport == current:
        return None, "none: click a sport in Q4.2"
    return sport, sport


@callback(Output("ge-share", "figure"), Input("filters", "data"), Input("ge-sport", "data"))
def update_share(f, sport):
    return fig_share(f, sport)


@callback(Output("ge-heatmap", "figure"), Input("filters", "data"), Input("ge-sport", "data"))
def update_heatmap(f, sport):
    return fig_heatmap(f, sport)


@callback(Output("ge-spine", "figure"), Input("filters", "data"))
def update_spine(f):
    return fig_spine(f)


@callback(Output("ge-pyramid", "figure"), Input("filters", "data"), Input("ge-sport", "data"))
def update_pyramid(f, sport):
    return fig_pyramid(f, sport)

"""Tab 4, Gender Participation: how did women enter the Games? (Q4.1-Q4.3)

The Sex filter is ignored here (this tab compares the sexes); all
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
from ..components import tab_callback, chart_card, data_note, tab_intro
from ..theme import (SEASON_COLORS, SELECTION_COLORS, SEX_COLORS, TEXT_MUTED, TEXT_PRIMARY,
                     TEXT_SECONDARY, empty_figure)

TAB_ID = "gender"
LABEL = "Gender"
IGNORE = ("sex",)
SEX_LABEL = {"Female": "Women", "Male": "Men"}
TOP_COUNTRIES = 25
MEN_YEARS = "#c9c8c2"     # timeline: years a sport was held for men only

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


# ====================================================================== layout
NO_SPORT = "none: click a sport in Q4.2"


def layout():
    return html.Div([
        dcc.Store(id="ge-sport"),
        tab_intro("How did women enter the Games?",
                  "From the first women in 1900 (2 % of athletes) to 48 % in 2020: the overall trend, when each "
                  "sport opened to women, and which countries send balanced teams. The Sex filter does not "
                  "apply here, because this tab compares the sexes."),
        html.Div([html.Span("Following sport: ", className="small text-secondary"),
                  html.Span(NO_SPORT, id="ge-sport-label", className="small fw-semibold me-2"),
                  dbc.Button("Clear", id="ge-sport-clear", size="sm", color="link", className="p-0 align-baseline")],
                 className="mb-2"),
        chart_card("ge-share", "Q4.1", "How did women's share of athletes evolve?",
                   "Annotated line", "Change v Time",
                   "Share of women among all athletes at each Games, Summer and Winter. Dashed line = parity "
                   "(50 %). Labels mark milestones. A sport clicked in Q4.2 is added as a dotted line.",
                   height=420),
        dbc.Row([
            dbc.Col(chart_card("ge-timeline", "Q4.2", "When did each sport open to women, and how balanced is it now?",
                               "Timeline (Priestley)", "Change v Time",
                               "Each row is a sport, from its first to its latest Games: gray = men only, violet = "
                               "women also compete. The dot marks the first Games with women; the number is the "
                               "share of women at the latest Games. Click a sport to follow it in Q4.1.",
                               height=None), lg=7),
            dbc.Col(chart_card("ge-spine", "Q4.3", "Which countries send balanced teams?",
                               "Spine chart", "Deviation",
                               "Each row is one country's athletes: women extend left from the centre line, men "
                               "right. A balanced team reaches the dashed 50 % mark on both sides. 25 largest "
                               "teams in the selection, most unbalanced at the top.",
                               height=700), lg=5),
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


# ====================================================================== Q4.2 timeline
def timeline_data(f: dict) -> pd.DataFrame:
    """One row per sport: first and latest Games, first Games with women, share of women at the latest Games."""
    a = da.filter_athletes(f, ignore=IGNORE)
    if a.empty:
        return pd.DataFrame()
    u = a.drop_duplicates(["athlete_id", "edition_id", "sport"])
    g = (u.groupby(["sport", "season", "year"]).agg(n=("athlete_id", "size"), women=("is_female", "sum"))
          .reset_index())
    # only sports still held at the end of the period (within the last two Games of their season):
    # long-gone sports such as tug-of-war add rows but say nothing about women's entry
    games = g.drop_duplicates(["season", "year"]).sort_values("year")
    cutoff = games.groupby("season").year.apply(lambda y: y.iloc[-2] if len(y) > 1 else y.iloc[-1])
    rows, dropped = [], 0
    for sport, d in g.groupby("sport"):
        d = d.sort_values("year")
        if d.year.iloc[-1] < cutoff[d.season.iloc[-1]]:
            dropped += 1
            continue
        with_women = d[d.women > 0]
        last = d.iloc[-1]
        rows.append({"sport": sport, "first": int(d.year.iloc[0]), "last": int(last.year),
                     "women_from": int(with_women.year.iloc[0]) if len(with_women) else None,
                     "share_now": last.women / last.n * 100, "n_now": int(last.n), "women_now": int(last.women),
                     "women_only": bool((d.women == d.n).all())})
    t = pd.DataFrame(rows)
    if t.empty:
        return t
    t.attrs["dropped"] = dropped
    # order: when women first took part (never = last), then current share
    t["order_key"] = t.women_from.fillna(9999)
    out = t.sort_values(["order_key", "share_now"], ascending=[True, False]).drop(columns="order_key")
    out.attrs["dropped"] = dropped
    return out.reset_index(drop=True)


def _status(r) -> str:
    if r.women_only:
        return "women only"
    if r.women_from is None or pd.isna(r.women_from):
        return "men only"
    return f"{r.share_now:.0f} %"


def fig_timeline(f: dict, sport: str | None = None) -> go.Figure:
    t = timeline_data(f)
    if t.empty:
        return empty_figure()
    has_women = t.women_from.notna()
    wf = t.women_from.where(has_women, t["last"]).astype(int)
    labels = [f"<b>{s}</b>" if s == sport else s for s in t.sport]
    gx, gy, vx, vy = [], [], [], []
    for lab, first, last, w, ok in zip(labels, t["first"], t["last"], wf, has_women):
        if w > first:                              # men-only years (the whole line if never with women)
            gx += [first, w, None]
            gy += [lab, lab, None]
        if ok:                                     # years with women
            vx += [w, max(last, w + 0.5), None]    # a sport with one Games still gets a visible stub
            vy += [lab, lab, None]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=gx, y=gy, mode="lines", line=dict(color=MEN_YEARS, width=5), name="Men only",
                             hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=vx, y=vy, mode="lines", line=dict(color=SEX_COLORS["Female"], width=5),
                             name="Women also compete", hoverinfo="skip"))
    w = t[has_women]
    hover = [f"<b>{r.sport}</b><br>held {r.first}–{r.last}<br>"
             + ("women only" if r.women_only else f"women since {int(r.women_from)}" if pd.notna(r.women_from)
                else "never with women")
             + f"<br>{r.last}: {r.women_now:,} women of {r.n_now:,} athletes ({r.share_now:.0f} %)"
             for r in t.itertuples()]
    fig.add_trace(go.Scatter(
        x=wf[has_women], y=[l for l, ok in zip(labels, has_women) if ok], mode="markers", showlegend=False,
        marker=dict(size=9, color=SEX_COLORS["Female"], line=dict(color="white", width=1.5)),
        customdata=w.sport, text=[h for h, ok in zip(hover, has_women) if ok],
        hovertemplate="%{text}<extra></extra>"))
    # status text to the right of every line (also clickable / hoverable)
    x_text = max(t["last"]) + 4
    fig.add_trace(go.Scatter(
        x=[x_text] * len(t), y=labels, mode="text", text=[_status(r) for r in t.itertuples()],
        textposition="middle right", showlegend=False, customdata=t.sport, hovertext=hover,
        textfont=dict(size=10.5, color=[SEX_COLORS["Female"] if r.share_now >= 40 else TEXT_SECONDARY
                                        for r in t.itertuples()]),
        hovertemplate="%{hovertext}<extra></extra>"))
    lo = min(t["first"])
    fig.update_xaxes(range=[lo - 3, x_text + 16], showgrid=True, gridcolor="#efeeea",
                     tickvals=[y for y in range(1900, 2021, 20) if y >= lo - 3], side="top")
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(size=11), automargin=True,
                     categoryorder="array", categoryarray=labels)
    note = (f"{t.attrs['dropped']} discontinued sports not shown" if t.attrs.get("dropped") else "")
    fig.update_layout(height=max(360, 17 * len(t) + 100), hovermode="closest", margin=dict(t=70, l=10, r=10, b=10),
                      legend=dict(orientation="h", y=0.995, yanchor="top", x=0, yref="container"),
                      title=dict(text=note, font=dict(size=10.5, color=TEXT_MUTED), x=1, xanchor="right",
                                 y=0.995, yanchor="top", yref="container"))
    return fig


def sport_from_timeline_click(click) -> str | None:
    if not click or not click.get("points"):
        return None
    cd = click["points"][0].get("customdata")
    if isinstance(cd, list):
        cd = cd[0] if cd else None
    if isinstance(cd, str) and cd:
        return cd
    y = click["points"][0].get("y") or ""
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


# ====================================================================== callbacks
@callback(Output("ge-sport", "data"), Output("ge-sport-label", "children"),
          Input("ge-timeline", "clickData"), Input("ge-sport-clear", "n_clicks"), State("ge-sport", "data"),
          prevent_initial_call=True)
def follow_sport(click, _clear, current):
    """Click a sport on the timeline to follow it; click it again (or Clear) to stop."""
    if ctx.triggered_id == "ge-sport-clear":
        return None, NO_SPORT
    sport = sport_from_timeline_click(click)
    if not sport or sport == current:
        return None, NO_SPORT
    return sport, sport


@tab_callback(TAB_ID, Output("ge-share", "figure"), Input("filters", "data"), Input("ge-sport", "data"))
def update_share(f, sport):
    return fig_share(f, sport)


@tab_callback(TAB_ID, Output("ge-timeline", "figure"), Input("filters", "data"), Input("ge-sport", "data"))
def update_timeline(f, sport):
    return fig_timeline(f, sport)


@tab_callback(TAB_ID, Output("ge-spine", "figure"), Input("filters", "data"))
def update_spine(f):
    return fig_spine(f)

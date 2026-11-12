"""Tab 2, Countries & Medals: who wins, and has that changed? (Q2.1-Q2.6)

Countries chosen in the sidebar are *highlighted* on this tab (not filtered out),
and clicking a country in the map, bump chart, scatter or Sankey adds/removes it
from that selection, so all four charts (and the other tabs) follow.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, ctx, dcc, html, no_update
import dash_bootstrap_components as dbc

from .. import data_access as da
from ..components import chart_card, data_note, segmented, tab_intro
from ..theme import (DEEMPHASIS, SELECTION_COLORS, SEQUENTIAL_BLUE, TEXT_MUTED, TEXT_PRIMARY,
                     TEXT_SECONDARY, empty_figure, tint)

TAB_ID = "countries"
LABEL = "Countries & Medals"

DEFAULT_SYMBOL = "#3987e5"          # map circles when nothing is selected
DIVERGING_RCA = [[0.0, "#c43c3c"], [0.5, "#f0efec"], [1.0, "#1c5cab"]]   # red <- gray -> blue
TOP_RANK = 10
HEATMAP_ROWS, HEATMAP_COLS = 20, 20
SEASON_NOTE = "Summer Games shown; choose Winter in the sidebar to see the Winter Games."


# ====================================================================== layout
def layout():
    map_controls = dbc.Row([
        dbc.Col(segmented("co-map-metric", ["total", "per_million", "per_gdp"], "total",
                          {"total": "Medals (total)", "per_million": "per million people",
                           "per_gdp": "per $100bn GDP"}), width="auto"),
        dbc.Col(segmented("co-map-mode", ["range", "games"], "range",
                          {"range": "Whole year range", "games": "One Games at a time ▶"}), width="auto"),
    ], className="g-2")
    scatter_controls = html.Div([
        html.Span("Games", className="small text-secondary me-2"),
        dcc.Dropdown(id="co-scatter-games", clearable=False, style={"minWidth": 220}),
    ], className="d-flex align-items-center")
    heat_controls = segmented("co-heat-metric", ["count", "index"], "count",
                              {"count": "Medal count", "index": "Specialisation index"})
    sankey_controls = html.Div([
        html.Span("Minimum athletes per flow", className="small text-secondary"),
        dcc.Slider(id="co-sankey-min", min=2, max=50, step=1, value=10,
                   marks={2: "2", 10: "10", 25: "25", 50: "50"}, tooltip={"placement": "bottom"}),
    ])
    return html.Div([
        tab_intro("Who wins, and has that changed?",
                  "Medal geography, the rise and fall of sporting powers, whether success is just size and "
                  "wealth, national specialisations, home advantage and athletes changing teams. "
                  "Countries chosen in the sidebar are highlighted here, not filtered out; click a country "
                  "in any chart to add or remove it."),
        chart_card("co-map", "Q2.1", "Where in the world are medals won?",
                   "Proportional-symbol map · choropleth", "Spatial",
                   "Totals are circles (area = medals); historic teams such as the USSR are drawn at their "
                   "main successor. Rates switch to a shaded map (1960 on, present-day countries only).",
                   height=480, controls=map_controls),
        dbc.Row([
            dbc.Col(chart_card("co-bump", "Q2.2", "Which countries dominated which eras?",
                               "Bump chart", "Ranking",
                               "Each line is a country's place in the medal table (1 = top), shown while it is "
                               "in the top 10. Coloured lines: your selection, or else the four countries with "
                               "the most golds in the period.", height=440), lg=7),
            dbc.Col(chart_card("co-scatter", "Q2.3", "Is success just a matter of size and wealth?",
                               "Bubble scatter (log-log)", "Correlation",
                               "x = GDP, y = medals, area = population. Above the dashed trend line = more "
                               "medals than the economy predicts.", height=440, controls=scatter_controls),
                    lg=5),
        ], className="g-3 my-1"),
        chart_card("co-heatmap", "Q2.4", "In which sports does each country specialise?",
                   "XY-heatmap", "Correlation",
                   "Count: darker = more medals. Specialisation index = a country's share of medals in a sport "
                   "÷ its share of all medals: blue = stronger than its overall level, red = weaker.",
                   height=560, controls=heat_controls),
        dbc.Row([
            dbc.Col(chart_card("co-host", "Q2.5", "Do host countries win more at their home Games?",
                               "Dumbbell", "Distribution (dot-plot)",
                               "Gray dot = the host's usual share of all medals (two Games before and after); "
                               "blue dot = its share at home. The line is the home boost.", height=620), lg=5),
            dbc.Col(chart_card("co-sankey", "Q2.6", "How do athletes move between national teams?",
                               "Sankey", "Flow",
                               "Left = team at one Games, right = team at the athlete's next Games; band width "
                               "= athletes. Break-ups (USSR → Unified Team → successors), reunification "
                               "(Germany) and naturalisation.", height=620, controls=sankey_controls), lg=7),
        ], className="g-3 my-1"),
        data_note("Medal totals follow the official medal table (team medals count once), without Art "
                  "Competitions. Per-sport medals (Q2.4) are counted from athlete results the same way. "
                  "Population and GDP: World Bank, 1960 onwards; historic teams have no World Bank data."),
    ])


# ====================================================================== selection helpers
def selection_colors(selected: list[str] | None) -> dict[str, str]:
    """Colour follows the country, in selection order; beyond four, dark gray."""
    return {noc: (SELECTION_COLORS[i] if i < len(SELECTION_COLORS) else TEXT_SECONDARY)
            for i, noc in enumerate(selected or [])}


def noc_from_click(click) -> str | None:
    if not click or not click.get("points"):
        return None
    p = click["points"][0]
    cd = p.get("customdata")
    if isinstance(cd, list):
        cd = cd[0] if cd else None
    if isinstance(cd, str) and cd:
        return cd
    label = p.get("label")                       # Sankey nodes
    return label if isinstance(label, str) and label.isupper() and len(label) == 3 else None


def toggle(selected: list[str] | None, noc: str) -> list[str]:
    selected = list(selected or [])
    return [s for s in selected if s != noc] if noc in selected else selected + [noc]


def _summer_if_both(f: dict) -> tuple[dict, str]:
    """Rank-based charts compare one season at a time."""
    if f["season"] == "Both":
        return {**f, "season": "Summer"}, SEASON_NOTE
    return f, ""


# ====================================================================== Q2.1 map
GEO = dict(projection_type="natural earth", showframe=False, showcoastlines=False, showcountries=True,
           countrycolor="#ffffff", countrywidth=0.5, showland=True, landcolor="#e9e8e4",
           showocean=False, lataxis_range=[-58, 85], bgcolor="rgba(0,0,0,0)")


def map_totals(cg: pd.DataFrame) -> pd.DataFrame:
    g = (cg[cg.map_iso3.notna()].groupby("noc")
         .agg(country=("country", "first"), map_iso3=("map_iso3", "first"), gold=("gold", "sum"),
              silver=("silver", "sum"), bronze=("bronze", "sum"), total=("total", "sum"),
              n_games=("edition_id", "nunique"))
         .reset_index())
    return g[g.total > 0].sort_values("total", ascending=False)   # big circles drawn first


def map_rates(cg: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Medals per million people (or per $100bn GDP) per Games, 1960 on.
    Pooled: sum of medals / sum of population over the Games the country attended."""
    base = "population" if metric == "per_million" else "gdp_usd"
    scale = 1e6 if metric == "per_million" else 1e11
    d = cg[cg.iso3.notna() & cg[base].notna() & (cg.n_athletes > 0)]
    g = d.groupby(["noc", "iso3"]).agg(country=("country", "first"), total=("total", "sum"),
                                       base=(base, "sum"), n_games=("edition_id", "nunique")).reset_index()
    g["rate"] = g.total / (g.base / scale)
    return g


def _symbol_trace(d: pd.DataFrame, colors: dict, sizeref: float) -> go.Scattergeo:
    any_sel = bool(colors)
    fill = [colors.get(n, DEEMPHASIS if any_sel else DEFAULT_SYMBOL) for n in d.noc]
    edge = [TEXT_PRIMARY if n in colors else "white" for n in d.noc]
    return go.Scattergeo(
        locations=d.map_iso3, locationmode="ISO-3", customdata=d.noc,
        marker=dict(size=d.total, sizemode="area", sizeref=sizeref, sizemin=3, color=fill,
                    opacity=0.72, line=dict(color=edge, width=[1.6 if n in colors else 0.6 for n in d.noc])),
        text=[f"<b>{c}</b> ({n})<br>{t:,} medals · G {g} · S {s} · B {b}<br>{k} Games"
              for c, n, t, g, s, b, k in zip(d.country, d.noc, d.total, d.gold, d.silver, d.bronze, d.n_games)],
        hovertemplate="%{text}<extra></extra>", showlegend=False)


def _rate_trace(d: pd.DataFrame, metric: str, colors: dict, zmax: float) -> go.Choropleth:
    unit = "per million people" if metric == "per_million" else "per $100bn GDP"
    return go.Choropleth(
        locations=d.iso3, z=d.rate, customdata=d.noc, zmin=0, zmax=zmax,
        colorscale=[[i / 6, c] for i, c in enumerate(SEQUENTIAL_BLUE)],
        marker=dict(line=dict(color=[colors.get(n, "white") for n in d.noc],
                              width=[2.2 if n in colors else 0.5 for n in d.noc])),
        colorbar=dict(title=dict(text=f"medals<br>{unit}<br>per Games", font=dict(size=11)), thickness=12,
                      len=0.7, ticksuffix="", tickfont=dict(size=10)),
        text=[f"<b>{c}</b> ({n})<br>{r:.2f} medals {unit} per Games<br>{t:,} medals in {k} Games"
              for c, n, r, t, k in zip(d.country, d.noc, d.rate, d.total, d.n_games)],
        hovertemplate="%{text}<extra></extra>")


def _short(games: str) -> str:
    """'2022 Winter Olympics' -> '2022 W' for the crowded slider ticks."""
    return f"{games[:4]} {games[5]}"


def fig_map(f: dict, metric: str = "total", mode: str = "range") -> go.Figure:
    cg = da.filter_country_games(f)
    colors = selection_colors(f["countries"])
    if metric != "total":
        cg = cg[cg.year >= 1960]
        if cg.empty:
            return empty_figure("No population or GDP data before 1960",
                                "Move the year range to 1960 or later, or switch to medal totals.")
    if cg.empty or cg.total.sum() == 0:
        return empty_figure()

    if mode == "range":
        if metric == "total":
            d = map_totals(cg)
            fig = go.Figure(_symbol_trace(d, colors, sizeref=d.total.max() / 40 ** 2))
        else:
            d = map_rates(cg, metric)
            fig = go.Figure(_rate_trace(d, metric, colors, zmax=float(d.rate.quantile(0.97))))
        lo, hi = int(cg.year.min()), int(cg.year.max())
        subtitle = f"{lo}–{hi}" + ("" if f["season"] == "Both" else f", {f['season']}")
    else:   # one Games at a time, with Plotly's play button and slider
        games = cg.drop_duplicates("edition_id").sort_values(["year", "season"])[["edition_id", "games"]]
        per = {gid: cg[cg.edition_id == gid] for gid in games.edition_id}
        if metric == "total":
            frames_d = {gid: map_totals(d) for gid, d in per.items()}
            sizeref = max(d.total.max() for d in frames_d.values() if len(d)) / 34 ** 2
            make = lambda d: _symbol_trace(d, colors, sizeref)  # noqa: E731
        else:
            frames_d = {gid: map_rates(d, metric) for gid, d in per.items()}
            zmax = float(pd.concat(frames_d.values()).rate.quantile(0.97))
            make = lambda d: _rate_trace(d, metric, colors, zmax)  # noqa: E731
        names = dict(zip(games.edition_id, games.games))
        frames = [go.Frame(data=[make(frames_d[gid])], name=names[gid]) for gid in games.edition_id]
        fig = go.Figure(data=frames[-1].data, frames=frames)
        fig.update_layout(
            updatemenus=[dict(type="buttons", showactive=False, x=0, y=0, xanchor="left", yanchor="top",
                              pad=dict(t=8, r=8), direction="left",
                              buttons=[dict(label="▶ Play", method="animate",
                                            args=[None, dict(frame=dict(duration=700, redraw=True),
                                                             transition=dict(duration=0), fromcurrent=True)]),
                                       dict(label="❚❚", method="animate",
                                            args=[[None], dict(mode="immediate", frame=dict(duration=0))])])],
            sliders=[dict(active=len(frames) - 1, x=0.16, len=0.84, y=0, yanchor="top", pad=dict(t=8),
                          currentvalue=dict(prefix="Games: ", suffix="  (S = Summer, W = Winter)", xanchor="right",
                                            font=dict(size=13, color=TEXT_PRIMARY)),
                          font=dict(size=9, color=TEXT_MUTED),
                          steps=[dict(method="animate", label=_short(fr.name),
                                      args=[[fr.name], dict(mode="immediate", frame=dict(duration=0, redraw=True))])
                                 for fr in frames])])
        subtitle = "one Games at a time: press ▶ or drag the slider"
    fig.update_geos(**GEO)
    fig.update_layout(margin=dict(l=0, r=0, t=24, b=40 if mode == "games" else 0),
                      title=dict(text=subtitle, font=dict(size=12, color=TEXT_SECONDARY), x=0, y=0.99))
    return fig


# ====================================================================== Q2.2 bump chart
def bump_data(f: dict) -> tuple[pd.DataFrame, list[str], str]:
    f2, note = _summer_if_both(f)
    cg = da.filter_country_games(f2)
    ranked = cg[cg["rank"].notna() & (cg["rank"] <= TOP_RANK)]
    top = (cg.groupby("noc").gold.sum().sort_values(ascending=False))
    highlight = [n for n in (f["countries"] or []) if n in set(ranked.noc)] or top.head(4).index.tolist()
    return cg, highlight, note


def fig_bump(f: dict) -> go.Figure:
    cg, highlight, note = bump_data(f)
    years = sorted(cg.year.unique())
    ranked = cg[cg["rank"].notna() & (cg["rank"] <= TOP_RANK)]
    if ranked.empty:
        return empty_figure()
    colors = selection_colors(highlight)
    fig = go.Figure()
    # context lines first (gray), highlighted lines on top
    order = [n for n in ranked.noc.unique() if n not in colors] + [n for n in highlight if n in set(ranked.noc)]
    for noc in order:
        d = cg[cg.noc == noc].set_index("year").reindex(years)
        y = d["rank"].where(d["rank"] <= TOP_RANK).astype(float)
        on = noc in colors
        name = d.country.dropna().iloc[0] if d.country.notna().any() else noc
        fig.add_trace(go.Scatter(
            x=years, y=y, mode="lines+markers", name=name, customdata=[noc] * len(years),
            line=dict(color=colors.get(noc, DEEMPHASIS), width=3 if on else 1.2),
            marker=dict(size=8 if on else 4, color=colors.get(noc, DEEMPHASIS),
                        line=dict(color="white", width=1)),
            opacity=1 if on else 0.55, showlegend=False, connectgaps=False,
            text=[f"<b>{name}</b> ({noc})<br>{y_} {d.season.dropna().iloc[0] if d.season.notna().any() else ''}"
                  f"<br>Rank {int(r)} · {int(gd)} gold · {int(t)} medals" if pd.notna(r) else ""
                  for y_, r, gd, t in zip(years, y, d.gold.fillna(0), d.total.fillna(0))],
            hovertemplate="%{text}<extra></extra>"))
        if on:   # direct label at the line's last point in the top 10
            last = y.dropna()
            if len(last):
                fig.add_annotation(x=last.index[-1], y=last.iloc[-1], text=f"<b>{noc}</b>", xanchor="left",
                                   xshift=8, showarrow=False, font=dict(color=colors[noc], size=12))
    fig.update_yaxes(autorange=False, range=[TOP_RANK + 0.6, 0.4], tickvals=list(range(1, TOP_RANK + 1)),
                     title_text="Rank in medal table", showgrid=False)
    fig.update_xaxes(showgrid=True, range=[years[0] - 2, years[-1] + 8] if years else None)
    fig.update_layout(hovermode="closest", margin=dict(t=30, r=10),
                      title=dict(text=note, font=dict(size=11, color=TEXT_MUTED), x=0, y=0.99))
    return fig


# ====================================================================== Q2.3 bubble scatter
def scatter_games_options(f: dict) -> tuple[list[dict], int | None]:
    cg = da.filter_country_games(f)
    g = cg[(cg.year >= 1960)].drop_duplicates("edition_id").sort_values(["year", "season"], ascending=False)
    options = [{"label": r.games, "value": int(r.edition_id)} for r in g.itertuples()]
    summer = g[g.season == "Summer"]
    default = int((summer if len(summer) else g).edition_id.iloc[0]) if len(g) else None
    return options, default


def scatter_data(edition_id: int) -> pd.DataFrame:
    cg = da.table("country_games")
    d = cg[(cg.edition_id == edition_id) & (cg.total > 0) & cg.gdp_usd.notna() & cg.population.notna()].copy()
    if len(d) < 3:
        return d
    slope, intercept = np.polyfit(np.log10(d.gdp_usd), np.log10(d.total), 1)
    d["expected"] = 10 ** (intercept + slope * np.log10(d.gdp_usd))
    d["ratio"] = d.total / d.expected
    d.attrs["fit"] = (slope, intercept)
    return d


def fig_scatter(f: dict, edition_id: int | None) -> go.Figure:
    if edition_id is None:
        return empty_figure("No Games from 1960 on in the selection", "GDP data start in 1960.")
    d = scatter_data(edition_id)
    if len(d) < 3:
        return empty_figure("Too few countries with medals and GDP data")
    colors = selection_colors(f["countries"])
    slope, intercept = d.attrs["fit"]
    d = d.sort_values("population", ascending=False)
    fig = go.Figure()
    xs = np.logspace(np.log10(d.gdp_usd.min()), np.log10(d.gdp_usd.max()), 20)
    fig.add_trace(go.Scatter(x=xs, y=10 ** (intercept + slope * np.log10(xs)), mode="lines",
                             line=dict(color=TEXT_MUTED, dash="dash", width=1.2), hoverinfo="skip",
                             showlegend=False))
    fig.add_trace(go.Scatter(
        x=d.gdp_usd, y=d.total, mode="markers", customdata=d.noc, showlegend=False,
        marker=dict(size=d.population, sizemode="area", sizeref=d.population.max() / 38 ** 2, sizemin=4,
                    color=[colors.get(n, DEFAULT_SYMBOL if not colors else DEEMPHASIS) for n in d.noc],
                    opacity=0.75, line=dict(color="white", width=0.8)),
        text=[f"<b>{c}</b> ({n})<br>{t} medals · {r:.1f}× expected<br>GDP ${g / 1e9:,.0f} bn · "
              f"population {p / 1e6:,.1f} m" for c, n, t, r, g, p in
              zip(d.country, d.noc, d.total, d.ratio, d.gdp_usd, d.population)],
        hovertemplate="%{text}<extra></extra>"))
    # selective direct labels: the 3 biggest over-performers plus the selection
    label = set(d.nlargest(3, "ratio").noc) | set(colors)
    for r in d[d.noc.isin(label)].itertuples():
        fig.add_annotation(x=np.log10(r.gdp_usd), y=np.log10(r.total), text=r.noc, showarrow=False,
                           yshift=11, font=dict(size=10, color=colors.get(r.noc, TEXT_SECONDARY)))
    gdp_ticks = [1e9, 1e10, 1e11, 1e12, 1e13]
    fig.update_xaxes(type="log", title_text="GDP, current US$ (log scale)", tickvals=gdp_ticks,
                     ticktext=["$1bn", "$10bn", "$100bn", "$1tn", "$10tn"])
    fig.update_yaxes(type="log", title_text="Medals (log scale)", tickvals=[1, 3, 10, 30, 100],
                     ticktext=["1", "3", "10", "30", "100"])
    fig.update_layout(margin=dict(t=30), hovermode="closest",
                      title=dict(text=f"{len(d)} medal-winning countries with World Bank data",
                                 font=dict(size=11, color=TEXT_MUTED), x=0, y=0.99))
    return fig


# ====================================================================== Q2.4 heatmap
def heatmap_matrix(f: dict, metric: str = "count") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (z, counts): rows = countries, columns = sports."""
    m = da.table("medals_by_sport")
    m = m[m.year.between(*f["years"])]
    if f["season"] != "Both":
        m = m[m.season == f["season"]]
    if f["sports"]:
        m = m[m.sport.isin(f["sports"])]
    elif f["hide_minor"]:
        m = m[~m.sport.isin(da.table("sports").query("is_minor").sport)]
    if m.empty:
        return pd.DataFrame(), pd.DataFrame()
    counts = m.pivot_table(index="noc", columns="sport", values="total", aggfunc="sum", fill_value=0)
    by_country = counts.sum(axis=1).sort_values(ascending=False)
    rows = [n for n in (f["countries"] or []) if n in counts.index]
    rows += [n for n in by_country.index if n not in rows][: max(0, HEATMAP_ROWS - len(rows))]
    cols = counts.sum(axis=0).sort_values(ascending=False).head(HEATMAP_COLS).index
    if metric == "index":
        # Revealed specialisation: (country's share in sport) / (sport's share of all medals)
        share_c = counts.div(counts.sum(axis=1), axis=0)
        share_w = counts.sum(axis=0) / counts.values.sum()
        z = share_c.div(share_w, axis=1)
    else:
        z = counts
    return z.loc[rows, cols], counts.loc[rows, cols]


def fig_heatmap(f: dict, metric: str = "count") -> go.Figure:
    z, counts = heatmap_matrix(f, metric)
    if z.empty:
        return empty_figure()
    names = da.table("countries").set_index("noc").country
    sel = set(f["countries"] or [])
    ylabels = [f"<b>{n}</b>" if n in sel else n for n in z.index]
    custom = np.dstack([counts.values, np.broadcast_to(np.array([names.get(n, n) for n in z.index])[:, None],
                                                       counts.shape)])
    if metric == "index":
        # No medals in a sport = blank (not "strongly weaker"), so red marks real under-performance only
        logz = np.log2(z.where(counts > 0)).clip(-3, 3)
        trace = go.Heatmap(z=logz.values, x=z.columns, y=ylabels, zmin=-3, zmax=3, colorscale=DIVERGING_RCA,
                           customdata=custom, text=z.round(2).values, hoverongaps=False,
                           colorbar=dict(title=dict(text="vs country's<br>average", font=dict(size=11)),
                                         tickvals=[-3, -2, -1, 0, 1, 2, 3], thickness=12,
                                         ticktext=["≤⅛×", "¼×", "½×", "1×", "2×", "4×", "≥8×"]),
                           hovertemplate="<b>%{customdata[1]}</b> · %{x}<br>%{customdata[0]} medals<br>"
                                         "Specialisation index %{text}<extra></extra>", xgap=1, ygap=1)
    else:
        trace = go.Heatmap(z=z.values, x=z.columns, y=ylabels,
                           colorscale=[[0, "#f5f4f1"]] + [[(i + 1) / 7, c] for i, c in enumerate(SEQUENTIAL_BLUE)],
                           customdata=custom, colorbar=dict(title=dict(text="medals", font=dict(size=11)),
                                                            thickness=12),
                           hovertemplate="<b>%{customdata[1]}</b> · %{x}<br>%{z} medals<extra></extra>",
                           xgap=1, ygap=1)
    fig = go.Figure(trace)
    if metric == "index":
        fig.add_annotation(text="blank = no medals in that sport", x=1, y=-0.02, xref="paper", yref="paper",
                           xanchor="right", yanchor="top", showarrow=False, font=dict(size=10, color=TEXT_MUTED))
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(size=11))
    fig.update_xaxes(side="top", tickangle=-40, showgrid=False, tickfont=dict(size=11))
    fig.update_layout(margin=dict(t=110, l=60, r=10, b=24), plot_bgcolor="#f5f4f1")
    return fig


# ====================================================================== Q2.5 host dumbbell
def host_data(f: dict) -> tuple[pd.DataFrame, str]:
    f2, note = _summer_if_both(f)
    cg = da.table("country_games")
    cg = cg[cg.season == f2["season"]]
    games = da.table("games")
    games = games[(games.season == f2["season"])].sort_values("year").reset_index(drop=True)
    totals = cg.groupby("edition_id").total.sum()
    cg = cg.assign(share=cg.total / cg.edition_id.map(totals) * 100)
    rows = []
    for i, g in games.iterrows():
        if not (f["years"][0] <= g.year <= f["years"][1]):
            continue
        near = games.iloc[max(0, i - 2): i + 3]
        near = near[near.edition_id != g.edition_id].edition_id
        mine = cg[cg.noc == g.host_noc].set_index("edition_id").share
        home = mine.get(g.edition_id, np.nan)
        usual = mine.reindex(near).dropna()
        if pd.isna(home) or usual.empty:
            continue
        rows.append({"label": f"{g.year} {g.city} · {g.host_noc}", "noc": g.host_noc, "year": g.year,
                     "home": home, "usual": usual.mean(), "n_ref": len(usual)})
    return pd.DataFrame(rows), note


def fig_host(f: dict) -> go.Figure:
    d, note = host_data(f)
    if d.empty:
        return empty_figure("No host Games with comparison Games in this range")
    d = d.sort_values("year", ascending=False)
    better = (d.home > d.usual).sum()
    ratio = (d.home / d.usual.replace(0, np.nan)).median()
    colors = selection_colors(f["countries"])
    fig = go.Figure()
    for r in d.itertuples():
        fig.add_trace(go.Scatter(x=[r.usual, r.home], y=[r.label, r.label], mode="lines",
                                 line=dict(color="#d6d5cf", width=3), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=d.usual, y=d.label, mode="markers", name="Usual share",
                             marker=dict(size=9, color=DEEMPHASIS), customdata=d.noc,
                             text=[f"{u:.1f}% (mean of {n} nearby Games)" for u, n in zip(d.usual, d.n_ref)],
                             hovertemplate="<b>%{y}</b><br>Usual: %{text}<extra></extra>"))
    fig.add_trace(go.Scatter(x=d.home, y=d.label, mode="markers", name="At home", customdata=d.noc,
                             marker=dict(size=10, color=[colors.get(n, SELECTION_COLORS[0]) for n in d.noc],
                                         line=dict(color="white", width=1)),
                             text=[f"{h:.1f}% · {h / u:.1f}× usual" if u else f"{h:.1f}%"
                                   for h, u in zip(d.home, d.usual)],
                             hovertemplate="<b>%{y}</b><br>At home: %{text}<extra></extra>"))
    fig.update_xaxes(title_text="Share of all medals (%)", rangemode="tozero")
    fig.update_yaxes(showgrid=False, tickfont=dict(size=10.5), categoryorder="array", automargin=True,
                     categoryarray=list(d.label[::-1]))
    summary = f"Hosts did better at home in {better} of {len(d)} Games (median {ratio:.1f}× their usual share)."
    fig.update_layout(margin=dict(t=84, l=10), legend=dict(y=1.0, yanchor="bottom", x=1, xanchor="right"),
                      title=dict(text=summary + (f"<br><span style='font-size:10px;color:{TEXT_MUTED}'>{note}</span>"
                                                 if note else ""),
                                 font=dict(size=11.5, color=TEXT_SECONDARY), x=0, xref="paper",
                                 y=0.995, yanchor="top"))
    return fig


# ====================================================================== Q2.6 Sankey
def team_switches(f: dict) -> pd.DataFrame:
    """Consecutive Games of the same athlete with a different team (event-level NOC)."""
    a = da.filter_athletes(f, ignore=("countries",))
    a = (a.drop_duplicates(["athlete_id", "edition_id", "noc"])
          .assign(order=lambda x: x.year * 10 + (x.season == "Summer"))
          .sort_values(["athlete_id", "order"]))
    a["prev"] = a.groupby("athlete_id").noc.shift()
    sw = a[a.prev.notna() & (a.prev != a.noc)]
    return sw.groupby(["prev", "noc"]).size().rename("athletes").reset_index().sort_values(
        "athletes", ascending=False)


def fig_sankey(f: dict, min_flow: int = 10) -> go.Figure:
    flows = team_switches(f)
    if flows.empty:
        return empty_figure("No athletes changed team in this selection")
    shown = flows[flows.athletes >= min_flow]
    hidden = flows[flows.athletes < min_flow]
    if shown.empty:
        return empty_figure(f"No flow has {min_flow}+ athletes", "Lower the minimum with the slider.")
    names = da.table("countries").set_index("noc").country
    colors = selection_colors(f["countries"])
    left = list(dict.fromkeys(shown.prev))
    right = list(dict.fromkeys(shown.noc))
    labels = left + right
    idx_l = {n: i for i, n in enumerate(left)}
    idx_r = {n: i + len(left) for i, n in enumerate(right)}
    node_color = [colors.get(n, "#8a8984") for n in labels]

    def link_color(a, b):
        c = colors.get(a) or colors.get(b)
        if c:
            h = c.lstrip("#")
            return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},0.55)"
        return "rgba(57,135,229,0.28)" if not colors else "rgba(138,137,132,0.22)"

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=labels, color=node_color, pad=10, thickness=14, line=dict(width=0),
                  customdata=[[n, names.get(n, n)] for n in labels],      # [noc, name]: noc used on click
                  hovertemplate="<b>%{customdata[1]}</b> (%{label})<br>%{value} athletes<extra></extra>"),
        link=dict(source=[idx_l[a] for a in shown.prev], target=[idx_r[b] for b in shown.noc],
                  value=shown.athletes, color=[link_color(a, b) for a, b in zip(shown.prev, shown.noc)],
                  customdata=[["", f"{names.get(a, a)} → {names.get(b, b)}"] for a, b in zip(shown.prev, shown.noc)],
                  hovertemplate="%{customdata[1]}<br>%{value} athletes<extra></extra>"),
        textfont=dict(size=11, color=TEXT_PRIMARY),
    ))
    note = (f"{len(shown)} flows, {shown.athletes.sum():,} athletes shown · {len(hidden)} smaller flows "
            f"({hidden.athletes.sum():,} athletes) hidden" if len(hidden) else f"{len(shown)} flows")
    fig.update_layout(margin=dict(l=8, r=8, t=30, b=8),
                      title=dict(text=note, font=dict(size=11, color=TEXT_MUTED), x=0, y=0.99))
    return fig


# ====================================================================== callbacks
@callback(Output("co-map", "figure"), Input("filters", "data"), Input("co-map-metric", "value"),
          Input("co-map-mode", "value"))
def update_map(f, metric, mode):
    return fig_map(f, metric, mode)


@callback(Output("co-bump", "figure"), Input("filters", "data"))
def update_bump(f):
    return fig_bump(f)


@callback(Output("co-scatter-games", "options"), Output("co-scatter-games", "value"),
          Input("filters", "data"), State("co-scatter-games", "value"))
def update_scatter_games(f, current):
    options, default = scatter_games_options(f)
    valid = {o["value"] for o in options}
    return options, (current if current in valid else default)


@callback(Output("co-scatter", "figure"), Input("filters", "data"), Input("co-scatter-games", "value"))
def update_scatter(f, edition_id):
    return fig_scatter(f, edition_id)


@callback(Output("co-heatmap", "figure"), Input("filters", "data"), Input("co-heat-metric", "value"))
def update_heatmap(f, metric):
    return fig_heatmap(f, metric)


@callback(Output("co-host", "figure"), Input("filters", "data"))
def update_host(f):
    return fig_host(f)


@callback(Output("co-sankey", "figure"), Input("filters", "data"), Input("co-sankey-min", "value"))
def update_sankey(f, min_flow):
    return fig_sankey(f, min_flow or 10)


@callback(Output("flt-countries", "value", allow_duplicate=True),
          Input("co-map", "clickData"), Input("co-bump", "clickData"), Input("co-scatter", "clickData"),
          Input("co-host", "clickData"), Input("co-sankey", "clickData"),
          State("flt-countries", "value"), prevent_initial_call=True)
def click_to_select(map_c, bump_c, scatter_c, host_c, sankey_c, selected):
    """Linked views: a click on a country in any chart toggles it in the sidebar selection."""
    clicks = {"co-map": map_c, "co-bump": bump_c, "co-scatter": scatter_c, "co-host": host_c,
              "co-sankey": sankey_c}
    noc = noc_from_click(clicks.get(ctx.triggered_id))
    if not noc:
        return no_update
    return toggle(selected, noc)

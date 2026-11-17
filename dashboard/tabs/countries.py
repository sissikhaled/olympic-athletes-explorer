"""Tab 2, Countries & Medals. Q1: what drives a country's Olympic success? Q2: do hosts win more at home?

Countries chosen in the filter panel are *highlighted* on this tab (not filtered
out), and clicking a country in the map, scatter or host chart adds/removes it
from that selection, so all charts (and the other tabs) follow.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, ctx, dcc, html, no_update
import dash_bootstrap_components as dbc

from .. import data_access as da
from ..components import tab_callback, chart_card, data_note, segmented, tab_intro
from ..theme import (DEEMPHASIS, SELECTION_COLORS, SEQUENTIAL_BLUE, TEXT_MUTED, TEXT_PRIMARY,
                     TEXT_SECONDARY, empty_figure)

TAB_ID = "countries"
LABEL = "Countries & Medals"

DEFAULT_SYMBOL = "#3987e5"          # map circles when nothing is selected
DIVERGING_RCA = [[0.0, "#c43c3c"], [0.5, "#f0efec"], [1.0, "#1c5cab"]]   # red <- gray -> blue
HEATMAP_ROWS, HEATMAP_COLS = 20, 20
SEASON_NOTE = "Summer Games shown; choose Winter in the filters to see the Winter Games."


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
    return html.Div([
        tab_intro("What drives a country's Olympic success: size, wealth or specialisation?",
                  "The map shows who wins; the two charts below test one possible driver each: the economy and "
                  "population, and concentrating on a few sports. Countries chosen in the filters are "
                  "highlighted here, not filtered out; click a country in any chart to add or remove it.",
                  qid="Q1"),
        chart_card("co-map", "Medals by country",
                   "Proportional-symbol map · choropleth", "Spatial",
                   "Totals are circles (area = medals); historic teams such as the USSR keep their own circle, "
                   "drawn at their main successor. Rates switch to a shaded map (1960 on, present-day countries "
                   "only).",
                   height=500, controls=map_controls),
        chart_card("co-scatter", "Size and wealth: medals vs GDP and population",
                   "Bubble scatter (log-log)", "Correlation",
                   "x = GDP, y = medals, bubble area = population. The dashed line is the trend: countries above "
                   "it win more medals than their economy predicts.",
                   height=520, controls=scatter_controls),
        chart_card("co-heatmap", "Specialisation: medals by country and sport",
                   "XY-heatmap", "Correlation",
                   "Count: darker = more medals. Specialisation index = a country's share of medals in a sport "
                   "÷ its share of all medals: blue = stronger than its overall level, red = weaker. Teams are "
                   "combined with their predecessors (marked *): Russia includes the USSR, Germany includes East "
                   "and West Germany; hover a row to see which teams.",
                   height=580, controls=heat_controls),
        tab_intro("Do hosts win more at home?",
                  "Each host country's share of all medals at its home Games, compared with its usual share at "
                  "the two Games before and after. Rank-based, so one season at a time.",
                  qid="Q2", section=True),
        chart_card("co-host", "Hosts at home vs their usual share",
                   "Dumbbell", "Distribution (dot-plot)",
                   "Gray dot = the host's usual share of all medals (two Games before and after); blue dot = its "
                   "share at home. The line is the home boost.", height=620),
        data_note("Medal totals follow the official medal table (team medals count once), without Art "
                  "Competitions. Per-sport medals (heatmap) are counted from athlete results the same way. "
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
    return None


def toggle(selected: list[str] | None, noc: str) -> list[str]:
    selected = list(selected or [])
    return [s for s in selected if s != noc] if noc in selected else selected + [noc]


def _summer_if_both(f: dict) -> tuple[dict, str]:
    """Rank-based charts compare one season at a time."""
    if f["season"] == "Both":
        return {**f, "season": "Summer"}, SEASON_NOTE
    return f, ""


# ====================================================================== medal map
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
    if cg.empty or cg.total.sum() == 0:          # no Games / no medals: say that first
        return empty_figure()
    if metric != "total":
        cg = cg[cg.year >= 1960]
        if cg.empty:
            return empty_figure("No population or GDP data before 1960",
                                "Move the year range to 1960 or later, or switch to medal totals.")

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


# ====================================================================== bubble scatter (size and wealth)
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


# ====================================================================== heatmap (specialisation)
def heatmap_matrix(f: dict, metric: str = "count") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (z, counts): rows = countries, columns = sports.

    Historic teams are folded into their present-day successor (da.lineage), so the USSR's
    gymnastics medals count for Russia and East Germany's for Germany: a long-run
    specialisation is about the sporting nation, not the flag it competed under."""
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
    lin = da.lineage()
    m = m.assign(noc=m.noc.map(lambda n: lin.get(n, n)))
    counts = m.pivot_table(index="noc", columns="sport", values="total", aggfunc="sum", fill_value=0)
    by_country = counts.sum(axis=1).sort_values(ascending=False)
    wanted = list(dict.fromkeys(lin.get(n, n) for n in (f["countries"] or [])))
    rows = [n for n in wanted if n in counts.index]
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


def predecessors(noc: str) -> list[str]:
    """Historic teams folded into `noc` on the heatmap, e.g. RUS -> [URS, EUN, ROC]."""
    return [h for h, succ in da.lineage().items() if succ == noc]


def fig_heatmap(f: dict, metric: str = "count") -> go.Figure:
    z, counts = heatmap_matrix(f, metric)
    if z.empty:
        return empty_figure()
    names = da.table("countries").set_index("noc").country
    lin = da.lineage()
    sel = {lin.get(n, n) for n in (f["countries"] or [])}
    ylabels = []
    full_names = []
    for n in z.index:
        pre = predecessors(n)
        label = n + ("*" if pre else "")
        ylabels.append(f"<b>{label}</b>" if n in sel else label)
        full_names.append(names.get(n, n) + (f" (incl. {', '.join(names.get(h, h) for h in pre)})" if pre else ""))
    custom = np.dstack([counts.values, np.broadcast_to(np.array(full_names)[:, None], counts.shape)])
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
    notes = []
    if any(predecessors(n) for n in z.index):
        notes.append("* includes predecessor teams (hover for details)")
    if metric == "index":
        notes.append("blank = no medals in that sport")
    if notes:
        fig.add_annotation(text=" · ".join(notes), x=1, y=-0.02, xref="paper", yref="paper",
                           xanchor="right", yanchor="top", showarrow=False, font=dict(size=10, color=TEXT_MUTED))
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(size=11))
    fig.update_xaxes(side="top", tickangle=-40, showgrid=False, tickfont=dict(size=11))
    fig.update_layout(margin=dict(t=110, l=60, r=10, b=24), plot_bgcolor="#f5f4f1")
    return fig


# ====================================================================== host dumbbell (home advantage)
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
    summary = (f"<b>Hosts did better at home in {better} of {len(d)} Games</b><br>"
               f"median {ratio:.1f}× their usual share of medals")
    if note:
        summary += f"<br><span style='font-size:10px;color:{TEXT_MUTED}'>{note}</span>"
    fig.add_annotation(text=summary, x=0, y=1, xref="paper", yref="paper", xanchor="left", yanchor="bottom",
                       yshift=6, showarrow=False, align="left", font=dict(size=11.5, color=TEXT_SECONDARY))
    fig.update_layout(margin=dict(t=76 if note else 60, l=10, b=96),
                      legend=dict(orientation="h", y=0, yref="container", yanchor="bottom", x=1, xanchor="right"))
    return fig


# ====================================================================== callbacks
@tab_callback(TAB_ID, Output("co-map", "figure"), Input("filters", "data"), Input("co-map-metric", "value"),
          Input("co-map-mode", "value"))
def update_map(f, metric, mode):
    return fig_map(f, metric, mode)


@tab_callback(TAB_ID, Output("co-scatter-games", "options"), Output("co-scatter-games", "value"),
          Input("filters", "data"), State("co-scatter-games", "value"))
def update_scatter_games(f, current):
    options, default = scatter_games_options(f)
    valid = {o["value"] for o in options}
    return options, (current if current in valid else default)


@tab_callback(TAB_ID, Output("co-scatter", "figure"), Input("filters", "data"), Input("co-scatter-games", "value"))
def update_scatter(f, edition_id):
    return fig_scatter(f, edition_id)


@tab_callback(TAB_ID, Output("co-heatmap", "figure"), Input("filters", "data"), Input("co-heat-metric", "value"))
def update_heatmap(f, metric):
    return fig_heatmap(f, metric)


@tab_callback(TAB_ID, Output("co-host", "figure"), Input("filters", "data"))
def update_host(f):
    return fig_host(f)


@callback(Output("flt-countries", "value", allow_duplicate=True),
          Input("co-map", "clickData"), Input("co-scatter", "clickData"), Input("co-host", "clickData"),
          State("flt-countries", "value"), prevent_initial_call=True)
def click_to_select(map_c, scatter_c, host_c, selected):
    """Linked views: a click on a country in any chart toggles it in the country filter."""
    clicks = {"co-map": map_c, "co-scatter": scatter_c, "co-host": host_c}
    noc = noc_from_click(clicks.get(ctx.triggered_id))
    if not noc:
        return no_update
    return toggle(selected, noc)

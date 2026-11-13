"""Tab 5, Sport Comparison: which sports are alike? (Q5.1-Q5.3)

Sport profiles are recomputed for the sidebar filters (years, season, sex,
countries; the sidebar's sport filter is ignored - this tab has its own picker).
Profile: mean height, weight, BMI (one row per athlete per sport), mean age (per
Games) and share of women. PCA on the standardised profiles places sports so
that distance = dissimilarity.
"""
from __future__ import annotations

import json
from functools import lru_cache

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, ctx, dcc, html
import dash_bootstrap_components as dbc
from plotly.subplots import make_subplots
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from .. import data_access as da
from ..components import tab_callback, chart_card, data_note, tab_intro
from ..theme import (DEEMPHASIS, SEASON_COLORS, SELECTION_COLORS, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY,
                     empty_figure, tint)

TAB_ID = "sports"
LABEL = "Sport Comparison"
DEFAULT_COMPARE = ["Basketball", "Artistic Gymnastics", "Weightlifting"]
MAX_COMPARE = 4
MIN_MEASURED = 30
IGNORE = ("sports",)

FEATURES = {"height": "Height", "weight": "Weight", "bmi": "BMI", "age": "Age", "female": "% women"}
# words used to name a PCA axis from its strongest loadings (positive direction)
AXIS_WORDS = {"height": "taller", "weight": "heavier", "bmi": "stockier", "age": "older", "female": "more women"}
AXIS_WORDS_NEG = {"height": "shorter", "weight": "lighter", "bmi": "leaner", "age": "younger", "female": "more men"}
SYMBOLS = {"Summer": "circle", "Winter": "diamond"}


# ====================================================================== layout
def layout():
    picker = html.Div([
        html.Label("Compare sports (2–4)", htmlFor="sp-compare", className="small text-secondary"),
        dcc.Dropdown(id="sp-compare", multi=True, value=DEFAULT_COMPARE, placeholder="Pick 2–4 sports…",
                     options=[{"label": s, "value": s} for s in DEFAULT_COMPARE]),
        html.Div(id="sp-compare-msg", className="small text-secondary mt-1"),
        dcc.Store(id="sp-colors", data=compare_colors(DEFAULT_COMPARE)),
    ], className="mb-3")
    return html.Div([
        tab_intro("Which sports are alike?",
                  "Sports placed by the athletes they attract (body size, age and share of women), then "
                  "compared side by side. The sidebar's sport filter does not apply here; use the picker or "
                  "click sports on the map."),
        picker,
        chart_card("sp-pca", "Q5.1", "Which sports have similar athletes?",
                   "Similarity map (PCA scatter)", "Correlation",
                   "Close sports have similar athletes. Each axis summarises several measures (named on the "
                   "axis; arrows show which way each measure grows). Circle = Summer, diamond = Winter, size = "
                   "athletes. Click a sport to add or remove it; box/lasso select to compare a group.",
                   height=560, selectable=True),
        dbc.Row([
            dbc.Col(chart_card("sp-radar", "Q5.2", "How do the chosen sports' athlete profiles compare?",
                               "Radar", "Magnitude",
                               "Each spoke is one measure in standard deviations from the average sport (middle "
                               "ring). Points outside the ring are above average.", height=460), lg=5),
            dbc.Col(chart_card("sp-dist", "Q5.3", "How much do the chosen sports' distributions overlap?",
                               "Violins (small multiples)", "Distribution",
                               "One violin per sport for height, weight and age; line = median. Where violins "
                               "overlap, the sports draw similar athletes.", height=460), lg=7),
        ], className="g-3 my-1"),
        data_note("Profiles are recomputed for the sidebar's years, season, sex and countries. Sports with fewer "
                  f"than {MIN_MEASURED} measured athletes are left out. With a Sex filter set, '% women' is "
                  "dropped from the comparison."),
    ])


# ====================================================================== profiles + PCA
def profiles(f: dict) -> pd.DataFrame:
    """Cached per filter: the picker, map, radar and violins all need the same profiles."""
    return _profiles_cached(json.dumps(f, sort_keys=True)).copy()


@lru_cache(maxsize=16)
def _profiles_cached(f_json: str) -> pd.DataFrame:
    f = json.loads(f_json)
    a = da.filter_athletes(f, ignore=IGNORE)
    a = a[~a.is_minor]
    if a.empty:
        return pd.DataFrame()
    body = a.sort_values(["year", "athlete_id"], kind="stable").drop_duplicates(["athlete_id", "sport"], keep="last")
    p = body.groupby("sport").agg(
        n=("athlete_id", "size"), n_measured=("height_cm", "count"), height=("height_cm", "mean"),
        weight=("weight_kg", "mean"), bmi=("bmi", "mean"), female=("is_female", "mean"),
        season=("season", lambda s: s.mode().iat[0]))
    p["age"] = a.groupby("sport").age.mean().astype(float)
    p["female"] = p.female * 100
    return p[p.n_measured >= MIN_MEASURED].dropna(subset=["height", "weight", "bmi", "age"])


def feature_list(f: dict) -> list[str]:
    """'% women' is meaningless (all 0 or 100) when the Sex filter is set."""
    return [k for k in FEATURES if not (k == "female" and f["sex"] != "All")]


def axis_name(loadings: pd.Series, pct: float, idx: int) -> str:
    strong = loadings[loadings.abs() >= 0.35].sort_values(key=abs, ascending=False)
    words = [(AXIS_WORDS if v > 0 else AXIS_WORDS_NEG)[k] for k, v in strong.items()][:4]
    return f"Axis {idx} ({pct:.0f} % of differences): " + (", ".join(words) if words else "mixed") + " →"


def pca_map(f: dict) -> tuple[pd.DataFrame, pd.DataFrame, list[float]]:
    """Returns (coordinates + profile per sport, loadings, explained variance %)."""
    p = profiles(f)
    feats = feature_list(f)
    if len(p) < 3:
        return pd.DataFrame(), pd.DataFrame(), []
    z = StandardScaler().fit_transform(p[feats])
    pca = PCA(n_components=2).fit(z)
    comps = pca.components_.copy()
    for i in range(2):                       # orient each axis so its largest loading is positive
        if comps[i, np.abs(comps[i]).argmax()] < 0:
            comps[i] *= -1
    xy = z @ comps.T
    out = p.assign(x=xy[:, 0], y=xy[:, 1])
    for k, col in zip(feats, z.T):
        out[f"z_{k}"] = col
    loadings = pd.DataFrame(comps.T, index=feats, columns=["x", "y"])
    return out, loadings, list(pca.explained_variance_ratio_ * 100)


def compare_colors(selected: list[str], previous: dict[str, str] | None = None) -> dict[str, str]:
    """Colour follows the sport, not its position: sports that stay keep their colour,
    and a newly added sport takes a colour that is free."""
    previous = previous or {}
    out = {s: previous[s] for s in selected[:MAX_COMPARE] if s in previous}
    free = [c for c in SELECTION_COLORS if c not in out.values()]
    for s in selected[:MAX_COMPARE]:
        if s not in out:
            out[s] = free.pop(0)
    return {s: out[s] for s in selected[:MAX_COMPARE]}


# ====================================================================== Q5.1 map
def fig_pca(f: dict, colors: dict[str, str]) -> go.Figure:
    m, load, var = pca_map(f)
    if m.empty:
        return empty_figure("Too few sports with measured athletes")
    fig = go.Figure()
    # loading arrows (biplot): direction in which each measure increases
    span = max(m.x.abs().max(), m.y.abs().max())
    for feat, r in load.iterrows():
        fig.add_annotation(x=r.x * span * 0.85, y=r.y * span * 0.85, ax=0, ay=0, xref="x", yref="y",
                           axref="x", ayref="y", showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.2,
                           arrowcolor="#c9c8c2", text="")
        fig.add_annotation(x=r.x * span * 0.92, y=r.y * span * 0.92, text=FEATURES[feat], showarrow=False,
                           font=dict(size=10, color=TEXT_MUTED))
    for season in ["Summer", "Winter"]:
        d = m[m.season == season]
        if d.empty:
            continue
        fig.add_trace(go.Scatter(
            x=d.x, y=d.y, mode="markers", name=season, customdata=d.index.tolist(),
            marker=dict(symbol=SYMBOLS[season], size=np.sqrt(d.n) / np.sqrt(m.n.max()) * 34 + 6,
                        color=[colors.get(s, DEEMPHASIS) for s in d.index],
                        opacity=[1 if s in colors else 0.65 for s in d.index],
                        line=dict(color=[TEXT_PRIMARY if s in colors else "white" for s in d.index], width=1)),
            text=[f"<b>{s}</b> ({season})<br>{r.n:,} athletes · {r.height:.0f} cm · {r.weight:.0f} kg<br>"
                  f"BMI {r.bmi:.1f} · age {r.age:.1f} · {r.female:.0f} % women"
                  for s, r in d.iterrows()],
            hovertemplate="%{text}<extra></extra>"))
    # selective labels: the compared sports plus the most extreme sports on each axis
    extremes = set(m.x.nlargest(3).index) | set(m.x.nsmallest(3).index) | set(m.y.nlargest(2).index) \
        | set(m.y.nsmallest(2).index)
    for s in extremes | set(colors):
        if s in m.index:
            r = m.loc[s]
            fig.add_annotation(x=r.x, y=r.y, text=f"<b>{s}</b>" if s in colors else s, showarrow=False,
                               yshift=13, font=dict(size=11 if s in colors else 10,
                                                    color=colors.get(s, TEXT_SECONDARY)))
    fig.update_xaxes(title_text=axis_name(load.x, var[0], 1), zeroline=True, zerolinecolor="#e2e1dc")
    fig.update_yaxes(title_text=axis_name(load.y, var[1], 2), zeroline=True, zerolinecolor="#e2e1dc")
    fig.update_layout(hovermode="closest", dragmode="select", margin=dict(t=40),
                      legend=dict(y=1.0, yanchor="bottom", x=0, itemsizing="constant"),
                      title=dict(text=f"{len(m)} sports · the two axes capture {sum(var):.0f} % of the differences",
                                 x=1, xanchor="right", y=0.99, font=dict(size=11, color=TEXT_MUTED)))
    return fig


# ====================================================================== Q5.2 radar
def fig_radar(f: dict, colors: dict[str, str]) -> go.Figure:
    m, _, _ = pca_map(f)
    chosen = [s for s in colors if s in m.index]
    if not colors:
        return empty_figure("Pick 2–4 sports to compare")
    if not chosen:
        return empty_figure("The chosen sports have too few measured athletes here",
                            f"Each sport needs {MIN_MEASURED}+ measured athletes in the selection.")
    feats = feature_list(f)
    labels = [FEATURES[k] for k in feats] + [FEATURES[feats[0]]]
    fig = go.Figure()
    # the reference: an average sport sits on this ring (z = 0)
    fig.add_trace(go.Scatterpolar(r=[3] * len(labels), theta=labels, mode="lines", name="average sport",
                                  line=dict(color=TEXT_MUTED, dash="dash", width=1.4), hoverinfo="skip"))
    for s in chosen:
        z = [float(np.clip(m.loc[s, f"z_{k}"], -3, 3)) + 3 for k in feats]
        raw = [m.loc[s, k] for k in feats]
        fig.add_trace(go.Scatterpolar(
            r=z + [z[0]], theta=labels, name=s, fill="toself", fillcolor=tint(colors[s], 0.75),
            line=dict(color=colors[s], width=2), marker=dict(size=5), opacity=0.9,
            customdata=[[v, zz - 3] for v, zz in zip(raw + [raw[0]], z + [z[0]])],
            hovertemplate=f"<b>{s}</b><br>%{{theta}}: %{{customdata[0]:.1f}}<br>"
                          "%{customdata[1]:+.1f} SD vs the average sport<extra></extra>"))
    fig.update_layout(
        polar=dict(bgcolor="#fcfcfb",
                   radialaxis=dict(range=[0, 6], tickvals=[1, 2, 3, 4, 5], ticktext=["−2", "−1", "avg", "+1", "+2"],
                                   tickfont=dict(size=9, color=TEXT_MUTED), gridcolor="#e9e8e4", angle=90),
                   angularaxis=dict(gridcolor="#e9e8e4", tickfont=dict(size=11))),
        legend=dict(y=-0.05, yanchor="top", x=0.5, xanchor="center", orientation="h"),
        margin=dict(t=30, b=40, l=40, r=40))
    return fig


# ====================================================================== Q5.3 distributions
DIST_MEASURES = [("height_cm", "Height (cm)"), ("weight_kg", "Weight (kg)"), ("age", "Age (years)")]


def fig_dist(f: dict, colors: dict[str, str]) -> go.Figure:
    a = da.filter_athletes(f, ignore=IGNORE)
    chosen = [s for s in colors if s in set(a.sport)]
    if not colors:
        return empty_figure("Pick 2–4 sports to compare")
    if not chosen:
        return empty_figure("The chosen sports did not take place in this selection",
                            "Widen the filters or pick other sports.")
    body = a.sort_values(["year", "athlete_id"], kind="stable").drop_duplicates(["athlete_id", "sport"], keep="last")
    fig = make_subplots(rows=1, cols=3, subplot_titles=[t for _, t in DIST_MEASURES], horizontal_spacing=0.07)
    for col, (measure, title) in enumerate(DIST_MEASURES, start=1):
        src = a if measure == "age" else body
        for s in chosen:
            v = src.loc[src.sport == s, measure].dropna().astype(float)
            if len(v) < 5:
                continue
            fig.add_trace(go.Violin(
                y=v, x=[s] * len(v), name=s, legendgroup=s, showlegend=(col == 1),
                line=dict(color=colors[s], width=1.3), fillcolor=tint(colors[s], 0.6), points=False,
                meanline=dict(visible=False), box=dict(visible=False), spanmode="hard", width=0.85,
                hoveron="violins", hoverinfo="skip"), row=1, col=col)
            fig.add_trace(go.Scatter(
                x=[s], y=[v.median()], mode="markers", showlegend=False,
                marker=dict(symbol="line-ew-open", size=22, color=colors[s], line=dict(width=2.5)),
                hovertemplate=f"<b>{s}</b><br>{title}: median %{{y:.1f}}<br>n = {len(v):,}<extra></extra>"),
                row=1, col=col)
    fig.update_xaxes(showticklabels=False, showgrid=False)
    fig.update_layout(violinmode="overlay", hovermode="closest", margin=dict(t=50),
                      legend=dict(y=-0.05, yanchor="top", x=0.5, xanchor="center", orientation="h"))
    for ann in fig.layout.annotations:
        ann.font = dict(size=12, color=TEXT_SECONDARY)
    return fig


# ====================================================================== selection logic
def update_selection(current: list[str], valid: set[str], trigger: str | None,
                     click_sport: str | None = None, lasso_sports: list[str] | None = None) -> tuple[list[str], str]:
    """Returns (new compare list, message). Keeps 2-4 valid sports in a stable order."""
    sel = [s for s in (current or []) if s in valid]
    msg = ""
    if trigger == "click" and click_sport in valid:
        if click_sport in sel:
            sel.remove(click_sport)
        else:
            sel.append(click_sport)
    elif trigger == "lasso" and lasso_sports:
        sel = [s for s in lasso_sports if s in valid]
    if len(sel) > MAX_COMPARE:
        dropped = sel[:-MAX_COMPARE] if trigger == "click" else sel[MAX_COMPARE:]
        sel = sel[-MAX_COMPARE:] if trigger == "click" else sel[:MAX_COMPARE]
        msg = f"At most {MAX_COMPARE} sports: left out {', '.join(dropped)}."
    if len(sel) < 2:
        msg = msg or "Pick at least 2 sports to compare."
    return sel, msg


@tab_callback(TAB_ID, Output("sp-compare", "value"), Output("sp-compare", "options"), Output("sp-compare-msg", "children"),
          Output("sp-colors", "data"),
          Input("filters", "data"), Input("sp-compare", "value"), Input("sp-pca", "clickData"),
          Input("sp-pca", "selectedData"), State("sp-compare", "value"), State("sp-colors", "data"))
def sync_compare(f, picked, click, selected, current, colors):
    p = profiles(f)
    valid = set(p.index)
    options = [{"label": f"{s} ({p.loc[s, 'season']})", "value": s} for s in sorted(valid)]
    prop = ctx.triggered[0]["prop_id"] if ctx.triggered else ""
    if prop == "sp-pca.clickData":
        point = ((click or {}).get("points") or [{}])[0]
        sel, msg = update_selection(current, valid, "click", click_sport=point.get("customdata"))
    elif prop == "sp-pca.selectedData":
        hit = {pt.get("customdata") for pt in (selected or {}).get("points", [])} & valid
        # when a lasso catches more than four sports, the biggest ones are kept
        sel, msg = update_selection(current, valid, "lasso",
                                    lasso_sports=sorted(hit, key=lambda s: -p.loc[s, "n"]))
    else:   # picker edited, or filters changed
        sel, msg = update_selection(picked, valid, None)
    return sel, options, msg, compare_colors(sel, colors)


@tab_callback(TAB_ID, Output("sp-pca", "figure"), Input("filters", "data"), Input("sp-colors", "data"))
def update_pca(f, colors):
    return fig_pca(f, colors or {})


@tab_callback(TAB_ID, Output("sp-radar", "figure"), Input("filters", "data"), Input("sp-colors", "data"))
def update_radar(f, colors):
    return fig_radar(f, colors or {})


@tab_callback(TAB_ID, Output("sp-dist", "figure"), Input("filters", "data"), Input("sp-colors", "data"))
def update_dist(f, colors):
    return fig_dist(f, colors or {})

"""Reusable layout pieces: chart cards, tab headers, filter controls."""
from __future__ import annotations

import logging

from dash import dcc, html
import dash_ag_grid as dag
import dash_bootstrap_components as dbc

from .theme import GRAPH_CONFIG, GRAPH_CONFIG_SELECT, MEDAL_COLORS, MEDAL_ORDER, empty_figure

FT_URL = "https://ft-interactive.github.io/visual-vocabulary/"


def chart_card(graph_id: str, title: str, chart: str, ft_category: str,
               how_to_read: str | None = None, height: int | None = 380, selectable: bool = False,
               controls=None) -> dbc.Card:
    """One chart = one card: a plain title on top, chart, then a 'how to read' hint.

    The analytical question is stated once per tab (tab_intro); the charts are the
    evidence for it, so they carry descriptive titles, not questions of their own.

    `ft_category` is the Financial Times Visual Vocabulary category the chart
    belongs to (shown as a badge so the chart choice is always explained).
    """
    header = html.Div([
        html.Div(html.Span(title, className="q-text")),
        html.Div([
            html.Span(chart, className="chart-name"),
            html.A(ft_category, href=FT_URL, target="_blank", className="ft-badge",
                   title="Chart category in the FT Visual Vocabulary"),
        ], className="chart-meta"),
    ], className="card-head")

    body = [header]
    if controls is not None:
        body.append(html.Div(controls, className="card-controls"))
    body.append(dcc.Loading(
        dcc.Graph(id=graph_id, figure=empty_figure("Loading chart…", ""),
                  config=GRAPH_CONFIG_SELECT if selectable else GRAPH_CONFIG,
                  # height=None: the figure sets its own height (e.g. one row per sport)
                  style={"height": f"{height}px"} if height else {}),
        type="dot", color="#2a78d6", delay_show=300))
    if how_to_read:
        body.append(html.Div([html.Span("How to read: ", className="fw-semibold"), how_to_read],
                             className="how-to-read"))
    return dbc.Card(dbc.CardBody(body), className="chart-card")


def tab_intro(title: str, note: str | None = None, qid: str | None = None, section: bool = False) -> html.Div:
    """Tab header. With `qid`, the title is an analytical question (Q1-Q5).
    `note` = only a rule the reader must know (e.g. a filter that does not apply here), shown with an ⓘ.
    `section=True` starts a second question further down the same tab."""
    heading = [html.Span(qid, className="q-id q-id-lg"), title] if qid else title
    children = [html.H2(heading, className="tab-title" + (" tab-question" if qid else ""))]
    if note:
        children.append(html.P([html.Span("ⓘ ", className="text-secondary"), note], className="tab-note"))
    return html.Div(children, className="tab-intro" + (" q-section" if section else ""))


def data_note(text: str) -> html.Div:
    return html.Div(text, className="data-note")


def segmented(id_: str, options: list[str], value: str, labels: dict | None = None) -> dbc.RadioItems:
    """Button-group style single choice (Season, Sex, metric switches)."""
    labels = labels or {}
    return dbc.RadioItems(
        id=id_, value=value, inline=True,
        options=[{"label": labels.get(o, o), "value": o} for o in options],
        className="btn-group segmented", inputClassName="btn-check",
        labelClassName="btn btn-outline-secondary btn-sm", labelCheckedClassName="active",
    )


def data_grid(id_: str, page_size: int = 10, row_selection: str | None = None,
              columns: list[dict] | None = None, server_side: bool = False) -> dag.AgGrid:
    """Sortable, filterable, paged table (AG Grid; replaces the deprecated DataTable).

    server_side=True uses AG Grid's infinite row model: the grid asks the server for one page
    at a time (getRowsRequest), so sorting and filtering run over ALL matching rows, not only
    the rows that were sent to the browser."""
    options = {"pagination": True, "paginationPageSize": page_size, "animateRows": False,
               "domLayout": "autoHeight"}
    extra = {}
    if server_side:
        options.update({"cacheBlockSize": page_size, "maxBlocksInCache": 20,
                        "paginationPageSizeSelector": False})
        extra = {"rowModelType": "infinite"}
    if row_selection:
        options["rowSelection"] = {"mode": "singleRow" if row_selection == "single" else "multiRow",
                                   "enableClickSelection": True, "checkboxes": False}
    if not server_side:
        extra = {"rowData": []}
    return dag.AgGrid(id=id_, columnDefs=columns or [], className="ag-theme-quartz", **extra,
                      getRowId="params.data.athlete_id",
                      defaultColDef={"sortable": True, "filter": True, "resizable": True, "flex": 1,
                                     "minWidth": 90},
                      dashGridOptions=options, style={"width": "100%"})


def medal_badges(counts: dict) -> html.Span:
    """Medal counts as coloured badges that always carry a text label (G/S/B):
    metallic colours alone are not distinguishable enough (design decision)."""
    badges = [html.Span(f"{m[0]} {counts[m]}", className="medal-badge",
                        style={"backgroundColor": MEDAL_COLORS[m]}, title=f"{counts[m]} {m.lower()}")
              for m in MEDAL_ORDER if counts.get(m, 0)]
    return html.Span(badges or "–", className="text-nowrap")


def tab_callback(tab_id: str, *deps, **kwargs):
    """Register a Dash callback that only does its work while `tab_id` is the visible tab.

    It adds Input("tabs", "active_tab") after the callback's own Inputs. While another tab
    is shown the update is skipped; switching to the tab fires it with the current filters,
    so nothing goes stale. The undecorated function is returned unchanged, so tests and
    scripts can still call it directly.
    """
    from dash import Input as _Input, State as _State, callback as _callback
    from dash.exceptions import PreventUpdate

    flat = []
    for d in deps:
        flat.extend(d if isinstance(d, (list, tuple)) else [d])
    outputs = [d for d in flat if not isinstance(d, (_Input, _State))]
    inputs = [d for d in flat if isinstance(d, _Input)]
    states = [d for d in flat if isinstance(d, _State)]
    pos = len(inputs)                                  # where the active tab arrives in *args
    single_figure = len(outputs) == 1 and getattr(outputs[0], "component_property", None) == "figure"

    def deco(fn):
        def dash_fn(*args):
            if args[pos] != tab_id:
                raise PreventUpdate
            try:
                return fn(*args[:pos], *args[pos + 1:])
            except PreventUpdate:
                raise
            except Exception:                          # safety net: one chart fails, the page lives
                logging.getLogger("dashboard").exception("callback %s failed", fn.__name__)
                if single_figure:
                    return empty_figure("This chart could not be drawn",
                                        "Try other filters; the error was logged on the server.")
                raise
        dash_fn.__name__ = f"{fn.__name__}_on_{tab_id}"
        _callback(*outputs, *inputs, _Input("tabs", "active_tab"), *states, **kwargs)(dash_fn)
        return fn
    return deco

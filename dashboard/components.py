"""Reusable layout pieces: chart cards, tab headers, filter controls."""
from __future__ import annotations

from dash import dcc, html
import dash_ag_grid as dag
import dash_bootstrap_components as dbc

from .theme import GRAPH_CONFIG, GRAPH_CONFIG_SELECT, empty_figure

FT_URL = "https://ft-interactive.github.io/visual-vocabulary/"


def chart_card(graph_id: str, qid: str, question: str, chart: str, ft_category: str,
               how_to_read: str, height: int = 380, selectable: bool = False,
               controls=None) -> dbc.Card:
    """One chart = one card: question on top, chart, then a 'how to read' hint.

    `ft_category` is the Financial Times Visual Vocabulary category the chart
    belongs to (shown as a badge so the chart choice is always explained).
    """
    header = html.Div([
        html.Div([
            html.Span(qid, className="q-id"),
            html.Span(question, className="q-text"),
        ]),
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
        dcc.Graph(id=graph_id, figure=empty_figure("Chart built in Phase 5", "Layout preview"),
                  config=GRAPH_CONFIG_SELECT if selectable else GRAPH_CONFIG,
                  style={"height": f"{height}px"}),
        type="dot", color="#2a78d6", delay_show=300))
    body.append(html.Div([html.Span("How to read: ", className="fw-semibold"), how_to_read],
                         className="how-to-read"))
    return dbc.Card(dbc.CardBody(body), className="chart-card")


def tab_intro(theme_question: str, description: str) -> html.Div:
    return html.Div([
        html.H2(theme_question, className="tab-title"),
        html.P(description, className="tab-desc"),
    ], className="tab-intro")


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


def data_grid(id_: str, page_size: int = 10, row_selection: str | None = None) -> dag.AgGrid:
    """Sortable, filterable, paged table (AG Grid; replaces the deprecated DataTable)."""
    options = {"pagination": True, "paginationPageSize": page_size, "animateRows": False,
               "domLayout": "autoHeight"}
    if row_selection:
        options["rowSelection"] = {"mode": "singleRow" if row_selection == "single" else "multiRow",
                                   "enableClickSelection": True, "checkboxes": False}
    return dag.AgGrid(id=id_, rowData=[], columnDefs=[], className="ag-theme-quartz",
                      defaultColDef={"sortable": True, "filter": True, "resizable": True, "flex": 1,
                                     "minWidth": 90},
                      dashGridOptions=options, style={"width": "100%"})

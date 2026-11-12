"""Tab 1, Overview: what is in the data? (Q1.1-Q1.4)"""
from dash import html
import dash_bootstrap_components as dbc

from ..components import chart_card, data_grid, tab_intro

TAB_ID = "overview"
LABEL = "Overview"

KPIS = [("kpi-athletes", "Athletes"), ("kpi-countries", "Countries"), ("kpi-sports", "Sports"),
        ("kpi-events", "Events"), ("kpi-medals", "Medals awarded")]


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
        html.Div(html.Div([html.Span("Q1.1", className="q-id"),
                           html.Span("How big are the Games in the current selection?", className="q-text")]),
                 className="card-head mb-2"),
        dbc.Row([kpi_tile(i, l) for i, l in KPIS], className="g-2 mb-3"),
        dbc.Row([
            dbc.Col(chart_card(
                "ov-participation", "Q1.2", "How has participation grown, and how was it split between women and men?",
                "Stacked area", "Change v Time · Part to whole",
                "Total height = athletes at each Games; the bands show the women/men split. "
                "Summer and Winter are separate panels."), lg=7),
            dbc.Col(chart_card(
                "ov-treemap", "Q1.3", "Which sports and events attract the most athletes?",
                "Treemap", "Part to whole",
                "Rectangle area = athlete entries. Click a sport to zoom into its events, click the "
                "top bar to zoom out."), lg=5),
        ], className="g-3 mb-3"),
        dbc.Card(dbc.CardBody([
            html.Div([html.Span("Q1.4", className="q-id"),
                      html.Span("Who is a specific athlete, and what did they achieve?", className="q-text")],
                     className="card-head"),
            dbc.Input(id="ov-search", placeholder="Search an athlete by name, e.g. 'Phelps' or 'Comăneci'…",
                      type="search", debounce=True, className="mb-2"),
            data_grid("ov-athlete-table", page_size=10, row_selection="single"),
            html.Div(id="ov-athlete-card", className="mt-2"),
        ]), className="chart-card"),
    ])

"""Tab 3, Athlete Physiques: what body does each sport select for? (Q3.1-Q3.4)"""
from dash import html
import dash_bootstrap_components as dbc

from ..components import chart_card, data_grid, data_note, segmented, tab_intro

TAB_ID = "physiques"
LABEL = "Physiques"

MEASURES = {"height_cm": "Height (cm)", "weight_kg": "Weight (kg)", "bmi": "BMI", "age": "Age (years)"}


def layout():
    return html.Div([
        tab_intro("What body does each sport select for?",
                  "Height, weight, BMI and age compared across sports, over time, and between medallists "
                  "and the rest of the field."),
        html.Div([html.Span("Measure", className="small text-secondary me-2"),
                  segmented("ph-measure", list(MEASURES), "height_cm", MEASURES)], className="mb-2"),
        chart_card("ph-boxes", "Q3.1", "How do body measures differ between sports, for women and men?",
                   "Box plots, ordered by median", "Distribution · Ranking",
                   "Each row is a sport, sorted by median. The box holds the middle 50 % of athletes. "
                   "Click a sport to drive the charts below.", height=900),
        dbc.Row([
            dbc.Col(chart_card("ph-density", "Q3.2", "Where does a sport sit in the overall height × weight space?",
                               "2D density + overlay", "Correlation · Distribution",
                               "Gray contours = all athletes; dots = the selected sport. Drag a box or lasso "
                               "to list the athletes inside.", height=440, selectable=True), lg=6),
            dbc.Col(chart_card("ph-trend", "Q3.3", "Have athletes in a sport changed over the decades?",
                               "Trend with interquartile band", "Change v Time (fan)",
                               "Line = median per Games, band = middle 50 %. Hover shows n; early Games "
                               "have few measured athletes.", height=440), lg=6),
        ], className="g-3 my-1"),
        dbc.Row([
            dbc.Col(chart_card("ph-violin", "Q3.4", "Do medallists differ physically from other competitors?",
                               "Split violin", "Distribution",
                               "Left half = medallists, right half = everyone else, in the selected sport.",
                               height=400), lg=6),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.Div([html.Span("Selection", className="q-id"),
                          html.Span("Athletes inside the box/lasso selection", className="q-text")],
                         className="card-head"),
                data_grid("ph-selection-table", page_size=10),
            ]), className="chart-card"), lg=6),
        ], className="g-3 my-1"),
        data_note("Height and weight are known for 93 % of athletes from 1960–2016, but for only 6–30 % before "
                  "1960 and 44 % at 2020/2022. Every chart reports how many athletes it is based on."),
    ])

"""Tab 2, Countries & Medals: who wins, and has that changed? (Q2.1-Q2.6)"""
from dash import dcc, html
import dash_bootstrap_components as dbc

from ..components import chart_card, data_note, segmented, tab_intro

TAB_ID = "countries"
LABEL = "Countries & Medals"


def layout():
    map_controls = dbc.Row([
        dbc.Col(segmented("co-map-metric", ["total", "per_million", "per_gdp"], "total",
                          {"total": "Medals (total)", "per_million": "per million people",
                           "per_gdp": "per $100bn GDP"}), width="auto"),
        dbc.Col(segmented("co-map-mode", ["range", "games"], "range",
                          {"range": "Whole year range", "games": "One Games at a time ▶"}), width="auto"),
    ], className="g-2")
    heat_controls = segmented("co-heat-metric", ["count", "index"], "count",
                              {"count": "Medal count", "index": "Specialisation index"})
    sankey_controls = html.Div([
        html.Span("Minimum athletes per flow", className="small text-secondary me-2"),
        dcc.Slider(id="co-sankey-min", min=2, max=50, step=1, value=10,
                   marks={2: "2", 10: "10", 25: "25", 50: "50"}, tooltip={"placement": "bottom"}),
    ])
    return html.Div([
        tab_intro("Who wins, and has that changed?",
                  "Medal geography, the rise and fall of sporting powers, whether success is just size and "
                  "wealth, national specialisations, home advantage and athletes changing teams. "
                  "Countries chosen in the sidebar are highlighted here, not filtered out."),
        chart_card("co-map", "Q2.1", "Where in the world are medals won?",
                   "Proportional-symbol map · choropleth", "Spatial",
                   "Totals are drawn as circles (area = medals); rates switch to a shaded map. Rates exist "
                   "from 1960 on and only for present-day countries.", height=460, controls=map_controls),
        dbc.Row([
            dbc.Col(chart_card("co-bump", "Q2.2", "Which countries dominated which eras?",
                               "Bump chart", "Ranking",
                               "Each line is a country's place in the medal table (1 = top). Gray lines are "
                               "context; selected countries are coloured. Click a line to select it."), lg=7),
            dbc.Col(chart_card("co-scatter", "Q2.3", "Is success just a matter of size and wealth?",
                               "Bubble scatter (log-log)", "Correlation",
                               "x = GDP, y = medals, bubble = population. Countries above the trend line win "
                               "more than their economy predicts."), lg=5),
        ], className="g-3 my-1"),
        chart_card("co-heatmap", "Q2.4", "In which sports does each country specialise?",
                   "XY-heatmap", "Correlation",
                   "Specialisation index = country's share of medals in a sport ÷ its share of all medals. "
                   "Above 1 means the country is unusually strong in that sport.", height=520,
                   controls=heat_controls),
        dbc.Row([
            dbc.Col(chart_card("co-host", "Q2.5", "Do host countries win more at their home Games?",
                               "Dumbbell", "Distribution (dot-plot)",
                               "Gray dot = usual medal share (two Games before and after); coloured dot = "
                               "share as host. The line is the home boost.", height=460), lg=5),
            dbc.Col(chart_card("co-sankey", "Q2.6", "How do athletes move between national teams?",
                               "Sankey", "Flow",
                               "Left = team at one Games, right = team at the athlete's next Games. Band "
                               "width = athletes. Shows break-ups (USSR), reunification (Germany) and "
                               "naturalisation.", height=460, controls=sankey_controls), lg=7),
        ], className="g-3 my-1"),
        data_note("Medal totals follow the official medal table (team medals count once), without Art "
                  "Competitions. Population and GDP: World Bank, 1960 onwards; historic teams such as the "
                  "USSR or East Germany have no World Bank data."),
    ])

"""Tab 4, Gender Participation: how did women enter the Games? (Q4.1-Q4.4)"""
from dash import html
import dash_bootstrap_components as dbc

from ..components import chart_card, data_note, tab_intro

TAB_ID = "gender"
LABEL = "Gender"


def layout():
    return html.Div([
        tab_intro("How did women enter the Games?",
                  "From 40 women (2 % of athletes) in 1900 to 48 % in 2020: the overall trend, the sports and countries "
                  "behind it, and the age structure of women and men. The sidebar's Sex filter does not "
                  "apply here, because this tab compares the sexes."),
        chart_card("ge-share", "Q4.1", "How did women's share of athletes evolve?",
                   "Annotated line", "Change v Time",
                   "Share of women among all athletes at each Games, Summer and Winter. Dashed line = parity "
                   "(50 %). Labels mark milestones.", height=380),
        chart_card("ge-heatmap", "Q4.2", "Which sports opened to women early or late, and which remain unbalanced?",
                   "XY-heatmap, diverging scale", "Correlation · Deviation",
                   "Violet = mostly women, aqua = mostly men, gray = balanced; blank = sport not held. "
                   "Click a cell to follow that sport.", height=760),
        dbc.Row([
            dbc.Col(chart_card("ge-spine", "Q4.3", "Which countries send balanced teams?",
                               "Spine chart", "Deviation",
                               "Each bar is one team split around 50 %. Bars reaching further right have more "
                               "men; further left, more women.", height=620), lg=6),
            dbc.Col(chart_card("ge-pyramid", "Q4.4", "Do female and male Olympians differ in age structure?",
                               "Population pyramid", "Distribution",
                               "Women to the left, men to the right; each bar is one year of age, as % of "
                               "that sex.", height=620), lg=6),
        ], className="g-3 my-1"),
        data_note("Counts are distinct athletes per Games. An athlete in two sports counts once in totals and "
                  "once in each sport."),
    ])

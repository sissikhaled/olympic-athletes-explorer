"""Tab 5, Sport Comparison: which sports are alike? (Q5.1-Q5.3)"""
from dash import dcc, html
import dash_bootstrap_components as dbc

from ..components import chart_card, data_note, tab_intro

TAB_ID = "sports"
LABEL = "Sport Comparison"
DEFAULT_COMPARE = ["Basketball", "Artistic Gymnastics", "Weightlifting"]
MAX_COMPARE = 4


def layout():
    picker = html.Div([
        html.Label("Compare sports (2–4)", htmlFor="sp-compare", className="small text-secondary"),
        dcc.Dropdown(id="sp-compare", multi=True, value=DEFAULT_COMPARE, placeholder="Pick 2–4 sports…"),
        html.Div(id="sp-compare-msg", className="small text-secondary mt-1"),
    ], className="mb-3")
    return html.Div([
        tab_intro("Which sports are alike?",
                  "Sports placed by the athletes they attract (body size, age and share of women), then "
                  "compared side by side. The sidebar's sport filter does not apply here; use the picker."),
        picker,
        chart_card("sp-pca", "Q5.1", "Which sports have similar athletes?",
                   "Similarity map (PCA scatter)", "Correlation",
                   "Close sports have similar athletes. Circle = Summer, diamond = Winter, size = number of "
                   "athletes. Click or lasso sports to compare them.", height=520, selectable=True),
        dbc.Row([
            dbc.Col(chart_card("sp-radar", "Q5.2", "How do the chosen sports' athlete profiles compare?",
                               "Radar", "Magnitude",
                               "Each axis is a standardised measure (0 = average sport). A larger shape means "
                               "above-average values.", height=440), lg=5),
            dbc.Col(chart_card("sp-dist", "Q5.3", "How much do the chosen sports' distributions overlap?",
                               "Overlaid violins (small multiples)", "Distribution",
                               "One violin per sport for height, weight and age. Overlap means the sports "
                               "draw similar athletes.", height=440), lg=7),
        ], className="g-3 my-1"),
        data_note("Sport profiles are recomputed for the sidebar's years, season, sex and countries. Sports "
                  "with fewer than 30 measured athletes in the selection are left out of the map."),
    ])

"""Page frame: header, global filter sidebar, tabs, About modal, footer."""
from dash import dcc, html
import dash_bootstrap_components as dbc

from . import data_access as da
from .components import segmented
from .tabs import countries, gender, overview, physiques, sports

TABS = [overview, countries, physiques, gender, sports]


def _year_marks() -> dict:
    # Dash 4 always draws the min/max marks, so the ends are 1896 and 2022 themselves
    return {y: {"label": str(y)} for y in [1896, 1920, 1940, 1960, 1980, 2000, 2022]}


def sidebar() -> html.Div:
    f = da.DEFAULT_FILTERS
    return html.Div([
        html.Div("Filters", className="sidebar-title"),
        html.Div("Apply to every tab (see each tab's note for exceptions).", className="sidebar-sub"),

        html.Label("Years", className="filter-label"),
        html.Div(id="flt-years-text", className="filter-value"),
        dcc.RangeSlider(id="flt-years", min=da.YEAR_MIN, max=da.YEAR_MAX, step=2, value=f["years"],
                        marks=_year_marks(), allowCross=False, pushable=0,
                        tooltip={"placement": "bottom", "always_visible": False}),

        html.Label("Season", className="filter-label"),
        segmented("flt-season", ["Both", "Summer", "Winter"], f["season"]),

        html.Label("Sex", className="filter-label"),
        segmented("flt-sex", ["All", "Female", "Male"], f["sex"], {"Female": "Women", "Male": "Men"}),

        html.Label("Sports", htmlFor="flt-sports", className="filter-label"),
        dcc.Dropdown(id="flt-sports", multi=True, value=f["sports"], placeholder="All sports",
                     options=da.sport_options(f["season"], f["hide_minor"])),
        dbc.Checkbox(id="flt-hide-minor", value=f["hide_minor"], className="mt-1 small",
                     label="Hide minor sports (< 100 athletes)"),

        html.Label("Countries", htmlFor="flt-countries", className="filter-label"),
        dcc.Dropdown(id="flt-countries", multi=True, value=f["countries"], placeholder="All countries",
                     options=da.country_options()),

        dbc.Button("Reset filters", id="flt-reset", color="secondary", outline=True, size="sm",
                   className="mt-3 w-100"),
        html.Div(id="flt-summary", className="filter-summary"),
    ], className="sidebar")


def about_modal() -> dbc.Modal:
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("About this dashboard")),
        dbc.ModalBody([
            html.H6("Data sources"),
            html.Ul([
                html.Li([html.B("126 Years of Historical Olympic Dataset"), " by Muhammad Ehsan (Kaggle), scraped "
                         "from Olympedia.org, 1896–2022. License CC BY 4.0. ",
                         html.A("Kaggle page", target="_blank",
                                href="https://www.kaggle.com/datasets/muhammadehsan02/126-years-of-historical-olympic-dataset")]),
                html.Li([html.B("World Bank Open Data"), ": population (SP.POP.TOTL) and GDP in current US$ "
                         "(NY.GDP.MKTP.CD), 1960–2024. License CC BY 4.0. ",
                         html.A("data.worldbank.org", href="https://data.worldbank.org", target="_blank")]),
            ]),
            html.H6("Main preparation decisions"),
            html.Ul([
                html.Li("Art Competitions and the unofficial 1906 Games are excluded; the 1956 Equestrian "
                        "events count as part of Melbourne 1956."),
                html.Li("Team medals count once per country per event, as in official medal tables."),
                html.Li("Historic teams (USSR, East/West Germany, Unified Team…) are kept as they competed."),
                html.Li("Weight ranges use the midpoint; birth years without a date give an approximate age."),
            ]),
            html.P(["Chart types follow the ",
                    html.A("FT Visual Vocabulary", href="https://ft-interactive.github.io/visual-vocabulary/",
                           target="_blank"),
                    "; each chart's category is shown on its card."], className="mb-0"),
        ]),
    ], id="about-modal", size="lg", is_open=False)


def serve_layout() -> html.Div:
    header = html.Div([
        html.Div([
            html.Span("Olympic Athletes Explorer", className="app-title"),
            html.Span("126 years of Olympic history · 1896–2022", className="app-sub"),
        ]),
        dbc.Button("About & sources", id="about-open", color="link", size="sm"),
    ], className="app-header")

    tabs = dbc.Tabs([dbc.Tab(t.layout(), label=t.LABEL, tab_id=t.TAB_ID) for t in TABS],
                    id="tabs", active_tab=overview.TAB_ID, className="main-tabs")

    footer = html.Div([
        "Sources: Olympedia.org via Kaggle (M. Ehsan, CC BY 4.0) · World Bank Open Data (CC BY 4.0). ",
        "Built with Plotly Dash.",
    ], className="app-footer")

    return html.Div([
        dcc.Store(id="filters", data=da.DEFAULT_FILTERS),
        header,
        html.Div([sidebar(), html.Main([tabs, footer], className="content")], className="app-body"),
        about_modal(),
    ])

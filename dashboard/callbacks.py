"""Global callbacks: sidebar -> filter store, reset, dependent options, About."""
from dash import Input, Output, State, callback, ctx, html, no_update

from . import data_access as da

FILTER_INPUTS = ["flt-years", "flt-season", "flt-sex", "flt-sports", "flt-hide-minor", "flt-countries"]


@callback(
    Output("filters", "data"),
    [Input(i, "value") for i in FILTER_INPUTS],
)
def update_filter_store(years, season, sex, sports, hide_minor, countries):
    """Single source of truth: every chart reads the filters from this store."""
    return {
        "years": list(years or da.DEFAULT_FILTERS["years"]),
        "season": season or "Both",
        "sex": sex or "All",
        "sports": sports or [],
        "hide_minor": bool(hide_minor),
        "countries": countries or [],
    }


@callback(
    [Output(i, "value", allow_duplicate=True) for i in FILTER_INPUTS],
    Input("flt-reset", "n_clicks"),
    prevent_initial_call=True,
)
def reset_filters(_):
    f = da.DEFAULT_FILTERS
    return f["years"], f["season"], f["sex"], f["sports"], f["hide_minor"], f["countries"]


@callback(
    Output("flt-sports", "options"),
    Output("flt-sports", "value", allow_duplicate=True),
    Input("flt-season", "value"),
    Input("flt-hide-minor", "value"),
    State("flt-sports", "value"),
    prevent_initial_call=True,
)
def update_sport_options(season, hide_minor, selected):
    """Sport list follows the season and minor-sport switch; drop picks that disappear."""
    options = da.sport_options(season, hide_minor)
    valid = {o["value"] for o in options}
    kept = [s for s in (selected or []) if s in valid]
    return options, (kept if kept != (selected or []) else no_update)


@callback(Output("flt-years-text", "children"), Input("flt-years", "value"))
def show_years(years):
    return f"{years[0]} – {years[1]}"


@callback(Output("flt-summary", "children"), Input("filters", "data"))
def show_summary(f):
    s = da.summary(f)
    if s["athletes"] == 0:
        return html.Span("No athletes match these filters.", className="text-danger")
    return [html.B(f"{s['athletes']:,}"), " athletes · ", html.B(s["games"]), " Games · ",
            html.B(s["countries"]), " countries · ", html.B(s["sports"]), " sports"]


@callback(Output("about-modal", "is_open"), Input("about-open", "n_clicks"),
          State("about-modal", "is_open"), prevent_initial_call=True)
def toggle_about(_, is_open):
    return not is_open if ctx.triggered_id == "about-open" else is_open

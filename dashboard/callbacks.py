"""Global callbacks: filter panel -> filter store, reset, dependent options, panel toggle, About."""
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


@callback(Output("filter-panel", "className"), Input("filter-open", "n_clicks"),
          Input("filter-close", "n_clicks"), State("filter-panel", "className"), prevent_initial_call=True)
def toggle_filter_panel(_open, _close, current):
    return panel_class(ctx.triggered_id, current)


def panel_class(trigger: str | None, current: str | None) -> str:
    """The round button toggles the panel; the × closes it."""
    is_open = "open" in (current or "").split()
    is_open = False if trigger == "filter-close" else not is_open
    return "filter-panel open" if is_open else "filter-panel"


def active_filter_count(f: dict) -> int:
    d = da.DEFAULT_FILTERS
    return sum([f["years"] != d["years"], f["season"] != d["season"], f["sex"] != d["sex"],
                bool(f["sports"]) or f["hide_minor"] != d["hide_minor"], bool(f["countries"])])


@callback(Output("filter-count", "children"), Output("filter-count", "className"), Input("filters", "data"))
def show_filter_count(f):
    n = active_filter_count(f)
    return (str(n), "fab-badge") if n else ("", "fab-badge d-none")


@callback(Output("about-modal", "is_open"), Input("about-open", "n_clicks"),
          State("about-modal", "is_open"), prevent_initial_call=True)
def toggle_about(_, is_open):
    return not is_open if ctx.triggered_id == "about-open" else is_open


# Per-tab exceptions to the global filters (see docs/analytical_questions.md §4.1)
TAB_EXCEPTIONS = {
    "countries": "Selected countries are highlighted, not filtered out. Medal totals do not split by sex.",
    "gender": "The Sex filter does not apply on this tab (it compares women and men).",
    "sports": "The Sports filter does not apply on this tab; use the sport picker.",
}


def filter_chips(f: dict) -> list[str]:
    d = da.DEFAULT_FILTERS
    chips = [f"{f['years'][0]}–{f['years'][1]}"]
    chips.append("Summer and Winter" if f["season"] == "Both" else f"{f['season']} Games")
    chips.append({"All": "Women and men", "Female": "Women only", "Male": "Men only"}[f["sex"]])
    if f["sports"]:
        chips.append(f["sports"][0] if len(f["sports"]) == 1 else f"{len(f['sports'])} sports")
    elif f["hide_minor"] != d["hide_minor"]:
        chips.append("incl. minor sports")
    if f["countries"]:
        chips.append(f["countries"][0] if len(f["countries"]) == 1 else f"{len(f['countries'])} countries")
    return chips


@callback(Output("filter-bar", "children"), Input("filters", "data"), Input("tabs", "active_tab"))
def show_filter_bar(f, tab):
    parts = [html.Span("Showing: ", className="fw-semibold")]
    for c in filter_chips(f):
        parts.append(html.Span(c, className="filter-chip"))
    if f != da.DEFAULT_FILTERS:
        parts.append(html.Span("(filtered)", className="text-secondary small ms-1"))
    note = TAB_EXCEPTIONS.get(tab)
    if note:
        parts.append(html.Div([html.Span("ⓘ ", className="text-secondary"), note], className="filter-note"))
    return parts

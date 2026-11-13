"""Visual design system: every color and chart default lives here.

Colors were validated with the dataviz palette validator (colorblind
separation, normal-vision distance, lightness, chroma); see
docs/analytical_questions.md §6. Charts import these constants instead of
writing hex codes, so a meaning always has the same color on every tab.
"""
import plotly.graph_objects as go
import plotly.io as pio

FONT_FAMILY = "Inter, -apple-system, 'Segoe UI', Roboto, sans-serif"

# ---------------------------------------------------------------- surfaces and text
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
TEXT_MUTED = "#8a8984"
GRID = "#e9e8e4"
DEEMPHASIS = "#b8b7b1"          # unselected items (emphasis pattern)

# ---------------------------------------------------------------- fixed encodings
SEX_COLORS = {"Female": "#6250d6", "Male": "#1baf7a"}            # violet / aqua
SEASON_COLORS = {"Summer": "#eda100", "Winter": "#2a78d6"}       # yellow / blue
# Metallic medal colors: silver fails the chroma check by nature, so every
# medal mark must also carry a text label (G/S/B) - decided in design review.
MEDAL_COLORS = {"Gold": "#d4a20a", "Silver": "#7f8c99", "Bronze": "#a0522d"}
MEDAL_ORDER = ["Gold", "Silver", "Bronze"]
# Up to 4 compared items (Sports tab, selected countries); validated all-pairs
SELECTION_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#9b2f8a"]   # blue, orange, aqua, plum

# Sequential (magnitude): one hue, light -> dark
SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
# Diverging (female share): violet <- gray at 50 % parity -> aqua
DIVERGING_SEX = [[0.0, "#6250d6"], [0.5, "#ecebe7"], [1.0, "#1baf7a"]]

# ---------------------------------------------------------------- Plotly template
_template = go.layout.Template()
_template.layout = go.Layout(
    font=dict(family=FONT_FAMILY, size=13, color=TEXT_PRIMARY),
    title=dict(font=dict(size=15, color=TEXT_PRIMARY), x=0, xanchor="left"),
    paper_bgcolor=SURFACE,
    plot_bgcolor=SURFACE,
    colorway=SELECTION_COLORS,
    margin=dict(l=48, r=16, t=36, b=40),
    hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(family=FONT_FAMILY, size=12,
                                                                  color=TEXT_PRIMARY)),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                font=dict(color=TEXT_SECONDARY), title=dict(text="")),
    xaxis=dict(gridcolor=GRID, zeroline=False, linecolor=GRID, ticks="",
               tickfont=dict(color=TEXT_SECONDARY), title=dict(font=dict(color=TEXT_SECONDARY))),
    yaxis=dict(gridcolor=GRID, zeroline=False, linecolor=GRID, ticks="",
               tickfont=dict(color=TEXT_SECONDARY), title=dict(font=dict(color=TEXT_SECONDARY))),
    colorscale=dict(sequential=[[i / (len(SEQUENTIAL_BLUE) - 1), c] for i, c in enumerate(SEQUENTIAL_BLUE)]),
)
pio.templates["olympics"] = _template
pio.templates.default = "olympics"

# Plotly toolbar: keep zoom/pan/reset/download, drop rarely useful buttons
GRAPH_CONFIG = {
    "displaylogo": False,
    "scrollZoom": False,          # the mouse wheel scrolls the page, also over the map (zoom: toolbar)
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d", "toggleSpikelines"],
    "toImageButtonOptions": {"format": "png", "scale": 2},
}
# Charts that support box/lasso selection keep those buttons
GRAPH_CONFIG_SELECT = {**GRAPH_CONFIG, "modeBarButtonsToRemove": ["autoScale2d", "toggleSpikelines"]}


def empty_figure(message: str = "No athletes match these filters",
                 hint: str = "Widen the year range or clear some filters.") -> go.Figure:
    """Placeholder shown instead of an empty or broken chart."""
    fig = go.Figure()
    fig.add_annotation(text=f"<b>{message}</b><br><span style='color:{TEXT_MUTED}'>{hint}</span>",
                       x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
                       font=dict(size=14, color=TEXT_SECONDARY))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(margin=dict(l=8, r=8, t=8, b=8))
    return fig


def tint(hex_color: str, amount: float) -> str:
    """Mix a colour with white (amount 0 = unchanged, 1 = white). Used for
    large areas such as treemap tiles, where full-strength colour is too heavy."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    mix = lambda c: round(c + (255 - c) * amount)  # noqa: E731
    return f"#{mix(r):02x}{mix(g):02x}{mix(b):02x}"

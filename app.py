"""Olympic Athletes Explorer: run with `python app.py`, then open http://127.0.0.1:8050"""
import dash
import dash_bootstrap_components as dbc

from dashboard import callbacks  # noqa: F401  (registers global callbacks)
from dashboard import theme  # noqa: F401  (registers the Plotly template)
from dashboard.layout import serve_layout

app = dash.Dash(
    __name__,
    title="Olympic Athletes Explorer",
    external_stylesheets=[
        dbc.themes.FLATLY,
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
    ],
    suppress_callback_exceptions=True,
)
app.layout = serve_layout
server = app.server  # for deployment with a WSGI server, if ever needed

if __name__ == "__main__":
    import os
    debug = os.environ.get("DASH_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 8050)), debug=debug)

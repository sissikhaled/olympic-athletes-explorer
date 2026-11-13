"""Time the server work behind one filter change, per tab.

Usage:  python scripts/benchmark_callbacks.py
"""
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard import data_access as da  # noqa: E402
from dashboard.tabs import countries as co, gender as ge, overview as ov, physiques as ph, sports as sp  # noqa: E402

COLORS = sp.compare_colors(sp.DEFAULT_COMPARE)
TABS = {
    "Overview": lambda f: [ov.update_kpis(f), ov.update_treemap(f), ov.update_athlete_table(f, None)],
    "Countries": lambda f: [co.update_map(f, "total", "range"),
                            co.update_scatter(f, co.scatter_games_options(f)[1]), co.update_heatmap(f, "count"),
                            co.update_host(f)],
    "Physiques": lambda f: [ph.update_focus_sport(f, "Basketball"), ph.update_density(f, "Basketball"),
                            ph.update_trend(f, "height_cm", "Basketball"), ph.update_violin(f, "height_cm", "Basketball")],
    "Gender": lambda f: [ge.update_share(f, None), ge.update_timeline(f, None), ge.update_spine(f)],
    "Sports": lambda f: [sp.update_pca(f, COLORS), sp.update_dist(f, COLORS)],
}
SCENARIOS = {"default": da.DEFAULT_FILTERS,
             "winter": {**da.DEFAULT_FILTERS, "season": "Winter"},
             "women_1960_2016": {**da.DEFAULT_FILTERS, "sex": "Female", "years": [1960, 2016]}}


def run(fn, f, repeats=3):
    times = []
    for _ in range(repeats):
        t = time.perf_counter()
        fn(f)
        times.append(time.perf_counter() - t)
    return statistics.median(times)


if __name__ == "__main__":
    da.table("athlete_games")  # warm the parquet cache
    print(f"{'scenario':18s}" + "".join(f"{t:>11s}" for t in TABS) + f"{'ALL TABS':>11s}")
    for name, f in SCENARIOS.items():
        row = {tab: run(fn, f) for tab, fn in TABS.items()}
        print(f"{name:18s}" + "".join(f"{v:10.2f}s" for v in row.values()) + f"{sum(row.values()):10.2f}s")

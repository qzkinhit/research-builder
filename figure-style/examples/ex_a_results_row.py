"""Example (a). Double-column result figure, one row of four panels, lines mixed with grouped bars.

Reproduces the look of the main result figure of the author's papers. Panels (a) and (c) draw every method, panel (b) compares
two conditions of the same methods with solid lines and filled markers against dashed lines and hollow markers
and carries its own legend inside the axes, panel (d) is a grouped-bar panel. One method legend sits above the
row. Canvas width is the IEEE text width.

Data: examples/data/demo_a_results.csv (demonstration data, not a result).
Run: python ex_a_results_row.py [--out DIR] [--gallery]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

import figstyle as fs  # noqa: E402

FAMILIES = {"A": ["A1", "A2", "A3"], "B": ["B1", "B2", "B3"], "C": ["C1", "C2", "C3"], "D": ["D1", "D2"]}


def wide(frame: pd.DataFrame, panel: str, condition: str = "all") -> pd.DataFrame:
    """One column per method, one row per x value, in the order the CSV lists the methods."""
    sub = frame[(frame.panel == panel) & (frame.condition == condition)]
    table = sub.pivot(index="x", columns="method", values="value")
    return table[list(dict.fromkeys(sub.method))]


def main(out_dir: Path = HERE / "out", gallery: bool = False) -> dict:
    data = pd.read_csv(HERE / "data" / "demo_a_results.csv", comment="#")
    fs.set_methods("Ours", FAMILIES)                      # same call in every figure script of one paper
    fig = fs.canvas("ieee", "text", height=2.7)
    axes = [fs.box(fig, 0.45 + 1.75 * k, 0.50, 1.20, 1.18) for k in range(4)]
    ax_a, ax_b, ax_c, ax_d = axes

    events = wide(data[data.panel == "events"].astype({"x": float}), "events")
    handles = fs.line_panel(ax_a, events.index, events, xlabel="Error types per record", ylabel="F1", dense=True)
    ax_a.set_xticks([1, 2, 3, 4])
    ax_a.set_xlim(0.7, 4.3)

    cov = data[data.panel == "coverage"].astype({"x": float})
    solid, dashed = wide(cov, "coverage", "all"), wide(cov, "coverage", "never")
    fs.line_panel(ax_b, solid.index, solid, xlabel="Labeling budget (%)", ylabel="F1", dense=True, zoom=False)
    fs.line_panel(ax_b, dashed.index, dashed, dense=True, zoom=False, ls=fs.NEVER_DASH, hollow=True)
    fs.zoom_ylim(ax_b, [solid, dashed])
    ax_b.set_xticks([10, 25, 50, 75, 100])
    ax_b.set_xlim(3, 107)

    scale = wide(data[data.panel == "scaling"].astype({"x": float}), "scaling")
    fs.line_panel(ax_c, scale.index, scale, xlabel="Training records (k)", ylabel="F1", dense=True)
    ax_c.set_xscale("log", base=2)
    ax_c.set_xticks([2, 8, 32, 128])
    ax_c.set_xticklabels(["2", "8", "32", "128"])
    ax_c.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax_c.set_xlim(1.6, 160)

    bars = data[data.panel == "bars"]
    groups = list(dict.fromkeys(bars.x))
    series = {m: bars[bars.method == m].set_index("x").loc[groups, "value"].to_numpy()
              for m in dict.fromkeys(bars.method)}
    fs.grouped_bars(ax_d, groups, series, xlabel="Dataset", ylabel="F1")

    for ax, caption in zip(axes, ["(a) Mixed errors", "(b) Budget", "(c) Scaling", "(d) Per dataset"]):
        fs.panel_caption(ax, caption)
    fs.pack_row(fig, axes, gap=0.10)
    # The legend of panel (b) explains line styles, so it belongs inside that panel.
    styles = [Line2D([], [], color=fs.DARK, lw=1.4, marker="o", ms=3.8, label="With feedback"),
              Line2D([], [], color=fs.DARK, lw=1.4, ls=fs.NEVER_DASH, marker="o", ms=3.8, mfc="white",
                     mec=fs.DARK, mew=1.0, label="Without feedback")]
    fs.inside_legend(ax_b, styles, locs=("lower right", "upper left", "lower left", "upper right"), ncols=(1,),
                     grow="bottom", handlelength=1.8)
    fs.shared_legend(fig, handles)
    record = fs.save(fig, Path(out_dir) / "ex_a_results_row")
    if gallery:
        fs.save(fig, HERE.parent / "gallery" / "ex_a_results_row", formats=("png",), dpi=150)
    matplotlib.pyplot.close(fig)
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=HERE / "out")
    parser.add_argument("--gallery", action="store_true", help="also write a 150 dpi PNG into ../gallery")
    args = parser.parse_args()
    print(main(args.out, args.gallery))

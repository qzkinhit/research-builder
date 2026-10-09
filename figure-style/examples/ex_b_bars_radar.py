"""Example (b). Single-column figure with grouped bars and a radar ablation side by side.

Reproduces the look of the comparison and ablation figures of the author's papers.
Panel (a) holds hatched grouped bars with the proposed method in red and its legend inside the axes. Panel (b)
is the ablation radar. Every axis has its own range, printed under the axis name, the full method is the red
outer polygon, and the variant legend is one row above both panels. Canvas width is the IEEE column width.

Data: examples/data/demo_b_bars.csv and demo_b_ablation.csv (demonstration data, not results).
Run: python ex_b_bars_radar.py [--out DIR] [--gallery]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

import figstyle as fs  # noqa: E402

FAMILIES = {"A": ["A1", "A2", "A3"], "B": ["B1", "B2", "B3"], "C": ["C1", "C2", "C3"], "D": ["D1", "D2"]}


def main(out_dir: Path = HERE / "out", gallery: bool = False) -> dict:
    bars = pd.read_csv(HERE / "data" / "demo_b_bars.csv", comment="#", dtype={"faults": str})
    abl = pd.read_csv(HERE / "data" / "demo_b_ablation.csv", comment="#")
    fs.set_methods("Ours", FAMILIES)
    width = fs.width("ieee", "column")
    fig = fs.canvas("ieee", "column", height=2.9)

    base, side = 0.42, 1.50
    ax_a = fs.box(fig, 0.36, base, 0.98, side)
    groups = list(dict.fromkeys(bars.faults))
    series = {m: bars[bars.method == m].set_index("faults").loc[groups, "value"].to_numpy()
              for m in dict.fromkeys(bars.method)}
    handles_a = fs.grouped_bars(ax_a, groups, series, xlabel="Error types per record", ylabel="F1")
    # Start the decorated box of (a) (tick labels and axis label) 0.03 in from the left edge of the canvas.
    fig.canvas.draw()
    dx = 0.03 - ax_a.get_tightbbox(fig.canvas.get_renderer()).x0 / fig.dpi
    pos = ax_a.get_position()
    ax_a.set_position([pos.x0 + dx / width, pos.y0, pos.width, pos.height])
    fs.inside_legend(ax_a, handles_a, locs=("upper left", "upper center", "upper right"), ncols=(2,), grow="top",
                     step=0.05, tries=10, handlelength=1.3)

    # The radar takes the width left of panel (a): its decorated box (circle and corner labels) runs from
    # the right edge of (a) plus a gap to the canvas edge, centred on the height of (a).
    axes_names = list(dict.fromkeys(abl.axis))
    variants = {v: abl[abl.variant == v].set_index("axis").loc[axes_names, "value"].to_numpy()
                for v in dict.fromkeys(abl.variant)}
    fig.canvas.draw()
    right_a = ax_a.get_tightbbox(fig.canvas.get_renderer()).x1 / fig.dpi
    gap, diam, ax_b = 0.12, 1.6, None
    for _ in range(12):
        if ax_b is not None:
            ax_b.remove()
        ax_b = fs.box(fig, right_a + gap, base + side / 2 - diam / 2, diam, diam, projection="polar")
        handles_b, ranges = fs.radar(ax_b, axes_names, variants, full="Full")
        fig.canvas.draw()
        tb = ax_b.get_tightbbox(fig.canvas.get_renderer())
        over = tb.x1 / fig.dpi - (width - 0.03) + max(0.0, right_a + gap - tb.x0 / fig.dpi)
        free = (width - 0.03) - (right_a + gap) - (tb.x1 - tb.x0) / fig.dpi
        if over <= 0 and free < 0.06:
            break
        diam += free * 0.9 if over <= 0 else -max(over, 0.02)
    fig.canvas.draw()
    tb = ax_b.get_tightbbox(fig.canvas.get_renderer())
    shift = ((right_a + gap) + (width - 0.03)) / 2 - (tb.x0 + tb.x1) / 2 / fig.dpi
    pos = ax_b.get_position()
    ax_b.set_position([pos.x0 + shift / width, pos.y0, pos.width, pos.height])

    fs.panel_caption(ax_a, "(a) Per error count")
    fs.panel_caption(ax_b, "(b) Ablation")
    fs.shared_legend(fig, handles_b, fontsize=fs.LEGEND_IN)
    record = fs.save(fig, Path(out_dir) / "ex_b_bars_radar")
    record["radar_ranges"] = ranges
    if gallery:
        fs.save(fig, HERE.parent / "gallery" / "ex_b_bars_radar", formats=("png",), dpi=150)
    plt.close(fig)
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=HERE / "out")
    parser.add_argument("--gallery", action="store_true", help="also write a 150 dpi PNG into ../gallery")
    args = parser.parse_args()
    print(main(args.out, args.gallery))

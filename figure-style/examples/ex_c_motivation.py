"""Example (c). Single-column motivation figure, a corrupted run against its paired clean run, and stacked bars.

Reproduces the look of a time-series motivation figure of the author's papers. The corrupted run and the clean
run share their noise until the onset, the dashed line marks the onset, and the red band after it is the effect
of the injected error. Panel (b) stacks, for every column, the violated rules coloured by their cause. Both
legends sit inside their panels. Canvas width is the IEEE column width.

Data: examples/data/demo_c_paired_run.csv and demo_c_causes.csv (demonstration data, not results).
Run: python ex_c_motivation.py [--out DIR] [--gallery]
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

CAUSES = [("fault_1", "Error A", fs.RED), ("fault_2", "Error B", fs.BLUE), ("both", "Both", fs.ORANGE),
          ("background", "Background", fs.MIDGRAY)]


def main(out_dir: Path = HERE / "out", gallery: bool = False) -> dict:
    run_path = HERE / "data" / "demo_c_paired_run.csv"
    run = pd.read_csv(run_path, comment="#")
    onset = float(run_path.read_text().splitlines()[1].split("onset=")[1])
    causes = pd.read_csv(HERE / "data" / "demo_c_causes.csv", comment="#")

    fig = fs.canvas("ieee", "column", height=2.0)
    ax_a = fs.box(fig, 0.44, 0.45, 1.04, 1.0)
    ax_b = fs.box(fig, 1.78, 0.45, 1.68, 1.0)

    handles_a = fs.ts_effect_panel(ax_a, run["sample"], run.faulty, run.fault_free, onset,
                                   labels=("Corrupted", "Clean"), xlabel="Time step", ylabel="Reading")
    ax_a.set_xticks([0, 50, 100])

    series = {label: causes[col].to_numpy() for col, label, _c in CAUSES}
    handles_b = fs.grouped_bars(ax_b, causes.sensor.tolist(), series, stacked=True, positions=causes.sensor,
                                colors={label: color for _col, label, color in CAUSES}, width=0.94,
                                xlabel="Column index", ylabel="Violated rules")
    ax_b.set_xticks([10, 20, 30, 40, 50])
    ax_b.set_xticklabels(["10", "20", "30", "40", "50"])
    ax_b.set_xlim(0.2, causes.sensor.max() + 0.8)
    ax_b.set_ylim(0, 3.4)
    ax_b.set_yticks([0, 1, 2, 3])
    # Point at the one column whose violated rules have three different causes.
    row = causes[(causes.fault_1 > 0) & (causes.fault_2 > 0) & (causes.both > 0)]
    if len(row):
        j = int(row.sensor.iloc[0])
        top = float(row[["fault_1", "fault_2", "both", "background"]].sum(axis=1).iloc[0])
        ax_b.annotate(f"Column {j}", xy=(j, top + 0.04), xytext=(j - 4.0, top + 0.42), fontsize=fs.NOTE,
                      ha="right", va="center", color=fs.DARK,
                      arrowprops={"arrowstyle": "-|>", "color": fs.DARK, "lw": 0.9, "shrinkA": 1.5, "shrinkB": 0.5,
                                  "mutation_scale": 7})

    fs.panel_caption(ax_a, "(a) Effect of an error")
    fs.panel_caption(ax_b, "(b) Causes of violations")
    fs.pack_row(fig, [ax_a, ax_b], gap=0.12, weights=[1.04, 1.68])
    fs.inside_legend(ax_a, handles_a, locs=("upper right", "upper center"), ncols=(1, 2), grow="top",
                     handlelength=1.3)
    fs.inside_legend(ax_b, handles_b, locs=("upper left", "upper center", "upper right"), ncols=(2, 4), grow="top",
                     handlelength=0.85, gap=0.5, tries=10)
    record = fs.save(fig, Path(out_dir) / "ex_c_motivation")
    if gallery:
        fs.save(fig, HERE.parent / "gallery" / "ex_c_motivation", formats=("png",), dpi=150)
    plt.close(fig)
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=HERE / "out")
    parser.add_argument("--gallery", action="store_true", help="also write a 150 dpi PNG into ../gallery")
    args = parser.parse_args()
    print(main(args.out, args.gallery))

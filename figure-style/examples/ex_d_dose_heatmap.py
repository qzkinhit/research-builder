"""Example (d). Single-column figure with a dose curve and a diverging heat map.

Reproduces the look of the dose and regime panels of the author's papers. Panel (a) draws the gain of each method
against the error rate, with the method legend above the row. Panel (b) is a heat map of the gain per dataset and
error rate with white cell borders, values printed in the strong cells and a colour key above the panel.

Data: examples/data/demo_d_dose.csv and demo_d_heat.csv (demonstration data, not a result).
Run: python ex_d_dose_heatmap.py [--out DIR] [--gallery]
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

FAMILIES = {"Repair": ["Rule", "Model"]}


def main(out_dir: Path = HERE / "out", gallery: bool = False) -> dict:
    dose = pd.read_csv(HERE / "data" / "demo_d_dose.csv", comment="#")
    heat = pd.read_csv(HERE / "data" / "demo_d_heat.csv", comment="#")
    fs.set_methods("Ours", FAMILIES)
    fig = fs.canvas("ieee", "column", height=2.3)
    ax_a = fs.box(fig, 0.44, 0.45, 1.20, 1.15)
    ax_b = fs.box(fig, 2.10, 0.45, 1.30, 1.15)

    post = dose[dose.consumer == "post"]
    rho = sorted(post.rho.unique())
    series = {m: post[post.method == m].set_index("rho").loc[rho, "gain_pp"].to_numpy()
              for m in dict.fromkeys(post.method)}
    handles = fs.line_panel(ax_a, rho, series, refs={"Clean": "oracle"}, xlabel="Error rate", ylabel="Gain (pp)")
    ax_a.set_xticks(rho[::2])

    table = heat.pivot(index="dataset", columns="rho", values="vs_nofix_pp")
    image = fs.heatmap(ax_b, table.to_numpy(), table.index.tolist(), [f"{c:g}" for c in table.columns],
                       annotate=2.0, xlabel="Error rate")

    fs.panel_caption(ax_a, "(a) Dose curve")
    fs.panel_caption(ax_b, "(b) Gain per dataset")
    fs.pack_row(fig, [ax_a, ax_b], gap=0.14, weights=[1.2, 1.3])
    fs.shared_legend(fig, handles, axes=[ax_a], fontsize=fs.LEGEND_IN, ncol=2)
    fs.colorbar_key(fig, image, [ax_b], label="pp")
    record = fs.save(fig, Path(out_dir) / "ex_d_dose_heatmap", strict=False)
    if gallery:
        fs.save(fig, HERE.parent / "gallery" / "ex_d_dose_heatmap", formats=("png",), dpi=150, strict=False)
    plt.close(fig)
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=HERE / "out")
    parser.add_argument("--gallery", action="store_true", help="also write a 150 dpi PNG into ../gallery")
    args = parser.parse_args()
    print(main(args.out, args.gallery))

"""figstyle: the experiment figure style of the author's papers as one small matplotlib module.

The style is distilled from the figure scripts of several published and submitted papers in data management and
machine learning. README.md lists every rule.
Dependencies are matplotlib and numpy. pandas objects are accepted wherever a mapping or an array is.

Rules encoded here.
1. Draw at print size. The canvas width is the text or column width of the venue (WIDTHS), LaTeX includes the
   PDF at scale one, so the point sizes below are the sizes on the page. save() crops the height only.
2. Closed four-sided frames, inward ticks on all four sides, a light grid along one axis, DejaVu Sans, 8.7 pt
   axis labels and panel captions, 8.0 pt tick labels, 7.0 to 7.8 pt legends, TrueType fonts embedded.
3. The proposed method is red with a star marker and a thin black marker edge, drawn last with the thickest
   line. Baselines take one colour per method family and one marker per method inside the family, with a thin
   white marker edge. Reference curves are dark dashed lines with hollow circles.
4. Panels that show the same methods share one legend row above them (shared_legend). A legend that belongs to
   one panel sits inside that panel at a place where it covers no data (inside_legend).
5. Axis ranges follow the plotted values so that the methods separate (zoom_ylim). No broken axes, no watermark.
6. Panel captions "(a) ..." sit 2 pt below the lowest axis decoration of their row (panel_caption, save).
7. A radar ablation scales every axis to its own range, prints that range under the axis name and puts the full
   method on the outer polygon (radar).

Minimal use (examples/ holds complete scripts):

    import figstyle as fs
    fs.set_methods("Ours", {"Statistical": ["A1", "A2"], "Deep": ["B1", "B2"]})
    fig = fs.canvas("ieee", "text", height=2.6)
    ax = fs.box(fig, 0.45, 0.50, 1.20, 1.18)
    handles = fs.line_panel(ax, [1, 2, 3, 4], {"Ours": ours, "A1": a1, "B1": b1},
                            xlabel="Error types per record", ylabel="F1")
    fs.panel_caption(ax, "(a) Mixed errors")
    fs.shared_legend(fig, handles)
    fs.save(fig, "out/fig_results")
"""
from __future__ import annotations

import math
import warnings
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.text
import matplotlib.transforms as mtransforms
import numpy as np
from matplotlib.colors import TwoSlopeNorm, to_rgba
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, MaxNLocator

__all__ = [
    "WIDTHS", "width", "apply_style", "canvas", "box", "frame",
    "set_methods", "ours_kw", "baseline_kw", "ref_kw", "handle", "bar_handle",
    "shared_legend", "inside_legend", "zoom_ylim", "panel_caption", "place_captions", "pack_row",
    "line_panel", "grouped_bars", "radar", "ts_effect_panel", "heatmap", "colorbar_key", "save", "min_font",
]

# ------------------------------------------------------------------------------------------------ page geometry
PT_PER_IN = 72.27   # TeX points per inch

# Printed widths in inches, read from the class files (TeX points divided by 72.27).
# IEEEtran and the IEEE Transactions template ieeecolor.cls give 516 pt text and 252 pt columns (21 pc columns, 1 pc gap).
# acmart sigconf, which PVLDB also uses, gives 506.295 pt text and 24 pt column gap.
# aaai.sty gives 7.0 in text with a 0.375 in gap, icml.sty 6.75 in with 0.25 in, ICLR and NeurIPS 5.5 in.
WIDTHS = {
    "ieee": {"column": 252.0 / PT_PER_IN, "text": 516.0 / PT_PER_IN},
    "acm": {"column": (506.295 - 24.0) / 2 / PT_PER_IN, "text": 506.295 / PT_PER_IN},
    "vldb": {"column": (506.295 - 24.0) / 2 / PT_PER_IN, "text": 506.295 / PT_PER_IN},
    "aaai": {"column": 3.3125, "text": 7.0},
    "icml": {"column": 3.25, "text": 6.75},
    "iclr": {"column": 5.5, "text": 5.5},
    "neurips": {"column": 5.5, "text": 5.5},
}


def width(venue: str = "ieee", kind: str = "text") -> float:
    """Printed width in inches of the text block (kind='text') or one column (kind='column') of a venue."""
    try:
        return WIDTHS[venue.lower()][kind]
    except KeyError as err:
        raise KeyError(f"unknown venue or kind {venue!r}/{kind!r}, known venues {sorted(WIDTHS)}") from err


# ------------------------------------------------------------------------------------------------ text sizes (pt)
FS = 8.7           # axis labels and panel captions
TICK = 8.0         # tick labels
LEGEND = 7.8       # legends outside the axes
LEGEND_IN = 7.0    # legends inside the axes, reduced in steps down to LEGEND_MIN when space is short
LEGEND_MIN = 6.3   # smallest legend size, also the floor that min_font() checks
NOTE = 7.4         # text inside a panel (onset, effect, annotations)
VALUE = 7.0        # value labels at bar ends and in heat map cells

# ------------------------------------------------------------------------------------------------ colours
RED = "#D62728"        # the proposed method only, and the faulty run of a motivating example
BLUE = "#4E79A7"
ORANGE = "#F28E2B"
GREEN = "#59A14F"
PURPLE = "#B279A2"
TEAL = "#17A2B8"
BROWN = "#8C564B"
OLIVE = "#A5A33A"
GRAY = "#8F8F8F"
MIDGRAY = "#6E6E6E"
DARK = "#303030"
FRAME = "#222222"
EFFECT_TEXT = "#8E1B1C"   # dark red label inside the red effect band

FAMILY_COLORS = (BLUE, ORANGE, GREEN, PURPLE, TEAL, BROWN, GRAY, OLIVE)
MARKERS = ("o", "s", "^", "D", "v", "P", "X", "h")
OURS_HATCH = "////"
HATCHES = ("\\\\\\\\", "....", "xxxx", "----", "++++", "oo")
NEVER_DASH = (0, (3.2, 1.6))   # dash pattern of a second condition of the same method (hollow markers)

RC = {
    "font.family": "DejaVu Sans",
    "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
    "xtick.labelsize": TICK, "ytick.labelsize": TICK, "legend.fontsize": LEGEND,
    "mathtext.fontset": "dejavusans", "axes.unicode_minus": True,
    "axes.linewidth": 0.8, "axes.edgecolor": FRAME, "axes.labelpad": 1.5,
    "axes.spines.top": True, "axes.spines.right": True, "axes.axisbelow": True, "axes.grid": False,
    "xtick.direction": "in", "ytick.direction": "in", "xtick.top": True, "ytick.right": True,
    "xtick.major.size": 2.6, "ytick.major.size": 2.6, "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "xtick.minor.size": 1.5, "ytick.minor.size": 1.5, "xtick.major.pad": 1.8, "ytick.major.pad": 1.8,
    "xtick.color": FRAME, "ytick.color": FRAME,
    "grid.linewidth": 0.4, "grid.alpha": 0.22,
    "lines.linewidth": 1.5, "lines.markersize": 4.8, "lines.solid_capstyle": "round",
    "hatch.linewidth": 0.5,
    "legend.frameon": False, "legend.handlelength": 1.3, "legend.handletextpad": 0.3,
    "legend.columnspacing": 0.7, "legend.labelspacing": 0.12, "legend.borderpad": 0.0,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    "figure.dpi": 150, "savefig.dpi": 450, "figure.facecolor": "white", "savefig.facecolor": "white",
}


def apply_style(overrides: dict | None = None) -> None:
    """Reset matplotlib to its defaults and apply the shared rcParams, then the optional overrides
    (a mapping of rcParams keys, for example {"axes.labelsize": 9.0})."""
    plt.rcdefaults()
    plt.rcParams.update(RC)
    plt.rcParams.update(overrides or {})


def canvas(venue: str = "ieee", kind: str = "text", height: float = 2.6, fig_width: float | None = None):
    """A white figure as wide as the printed text or column of the venue. The height is only a working
    height. save() crops it to the content, so choose it generously."""
    apply_style()
    w = fig_width if fig_width is not None else width(venue, kind)
    return plt.figure(figsize=(w, height), facecolor="white")


def box(fig, x: float, y: float, w: float, h: float, **kw):
    """Axes placed in inches from the lower-left corner of the canvas. Pass projection='polar' for a radar."""
    fw, fh = fig.get_size_inches()
    return fig.add_axes([x / fw, y / fh, w / fw, h / fh], **kw)


def frame(ax, grid: str = "y") -> None:
    """Closed frame, inward ticks on all four sides and a light grid along 'x', 'y', 'both' or '' (none)."""
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.8)
        spine.set_color(FRAME)
        spine.set_zorder(4)           # above the bars, so white bar edges never break the frame
    ax.tick_params(which="both", direction="in", top=True, right=True, labelsize=TICK, length=2.6, width=0.7,
                   pad=1.8, color=FRAME)
    ax.tick_params(which="minor", length=1.5)
    if grid:
        ax.grid(axis=grid, alpha=0.22, lw=0.4)
    ax.set_axisbelow(True)


def compact_ticks(ax, axis: str = "y", nbins: int = 4) -> None:
    """At most nbins+1 ticks at round values, printed without trailing zeros and with a true minus sign."""
    target = ax.yaxis if axis == "y" else ax.xaxis
    target.set_major_locator(MaxNLocator(nbins=nbins, steps=[1, 2, 2.5, 5, 10]))
    target.set_major_formatter(FuncFormatter(_decimal))


def _decimal(v, _pos=None) -> str:
    return f"{round(v, 6):g}".replace("-", "−")


# ------------------------------------------------------------------------------------------------ method styles
_METHODS = {"ours": "Ours", "family_of": {}, "families": [], "members": {}}


def set_methods(ours: str, families: dict | None = None) -> None:
    """Fix the display name of the proposed method and the baseline families of one paper.

    Call it at the top of every figure script of the paper with the same arguments (for example from a shared
    methods.py), so that each method keeps its colour, marker and hatch in every figure.

    Args:
        ours: display name of the proposed method.
        families: ordered mapping from a family name to the ordered list of its methods, in the row order of
            the main table. Family k takes FAMILY_COLORS[k]. Method j of a family takes MARKERS[j] and HATCHES[j].
    """
    _METHODS["ours"] = ours
    _METHODS["family_of"] = {}
    _METHODS["families"] = []
    _METHODS["members"] = {}
    for fam, names in (families or {}).items():
        _METHODS["families"].append(fam)
        _METHODS["members"][fam] = list(names)
        for name in names:
            _METHODS["family_of"][name] = fam


def _slot(name: str, family: str | None = None):
    """Family index and index inside the family of a method. Unknown methods are registered on first use, in
    their own family unless one is given."""
    fam = _METHODS["family_of"].get(name)
    if fam is None:
        fam = family if family is not None else name
        if fam not in _METHODS["members"]:
            _METHODS["families"].append(fam)
            _METHODS["members"][fam] = []
        _METHODS["members"][fam].append(name)
        _METHODS["family_of"][name] = fam
    return _METHODS["families"].index(fam), _METHODS["members"][fam].index(name)


def _baselines_in_order(names) -> list:
    """The given baseline names in registry order (family order, then order inside the family)."""
    for n in names:
        _slot(n)
    return sorted(names, key=lambda n: _slot(n))


def ours_kw(dense: bool = False) -> dict:
    """Plot keywords of the proposed method: red line, star marker with a thin black edge, drawn on top."""
    return {"color": RED, "marker": "*", "ms": 10.0 if dense else 9.0, "lw": 2.3, "mec": "black", "mew": 0.4,
            "zorder": 6}


def baseline_kw(name: str, family: str | None = None, dense: bool = False) -> dict:
    """Plot keywords of one baseline: the colour of its family, the marker of its rank inside the family and a
    thin white marker edge. dense=True gives the thinner lines and smaller markers used with many baselines."""
    k, j = _slot(name, family)
    marker = MARKERS[j % len(MARKERS)]
    size = 3.7 if dense else 4.8
    if marker in ("D", "h"):
        size *= 0.87                  # diamonds and hexagons look larger than circles at the same size
    return {"color": FAMILY_COLORS[k % len(FAMILY_COLORS)], "marker": marker, "ms": size,
            "lw": 0.95 if dense else 1.5, "mec": "white", "mew": 0.3, "zorder": 3 + 0.1 * j}


def ref_kw(kind: str = "baseline") -> dict:
    """Plot keywords of a reference curve.

    kind='baseline' is the untouched or random reference (dark dashed line, hollow circles).
    kind='oracle' is a clean or upper reference (green dashed line, squares).
    kind='zero' is a thin solid line for axhline(0) or axvline(0).
    """
    if kind == "oracle":
        return {"color": GREEN, "ls": (0, (4, 2)), "lw": 1.4, "marker": "s", "ms": 4.0, "mec": "white",
                "mew": 0.3, "zorder": 4}
    if kind == "zero":
        return {"color": FRAME, "ls": "-", "lw": 0.7, "zorder": 2}
    return {"color": DARK, "ls": (0, (3, 2)), "lw": 1.1, "marker": "o", "ms": 4.2, "mfc": "white", "mec": DARK,
            "mew": 0.9, "zorder": 5}


def handle(label: str, kw: dict, scale: float = 0.85) -> Line2D:
    """Legend handle of a line style (ours_kw, baseline_kw or ref_kw), marker slightly reduced."""
    return Line2D([], [], label=label, color=kw.get("color"), ls=kw.get("ls", "-"), lw=kw.get("lw", 1.5),
                  marker=kw.get("marker"), ms=kw.get("ms", 4.8) * scale, mfc=kw.get("mfc", kw.get("color")),
                  mec=kw.get("mec", kw.get("color")), mew=kw.get("mew", 0.0))


def bar_handle(label: str, color: str, hatch: str | None = None, edge: str = DARK) -> Patch:
    """Legend handle of a hatched bar."""
    return Patch(facecolor=to_rgba(color, 0.85), edgecolor=edge, lw=0.35, hatch=hatch, label=label)


def _bar_style(name: str, ours: str) -> tuple:
    if name == ours:
        return RED, OURS_HATCH
    k, j = _slot(name)
    return FAMILY_COLORS[k % len(FAMILY_COLORS)], HATCHES[j % len(HATCHES)]


# ------------------------------------------------------------------------------------------------ layout helpers
def _renderer(fig):
    fig.canvas.draw()
    return fig.canvas.get_renderer()


def _content_axes(fig) -> list:
    return [a for a in fig.axes if not getattr(a, "_figstyle_key", False)]


def panel_caption(ax, text: str, gap_pt: float = 2.0) -> None:
    """Attach the caption "(a) ..." to a panel. place_captions() and save() put it centred under the panel,
    gap_pt below the lowest axis decoration of its row, in regular weight at the axis label size."""
    ax._figstyle_caption = (text, gap_pt)


def _rows(axes) -> list:
    """Group axes into rows: two axes share a row when their vertical extents overlap by half or more."""
    rows = []
    for ax in sorted(axes, key=lambda a: -a.get_position().y1):
        p = ax.get_position()
        for row in rows:
            q = row[0].get_position()
            overlap = min(p.y1, q.y1) - max(p.y0, q.y0)
            if overlap >= 0.5 * min(p.height, q.height):
                row.append(ax)
                break
        else:
            rows.append([ax])
    return rows


def place_captions(fig) -> list:
    """Draw the captions attached by panel_caption(). Captions of one row share one baseline. Returns them."""
    for t in getattr(fig, "_figstyle_captions", []):
        t.remove()
    fig._figstyle_captions = []
    captioned = [a for a in fig.axes if getattr(a, "_figstyle_caption", None)]
    if not captioned:
        return []
    r = _renderer(fig)
    fh = fig.get_figheight() * fig.dpi
    for row in _rows(captioned):
        bottom = min(a.get_tightbbox(r).y0 for a in row)
        for ax in row:
            text, gap = ax._figstyle_caption
            pos = ax.get_position()
            y = (bottom - gap * fig.dpi / 72) / fh
            fig._figstyle_captions.append(fig.text((pos.x0 + pos.x1) / 2, y, text, ha="center", va="top",
                                                   fontsize=FS))
    return fig._figstyle_captions


def pack_row(fig, axes, gap: float = 0.10, edge: float = 0.03, weights=None, passes: int = 4) -> float:
    """Set the widths of a row of panels so that the decorated boxes (tick labels, axis labels and captions)
    are gap inches apart and the row fills the canvas up to edge inches on each side. Panel widths follow
    weights (equal by default). Heights and vertical positions stay. Returns the width of a weight-one panel."""
    weights = list(weights) if weights is not None else [1.0] * len(axes)
    fw = fig.get_figwidth()
    r = _renderer(fig)
    half = []
    for ax in axes:
        cap = getattr(ax, "_figstyle_caption", None)
        if cap:
            probe = fig.text(0, 0, cap[0], fontsize=FS)
            half.append(probe.get_window_extent(r).width / fig.dpi / 2)
            probe.remove()
        else:
            half.append(0.0)
    unit = 0.0
    for _ in range(passes):
        r = _renderer(fig)
        over = []
        for ax, h in zip(axes, half):
            tb = ax.get_tightbbox(r)
            pos = ax.get_position()
            w = pos.width * fw
            over.append((max(pos.x0 * fw - tb.x0 / fig.dpi, h - w / 2), max(tb.x1 / fig.dpi - pos.x1 * fw, h - w / 2)))
        unit = (fw - 2 * edge - gap * (len(axes) - 1) - sum(a + b for a, b in over)) / sum(weights)
        x = edge
        for ax, (left, right), wt in zip(axes, over, weights):
            pos = ax.get_position()
            ax.set_position([(x + left) / fw, pos.y0, unit * wt / fw, pos.height])
            x += left + unit * wt + right + gap
    return unit


def _row_major(handles, ncol: int) -> list:
    """Reorder handles so that matplotlib, which fills legend columns first, prints them row by row."""
    rows = -(-len(handles) // ncol)
    return [handles[r * ncol + c] for c in range(ncol) for r in range(rows) if r * ncol + c < len(handles)]


def shared_legend(fig, handles, ncol: int | None = None, axes=None, gap_pt: float = 3.0, fontsize: float = LEGEND,
                  order: str = "row", x: float | None = None):
    """One legend for panels that show the same methods, gap_pt above the highest decoration of those panels.

    ncol=None tries one row. A row wider than the canvas is first set in smaller type (down to LEGEND_MIN) and
    then broken into more rows. order='row' prints the handles row by row, order='column' column by column
    (keeps the methods of one family above each other). axes defaults to every panel of the figure, x to the
    centre of those panels (in figure coordinates).
    """
    axes = list(axes) if axes is not None else _content_axes(fig)
    fw, fh = fig.get_size_inches()
    r = _renderer(fig)
    top = max(a.get_tightbbox(r).y1 for a in axes) / fig.dpi
    if x is None:
        if len(axes) == len(_content_axes(fig)):
            x = 0.5
        else:
            x0 = min(a.get_tightbbox(r).x0 for a in axes) / fig.dpi
            x1 = max(a.get_tightbbox(r).x1 for a in axes) / fig.dpi
            x = (x0 + x1) / 2 / fw
    n = len(handles)
    ncols = [ncol] if ncol else []
    ncols += [c for c in (n, -(-n // 2), -(-n // 3), -(-n // 4)) if c not in ncols]
    sizes = [fontsize] + [s for s in (7.4, 7.0, 6.7, LEGEND_MIN) if s < fontsize]
    for nc in ncols:
        for size in sizes:
            hs = _row_major(handles, nc) if order == "row" else list(handles)
            leg = fig.legend(handles=hs, loc="lower center", bbox_to_anchor=(x, (top + gap_pt / 72) / fh),
                             ncol=nc, frameon=False, fontsize=size, handlelength=1.3, handleheight=0.8,
                             handletextpad=0.3, columnspacing=0.7, labelspacing=0.12, borderaxespad=0,
                             borderpad=0)
            bb = leg.get_window_extent(_renderer(fig))
            if bb.x0 >= 0.02 * fig.dpi and bb.x1 <= (fw - 0.02) * fig.dpi:
                leg._figstyle_shared = True
                return leg
            leg.remove()
    raise ValueError("the shared legend does not fit the canvas width even in several rows")


# ------------------------------------------------------------------------------------------------ legends inside
def _line_boxes(ln, dpi: float) -> list:
    """Display-space boxes covered by a Line2D: one per marker and small boxes along every drawn segment."""
    if not ln.get_visible():
        return []
    xy = np.asarray(ln.get_xydata(), dtype=float)
    if xy.size == 0:
        return []
    pts = ln.get_transform().transform(xy)
    out = []
    half_w = max(ln.get_linewidth() * dpi / 72 / 2, 0.5)
    if ln.get_linestyle() not in ("None", "none", "", " "):
        for a, b in zip(pts[:-1], pts[1:]):
            if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))):
                continue
            steps = max(2, int(np.hypot(*(b - a)) / (1.5 * dpi / 72)) + 1)
            for t in np.linspace(0.0, 1.0, steps):
                p = a + (b - a) * t
                out.append((p[0] - half_w, p[1] - half_w, p[0] + half_w, p[1] + half_w))
    if ln.get_marker() not in (None, "None", "none", "", " "):
        half_m = ln.get_markersize() * dpi / 72 / 2 + ln.get_markeredgewidth() * dpi / 72 / 2
        out += [(p[0] - half_m, p[1] - half_m, p[0] + half_m, p[1] + half_m) for p in pts if np.all(np.isfinite(p))]
    return out


def _obstacles(ax) -> list:
    """Display boxes of everything drawn in the axes that a legend must not cover."""
    r = _renderer(ax.figure)
    dpi = ax.figure.dpi
    boxes = []
    for ln in ax.lines:
        boxes += _line_boxes(ln, dpi)
    for pa in ax.patches:
        if pa.get_visible():
            bb = pa.get_window_extent(r)
            boxes.append((bb.x0, bb.y0, bb.x1, bb.y1))
    for coll in ax.collections:
        if not coll.get_visible():
            continue
        offsets = coll.get_offsets() if hasattr(coll, "get_offsets") else []
        if len(offsets) and len(coll.get_paths()) == 1:          # scatter: one marker path at many offsets
            pts = coll.get_offset_transform().transform(np.asarray(offsets, dtype=float))
            boxes += [(p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3) for p in pts if np.all(np.isfinite(p))]
            continue
        for path in coll.get_paths():
            v = coll.get_transform().transform(path.vertices)
            boxes += [(p[0] - 1, p[1] - 1, p[0] + 1, p[1] + 1) for p in v if np.all(np.isfinite(p))]
    for t in ax.texts:
        if t.get_visible() and t.get_text():
            bb = t.get_window_extent(r)
            boxes.append((bb.x0, bb.y0, bb.x1, bb.y1))
            arrow = getattr(t, "arrow_patch", None)
            if arrow is not None:
                ab = arrow.get_window_extent(r)
                boxes.append((ab.x0, ab.y0, ab.x1, ab.y1))
    return boxes


def _covered(bb, boxes, pad: float) -> float:
    x0, y0, x1, y1 = bb.x0 - pad, bb.y0 - pad, bb.x1 + pad, bb.y1 + pad
    area = 0.0
    for a0, b0, a1, b1 in boxes:
        w, h = min(x1, a1) - max(x0, a0), min(y1, b1) - max(y0, b0)
        if w > 0 and h > 0:
            area += w * h
    return area


LOCS = ("upper left", "upper right", "lower right", "lower left", "upper center", "lower center", "center left",
        "center right", "center")


def inside_legend(ax, handles, locs=LOCS, ncols=(1, 2), sizes=None, handlelength: float = 1.4, gap: float = 0.6,
                  grow: str = "", step: float = 0.08, tries: int = 4, pad_pt: float = 1.6):
    """Legend inside one panel at the first place where it covers no line, marker, bar or text.

    The search keeps the largest font as long as possible. For each font size (LEGEND_IN down to LEGEND_MIN)
    it tries every position in locs and every column count in ncols. When none is free and grow names sides
    ('top', 'bottom', 'left', 'right'), the data limits are widened by step of their span on those sides, at
    most tries times, before the next smaller size is tried with the original limits.
    Raises ValueError when no free place exists, so a legend never hides data silently.
    """
    fig = ax.figure
    sizes = sizes or [LEGEND_IN, 6.7, LEGEND_MIN]
    pad = pad_pt * fig.dpi / 72
    xlim0, ylim0 = ax.get_xlim(), ax.get_ylim()
    for size in sizes:
        ax.set_xlim(xlim0)
        ax.set_ylim(ylim0)
        for attempt in range(tries + 1):
            boxes = _obstacles(ax)
            frame_bb = ax.get_window_extent(_renderer(fig))
            for loc in locs:
                for nc in ncols:
                    if nc > len(handles):
                        continue
                    leg = ax.legend(handles=_row_major(list(handles), nc), loc=loc, ncol=nc, frameon=False,
                                    fontsize=size, handlelength=handlelength, handleheight=0.7, handletextpad=0.35,
                                    columnspacing=gap, labelspacing=0.18, borderaxespad=0.55, borderpad=0.0)
                    bb = leg.get_window_extent(_renderer(fig))
                    fits = (bb.x0 >= frame_bb.x0 + 1 and bb.x1 <= frame_bb.x1 - 1 and bb.y0 >= frame_bb.y0 + 1
                            and bb.y1 <= frame_bb.y1 - 1)
                    if fits and _covered(bb, boxes, pad) == 0.0:
                        leg.set_zorder(20)
                        leg._figstyle_inside = True
                        return leg
                    leg.remove()
            if not grow or attempt == tries:
                break
            if "top" in grow or "bottom" in grow:
                lo, hi = ax.get_ylim()
                span = hi - lo
                ax.set_ylim(lo - (step * span if "bottom" in grow else 0),
                            hi + (step * span if "top" in grow else 0))
            if "left" in grow or "right" in grow:
                lo, hi = ax.get_xlim()
                span = hi - lo
                ax.set_xlim(lo - (step * span if "left" in grow else 0),
                            hi + (step * span if "right" in grow else 0))
    ax.set_xlim(xlim0)
    ax.set_ylim(ylim0)
    raise ValueError(f"no free place inside the panel for the legend {[h.get_label() for h in handles]}, "
                     "pass grow='top' (or another side) or fewer columns")


# ------------------------------------------------------------------------------------------------ axis ranges
def _flat(values) -> np.ndarray:
    if isinstance(values, dict):
        values = list(values.values())
    if hasattr(values, "to_numpy"):
        values = values.to_numpy()
    out = []
    for v in (values if isinstance(values, (list, tuple)) else [values]):
        if hasattr(v, "to_numpy"):
            v = v.to_numpy()
        out.append(np.asarray(v, dtype=float).ravel())
    return np.concatenate(out) if out else np.array([])


def zoom_ylim(ax, values, margin=(0.06, 0.08), include=None, quantum: float | None = None, nbins: int = 4,
              axis: str = "y") -> tuple:
    """Set the axis range from the plotted values so that the methods spread over the panel.

    The range runs from margin[0] of the data span below the smallest value to margin[1] above the largest.
    include adds values that must stay visible (for example 0 for a gain axis). quantum rounds the limits
    outward to a multiple (for example 0.05). Ticks are set by compact_ticks(). Returns the limits.
    """
    v = _flat(values)
    if include is not None:
        v = np.concatenate([v, np.atleast_1d(np.asarray(include, dtype=float))])
    v = v[np.isfinite(v)]
    if v.size == 0:
        return (ax.get_ylim() if axis == "y" else ax.get_xlim())
    lo, hi = float(v.min()), float(v.max())
    span = hi - lo if hi > lo else (abs(hi) * 0.1 or 1.0)
    a, b = lo - margin[0] * span, hi + margin[1] * span
    if quantum:
        a, b = math.floor(a / quantum) * quantum, math.ceil(b / quantum) * quantum
    (ax.set_ylim if axis == "y" else ax.set_xlim)(a, b)
    compact_ticks(ax, axis, nbins)
    return a, b


# ------------------------------------------------------------------------------------------------ chart types
def _series_items(series) -> list:
    if hasattr(series, "items") and not isinstance(series, dict):        # a DataFrame: one column per method
        return [(str(c), series[c].to_numpy()) for c in series.columns]
    return [(str(k), v) for k, v in series.items()]


def line_panel(ax, x, series, *, ours: str | None = None, refs=(), xlabel: str | None = None,
               ylabel: str | None = None, ls="-", hollow: bool = False, dense: bool | None = None,
               zoom: bool = True, grid: str = "y") -> list:
    """One line with markers per method, baselines first, references next, the proposed method last on top.

    Args:
        x: x positions shared by all series, or a mapping from method to its own x positions.
        series: mapping (or DataFrame) from method name to y values. NaN leaves a gap in the line.
        ours: name of the proposed method (default the one given to set_methods()).
        refs: names drawn as reference curves, or a mapping name -> 'baseline' | 'oracle' (see ref_kw).
        ls, hollow: line style and hollow markers for a second condition of the same methods.
        dense: thinner lines and smaller markers, default True with more than seven methods.
    Returns legend handles of the plotted methods: proposed method first, baselines in registry order,
    references last.
    """
    ours = ours or _METHODS["ours"]
    items = _series_items(series)
    refs = dict(refs) if isinstance(refs, dict) else {r: "baseline" for r in refs}
    dense = len(items) > 7 if dense is None else dense
    data = dict(items)
    xs_of = (lambda n: np.asarray(x[n], dtype=float)) if isinstance(x, dict) else (lambda n: np.asarray(x, dtype=float))
    base = _baselines_in_order([n for n, _ in items if n != ours and n not in refs])
    handles = []
    plotted = []
    for name in base + [n for n in data if n in refs] + ([ours] if ours in data else []):
        if name == ours:
            kw = ours_kw(dense)
        elif name in refs:
            kw = ref_kw(refs[name])
        else:
            kw = baseline_kw(name, dense=dense)
        face = "white" if hollow else kw.get("mfc", kw["color"])
        edge = kw["color"] if hollow else kw.get("mec", kw["color"])
        ax.plot(xs_of(name), np.asarray(data[name], dtype=float), color=kw["color"],
                ls=ls if name not in refs else kw.get("ls", ls), lw=kw.get("lw", 1.5), marker=kw.get("marker"),
                ms=kw.get("ms", 4.8), mfc=face, mec=edge, mew=1.0 if hollow else kw.get("mew", 0.0),
                zorder=kw.get("zorder", 3), clip_on=False, solid_capstyle="round", dash_capstyle="butt")
        plotted.append(np.asarray(data[name], dtype=float))
        handles.append(handle(name, kw))
    if zoom and plotted:
        zoom_ylim(ax, plotted)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    frame(ax, grid)
    # Legend order: proposed method first, then baselines, then references.
    by_name = {h.get_label(): h for h in handles}
    order = ([ours] if ours in by_name else []) + [n for n in base if n in by_name] + [n for n in data if n in refs]
    return [by_name[n] for n in order]


def grouped_bars(ax, groups, series, *, ours: str | None = None, horizontal: bool = False, stacked: bool = False,
                 colors: dict | None = None, hatches: dict | None = None, positions=None, width: float = 0.8,
                 values: bool = False, fmt="{:.2f}", zoom: bool = True, xlabel: str | None = None,
                 ylabel: str | None = None) -> list:
    """Grouped (or stacked) bars: one group per entry of groups, one bar per method inside a group.

    Side-by-side bars are hatched with a dark edge, the proposed method red with '////' and placed last in each
    group. Stacked bars (stacked=True) keep the given order and use white edges without hatches. colors and
    hatches override the defaults per series. positions gives numeric group positions (default 0, 1, ...).
    values=True prints each value at the bar end with fmt (a format string or a function). With zoom the value
    axis starts below the smallest bar when all bars are well above zero, otherwise at zero.
    Returns legend handles, proposed method first.
    """
    ours = ours or _METHODS["ours"]
    items = _series_items(series)
    data = dict(items)
    names = list(data) if stacked else _baselines_in_order([n for n in data if n != ours]) + (
        [ours] if ours in data else [])
    pos = np.arange(len(groups), dtype=float) if positions is None else np.asarray(positions, dtype=float)
    bar = ax.barh if horizontal else ax.bar
    handles = {}
    bottom = np.zeros(len(pos))
    every = []
    for i, name in enumerate(names):
        vals = np.asarray(data[name], dtype=float)
        color, hatch = _bar_style(name, ours) if not stacked else (None, None)
        if stacked and color is None:
            color = (RED, BLUE, ORANGE, MIDGRAY, GREEN, PURPLE, TEAL, BROWN)[i % 8]
        color = (colors or {}).get(name, color)
        hatch = (hatches or {}).get(name, hatch)
        if stacked:
            on = np.isfinite(vals) & (vals != 0)
            kw = {"left" if horizontal else "bottom": bottom[on]}
            bar(pos[on], vals[on], width if not horizontal else width, color=color, edgecolor="white", lw=0.35,
                hatch=hatch, zorder=3, **kw)
            bottom = bottom + np.nan_to_num(vals)
            handles[name] = Patch(facecolor=color, edgecolor="white", lw=0.35, hatch=hatch, label=name)
            continue
        w = width / len(names)
        off = (i - (len(names) - 1) / 2) * w
        bar(pos + off, vals, w, color=to_rgba(color, 0.85), edgecolor=DARK, lw=0.35, hatch=hatch, zorder=3)
        every.append(vals)
        handles[name] = bar_handle(name, color, hatch)
        if values:
            for p, v in zip(pos + off, vals):
                if not np.isfinite(v):
                    continue
                text = fmt(v) if callable(fmt) else fmt.format(v)
                text = text.replace("-", "−")
                if horizontal:
                    ax.annotate(text, (v, p), xytext=(2 if v >= 0 else -2, 0), textcoords="offset points",
                                ha="left" if v >= 0 else "right", va="center", fontsize=VALUE, zorder=6)
                else:
                    ax.annotate(text, (p, v), xytext=(0, 1.5 if v >= 0 else -1.5), textcoords="offset points",
                                ha="center", va="bottom" if v >= 0 else "top", fontsize=VALUE, zorder=6)
    value_axis = "x" if horizontal else "y"
    if stacked:
        top = float(np.nanmax(bottom)) if len(bottom) else 1.0
        (ax.set_xlim if horizontal else ax.set_ylim)(0, top * 1.06)
        compact_ticks(ax, value_axis)
    elif zoom and every:
        v = _flat(every)
        v = v[np.isfinite(v)]
        lo, hi = float(v.min()), float(v.max())
        if lo > 0 and lo > 0.4 * hi:
            zoom_ylim(ax, v, margin=(0.25, 0.08), axis=value_axis)
        else:
            zoom_ylim(ax, v, margin=(0.04, 0.12), include=0.0, axis=value_axis)
            lim = ax.get_xlim() if horizontal else ax.get_ylim()
            if lo >= 0:
                (ax.set_xlim if horizontal else ax.set_ylim)(0, lim[1])
    if horizontal:
        ax.set_yticks(pos)
        ax.set_yticklabels([str(g) for g in groups])
        ax.set_ylim(pos.max() + 0.5 + (width - 0.8) / 2, pos.min() - 0.5 - (width - 0.8) / 2)
    else:
        ax.set_xticks(pos)
        ax.set_xticklabels([str(g) for g in groups])
        ax.set_xlim(pos.min() - 0.5, pos.max() + 0.5)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    frame(ax, "x" if horizontal else "y")
    ax.tick_params(axis="y" if horizontal else "x", length=0, pad=2.0)
    if horizontal:
        ax.tick_params(axis="y", right=False)
    else:
        ax.tick_params(axis="x", top=False)
    order = names if stacked else ([ours] if ours in handles else []) + [n for n in names if n != ours]
    return [handles[n] for n in order]


def radar(ax, axes_names, series, *, full: str | None = None, ranges: dict | None = None,
          offset: float | None = None, fmt: str = "{:.2f}", r0: float = 0.12, name_pt: float = 8.0,
          range_pt: float = 6.4, colors: dict | None = None):
    """Ablation radar in which every axis has its own radial range.

    Args:
        ax: polar axes (box(..., projection='polar')).
        axes_names: axis (spoke) names, clockwise from the first spoke.
        series: mapping from variant name to its values in axis order. The full method is drawn red with a star
            marker, a black marker edge and a light fill. Other variants take solid lines and white-edged
            markers whose sizes fall in drawing order, so coinciding vertices stay visible as nested marks.
        full: name of the full method (default the proposed method of set_methods(), else the first series).
        ranges: mapping axis -> (inner, outer). Default per axis from slightly below the lowest to slightly above
            the highest plotted value, rounded outward to 0.01, so the full method lies on or near the rim when it
            is best. A variant that beats the full method on an axis is drawn as measured, never clipped.
        offset: angle of the first spoke in radians. Default pi/4 for four axes (spokes on the diagonals, labels
            in the corners) and pi/2 (top) otherwise.
    Returns the legend handles (full method first) and the ranges used.
    """
    names = list(series)
    full = full or (_METHODS["ours"] if _METHODS["ours"] in series else names[0])
    n = len(axes_names)
    values = {k: np.asarray(series[k], dtype=float) for k in names}
    if ranges is None:
        ranges = {}
        for i, a in enumerate(axes_names):
            col = np.array([values[k][i] for k in names])
            lo, hi = float(np.nanmin(col)), float(np.nanmax(col))
            span = max(hi - lo, 0.004)
            ranges[a] = (math.floor((lo - 0.15 * span) * 100) / 100, math.ceil((hi + 0.06 * span) * 100) / 100)
    offset = (math.pi / 4 if n == 4 else math.pi / 2) if offset is None else offset
    angles = np.linspace(0, 2 * math.pi, n, endpoint=False)
    closed = np.concatenate([angles, angles[:1]])
    ax.set_theta_offset(offset)
    ax.set_theta_direction(-1)

    def radius(i, v):
        lo, hi = ranges[axes_names[i]]
        return r0 + (1 - r0) * (v - lo) / (hi - lo)

    others = [k for k in names if k != full]
    palette = (BLUE, ORANGE, GREEN, PURPLE, TEAL, BROWN, GRAY, OLIVE)
    sizes = np.linspace(5.2, 3.6, max(len(others), 1))
    handles = []
    for k, name in enumerate([full] + others):
        r = np.array([radius(i, v) for i, v in enumerate(values[name])])
        if name == full:
            color, marker, lw, ms = RED, "*", 1.9, 8.0
            edge = {"mec": "black", "mew": 0.4}
        else:
            j = others.index(name)
            color, marker, lw, ms = palette[j % len(palette)], MARKERS[(j + 1) % len(MARKERS)], 1.1, float(sizes[j])
            edge = {"mec": "white", "mew": 0.45}
        color = (colors or {}).get(name, color)
        ax.plot(closed, np.concatenate([r, r[:1]]), color=color, lw=lw, ls="-", zorder=5 if name == full else 3)
        ax.plot(angles, r, ls="none", marker=marker, ms=ms, mfc=color, zorder=10 + k, clip_on=False, **edge)
        if name == full:
            ax.fill(closed, np.concatenate([r, r[:1]]), color=color, alpha=0.10, zorder=1)
        handles.append(Line2D([], [], color=color, lw=lw, marker=marker, ms=ms * (0.8 if name == full else 1.0),
                              mfc=color, label=name, **edge))
    ax.set_ylim(0, 1)
    ax.set_yticks([r0, (r0 + 1) / 2, 1.0])
    ax.set_yticklabels([])
    ax.set_xticks(angles)
    ax.set_xticklabels([])
    ax.grid(True, lw=0.35, alpha=0.45)
    ax.spines["polar"].set_linewidth(0.6)
    ax.spines["polar"].set_color(FRAME)
    # Axis name and its range (inner ring to outer ring), set outward from the end of the spoke.
    for theta, a in zip(angles, axes_names):
        disp = offset - theta
        c, s = math.cos(disp), math.sin(disp)
        ha = "center" if abs(c) < 0.3 else ("left" if c > 0 else "right")
        name_h, range_h = name_pt + 1.2, range_pt + 1.0
        block = name_h + range_h
        ox, oy = 1.6 * c, 1.6 * s
        top = oy + (block if s > 0.3 else (0.0 if s < -0.3 else block / 2))
        lo, hi = ranges[a]
        ax.annotate(a, xy=(theta, 1.0), xytext=(ox, top), textcoords="offset points", ha=ha, va="top",
                    fontsize=name_pt, color=DARK, annotation_clip=False)
        ax.annotate(f"{fmt.format(lo)}–{fmt.format(hi)}", xy=(theta, 1.0), xytext=(ox, top - name_h),
                    textcoords="offset points", ha=ha, va="top", fontsize=range_pt, color=MIDGRAY,
                    annotation_clip=False)
    return handles, ranges


def ts_effect_panel(ax, t, faulty, reference, onset: float, *, labels=("Faulty", "Fault-free"),
                    onset_label: str = "onset", effect_label: str = "effect", effect_xy=None,
                    xlabel: str | None = None, ylabel: str | None = None) -> list:
    """A faulty or corrupted run against its paired clean run, as in a time-series motivation figure.

    The two runs share their noise before the onset. The band between them after the onset is shaded red and
    labelled effect_label, the onset is a dashed vertical line labelled onset_label at the top of the panel.
    effect_xy places the effect label in data coordinates (default where the band is widest). Returns the two
    legend handles for inside_legend().
    """
    t = np.asarray(t, dtype=float)
    faulty = np.asarray(faulty, dtype=float)
    reference = np.asarray(reference, dtype=float)
    step = float(np.median(np.diff(t))) if len(t) > 1 else 1.0
    ax.fill_between(t, reference, faulty, where=t >= onset - step, color=RED, alpha=0.20, lw=0, zorder=2,
                    interpolate=True)
    ax.plot(t, faulty, color=RED, lw=2.2, zorder=4, solid_capstyle="round")
    ax.plot(t, reference, color=DARK, lw=1.2, zorder=5)
    ax.axvline(onset, color=FRAME, ls=(0, (3, 2)), lw=1.1, zorder=3)
    lo = float(np.nanmin([faulty.min(), reference.min()]))
    hi = float(np.nanmax([faulty.max(), reference.max()]))
    span = hi - lo or 1.0
    ax.set_ylim(lo - 0.08 * span, hi + 0.22 * span)       # head room for the onset label
    ax.set_xlim(t.min(), t.max())
    compact_ticks(ax, "y", nbins=3)
    xspan = t.max() - t.min()
    # The label is anchored in data coordinates, so a legend that widens the top limit ends up above it.
    ax.text(onset + 0.03 * xspan, hi + 0.19 * span, onset_label, fontsize=NOTE, va="top", ha="left", color=DARK,
            zorder=6)
    if effect_xy is None:
        after = t >= onset
        gap = np.where(after, np.abs(faulty - reference), -np.inf)
        win = max(3, int(0.12 * len(t)))
        smooth = np.array([gap[max(0, i - win // 2): i + win // 2 + 1].min() for i in range(len(t))])
        i = int(np.argmax(smooth))
        effect_xy = (t[i], (faulty[i] + reference[i]) / 2)
    ax.text(effect_xy[0], effect_xy[1], effect_label, fontsize=NOTE, va="center", ha="center", color=EFFECT_TEXT,
            zorder=6)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    frame(ax, "y")
    return [Line2D([], [], color=RED, lw=2.2, label=labels[0]), Line2D([], [], color=DARK, lw=1.2, label=labels[1])]


def heatmap(ax, matrix, rows, cols, *, center: float = 0.0, limit: float | None = None, cmap: str = "RdBu_r",
            annotate: float | None = None, fmt: str = "{:.0f}", xlabel: str | None = None,
            ylabel: str | None = None):
    """Diverging heat map with white cell borders, as in a gain-per-regime panel.

    The colour scale is centred on center and symmetric up to limit (default the largest absolute deviation),
    so two heat maps with the same limit share one colour key (colorbar_key). Cells whose absolute deviation
    reaches annotate carry their value, in white on dark cells. Returns the image for colorbar_key().
    """
    m = np.asarray(matrix, dtype=float)
    limit = limit if limit is not None else float(np.nanmax(np.abs(m - center))) or 1.0
    norm = TwoSlopeNorm(vmin=center - limit, vcenter=center, vmax=center + limit)
    img = ax.imshow(m, cmap=cmap, norm=norm, aspect="auto", zorder=1)
    if annotate is not None:
        for i, row in enumerate(m):
            for j, v in enumerate(row):
                if np.isfinite(v) and abs(v - center) >= annotate:
                    ax.text(j, i, fmt.format(v).replace("-", "−"), ha="center", va="center", fontsize=VALUE,
                            color="white" if abs(v - center) > 0.55 * limit else DARK, zorder=3)
    ax.set_xticks(range(m.shape[1]))
    ax.set_xticklabels([str(c) for c in cols])
    ax.set_yticks(range(m.shape[0]))
    ax.set_yticklabels([str(r) for r in rows])
    ax.set_xticks(np.arange(-0.5, m.shape[1]), minor=True)
    ax.set_yticks(np.arange(-0.5, m.shape[0]), minor=True)
    ax.grid(which="minor", color="white", lw=0.45)
    ax.tick_params(which="both", length=0, pad=1.7, labelsize=TICK)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.8)
        spine.set_color(FRAME)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    return img


def colorbar_key(fig, image, axes, ticks=None, label: str | None = None, gap_pt: float = 3.0,
                 height: float = 0.055, inset: float = 0.06):
    """Horizontal colour key above the given heat map panels, in the same row as a shared method legend.
    Tick labels sit on top of the bar, label (for example the unit 'pp') to its right. Returns the key axes."""
    r = _renderer(fig)
    fw, fh = fig.get_size_inches()
    top = max(a.get_tightbbox(r).y1 for a in _content_axes(fig)) / fig.dpi
    x0 = min(a.get_position().x0 for a in axes) * fw + inset
    x1 = max(a.get_position().x1 for a in axes) * fw - inset - (0.18 if label else 0.0)
    cax = fig.add_axes([x0 / fw, (top + gap_pt / 72) / fh, (x1 - x0) / fw, height / fh])
    cax._figstyle_key = True
    cb = fig.colorbar(image, cax=cax, orientation="horizontal", ticks=ticks)
    cb.ax.tick_params(labelsize=VALUE, length=1.2, pad=0.6)
    cb.ax.xaxis.set_ticks_position("top")
    cb.ax.xaxis.set_major_formatter(FuncFormatter(_decimal))
    cb.outline.set_linewidth(0.6)
    if label:
        cax.text(1.0 + 0.04 / ((x1 - x0) or 1.0), 0.5, label, transform=cax.transAxes, fontsize=VALUE,
                 va="center", ha="left")
    return cax


# ------------------------------------------------------------------------------------------------ export
def min_font(fig) -> float:
    """Smallest font size in points among the visible, non-empty texts of the figure."""
    sizes = [t.get_fontsize() for t in fig.findobj(matplotlib.text.Text) if t.get_visible() and t.get_text().strip()]
    return float(min(sizes)) if sizes else float("nan")


def _overlap(a, b, pad: float = 0.0) -> bool:
    return not (a.x1 + pad <= b.x0 or b.x1 + pad <= a.x0 or a.y1 + pad <= b.y0 or b.y1 + pad <= a.y0)


def _problems(fig) -> list:
    """Layout faults that make a figure unfit for print."""
    r = _renderer(fig)
    dpi = fig.dpi
    fw = fig.get_figwidth()
    out = []
    bb = fig.get_tightbbox(r)
    if bb.x0 < -0.02 or bb.x1 > fw + 0.02:
        out.append(f"an artist leaves the canvas sideways: content spans {bb.x0:.3f} to {bb.x1:.3f} in, "
                   f"canvas width {fw:.3f} in")
    caps = [(t.get_text(), t.get_window_extent(r)) for t in getattr(fig, "_figstyle_captions", [])]
    for i in range(len(caps)):
        for j in range(i + 1, len(caps)):
            if _overlap(caps[i][1], caps[j][1], pad=2 * dpi / 72):
                out.append(f"captions {caps[i][0]!r} and {caps[j][0]!r} are closer than 2 pt")
    legends = list(fig.legends) + [a.get_legend() for a in fig.axes if a.get_legend() is not None]
    lboxes = [leg.get_window_extent(r) for leg in legends]
    for i in range(len(lboxes)):
        for j in range(i + 1, len(lboxes)):
            if _overlap(lboxes[i], lboxes[j], pad=2 * dpi / 72):
                out.append("two legends are closer than 2 pt")
        for text, cb in caps:
            if _overlap(lboxes[i], cb):
                out.append(f"a legend overlaps the caption {text!r}")
    for leg, lb in zip(fig.legends, lboxes):
        for ax in fig.axes:
            if getattr(ax, "_figstyle_key", False):
                continue
            if _overlap(lb, ax.get_window_extent(r)):
                out.append("a figure legend overlaps a panel")
    for ax in fig.axes:
        leg = ax.get_legend()
        if leg is not None and getattr(leg, "_figstyle_inside", False):
            hidden = _covered(leg.get_window_extent(r), _obstacles(ax), 0.0)
            if hidden > 0:
                out.append("an inside legend covers data")
    return out


def save(fig, stem, formats=("pdf", "svg", "png"), dpi: int = 450, strict: bool = True, pad: float = 0.022) -> dict:
    """Place the captions, check the layout, crop the height to the content and write stem.pdf/.svg/.png.

    The canvas width is kept, so LaTeX includes the figure at scale one with width=\\textwidth or \\columnwidth.
    strict=True raises ValueError on a layout fault (artist outside the canvas width, overlapping captions or
    legends, a legend covering data), strict=False only warns. Returns a record with the printed size, the
    smallest font size and the written files.
    """
    place_captions(fig)
    problems = _problems(fig)
    if problems:
        message = "; ".join(problems)
        if strict:
            raise ValueError("figure layout: " + message)
        warnings.warn("figure layout: " + message)
    r = _renderer(fig)
    bb = fig.get_tightbbox(r)
    fw = fig.get_figwidth()
    crop = mtransforms.Bbox.from_extents(0, bb.y0 - pad, fw, bb.y1 + pad)
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    files = []
    for ext in formats:
        path = stem.with_suffix("." + ext)
        fig.savefig(path, dpi=dpi, bbox_inches=crop, pad_inches=0)
        files.append(str(path))
    smallest = min_font(fig)
    if smallest < LEGEND_MIN - 1e-6:
        warnings.warn(f"smallest font {smallest:.1f} pt is below {LEGEND_MIN} pt")
    return {"width_in": round(fw, 3), "height_in": round(crop.height, 3), "min_font_pt": smallest,
            "files": files, "problems": problems}

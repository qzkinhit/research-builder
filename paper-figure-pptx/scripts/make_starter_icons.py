#!/usr/bin/env python3
"""Generate the starter icon library of paper-figure-pptx.

Writes assets/icon-library/starter/
    svg/<id>.svg          hand-written vector icons on a 64 x 64 canvas, one palette, one stroke width
    fallback/<id>.png     PNG fallbacks at 256 px (needs cairosvg, skipped with a message otherwise)
    manifest.json         id, meaning, tags, files and SHA256 of every icon
    contact-sheet.png     overview for choosing by eye (needs Pillow and the PNG fallbacks)

The icons are original drawings made for this skill, released with the repository license. This script is their
editable design source: change a shape here and rerun, never edit the generated files by hand.

Usage:
    python scripts/make_starter_icons.py [--out DIR]
On macOS with Homebrew cairo, cairosvg may need DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

INK = "#2B3A55"
BLUE, BLUE_L = "#2F6DB5", "#DCE8F6"
ORANGE, ORANGE_L = "#F28E2B", "#FDE8D3"
GREEN, GREEN_L = "#59A14F", "#E1F0DE"
RED, RED_L = "#D62728", "#F9DADA"
PURPLE, PURPLE_L = "#8E6BB8", "#ECE4F5"
GRAY, GRAY_L = "#5A6270", "#E9ECF0"
SW = 2.4  # stroke width on the 64 x 64 canvas


def svg(body: str) -> str:
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64" '
            f'fill="none" stroke="{INK}" stroke-width="{SW}" stroke-linecap="round" stroke-linejoin="round">'
            f"{body}</svg>\n")


def cylinder(cx=32, top=14, rx=18, ry=7, h=34, fill=BLUE_L, cap=BLUE):
    l, r, b = cx - rx, cx + rx, top + h
    bands = "".join(f'<path d="M{l} {y}c0 3.9 8 {ry} {rx} {ry}s{rx}-3.1 {rx}-{ry}"/>' for y in (top + h / 3, top + 2 * h / 3))
    return (f'<path d="M{l} {top}v{h}c0 3.9 8 {ry} {rx} {ry}s{rx}-3.1 {rx}-{ry}V{top}" fill="{fill}"/>'
            f'<ellipse cx="{cx}" cy="{top}" rx="{rx}" ry="{ry}" fill="{cap}"/>{bands}')


def gear_path(cx=32, cy=32, r_out=22, r_in=16.5, teeth=8):
    pts = []
    for k in range(teeth):
        a0 = 2 * math.pi * k / teeth
        for da, r in ((-0.20, r_in), (-0.12, r_out), (0.12, r_out), (0.20, r_in)):
            a = a0 + da
            pts.append(f"{cx + r * math.cos(a):.2f} {cy + r * math.sin(a):.2f}")
        a = a0 + math.pi / teeth
        pts.append(f"{cx + r_in * math.cos(a):.2f} {cy + r_in * math.sin(a):.2f}")
    return "M" + " L".join(pts) + " Z"


ICONS = {
    "database": ("数据集、数据源、数据池", ["data", "source", "pool"], cylinder()),
    "database-warning": ("数据质量问题，如缺失、异常、重复、错误值", ["quality issue", "error"],
                         cylinder(cx=27, top=12, rx=16, ry=6, h=30) +
                         f'<path d="M45 34 L58 56 H32 Z" fill="{ORANGE}"/>'
                         '<path d="M45 42v6" stroke="white" stroke-width="3"/>'
                         '<circle cx="45" cy="52" r="0.6" stroke="white" stroke-width="2.6"/>'),
    "shield-check": ("质量保障、真实性", ["quality assurance", "authenticity"],
                     f'<path d="M32 6 L52 13 V30 C52 44 43 53 32 58 C21 53 12 44 12 30 V13 Z" fill="{GREEN_L}"/>'
                     f'<path d="M22 31 l7 7 l13 -14" stroke="{GREEN}" stroke-width="4.2"/>'),
    "magnifier-signal": ("检测、分析", ["detection", "analysis"],
                         '<circle cx="27" cy="27" r="17" fill="white"/>'
                         f'<path d="M14 29 h5 l3 -8 l5 15 l4 -11 l3 4 h6" stroke="{RED}" stroke-width="2.6"/>'
                         '<path d="M40 40 L54 54" stroke-width="6.5"/>'),
    "gear": ("模型、处理流程、指标聚合", ["model", "process", "aggregation"],
             f'<path d="{gear_path()}" fill="{ORANGE_L}"/><circle cx="32" cy="32" r="7" fill="{ORANGE}"/>'),
    "gauge": ("评估、优化校验", ["evaluation", "validation"],
              f'<path d="M10 42 A22 22 0 0 1 54 42 Z" fill="{BLUE_L}"/>'
              f'<path d="M10 42 A22 22 0 0 1 21 23" stroke="{RED}" stroke-width="4"/>'
              f'<path d="M43 23 A22 22 0 0 1 54 42" stroke="{GREEN}" stroke-width="4"/>'
              '<path d="M32 42 L44 28" stroke-width="3.4"/><circle cx="32" cy="42" r="3.2" fill="white"/>'
              '<path d="M14 54 H50"/>'),
    "pie-bars": ("质量维度刻画、统计分析", ["statistics", "dimensions"],
                 f'<circle cx="21" cy="25" r="13" fill="{BLUE_L}"/>'
                 f'<path d="M21 25 V12 A13 13 0 0 1 33.4 29 Z" fill="{BLUE}"/>'
                 f'<rect x="38" y="30" width="6" height="22" fill="{ORANGE}"/>'
                 f'<rect x="48" y="20" width="6" height="32" fill="{GREEN}"/>'
                 '<path d="M8 56 H58"/>'
                 f'<path d="M12 44 l4 4 l8 -8" stroke="{GREEN}" stroke-width="3.2"/>'),
    "network-model": ("模型反馈、关联建模", ["model feedback", "relations"],
                      '<path d="M32 12 L14 26 L20 48 L44 48 L50 26 Z M32 12 L32 32 L14 26 M32 32 L20 48 M32 32 L44 48 M32 32 L50 26"'
                      f' stroke="{PURPLE}" stroke-width="2"/>' +
                      "".join(f'<circle cx="{x}" cy="{y}" r="5.2" fill="{PURPLE_L}"/>'
                              for x, y in ((32, 12), (14, 26), (20, 48), (44, 48), (50, 26))) +
                      f'<circle cx="32" cy="32" r="6.5" fill="{PURPLE}"/>'),
    "lightbulb": ("创新点、可解释", ["idea", "explanation"],
                  f'<path d="M32 8 C20 8 13 17 13 27 C13 35 18 39 22 44 V48 H42 V44 C46 39 51 35 51 27 C51 17 44 8 32 8 Z" fill="{ORANGE_L}"/>'
                  '<path d="M24 53 H40 M27 58 H37"/>'
                  f'<path d="M27 36 L32 26 L37 36" stroke="{ORANGE}" stroke-width="2.6"/>'),
    "diamond": ("高价值数据", ["high value"],
                f'<path d="M18 12 H46 L58 26 L32 56 L6 26 Z" fill="{BLUE_L}"/>'
                f'<path d="M6 26 H58 M18 12 L26 26 L32 56 L38 26 L46 12 M26 26 L32 12 L38 26" stroke="{BLUE}" stroke-width="2"/>'),
    "document-check": ("报告、规则、标注", ["report", "rule", "annotation"],
                       f'<path d="M14 6 H38 L50 18 V58 H14 Z" fill="{GRAY_L}"/><path d="M38 6 V18 H50"/>'
                       '<path d="M21 26 H43 M21 34 H43 M21 42 H33"/>'
                       f'<circle cx="46" cy="48" r="9" fill="{GREEN}"/>'
                       '<path d="M41.5 48 l3 3 l6 -6" stroke="white" stroke-width="2.8"/>'),
    "tree-boxes": ("层级结构、模型需求", ["hierarchy", "requirements"],
                   f'<rect x="22" y="6" width="20" height="14" rx="3" fill="{BLUE}"/>'
                   '<path d="M32 20 V30 M14 30 H50 M14 30 V40 M50 30 V40 M32 30 V40"/>'
                   f'<rect x="5" y="40" width="18" height="14" rx="3" fill="{BLUE_L}"/>'
                   f'<rect x="23" y="40" width="18" height="14" rx="3" fill="{BLUE_L}"/>'
                   f'<rect x="41" y="40" width="18" height="14" rx="3" fill="{BLUE_L}"/>'),
    "flow-nodes": ("修复策略集、流程编排", ["workflow", "orchestration"],
                   f'<rect x="4" y="10" width="18" height="14" rx="3" fill="{GREEN_L}"/>'
                   f'<rect x="42" y="10" width="18" height="14" rx="3" fill="{GREEN_L}"/>'
                   f'<rect x="23" y="40" width="18" height="14" rx="3" fill="{GREEN}"/>'
                   '<path d="M22 17 H38 M34 13 L38 17 L34 21"/>'
                   '<path d="M51 24 V34 Q51 47 41 47 M45 43 L41 47 L45 51"/>'),
    "sensor-wave": ("原始工业数据、采集", ["sensor", "acquisition", "time series"],
                    f'<rect x="8" y="22" width="16" height="22" rx="3" fill="{GRAY_L}"/>'
                    '<path d="M16 44 V54 M10 54 H22"/>'
                    f'<path d="M28 26 Q33 33 28 40 M33 22 Q41 33 33 44" stroke="{BLUE}"/>'
                    f'<path d="M38 50 l4 -6 l4 4 l4 -12 l4 8 l4 -4" stroke="{RED}" stroke-width="2.2"/>'),
    "table": ("表格数据、关系数据", ["table", "relational"],
              f'<rect x="8" y="10" width="48" height="44" rx="3" fill="white"/>'
              f'<path d="M8 13 a3 3 0 0 1 3 -3 H53 a3 3 0 0 1 3 3 V21 H8 Z" fill="{BLUE}"/>'
              '<path d="M8 32 H56 M8 43 H56 M24 21 V54 M40 21 V54"/>'
              f'<rect x="41.5" y="33.5" width="13" height="8" fill="{RED_L}" stroke="none"/>'),
    "chip-model": ("基础模型、大模型", ["foundation model", "LLM"],
                   f'<rect x="16" y="16" width="32" height="32" rx="4" fill="{PURPLE_L}"/>'
                   f'<rect x="24" y="24" width="16" height="16" rx="2" fill="{PURPLE}"/>'
                   '<path d="M24 8 V16 M32 8 V16 M40 8 V16 M24 48 V56 M32 48 V56 M40 48 V56 '
                   'M8 24 H16 M8 32 H16 M8 40 H16 M48 24 H56 M48 32 H56 M48 40 H56"/>'),
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    here = Path(__file__).resolve().parent.parent
    ap.add_argument("--out", type=Path, default=here / "assets" / "icon-library" / "starter")
    out = ap.parse_args().out
    (out / "svg").mkdir(parents=True, exist_ok=True)
    (out / "fallback").mkdir(parents=True, exist_ok=True)
    try:
        import cairosvg
    except (ImportError, OSError):
        cairosvg = None
        print("cairosvg unavailable, PNG fallbacks and the contact sheet are skipped")
    manifest = []
    for icon_id, (meaning, tags, body) in ICONS.items():
        text = svg(body)
        sp = out / "svg" / f"{icon_id}.svg"
        sp.write_text(text, encoding="utf-8")
        entry = {"id": icon_id, "meaning": meaning, "tags": tags, "author_type": "self-designed",
                 "style": "64 px canvas, 2.4 px ink stroke, shared palette of figure-archetypes.md",
                 "svg": f"svg/{icon_id}.svg", "svg_sha256": hashlib.sha256(text.encode()).hexdigest()}
        if cairosvg:
            pp = out / "fallback" / f"{icon_id}.png"
            cairosvg.svg2png(bytestring=text.encode(), write_to=str(pp), output_width=256, output_height=256)
            entry["png"] = f"fallback/{icon_id}.png"
            entry["png_sha256"] = hashlib.sha256(pp.read_bytes()).hexdigest()
        manifest.append(entry)
    (out / "manifest.json").write_text(json.dumps({"library": "starter", "count": len(manifest),
                                                   "icons": manifest}, ensure_ascii=False, indent=1) + "\n",
                                       encoding="utf-8")
    if cairosvg:
        contact_sheet(out, manifest)
    print("wrote %d icons to %s" % (len(manifest), out))


def contact_sheet(out: Path, manifest: list, cols: int = 8, cell: int = 150) -> None:
    from PIL import Image, ImageDraw, ImageFont
    try:
        import matplotlib
        font = ImageFont.truetype(str(Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf"), 15)
    except Exception:
        font = ImageFont.load_default()
    rows = math.ceil(len(manifest) / cols)
    sheet = Image.new("RGB", (cols * cell, rows * cell), "white")
    draw = ImageDraw.Draw(sheet)
    for k, e in enumerate(manifest):
        x, y = (k % cols) * cell, (k // cols) * cell
        im = Image.open(out / e["png"]).convert("RGBA").resize((96, 96))
        sheet.paste(im, (x + (cell - 96) // 2, y + 12), im)
        w = draw.textlength(e["id"], font=font)
        draw.text((x + (cell - w) / 2, y + 118), e["id"], fill=INK, font=font)
    sheet.save(out / "contact-sheet.png")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Compare the layout of two builds of a two-column paper, column by column.

A text edit that looks harmless can move a float, open a gap above a heading or
push the last line onto the next page. Comparing only the bottom of each column
misses most of this, because flushbottom stretches glue until the bottoms agree
again. This script compares, for every page and column, the full set of line
positions, the last line, and the largest vertical gap.

    python tools/layout_diff.py reference.pdf new.pdf
    python tools/layout_diff.py reference.pdf new.pdf --tol 1.5 --gap 13

Exit status is 0 when every column matches within the tolerance, 1 otherwise.
Needs pdftotext from poppler.
"""
import argparse
import re
import subprocess
import sys
from html import unescape

LINE = re.compile(r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</line>', re.S)
WORD = re.compile(r'<word[^>]*>(.*?)</word>', re.S)
PAGE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', re.S)


def pages(pdf):
    xml = subprocess.run(['pdftotext', '-bbox-layout', pdf, '-'],
                         capture_output=True, text=True, check=True).stdout
    out = []
    for w, h, body in PAGE.findall(xml):
        lines = []
        for x0, y0, x1, y1, inner in LINE.findall(body):
            text = ' '.join(unescape(t) for t in WORD.findall(inner))
            lines.append((float(x0), float(y0), float(x1), float(y1), text))
        out.append((float(w), float(h), lines))
    return out


def columns(page, top, bottom):
    w, h, lines = page
    split = w / 2
    cols = {'L': [], 'R': []}
    for x0, y0, x1, y1, t in lines:
        if y1 < top * h or y0 > bottom * h:
            continue  # running head and folio
        cols['L' if x0 < split else 'R'].append((round(y1, 1), t))
    for k in cols:
        cols[k].sort()
    return cols


def summary(col, gap):
    ys = sorted({y for y, _ in col})
    gaps = [round(b - a, 1) for a, b in zip(ys, ys[1:]) if b - a > gap]
    last = col[-1][1][:60] if col else ''
    return ys, gaps, last


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('reference')
    ap.add_argument('new')
    ap.add_argument('--tol', type=float, default=1.2, help='points of drift tolerated per line')
    ap.add_argument('--gap', type=float, default=13.0, help='report vertical gaps larger than this')
    ap.add_argument('--top', type=float, default=0.06, help='fraction of the page treated as running head')
    ap.add_argument('--bottom', type=float, default=0.95, help='fraction below which the folio sits')
    a = ap.parse_args()

    ref, new = pages(a.reference), pages(a.new)
    print(f'pages: reference {len(ref)}, new {len(new)}')
    differ = 0
    for i in range(max(len(ref), len(new))):
        for k in ('L', 'R'):
            r = summary(columns(ref[i], a.top, a.bottom)[k], a.gap) if i < len(ref) else ([], [], '')
            n = summary(columns(new[i], a.top, a.bottom)[k], a.gap) if i < len(new) else ([], [], '')
            same_count = len(r[0]) == len(n[0])
            same_pos = same_count and all(abs(x - y) <= a.tol for x, y in zip(r[0], n[0]))
            if same_pos and r[2] == n[2]:
                continue
            differ += 1
            print(f'p{i + 1}{k}: lines {len(r[0])} -> {len(n[0])}, bottom '
                  f'{(r[0] or [0])[-1]} -> {(n[0] or [0])[-1]}')
            if r[2] != n[2]:
                print(f'    last line  ref: {r[2]!r}\n               new: {n[2]!r}')
            if r[1] != n[1]:
                print(f'    gaps > {a.gap}pt  ref: {r[1]}  new: {n[1]}')
    print('identical within tolerance' if not differ else f'{differ} column(s) differ')
    sys.exit(1 if differ else 0)


if __name__ == '__main__':
    main()

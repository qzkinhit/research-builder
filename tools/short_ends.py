#!/usr/bin/env python3
"""List paragraph-final lines short enough for \\looseness=-1 to be worth a try.

\\looseness=-1 asks TeX to set a paragraph one line shorter. It succeeds only when
the last line is short and the paragraph has enough lines to absorb it, so trying
it on every paragraph wastes builds. The script lists, per page and column, the
lines that end a paragraph (the next line of the column is indented, sits after a
larger gap, or does not exist) and fill less than --max-frac of the column width,
with the number of lines of that paragraph seen on the same column.

    python tools/short_ends.py paper.pdf --pages 3-5 --max-frac 0.35

Needs pdftotext from poppler.
"""
import argparse
import re
import statistics
import subprocess
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


def page_range(spec, n):
    if not spec:
        return range(1, n + 1)
    lo, _, hi = spec.partition('-')
    return range(int(lo), int(hi or lo) + 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('pdf')
    ap.add_argument('--pages', default='', help='page range such as 3-5, default all')
    ap.add_argument('--max-frac', type=float, default=0.35, help='report last lines narrower than this share of the column')
    ap.add_argument('--indent', type=float, default=6.0, help='points of indent that mark a new paragraph')
    ap.add_argument('--top', type=float, default=0.06)
    ap.add_argument('--bottom', type=float, default=0.95)
    a = ap.parse_args()

    pp = pages(a.pdf)
    for pno in page_range(a.pages, len(pp)):
        if pno > len(pp):
            break
        w, h, lines = pp[pno - 1]
        lines = [l for l in lines if l[3] >= a.top * h and l[1] <= a.bottom * h]
        for k in ('L', 'R'):
            col = sorted((l for l in lines if (l[0] < w / 2) == (k == 'L')), key=lambda l: l[1])
            if len(col) < 3:
                continue
            widths = [l[2] - l[0] for l in col]
            full = max(widths)
            body = [l for l in col if l[2] - l[0] > 0.8 * full]
            if not body:
                continue
            left = min(l[0] for l in body)
            leading = statistics.median(b[1] - a_[1] for a_, b in zip(body, body[1:])) if len(body) > 1 else 11.0
            start = 0
            for i, l in enumerate(col):
                nxt = col[i + 1] if i + 1 < len(col) else None
                ends = (nxt is None or nxt[0] > left + a.indent or nxt[1] - l[1] > 1.6 * leading)
                if not ends:
                    continue
                frac = (l[2] - l[0]) / full
                n = i - start + 1
                if frac < a.max_frac and n >= 3 and re.search(r'[.)\]:]\s*$', l[4]):
                    print(f'p{pno}{k} y={l[1]:.0f} last line {frac:.0%} of the column, '
                          f'{n} lines seen: {l[4][:70]}')
                start = i + 1


if __name__ == '__main__':
    main()

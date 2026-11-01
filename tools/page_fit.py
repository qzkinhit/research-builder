#!/usr/bin/env python3
"""Report the fixed points of a page-limited two-column paper after an edit.

An edit near the page limit must not move a few things: the page on which the
references start, the pages that hold the large floats, the gap above the first
heading of a page, and the last body lines of the last allowed page. Run this on
the previous build and on the new one and compare the two reports before the new
PDF replaces the submitted one. layout_diff.py compares every line, this script
answers the questions a page budget asks.

    python tools/page_fit.py paper.pdf --heading "PROBLEM STATEMENT" \
        --captions "Table 1,Table 4" --last-body-page 12

With --last-body-page the exit status is 1 when the references do not start on
the page after it. Needs pdftotext from poppler.
"""
import argparse
import re
import subprocess
import sys
from html import unescape

LINE = re.compile(r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</line>', re.S)
WORD = re.compile(r'<word[^>]*>(.*?)</word>', re.S)
PAGE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', re.S)
REFS = re.compile(r'^(REFERENCES|References|参考文献)\b')


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


def body_lines(page, top, bottom):
    """Lines between the running head and the folio. A bare page number near the foot is the folio."""
    w, h, lines = page
    return [l for l in lines if l[3] >= top * h and l[1] <= bottom * h
            and not (l[4].strip().isdigit() and l[1] > 0.85 * h)]


def column(line, width):
    return 'L' if line[0] < width / 2 else 'R'


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('pdf')
    ap.add_argument('--heading', action='append', default=[],
                    help='text of a heading whose gap to the line above is reported (repeatable)')
    ap.add_argument('--captions', default='', help='comma-separated caption labels, e.g. "Table 1,Figure 4"')
    ap.add_argument('--last-body-page', type=int, default=0, help='last page allowed for body text')
    ap.add_argument('--top', type=float, default=0.06, help='fraction of the page treated as running head')
    ap.add_argument('--bottom', type=float, default=0.95, help='fraction below which the folio sits')
    a = ap.parse_args()

    pp = pages(a.pdf)
    print(f'pages: {len(pp)}')
    found = {}
    for i, page in enumerate(pp, 1):
        for x0, y0, x1, y1, t in body_lines(page, a.top, a.bottom):
            for cap in filter(None, (c.strip() for c in a.captions.split(','))):
                if cap not in found and re.match(re.escape(cap) + r'\s*[:.：]', t):
                    found[cap] = i
            if 'references' not in found and REFS.match(t):
                found['references'] = i
    for k, v in found.items():
        print(f'{k}: page {v}')

    upto = min(len(pp), (a.last_body_page or len(pp)) + 1)
    bottoms = []
    for i in range(upto):
        w = pp[i][0]
        lines = body_lines(pp[i], a.top, a.bottom)
        cols = {'L': [l[3] for l in lines if column(l, w) == 'L'], 'R': [l[3] for l in lines if column(l, w) == 'R']}
        bottoms.append(f"p{i + 1}:{max(cols['L'], default=0):.0f}/{max(cols['R'], default=0):.0f}")
    print('column bottoms', ' '.join(bottoms))

    for head in a.heading:
        for i, page in enumerate(pp, 1):
            w = page[0]
            lines = body_lines(page, a.top, a.bottom)
            for l in lines:
                if head in l[4]:
                    above = [m for m in lines if column(m, w) == column(l, w) and m[3] <= l[1] + 0.5 and m is not l]
                    if above:
                        prev = max(above, key=lambda m: m[3])
                        print(f'"{head}" on p{i}{column(l, w)}: gap {l[1] - prev[3]:.1f}pt below "{prev[4][:50]}"')
                    else:
                        print(f'"{head}" on p{i}{column(l, w)}: first line of the column')

    status = 0
    if a.last_body_page and a.last_body_page <= len(pp):
        page = pp[a.last_body_page - 1]
        w = page[0]
        lines = body_lines(page, a.top, a.bottom)
        for k in ('L', 'R'):
            col = sorted((l for l in lines if column(l, w) == k), key=lambda l: l[3])
            print(f'p{a.last_body_page}{k} last line: {col[-1][4][:80] if col else ""}')
        refs = found.get('references')
        if refs != a.last_body_page + 1:
            print(f'references start on page {refs}, expected {a.last_body_page + 1}')
            status = 1
    sys.exit(status)


if __name__ == '__main__':
    main()

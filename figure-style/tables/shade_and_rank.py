"""Rank, shade and format the rows of a main results table in the table style of figure-style/tables.

Input is a CSV with one row per method and the columns
    method, family, <col 1>, <col 2>, ...
The proposed method is the row whose family is "ours" and goes last. Higher is better in every column unless the
column name ends with "(lower)". An empty cell is printed as a red placeholder (\\pend) and its column is left out of
the ranks, so a table with placeholders is visibly unfinished.

Output is the LaTeX body between \\midrule and \\bottomrule of the main table:
    * one bold italic group row (\\grp) per family, families in the order of the CSV or of --families
    * the rank column, the mean of the per-column ranks, computed on the printed values (ties share the average
      rank), then ordered by mean rank and, for equal mean ranks, by the mean printed value
    * the best printed value of each column wrapped in \\best (dark background, bold) and the second best in
      \\secondbest (light background), ties share the shade, both decided on the printed values so that a reader can
      check them from the table
    * a \\midrule and \\oursrow before the row of the proposed method
Everything is decided on printed values, so the table, its shading and its ranks agree with what the reader sees.

Usage:
    python shade_and_rank.py results.csv [--decimals 3] [--families "A,B,C"] [--name-macro "\\textbf{\\sys}"] > rows.tex
"""
import argparse
import csv
import sys


def read(path):
    with open(path, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    cols = [c for c in rows[0].keys() if c not in ('method', 'family')]
    return rows, cols


def printed(value, decimals):
    return None if value in ('', None) else round(float(value), decimals)


def column_ranks(values, lower_is_better):
    """Average ranks of a list of (method, value); equal values share the mean of their positions."""
    order = sorted(values, key=lambda t: t[1] if lower_is_better else -t[1])
    ranks, i = {}, 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and order[j + 1][1] == order[i][1]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k][0]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def render_rows(rows, cols, decimals=3, families=(), name_macro=''):
    """Return the LaTeX body of the main table for rows (dicts with method, family and one key per column).

    Importable, so a backfill script can write the same body into a marked block of the paper.
    """
    d = decimals
    vals = {r['method']: {c: printed(r[c], d) for c in cols} for r in rows}
    lower = {c: c.endswith('(lower)') for c in cols}

    # columns with a placeholder do not enter the ranks
    complete = [c for c in cols if all(vals[m][c] is not None for m in vals)]
    for c in cols:
        if c not in complete:
            print('warning: column %s has empty cells, printed as \\pend and left out of the ranks' % c, file=sys.stderr)
    per = {m: [] for m in vals}
    for c in complete:
        r = column_ranks([(m, vals[m][c]) for m in vals], lower[c])
        for m in vals:
            per[m].append(r[m])
    mean_rank = {m: sum(per[m]) / len(per[m]) if per[m] else float('inf') for m in vals}
    mean_val = {m: sum(vals[m][c] for c in complete) / max(1, len(complete)) for m in vals}
    order = sorted(vals, key=lambda m: (mean_rank[m], -mean_val[m]))
    final_rank = {m: i + 1 for i, m in enumerate(order)}

    # shading on printed values: best and second distinct value of each column
    shade = {}
    for c in cols:
        present = sorted({vals[m][c] for m in vals if vals[m][c] is not None}, reverse=not lower[c])
        best = present[0] if present else None
        second = present[1] if len(present) > 1 else None
        for m in vals:
            v = vals[m][c]
            if v is None:
                shade[m, c] = '\\pend{%s}' % ('0.' + 'x' * d)
            elif v == best:
                shade[m, c] = '\\best{%.*f}' % (d, v)
            elif v == second:
                shade[m, c] = '\\secondbest{%.*f}' % (d, v)
            else:
                shade[m, c] = '%.*f' % (d, v)

    ncol = 2 + len(cols)
    families = [f for f in families if f]
    for r in rows:
        if r['family'] != 'ours' and r['family'] not in families:
            families.append(r['family'])
    out = []
    for fam in families:
        members = [r['method'] for r in rows if r['family'] == fam]
        if not members:
            continue
        out.append('\\grp{%d}{%s} \\\\' % (ncol, fam))
        for m in members:
            out.append('%d & %s & %s \\\\' % (final_rank[m], m, ' & '.join(shade[m, c] for c in cols)))
    ours = [r['method'] for r in rows if r['family'] == 'ours']
    if ours:
        out.append('\\midrule')
        for m in ours:
            name = name_macro or '\\textbf{%s}' % m
            out.append('\\oursrow\n%d & %s & %s \\\\' % (final_rank[m], name, ' & '.join(shade[m, c] for c in cols)))
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv')
    ap.add_argument('--decimals', type=int, default=3)
    ap.add_argument('--families', default='')
    ap.add_argument('--name-macro', default='', help='LaTeX for the name of the proposed method, e.g. \\textbf{\\sys}')
    a = ap.parse_args()
    rows, cols = read(a.csv)
    print(render_rows(rows, cols, a.decimals, a.families.split(','), a.name_macro))


if __name__ == '__main__':
    main()

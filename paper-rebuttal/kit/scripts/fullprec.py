#!/usr/bin/env python3
"""Exact statistics on per-run records, rounding once, per-comparison bootstrap seeds.

Library for check_rounding.py and build_interval_map.py. Python standard library only.

Records are the rows of a CSV file with one row per run. The default columns are
method (the arm), dataset (the table), seed (the data split) and one or more
metric columns. A metric is a column name or num/den for the ratio of two
integer columns, in which case the value stays an exact fraction.

Aggregation follows the usual reporting order. Runs are averaged inside a cell
(arm, dataset, seed), cells are averaged inside a dataset, and datasets are
averaged with equal weight. Every step uses exact fractions. Rounding happens
once, at the end, from the exact value.
"""
from __future__ import annotations

import csv
import hashlib
import random
from collections import defaultdict
from fractions import Fraction


def read_runs(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def select(rows, spec):
    """Rows matching a filter such as "budget=5&dataset=D1". An empty filter keeps every row."""
    terms = [t.split("=", 1) for t in (spec or "").split("&") if t.strip()]
    return [r for r in rows if all(r.get(k.strip(), "") == v.strip() for k, v in terms)]


def value_of(row, metric):
    """Exact value of a metric in one row. "num/den" is the ratio of two columns."""
    if "/" in metric:
        num, den = metric.split("/", 1)
        return Fraction(row[num]) / Fraction(row[den])
    return Fraction(row[metric])


def cells(rows, metric, arm="method", table="dataset", seed="seed"):
    """{arm: {(table, seed): exact mean over runs}}."""
    runs = defaultdict(list)
    for r in rows:
        runs[(r[arm], r[table], r[seed])].append(value_of(r, metric))
    out = defaultdict(dict)
    for (a, t, s), v in runs.items():
        out[a][(t, s)] = sum(v, Fraction(0)) / len(v)
    return out


def per_table(cell_map):
    """{table: exact mean over seeds} of one arm, or of one paired difference."""
    by = defaultdict(list)
    for (t, _s), v in cell_map.items():
        by[t].append(v)
    return {t: sum(v, Fraction(0)) / len(v) for t, v in by.items()}


def grand_mean(table_values):
    """Exact mean of the table means, with equal weight per table."""
    return sum(table_values.values(), Fraction(0)) / len(table_values)


def paired_cells(values, a, b):
    """{(table, seed): a - b} over the cells both arms hold."""
    if a not in values or b not in values:
        raise KeyError(f"arm not in the records: {a if a not in values else b}")
    return {c: values[a][c] - values[b][c] for c in sorted(set(values[a]) & set(values[b]))}


def rnd(x, decimals):
    """Round an exact number half up (ties away from zero) and format it."""
    x = Fraction(x)
    sign = "-" if x < 0 else ""
    scaled = abs(x) * 10 ** decimals
    quo, rem = divmod(scaled.numerator, scaled.denominator)
    if 2 * rem >= scaled.denominator:
        quo += 1
    digits = str(quo).rjust(decimals + 1, "0")
    if quo == 0:
        sign = ""
    if decimals == 0:
        return sign + digits
    return f"{sign}{digits[:-decimals]}.{digits[-decimals:]}"


def call_rng(base_seed, *parts):
    """Generator of one bootstrap call, seeded from a SHA-256 hash of the strings that name the call.

    Each comparison owns its stream, so an interval depends only on its own cells. Adding rows, comparisons or
    experiments elsewhere leaves it unchanged. The sequence is identical across Python versions and processes.
    """
    text = "\x1f".join([str(base_seed), *parts])
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest, "big"))


def percentile(sorted_draws, q):
    """Percentile with linear interpolation."""
    pos = (len(sorted_draws) - 1) * q / 100
    low = int(pos)
    high = min(low + 1, len(sorted_draws) - 1)
    return sorted_draws[low] + (sorted_draws[high] - sorted_draws[low]) * (pos - low)


def paired_interval(diff_cells, n_boot, rng, level=95):
    """(point, low, high) of the mean of table means of paired differences.

    The interval is a percentile bootstrap that resamples seeds within each table. point is exact, low and high
    are floats kept to the end, so that the printed values still come from one rounding step.
    """
    groups = defaultdict(list)
    for (t, _s), v in diff_cells.items():
        groups[t].append(float(v))
    tables = sorted(groups)
    draws = []
    for _ in range(n_boot):
        total = 0.0
        for t in tables:
            xs = groups[t]
            total += sum(xs[int(rng.random() * len(xs))] for _i in range(len(xs))) / len(xs)
        draws.append(total / len(tables))
    draws.sort()
    tail = (100 - level) / 2
    return grand_mean(per_table(diff_cells)), percentile(draws, tail), percentile(draws, 100 - tail)

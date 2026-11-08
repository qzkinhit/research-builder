#!/usr/bin/env python3
"""Check every printed number against the per-run records at full precision.

usage: check_rounding.py --claims claims.csv --runs runs.csv [--root DIR] [--summary-decimals 4]

Claim columns (a CSV header line is required)
  id        a short name for the report
  kind      value, diff, within, within_each, at_least, at_least_each,
            at_most, at_most_each, wins
  printed   the number as printed, for example 0.867, +3.6 or 15 of 15
  decimals  digits after the decimal point of the printed number
  scale     multiplier before rounding, 100 for percentage points, empty means 1
  metric    a column name, or num/den for the ratio of two integer columns
  a, b      the arms, b is empty for kind value
  filter    rows that enter the computation, for example budget=5&dataset=D1
  bound     the bound of a within or at_least or at_most claim, in scaled units
  file      optional file (relative to --root) in which the printed number must occur

Meaning of the kinds
  value          printed equals the once-rounded mean of arm a
  diff           printed equals the once-rounded paired difference a - b
  within         |a - b| at full precision does not exceed bound
  at_least       a - b at full precision is at least bound, at_most is the mirror
  *_each         the same on every table separately
  wins           printed "n of m" equals the count of cells with a above b

A number that passes when the 4-decimal summary is rounded a second time but
fails when the exact value is rounded once is reported as DOUBLE ROUNDING. A
correct number whose 4-decimal summary would round differently is noted as a
trap, because a later copy from the summary would break it.

Exit status 1 if any claim fails.
"""
import argparse
import csv
import re
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fullprec import cells, grand_mean, paired_cells, per_table, read_runs, rnd, select  # noqa: E402

EACH = {"within_each", "at_least_each", "at_most_each"}


def number_of(printed):
    return printed.strip().lstrip("+")


def occurs(token, text):
    """True if the number occurs in the text as a whole number token."""
    return re.search(r"(?<![\d.])" + re.escape(token) + r"(?![\d])", text) is not None


def evaluate(claim, rows, summary_decimals):
    """Return (ok, shown, detail) for one claim."""
    kind = claim["kind"].strip()
    decimals = int(claim.get("decimals") or 0)
    scale = Fraction(claim.get("scale") or "1")
    values = cells(select(rows, claim.get("filter", "")), claim["metric"].strip())
    a, b = claim["a"].strip(), (claim.get("b") or "").strip()
    printed = claim["printed"].strip()
    if kind == "value":
        if a not in values:
            raise KeyError(f"arm not in the records: {a}")
        full = grand_mean(per_table(values[a]))
    else:
        if not b:
            raise ValueError(f"claim {claim['id']}: kind {kind} needs the arm b")
        pairs = paired_cells(values, a, b)
        tables = per_table(pairs)
        full = grand_mean(tables)
    if kind in ("value", "diff"):
        direct = rnd(full * scale, decimals)
        twice = rnd(Fraction(rnd(full, summary_decimals)) * scale, decimals)
        got = number_of(printed)
        shown = f"{float(full * scale):.6f}"
        if kind == "diff" and full > 0 and printed.startswith("-"):
            return False, shown, f"sign of printed {printed} disagrees with the exact value"
        if got != direct.lstrip("+") and got != direct:
            if got == twice:
                return False, shown, f"DOUBLE ROUNDING printed {printed}, exact rounding gives {direct}, the {summary_decimals}-decimal summary gives {twice}"
            return False, shown, f"printed {printed}, exact rounding gives {direct}"
        if direct != twice:
            return True, shown, f"trap avoided, the {summary_decimals}-decimal summary would give {twice}"
        return True, shown, ""
    if kind == "wins":
        n = sum(v > 0 for v in pairs.values())
        m = len(pairs)
        expected = f"{n} of {m}"
        return printed == expected, f"{n}/{m} cells", "" if printed == expected else f"printed {printed}, records give {expected}"
    bound = Fraction(claim["bound"])
    if kind in EACH:
        scaled = {t: v * scale for t, v in tables.items()}
        shown = "; ".join(f"{t} {float(v):.4f}" for t, v in sorted(scaled.items()))
        if kind == "within_each":
            bad = [t for t, v in scaled.items() if abs(v) > bound]
        elif kind == "at_least_each":
            bad = [t for t, v in scaled.items() if v < bound]
        else:
            bad = [t for t, v in scaled.items() if v > bound]
        return not bad, shown, "" if not bad else f"fails on {', '.join(sorted(bad))}"
    x = full * scale
    shown = f"{float(x):.6f}"
    ok = {"within": abs(x) <= bound, "at_least": x >= bound, "at_most": x <= bound}.get(kind)
    if ok is None:
        raise ValueError(f"claim {claim['id']}: unknown kind {kind}")
    return ok, shown, "" if ok else f"exact value {float(x):.6f} against bound {claim['bound']}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--claims", required=True)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--root", default=".", help="directory that the file column is relative to")
    ap.add_argument("--summary-decimals", type=int, default=4)
    args = ap.parse_args(argv)
    rows = read_runs(args.runs)
    with open(args.claims, newline="", encoding="utf-8") as handle:
        claims = [c for c in csv.DictReader(handle) if c["id"].strip() and not c["id"].startswith("#")]
    root = Path(args.root)
    failed = 0
    texts = {}
    for c in claims:
        try:
            ok, shown, detail = evaluate(c, rows, args.summary_decimals)
        except (KeyError, ValueError) as err:
            ok, shown, detail = False, "", str(err)
        rel = (c.get("file") or "").strip()
        if rel:
            p = root / rel
            texts.setdefault(rel, p.read_text(encoding="utf-8") if p.exists() else "")
            token = number_of(c["printed"]).split(" of ")[0]
            if not occurs(token, texts[rel]):
                ok = False
                detail = (detail + "; " if detail else "") + f"{token} does not occur in {rel}"
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {c['id']:6s} {c['kind']:14s} printed {c['printed']:9s} exact {shown}  {detail}")
    print(f"rounding check: {len(claims)} claims, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

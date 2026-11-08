#!/usr/bin/env python3
"""Build the interval map: every bracketed interval in the reply or the revision, its comparison and its recomputed value.

usage: build_interval_map.py --config kit.json --runs runs.csv --comparisons comparisons.json --out map.md
                             [--json map.json] [--root DIR] [--boot 10000] [--seed 0]

Skeleton to fill in for a new paper
  comparisons.json   one object per comparison, with the fields below
  load_values()      replace it if your run records are not one CSV per project

Fields of a comparison
  id        short name used in the map
  printed   list of the interval strings as printed, for example "[2.9, 4.5]"
  a, b      arms of the paired difference a - b
  metric    a column name, or num/den for the ratio of two integer columns
  filter    rows to use, for example budget=5
  scale     multiplier applied before printing, 100 for percentage points
  decimals  digits after the decimal point
  context   optional substring of the source line, to separate two comparisons
            that print the same interval

Each comparison gets its own random generator, seeded from the base seed and a
hash of its filter, metric and arms (fullprec.call_rng). An interval then depends
only on its own cells, so adding rows, comparisons or experiments elsewhere
leaves it unchanged. The map is read only and never edits the sources.

Files scanned: the responseen blocks of the key main of kit.json, and the whole
of every file matched by the key revision_en.

Exit status 1 if a printed interval differs from its recomputed value, an
interval is not mapped, or a mapping is ambiguous.
"""
import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fullprec import Fraction, call_rng, cells, paired_cells, paired_interval, read_runs, rnd, select  # noqa: E402

NUM = r"(?:\$-\$|\$\{-\}\$|\{-\}|-|\N{MINUS SIGN}|\\textminus\s*|\+)?\s*\$?\s*\d+(?:\.\d+)?\s*\$?"
BRACKET = re.compile(r"\[([^\[\]]{1,120})\]")
PAIR = re.compile(rf"^\s*\$?\s*({NUM})\s*,\s*({NUM})\s*\$?\s*$")


def clean_number(tok):
    return tok.replace("$", "").replace("{", "").replace("}", "").replace("\\textminus", "-").replace("\N{MINUS SIGN}", "-").replace(" ", "")


def extract(path, english_only):
    """[{file, line, start, raw, lo, hi}] and the bracket texts with a digit and a comma that are not intervals."""
    found, loose = [], []
    inside = not english_only
    for i, line in enumerate(Path(path).read_text(encoding="utf-8").split("\n"), 1):
        if english_only:
            if "\\begin{responseen}" in line:
                inside = True
            if "\\end{responseen}" in line:
                inside = False
                continue
            if not inside:
                continue
        code = re.sub(r"(?<!\\)%.*$", "", line)
        for m in BRACKET.finditer(code):
            p = PAIR.match(m.group(1))
            if not p:
                if re.search(r"\d", m.group(1)) and "," in m.group(1):
                    loose.append((path, i, m.group(0)))
                continue
            a, b = clean_number(p.group(1)), clean_number(p.group(2))
            if "." not in a and "." not in b:
                continue                      # integer pairs such as [1, 5] are citations or counts
            found.append({"file": path, "line": i, "start": m.start(), "raw": f"[{a}, {b}]", "text": code})
    return found, loose


def load_values(runs_path, comparison):
    """Cells of one comparison from the per-run CSV. Replace for another record format."""
    rows = read_runs(runs_path)
    return cells(select(rows, comparison.get("filter", "")), comparison["metric"])


def recompute(c, runs_path, base_seed, n_boot):
    values = load_values(runs_path, c)
    pairs = paired_cells(values, c["a"], c["b"])
    rng = call_rng(base_seed, c.get("filter", ""), c["metric"], c["a"], c["b"])
    point, lo, hi = paired_interval(pairs, n_boot, rng)
    scale = Fraction(str(c.get("scale", 1)))
    d = int(c.get("decimals", 1))
    return {"cells": len(pairs), "wins": sum(v > 0 for v in pairs.values()),
            "point": float(point * scale), "lo": float(Fraction(lo) * scale), "hi": float(Fraction(hi) * scale),
            "recomputed": f"[{rnd(Fraction(lo) * scale, d)}, {rnd(Fraction(hi) * scale, d)}]",
            "point_printed": rnd(point * scale, d)}


def fragment(text, start, end):
    s = text.rfind(". ", 0, start)
    s = 0 if s < 0 else s + 2
    frag = text[s:end]
    if len(frag) > 170:
        frag = "..." + frag[-167:]
    return frag.replace("|", "\\|").replace("\n", " ")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default="kit.json")
    ap.add_argument("--root", default=None)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--comparisons", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", default=None)
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    root = args.root or os.path.dirname(os.path.abspath(args.config))
    comps = json.loads(Path(args.comparisons).read_text(encoding="utf-8"))
    found, loose = extract(os.path.join(root, cfg["main"]), english_only=True)
    for pattern in cfg.get("revision_en", []):
        for f in sorted(glob.glob(os.path.join(root, pattern))):
            more, odd = extract(f, english_only=False)
            found += more
            loose += odd
    results = {c["id"]: recompute(c, args.runs, args.seed, args.boot) for c in comps}
    rows, bad = [], 0
    for k, f in enumerate(found, 1):
        hits = [c for c in comps if f["raw"] in c["printed"] and (not c.get("context") or c["context"] in f["text"])]
        rel = os.path.relpath(f["file"], root)
        frag = fragment(f["text"], f["start"], f["start"] + len(f["raw"]))
        if len(hits) != 1:
            bad += 1
            status = "UNMAPPED" if not hits else "AMBIGUOUS: " + ", ".join(c["id"] for c in hits)
            rows.append((k, rel, f["line"], frag, f["raw"], status, "", "", ""))
            continue
        c = hits[0]
        r = results[c["id"]]
        changed = f["raw"] != r["recomputed"]
        bad += changed
        comp = f"{c['a']} \N{MINUS SIGN} {c['b']}, {c['metric']}, {c.get('filter', '')}"
        rows.append((k, rel, f["line"], frag, f["raw"], comp, r["recomputed"], "yes" if changed else "no", c["id"]))
    lines = ["# 区间对照表", "",
             f"共 {len(rows)} 处区间，对应 {len(comps)} 个比较，{bad} 处需要处理。printed 是源文件中的值，recomputed 是该比较用独立种子的自助法从全精度端点舍入一次的值。", "",
             "## 逐处对照", "",
             "| # | file | line | sentence fragment | printed | comparison | recomputed | changed | ID |",
             "|---|---|---|---|---|---|---|---|---|"]
    lines += [f"| {a} | {b} | {c} | {d} | {e} | {f} | {g} | {h} | {i} |" for a, b, c, d, e, f, g, h, i in rows]
    lines += ["", "## 按比较汇总", "", "| ID | comparison | cells | wins | point | full-precision interval | recomputed |", "|---|---|---|---|---|---|---|"]
    for c in comps:
        r = results[c["id"]]
        lines.append(f"| {c['id']} | {c['a']} \N{MINUS SIGN} {c['b']}, {c['metric']}, {c.get('filter', '')} | {r['cells']} | {r['wins']} | "
                     f"{r['point_printed']} | [{r['lo']:.3f}, {r['hi']:.3f}] | {r['recomputed']} |")
    if loose:
        lines += ["", "## 未能解析的方括号内容（人工确认）", ""]
        lines += [f"- {os.path.relpath(p, root)}:{i} {t}" for p, i, t in loose]
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps({"rows": rows, "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(rows)} intervals, {len(comps)} comparisons, {bad} to handle, map written to {args.out}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

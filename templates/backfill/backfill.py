#!/usr/bin/env python3
"""Backfill measured numbers into both language versions of a paper.

Every number quoted in the paper is a macro \\num{key}. This script reads a registry that says where each value
comes from, reads the result files, and writes

    numbers_en.tex and numbers_zh.tex   one \\setnum{key}{value} line per number that is available
    marked blocks in the section files  the rows of the main table between %%BEGIN-<TAG> and %%END-<TAG>
    BACKFILL.md                         value, status and source of every number, and what is still missing

A number whose result file or key is missing gets no \\setnum line, so the paper prints it as a red [key]
placeholder and BACKFILL.md lists it as waiting. Rerunning the experiments and then this script refills the paper.
Nobody edits a number by hand.

Registry (JSON, paths relative to the registry file):
{
  "numbers": [
    {"name": "datasets", "value": 3},
    {"name": "recall ours", "source": "results/summary.json", "key": "recall.ours", "fmt": "{:.3f}"},
    {"name": "label share pct", "source": "results/summary.json", "key": "label_share", "scale": 100, "fmt": "{:.0f}"},
    {"name": "gain over best pct", "expr": "100 * (v['recall ours'] / v['recall best baseline'] - 1)", "fmt": "{:.1f}"},
    {"name": "families", "value": 4, "text_en": "four", "text_zh": "四"}
  ],
  "tables": [
    {"tag": "MAINROWS", "source": "results/main_table.csv", "decimals": 3,
     "families": ["Rule-based", "Learning-based"], "name_macro": "\\\\textbf{\\\\sys}"}
  ],
  "targets": {
    "en": {"numbers": "numbers_en.tex", "sections": ["sections_en/05_experiments.tex"]},
    "zh": {"numbers": "numbers_zh.tex", "sections": ["sections_zh/05_experiments.tex"]}
  },
  "report": "BACKFILL.md"
}

"key" is a dotted path into a JSON file. A CSV source takes "row" (value of its first column) and "column".
"expr" is a Python expression over v, the dict of already resolved raw values. The main table CSV has the
columns method, family, <one column per dataset>, as for figure-style/tables/shade_and_rank.py.

Usage:
    python backfill.py --registry registry.json --paper-dir ../latex-bilingual [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import sys
from pathlib import Path


def import_shade_and_rank():
    """shade_and_rank.py sits next to this script in a paper repository, or in figure-style/tables of the skill."""
    here = Path(__file__).resolve().parent
    candidates = [here] + [p / "figure-style" / "tables" for p in here.parents]
    for c in candidates:
        if (c / "shade_and_rank.py").is_file():
            sys.path.insert(0, str(c))
            import shade_and_rank  # noqa: E402
            return shade_and_rank
    sys.exit("shade_and_rank.py not found. Copy figure-style/tables/shade_and_rank.py next to backfill.py.")


def dotted(obj, key: str):
    for part in key.split("."):
        if isinstance(obj, list):
            obj = obj[int(part)]
        else:
            obj = obj[part]
    return obj


def read_value(base: Path, item: dict):
    """Return (raw value or None, source description)."""
    if "value" in item:
        return item["value"], "literal in registry"
    if "expr" in item:
        return None, "expr: " + item["expr"]
    src = base / item["source"]
    desc = item["source"] + (" " + item["key"] if "key" in item else "")
    if not src.is_file():
        return None, desc + " (file missing)"
    try:
        if src.suffix == ".json":
            raw = dotted(json.loads(src.read_text(encoding="utf-8")), item["key"])
        elif src.suffix == ".csv":
            with src.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            first = list(rows[0].keys())[0]
            match = [r for r in rows if r[first] == str(item["row"])]
            raw = match[0][item["column"]]
            desc = "%s row %s column %s" % (item["source"], item["row"], item["column"])
        else:
            raise ValueError("unsupported source type " + src.suffix)
    except (KeyError, IndexError, ValueError) as e:
        return None, desc + " (key missing: %s)" % e
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return None, desc + " (empty value)"
    return raw, desc


def latex_number(text: str) -> str:
    """A leading minus becomes a math minus so that it does not print as a hyphen."""
    return "$-$" + text[1:] if text.startswith("-") else text


def format_value(item: dict, raw, lang: str) -> str:
    if "text_" + lang in item:
        return item["text_" + lang]
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        raw = raw * item.get("scale", 1)
        return latex_number(item.get("fmt", "{}").format(raw))
    return str(raw)


def resolve_numbers(base: Path, registry: dict):
    raw, rows = {}, []
    for item in registry.get("numbers", []):
        value, desc = read_value(base, item)
        if "expr" in item:
            try:
                value = eval(item["expr"], {"__builtins__": {}, "math": math, "min": min, "max": max,
                                            "abs": abs, "round": round}, {"v": raw})
            except KeyError as e:
                desc += " (waiting for %s)" % e
                value = None
            except (TypeError, ZeroDivisionError) as e:
                desc += " (%s)" % e
                value = None
        if value is not None and isinstance(value, str) and "fmt" in item:
            try:
                value = float(value)
            except ValueError:
                pass
        if value is not None:
            raw[item["name"]] = value
        rows.append((item, value, desc))
    return raw, rows


def write_numbers(path: Path, rows, lang: str, registry_name: str, dry: bool) -> str:
    lines = ["%% Generated by backfill.py from %s. Do not edit by hand (%s)." % (registry_name, lang)]
    for item, value, desc in sorted(rows, key=lambda r: r[0]["name"]):
        if value is None:
            lines.append("%% waiting: %s <- %s" % (item["name"], desc))
        else:
            lines.append("\\setnum{%s}{%s}" % (item["name"], format_value(item, value, lang)))
    text = "\n".join(lines) + "\n"
    if not dry:
        path.write_text(text, encoding="utf-8")
    return text


def patch_block(path: Path, tag: str, body: str, dry: bool) -> None:
    s = path.read_text(encoding="utf-8")
    begin, end = "%%BEGIN-" + tag, "%%END-" + tag
    if s.count(begin) != 1 or s.count(end) != 1:
        sys.exit("%s must contain %s and %s exactly once" % (path, begin, end))
    a = s.index(begin) + len(begin)
    b = s.index(end)
    s = s[:a] + "\n" + body.rstrip("\n") + "\n" + s[b:]
    if not dry:
        path.write_text(s, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--registry", required=True, type=Path)
    ap.add_argument("--paper-dir", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true", help="print the report, write nothing")
    a = ap.parse_args()
    registry = json.loads(a.registry.read_text(encoding="utf-8"))
    base = a.registry.resolve().parent
    paper = a.paper_dir.resolve()
    sar = import_shade_and_rank()

    raw, rows = resolve_numbers(base, registry)
    targets = registry["targets"]
    for lang, t in targets.items():
        write_numbers(paper / t["numbers"], rows, lang, a.registry.name, a.dry_run)

    table_notes = []
    for tab in registry.get("tables", []):
        src = base / tab["source"]
        if not src.is_file():
            body = "%% waiting: " + tab["source"]
            table_notes.append((tab["tag"], tab["source"], "waiting, file missing"))
        else:
            trows, cols = sar.read(str(src))
            body = sar.render_rows(trows, cols, tab.get("decimals", 3), list(tab.get("families", [])),
                                   tab.get("name_macro", ""))
            missing = sum(1 for r in trows for c in cols if r[c] in ("", None))
            table_notes.append((tab["tag"], tab["source"], "%d rows, %d empty cells" % (len(trows), missing)))
        for lang, t in targets.items():
            for sec in t.get("sections", []):
                p = paper / sec
                if "%%BEGIN-" + tab["tag"] in p.read_text(encoding="utf-8"):
                    patch_block(p, tab["tag"], body, a.dry_run)

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    waiting = [(i["name"], d) for i, v, d in rows if v is None]
    rep = ["# Backfill record", "",
           "Generated by `backfill.py` at %s from `%s`." % (now, a.registry.name), "",
           "## Numbers", "", "| Macro | Value (en) | Status | Source |", "|---|---|---|---|"]
    for item, value, desc in rows:
        shown = format_value(item, value, "en") if value is not None else ""
        rep.append("| `\\num{%s}` | %s | %s | %s |" % (item["name"], shown, "final" if value is not None else
                                                       "waiting", desc))
    rep += ["", "## Tables", ""] + ["- `%s` from `%s`: %s." % t for t in table_notes]
    rep += ["", "## Still waiting", ""] + (["- `%s` <- %s" % w for w in waiting] or ["Nothing."])
    report = "\n".join(rep) + "\n"
    if not a.dry_run:
        (paper / registry.get("report", "BACKFILL.md")).write_text(report, encoding="utf-8")
    print(report)
    print("%d numbers final, %d waiting%s." % (len(rows) - len(waiting), len(waiting),
                                               " (dry run, nothing written)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

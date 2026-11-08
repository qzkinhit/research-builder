#!/usr/bin/env python3
"""Check the at-a-glance table that opens the reply to each reviewer.

The first comment to each reviewer carries a three-column table (review comment,
result, location in the revision with its margin tag), written as rtable{lll} in
the first responseen block and mirrored in the first responsezh block.

usage: check_glance_table.py --config kit.json [--root DIR] [--optional] [--revision FILE ...] [--allow N,N]

Checks
  1. every number of the English and of the Chinese table occurs in the English
     reply bodies of the same reviewer outside that table
  2. the English and the Chinese table hold the same multiset of numbers
  3. every row has three cells and a third cell with a location and a margin tag
  4. every number written in a displayed formula of an English reply occurs in
     the revision (with --revision), except the structural values of --allow

With --optional a reviewer without a table is reported but not counted as a
failure. Exit status 1 if any check fails.
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

NUM = re.compile(r"(?<![\w.])[-\u2212]?\d[\d,]*(?:\.\d+)?")
TAG = re.compile(r"[A-Za-z0-9_]+-[A-Za-z0-9_-]+")
TABLE = re.compile(r"\\begin\{rtable\}\{lll\}(.*?)\\end\{rtable\}", re.S)


def strip_comments(s):
    return "\n".join(re.sub(r"((?:^|[^\\])(?:\\\\)*)%.*", r"\1", ln) for ln in s.split("\n"))


def nums(s):
    return [x.replace(",", "").lstrip("-\u2212") for x in NUM.findall(s)]


def sections(text):
    """{key: section text} of the general section and every reviewer section, in order."""
    begin = text.find("\\begin{document}")
    base = begin if begin >= 0 else 0
    marks = []
    for m in re.finditer(r"\\GeneralSection(?![A-Za-z])|\\ReviewerSection\s*\{([^}]*)\}|\\ReferenceSection(?![A-Za-z])|\\end\{document\}", text):
        if m.start() < base:
            continue
        tok = m.group(0)
        if tok.startswith("\\GeneralSection"):
            marks.append(("general", m.start()))
        elif tok.startswith("\\ReviewerSection"):
            marks.append((m.group(1).strip(), m.start()))
        else:
            marks.append((None, m.start()))
    out = collections.OrderedDict()
    for k, (key, pos) in enumerate(marks[:-1]):
        if key is not None:
            out[key] = text[pos:marks[k + 1][1]]
    return out


def split_cells(row):
    cells, depth, cur = [], 0, ""
    i = 0
    while i < len(row):
        c = row[i]
        if c == "\\":
            cur += row[i:i + 2]
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        if c == "&" and depth == 0:
            cells.append(cur)
            cur = ""
        else:
            cur += c
        i += 1
    cells.append(cur)
    return [c.strip() for c in cells]


def rows_of(table):
    """Data rows of the table body, header row dropped."""
    parts = re.split(r"\\\\(?:\s*\\midrule)?", table)
    rows = [re.sub(r"\\(toprule|midrule|bottomrule)", "", p).strip() for p in parts]
    return [r for r in rows if r][1:]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default="kit.json")
    ap.add_argument("--root", default=None)
    ap.add_argument("--optional", action="store_true")
    ap.add_argument("--revision", nargs="*", default=[])
    ap.add_argument("--allow", default="0,1,2", help="comma-separated structural values allowed in formulas")
    args = ap.parse_args(argv)
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    root = Path(args.root) if args.root else Path(args.config).resolve().parent
    text = strip_comments((root / cfg["main"]).read_text(encoding="utf-8"))
    bad = 0
    secs = sections(text)
    for key, body in secs.items():
        if key == "general":
            continue
        en = re.findall(r"\\begin\{responseen\}(.*?)\\end\{responseen\}", body, re.S)
        zh = re.findall(r"\\begin\{responsezh\}(.*?)\\end\{responsezh\}", body, re.S)
        t_en = TABLE.findall(en[0]) if en else []
        t_zh = TABLE.findall(zh[0]) if zh else []
        if len(t_en) != 1 or len(t_zh) != 1:
            print(f"{key}: expected one rtable{{lll}} in the first English and Chinese block, found {len(t_en)} and {len(t_zh)}")
            bad += 0 if args.optional else 1
            continue
        rest = en[0].replace(t_en[0], " ") + "\n".join(en[1:])
        pool = set(nums(rest))
        for lang, tab in (("EN", t_en[0]), ("ZH", t_zh[0])):
            missing = [x for x in nums(tab) if x not in pool]
            bad += len(missing)
            print(f"{key} {lang}: {len(nums(tab))} numbers, missing in the reply body: {missing}")
        c_en, c_zh = collections.Counter(nums(t_en[0])), collections.Counter(nums(t_zh[0]))
        if c_en != c_zh:
            bad += 1
            print(f"{key}: English-only {dict(c_en - c_zh)}, Chinese-only {dict(c_zh - c_en)}")
        for row in rows_of(t_en[0]):
            cells = split_cells(row)
            if len(cells) != 3:
                bad += 1
                print(f"{key}: row with {len(cells)} cells: {row[:60]}")
                continue
            if not re.search(r"\d", cells[2]) or not TAG.search(cells[2]):
                bad += 1
                print(f"{key}: third cell needs a location and a margin tag: {cells[2][:60]}")
        print(f"{key}: {len(rows_of(t_en[0]))} rows")
    if args.revision:
        allowed = {x.strip() for x in args.allow.split(",")}
        rev = "\n".join(Path(f).read_text(encoding="utf-8") for f in args.revision)
        pool = set(nums(rev))
        for key, body in secs.items():
            for block in re.findall(r"\\begin\{responseen\}(.*?)\\end\{responseen\}", body, re.S):
                for formula in re.findall(r"\\\[(.*?)\\\]|\$\\displaystyle(.*?)\$", block, re.S):
                    shown = formula[0] or formula[1]
                    missing = [x for x in nums(shown) if x not in pool and x not in allowed]
                    bad += len(missing)
                    print(f"{key}: formula numbers {nums(shown)}, not in the revision: {missing}")
    print(f"glance table check: {bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

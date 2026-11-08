#!/usr/bin/env python3
"""Check the exported Markdown files for constructs that OpenReview renders wrongly.

OpenReview runs Markdown before TeX, so Markdown can change a formula before it
is typeset. The checks need no third party package.

usage: python3 tools/check_markdown.py [--dir openreview] [--strict] [FILE ...]

Errors (exit status 1 with --strict)
  a table row whose number of cells differs from the header
  an unclosed $ or $$
  unbalanced braces inside a formula
  a LaTeX command outside a formula
  a backslash before ASCII punctuation inside a formula, for example \\{ \\, \\\\ ,
    because the Markdown pass removes the backslash
  an underscore or star inside a formula that can pair with another delimiter
    of the same paragraph and turn the text between them into emphasis
Notes (never fatal)
  characters that are often unintended outside a formula
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ASCII_PUNCT = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
REWRITE = {"{": "\\lbrace", "}": "\\rbrace", ",": "\\thinspace", ";": "\\thickspace", "!": "\\negthinspace",
           "|": "\\Vert", "\\": "one formula per line", "%": "the percent sign outside the formula"}


def math_spans(text):
    """Yield (start, end, body, display) for $...$ and $$...$$, and (start, None, None, None) for an open one."""
    i, n = 0, len(text)
    while i < n:
        if text[i] == "\\" and text[i + 1:i + 2] == "$":
            i += 2
            continue
        if text.startswith("$$", i):
            j = text.find("$$", i + 2)
            if j < 0:
                yield i, None, None, True
                return
            yield i, j + 2, text[i + 2:j], True
            i = j + 2
            continue
        if text[i] == "$":
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == "$":
                    break
                j += 1
            if j >= n:
                yield i, None, None, False
                return
            yield i, j + 1, text[i + 1:j], False
            i = j + 1
            continue
        i += 1


def balanced(s):
    depth, i = 0, 0
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth < 0:
                return False
        i += 1
    return depth == 0


def flanking(s, i, size=1):
    """(can_open, can_close) of the delimiter run s[i:i+size], by the CommonMark rules for underscores."""
    before = s[i - 1] if i > 0 else " "
    after = s[i + size] if i + size < len(s) else " "
    ws_b, ws_a = before.isspace(), after.isspace()
    pu_b, pu_a = before in ASCII_PUNCT, after in ASCII_PUNCT
    left = not ws_a and (not pu_a or ws_b or pu_b)
    right = not ws_b and (not pu_b or ws_a or pu_a)
    return left and (not right or pu_b), right and (not left or pu_a)


def table_cells(line):
    i = 0
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    n = 1
    while i < len(body):
        if body[i] == "\\":
            i += 2
            continue
        if body[i] == "|":
            n += 1
        i += 1
    return n


def paragraphs(text):
    return [p for p in re.split(r"\n[ \t]*\n", text) if p.strip()]


def check_text(name, text):
    """Return (errors, notes) for one exported file."""
    errors, notes = [], []
    block = []
    for no, line in enumerate(text.split("\n") + [""], 1):
        if line.startswith("|"):
            block.append((no, line))
            continue
        if block:
            head = table_cells(block[0][1])
            for k, ln in block:
                if table_cells(ln) != head:
                    errors.append(f"{name}:{k}: table row has {table_cells(ln)} cells, header has {head}")
            block = []
    outside, last = [], 0
    spans = []
    for sp in math_spans(text):
        if sp[1] is None:
            errors.append(f"{name}: unclosed {'$$' if sp[3] else '$'} at offset {sp[0]}: {text[sp[0]:sp[0] + 50]!r}")
            continue
        spans.append(sp)
        outside.append(text[last:sp[0]])
        last = sp[1]
    outside.append(text[last:])
    plain = re.sub(r"^\|[-:| ]+\|$", " ", " ".join(outside), flags=re.M)
    for s, e, body, _ in spans:
        src = text[s:e]
        if not balanced(body):
            errors.append(f"{name}: unbalanced braces in {src[:60]}")
        for m in re.finditer(r"\\([!-/:-@\[-`{-~])", body):
            ch = m.group(1)
            hint = REWRITE.get(ch)
            errors.append(f"{name}: Markdown removes the backslash of \\{ch} in {src[:60]}"
                          + (f", write {hint}" if hint else ""))
    cmds = sorted(set(re.findall(r"\\[A-Za-z]+", plain)))
    if cmds:
        errors.append(f"{name}: LaTeX command outside a formula: {' '.join(cmds)}")
    odd = sorted(set(re.findall(r"[{}~]|---", plain)))
    if odd:
        notes.append(f"{name}: characters outside a formula: {' '.join(odd)}")
    for para in paragraphs(text):
        opened = False
        for s, e, body, display in math_spans(para):
            if e is None:
                continue
            offset = s + (2 if display else 1)
            for m in re.finditer(r"(?<!\\)_", body):
                can_open, can_close = flanking(para, offset + m.start())
                if can_close and opened:
                    errors.append(f"{name}: underscores in {para[s:e][:60]} can pair into emphasis, "
                                  "avoid a subscript right after a closing brace")
                    opened = False
                    continue
                opened = opened or can_open
            if re.search(r"(?<!\\)\*", body):
                errors.append(f"{name}: a star inside a formula can start emphasis in {para[s:e][:60]}, write \\ast or \\cdot")
    return errors, notes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="*")
    ap.add_argument("--dir", default=None, help="directory with the exported files, default: outdir of kit.json")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)
    if args.files:
        paths = [Path(f) for f in args.files]
    else:
        cfg_path = ROOT / "kit.json"
        outdir = "openreview"
        if cfg_path.exists():
            outdir = json.loads(cfg_path.read_text(encoding="utf-8")).get("outdir", outdir)
        base = Path(args.dir) if args.dir else ROOT / outdir
        paths = sorted(base.glob("*.md"))
    total_err = 0
    for p in paths:
        errors, notes = check_text(p.name, p.read_text(encoding="utf-8"))
        for line in errors:
            print(f"PROBLEM {line}")
        for line in notes:
            print(f"NOTE    {line}")
        total_err += len(errors)
    print(f"markdown check: {len(paths)} files, {total_err} problem(s)")
    return 1 if args.strict and total_err else 0


if __name__ == "__main__":
    sys.exit(main())

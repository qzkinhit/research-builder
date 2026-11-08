#!/usr/bin/env python3
"""Check that every English review text in reviews_bilingual.tex is verbatim.

Each \\DefConcern{id}{label}{EN}{ZH} is read, the LaTeX escapes in EN are
undone, and the result is compared with the unit of the same id parsed from
source/reviews.md. Whitespace inside a paragraph is normalised on both sides,
paragraph breaks must match. Every unit of reviews.md must be defined exactly
once, and every translation must be filled in. Exit status 1 on any difference.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from reviews_source import parse  # noqa: E402

UNESC = [("\\textbackslash{}", "\\"), ("\\textasciitilde{}", "~"),
         ("\\textasciicircum{}", "^"), ("\\textquotedbl{}", '"'), ("\\#", "#"), ("\\%", "%"), ("\\&", "&"),
         ("\\_", "_"), ("\\$", "$"), ("\\{", "{"), ("\\}", "}")]
TODO = "（待翻译）"


def read_group(s, i):
    """s[i] must be '{'. Return (content, index after the closing brace)."""
    if s[i] != "{":
        raise ValueError(f"expected '{{' at offset {i}")
    depth, j = 0, i
    while j < len(s):
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    raise ValueError(f"unbalanced braces from offset {i}")


def skip_ws_comments(s, i):
    while i < len(s):
        if s[i].isspace():
            i += 1
        elif s[i] == "%":
            while i < len(s) and s[i] != "\n":
                i += 1
        else:
            break
    return i


def norm(t):
    paras = re.split(r"\n\s*\n", t.strip())
    return "\n\n".join(re.sub(r"\s+", " ", p).strip() for p in paras)


def unescape(t):
    for a, b in UNESC:
        t = t.replace(a, b)
    return t


def strip_comments(s):
    """Drop LaTeX comments (an unescaped % to the end of the line)."""
    lines = []
    for line in s.split("\n"):
        j = 0
        while j < len(line):
            if line[j] == "\\":
                j += 2
                continue
            if line[j] == "%":
                line = line[:j]
                break
            j += 1
        lines.append(line)
    return "\n".join(lines)


def defs(tex_path):
    s = strip_comments(Path(tex_path).read_text(encoding="utf-8"))
    out = {}
    for m in re.finditer(r"\\DefConcern\s*", s):
        i = m.end()
        args = []
        for _ in range(4):
            i = skip_ws_comments(s, i)
            a, i = read_group(s, i)
            args.append(a)
        if args[0] in out:
            raise ValueError(f"duplicate id {args[0]}")
        out[args[0]] = args
    return out


def paths():
    cfg = {}
    cfg_path = ROOT / "kit.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    return ROOT / cfg.get("reviews_source", "source/reviews.md"), ROOT / cfg.get("reviews_tex", "reviews_bilingual.tex")


def main():
    src, tex = paths()
    units, _ = parse(src)
    d = defs(tex)
    bad = 0
    for uid, _r, _s, en in units:
        if uid not in d:
            print(f"MISSING  {uid}")
            bad += 1
            continue
        got = norm(unescape(d[uid][2]))
        want = norm(en)
        if got != want:
            k = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))
            print(f"DIFF     {uid} at char {k}: tex={got[k:k+40]!r} source={want[k:k+40]!r}")
            bad += 1
        if not d[uid][3].strip() or d[uid][3].strip() == TODO:
            print(f"NO-ZH    {uid}")
            bad += 1
    known = {u[0] for u in units}
    for uid in d:
        if uid not in known:
            print(f"EXTRA    {uid} (not in {src.name})")
            bad += 1
    print(f"verbatim check: {len(units)} units, {bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Check that the English paper and its Chinese mirror have the same structure.

Follows \\input and \\include from the document body of both main files and compares
labels, references, citation keys, \\num keys, environment counts and heading counts.
Any difference is printed and the exit code is 1.

Usage:
    python check_mirror.py [main_en.tex] [main_zh.tex]
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ENVS = ("theorem", "lemma", "proposition", "corollary", "definition", "assumption", "example", "finding",
        "remark", "proof", "figure", "figure*", "table", "table*", "algorithm", "equation", "align")
HEADS = ("section", "subsection", "subsubsection", "paragraph")


def strip_comments(s: str) -> str:
    # an unescaped % starts a comment; %%BEGIN-... markers are comments too
    return "\n".join(re.sub(r"((?:^|[^\\])(?:\\\\)*)%.*", r"\1", ln) for ln in s.split("\n"))


def expand(path: Path, seen: set[Path]) -> str:
    path = path if path.suffix == ".tex" else path.with_suffix(".tex")
    if path in seen or not path.is_file():
        return ""
    seen.add(path)
    s = strip_comments(path.read_text(encoding="utf-8"))

    def sub(m):
        return expand(path.parent / m.group(1), seen)
    return re.sub(r"\\(?:input|include)\{([^}]+)\}", sub, s)


def body(main: Path) -> str:
    s = strip_comments(main.read_text(encoding="utf-8"))
    if "\\begin{document}" in s:
        s = s.split("\\begin{document}", 1)[1]
    seen: set[Path] = set()
    return re.sub(r"\\(?:input|include)\{([^}]+)\}", lambda m: expand(main.parent / m.group(1), seen), s)


def profile(text: str) -> dict:
    keys = lambda pat: Counter(k.strip() for grp in re.findall(pat, text) for k in grp.split(","))  # noqa: E731
    return {
        "labels": keys(r"\\label\{([^}]+)\}"),
        "refs": keys(r"\\(?:ref|eqref|autoref|cref|Cref|pageref)\{([^}]+)\}"),
        "cites": keys(r"\\cite[tp]?\*?(?:\[[^\]]*\])?\{([^}]+)\}"),
        "nums": keys(r"\\num\{([^}]+)\}"),
        "envs": Counter({e: len(re.findall(r"\\begin\{" + re.escape(e) + r"\}", text)) for e in ENVS}),
        "heads": Counter({h: len(re.findall(r"\\" + h + r"\*?\{", text)) for h in HEADS}),
    }


def main() -> int:
    here = Path(__file__).resolve().parent
    en = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "main_en.tex"
    zh = Path(sys.argv[2]) if len(sys.argv) > 2 else here / "main_zh.tex"
    a, b = profile(body(en)), profile(body(zh))
    bad = 0
    for k in a:
        if a[k] != b[k]:
            only_en = a[k] - b[k]
            only_zh = b[k] - a[k]
            print("[DIFF] %s" % k)
            if only_en:
                print("   more in %s: %s" % (en.name, dict(only_en)))
            if only_zh:
                print("   more in %s: %s" % (zh.name, dict(only_zh)))
            bad = 1
        else:
            print("[OK] %s: %d items" % (k, sum(a[k].values())))
    return bad


if __name__ == "__main__":
    raise SystemExit(main())

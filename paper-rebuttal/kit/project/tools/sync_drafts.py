#!/usr/bin/env python3
"""Keep drafts/<section>.tex equal to the sections of the main rebuttal file.

The main file is the single source. One draft file per section is written so
that a section can be read, reviewed or handed to a co-author on its own.

usage: python3 tools/sync_drafts.py            write the drafts
       python3 tools/sync_drafts.py --check    exit 1 if a draft differs from the main file
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CN = "零一两三四五六七八九十"


def sections(main_text):
    """[(key, body)] for the general section and every reviewer section of the document body."""
    begin = main_text.find("\\begin{document}")
    start = begin + len("\\begin{document}") if begin >= 0 else 0
    marks = []
    for m in re.finditer(r"^\\GeneralSection\b.*$|^\\ReviewerSection\s*\{([^}]*)\}.*$|^\\ReferenceSection\b.*$|^\\end\{document\}",
                         main_text[start:], re.M):
        tok = m.group(0)
        if tok.startswith("\\GeneralSection"):
            marks.append(("general", start + m.start(), start + m.end()))
        elif tok.startswith("\\ReviewerSection"):
            marks.append((m.group(1).strip(), start + m.start(), start + m.end()))
        else:
            marks.append((None, start + m.start(), start + m.end()))
    out = []
    for k, (key, _a, b) in enumerate(marks):
        if key is None:
            continue
        next_start = marks[k + 1][1] if k + 1 < len(marks) else len(main_text)
        body = main_text[b:next_start].strip("\n")
        body = re.sub(r"\n%% =+\s*$", "", body).rstrip()
        out.append((key, body + "\n"))
    return out


def header(key, body):
    n = len(re.findall(r"^\\CommentBreak\{", body, re.M)) + 1
    count = CN[n] if n < len(CN) else str(n)
    where = "\\GeneralSection" if key == "general" else f"\\ReviewerSection{{{key}}}"
    name = "公共回复" if key == "general" else f"审稿人 {key} 的回复"
    return f"%% drafts/{key}.tex  {name}（{count}条评论），放在主文件 {where} 之后。\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--main", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    cfg = {}
    cfg_path = ROOT / "kit.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    main_tex = Path(args.main) if args.main else ROOT / cfg.get("main", "rebuttal_main.tex")
    out = Path(args.out) if args.out else ROOT / cfg.get("drafts", "drafts")
    wanted = {f"{key}.tex": header(key, body) + body for key, body in sections(main_tex.read_text(encoding="utf-8"))}
    if args.check:
        bad = 0
        for name, text in wanted.items():
            p = out / name
            if not p.exists() or p.read_text(encoding="utf-8") != text:
                print(f"DIFF    drafts/{name} differs from the main file")
                bad += 1
        for p in sorted(out.glob("*.tex")) if out.exists() else []:
            if p.name not in wanted:
                print(f"STALE   drafts/{p.name} has no section in the main file")
                bad += 1
        print(f"drafts check: {len(wanted)} sections, {bad} problem(s)")
        return 1 if bad else 0
    out.mkdir(parents=True, exist_ok=True)
    for name, text in wanted.items():
        (out / name).write_text(text, encoding="utf-8")
    print(f"wrote {len(wanted)} draft files to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Write reviews_bilingual.tex from source/reviews.md.

Every review unit becomes \\DefConcern{id}{label}{English}{translation}. The
English text is escaped for LaTeX and stays verbatim. A translation that already
exists in reviews_bilingual.tex is kept, a new unit gets the placeholder that
tools/check_reviews.py reports as NO-ZH until it is translated.

usage: python3 tools/gen_reviews_tex.py [--force]
With no --force, the script stops if the output file would lose a translation of
a unit that is no longer in reviews.md.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from check_reviews import TODO, defs  # noqa: E402
from reviews_source import parse  # noqa: E402

ESC = [("\\", "\\textbackslash{}"), ("#", "\\#"), ("%", "\\%"), ("&", "\\&"),
       ("_", "\\_"), ("$", "\\$"), ("{", "\\{"), ("}", "\\}"), ("~", "\\textasciitilde{}"),
       ("^", "\\textasciicircum{}"), ('"', "\\textquotedbl{}")]


def esc(t):
    out = []
    for ch in t:
        for a, b in ESC:
            if ch == a:
                out.append(b)
                break
        else:
            out.append(ch)
    return "".join(out)


def label(uid):
    """Display label of a unit in the PDF."""
    if uid.endswith("-Sum"):
        return uid[:-4] + " 摘要"
    if "-S" in uid and uid.split("-S")[-1].isdigit():
        r, k = uid.rsplit("-S", 1)
        return f"{r} 优点 {k}"
    if "-end" in uid:
        return uid.split("-end")[0] + "（末段）"
    if uid.startswith("REF-"):
        return "参考 " + uid[4:]
    return uid


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--force", action="store_true", help="write even if a translation would be dropped")
    args = ap.parse_args(argv)
    cfg = {}
    cfg_path = ROOT / "kit.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    src = ROOT / cfg.get("reviews_source", "source/reviews.md")
    tex = ROOT / cfg.get("reviews_tex", "reviews_bilingual.tex")
    units, _meta = parse(src)
    old = defs(tex) if tex.exists() else {}
    known = {u[0] for u in units}
    dropped = [k for k, v in old.items() if k not in known and v[3].strip() and v[3].strip() != TODO]
    if dropped and not args.force:
        print(f"would drop the translations of {', '.join(dropped)}, rerun with --force to accept", file=sys.stderr)
        return 1
    out = ["%% reviews_bilingual.tex  审稿意见原文与中文译文。",
           "%% 由 tools/gen_reviews_tex.py 从 source/reviews.md 生成，之后只手改中文译文。",
           "%% 英文原文（第三个参数）必须与 source/reviews.md 逐字一致，make verify 会核对。",
           "%% 格式 \\DefConcern{编号}{显示标签}{英文原文}{中文译文}",
           ""]
    cur, new = None, 0
    for uid, r, _sec, en in units:
        if r != cur:
            out.append(f"%% ==================== {r} ====================")
            cur = r
        en_t = "\n\n".join(esc(p) for p in en.split("\n\n"))
        zh = old[uid][3].strip() if uid in old and old[uid][3].strip() else TODO
        new += zh == TODO
        out.append(f"\\DefConcern{{{uid}}}{{{label(uid)}}}%")
        out.append("{" + en_t + "}%")
        out.append("{" + zh + "}")
        out.append("")
    tex.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {tex.name}, {len(units)} units, {new} still to translate")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Invariance check for wording passes over the reply and the revision.

A wording pass may change sentences, and may not change what they state. Dump
the invariants before the pass, dump again after it, and compare.

usage
  check_invariants.py dump OUT.json [--config kit.json] [--root DIR]
  check_invariants.py compare BEFORE.json AFTER.json
  check_invariants.py text OUT.txt [--config kit.json] [--root DIR]    write the prose of every block for reading
  check_invariants.py lint [--config kit.json] [--root DIR]            list dashes, semicolons, colons and stock words

Files come from kit.json, relative to its directory or to --root, so that a
backup copy of the project can be read with the same code.
  main            the rebuttal file, every responseen and responsezh is a block
  markdown        Markdown files, every "## English" and "## 中文" section is a block
  revision_en, revision_zh   globs of revised source files, the text of every
                  \\rev{text}{items}, \\revred{text} and \\revcap{text}{items} is a
                  block and the items are an invariant of the block
  terms           method and dataset names, compared as warnings

Invariants per block (multisets): numbers written with digits (sign kept),
English number words and ordinals, Chinese numerals before a classifier and
Chinese ordinals, \\ref and \\cite keys, \\num keys, \\label keys, margin tags such as R1-W1,
item tags such as W1a or Q2, table, figure, section, appendix, equation, finding
mentions (English and Chinese forms), bare appendix ids such as C.9, and the
counts of the words that say which document is meant (submission or submitted,
revision or revised, 提交稿, 提交时, 修订稿). Skeleton: every scanned file with
each block replaced by a placeholder, so that nothing outside the blocks may
change. Tables inside the rebuttal blocks must stay verbatim.

Exit status of compare: 1 if any invariant differs.
"""
import argparse
import collections
import difflib
import glob
import hashlib
import json
import os
import re
import sys


# --------------------------------------------------------------- parsing helpers
def strip_comments(s):
    return "\n".join(re.sub(r"((?:^|[^\\])(?:\\\\)*)%.*", r"\1", ln) for ln in s.split("\n"))


def group(s, i):
    """s[i] == '{'. Return (content, index after the closing brace)."""
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
    raise ValueError("unbalanced braces at offset %d" % i)


def skip_ws(s, i):
    while i < len(s) and s[i] in " \t\n":
        i += 1
    return i


def revision_blocks(path, tag):
    """Return (comment-stripped text, [(key, text, items, start, end, kind)]) for one revised source file."""
    s = strip_comments(open(path, encoding="utf-8").read())
    out, spans, k = [], [], 0
    stem = os.path.basename(path)[:-4]
    for m in re.finditer(r"\\(revred|revcap|rev)(?![A-Za-z])", s):
        if any(a <= m.start() < b for a, b in spans):      # nested inside an earlier block, part of its text
            continue
        i = skip_ws(s, m.end())
        if i >= len(s) or s[i] != "{":
            continue
        text, j = group(s, i)
        items = ""
        if m.group(1) in ("rev", "revcap"):
            j2 = skip_ws(s, j)
            if j2 < len(s) and s[j2] == "{":
                items, j = group(s, j2)
        k += 1
        out.append(("%s/%s#%02d" % (tag, stem, k), text, items.strip(), i + 1, i + 1 + len(text), m.group(1)))
        spans.append((m.start(), j))
    return s, out


def rebuttal_blocks(path):
    """Return (comment-stripped text, blocks) for the responseen and responsezh environments of the rebuttal."""
    s = strip_comments(open(path, encoding="utf-8").read())
    begin = s.find("\\begin{document}")
    base = begin if begin >= 0 else 0
    marks = [(m.start(), "general") for m in re.finditer(r"\\GeneralSection(?![A-Za-z])", s) if m.start() > base]
    marks += [(m.start(), m.group(1)) for m in re.finditer(r"\\ReviewerSection\{(\w+)\}", s) if m.start() > base]
    marks += [(m.start(), "reference") for m in re.finditer(r"\\ReferenceSection(?![A-Za-z])", s) if m.start() > base]
    marks.sort()
    out, g, sec = [], 0, "pre"
    pat = re.compile(r"\\begin\{rbgroup\}(\*?)(?:\[([^\]]*)\])?\{([^}]*)\}(.*?)\\end\{rbgroup\}", re.S)
    for gm in pat.finditer(s):
        if gm.start() < base:
            continue
        g += 1
        for p, name in marks:
            if p < gm.start():
                sec = name
        items = gm.group(3).replace(" ", "")
        cnt = collections.Counter()
        for em in re.finditer(r"\\begin\{(responseen|responsezh)\}(.*?)\\end\{\1\}", gm.group(4), re.S):
            lang = "en" if em.group(1) == "responseen" else "zh"
            cnt[lang] += 1
            key = "rebuttal/%s/g%02d[%s]/%s%d" % (sec, g, items, lang, cnt[lang])
            a = gm.start(4) + em.start(2)
            out.append((key, em.group(2), "", a, a + len(em.group(2)), lang))
    return s, out


def markdown_blocks(path):
    """Blocks of a Markdown file under headings English, 中文 or 中文参考译文 at any level."""
    s = open(path, encoding="utf-8").read()
    out = []
    pat = re.compile(r"^(#{2,5}) (English|中文[^\n]*)\n(.*?)(?=^#{1,5} |\Z)", re.S | re.M)
    counts = collections.Counter()
    stem = os.path.basename(path)
    for m in pat.finditer(s):
        lang = "en" if m.group(2) == "English" else "zh"
        counts[lang] += 1
        out.append(("markdown/%s/%s%d" % (stem, lang, counts[lang]), m.group(3), "", m.start(3), m.end(3), lang))
    return s, out


# ------------------------------------------------------------------- invariants
NUM = re.compile(r"(?<![A-Za-z0-9_.\\])([-+\u2212]?)(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?![A-Za-z0-9_])")
EN_WORDS = re.compile(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
                      r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|hundred|thousand|"
                      r"million|dozens?|half|quarter|twice|double|single|first|second|third|fourth|fifth|sixth|"
                      r"seventh|eighth|ninth|tenth)\b", re.I)
EN_QUANT = re.compile(r"\b(once|both|all|every|each|none|no|only|alone|any|always|never)\b", re.I)
ZH_CLS = r"(?:个|张|条|次|种|项|类|组|格|列|行|位|处|轮|倍|段|块|步|层|篇|份|批|点|名|成|阶段|楼|节|章|页|档|路|套|遍|台|分之|方面|部分|对)"
ZH_NUM = re.compile(r"(第?)([一二三四五六七八九十两百千万零半]+)(?=" + ZH_CLS + r")|第([一二三四五六七八九十]+)")
ZH_WORDS = re.compile(r"(全部|所有|每|只|仅|都|均|唯一|单独|两者|二者|各)")
REF = re.compile(r"\\(?:ref|Cref|cref|autoref|eqref|pageref|nameref)\*?\{([^}]*)\}")
CITE = re.compile(r"\\cite[a-zA-Z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}")
NUMKEY = re.compile(r"\\num\{([^}]*)\}")
LABEL = re.compile(r"\\label\{([^}]*)\}")
TAG = re.compile(r"(?<![A-Za-z0-9_-])([A-Za-z0-9_]+-(?:W|Q|S|O|M|D)\d+[a-z]?(?:-end)?)(?![A-Za-z0-9_-])")
ITEM = re.compile(r"(?<![A-Za-z0-9-])((?:W|Q|S|O|M|D)\d+[a-z]?)(?![A-Za-z0-9])")
EN_MENTION = re.compile(
    r"\b(Tables?|Figures?|Fig\.|Sections?|Appendix|Appendices|Examples?|Findings?|Propositions?|Theorems?|"
    r"Lemmas?|Definitions?|Corollary|Corollaries|Algorithms?|Equations?|Eq\.|Assumptions?|Remarks?)"
    r"(?:~|\s)+(\\(?:ref|Cref|cref|autoref|eqref)\{[^}]*\}|[A-Z]?\d+(?:\.\d+)*(?:\([a-z](?:,\s?[a-z])*\))?|"
    r"[A-Z]\.\d+(?:\.\d+)*|[A-Z]\d?(?![A-Za-z0-9]))")
ZH_MENTION = re.compile(
    r"(附录表|附录图|附录|表|图|例|发现|命题|定理|引理|定义|推论|算法|假设|公式)\s*~?\s*"
    r"(\\(?:ref|Cref|cref|autoref|eqref)\{[^}]*\}|[A-Z]?\d+(?:\.\d+)*(?:\([a-z](?:,\s?[a-z])*\))?|"
    r"[A-Z]\.\d+(?:\.\d+)*|[A-Z]\d?(?![A-Za-z0-9]))")
ZH_ORD = re.compile(r"第\s*~?\s*(\\ref\{[^}]*\}|\d+(?:\.\d+)*)\s*~?\s*(节|章|条|楼|行|页|段)")
BARE_ID = re.compile(r"(?<![A-Za-z0-9.])([A-Z]\.\d+(?:\.\d+)?)(?![A-Za-z0-9])")
SING = {"Tables": "Table", "Figures": "Figure", "Fig.": "Figure", "Sections": "Section", "Appendices": "Appendix",
        "Examples": "Example", "Findings": "Finding", "Propositions": "Proposition", "Theorems": "Theorem",
        "Lemmas": "Lemma", "Definitions": "Definition", "Corollaries": "Corollary", "Algorithms": "Algorithm",
        "Equations": "Equation", "Eq.": "Equation", "Assumptions": "Assumption", "Remarks": "Remark"}
QUAL_EN = re.compile(r"\b(submission|submitted|revision|revised)\b", re.I)
QUAL_ZH = re.compile(r"(提交稿|提交时|提交的|修订稿)")


def split_keys(c, pat, s):
    for g in pat.findall(s):
        c.update(x.strip() for x in g.split(",") if x.strip())


def invariants(text, lang, terms):
    s = text
    d = {"numbers": collections.Counter(a + b for a, b in NUM.findall(s))}
    if lang == "en":
        d["numwords"] = collections.Counter(w.lower() for w in EN_WORDS.findall(s))
        d["quantifiers"] = collections.Counter(w.lower() for w in EN_QUANT.findall(s))
        d["mentions"] = collections.Counter("%s %s" % (SING.get(a, a), re.sub(r"\s", "", b)) for a, b in EN_MENTION.findall(s))
        d["quals"] = collections.Counter(w.lower() for w in QUAL_EN.findall(s))
    else:
        zn = collections.Counter()
        for a, b, c in ZH_NUM.findall(s):
            zn[(a + b) if b else ("第" + c)] += 1
        d["numwords"] = zn
        d["quantifiers"] = collections.Counter(ZH_WORDS.findall(s))
        mm = collections.Counter("%s %s" % (a, re.sub(r"\s", "", b)) for a, b in ZH_MENTION.findall(s))
        mm.update("第 %s %s" % (a, b) for a, b in ZH_ORD.findall(s))
        d["mentions"] = mm
        d["quals"] = collections.Counter(QUAL_ZH.findall(s))
    d["refs"] = collections.Counter()
    split_keys(d["refs"], REF, s)
    d["cites"] = collections.Counter()
    split_keys(d["cites"], CITE, s)
    d["numkeys"] = collections.Counter()
    split_keys(d["numkeys"], NUMKEY, s)
    d["labels"] = collections.Counter(LABEL.findall(s))
    d["tags"] = collections.Counter(TAG.findall(s))
    d["items"] = collections.Counter(ITEM.findall(TAG.sub("", s)))
    d["ids"] = collections.Counter(BARE_ID.findall(s))
    d["rtables"] = collections.Counter(hashlib.sha1(x.encode()).hexdigest()[:12]
                                       for x in re.findall(r"\\begin\{rtable\}(.*?)\\end\{rtable\}", s, re.S))
    t = collections.Counter()
    for name in terms:
        t[name] = len(re.findall(r"(?<![A-Za-z0-9+.-])" + re.escape(name) + r"(?![A-Za-z0-9])", s))
    d["terms"] = +t
    return {k: dict(v) for k, v in d.items()}


def load_config(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def expand(root, patterns):
    out = []
    for pattern in patterns or []:
        out += sorted(glob.glob(os.path.join(root, pattern)))
    return out


def collect(root, cfg):
    blocks, skel = {}, {}
    files = [(os.path.join(root, cfg["main"]), "rebuttal", rebuttal_blocks)]
    for p in expand(root, cfg.get("markdown")):
        files.append((p, "markdown", markdown_blocks))
    for tag, key in (("en", "revision_en"), ("zh", "revision_zh")):
        for p in expand(root, cfg.get(key)):
            files.append((p, tag, (lambda x, t=tag: revision_blocks(x, t))))
    terms = cfg.get("terms", [])
    for path, tag, fn in files:
        s, bl = fn(path)
        pieces, last = [], 0
        for key, text, items, a, b, kind in bl:
            lang = kind if kind in ("en", "zh") else tag
            inv = invariants(text, lang, terms)
            inv["macro_items"] = items
            inv["kind"] = kind
            inv["chars"] = len(text)
            blocks[key] = {"inv": inv, "text": text}
            pieces.append(s[last:a])
            pieces.append("\x00%s\x00" % key)
            last = b
        pieces.append(s[last:])
        sk = "".join(pieces)
        rel = os.path.relpath(path, root)
        skel[rel] = {"sha": hashlib.sha256(sk.encode()).hexdigest(), "text": sk}
    return blocks, skel


# ------------------------------------------------------------------------- lint
LINT = [
    ("dash", re.compile(r"[\u2014\u2013]|(?<![\d$\]])\s--\s|---")),
    ("semicolon", re.compile(r"[;\uff1b]")),
    ("colon", re.compile(r"(?<![a-z])(?<!\\url\{)(?<!https)(?<!http)[:\uff1a](?![^{]*\})")),
    ("stock_en", re.compile(r"\b(additionally|crucial(?:ly)?|delve|enhanc\w*|foster\w*|highlight\w*|interplay|intricate\w*|"
                            r"landscape|meticulous\w*|pivotal|showcas\w*|tapestry|testament|underscor\w*|valuable|vibrant|"
                            r"notably|furthermore|moreover|it is worth noting|importantly|essentially|seamless\w*|"
                            r"leverag\w*|holistic|comprehensive|in conclusion|overall|indeed|clearly|remarkabl\w*|"
                            r"significant(?:ly)?|substantial(?:ly)?|dramatic\w*|striking\w*|unlock\w*|harness\w*|"
                            r"navigat\w*|realm|journey|game-chang\w*|cutting-edge|state-of-the-art|novel|key)\b", re.I)),
    ("stock_zh", re.compile(r"(值得注意的是|需要指出的是|综上所述|总而言之|闭环|闸门|门控|显著|极大地|充分|有力地|"
                            r"无疑|毋庸置疑|至关重要|核心在于|本质上|赋能|助力|打造|深入|全面地|有效地|进一步地|事实上|"
                            r"可以看出|不难发现|换言之|也就是说|一方面|另一方面)")),
    ("contrast", re.compile(r"\b(not only|not just|not merely|rather than|as opposed to|instead of)\b|不是.{1,30}而是|不仅|而非", re.I)),
    ("anthro", re.compile(r"\b(knows?|cares?|believes?|thinks?|realizes?|understands?|learns?|wants?|tries|refuses?|"
                          r"notices?|decides?|sees|aware|honest\w*)\b|认为|意识到|察觉|懂得|学会|试图|拒绝|知道", re.I)),
]


def lint_text(s):
    s2 = re.sub(r"\$[^$]*\$", " ", s)                      # math
    s2 = re.sub(r"\\(?:url|href|texttt|ref|cref|Cref|eqref|label|cite[a-z]*|num)\{[^}]*\}", " ", s2)
    s2 = re.sub(r"\\begin\{rtable\}.*?\\end\{rtable\}", " ", s2, flags=re.S)
    s2 = re.sub(r"^\|.*\|$", " ", s2, flags=re.M)             # markdown tables
    out = collections.OrderedDict()
    for name, pat in LINT:
        hits = [m.group(0) for m in pat.finditer(s2)]
        if hits:
            out[name] = hits
    return out


def compare(a_path, b_path):
    A = json.load(open(a_path, encoding="utf-8"))
    B = json.load(open(b_path, encoding="utf-8"))
    bad = 0
    ka, kb = set(A["blocks"]), set(B["blocks"])
    if ka != kb:
        bad += 1
        print("BLOCK SET DIFFERS  only before:", sorted(ka - kb)[:20], " only after:", sorted(kb - ka)[:20])
    cats = ["numbers", "numwords", "mentions", "quals", "refs", "cites", "numkeys", "labels",
            "tags", "items", "ids", "rtables", "macro_items", "kind"]
    changed = warn = 0
    for k in sorted(ka & kb):
        a, b = A["blocks"][k], B["blocks"][k]
        if a.get("chars") != b.get("chars"):
            changed += 1
        for c in cats:
            if a.get(c) != b.get(c):
                bad += 1
                if isinstance(a.get(c), dict):
                    ca, cb = collections.Counter(a.get(c) or {}), collections.Counter(b.get(c) or {})
                    print("DIFF %-48s %-12s before-only %s  after-only %s" % (k, c, dict(ca - cb), dict(cb - ca)))
                else:
                    print("DIFF %-48s %-12s %r -> %r" % (k, c, a.get(c), b.get(c)))
        for c in ("terms", "quantifiers"):
            if a.get(c) != b.get(c):
                warn += 1
                ca, cb = collections.Counter(a.get(c) or {}), collections.Counter(b.get(c) or {})
                print("warn %-48s %-12s before-only %s  after-only %s" % (k, c, dict(ca - cb), dict(cb - ca)))
    for f in sorted(set(A["skeleton"]) | set(B["skeleton"])):
        if A["skeleton"].get(f) != B["skeleton"].get(f):
            bad += 1
            print("SKELETON DIFFERS", f)
            for ln in list(difflib.unified_diff(A["skeleton_text"].get(f, "").split("\n"),
                                                B["skeleton_text"].get(f, "").split("\n"), lineterm="", n=0))[:20]:
                print("    " + ln[:200])
    print("blocks: %d, text changed in %d, invariant differences: %d, term warnings: %d, skeleton files: %d"
          % (len(ka & kb), changed, bad, warn, len(B["skeleton"])))
    print("INVARIANCE OK" if bad == 0 else "INVARIANCE FAILED")
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("dump", "text"):
        p = sub.add_parser(name)
        p.add_argument("out")
        p.add_argument("--config", default="kit.json")
        p.add_argument("--root", default=None)
    p = sub.add_parser("lint")
    p.add_argument("--config", default="kit.json")
    p.add_argument("--root", default=None)
    p = sub.add_parser("compare")
    p.add_argument("before")
    p.add_argument("after")
    args = ap.parse_args(argv)
    if args.cmd == "compare":
        return compare(args.before, args.after)
    cfg = load_config(args.config)
    root = args.root or os.path.dirname(os.path.abspath(args.config))
    blocks, skel = collect(root, cfg)
    if args.cmd == "dump":
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump({"blocks": {k: v["inv"] for k, v in blocks.items()},
                       "skeleton": {k: v["sha"] for k, v in skel.items()},
                       "skeleton_text": {k: v["text"] for k, v in skel.items()}},
                      handle, ensure_ascii=False, indent=0, sort_keys=True)
        n = collections.Counter(k.split("/")[0] for k in blocks)
        print("blocks:", dict(n), "files:", len(skel))
    elif args.cmd == "text":
        with open(args.out, "w", encoding="utf-8") as f:
            for k, v in blocks.items():
                f.write("=== %s  [%s] items={%s} chars=%d\n%s\n\n" % (k, v["inv"]["kind"], v["inv"]["macro_items"],
                                                                     v["inv"]["chars"], v["text"].strip()))
        print("wrote", len(blocks), "blocks")
    elif args.cmd == "lint":
        tot = collections.Counter()
        for k, v in blocks.items():
            r = lint_text(v["text"])
            if r:
                print(k)
                for name, hits in r.items():
                    tot[name] += len(hits)
                    print("   %-10s %s" % (name, hits[:12]))
        print("TOTAL", dict(tot))
    return 0


if __name__ == "__main__":
    sys.exit(main())

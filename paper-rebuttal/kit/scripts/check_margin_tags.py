#!/usr/bin/env python3
"""Check the margin tags of a revised paper, in the PDF and in the source.

usage
  check_margin_tags.py --reviewers reviewers.tex --pdf revised.pdf [options]
  check_margin_tags.py --reviewers reviewers.tex --tex sections/*.tex [--reviews reviews.md] [--rebuttal main.tex]
  check_margin_tags.py --original original.tex --revised revised.tex

PDF checks (need PyMuPDF, pip install pymupdf)
  colour     every tag has the colour of its reviewer in reviewers.tex
  place      every tag lies right of the text block and inside the page
  overlap    no two tags overlap, and no tag overlaps body text
  near       every tag lies within --max-gap points of red text (a tag that
             drifted away from its change)
  census     body text uses only black, the change colour, the link colour and
             the colours passed with --allow

Source checks (with --tex)
  a tag with a reviewer that is not declared, a tag that is not a review unit
  (with --reviews), more than --max-stack tags on one note, a mark inside a
  heading that should be \\revred, red text outside the macros, marked text that
  ends in punctuation, and tags quoted in the reply that no note carries
  (with --rebuttal)

Unmarked edits (with --original and --revised)
  lists every change of the source outside the marks, for the author to confirm
  that each one is a small edit

Exit status 1 if any check fails. Tags far from red text count as failures only
with --strict.
"""
import argparse
import collections
import difflib
import re
import sys
from pathlib import Path

REVIEWER_RE = re.compile(r"^\s*\\RevReviewer\s*\{([^}]*)\}\s*\{([0-9A-Fa-f]{6})\}", re.M)


def read_reviewers(path):
    text = re.sub(r"(?m)(?<!\\)%.*$", "", Path(path).read_text(encoding="utf-8"))
    return {m.group(1).strip(): int(m.group(2), 16) for m in REVIEWER_RE.finditer(text)}


# ------------------------------------------------------------------- PDF checks
def spans_of(page, pymupdf):
    """[(text, colour, bbox, line_id)] of all text spans of the page, including text outside the page box."""
    out = []
    flags = getattr(pymupdf, "TEXTFLAGS_DICT", None)
    if flags is not None and hasattr(pymupdf, "TEXT_MEDIABOX_CLIP"):
        flags &= ~pymupdf.TEXT_MEDIABOX_CLIP
    data = page.get_text("dict", flags=flags) if flags is not None else page.get_text("dict")
    line_id = 0
    for block in data["blocks"]:
        for line in block.get("lines", []):
            line_id += 1
            for s in line["spans"]:
                if s["text"].strip():
                    out.append((s["text"], s["color"], tuple(s["bbox"]), line_id))
    return out


def find_tags(spans, prefix):
    """[(item, colours, bbox, indices of the spans)] for every prefix-item pair, also across spans of one line."""
    pat = re.compile(re.escape(prefix) + r"\s*(?<![A-Za-z0-9_-])([A-Za-z0-9_]+-(?:W|Q|S|O|M|D)\d+[a-z]?(?:-end)?)(?![A-Za-z0-9_-])")
    tags = []
    by_line = collections.defaultdict(list)
    for k, sp in enumerate(spans):
        by_line[sp[3]].append(k)
    for ids in by_line.values():
        joined, owners = "", []
        for k in ids:
            joined += spans[k][0]
            owners += [k] * len(spans[k][0])
        for m in pat.finditer(joined):
            members = sorted(set(owners[m.start():m.end()]))
            colours = sorted({spans[k][1] for k in members})
            x0 = min(spans[k][2][0] for k in members)
            y0 = min(spans[k][2][1] for k in members)
            x1 = max(spans[k][2][2] for k in members)
            y1 = max(spans[k][2][3] for k in members)
            tags.append((m.group(1), colours, (x0, y0, x1, y1), members))
    return tags


def intersects(a, b, eps=0.5):
    return min(a[2], b[2]) - max(a[0], b[0]) > eps and min(a[3], b[3]) - max(a[1], b[1]) > eps


def check_pdf(args, reviewers):
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            print("PDF checks need PyMuPDF, install it with pip install pymupdf", file=sys.stderr)
            return 1, 0
    doc = pymupdf.open(args.pdf)
    change = int(args.change_color, 16)
    link = int(args.link_color, 16) if args.link_color else None
    allowed = {0, change} | set(reviewers.values()) | {int(c, 16) for c in args.allow}
    if link is not None:
        allowed.add(link)
    problems, warnings, n_tags = [], [], 0
    per_reviewer = collections.Counter()
    census = collections.Counter()
    where_colour = collections.defaultdict(set)
    bodies = []
    for pno, page in enumerate(doc, 1):
        spans = spans_of(page, pymupdf)
        tags = find_tags(spans, args.tag_prefix)
        tag_spans = {k for t in tags for k in t[3]}
        body = [s for k, s in enumerate(spans) if k not in tag_spans]
        bodies.append((pno, page, body, tags))
        for text, colour, _bbox, _lid in body:
            n = len(text.strip())
            census[colour] += n
            where_colour[colour].add(pno)
    right_edges = sorted(s[2][2] for _p, _pg, body, _t in bodies for s in body if len(s[0].strip()) > 4)
    text_right = args.text_right
    if text_right is None and right_edges:
        text_right = right_edges[int(0.98 * (len(right_edges) - 1))]
    for pno, page, body, tags in bodies:
        red = [s for s in body if s[1] == change]
        for item, colours, box, _members in tags:
            n_tags += 1
            who = item.split("-", 1)[0]
            per_reviewer[who] += 1
            where = f"page {pno} {args.tag_prefix} {item}"
            want = reviewers.get(who)
            if want is None:
                problems.append(f"{where}: reviewer {who} is not declared in reviewers.tex")
            elif colours != [want]:
                got = ", ".join(f"{c:06X}" for c in colours)
                problems.append(f"{where}: colour {got}, expected {want:06X}")
            if text_right is not None and box[0] <= text_right:
                problems.append(f"{where}: left edge {box[0]:.1f} is not right of the text block ({text_right:.1f})")
            if box[2] > page.rect.width - args.page_gap:
                problems.append(f"{where}: right edge {box[2]:.1f} leaves less than {args.page_gap} pt to the page edge")
            if red:
                dist = min(0.0 if (r[2][1] <= box[3] and r[2][3] >= box[1]) else min(abs(r[2][1] - box[3]), abs(box[1] - r[2][3]))
                           for r in red)
            else:
                dist = float("inf")
            if dist > args.max_gap:
                warnings.append(f"{where}: nearest red text is {dist:.1f} pt away")
            for other in body:
                if intersects(box, other[2]):
                    problems.append(f"{where}: overlaps body text {other[0].strip()[:40]!r}")
                    break
        ordered = sorted(tags, key=lambda t: (t[2][1], t[2][0]))
        for a, b in zip(ordered, ordered[1:]):
            if intersects(a[2], b[2]):
                problems.append(f"page {pno}: tags {a[0]} and {b[0]} overlap")
    for colour, n in census.most_common():
        if colour not in allowed:
            pages = ", ".join(str(p) for p in sorted(where_colour[colour])[:8])
            problems.append(f"body text colour {colour:06X} on {n} characters (pages {pages}), not an allowed colour")
    print(f"tags: {n_tags} {dict(per_reviewer)}")
    print("text colours (characters): " + ", ".join(f"{c:06X} {n}" for c, n in census.most_common()))
    if text_right is not None:
        print(f"right edge of the text block: {text_right:.1f} pt")
    for line in problems:
        print(f"PROBLEM {line}")
    for line in warnings:
        print(f"WARN    {line}")
    return len(problems) + (len(warnings) if args.strict else 0), n_tags


# ---------------------------------------------------------------- source checks
def strip_comments(s):
    return "\n".join(re.sub(r"((?:^|[^\\])(?:\\\\)*)%.*", r"\1", ln) for ln in s.split("\n"))


def match_brace(s, i):
    """s[i] == '{'. Return the index of the matching closing brace."""
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
                return j
        j += 1
    raise ValueError(f"unbalanced braces at offset {i}")


def lineno(s, i):
    return s.count("\n", 0, i) + 1


def rev_calls(text):
    """[(macro, line, marked text, [tags], offset, end offset)] of the marks of one source text."""
    s = strip_comments(text)
    out = []
    i = 0
    pat = re.compile(r"\\(revcap|revred|rev|revnote|revfloatnote)(?![A-Za-z])\s*")
    while True:
        m = pat.search(s, i)
        if not m:
            break
        name, j = m.group(1), m.end()
        if j >= len(s) or s[j] != "{":
            i = j
            continue
        k = match_brace(s, j)
        first = s[j + 1:k]
        items, end = "", k + 1
        if name in ("rev", "revcap"):
            k2 = k + 1
            while k2 < len(s) and s[k2] in " \t\n":
                k2 += 1
            if k2 < len(s) and s[k2] == "{":
                k3 = match_brace(s, k2)
                items, end = s[k2 + 1:k3], k3 + 1
            text_part = first
        elif name in ("revnote", "revfloatnote"):
            items, text_part = first, ""
        else:
            text_part = first
        tags = [t.strip() for t in items.split(",") if t.strip()]
        out.append((name, lineno(s, m.start()), text_part, tags, m.start(), end))
        i = end
    return s, out


def check_source(args, reviewers):
    problems = []
    all_tags = collections.Counter()
    n_marks = 0
    known_units = None
    if args.reviews:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "project" / "tools"))
        sys.path.insert(0, str(Path(args.reviews).resolve().parent.parent / "tools"))
        from reviews_source import parse
        known_units = {u[0] for u in parse(args.reviews)[0]}
    for pattern in args.tex:
        path = Path(pattern)
        text, calls = rev_calls(path.read_text(encoding="utf-8"))
        for name, line, body, tags, start, _end in calls:
            n_marks += 1
            all_tags.update(tags)
            where = f"{path.name}:{line}"
            if len(tags) > args.max_stack:
                problems.append(f"{where}: {len(tags)} tags on one note, at most {args.max_stack}")
            for t in tags:
                if reviewers and t.split("-", 1)[0] not in reviewers:
                    problems.append(f"{where}: tag {t} has an undeclared reviewer")
                if known_units is not None and t not in known_units:
                    problems.append(f"{where}: tag {t} is not a unit of {Path(args.reviews).name}")
            if name in ("rev", "revcap") and not tags:
                problems.append(f"{where}: \\{name} has an empty tag list, use \\revred for a passage without a note")
            cleaned = " ".join(body.split())
            if re.search(r"[,;:，；：、]$", cleaned):
                problems.append(f"{where}: marked text ends in punctuation that belongs outside the mark")
            if re.fullmatch(r"\\pending\{[^}]*\}", cleaned):
                problems.append(f"{where}: the mark holds only a \\pending item")
            if re.fullmatch(r"[(（][^()（）]*[)）]", cleaned):
                problems.append(f"{where}: the mark holds only a parenthetical, mark the sentence it belongs to")
            before = text[max(0, start - 200):start]
            if name == "rev" and re.search(r"\\(?:sub)*(?:section|paragraph)\*?\{[^}]*$", before):
                problems.append(f"{where}: \\rev inside a heading, use \\revred")
        for m in re.finditer(r"\\(textcolor|color)\s*\{red\}", text):
            problems.append(f"{path.name}:{lineno(text, m.start())}: red text outside the marks")
    print(f"marks: {n_marks}, tags: {sum(all_tags.values())} ({len(all_tags)} distinct)")
    if args.rebuttal:
        reply = strip_comments(Path(args.rebuttal).read_text(encoding="utf-8"))
        quoted = set()
        for block in re.findall(r"\\begin\{responseen\}(.*?)\\end\{responseen\}", reply, re.S):
            quoted.update(re.findall(r"(?<![A-Za-z0-9_-])([A-Za-z0-9_]+-(?:W|Q|S|O|M|D)\d+[a-z]?(?:-end)?)(?![A-Za-z0-9_-])", block))
        for t in sorted(quoted - set(all_tags)):
            problems.append(f"the reply quotes {t} but no note in the revision carries it")
        unused = sorted(set(all_tags) - quoted)
        if unused:
            print(f"tags on notes that the reply does not quote: {', '.join(unused)}")
    for line in problems:
        print(f"PROBLEM {line}")
    return len(problems), n_marks


# --------------------------------------------------------------- unmarked edits
def strip_marks(s):
    text, calls = rev_calls(s)
    out, last = [], 0
    for _name, _line, _body, _tags, start, end in calls:
        if start < last:
            continue
        out.append(text[last:start])
        out.append(" <<REV>> ")
        last = end
    out.append(text[last:])
    return "".join(out)


def tokens(s):
    return re.findall(r"<<REV>>|\\[A-Za-z]+|[A-Za-z0-9.+-]+|[^\sA-Za-z0-9]", s)


def list_unmarked(original, revised):
    old, new = tokens(strip_comments(Path(original).read_text(encoding="utf-8"))), tokens(strip_marks(Path(revised).read_text(encoding="utf-8")))
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    n = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        before, after = " ".join(old[i1:i2]), " ".join(new[j1:j2])
        if tag in ("insert", "replace") and re.fullmatch(r"(?:<<REV>>\s*)+[.,)(]*", after.strip()):
            continue
        n += 1
        print(f"{tag.upper()}  old: {before[:200]}\n        new: {after[:200]}")
    print(f"unmarked edits: {n} (review each one, a substantive edit needs a mark)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--reviewers", help="reviewers.tex with \\RevReviewer{id}{colour}")
    ap.add_argument("--pdf")
    ap.add_argument("--tex", nargs="*", default=[])
    ap.add_argument("--reviews", help="source/reviews.md, enables the check that tags are review units")
    ap.add_argument("--rebuttal", help="main rebuttal file, enables the check that quoted tags exist")
    ap.add_argument("--original")
    ap.add_argument("--revised")
    ap.add_argument("--tag-prefix", default="")
    ap.add_argument("--change-color", default="FF0000")
    ap.add_argument("--link-color", default=None)
    ap.add_argument("--allow", nargs="*", default=[], help="further allowed body text colours, HTML values")
    ap.add_argument("--text-right", type=float, default=None, help="right edge of the text block in pt, default: estimated")
    ap.add_argument("--page-gap", type=float, default=9.0, help="minimum distance between a tag and the page edge")
    ap.add_argument("--max-gap", type=float, default=14.0, help="largest vertical distance between a tag and red text")
    ap.add_argument("--max-stack", type=int, default=2, help="largest number of tags on one note")
    ap.add_argument("--strict", action="store_true", help="tags far from red text count as failures")
    args = ap.parse_args(argv)
    reviewers = read_reviewers(args.reviewers) if args.reviewers else {}
    failures = 0
    if args.pdf:
        if not reviewers:
            ap.error("--pdf needs --reviewers")
        bad, _n = check_pdf(args, reviewers)
        failures += bad
    if args.tex:
        bad, _n = check_source(args, reviewers)
        failures += bad
    if args.original and args.revised:
        list_unmarked(args.original, args.revised)
    print(f"margin tag check: {failures} problem(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

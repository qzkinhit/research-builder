#!/usr/bin/env python3
"""Export the English response blocks of the rebuttal to OpenReview Markdown.

Source of truth: the bodies of the responseen environments in the main tex
file (and in any file it pulls in with \\input). A body belongs to the section
opened by the most recent \\GeneralSection or \\ReviewerSection{<id>} marker.
Only the part after \\begin{document} is read, so \\input files of the
preamble are ignored. Bodies of one section are joined, in order, with one
blank line.

Several OpenReview comments for one section: a \\CommentBreak{<label>} line
between two response groups starts a new comment. A section with k-1 breaks is
exported to k files, <id>_part1.md ... <id>_partk.md, each counted and checked
against the limit on its own. A section without \\CommentBreak gives <id>.md.
Every part must contain at least one responseen block.

Project settings come from kit.json next to the tools directory (see DEFAULTS).

Outputs
  openreview/general.md, openreview/<id>.md   text to paste into OpenReview
  openreview/<id>_part<k>.md                  one file per comment if split
  openreview/index.json                       posting order, title of every
                                              comment, counts, open problems
  counts.tex                                  \\RBsetcount (one per file) and
                                              \\RBsetparts{<id>}{k} if split
Character count = Python len() of the pasted text (file content without the
final newline). A newline counts as 1.

Titles: "<base>" for a single comment and "<base> (k of n)" for a split section.
Labels of the form (k of n) in \\CommentBreak{...} or in the optional argument
of \\begin{rbgroup} are compared with the exported comments.

Supported LaTeX inside responseen (everything else is an error, never dropped):
  paragraphs (blank line)          -> blank line
  \\textbf{x}                       -> **x**
  \\textit{x}, \\emph{x}             -> *x*
  \\texttt{x}                       -> `x`
  $...$                            -> kept verbatim (OpenReview renders it)
  \\[ ... \\]                        -> $$...$$ on its own line, kept verbatim
  \\% \\& \\_ \\# \\$ \\{ \\}            -> the character
  ~                                -> space
  -- (range)                       -> en dash, --- is rejected
  ``x''                            -> "x"
  \\ldots                           -> ...
  \\url{u}, \\href{u}{t}             -> u, [t](u)
  \\rhead{x}                        -> #### x   (heading line)
  itemize / enumerate with \\item   -> "- " / "1. " lists, nesting allowed
  rtable{lcr...} rows `a & b \\\\`    -> pipe table, first row is the header,
                                      \\toprule \\midrule \\bottomrule \\hline ignored
  \\pending{note}                   -> **[PENDING: note]**, listed on the console
  \\respTBD                         -> nothing, the block is reported as unfilled
  % comments                       -> removed
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULTS = {
    "main": "rebuttal_main.tex",
    "reviewers": "reviewers.tex",
    "comment_limit": 5000,
    "general_title": "General response",
    "reviewer_title": "Response to Reviewer {id}",
    "outdir": "openreview",
    "counts": "counts.tex",
}
PENDING_FILLED = 6   # assumed length of a number written in place of one \pending

MARK_RE = re.compile(
    r"\\GeneralSection(?![A-Za-z])"
    r"|\\ReviewerSection\s*\{([^}]*)\}"
    r"|\\begin\{responseen\}"
    r"|\\input\s*\{([^}]*)\}"
    r"|\\CommentBreak\s*\{([^}]*)\}"
    r"|\\begin\{rbgroup\}\*?\s*\[([^\]]*)\]"
)
RULES_RE = re.compile(r"\\(toprule|midrule|bottomrule|hline)(?![A-Za-z])")
KN_RE = re.compile(r"^\s*\(\s*(\d+)\s+of\s+(\d+)\s*\)\s*$")
REVIEWER_RE = re.compile(r"^\s*\\RevReviewer\s*\{([^}]*)\}\s*\{[0-9A-Fa-f]{6}\}", re.M)


class ExportError(Exception):
    pass


def load_config(path=None):
    """Settings from kit.json, with DEFAULTS for every key that is absent."""
    cfg = dict(DEFAULTS)
    p = Path(path) if path else ROOT / "kit.json"
    if p.exists():
        cfg.update(json.loads(p.read_text(encoding="utf-8")))
    return cfg


# ---------------------------------------------------------------- source files
def strip_comments(raw):
    """Remove comments. A line that is only a comment is removed entirely, as
    LaTeX does not see a paragraph break there. Returns (text, linemap) where
    linemap[k] is the 1-based source line of output line k."""
    out, lm = [], []
    join = False
    for no, line in enumerate(raw.split("\n"), 1):
        if join and line.strip():
            # a comment also removes the end of its line, so LaTeX joins the next line
            line = line.lstrip()
        else:
            join = False
        j, cut = 0, None
        while j < len(line):
            if line[j] == "\\":
                j += 2
                continue
            if line[j] == "%":
                cut = j
                break
            j += 1
        if cut is not None:
            if not line[:cut].strip() and not join:
                continue
            line = line[:cut]
        if join:
            out[-1] += line
        else:
            out.append(line)
            lm.append(no)
        join = cut is not None
    return "\n".join(out), lm


class Where:
    """Maps an offset inside a response body back to file:line."""

    def __init__(self, path, text, linemap, base):
        self.path, self.text, self.lm, self.base = path, text, linemap, base

    def __call__(self, off):
        k = self.text.count("\n", 0, self.base + off)
        line = self.lm[k] if k < len(self.lm) else self.lm[-1]
        try:
            name = self.path.relative_to(ROOT)
        except ValueError:
            name = self.path
        return f"{name}:{line}"


def scan(path, events, seen=None):
    seen = seen or set()
    path = Path(path).resolve()
    if path in seen:
        raise ExportError(f"{path}: \\input loop")
    seen = seen | {path}
    text, lm = strip_comments(path.read_text(encoding="utf-8"))
    # in the main file only the document body counts, so that the preamble
    # (which defines \GeneralSection and friends) is never read as content
    begin = text.find("\\begin{document}")
    pos = begin + len("\\begin{document}") if begin >= 0 else 0
    while True:
        m = MARK_RE.search(text, pos)
        if not m:
            break
        where = Where(path, text, lm, m.start())
        tok = m.group(0)
        if tok.startswith("\\GeneralSection"):
            events.append(("section", "general", where(0)))
            pos = m.end()
        elif tok.startswith("\\ReviewerSection"):
            events.append(("section", m.group(1).strip(), where(0)))
            pos = m.end()
        elif tok.startswith("\\CommentBreak"):
            events.append(("break", m.group(3).strip(), where(0)))
            pos = m.end()
        elif tok.startswith("\\input"):
            name = m.group(2).strip()
            cand = path.parent / name
            if cand.suffix != ".tex":
                cand = cand.with_name(cand.name + ".tex")
            if cand.exists():
                scan(cand, events, seen)
            pos = m.end()
        elif tok.startswith("\\begin{rbgroup}"):
            events.append(("grouplabel", m.group(4).strip(), where(0)))
            pos = m.end()
        else:
            end = text.find("\\end{responseen}", m.end())
            if end < 0:
                raise ExportError(f"{where(0)}: responseen is not closed")
            body = text[m.end():end]
            nested = body.find("\\begin{responseen}")
            if nested >= 0:
                raise ExportError(f"{Where(path, text, lm, m.end())(nested)}: nested responseen")
            events.append(("response", body, Where(path, text, lm, m.end())))
            pos = end + len("\\end{responseen}")
    return events


# ------------------------------------------------------------------- converter
class Converter:
    def __init__(self, src, where=None):
        self.s = src
        self.where = where or (lambda off: f"offset {off}")
        self.pending = []   # (location, note)
        self.tbd = False

    def err(self, off, msg):
        raise ExportError(f"{self.where(off)}: {msg}")

    # helpers
    def group(self, i):
        """self.s[i] == '{'. Return (a, b, next) with content self.s[a:b]."""
        s = self.s
        if i >= len(s) or s[i] != "{":
            self.err(i, "expected '{'")
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
                    return i + 1, j, j + 1
            j += 1
        self.err(i, "unbalanced '{'")

    def arg(self, i):
        while i < len(self.s) and self.s[i] in " \t":
            i += 1
        return self.group(i)

    def cmdname(self, i):
        """self.s[i] == '\\'. Return (name, next) for a control word."""
        j = i + 1
        while j < len(self.s) and self.s[j].isalpha():
            j += 1
        return self.s[i + 1:j], j

    def math_end(self, i):
        """self.s[i] == '$'. Return index of the closing '$'."""
        s = self.s
        if s.startswith("$$", i):
            self.err(i, "$$...$$ is not supported in the source, write \\[ ... \\] for displayed math")
        j = i + 1
        while j < len(s):
            if s[j] == "\\":
                j += 2
                continue
            if s[j] == "$":
                return j
            j += 1
        self.err(i, "unclosed $")

    def display_end(self, i):
        """self.s starts a \\[ at i. Return the index of the matching \\]."""
        j = i + 2
        while j < len(self.s):
            if self.s.startswith("\\]", j):
                return j
            j += 2 if self.s[j] == "\\" else 1
        self.err(i, "\\[ is not closed")

    def env_end(self, name, i):
        """Index of the \\end{name} matching a \\begin{name} that ends before i."""
        depth = 1
        b, e = f"\\begin{{{name}}}", f"\\end{{{name}}}"
        j = i
        while True:
            nb, ne = self.s.find(b, j), self.s.find(e, j)
            if ne < 0:
                self.err(i, f"\\begin{{{name}}} is not closed")
            if 0 <= nb < ne:
                depth += 1
                j = nb + len(b)
            else:
                depth -= 1
                if depth == 0:
                    return ne
                j = ne + len(e)

    # inline
    def inline(self, a, b, table=False):
        s, out, i = self.s, [], a
        while i < b:
            c = s[i]
            if c == "\\":
                if i + 1 < b and s[i + 1].isalpha():
                    name, j = self.cmdname(i)
                    if name in ("textbf", "textit", "emph", "texttt"):
                        x, y, j = self.arg(j)
                        inner = self.inline(x, y, table).strip()
                        mark = {"textbf": "**", "textit": "*", "emph": "*", "texttt": "`"}[name]
                        out.append(mark + inner + mark)
                    elif name == "url":
                        x, y, j = self.arg(j)
                        out.append(s[x:y].strip())
                    elif name == "href":
                        x, y, j = self.arg(j)
                        u = s[x:y].strip()
                        x, y, j = self.arg(j)
                        out.append("[" + self.inline(x, y, table).strip() + "](" + u + ")")
                    elif name == "pending":
                        x, y, j = self.arg(j)
                        note = re.sub(r"\s+", " ", self.inline(x, y, table)).strip()
                        self.pending.append((self.where(i), note))
                        out.append(f"**[PENDING: {note}]**")
                    elif name in ("respTBD", "ldots"):
                        if name == "respTBD":
                            self.tbd = True
                        else:
                            out.append("...")
                        if s.startswith("{}", j):
                            j += 2
                        elif name == "respTBD":
                            while j < b and s[j] in " \t":
                                j += 1
                    elif name == "CommentBreak":
                        self.err(i, "\\CommentBreak is only allowed between response groups, not inside responseen")
                    elif name in ("begin", "end", "item", "rhead"):
                        self.err(i, f"\\{name} is not allowed here (inside a paragraph, table cell or argument)")
                    else:
                        self.err(i, f"unsupported command \\{name}")
                    i = j
                    continue
                nxt = s[i + 1] if i + 1 < b else ""
                if nxt in ("[", "]") and nxt:
                    self.err(i, "displayed math must stand between paragraphs, not inside a table cell or argument")
                if nxt in ("%", "&", "_", "#", "$", "{", "}"):
                    # a literal $ is written as \$ so that OpenReview does not start math
                    out.append("\\$" if nxt == "$" else nxt)
                    i += 2
                    continue
                if nxt == " ":
                    out.append(" ")
                    i += 2
                    continue
                if nxt == "\\":
                    self.err(i, "line break \\\\ is only allowed between rtable rows")
                self.err(i, f"unsupported control symbol \\{nxt}")
            if c == "$":
                j = self.math_end(i)
                if table and "|" in s[i:j + 1]:
                    self.err(i, "a | inside math splits a Markdown table cell, write \\mid or \\vert")
                out.append(s[i:j + 1])
                i = j + 1
                continue
            if c == "{":
                x, y, j = self.group(i)
                out.append(self.inline(x, y, table))
                i = j
                continue
            if c == "}":
                self.err(i, "unbalanced '}'")
            if c == "~":
                out.append(" ")
                i += 1
                continue
            if s.startswith("---", i):
                self.err(i, "--- (em dash) is not allowed")
            if s.startswith("--", i):
                out.append("–")
                i += 2
                continue
            if s.startswith("``", i) or s.startswith("''", i):
                out.append('"')
                i += 2
                continue
            if c in "&#^_":
                self.err(i, f"bare '{c}' outside a table or math, escape it as \\{c}" if c != "^"
                         else "bare '^' outside math")
            if c == "*":
                out.append("\\*")
                i += 1
                continue
            if c == "|" and table:
                out.append("\\|")
                i += 1
                continue
            out.append(c)
            i += 1
        return re.sub(r"\s+", " ", "".join(out))

    # blocks
    def blocks(self, a, b):
        s, out = self.s, []
        para, i = a, a

        def flush(end):
            t = self.inline(para, end).strip()
            if t:
                out.append(t)

        while i < b:
            c = s[i]
            if c == "\n":
                m = re.compile(r"\n[ \t]*\n\s*").match(s, i)
                if m and m.start() < b:
                    flush(i)
                    i = min(m.end(), b)
                    para = i
                    continue
                i += 1
                continue
            if c == "$":
                i = self.math_end(i) + 1
                continue
            if c == "\\":
                if s.startswith("\\[", i):
                    flush(i)
                    end = self.display_end(i)
                    body = re.sub(r"\s+", " ", s[i + 2:end]).strip()
                    out.append("$$" + body + "$$")
                    i = para = end + 2
                    continue
                if s.startswith("\\begin{", i):
                    x, y, j = self.group(i + 6)
                    name = s[x:y]
                    if name not in ("itemize", "enumerate", "rtable"):
                        self.err(i, f"unsupported environment {name}")
                    flush(i)
                    end = self.env_end(name, j)
                    if name == "rtable":
                        out.append(self.table(j, end))
                    else:
                        out.append(self.listing(name, j, end))
                    i = end + len(f"\\end{{{name}}}")
                    para = i
                    continue
                if s.startswith("\\end{", i):
                    self.err(i, "\\end without matching \\begin")
                if s.startswith("\\rhead", i) and not s[i + 6:i + 7].isalpha():
                    flush(i)
                    x, y, j = self.arg(i + 6)
                    out.append("#### " + self.inline(x, y).strip())
                    i = para = j
                    continue
                if s.startswith("\\item", i) and not s[i + 5:i + 6].isalpha():
                    self.err(i, "\\item outside itemize/enumerate")
                i += 2
                continue
            i += 1
        flush(b)
        return out

    def split_items(self, a, b):
        s, starts, i, depth = self.s, [], a, 0
        while i < b:
            if s[i] == "\\":
                if s.startswith("\\begin{", i):
                    depth += 1
                elif s.startswith("\\end{", i):
                    depth -= 1
                elif depth == 0 and s.startswith("\\item", i) and not s[i + 5:i + 6].isalpha():
                    starts.append(i)
                i += 2
                continue
            if s[i] == "$":
                i = self.math_end(i) + 1
                continue
            i += 1
        if not starts:
            self.err(a, "list without \\item")
        if s[a:starts[0]].strip():
            self.err(a, "text before the first \\item")
        bounds = starts + [b]
        items = []
        for k, st in enumerate(starts):
            j = st + 5
            if s.startswith("[", j):
                self.err(st, "\\item[...] labels are not supported")
            items.append((j, bounds[k + 1]))
        return items

    def listing(self, name, a, b):
        lines = []
        for n, (x, y) in enumerate(self.split_items(a, b), 1):
            marker = "- " if name == "itemize" else f"{n}. "
            parts = self.blocks(x, y)
            body = parts[0] if parts else ""
            for prev, nxt in zip(parts, parts[1:]):
                # a nested list right after text stays a tight list
                body += ("\n" if re.match(r"(- |\d+\. )", nxt) else "\n\n") + nxt
            if not body:
                self.err(x, "empty \\item")
            pad = " " * len(marker)
            sub = body.split("\n")
            lines.append(marker + sub[0])
            lines.extend((pad + t) if t else "" for t in sub[1:])
        return "\n".join(lines)

    def table(self, a, b):
        s = self.s
        x, y, j = self.arg(a)
        spec = re.sub(r"\s", "", s[x:y])
        # blank out booktabs rules in place (same length, so offsets stay valid)
        s = self.s = s[:j] + RULES_RE.sub(lambda m: " " * len(m.group(0)), s[j:b]) + s[b:]
        if not re.fullmatch(r"[lcr]+", spec):
            self.err(a, f"rtable column spec must use only l, c, r (got {spec!r})")
        rows, cur, i, depth = [], [], j, 0
        cell = j
        while i < b:
            c = s[i]
            if c == "\\":
                if s.startswith("\\\\", i) and depth == 0:
                    cur.append((cell, i))
                    rows.append(cur)
                    cur = []
                    i += 2
                    cell = i
                    continue
                i += 2
                continue
            if c == "$":
                i = self.math_end(i) + 1
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            elif c == "&" and depth == 0:
                cur.append((cell, i))
                cell = i + 1
            i += 1
        cur.append((cell, b))
        rows.append(cur)
        md_rows = []
        for r in rows:
            texts = [self.inline(p, q, table=True).strip() for (p, q) in r]
            if len(texts) == 1 and not texts[0]:
                continue
            if len(texts) != len(spec):
                self.err(r[0][0], f"rtable row has {len(texts)} cells, column spec has {len(spec)}")
            md_rows.append(texts)
        if len(md_rows) < 2:
            self.err(a, "rtable needs a header row and at least one data row")
        delim = {"l": "---", "c": ":---:", "r": "---:"}
        lines = ["|" + "|".join(md_rows[0]) + "|",
                 "|" + "|".join(delim[ch] for ch in spec) + "|"]
        lines += ["|" + "|".join(r) + "|" for r in md_rows[1:]]
        return "\n".join(lines)


def convert_block(body, where=None):
    """Convert one responseen body. Returns (markdown, pending, tbd)."""
    cv = Converter(body, where)
    md = "\n\n".join(cv.blocks(0, len(body)))
    return md, cv.pending, cv.tbd


# ------------------------------------------------------------------------ main
def new_part(label=None, where=None):
    return {"parts": [], "pending": [], "tbd": 0, "blocks": 0, "label": label, "where": where,
            "kn": []}


def part_name(key, k, n):
    """Output name of comment k (1-based) of a section that has n comments."""
    return key if n == 1 else f"{key}_part{k}"


def comment_title(key, k, n, cfg):
    """Title of comment k of a section with n comments."""
    base = cfg["general_title"] if key == "general" else cfg["reviewer_title"].format(id=key)
    return base if n == 1 else f"{base} ({k} of {n})"


def read_reviewers(path):
    """Reviewer ids declared in reviewers.tex, in order. Empty if the file is absent."""
    p = Path(path)
    if not p.exists():
        return []
    text, _ = strip_comments(p.read_text(encoding="utf-8"))
    return [m.group(1).strip() for m in REVIEWER_RE.finditer(text)]


def label_problems(sections):
    """Compare every (k of n) label with the exported comments of its section."""
    bad = []
    for key, parts in sections.items():
        n = len(parts)
        seen = set()
        for k, sec in enumerate(parts, 1):
            for label_k, label_n, loc in sec["kn"]:
                if label_k != k or label_n != n:
                    bad.append(f"{loc}: label ({label_k} of {label_n}) sits on comment {k} of {n} of section {key}")
                seen.add(k)
        if n > 1:
            for k in range(1, n + 1):
                if k not in seen:
                    bad.append(f"section {key}: comment {k} of {n} has no ({k} of {n}) label")
    return bad


def export(main=None, outdir=None, counts_path=None, cfg=None):
    cfg = cfg or load_config()
    main = Path(main) if main else ROOT / cfg["main"]
    outdir = Path(outdir) if outdir else ROOT / cfg["outdir"]
    counts_path = Path(counts_path) if counts_path else ROOT / cfg["counts"]
    limit = int(cfg["comment_limit"])
    events = scan(main, [])
    sections = {}
    cur = None
    for ev in events:
        if ev[0] == "section":
            cur = ev[1]
            sections.setdefault(cur, [new_part()])
            continue
        if ev[0] == "break":
            _, label, loc = ev
            if cur is None:
                raise ExportError(f"{loc}: \\CommentBreak before any \\GeneralSection or \\ReviewerSection")
            if sections[cur][-1]["blocks"] == 0:
                raise ExportError(f"{loc}: \\CommentBreak{{{label}}} closes a comment of section "
                                  f"{cur} that has no responseen block")
            sections[cur].append(new_part(label, loc))
            m = KN_RE.match(label)
            if m:
                sections[cur][-1]["kn"].append((int(m.group(1)), int(m.group(2)), loc))
            continue
        if ev[0] == "grouplabel":
            _, label, loc = ev
            m = KN_RE.match(label)
            if m and cur is not None:
                sections[cur][-1]["kn"].append((int(m.group(1)), int(m.group(2)), loc))
            continue
        _, body, where = ev
        if cur is None:
            raise ExportError(f"{where(0)}: responseen before any \\GeneralSection or \\ReviewerSection")
        md, pend, tbd = convert_block(body, where)
        sec = sections[cur][-1]
        sec["blocks"] += 1
        sec["pending"] += pend
        if tbd:
            sec["tbd"] += 1
        if md:
            sec["parts"].append(md)
    for key, parts in sections.items():
        if len(parts) > 1 and parts[-1]["blocks"] == 0:
            raise ExportError(f"{parts[-1]['where']}: \\CommentBreak{{{parts[-1]['label']}}} opens a comment of "
                              f"section {key} that has no responseen block")
    outdir.mkdir(parents=True, exist_ok=True)
    report = {}
    comments = []
    lines = ["%% counts.tex is written by tools/export_openreview.py. Do not edit.",
             "%% \\RBsetcount{file name}{characters}{limit}{pending items}{unfilled blocks}",
             "%% \\RBsetparts{section}{number of comments}, only for a section split by \\CommentBreak"]
    for key, parts in sections.items():
        n_parts = len(parts)
        # remove files of a previous export that used a different split
        stale = [outdir / f"{key}.md"] if n_parts > 1 else []
        stale += [f for f in outdir.glob(f"{key}_part*.md")
                  if not (n_parts > 1 and re.fullmatch(rf"{re.escape(key)}_part([1-9]\d*)\.md", f.name)
                          and int(f.name[len(key) + 5:-3]) <= n_parts)]
        for f in stale:
            if f.exists():
                f.unlink()
        if n_parts > 1:
            lines.append(f"\\RBsetparts{{{key}}}{{{n_parts}}}")
        for k, sec in enumerate(parts, 1):
            name = part_name(key, k, n_parts)
            text = "\n\n".join(sec["parts"])
            (outdir / f"{name}.md").write_text(text + "\n" if text else "", encoding="utf-8")
            n = len(text)
            sec["section"], sec["index"], sec["count"] = key, k, n_parts
            sec["title"] = comment_title(key, k, n_parts, cfg)
            report[name] = (n, sec)
            lines.append(f"\\RBsetcount{{{name}}}{{{n}}}{{{limit}}}{{{len(sec['pending'])}}}{{{sec['tbd']}}}")
            comments.append({"order": len(comments) + 1, "section": key, "part": k, "parts": n_parts,
                             "file": f"{name}.md", "title": sec["title"], "chars": n,
                             "newlines": text.count("\n"), "blocks": sec["blocks"],
                             "pending": len(sec["pending"]), "unfilled": sec["tbd"]})
    counts_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    problems = label_problems(sections)
    declared = read_reviewers(main.parent / cfg["reviewers"])
    if declared:
        present = [k for k in sections if k != "general"]
        problems += [f"reviewer {r} is declared in {cfg['reviewers']} but has no \\ReviewerSection"
                     for r in declared if r not in present]
        problems += [f"\\ReviewerSection{{{r}}} is not declared in {cfg['reviewers']}"
                     for r in present if r not in declared]
    over = sum(c["chars"] > limit for c in comments)
    unfilled = sum(c["unfilled"] for c in comments)
    pending = sum(c["pending"] for c in comments)
    index = {"limit": limit, "ready": not (over or unfilled or pending or problems),
             "comments": comments, "problems": problems}
    (outdir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    report["__index__"] = index
    return report


def estimate(n, pending):
    """Character count after every \\pending marker is replaced by PENDING_FILLED characters."""
    return n - sum(len(f"**[PENDING: {t}]**") - PENDING_FILLED for _, t in pending)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default=None, help="default: kit.json next to the tools directory")
    ap.add_argument("--main", default=None, help="default: the key main of kit.json")
    ap.add_argument("--outdir", default=None, help="default: the key outdir of kit.json")
    ap.add_argument("--counts", default=None, help="default: the key counts of kit.json")
    ap.add_argument("--limit", type=int, default=None, help="characters per comment, default: comment_limit of kit.json")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any file (any comment of a split section) exceeds the limit, "
                         "any \\pending or \\respTBD is left, or a (k of n) label or the reviewer list disagrees")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    if args.limit is not None:
        cfg["comment_limit"] = args.limit
    limit = int(cfg["comment_limit"])
    try:
        report = export(args.main, args.outdir, args.counts, cfg)
    except ExportError as e:
        print(f"export failed: {e}", file=sys.stderr)
        return 2
    index = report.pop("__index__")
    print("OpenReview export (characters = len of pasted text, newline = 1; "
          f"est. = count with every \\pending filled by {PENDING_FILLED} characters)")
    over = unfilled = 0
    all_pending = []
    for key, (n, sec) in report.items():
        flag = "OVER LIMIT" if n > limit else "ok"
        over += n > limit
        unfilled += sec["tbd"]
        print(f"  {key + '.md':20s} {n:5d} / {limit}  {flag:10s}"
              f" est. {estimate(n, sec['pending']):5d}, blocks {sec['blocks']}, unfilled {sec['tbd']},"
              f" pending {len(sec['pending'])}  title: {sec['title']}")
        all_pending += [(key, w, t) for w, t in sec["pending"]]
    if all_pending:
        print(f"Pending items (\\pending), {len(all_pending)} in total:")
        for key, w, t in all_pending:
            print(f"  [{key}] {w}  {t}")
    else:
        print("Pending items (\\pending): none")
    for p in index["problems"]:
        print(f"PROBLEM: {p}")
    if args.strict and (over or unfilled or all_pending or index["problems"]):
        print("strict mode: not ready to paste", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

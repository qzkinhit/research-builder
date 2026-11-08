#!/usr/bin/env python3
"""Parse source/reviews.md into review units (id, reviewer, section, text).

Shared by gen_reviews_tex.py and check_reviews.py. The format of reviews.md is
described in the README of the kit.

  ## Reviewer <R>  (scores)        starts one review
  ### <heading>                    a part of the review
  (<R>-W1) text                    a numbered unit, also as the item of a bullet
  ## Context: ...                  a block of reference items (not replied to)
  ---                              closes the current block

Unit ids follow the numbering written in reviews.md (for example R1-W1a, R2-Q2).
Text without a number gets a derived id.
  <R>-Sum        the summary (all paragraphs in one unit)
  <R>-S<k>       the k-th paragraph or bullet of the strengths
  <id>-end       an unnumbered paragraph that closes the numbered unit <id>
                 (<id>-end2, <id>-end3 for further paragraphs)
  REF-<k>        the k-th bullet of a context block
The leading "- " of a bullet and the "(id) " prefix are presentation and are
dropped from the unit text. Everything else is kept character for character.
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = HERE.parent / "source" / "reviews.md"

REVIEWER_RE = re.compile(r"^## Reviewer (\w+)\s+\((.*)\)\s*$")
ID_RE = re.compile(r"^\((\w+-\w+)\)\s+(.*)$", re.S)
SUMMARY = {"summary", "paper summary"}
STRENGTHS = {"strengths", "critical strengths", "strength"}


def _chunks(lines):
    """Split a subsection into paragraphs, every bullet line is its own chunk."""
    chunks, buf = [], []
    for line in lines:
        if not line.strip():
            if buf:
                chunks.append(" ".join(buf))
                buf = []
            continue
        if line.startswith("- "):
            if buf:
                chunks.append(" ".join(buf))
                buf = []
            chunks.append(line[2:].strip())
            continue
        buf.append(line.strip())
    if buf:
        chunks.append(" ".join(buf))
    return chunks


def parse(path=DEFAULT_SOURCE):
    text = Path(path).read_text(encoding="utf-8")
    lines = text.split("\n")
    units, meta = [], {}
    reviewer, section, sec_lines = None, None, []

    def flush():
        if reviewer is None or section is None:
            return
        chunks = _chunks(sec_lines)
        low = section.lower()
        if low in SUMMARY:
            units.append((f"{reviewer}-Sum", reviewer, section, "\n\n".join(chunks)))
            return
        last_id, tail = None, 0
        for k, ch in enumerate(chunks, 1):
            m = ID_RE.match(ch)
            if m:
                last_id, tail = m.group(1), 0
                units.append((last_id, reviewer, section, m.group(2)))
            elif low in STRENGTHS:
                units.append((f"{reviewer}-S{k}", reviewer, section, ch))
            elif section == "REF":
                units.append((f"REF-{k}", "REF", section, ch))
            elif last_id:
                tail += 1
                suffix = "-end" if tail == 1 else f"-end{tail}"
                units.append((f"{last_id}{suffix}", reviewer, section, ch))
            else:
                raise ValueError(f"unnumbered text in {reviewer}/{section}: {ch[:60]}")

    for line in lines:
        m = REVIEWER_RE.match(line)
        if m:
            flush()
            reviewer, section, sec_lines = m.group(1), None, []
            meta[reviewer] = m.group(2)
            continue
        if line.startswith("## Context:"):
            flush()
            reviewer, section, sec_lines = "REF", "REF", []
            continue
        if line.startswith("### "):
            flush()
            section, sec_lines = line[4:].strip(), []
            continue
        if line.strip() == "---":
            flush()
            section, sec_lines = None, []
            continue
        if section is not None:
            sec_lines.append(line)
    flush()
    return units, meta


if __name__ == "__main__":
    us, meta = parse()
    for uid, r, s, t in us:
        print(f"{uid:16s} {s:22s} {len(t):5d}  {t[:50]}")
    print(meta)

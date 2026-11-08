#!/usr/bin/env python3
"""Self-test for export_openreview.py and check_markdown.py. Run: python3 tools/test_export_openreview.py"""
import contextlib
import io
import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_markdown as cm  # noqa: E402
import export_openreview as ex  # noqa: E402

CFG = dict(ex.DEFAULTS)

SAMPLE = r"""
% a full-line comment is dropped without breaking the paragraph
\rhead{W1a \& Q1. Variance across splits}
We ran \textbf{five splits} and \textit{three} training runs,% trailing comment
here the gain is $\Delta = 0.07 \pm 0.01$ at $\rho=0.4$, i.e.\ 7.0\% over
R-Match~(Table~1). Ranges such as 0.05--0.30 keep an en dash, and ``quotes''
become plain. \emph{Emphasis}, \texttt{code\_name}, \ldots{} and a literal \$5
plus \{braces\}, \#123 and a\_b. A star * is escaped.

\begin{itemize}
  \item First point with \textbf{bold}.
  \item Second point
  \begin{enumerate}
    \item nested one
    \item nested two
  \end{enumerate}
\end{itemize}

\begin{enumerate}
\item Step one.
\item Step two with \pending{extra mean}.
\end{enumerate}

\begin{rtable}{lrc}
Method & Mean & Note \\
\midrule
OurSys & \pending{mean} & $a$ \\
R-Match & 0.7333 & x | y \\
\end{rtable}

See \href{https://example.org/r/x}{the repository} or \url{https://example.org}.
"""

EXPECTED = (
    "#### W1a & Q1. Variance across splits\n"
    "\n"
    "We ran **five splits** and *three* training runs,"
    "here the gain is $\\Delta = 0.07 \\pm 0.01$ at $\\rho=0.4$, i.e. 7.0% over "
    "R-Match (Table 1). Ranges such as 0.05\u20130.30 keep an en dash, and \"quotes\" "
    "become plain. *Emphasis*, `code_name`, ... and a literal \\$5 "
    "plus {braces}, #123 and a_b. A star \\* is escaped.\n"
    "\n"
    "- First point with **bold**.\n"
    "- Second point\n"
    "  1. nested one\n"
    "  2. nested two\n"
    "\n"
    "1. Step one.\n"
    "2. Step two with **[PENDING: extra mean]**.\n"
    "\n"
    "|Method|Mean|Note|\n"
    "|---|---:|:---:|\n"
    "|OurSys|**[PENDING: mean]**|$a$|\n"
    "|R-Match|0.7333|x \\| y|\n"
    "\n"
    "See [the repository](https://example.org/r/x) or https://example.org."
)


def run_main(args):
    """ex.main with its console output captured, independent of the kit.json of the project."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return ex.main(args + ["--config", "/nonexistent/kit.json"])


def conv(body):
    text, lm = ex.strip_comments(body)
    return ex.convert_block(text)


class TestConvert(unittest.TestCase):
    def test_sample(self):
        md, pending, tbd = conv(SAMPLE)
        if md != EXPECTED:
            print("\n--- got ---\n" + md + "\n--- expected ---\n" + EXPECTED)
        self.assertEqual(md, EXPECTED)
        self.assertEqual([n for _, n in pending], ["extra mean", "mean"])
        self.assertFalse(tbd)

    def test_tbd(self):
        md, pending, tbd = conv(r"\respTBD")
        self.assertEqual(md, "")
        self.assertTrue(tbd)

    def test_display_math(self):
        md, _, _ = conv("Before,\n\n\\[ s(p) = \\frac{1}{|B|}\n  \\sum_{b \\in B} R(b) , \\]\n\nafter.")
        self.assertEqual(md, "Before,\n\n$$s(p) = \\frac{1}{|B|} \\sum_{b \\in B} R(b) ,$$\n\nafter.")

    def test_errors(self):
        bad = {
            r"see \cite{x}": "unsupported command \\cite",
            r"a \ref{fig}": "unsupported command \\ref",
            r"$$x$$": "displayed math",
            "a --- b": "em dash",
            "a & b": "bare '&'",
            "line\\\\break": "line break",
            r"\begin{table}x\end{table}": "unsupported environment table",
            "\\begin{rtable}{lr}\nA & B \\\\\n1 & 2 & 3 \\\\\n\\end{rtable}": "3 cells",
            "\\begin{rtable}{l|r}\nA & B \\\\\n\\end{rtable}": "column spec",
            "\\begin{rtable}{l}\nA \\\\\n$a|b$ \\\\\n\\end{rtable}": "splits a Markdown table cell",
            "\\begin{rtable}{l}\nA \\\\\n\\[ x \\] \\\\\n\\end{rtable}": "displayed math",
            r"\begin{itemize}\item[a] x\end{itemize}": "labels are not supported",
            r"\textbf{open": "unbalanced",
            r"x \, y": "control symbol",
            r"\[ x": "not closed",
        }
        for src, msg in bad.items():
            with self.subTest(src=src):
                with self.assertRaises(ex.ExportError) as caught:
                    conv(src)
                self.assertIn(msg, str(caught.exception))


class TestExport(unittest.TestCase):
    def test_files_and_counts(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "part.tex").write_text(textwrap.dedent(r"""
                \ReviewerSection{R2}
                \begin{responseen}
                Short answer with \pending{n}.
                \end{responseen}
            """), encoding="utf-8")
            (d / "main.tex").write_text(textwrap.dedent(r"""
                \GeneralSection
                \begin{responseen}
                \respTBD
                \end{responseen}
                \ReviewerSection{R1}
                \begin{responseen}
                First block.
                \end{responseen}
                % \begin{responseen} commented out \end{responseen}
                \begin{responseen}
                Second
                block.
                \end{responseen}
                \input{part}
            """), encoding="utf-8")
            rep = ex.export(d / "main.tex", d / "out", d / "counts.tex", CFG)
            r1 = (d / "out" / "R1.md").read_text(encoding="utf-8")
            self.assertEqual(r1, "First block.\n\nSecond block.\n")
            self.assertEqual(rep["R1"][0], len("First block.\n\nSecond block."))
            self.assertEqual(rep["general"][0], 0)
            self.assertEqual(rep["general"][1]["tbd"], 1)
            self.assertEqual(len(rep["R2"][1]["pending"]), 1)
            counts = (d / "counts.tex").read_text(encoding="utf-8")
            self.assertIn("\\RBsetcount{R1}{27}{5000}{0}{0}", counts)
            self.assertIn("\\RBsetcount{general}{0}{5000}{0}{1}", counts)

    def _split_main(self, d):
        (d / "main.tex").write_text(textwrap.dedent(r"""
            \GeneralSection
            \begin{responseen}
            General.
            \end{responseen}
            \ReviewerSection{R1}
            \begin{rbgroup}[(1 of 2)]{R1-W1}
            \begin{responseen}
            One \pending{a}.
            \end{responseen}
            \end{rbgroup}
            \begin{responseen}
            Two.
            \end{responseen}
            \CommentBreak{(2 of 2)}
            \begin{responseen}
            Three \pending{b} and \pending{c}.
            \end{responseen}
            \begin{responseen}
            \respTBD
            \end{responseen}
            \ReviewerSection{R3}
            \begin{responseen}
            Single.
            \end{responseen}
        """), encoding="utf-8")

    def test_comment_break(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            out = d / "out"
            out.mkdir()
            # files of an earlier export with a different split are removed
            (out / "R1.md").write_text("old\n", encoding="utf-8")
            (out / "R1_part3.md").write_text("old\n", encoding="utf-8")
            (out / "R3_part1.md").write_text("old\n", encoding="utf-8")
            self._split_main(d)
            rep = ex.export(d / "main.tex", out, d / "counts.tex", CFG)
            names = sorted(p.name for p in out.glob("*.md"))
            self.assertEqual(names, ["R1_part1.md", "R1_part2.md", "R3.md", "general.md"])
            p1 = (out / "R1_part1.md").read_text(encoding="utf-8")
            p2 = (out / "R1_part2.md").read_text(encoding="utf-8")
            self.assertEqual(p1, "One **[PENDING: a]**.\n\nTwo.\n")
            self.assertEqual(p2, "Three **[PENDING: b]** and **[PENDING: c]**.\n")
            self.assertNotIn("R1", rep)
            self.assertEqual(rep["R1_part1"][0], len(p1) - 1)
            self.assertEqual(rep["R1_part2"][0], len(p2) - 1)
            self.assertEqual(len(rep["R1_part1"][1]["pending"]), 1)
            self.assertEqual(len(rep["R1_part2"][1]["pending"]), 2)
            self.assertEqual(rep["R1_part2"][1]["tbd"], 1)
            self.assertEqual(rep["R3"][0], len("Single."))
            counts = (d / "counts.tex").read_text(encoding="utf-8")
            self.assertIn("\\RBsetparts{R1}{2}", counts)
            self.assertIn(f"\\RBsetcount{{R1_part1}}{{{len(p1) - 1}}}{{5000}}{{1}}{{0}}", counts)
            self.assertIn(f"\\RBsetcount{{R1_part2}}{{{len(p2) - 1}}}{{5000}}{{2}}{{1}}", counts)
            self.assertIn("\\RBsetcount{R3}{7}{5000}{0}{0}", counts)
            self.assertNotIn("\\RBsetparts{R3}", counts)
            self.assertNotIn("\\RBsetcount{R1}", counts)
            args = ["--main", str(d / "main.tex"), "--outdir", str(out), "--counts", str(d / "counts.tex")]
            self.assertEqual(run_main(args), 0)
            # strict mode fails on the pending items and the unfilled block of the split section
            self.assertEqual(run_main(args + ["--strict"]), 1)
            self.assertEqual(ex.estimate(len("x **[PENDING: ab]**"), [("f:1", "ab")]), len("x ") + 6)

    def test_titles_and_index(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self._split_main(d)
            ex.export(d / "main.tex", d / "out", d / "counts.tex", CFG)
            index = json.loads((d / "out" / "index.json").read_text(encoding="utf-8"))
            titles = [c["title"] for c in index["comments"]]
            self.assertEqual(titles, ["General response", "Response to Reviewer R1 (1 of 2)",
                                      "Response to Reviewer R1 (2 of 2)", "Response to Reviewer R3"])
            self.assertEqual([c["order"] for c in index["comments"]], [1, 2, 3, 4])
            self.assertEqual(index["comments"][1]["file"], "R1_part1.md")
            self.assertFalse(index["ready"])
            self.assertEqual(index["problems"], [])

    def test_label_problems(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            block = "\\begin{responseen}\nx\n\\end{responseen}\n"
            (d / "main.tex").write_text("\\ReviewerSection{R1}\n" + block + "\\CommentBreak{(2 of 3)}\n" + block,
                                        encoding="utf-8")
            rep = ex.export(d / "main.tex", d / "out", d / "counts.tex", CFG)
            problems = " | ".join(rep["__index__"]["problems"])
            self.assertIn("label (2 of 3) sits on comment 2 of 2", problems)
            self.assertIn("comment 1 of 2 has no (1 of 2) label", problems)
            args = ["--main", str(d / "main.tex"), "--outdir", str(d / "out"), "--counts", str(d / "counts.tex")]
            self.assertEqual(run_main(args + ["--strict"]), 1)

    def test_declared_reviewers(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "reviewers.tex").write_text("\\RevReviewer{R1}{112233}\n\\RevReviewer{R2}{445566}\n", encoding="utf-8")
            block = "\\begin{responseen}\nx\n\\end{responseen}\n"
            (d / "main.tex").write_text("\\ReviewerSection{R1}\n" + block + "\\ReviewerSection{R9}\n" + block,
                                        encoding="utf-8")
            rep = ex.export(d / "main.tex", d / "out", d / "counts.tex", CFG)
            problems = " | ".join(rep["__index__"]["problems"])
            self.assertIn("reviewer R2 is declared", problems)
            self.assertIn("\\ReviewerSection{R9} is not declared", problems)

    def test_limit_per_comment(self):
        # two comments of 3000 characters each pass, one comment of 6000 fails
        para = "w" * 3000
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            block = "\\begin{responseen}\n" + para + "\n\\end{responseen}\n"
            src = "\\ReviewerSection{R2}\n" + block + "\\CommentBreak{(2 of 2)}\n" + block
            (d / "main.tex").write_text(src.replace("\\ReviewerSection{R2}\n", "\\ReviewerSection{R2}\n\\begin{rbgroup}[(1 of 2)]{}\\end{rbgroup}\n"),
                                        encoding="utf-8")
            args = ["--main", str(d / "main.tex"), "--outdir", str(d / "out"), "--counts", str(d / "c.tex")]
            self.assertEqual(run_main(args + ["--strict"]), 0)
            (d / "main.tex").write_text("\\ReviewerSection{R2}\n" + block.replace(para, para + para),
                                        encoding="utf-8")
            self.assertEqual(run_main(args + ["--strict"]), 1)

    def test_comment_break_errors(self):
        bad = {
            "\\CommentBreak{P}\n\\GeneralSection\n": "before any",
            "\\ReviewerSection{R1}\n\\CommentBreak{P}\n\\begin{responseen}\nx\n\\end{responseen}\n":
                "has no responseen block",
            "\\ReviewerSection{R1}\n\\begin{responseen}\nx\n\\end{responseen}\n\\CommentBreak{P}\n":
                "has no responseen block",
            "\\ReviewerSection{R1}\n\\begin{responseen}\nx\n\\CommentBreak{P}\ny\n\\end{responseen}\n":
                "not inside responseen",
        }
        for src, msg in bad.items():
            with self.subTest(src=src):
                with tempfile.TemporaryDirectory() as d:
                    d = Path(d)
                    (d / "main.tex").write_text(src, encoding="utf-8")
                    with self.assertRaises(ex.ExportError) as caught:
                        ex.export(d / "main.tex", d / "out", d / "counts.tex", CFG)
                    self.assertIn(msg, str(caught.exception))

    def test_error_location(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "main.tex").write_text(
                "\\ReviewerSection{R3}\n\\begin{responseen}\nok\n\nbad \\cite{x}\n\\end{responseen}\n",
                encoding="utf-8")
            with self.assertRaises(ex.ExportError) as caught:
                ex.export(d / "main.tex", d / "out", d / "counts.tex", CFG)
            self.assertIn("main.tex:5", str(caught.exception))


class TestReviewsSource(unittest.TestCase):
    SAMPLE = """\
# Title

## Reviewer R1  (Rating 3; Confidence 4)

### Summary
First paragraph.

Second paragraph.

### Strengths
Clear writing.

- A wide "comparison".

### Weaknesses
(R1-W1) One weakness.
- (R1-W2) A bulleted weakness with 5% and a_b.
A closing paragraph without a number.

### Questions
(R1-Q1) A question?

---

## Context: reference items only
- First item.
- Second item.
"""

    def test_units(self):
        import reviews_source as rs
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "reviews.md"
            p.write_text(self.SAMPLE, encoding="utf-8")
            units, meta = rs.parse(p)
        ids = [u[0] for u in units]
        self.assertEqual(ids, ["R1-Sum", "R1-S1", "R1-S2", "R1-W1", "R1-W2", "R1-W2-end", "R1-Q1", "REF-1", "REF-2"])
        self.assertEqual(units[0][3], "First paragraph.\n\nSecond paragraph.")
        self.assertEqual(units[4][3], "A bulleted weakness with 5% and a_b.")
        self.assertEqual(meta, {"R1": "Rating 3; Confidence 4"})

    def test_unnumbered_text_is_an_error(self):
        import reviews_source as rs
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "reviews.md"
            p.write_text("## Reviewer R1  (x)\n\n### Weaknesses\nNo number here.\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                rs.parse(p)

    def test_escape_round_trip(self):
        import check_reviews as chk
        import gen_reviews_tex as gen
        text = 'A "quote", 5% of a_b, $x$, #1, {b}, c~d, e^f and g\\h & i.'
        self.assertEqual(chk.unescape(gen.esc(text)), text)
        self.assertEqual(gen.label("R1-Sum"), "R1 摘要")
        self.assertEqual(gen.label("R1-S2"), "R1 优点 2")
        self.assertEqual(gen.label("R1-W1-end"), "R1-W1（末段）")
        self.assertEqual(gen.label("REF-3"), "参考 3")


class TestMarkdown(unittest.TestCase):
    def errors(self, text):
        return cm.check_text("t.md", text)[0]

    def test_clean(self):
        text = ("Gain $x_{i}$ and $\\frac{a}{b}$.\n\n$$s = \\sum_{b \\in B} R(b)$$\n\n"
                "|A|B|\n|---|---|\n|1|$c$|\n")
        self.assertEqual(self.errors(text), [])

    def test_table_cells(self):
        self.assertIn("table row", self.errors("|A|B|\n|---|---|\n|1|2|3|\n")[0])

    def test_escaped_pipe_is_not_a_cell(self):
        self.assertEqual(self.errors("|A|B|\n|---|---|\n|1|2 \\| 3|\n"), [])

    def test_unclosed_math(self):
        self.assertIn("unclosed", self.errors("price $x")[0])

    def test_latex_outside_math(self):
        self.assertIn("LaTeX command", self.errors("see \\cite{x}")[0])

    def test_backslash_punctuation(self):
        self.assertIn("\\lbrace", self.errors("set $\\{a\\}$")[0])
        self.assertIn("removes the backslash", self.errors("space $a\\,b$")[0])
        self.assertIn("removes the backslash", self.errors("$$a \\\\ b$$")[0])

    def test_underscore_pairs(self):
        # a subscript after a closing brace opens emphasis, a later subscript closes it
        self.assertIn("emphasis", self.errors("Here $\\mathrm{a}_k$ and $x_{i}$ appear.")[0])
        self.assertEqual(self.errors("Here $x_{i}$ and $\\mathrm{a}_k$ appear."), [])
        self.assertEqual(self.errors("Here $\\mathrm{a}_k$ appears.\n\nThere $x_{i}$ appears."), [])

    def test_star(self):
        self.assertIn("star", self.errors("$a*b$")[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)

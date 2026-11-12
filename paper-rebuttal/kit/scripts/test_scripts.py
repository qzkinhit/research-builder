#!/usr/bin/env python3
"""Tests of the checking scripts on the fictional example. Run: python3 scripts/test_scripts.py

Every test works on a temporary copy of the kit, so the kit itself stays unchanged.
PDF tests are skipped if PyMuPDF is not installed.
"""
import contextlib
import csv
import importlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(KIT / "project" / "tools"))

import build_deliverables as bd  # noqa: E402
import build_interval_map as bim  # noqa: E402
import check_glance_table as cgt  # noqa: E402
import check_invariants as ci  # noqa: E402
import check_margin_tags as cmt  # noqa: E402
import check_rounding as cr  # noqa: E402
import export_openreview as ex  # noqa: E402


def run(main, argv):
    """Run a script main function, capture its output and return (status, text)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        status = main(argv)
    return status, out.getvalue()


def read_claims(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_claims(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        w = csv.DictWriter(handle, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


class KitCopy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "kit"
        shutil.copytree(KIT, self.root, ignore=shutil.ignore_patterns("__pycache__", "*.pdf", "*.aux", "*.log", "openreview",
                                                                      "deliverables", "drafts", "counts.tex"))
        self.project = self.root / "project"
        self.cfg = self.project / "kit.json"
        self.main_tex = self.project / "rebuttal_main.tex"

    def tearDown(self):
        self.tmp.cleanup()

    def export(self):
        cfg = json.loads(self.cfg.read_text(encoding="utf-8"))
        ex.export(self.main_tex, self.project / "openreview", self.project / "counts.tex", {**ex.DEFAULTS, **cfg})

    def edit(self, path, old, new):
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"{old!r} not in {path}")
        path.write_text(text.replace(old, new), encoding="utf-8")


class TestRounding(KitCopy):
    def claims(self, rows):
        p = self.root / "example" / "c.csv"
        write_claims(p, rows)
        return run(cr.main, ["--claims", str(p), "--runs", str(self.root / "example" / "runs.csv"), "--root", str(self.root)])

    def test_example(self):
        status, text = run(cr.main, ["--claims", str(self.root / "example" / "claims.csv"),
                                     "--runs", str(self.root / "example" / "runs.csv"), "--root", str(self.root)])
        self.assertEqual(status, 0, text)
        self.assertIn("23 claims, 0 failed", text)
        self.assertIn("trap avoided", text)

    def test_double_rounding_is_reported(self):
        rows = read_claims(self.root / "example" / "claims.csv")
        wrong = [dict(r) for r in rows if r["id"] == "C07"]
        wrong[0]["printed"] = "+3.7"
        wrong[0]["file"] = ""
        status, text = self.claims(wrong)
        self.assertEqual(status, 1)
        self.assertIn("DOUBLE ROUNDING", text)

    def test_within_uses_full_precision(self):
        # 2.4013 rounds to 2.4, but the claim "within 2.4" is false at full precision
        rows = read_claims(self.root / "example" / "claims.csv")
        wrong = [dict(r) for r in rows if r["id"] == "C15"]
        wrong[0]["printed"] = "2.4"
        wrong[0]["bound"] = "2.4"
        wrong[0]["file"] = ""
        status, text = self.claims(wrong)
        self.assertEqual(status, 1)
        self.assertIn("fails on D1", text)

    def test_wins_and_at_least(self):
        rows = read_claims(self.root / "example" / "claims.csv")
        w = [dict(r) for r in rows if r["id"] == "C12"]
        w[0]["printed"] = "14 of 15"
        w[0]["file"] = ""
        self.assertEqual(self.claims(w)[0], 1)
        a = [dict(r) for r in rows if r["id"] == "C13"]
        a[0]["bound"] = "5"
        self.assertIn("fails on", self.claims(a)[1])


class TestRoundingHelper(unittest.TestCase):
    def test_rnd_is_half_up_and_exact(self):
        from fractions import Fraction as F
        import fullprec as P
        self.assertEqual(P.rnd(F(5, 1000), 2), "0.01")
        self.assertEqual(P.rnd(F(-5, 1000), 2), "-0.01")
        self.assertEqual(P.rnd(F(4999, 1000000), 2), "0.00")
        self.assertEqual(P.rnd(F(0), 2), "0.00")
        self.assertEqual(P.rnd(F(1, 3), 0), "0")
        self.assertEqual(P.rnd(F(-1, 1000000), 2), "0.00")

    def test_call_rng_depends_only_on_its_parts(self):
        import fullprec as P
        self.assertEqual(P.call_rng(0, "a", "b").random(), P.call_rng(0, "a", "b").random())
        self.assertNotEqual(P.call_rng(0, "a", "b").random(), P.call_rng(0, "a", "c").random())
        self.assertNotEqual(P.call_rng(0, "a", "b").random(), P.call_rng(1, "a", "b").random())


class TestIntervalMap(KitCopy):
    def run_map(self):
        out = Path(self.tmp.name) / "map.md"
        status, text = run(bim.main, ["--config", str(self.cfg), "--runs", str(self.root / "example" / "runs.csv"),
                                      "--comparisons", str(self.root / "example" / "comparisons.json"), "--out", str(out)])
        return status, text, out.read_text(encoding="utf-8")

    def test_example(self):
        status, text, _doc = self.run_map()
        self.assertEqual(status, 0, text)
        self.assertIn("0 to handle", text)

    def test_unmapped_and_changed(self):
        self.edit(self.main_tex, "D2 & 0.831 & 0.796 & 0.782 & +3.5 [1.7, 5.6]", "D2 & 0.831 & 0.796 & 0.782 & +3.5 [1.8, 5.6]")
        status, text, doc = self.run_map()
        self.assertEqual(status, 1)
        self.assertIn("UNMAPPED", doc)
        comps = json.loads((self.root / "example" / "comparisons.json").read_text(encoding="utf-8"))
        for c in comps:
            if c["id"] == "D":
                c["printed"] = ["[1.8, 5.6]"]
        (self.root / "example" / "comparisons.json").write_text(json.dumps(comps), encoding="utf-8")
        status, _text, doc = self.run_map()
        self.assertEqual(status, 1)
        self.assertIn("| yes | D |", doc)

    def test_stream_does_not_depend_on_other_comparisons(self):
        _s, _t, before = self.run_map()
        comps = json.loads((self.root / "example" / "comparisons.json").read_text(encoding="utf-8"))
        comps.insert(0, {"id": "Z", "printed": [], "a": "R-Match", "b": "R-Block", "metric": "n_found/n_true",
                         "filter": "budget=5", "scale": 100, "decimals": 1})
        (self.root / "example" / "comparisons.json").write_text(json.dumps(comps), encoding="utf-8")
        status, _t, after = self.run_map()
        self.assertEqual(status, 0)
        for row in before.split("\n"):
            if row.startswith("| A |") or row.startswith("| B |"):
                self.assertIn(row, after)


class TestInvariants(KitCopy):
    def dump(self, name):
        p = Path(self.tmp.name) / name
        status, text = run(ci.main, ["dump", str(p), "--config", str(self.cfg)])
        self.assertEqual(status, 0, text)
        return p

    def compare(self, a, b):
        return run(ci.main, ["compare", str(a), str(b)])

    def test_rewording_passes(self):
        before = self.dump("before.json")
        self.edit(self.main_tex, "Replies follow point by point, and the end of each reply gives the corresponding place in the revision.\n\nResults per comment, with the matching place in the revised PDF.\n\n\\begin{rtable}{lll}\nComment & Finding & Location (margin note) \\\\\n\\midrule\nW1, Q1",
                  "Replies are given point by point, each ending with the corresponding place in the revision.\n\nResults per comment, with the matching place in the revised PDF.\n\n\\begin{rtable}{lll}\nComment & Finding & Location (margin note) \\\\\n\\midrule\nW1, Q1")
        status, text = self.compare(before, self.dump("after.json"))
        self.assertEqual(status, 0, text)
        self.assertIn("INVARIANCE OK", text)

    def test_changed_number_fails(self):
        before = self.dump("before.json")
        self.edit(self.main_tex, "OurSys reaches 0.799 against 0.763 for L-Boost and 0.743", "OurSys reaches 0.799 against 0.764 for L-Boost and 0.743")
        status, text = self.compare(before, self.dump("after.json"))
        self.assertEqual(status, 1)
        self.assertIn("numbers", text)

    def test_changed_reference_fails(self):
        before = self.dump("before.json")
        self.edit(self.main_tex, "In the revision, Section 4.2 reports this budget (margin note R2-W1).",
                  "In the revision, Section 3.1 reports this budget (margin note R2-W1).")
        status, text = self.compare(before, self.dump("after.json"))
        self.assertEqual(status, 1)
        self.assertIn("mentions", text)

    def test_changed_tag_fails(self):
        before = self.dump("before.json")
        self.edit(self.main_tex, "In the revision, Section 4.2 reports these times (margin note R2-Q1).",
                  "In the revision, Section 4.2 reports these times (margin note R2-W1).")
        status, text = self.compare(before, self.dump("after.json"))
        self.assertEqual(status, 1)
        self.assertIn("tags", text)

    def test_text_outside_blocks_fails(self):
        before = self.dump("before.json")
        self.edit(self.main_tex, "\\begin{itemize}\\small", "\\begin{itemize}\\footnotesize")
        status, text = self.compare(before, self.dump("after.json"))
        self.assertEqual(status, 1)
        self.assertIn("SKELETON DIFFERS", text)

    def test_table_body_must_stay_verbatim(self):
        before = self.dump("before.json")
        self.edit(self.main_tex, "D1 & 0.880 & 0.840 & 0.816 & +4.0 [3.4, 4.6] \\\\\nD2 & 0.831 & 0.796 & 0.782 & +3.5 [1.7, 5.6] \\\\\nD3 & 0.890 & 0.856 & 0.843 & +3.4 [2.3, 4.6] \\\\\nMean",
                  "D1 & 0.880 & 0.840 & 0.816 & +4.0 [3.4, 4.6] \\\\\nD3 & 0.890 & 0.856 & 0.843 & +3.4 [2.3, 4.6] \\\\\nD2 & 0.831 & 0.796 & 0.782 & +3.5 [1.7, 5.6] \\\\\nMean")
        status, text = self.compare(before, self.dump("after.json"))
        self.assertEqual(status, 1)
        self.assertIn("rtables", text)

    def test_lint_flags_style(self):
        self.edit(self.main_tex, "Our thanks go to both reviewers for the attention", "Notably; our thanks go to both reviewers for the attention")
        status, text = run(ci.main, ["lint", "--config", str(self.cfg)])
        self.assertEqual(status, 0)
        self.assertIn("semicolon", text)
        self.assertIn("stock_en", text)


class TestGlanceTable(KitCopy):
    def check(self, *extra):
        return run(cgt.main, ["--config", str(self.cfg), *extra])

    def test_example(self):
        status, text = self.check("--revision", str(self.root / "revision" / "revmark_demo.tex"))
        self.assertEqual(status, 0, text)
        self.assertIn("glance table check: 0 problem(s)", text)

    def test_number_not_in_body(self):
        self.edit(self.main_tex, "W1, Q1, split variance & \\textbf{+3.6 points} over L-Boost [2.9, 4.5], positive in 15 of 15 cells",
                  "W1, Q1, split variance & \\textbf{+3.7 points} over L-Boost [2.9, 4.5], positive in 15 of 15 cells")
        status, text = self.check()
        self.assertEqual(status, 1)
        self.assertIn("'3.7'", text)

    def test_chinese_table_must_match(self):
        self.edit(self.main_tex, "W2，选择分数 & 分数改为基于召回率增益的独立公式", "W2，选择分数 & 分数改为基于 9 个增益的独立公式")
        status, text = self.check()
        self.assertEqual(status, 1)
        self.assertIn("Chinese-only", text)

    def test_third_cell_needs_tag(self):
        self.edit(self.main_tex, "Equation 2 in Section 3.2 (R1-W2)", "Equation 2 in Section 3.2")
        status, text = self.check()
        self.assertEqual(status, 1)
        self.assertIn("third cell", text)

    def test_missing_table(self):
        self.edit(self.main_tex, "\\begin{rtable}{lll}", "\\begin{rtable}{ccc}")
        status, text = self.check()
        self.assertEqual(status, 1)
        status, text = self.check("--optional")
        self.assertEqual(status, 0, text)


class TestDeliverables(KitCopy):
    def build(self, *extra):
        return run(bd.main, ["--config", str(self.cfg), "--out", str(self.out), *extra])

    def setUp(self):
        super().setUp()
        self.out = Path(self.tmp.name) / "deliv"
        self.export()
        for src in ("rebuttal_main.pdf",):
            (self.project / src).write_bytes(b"%PDF-demo\n")
        (self.root / "revision" / "revmark_demo.pdf").write_bytes(b"%PDF-demo2\n")

    def test_example(self):
        status, text = self.build()
        self.assertEqual(status, 0, text)
        names = sorted(p.name for p in (self.out / "openreview").iterdir())
        self.assertIn("02_R1_1of2.md", names)
        self.assertIn("05_followup_after_upload.md", names)
        self.assertFalse((self.out / "SHA256SUMS").exists())
        self.assertTrue(bd.checksum_path(self.out).read_text(encoding="utf-8").strip())
        self.assertIn("Response to Reviewer R1 (1 of 2)", (self.out / "README.md").read_text(encoding="utf-8"))
        self.assertEqual((self.out / "openreview" / "01_general.md").read_bytes(),
                         (self.project / "openreview" / "general.md").read_bytes())

    def test_byte_difference_is_detected(self):
        real = shutil.copyfile

        def corrupt(src, dst, **kw):
            real(src, dst, **kw)
            if Path(dst).name == "04_R2.md":
                with open(dst, "ab") as handle:
                    handle.write(b"x")
            return dst

        bd.shutil.copyfile = corrupt
        try:
            status, text = self.build("--clean")
        finally:
            bd.shutil.copyfile = real
        self.assertEqual(status, 1)
        self.assertIn("identical=False", text)

    def test_stale_file_stops_the_build(self):
        self.assertEqual(self.build()[0], 0)
        (self.out / "openreview" / "99_old.md").write_text("old", encoding="utf-8")
        status, text = self.build()
        self.assertEqual(status, 1)
        self.assertIn("unexpected files", text)
        self.assertEqual(self.build("--clean")[0], 0)

    def test_not_ready_is_refused(self):
        index = json.loads((self.project / "openreview" / "index.json").read_text(encoding="utf-8"))
        index["ready"] = False
        (self.project / "openreview" / "index.json").write_text(json.dumps(index), encoding="utf-8")
        status, text = self.build()
        self.assertEqual(status, 1)
        self.assertIn("not ready", text)
        self.assertEqual(self.build("--allow-not-ready")[0], 0)

    def test_placeholder_is_detected(self):
        self.edit(self.project / "templates" / "reminder_before_deadline.md", "ends on December 3", "closes on <date>")
        status, text = self.build("--clean")
        self.assertEqual(status, 1)
        self.assertIn("PLACEHOLDER", text)

    def test_over_limit_is_detected(self):
        index = json.loads((self.project / "openreview" / "index.json").read_text(encoding="utf-8"))
        index["limit"] = 100
        (self.project / "openreview" / "index.json").write_text(json.dumps(index), encoding="utf-8")
        status, text = self.build("--clean")
        self.assertEqual(status, 1)
        self.assertIn("chars=", text)


class TestMarginTagsSource(KitCopy):
    def check(self, *extra):
        return run(cmt.main, ["--reviewers", str(self.project / "reviewers.tex"), *extra])

    def test_example(self):
        status, text = self.check("--tex", str(self.root / "revision" / "revmark_demo.tex"),
                                  "--reviews", str(self.project / "source" / "reviews.md"),
                                  "--rebuttal", str(self.main_tex))
        self.assertEqual(status, 0, text)

    def tex(self, body):
        p = Path(self.tmp.name) / "t.tex"
        p.write_text(body, encoding="utf-8")
        return str(p)

    def test_unknown_reviewer_and_unit(self):
        status, text = self.check("--tex", self.tex("\\rev{x}{R9-W1} \\rev{y}{R1-W9}"),
                                  "--reviews", str(self.project / "source" / "reviews.md"))
        self.assertEqual(status, 1)
        self.assertIn("undeclared reviewer", text)
        self.assertIn("R1-W9 is not a unit", text)

    def test_too_many_tags(self):
        status, text = self.check("--tex", self.tex("\\rev{x}{R1-W1, R1-W2, R1-Q1}"))
        self.assertEqual(status, 1)
        self.assertIn("3 tags on one note", text)

    def test_marks_rules(self):
        status, text = self.check("--tex", self.tex("\\section{Title \\rev{x}{R1-W1}}\n\\rev{ends with a comma,}{R1-W1}\n\\textcolor{red}{y}\n\\rev{z}{}"))
        self.assertEqual(status, 1)
        self.assertIn("inside a heading", text)
        self.assertIn("ends in punctuation", text)
        self.assertIn("red text outside", text)
        self.assertIn("empty tag list", text)
        status, text = self.check("--tex", self.tex("\\rev{\\pending{x}}{R1-W1} \\rev{(only this)}{R1-W1}"))
        self.assertEqual(status, 1)
        self.assertIn("only a \\pending", text)
        self.assertIn("only a parenthetical", text)

    def test_quoted_tag_must_exist(self):
        status, text = self.check("--tex", self.tex("\\rev{x}{R1-W1}"), "--rebuttal", str(self.main_tex))
        self.assertEqual(status, 1)
        self.assertIn("no note in the revision carries it", text)

    def test_unmarked_edits_are_listed(self):
        original = self.tex("Plain text stays. Another sentence stays.")
        revised = Path(self.tmp.name) / "r.tex"
        revised.write_text("Plain text stays. \\rev{New sentence.}{R1-W1} Another sentence moved a word.", encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = cmt.main(["--original", original, "--revised", str(revised)])
        self.assertEqual(status, 0)
        self.assertIn("unmarked edits: 1", out.getvalue())
        self.assertNotIn("New sentence", out.getvalue())


try:
    pymupdf = importlib.import_module("pymupdf")
except ImportError:
    pymupdf = None


@unittest.skipIf(pymupdf is None, "PyMuPDF is not installed")
class TestMarginTagsPdf(KitCopy):
    def setUp(self):
        super().setUp()
        self.pdf = Path(self.tmp.name) / "t.pdf"
        self.reviewers = self.project / "reviewers.tex"

    def make(self, spans):
        doc = pymupdf.open()
        page = doc.new_page(width=612, height=792)
        for text, x, y, color in spans:
            page.insert_text((x, y), text, fontsize=10, color=tuple(c / 255 for c in color))
        doc.save(self.pdf)

    def check(self, *extra):
        return run(cmt.main, ["--reviewers", str(self.reviewers), "--pdf", str(self.pdf), "--text-right", "500", *extra])

    RED = (255, 0, 0)
    R1 = (0x7B, 0x32, 0x94)

    def base(self):
        return [("Body text of the paper in black.", 100, 100, (0, 0, 0)), ("Changed text in red.", 100, 116, self.RED)]

    def test_clean(self):
        self.make(self.base() + [("R1-W1", 510, 116, self.R1)])
        status, text = self.check()
        self.assertEqual(status, 0, text)

    def test_wrong_colour(self):
        self.make(self.base() + [("R1-W1", 510, 116, (0, 0, 255))])
        status, text = self.check()
        self.assertEqual(status, 1)
        self.assertIn("expected 7B3294", text)

    def test_undeclared_reviewer(self):
        self.make(self.base() + [("R7-W1", 510, 116, self.R1)])
        status, text = self.check()
        self.assertEqual(status, 1)
        self.assertIn("not declared", text)

    def test_overlap(self):
        self.make(self.base() + [("R1-W1", 510, 116, self.R1), ("R1-Q1", 512, 119, self.R1)])
        status, text = self.check()
        self.assertEqual(status, 1)
        self.assertIn("overlap", text)

    def test_outside_the_page(self):
        # the writer of the test PDF drops glyphs beyond the page, so the tag stops just short of it
        self.make(self.base() + [("R1-W1", 540, 116, self.R1)])
        status, text = self.check()
        self.assertEqual(status, 1)
        self.assertIn("page edge", text)

    def test_inside_the_text_block(self):
        self.make(self.base() + [("R1-W1", 400, 116, self.R1)])
        status, text = self.check()
        self.assertEqual(status, 1)
        self.assertIn("not right of the text block", text)

    def test_far_from_red(self):
        self.make(self.base() + [("R1-W1", 510, 400, self.R1)])
        status, text = self.check()
        self.assertEqual(status, 0, text)
        self.assertIn("WARN", text)
        status, text = self.check("--strict")
        self.assertEqual(status, 1)

    def test_stray_colour(self):
        self.make(self.base() + [("Green text", 100, 140, (0, 128, 0)), ("R1-W1", 510, 116, self.R1)])
        status, text = self.check()
        self.assertEqual(status, 1)
        self.assertIn("not an allowed colour", text)
        status, text = self.check("--allow", "008000")
        self.assertEqual(status, 0, text)


class TestFindTags(unittest.TestCase):
    def test_prefix_and_item_in_separate_spans(self):
        # paragraph-end tags come out of the PDF as "(#Review" and "R1-W2)" without a space between the spans
        spans = [("text.", 0, (0, 0, 10, 10), 1), ("(#Review", 1, (11, 0, 30, 10), 1),
                 ("R1-W2,", 1, (31, 0, 40, 10), 1), ("#Review", 1, (41, 0, 60, 10), 1), ("R1-Q1)", 1, (61, 0, 70, 10), 1)]
        items = [t[0] for t in cmt.find_tags(spans, "#Review")]
        self.assertEqual(items, ["R1-W2", "R1-Q1"])

    def test_margin_tag_in_one_span(self):
        spans = [("R2-Q1", 2, (500, 0, 530, 10), 1)]
        self.assertEqual([t[0] for t in cmt.find_tags(spans, "")], ["R2-Q1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Collect the texts and files of the discussion period into one directory and verify them.

usage: build_deliverables.py --config kit.json [--root DIR] [--out DIR] [--clean] [--allow-not-ready]

Reads the export index (openreview/index.json) and the key deliverables of
kit.json. Comments are copied in posting order as NN_<section>_<k>of<n>.md, then
the follow-up after the upload (the English text alone, and with its Chinese
reference), then the reminder file, then the files listed in copy. Every copy is
compared byte for byte with its source. A README.md lists each comment with its
title and character count. The SHA-256 list of every file is written beside the
directory, as <out>_checksums.txt, so the directory holds no checksum file (the
playbook keeps checksum files out of what reviewers receive).

The build stops if a file of an earlier build would remain beside the new one
(use --clean), if the export is not ready to paste (use --allow-not-ready only
for a dry run), if a comment exceeds the limit, or if a template still holds a
<placeholder>. Exit status 1 on any problem.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

SEP = "\n\n"


def checksum_path(out):
    """Local checksum list beside the deliverables directory, never inside it."""
    return out.parent / f"{out.name}_checksums.txt"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def english_of(template):
    """The text under the heading English of a follow-up template."""
    m = re.search(r"^## English\n\n(.*?)\n\n^## ", template, re.S | re.M)
    if not m:
        raise SystemExit("the follow-up template has no ## English section followed by another ## section")
    return m.group(1)


def placeholders(text):
    return re.findall(r"<[A-Za-z一-鿿][^<>\n]{0,40}>", text)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default="kit.json")
    ap.add_argument("--root", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--clean", action="store_true", help="remove the output directory first")
    ap.add_argument("--allow-not-ready", action="store_true")
    args = ap.parse_args(argv)
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    root = Path(args.root) if args.root else Path(args.config).resolve().parent
    spec = cfg.get("deliverables", {})
    out = Path(args.out) if args.out else root / spec.get("out", "deliverables")
    src_dir = root / cfg.get("outdir", "openreview")
    index = json.loads((src_dir / "index.json").read_text(encoding="utf-8"))
    limit = int(index["limit"])
    if not index["ready"] and not args.allow_not_ready:
        print("the export is not ready to paste, run make strict first", file=sys.stderr)
        return 1
    if args.clean and out.exists():
        shutil.rmtree(out)
    paste = out / "openreview"
    plan = []        # (source, destination, title, kind)
    k = 0
    for c in index["comments"]:
        k += 1
        tail = f"{c['section']}_{c['part']}of{c['parts']}" if c["parts"] > 1 else c["section"]
        plan.append((src_dir / c["file"], paste / f"{k:02d}_{tail}.md", c["title"], "comment"))
    followup = root / spec["followup"] if spec.get("followup") else None
    reminder = root / spec["reminder"] if spec.get("reminder") else None
    extras = []
    if followup:
        k += 1
        extras.append((None, paste / f"{k:02d}_followup_after_upload.md", "上传修订稿后发，标题自拟", "followup"))
        extras.append((followup, paste / f"{k:02d}_followup_after_upload_with_chinese_reference.md", "同一跟帖的中英对照，中文不发", "copy"))
    if reminder:
        k += 1
        extras.append((reminder, paste / f"{k:02d}_reminder_before_deadline.md", "讨论期结束前按需催复，审稿人回应后致谢", "copy"))
    files = [(root / item["src"], out / item["dst"], "", "copy") for item in spec.get("copy", [])]
    wanted = {p for _s, p, _t, _k in plan + extras + files}
    existing = {p for p in out.rglob("*") if p.is_file()} if out.exists() else set()
    old_sums = out / "SHA256SUMS"
    if old_sums in existing:
        old_sums.unlink()
        existing.discard(old_sums)
        print(f"removed {old_sums} of an earlier build, the list now goes to {checksum_path(out)}")
    stale = sorted(str(p.relative_to(out)) for p in existing - wanted if p.name != "README.md")
    if stale:
        print(f"unexpected files in {out}: {stale} (use --clean)", file=sys.stderr)
        return 1
    bad = 0
    for s, dst, _t, kind in plan + extras + files:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if kind == "followup":
            text = english_of(followup.read_text(encoding="utf-8")) + "\n"
            dst.write_text(text, encoding="utf-8")
        else:
            if not s.exists():
                print(f"MISSING  {s}")
                bad += 1
                continue
            shutil.copyfile(s, dst)
    table = []
    for s, dst, title, kind in plan:
        a, b = s.read_bytes(), dst.read_bytes()
        same = a == b
        text = b.decode("utf-8")
        n = len(text[:-1] if text.endswith("\n") else text)
        newlines = text.rstrip("\n").count("\n")
        ok = same and n <= limit
        bad += not ok
        table.append((dst.name, title, n))
        crlf = "" if n + newlines <= limit else f", {n + newlines} if newlines count twice"
        print(f"{dst.name:34s} identical={same} chars={n}/{limit}{crlf}")
    for s, dst, title, kind in extras:
        if kind == "followup":
            text = dst.read_text(encoding="utf-8")
            n = len(text) - 1
            ok = text == english_of(followup.read_text(encoding="utf-8")) + "\n" and n <= limit
            bad += not ok
            table.append((dst.name, title, n))
            print(f"{dst.name:34s} equals the English section of the template={ok} chars={n}")
        else:
            same = s.read_bytes() == dst.read_bytes()
            bad += not same
            table.append((dst.name, title, ""))
            print(f"{dst.name:34s} identical={same}")
        marks = placeholders(dst.read_text(encoding="utf-8"))
        if marks:
            bad += 1
            print(f"PLACEHOLDER in {dst.name}: {marks[:6]}")
    for s, dst, _title, _kind in files:
        same = s.exists() and s.read_bytes() == dst.read_bytes()
        bad += not same
        print(f"{dst.name:34s} identical={same}")
    lines = ["# 讨论期交付物", "",
             "发帖顺序见编号，每个文件对应一条评论，全文粘贴。Readers 选项按会议要求勾选。修订稿 PDF 与补充材料过几天再上传，上传后发跟帖。", "",
             "| 文件 | OpenReview 评论标题 | 字符数 |", "|---|---|---:|"]
    lines += [f"| {a} | {b} | {c} |" for a, b, c in table]
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    sums = [f"{sha256(p)}  {p.relative_to(out)}" for p in sorted(out.rglob("*")) if p.is_file()]
    checksum_path(out).write_text("\n".join(sums) + "\n", encoding="utf-8")
    print(f"deliverables in {out}: {len(table)} texts, {len(files)} files, {bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

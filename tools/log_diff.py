#!/usr/bin/env python3
"""Compare the warnings of two LaTeX builds of the same paper.

A late wording change can add an overfull line, an undefined reference, a
broken link or a font substitution that a look at the PDF does not reveal.
Compile the previous version under a temporary name in the same directory, so
that relative paths resolve in the same way, with the same sequence of runs as
the paper (engine, BibTeX, engine twice), and compare its log with the log of
the new build. A previous version compiled only once has no bibliography, and
the overfull lines of the reference list then show up as new warnings.

    python tools/log_diff.py old.log new.log
    python tools/log_diff.py old.log new.log --job paper_v1 --job paper_v2

Warnings, pdfTeX warnings and errors (with the l.<n> line that names the
offending command, also in the -file-line-error format) are compared as
multisets. The log is read byte for byte, so Chinese text in a warning stays
whole and is printed as UTF-8. TeX breaks log lines at 79 characters, often inside a word, so a
broken line is joined to the next one without a space. Before the comparison
the job names where they stand as file names (the names of the two logs, plus
any --job), input line numbers and page numbers are replaced by placeholders, so that a source line
that moved does not count as a change. Box sizes are kept, a changed size is a
changed warning. Exit status is 0 when the new log has no entry that the old
log lacks, 1 otherwise.
"""
import argparse
import collections
import os
import re
import sys

# pdfTeX writes "pdfTeX warning (dest)" in lower case, -file-line-error writes "./main.tex:12:" in place of "! "
START = re.compile(r'Warning|warning\s*[(:]|Overfull|Underfull|Missing character|^! |^\S+\.\w+:\d+: ')
ERR = re.compile(r'! |\S+\.\w+:\d+: ')
# a package warning continues on lines that start with the package name in parentheses, a kernel
# warning broken with \MessageBreak on lines indented by several spaces
CONT = re.compile(r'^(?:\([A-Za-z@][\w@.-]*\)\s|\s{4,}\S)')
WRAP = 79  # TeX breaks log lines at max_print_line


def entries(path):
    # latin-1 keeps every byte, and split('\n') keeps the UTF-8 bytes 0x85 and 0xa0 that splitlines() breaks at
    lines = [l.rstrip('\r') for l in open(path, encoding='latin-1', newline='').read().split('\n')]
    out, i = [], 0
    while i < len(lines):
        if not START.search(lines[i]):
            i += 1
            continue
        text, j = lines[i], i + 1
        while j < len(lines) and (len(lines[j - 1]) >= WRAP or CONT.match(lines[j])):
            text += ' ' + lines[j].strip(' \t') if CONT.match(lines[j]) else lines[j]
            j += 1
        if ERR.match(lines[i]):  # an error names the offending command only on its l.<n> line
            for k in range(j, min(j + 12, len(lines))):
                if ERR.match(lines[k]):
                    break
                if re.match(r'l\.\d+ ', lines[k]):
                    text += ' ' + lines[k]
                    break
        out.append(text)
        i = j
    return out


def normalize(entry, jobs):
    for job in sorted(jobs, key=len, reverse=True):  # only where the job name stands as a file name
        entry = re.sub(r'(?<![\w.-])' + re.escape(job) + r"(?=\.[A-Za-z]|['\s]|$)", 'JOB', entry)
    entry = re.sub(r'^(\S+\.\w+):\d+: ', r'\1:N: ', entry)
    entry = re.sub(r'\bl\.\d+ ', 'l.N ', entry)
    entry = re.sub(r'on input line \d+', 'on input line N', entry)
    entry = re.sub(r'at lines? \d+(--\d+)?', 'at lines N', entry)
    entry = re.sub(r'\bpage \d+', 'page N', entry)
    entry = re.sub(r'\[\d+\]', '[N]', entry)
    return re.sub(r'[ \t]+', ' ', entry).strip(' \t')


def shown(entry):
    return entry.encode('latin-1').decode('utf-8', 'replace')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('old')
    ap.add_argument('new')
    ap.add_argument('--job', action='append', default=[], help='another job name to replace, repeatable')
    a = ap.parse_args()
    jobs = set(a.job) | {os.path.splitext(os.path.basename(p))[0] for p in (a.old, a.new)}
    old = collections.Counter(normalize(e, jobs) for e in entries(a.old))
    new = collections.Counter(normalize(e, jobs) for e in entries(a.new))
    added, removed = new - old, old - new
    print(f'entries: {sum(old.values())} in {a.old}, {sum(new.values())} in {a.new}')
    print(f'only in the new build ({sum(added.values())}):')
    for e, n in sorted(added.items()):
        print(f'  {n}x {shown(e)}')
    print(f'only in the old build ({sum(removed.values())}):')
    for e, n in sorted(removed.items()):
        print(f'  {n}x {shown(e)}')
    sys.exit(1 if added else 0)


if __name__ == '__main__':
    main()

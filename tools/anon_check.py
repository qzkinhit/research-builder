#!/usr/bin/env python3
"""Check a PDF before it goes to a double-blind submission system.

Identity leaks through channels that a reader of the rendered pages does not
see: the document metadata (the Info fields and the XMP stream), the metadata
and file names that pdfTeX copies from every included PDF figure, the targets
of links, the text of figures and footnotes, and fonts that the portal flags
because they are not embedded. A figure exported from an office program carries
the user name of that program in its Author field, and pdfTeX keeps it unless
the preamble sets \\pdfsuppressptexinfo=-1.

This script prints the metadata fields, lists the fonts that are not embedded,
and searches the text, the metadata, the strings of included figures and the
link targets for every string of a names file. Both sides are put in Unicode
NFKC form first, so an accented name typed in the names file matches the base
letter and combining accent that pdftotext writes for the OT1 encoding, and a
ligature matches its letters. Case is ignored, the words of a name may be
separated by any whitespace (pdftotext breaks lines inside names), the
characters of a Chinese, Japanese or Korean name may be separated too, and an
end that is a Latin letter or a digit must not touch another letter or digit,
so a short surname does not match inside a longer word (Hart inside chart).

Each hit in the text is printed with its page and context and marked when it
lies in the reference list, from the last reference heading to the first heading
after it that starts an appendix, a checklist or the acknowledgments. A
self-citation written in the third person is allowed there, and whether it
reveals the authors is for the authors to decide. Headings that the script does
not recognize, for example in a line-numbered review layout, can be given with
--refs-end, and every hit marked as references on the last reference page
deserves a look.

    python tools/anon_check.py paper.pdf --names names.txt
    python tools/anon_check.py paper.pdf --names names.txt --refs-end "PROOFS OF"

names.txt holds one string per line, such as names, e-mail domains,
institutions, grant numbers and repository owners. Lines starting with # are
skipped. Keep the file out of any public repository. Exit status is 1 when the
Author field is set, a name occurs in the metadata, in an included figure, in a
link target that the reference list does not print, or in the text outside the
reference list, or a font is not embedded, and 0 otherwise. Needs poppler
(pdfinfo, pdffonts, pdftotext).
"""
import argparse
import re
import subprocess
import sys
import unicodedata
import zlib

REF_HEADINGS = {'REFERENCES', 'BIBLIOGRAPHY', '参考文献'}
END_HEADINGS = re.compile(r'^(?:APPENDIX.*|APPENDICES|SUPPLEMENTARY.*|.*CHECKLIST|ACKNOWLEDG(?:E)?MENTS?|附录.*|致谢)$')
META_KEYS = rb'/(?:Author|Title|Subject|Keywords|Creator|Producer|PTEX\.FileName)\s*\(((?:[^()\\]|\\.)*)\)'


def nfkc(s):
    return unicodedata.normalize('NFKC', s)


def out(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, errors='replace', check=True).stdout


def metadata(pdf):
    fields = {}
    for line in out(['pdfinfo', pdf]).splitlines():
        if ':' in line:
            k, v = line.split(':', 1)
            fields[k.strip()] = nfkc(v.strip())
    # custom Info keys and the XMP stream, where hyperxmp writes e-mail, copyright and source file name
    for flag, key in (('-custom', 'custom Info keys'), ('-meta', 'XMP')):
        try:
            fields[key] = nfkc(' '.join(out(['pdfinfo', flag, pdf]).split()))
        except subprocess.CalledProcessError:
            pass
    return fields


def unembedded(pdf):
    """Fonts whose emb column is not yes. The last five fields of a row are emb, sub, uni and the
    two numbers of the object ID, so the row is read from the right, which also works for long names."""
    bad = []
    for line in out(['pdffonts', pdf]).splitlines()[2:]:
        parts = line.split()
        if len(parts) >= 6 and parts[-5] != 'yes':
            bad.append(parts[0])
    return bad


def blobs(pdf):
    """The raw file and every stream that inflates. pdfTeX keeps link annotations and the Info
    dictionaries of included figures in compressed object streams, which pdftotext does not read."""
    data = open(pdf, 'rb').read()
    found = [data]
    for m in re.finditer(rb'stream\r?\n', data):
        try:
            found.append(zlib.decompress(data[m.end():data.find(b'endstream', m.end())]))
        except zlib.error:
            pass
    return found


def unescape(b):
    return re.sub(r'\\([()\\])', r'\1', b.decode('latin-1'))


def link_targets(parts):
    return sorted({nfkc(unescape(u)) for b in parts for u in re.findall(rb'/URI\s*\(((?:[^()\\]|\\.)*)\)', b)})


def object_strings(parts):
    """Metadata strings anywhere in the file, including the /PTEX.InfoDict and /PTEX.FileName of figures,
    as literal strings and as UTF-16 hex strings."""
    found = set()
    for b in parts:
        for h in re.findall(rb'<\s*(fe\s*ff[0-9a-fA-F\s]*)>', b, re.I):
            try:
                found.add(bytes.fromhex(re.sub(rb'\s', b'', h).decode()).decode('utf-16-be', 'replace'))
            except ValueError:
                pass
        found |= {unescape(lit) for lit in re.findall(META_KEYS, b)}
    return sorted(nfkc(s) for s in found if s.strip())


def cjk(c):
    return '⺀' <= c <= '鿿' or '가' <= c <= '힯' or '豈' <= c <= '﫿'


def name_pattern(n):
    if any(cjk(c) for c in n):
        body = r'\s*'.join(re.escape(c) for c in n if not c.isspace())
    else:
        body = r'\s+'.join(re.escape(w) for w in n.split())

    def edge(c):
        return '[A-Za-z]' if c.isascii() and c.isalpha() else '[0-9]' if c.isdigit() else None
    left, right = edge(n[0]), edge(n[-1])
    return re.compile((f'(?<!{left})' if left else '') + body + (f'(?!{right})' if right else ''), re.I)


def reference_span(pages, refs_end=''):
    """(page, offset) of the last reference heading and of the first appendix, checklist or
    acknowledgments heading after it. Small caps come out letter-spaced from pdftotext (R EFERENCES),
    so spaces are removed first. A lone A counts as the first appendix heading unless the next line
    starts a numbered reference, as after a broken "Series A." in a reference entry."""
    lines = []
    for i, page in enumerate(pages):
        offset = 0
        for line in page.splitlines(keepends=True):
            lines.append((i, offset, line.replace(' ', '').strip().upper()))
            offset += len(line)
    starts = [k for k, (_, _, key) in enumerate(lines) if key in REF_HEADINGS]
    if not starts:
        return (len(pages), 0), (len(pages), 0)
    k0 = starts[-1]
    stop = refs_end.replace(' ', '').upper()
    for k in range(k0 + 1, len(lines)):
        key = lines[k][2]
        nxt = next((x[2] for x in lines[k + 1:] if x[2]), '')
        if (stop and key.startswith(stop)) or END_HEADINGS.match(key) or \
                (key == 'A' and not re.match(r'\[\d+\]|\d+\.', nxt)):
            return lines[k0][:2], lines[k][:2]
    return lines[k0][:2], (len(pages), 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('pdf')
    ap.add_argument('--names', required=True, help='file with one name, address or number per line')
    ap.add_argument('--refs-end', default='', help='start of the first heading after the reference list')
    a = ap.parse_args()
    names = [nfkc(l.strip()) for l in open(a.names, encoding='utf-8-sig') if l.strip() and not l.startswith('#')]
    pats = {n: name_pattern(n) for n in names}
    fail = False

    meta = metadata(a.pdf)
    print('metadata:')
    for k in ('Title', 'Author', 'Subject', 'Keywords', 'Creator', 'Producer'):
        print(f'  {k:9s} {meta.get(k, "")}')
    if meta.get('Author', '').strip():
        print('  the Author field is set')
        fail = True
    for n, p in pats.items():
        for k, v in meta.items():
            if p.search(v):
                print(f'  "{n}" occurs in {k}')
                fail = True

    bad = unembedded(a.pdf)
    print(f'fonts not embedded ({len(bad)}):')
    for f in bad:
        print('  ' + f)
    fail = fail or bool(bad)

    parts = blobs(a.pdf)
    print('name hits in metadata strings of the file and its included figures:')
    obj_hits = [(n, s) for s in object_strings(parts) for n, p in pats.items() if p.search(s)]
    for n, s in obj_hits:
        print(f'  "{n}" in {s[:120]}')
    if obj_hits:
        print('  set \\pdfsuppressptexinfo=-1 in the preamble, or clean the figure files')
        fail = True
    else:
        print('  none')

    pages = nfkc(out(['pdftotext', a.pdf, '-'])).split('\f')
    start, end = reference_span(pages, a.refs_end)
    print('name hits in the text:')
    hits = 0
    for n, p in pats.items():
        for i, page in enumerate(pages):
            for m in p.finditer(page):
                in_refs = start <= (i, m.start()) < end
                c = ' '.join(page[max(0, m.start() - 50):m.end() + 50].split())
                print(f'  p{i + 1} {"references" if in_refs else "BODY      "} "{n}" ...{c}...')
                hits += 1
                fail = fail or not in_refs
    if not hits:
        print('  none')

    refs = re.sub(r'\s+', '', ''.join(pages[start[0]:end[0] + 1]))
    print('name hits in link targets:')
    link_hits = 0
    for u in link_targets(parts):
        for n, p in pats.items():
            if p.search(u):
                printed = re.sub(r'^https?://', '', u) in refs  # a URL printed in the reference list
                print(f'  {"references" if printed else "LINK      "} "{n}" {u}')
                link_hits += 1
                fail = fail or not printed
    if not link_hits:
        print('  none')
    print('FAIL' if fail else 'PASS')
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Check that a LaTeX source package rebuilds the PDF that goes to the submission system.

Journals that take the LaTeX source next to the PDF compile the package again.
A package rebuilt after a late edit can miss a changed file, keep a stale .bbl,
keep a .bbl named after the old main file, or carry extra entries. This script
unpacks the package into an empty directory, deletes the packaged .bbl, .aux and
PDF of the main file, runs the engine, BibTeX (or Biber) and the engine twice,
and compares the result with the PDF that will be uploaded, page by page, as
extracted text and as rendered pixels.

    python tools/pkg_check.py package.zip en/main.tex submitted.pdf
    python tools/pkg_check.py package.zip main.tex submitted.pdf --engine xelatex --bib biber --dpi 150
    python tools/pkg_check.py package.zip main.tex submitted.pdf --bib none

--bib none keeps the packaged .bbl, for a package that ships the .bbl without
the .bib. The runs do not see TEXINPUTS, BIBINPUTS, BSTINPUTS or the personal
texmf tree, so a style or bibliography file that the package lacks makes the
build fail here as it would at the journal. The engine runs with its default
restricted shell escape. Some templates convert an EPS logo through that
channel, and with shell escape disabled the page shows a placeholder in place
of the logo. The PDF files themselves always differ, because every build writes
its own time stamp, so the comparison is made on text and pixels. Exit status
is 0 when every run exits 0 (or BibTeX exits 1 and its .blg reports warnings
and no error), the page counts, the text and the pixels of every page agree and
the regenerated .bbl equals the packaged one, 1 otherwise.
Needs a TeX installation and poppler (pdftotext, pdftoppm).
"""
import argparse
import collections
import glob
import hashlib
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile


def run(cmd, cwd):
    # a personal texmf tree or an input path would supply files that the package lacks
    env = {k: v for k, v in os.environ.items() if k not in ('TEXINPUTS', 'BIBINPUTS', 'BSTINPUTS')}
    env['TEXMFHOME'] = os.path.join(cwd, '.no-texmfhome')
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, errors='replace', timeout=900)
    return r.returncode


def warnings_only(blg):
    """Some BibTeX builds exit 1 when there were warnings and no errors, which the .blg states."""
    if not os.path.exists(blg):
        return False
    log = open(blg, encoding='latin-1').read()
    return bool(re.search(r'\(There (was 1 warning|were \d+ warnings)\)', log)) and 'error message' not in log


def page_texts(pdf):
    out = subprocess.run(['pdftotext', pdf, '-'], capture_output=True, text=True,
                         errors='replace', check=True).stdout.split('\f')
    return out[:-1] if out and not out[-1].strip() else out


def page_hashes(pdf, dpi, workdir):
    d = tempfile.mkdtemp(dir=workdir)
    subprocess.run(['pdftoppm', '-r', str(dpi), '-gray', pdf, os.path.join(d, 'p')], check=True)
    files = sorted(glob.glob(os.path.join(d, 'p-*.pgm')),
                   key=lambda f: int(re.search(r'-(\d+)\.pgm$', f).group(1)))
    return [hashlib.md5(open(f, 'rb').read()).hexdigest() for f in files]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('package', help='the .zip that will be uploaded')
    ap.add_argument('main', help='path of the main .tex inside the package')
    ap.add_argument('pdf', help='the PDF that will be uploaded')
    ap.add_argument('--engine', default='pdflatex')
    ap.add_argument('--bib', default='bibtex', choices=['bibtex', 'biber', 'none'])
    ap.add_argument('--dpi', type=int, default=150)
    ap.add_argument('--keep', action='store_true', help='keep the build directory and print its path')
    a = ap.parse_args()

    ok = True
    tmp = tempfile.mkdtemp(prefix='pkg_check-')
    src = os.path.join(tmp, 'src')
    job = os.path.splitext(os.path.basename(a.main))[0]
    want_bbl = posixpath.join(posixpath.dirname(a.main), job + '.bbl')
    with zipfile.ZipFile(a.package) as z:
        names = z.namelist()
        dirs = [n for n in names if n.endswith('/')]
        dups = [n for n, c in collections.Counter(names).items() if c > 1]
        print(f'{len(names)} entries, {len(dirs)} directory entries, {len(dups)} duplicate names')
        for n in dups:
            print(f'  duplicate: {n}')
            ok = False
        if a.main not in names:
            print(f'main file {a.main} is not in the package')
            sys.exit(1)
        stray = [n for n in names if n.endswith('.bbl') and n != want_bbl]
        if want_bbl not in names and stray:
            print(f'no {want_bbl} in the package but {stray}, name the .bbl after the main file')
            ok = False
        z.extractall(src)

    main_dir = os.path.join(src, os.path.dirname(a.main))
    bbl = os.path.join(main_dir, job + '.bbl')
    packaged_bbl = open(bbl, 'rb').read() if os.path.exists(bbl) else None
    removed = []
    for ext in (['.pdf', '.aux'] + (['.bbl'] if a.bib != 'none' else [])):
        f = os.path.join(main_dir, job + ext)
        if os.path.exists(f):  # a packaged PDF or .aux would stand in for a build that fails
            os.remove(f)
            removed.append(job + ext)
    if removed:
        print('removed before the build:', ', '.join(removed))

    steps = [[a.engine, '-interaction=nonstopmode', job]]
    if a.bib != 'none':
        steps.append([a.bib, job])
    steps += [[a.engine, '-interaction=nonstopmode', job]] * 2
    for cmd in steps:
        code = run(cmd, main_dir)
        if cmd[0] == 'bibtex' and code == 1 and warnings_only(os.path.join(main_dir, job + '.blg')):
            print(f'{" ".join(cmd)} -> exit 1, warnings only')
            continue
        print(f'{" ".join(cmd)} -> exit {code}')
        if code != 0:
            ok = False

    built = os.path.join(main_dir, job + '.pdf')
    if not os.path.exists(built):
        print('no PDF was produced, see the log in', main_dir)
        sys.exit(1)
    if a.bib == 'none':
        print('--bib none, the packaged .bbl is used as it is' if packaged_bbl is not None
              else '--bib none and the package has no .bbl')
    elif packaged_bbl is None:
        print('the package has no .bbl, the journal has to run the bibliography tool itself')
    elif not os.path.exists(bbl):
        print('no .bbl was regenerated')
        ok = False
    elif open(bbl, 'rb').read() == packaged_bbl:
        print('regenerated .bbl is byte-identical to the packaged one')
    else:
        print('regenerated .bbl differs from the packaged one')
        ok = False

    ta, tb = page_texts(built), page_texts(a.pdf)
    ha, hb = page_hashes(built, a.dpi, tmp), page_hashes(a.pdf, a.dpi, tmp)
    print(f'pages: rebuilt {len(ha)}, submitted {len(hb)}')
    if len(ha) != len(hb):
        ok = False
    text_diff = [i + 1 for i in range(min(len(ta), len(tb))) if ta[i] != tb[i]]
    pix_diff = [i + 1 for i in range(min(len(ha), len(hb))) if ha[i] != hb[i]]
    print('text differs on pages', text_diff if text_diff else 'none')
    print(f'pixels at {a.dpi} dpi differ on pages', pix_diff if pix_diff else 'none')
    ok = ok and not text_diff and not pix_diff

    if a.keep:
        print('build directory kept at', tmp)
    else:
        shutil.rmtree(tmp, ignore_errors=True)
    print('PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()

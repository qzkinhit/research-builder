#!/usr/bin/env python3
"""Count the words of a LaTeX abstract the way the rendered PDF shows them.

Abstracts often carry number macros (\\nDatasets{}, \\gainBest{}) whose values
change at backfill, so counting the source undercounts or overcounts. The script
expands every zero- and one-argument \\newcommand defined in the same file,
drops the remaining commands and math markers, and counts whitespace-separated
tokens. Check the count against the venue limit after every backfill and every
edit to the abstract, an edit that shortens one sentence is often made to meet
the limit, and undoing it silently breaks the limit again.

    python tools/abstract_words.py main.tex --limit 250

Submission systems take the abstract as plain text, and the text pasted there
drifts from the PDF when the abstract is edited late. --plain prints the expanded
abstract as plain text for pasting, and --compare checks it word by word against
the text that is already in the system.

    python tools/abstract_words.py main.tex --plain > abstract.txt
    python tools/abstract_words.py main.tex --compare submitted_abstract.txt
"""
import argparse
import difflib
import re
import sys


def macros(src):
    defs = {}
    for m in re.finditer(r'\\(?:re)?newcommand\{?\\([A-Za-z]+)\}?(\[(\d)\])?\{', src):
        i, depth = m.end(), 1
        while i < len(src) and depth:
            depth += {'{': 1, '}': -1}.get(src[i], 0)
            i += 1
        defs[m.group(1)] = (int(m.group(3) or 0), src[m.end():i - 1])
    return defs


def expand(text, defs, rounds=5):
    for _ in range(rounds):
        before = text
        for name, (nargs, body) in defs.items():
            if nargs == 0:
                text = re.sub(r'\\' + name + r'(?![A-Za-z])(\{\})?', lambda _m: body, text)
            elif nargs == 1:
                text = re.sub(r'\\' + name + r'\{([^{}]*)\}', lambda m: body.replace('#1', m.group(1)), text)
        if text == before:
            break
    return text


MATH_WORDS = {'ln': 'ln', 'log': 'log', 'exp': 'exp', 'min': 'min', 'max': 'max', 'times': 'x', 'cdot': '*',
              'le': '<=', 'leq': '<=', 'ge': '>=', 'geq': '>=', 'approx': '~', 'pm': '+/-'}


def plain(text):
    """The abstract as a submission system shows it: commands dropped, math kept as words."""
    text = re.sub(r'\\[A-Za-z]+\s*=\s*-?[\d.]+(pt|em)?', ' ', text)          # \looseness=-1 and similar
    text = re.sub(r'\\[td]?frac\{([^{}]*)\}\{([^{}]*)\}', r'(\1)/(\2)', text)
    text = re.sub(r'\\([A-Za-z]+)', lambda m: ' ' + MATH_WORDS[m.group(1)] + ' ' if m.group(1) in MATH_WORDS
                  else ' ', text)
    text = text.replace('\\%', '%').replace('\\&', '&').replace('~', ' ').replace('--', '-')
    text = re.sub(r'[{}$\\]', '', text)
    text = re.sub(r'\s+([,.;:%)])', r'\1', ' '.join(text.split()))
    return re.sub(r'\(\s+', '(', text)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('tex')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--plain', action='store_true', help='print the abstract as plain text for a submission system')
    ap.add_argument('--compare', default='', help='plain-text file to compare the abstract against, word by word')
    a = ap.parse_args()
    src = open(a.tex, encoding='utf-8').read()
    m = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', src, re.S)
    if not m:
        sys.exit('no abstract environment found')
    text = re.sub(r'(?<!\\)%.*', '', m.group(1))
    text = expand(text, macros(src))
    text = re.sub(r'\\(cite|ref|label)\{[^}]*\}', '', text)
    if a.plain or a.compare:
        flat = plain(text)
        if a.plain:
            print(flat)
        if a.compare:
            old = ' '.join(open(a.compare, encoding='utf-8').read().split())
            if old == flat:
                print(f'identical to {a.compare} ({len(flat.split())} words)')
            else:
                diff = [d for d in difflib.ndiff(old.split(), flat.split()) if d[0] in '+-']
                print(f'differs from {a.compare}: {len(old.split())} -> {len(flat.split())} words')
                print(' '.join(diff[:60]))
                sys.exit(1)
        return
    text = re.sub(r'\\[A-Za-z]+\*?', ' ', text)
    text = re.sub(r'[{}$~]', ' ', text)
    n = len(text.split())
    status = '' if not a.limit else (' within the limit' if n <= a.limit else f' OVER the limit of {a.limit}')
    print(f'{n} words{status}')
    sys.exit(1 if a.limit and n > a.limit else 0)


if __name__ == '__main__':
    main()

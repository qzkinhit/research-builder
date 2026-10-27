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
"""
import argparse
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


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('tex')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    src = open(a.tex, encoding='utf-8').read()
    m = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', src, re.S)
    if not m:
        sys.exit('no abstract environment found')
    text = re.sub(r'(?<!\\)%.*', '', m.group(1))
    text = expand(text, macros(src))
    text = re.sub(r'\\(cite|ref|label)\{[^}]*\}', '', text)
    text = re.sub(r'\\[A-Za-z]+\*?', ' ', text)
    text = re.sub(r'[{}$~]', ' ', text)
    n = len(text.split())
    status = '' if not a.limit else (' within the limit' if n <= a.limit else f' OVER the limit of {a.limit}')
    print(f'{n} words{status}')
    sys.exit(1 if a.limit and n > a.limit else 0)


if __name__ == '__main__':
    main()

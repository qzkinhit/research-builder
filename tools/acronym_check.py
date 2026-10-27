#!/usr/bin/env python3
"""List the acronyms of a LaTeX paper that a reader outside the subfield cannot resolve.

A broad reader stops at the first unexplained acronym. The check collects every
token with an all-capital part or a digit (XGB, BERT-base, F1, k-NN), and looks
for a gloss or a citation at any of its occurrences. A gloss is "long name (ACR)"
or "ACR (long name)", with \\textbf, \\emph and \\textsc wrappers removed first.

Two lists come out:
  never   no occurrence is glossed or cited. Fix these, in a caption when the
          acronym sits in a table or figure, since captions are read alone.
  later   glossed or cited, but not where it first appears. Often a table or
          figure that floats ahead of the definition. Gloss it in that caption
          or accept it knowingly.

    python tools/acronym_check.py main.tex
    python tools/acronym_check.py main.tex --known known_acronyms.txt

known_acronyms.txt lists acronyms that need no gloss for the venue, one per line.
Dataset and model names show up too, decide for each one whether the reader
needs a citation or a gloss.
"""
import argparse
import re

ENV = re.compile(r'\\begin\{(equation|align|gather|multline|eqnarray|displaymath|algorithmic)\*?\}.*?'
                 r'\\end\{\1\*?\}', re.S)
CMD_ARG = re.compile(r'\\(label|ref|eqref|autoref|cref|url|href|includegraphics|input|include|title|author|'
                     r'begin|end|bibliographystyle|bibliography|externaldocument|usepackage|bstctlcite)\*?'
                     r'(\[[^\]]*\])?\{[^}]*\}')
TOKEN = re.compile(r'(?<![\\A-Za-z0-9-])([A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*)(?![A-Za-z0-9])')


def body_text(path):
    s = open(path, encoding='utf-8').read()
    s = re.sub(r'(?<!\\)%.*', '', s)
    if '\\begin{document}' in s:
        s = s[s.index('\\begin{document}') + len('\\begin{document}'):]
    m = re.search(r'\\bibliography\{|\\begin\{thebibliography\}|\\printbibliography', s)
    if m:
        s = s[:m.start()]
    s = ENV.sub(' ', s)
    s = s.replace('\\$', ' ')  # an escaped dollar sign is text, not a math delimiter
    # a lone \[ opens display math, \\[2pt] in a table is a line break
    s = re.sub(r'(?<!\\)\\\[.*?(?<!\\)\\\]|\$\$.*?\$\$|\$[^$]*\$', ' ', s, flags=re.S)
    for _ in range(2):
        s = re.sub(r'\\(textsc|textbf|emph|textit|texttt|mbox)\{([^{}]*)\}', r'\2', s)
    s = re.sub(r'~?\\cite[pt]?\*?(\[[^\]]*\])?\{[^}]*\}', ' CITE ', s)
    return CMD_ARG.sub(' ', s)


def core(token):
    """The acronym parts of a token: all-capital parts of two or more letters, or parts with a digit."""
    return [p for p in token.split('-')
            if (sum(c.isupper() for c in p) >= 2 and p.upper() == p) or
               (re.search(r'\d', p) and re.search(r'[A-Z]', p)) or
               sum(c.isupper() for c in p) >= 2 and not p.istitle()]


def glossed(text, pos, t):
    near = text[max(0, pos - 12):pos + len(t) + 60]
    esc = re.escape(t)
    return bool(re.search(r'\(\s*' + esc + r'\s*[),]', near)
                or re.match(esc + r'\s*\(', text[pos:pos + len(t) + 3])
                or 'CITE' in text[pos:pos + len(t) + 40])


def ctx(text, pos, t):
    return ' '.join(text[max(0, pos - 70):pos + len(t) + 50].split())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('tex')
    ap.add_argument('--known', help='file of acronyms that need no gloss')
    a = ap.parse_args()
    known = {'AI', 'ML', 'GPU', 'CPU', 'PDF', 'URL', 'API', 'IEEE', 'ACM', 'CITE', 'NP', 'II', 'III', 'IV'}
    if a.known:
        known |= {l.strip() for l in open(a.known, encoding='utf-8') if l.strip()}

    text = body_text(a.tex)
    occ = {}
    for m in TOKEN.finditer(text):
        t = m.group(1)
        parts = core(t)
        if not parts or all(p in known for p in parts):
            continue
        occ.setdefault(t, []).append(m.start())

    resolved = {t for t, ps in occ.items() if any(glossed(text, p, t) for p in ps)}
    never, later = [], []
    for t, positions in sorted(occ.items(), key=lambda kv: kv[1][0]):
        if '-' in t and all(p in resolved or p in known for p in core(t)):
            continue  # LLM-based, SVM-style: built from acronyms glossed elsewhere
        ok = [p for p in positions if glossed(text, p, t)]
        if not ok:
            never.append((t, ctx(text, positions[0], t)))
        elif ok[0] != positions[0]:
            later.append((t, ctx(text, positions[0], t)))
    print(f'never glossed or cited ({len(never)}):')
    for t, c in never:
        print(f'  {t:16s} ...{c}...')
    print(f'glossed or cited only after first use ({len(later)}):')
    for t, c in later:
        print(f'  {t:16s} ...{c}...')


if __name__ == '__main__':
    main()

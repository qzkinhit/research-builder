#!/usr/bin/env python3
"""List the acronyms of a LaTeX paper that a reader outside the subfield cannot resolve.

A broad reader stops at the first unexplained acronym. The check collects every
token with an all-capital part or a digit (XGB, BERT-base, F1, k-NN), and looks
for a gloss or a citation at any of its occurrences. A gloss is "long name (ACR)"
or "ACR (long name)", with \\textbf, \\emph and \\textsc wrappers removed first.
Files pulled in with \\input and \\include are read, and zero- and one-argument
macros defined with \\newcommand, \\renewcommand, \\providecommand,
\\DeclareRobustCommand or a parameterless \\def are expanded before the scan, so a
system or step name written as a macro (\\sys, \\stepname) is checked too. The
system name of a "Name: subtitle" title counts as known when the part before
the colon is a single word.

Three lists come out:
  never   no occurrence is glossed or cited. Fix these, in a caption when the
          acronym sits in a table or figure, since captions are read alone.
  later   glossed or cited, but not where it first appears. Often a table or
          figure that floats ahead of the definition. Gloss it in that caption
          or accept it knowingly.
  twice   defined as "long name (ACR)" at two or more places of the body. A
          contribution list often repeats the definition right after a bold
          run-in title that names the same step. Keep the first definition and
          use the bare acronym afterwards. The abstract, captions, tables and
          figures are not counted, because IEEE asks for the definition again at
          the first use in the body even after the abstract, and captions and
          tables are read on their own. A parenthesis counts as a definition only
          when the acronym has two or more capitals and more than half of them
          start words just before it, so a label such as "(C1)" or a reference
          such as "Under (P1) to (P3)" is not listed.

    python tools/acronym_check.py main.tex
    python tools/acronym_check.py main.tex --known known_acronyms.txt

known_acronyms.txt lists acronyms that need no gloss for the venue, one per line.
Dataset and model names show up too, decide for each one whether the reader
needs a citation or a gloss.
"""
import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from abstract_words import expand, macros  # noqa: E402  the same macro expansion as the word count

ENV = re.compile(r'\\begin\{(equation|align|gather|multline|eqnarray|displaymath|algorithmic)\*?\}.*?'
                 r'\\end\{\1\*?\}', re.S)
CMD_ARG = re.compile(r'\\(label|ref|eqref|autoref|cref|url|href|includegraphics|input|include|title|author|'
                     r'cellcolor|rowcolor|columncolor|color|'
                     r'begin|end|bibliographystyle|bibliography|externaldocument|usepackage|bstctlcite)\*?'
                     r'(\[[^\]]*\])?\{[^}]*\}')
TOKEN = re.compile(r'(?<![\\A-Za-z0-9-])([0-9]*[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*)(?![A-Za-z0-9])')
OPEN, CLOSE = '\x1e', '\x1f'  # whitespace characters that mark the abstract, tables and figures


def read_tex(path, root=None, depth=0):
    """The file with comments removed and \\input and \\include inlined, paths taken from the main file's directory."""
    root = root or os.path.dirname(os.path.abspath(path))
    s = re.sub(r'(?<!\\)%.*', '', open(path, encoding='utf-8', errors='replace').read())

    def inline(m):
        f = os.path.join(root, (m.group(1) or m.group(2)).strip())
        for cand in (f + '.tex', f):  # LaTeX tries name.tex first, then the name as given
            if depth < 10 and os.path.isfile(cand):
                return read_tex(cand, root, depth + 1)
        return m.group(0)
    return re.sub(r'\\(?:input|include)\s*\{([^}]*)\}|\\input\s+([^\s{}\\%]+)', inline, s)


def body_text(src):
    defs = macros(src)  # system and step names are often macros, \sys or \stepname
    s = src
    if '\\begin{document}' in s:
        s = s[s.index('\\begin{document}') + len('\\begin{document}'):]
    s = re.sub(r'\\captionof\*?\{[^}]*\}', r'\\caption', s)  # \captionof{table}{...} is a caption too
    s = re.sub(r'(\\[A-Za-z]+)(?=\\[A-Za-z])', r'\1 ', s)  # \fi\sys would swallow the expanded name
    s = expand(s, defs).replace('\\xspace', '')
    m = re.search(r'\\bibliography\{|\\begin\{thebibliography\}|\\printbibliography', s)
    if m:
        s = s[:m.start()]
    m = re.search(r'\\abstract(\[[^\]]*\])?\{', s)  # Springer and Wiley templates write \abstract{...}
    if m:
        i, depth = m.end(), 1
        while i < len(s) and depth:
            depth += {'{': 1, '}': -1}.get(s[i], 0)
            i += 1
        s = s[:m.start()] + f' {OPEN} ' + s[m.end():i - 1] + f' {CLOSE} ' + s[i:]
    s = re.sub(r'\\begin\{(abstract|table|figure)\*?\}', f' {OPEN} ', s)
    s = re.sub(r'\\end\{(abstract|table|figure)\*?\}', f' {CLOSE} ', s)
    s = ENV.sub(' ', s)
    s = s.replace('\\$', ' ')  # an escaped dollar sign is text, not a math delimiter
    # a lone \[ opens display math, \\[2pt] in a table is a line break
    s = re.sub(r'(?<!\\)\\\[.*?(?<!\\)\\\]|\$\$.*?\$\$|\$[^$]*\$', ' ', s, flags=re.S)
    for _ in range(6):  # nested wrappers such as \textbf{\textup{\textsc{...}}} after macro expansion
        before = s
        # the space keeps a preceding control word (\fi\textbf{...}) from swallowing the text
        s = re.sub(r'\\(textsc|textbf|textup|emph|textit|texttt|mbox)\{([^{}]*)\}', r' \2', s)
        if s == before:
            break
    s = re.sub(r'~?\\cite[pt]?\*?(\[[^\]]*\])?\{[^}]*\}', ' CITE ', s)
    s = re.sub(r'\\href\{[^}]*\}\{[^}]*\}|\\textcolor(\[[^\]]*\])?\{[^}]*\}', ' ', s)  # link text, color names
    return CMD_ARG.sub(' ', s)


def core(token):
    """The acronym parts of a token: all-capital parts of two or more letters, or parts with a digit."""
    return [p for p in token.split('-')
            if not re.fullmatch(r'\d+[A-Z]{1,2}', p) and  # 3D, 7B, 24GB are sizes, not acronyms
               ((sum(c.isupper() for c in p) >= 2 and p.upper() == p) or
                (re.search(r'\d', p) and re.search(r'[A-Z]', p)) or
                (sum(c.isupper() for c in p) >= 2 and not p.istitle()))]


def glossed(text, pos, t):
    near = text[max(0, pos - 12):pos + len(t) + 60]
    esc = re.escape(t)
    sentence = re.split(r'\.\s|\n\s*\n', text[pos:pos + 250])[0]  # a citation later in the same sentence
    return bool(re.search(r'\(\s*' + esc + r'\s*[),]', near)
                or re.match(esc + r'\s*\(', text[pos:pos + len(t) + 3])
                or 'CITE' in sentence)


def defines(text, pos, t):
    """True for the "(ACR)" of "long name (ACR)". The acronym stands alone in parentheses, has two or more
    capitals, and more than half of its capitals start words just before the parenthesis. A label with one
    capital (C1, P3) is referred to in parentheses, and "recall over all baselines (RQ1)" fails the test."""
    if not (re.search(r'\(\s*$', text[max(0, pos - 4):pos]) and re.match(r'\s*\)', text[pos + len(t):pos + len(t) + 4])):
        return False
    letters = {c.lower() for c in t if c.isupper()}
    if len([c for c in t if c.isupper()]) < 2:
        return False
    before = text[max(0, pos - 200):pos]
    before = re.sub(r'\([^()]*\)', ' ', before[:before.rfind('(')])  # in "(P1) to (P3)" the P1 is no initial
    if re.search(r'([.:;]|\\item(\[[^\]]*\])?)\s*$', before):
        return False  # a parenthesis after a full stop or an \item labels a statement
    initials = {w[0].lower() for w in re.findall(r'[A-Za-z0-9]+', before)[-max(4, len(letters) + 2):]}
    return len(letters & initials) > len(letters) / 2


def in_caption(text, pos):
    start = text.rfind('\\caption', 0, pos)
    if start < 0:
        return False
    brace = text.find('{', start)
    if brace < 0 or brace > pos:
        return False
    depth = 0
    for ch in text[brace:pos]:
        depth += {'{': 1, '}': -1}.get(ch, 0)
        if depth == 0:
            return False
    return depth > 0


def in_float_or_abstract(text, pos):
    return text.rfind(OPEN, 0, pos) > text.rfind(CLOSE, 0, pos)


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

    src = read_tex(a.tex)
    title_names = set()
    m = re.search(r'\\title(\[[^\]]*\])?\{', src)
    if m:  # the system name of a "Name: subtitle" title is defined by the title itself
        i, depth = m.end(), 1
        while i < len(src) and depth:
            depth += {'{': 1, '}': -1}.get(src[i], 0)
            i += 1
        title = expand(src[m.end():i - 1], macros(src))
        head = re.split(r'[:：]', title)[0] if re.search(r'[:：]', title) else ''
        head_tokens = TOKEN.findall(re.sub(r'\\[A-Za-z]+', ' ', head))
        title_names = set(head_tokens) if len(head_tokens) == 1 else set()
    text = body_text(src)
    occ = {}
    for m in TOKEN.finditer(text):
        t = m.group(1)
        parts = core(t)
        if not parts or t in title_names or all(p in known or p in title_names for p in parts):
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
    twice = []
    for t, positions in sorted(occ.items(), key=lambda kv: kv[1][0]):
        spots = [p for p in positions if defines(text, p, t) and not in_caption(text, p)
                 and not in_float_or_abstract(text, p)]
        if len(spots) > 1:
            twice.append((t, [ctx(text, p, t) for p in spots]))
    print(f'twice, defined more than once in the body ({len(twice)}):')
    for t, cs in twice:
        for c in cs:
            print(f'  {t:16s} ...{c}...')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""LaTeX 投稿前审计(纯标准库)。零红项才算过,任何红项 exit 1。

  python audit_tex.py main.tex [appendix.tex ...] [banned_words.txt]

查九样:禁词(默认表+项目自定义,大小写不敏感,英文按整词匹配,词表支持 # 注释行)、
writing-deai.md 的强痕迹(模式表与 polish_check.py 共用)、正文里的破折号分号花引号、$ 配对、
花括号平衡、环境 begin/end 配平(含孤儿 \\end)、ref/pageref/eqref/autoref/
cref 全有对应 \\label 且 label 不重复、Finding/RQ 编号带空格且跨文件连续、
标题里的中文"发现k"带空格。弱痕迹只提示不计入失败,加 --no-hints 不打印。
查标点与痕迹前先屏蔽数学环境、TikZ、\\cite/\\ref/\\label/\\url 的参数,
数值范围 1--5 与 (a--e) 不算破折号,LaTeX 的 ``...'' 不算花引号。
扫描前先掩掉 verbatim/lstlisting/minted 环境与 \\verb,再剥 % 注释(保留 \\%,
表格换行 \\\\ 后的 % 仍按注释剥)。多个 tex 一起传时 label 与 Finding 编号
跨文件汇总,正文引附录不误报;正文附录分开传会漏跨文件核验,一起传。
默认禁词表只含通用的 AI 词、工程词与行话(writing-playbook.md 第 5 节),项目自己的
禁词一行一词写进 banned_words.txt 传入。禁词只管论文行文,代码与仓库文档不受限。
数字对账与句式规则脚本查不了,人工过 writing-playbook.md 第 4、5 节。
"""
import os, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import polish_check as pc  # noqa: E402  共用 writing-deai.md 的模式表

DEFAULT_BANNED = ["delve", "delving", "crucially", "notably", "leverage", "leveraging", "It is worth noting",
    "pipeline", "hyperparameter", "snapshot", "manifest",
    "re-implemented", "re-executed", "winner's-curse",
    "闭环", "门控", "闸门", "赋能", "落地", "快照", "重跑"]

HEAD_CMDS = r'\\(?:section|subsection|subsubsection|paragraph|subparagraph)\*?\{([^}]*)'


def banned_hit(term, low):
    # 英文词按整词匹配(允许 s/es/d/ed 词尾),避免 manifest 命中 manifestations;中文词按子串匹配
    t = term.lower()
    if re.fullmatch(r"[a-z][a-z' -]*", t):
        return re.search(r"(?<![a-z])" + re.escape(t) + r"(?:s|es|d|ed)?(?![a-z])", low) is not None
    return t in low


def mask_verbatim(s):
    s = re.sub(r'\\begin\{(verbatim\*?|lstlisting|minted)\}.*?\\end\{\1\}', '', s, flags=re.S)
    return re.sub(r'\\verb\*?(.)(.*?)\1', '', s)


def strip_comments(s):
    # 偶数个反斜杠之后的 % 才是注释起点: \% 是字面百分号, \\% 是表格换行后跟注释
    return '\n'.join(re.sub(r'((?:^|[^\\])(?:\\\\)*)%.*', r'\1', ln) for ln in s.split('\n'))


def load(path):
    return strip_comments(mask_verbatim(open(path, encoding="utf-8").read()))


MATH_ENVS = r"(?:equation|align|gather|multline|eqnarray|math|displaymath|tikzpicture|lstlisting|minted)\*?"


def prose_of(s):
    """正文文字:去掉导言、数学、TikZ 和引用类命令的参数,用于查标点与痕迹。"""
    if "\\begin{document}" in s:
        s = s.split("\\begin{document}", 1)[1]
    s = re.sub(r"\\begin\{(" + MATH_ENVS + r")\}.*?\\end\{\1\}", " ", s, flags=re.S)
    s = re.sub(r"\\\[.*?\\\]|\\\(.*?\\\)", " ", s, flags=re.S)
    s = re.sub(r"(?<!\\)\$\$.*?(?<!\\)\$\$|(?<!\\)\$.*?(?<!\\)\$", " ", s, flags=re.S)
    s = re.sub(r"\\(?:cite[tp]?|ref|eqref|autoref|cref|Cref|pageref|label|url|href|input|include|"
               r"includegraphics|bibliography|bibliographystyle|num|setnum|usepackage)\*?(?:\[[^\]]*\])?\{[^}]*\}",
               " ", s)
    return s.replace("\\;", " ").replace("\\,", " ")


def punct_view(prose):
    """查标点用的文字:再去掉算法伪代码和表格里表示空格子的横杠,这两处的分号与横杠是允许的。"""
    prose = re.sub(r"\\begin\{algorithmic\}.*?\\end\{algorithmic\}", " ", prose, flags=re.S)
    return re.sub(r"(?:(?<=&)|^)\s*-{1,3}\s*(?=&|\\\\|$)", " ", prose, flags=re.M)


def style(prose):
    """返回 (红线, 提示),规则见 writing-deai.md。"""
    red, hint = [], []
    for name, pat in (("8 破折号", r"---|——|—|–|(?<=\w) -- (?=\w)"), ("硬禁令 分号", r"[;；]"),
                      ("21 花引号", r"[“”‘’]")):
        hits = re.findall(pat, punct_view(prose))
        if hits:
            red.append(f"{name}: {len(hits)}")
    for name, pat in pc.STRONG.items():
        hits = [m.group(0) for m in re.finditer(pat, prose)]
        if hits:
            red.append(f"{name}: {hits[:3]}")
    for ph in pc.ZH_META:
        if ph in prose:
            red.append(f"4 元话术: {ph}")
    for w, sug in pc.WEIRD.items():
        if w in prose:
            red.append(f"29 生硬词: {w} -> {sug}")
    for para in pc.paragraphs(prose):
        low = para.lower()
        found = sorted({w for w in pc.WEAK_WORDS if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", low)})
        if len(found) >= 3:
            red.append(f"12 弱 AI 词成群: {found}")
    for name, pat in pc.HINTS.items():
        if name in ("说明性冒号", "斜杠除法"):
            continue
        hits = [m.group(0) for m in re.finditer(pat, prose)]
        if hits:
            hint.append(f"{name}: {len(hits)} {hits[:3]}")
    return red, hint


def audit(path, s, banned, all_labels, show_hints=True):
    low = s.lower()
    red = []
    hits = [t for t in banned if banned_hit(t, low)]
    if hits:
        red.append(f"banned terms present: {hits}")
    style_red, style_hint = style(prose_of(s))
    red += style_red
    esc = len(re.findall(r'(?<!\\)\\\$', s))
    if (s.count('$') - esc) % 2:
        red.append("odd number of $ delimiters")
    if s.count('{') != s.count('}'):
        red.append(f"brace imbalance: {s.count('{') - s.count('}')}")
    for e in set(re.findall(r'\\(?:begin|end)\{([a-zA-Z*]+)\}', s)):
        b = len(re.findall(r'\\begin\{' + re.escape(e) + r'\}', s))
        en = len(re.findall(r'\\end\{' + re.escape(e) + r'\}', s))
        if b != en:
            red.append(f"env {e}: begin {b} vs end {en}")
    raw_refs = re.findall(r'\\(?:page|auto|eq|name|c|C)?ref\{([^}]+)\}', s)
    refs = {r.strip() for grp in raw_refs for r in grp.split(',')}
    if refs - all_labels:
        red.append(f"unresolved refs: {sorted(refs - all_labels)}")
    for m in re.finditer(r'(?:Finding|RQ)\d', s):
        red.append(f"missing space in heading near: {m.group(0)}")
    for h in re.findall(HEAD_CMDS, s):
        for m in re.finditer(r'发现\d', h):
            red.append(f"missing space in heading near: {m.group(0)} (标题: {h[:30]})")
    if show_hints and style_hint:
        print(f"[HINT] {path} (人工判断,不计入失败)")
        for h in style_hint:
            print("  -", h)
    if red:
        print(f"[FAIL] {path}")
        for r in red:
            print("  -", r)
        return 1
    print(f"[OK] {path}: banned=0, style red lines=0, $ paired, braces balanced, envs balanced, refs closed")
    return 0


if __name__ == "__main__":
    show_hints = "--no-hints" not in sys.argv
    args = [a for a in sys.argv[1:] if a != "--no-hints"]
    texs = list(dict.fromkeys(a for a in args if a.endswith(".tex")))
    words = [a for a in args if not a.endswith(".tex")]
    if not texs:
        sys.exit("usage: audit_tex.py main.tex [appendix.tex ...] [banned_words.txt] [--no-hints]")
    banned = DEFAULT_BANNED[:]
    for w in words:
        if not os.path.isfile(w):
            sys.exit(f"词表文件不存在: {w} (tex 文件须以 .tex 结尾,词表一行一词)")
        banned += [l.strip() for l in open(w, encoding="utf-8")
                   if l.strip() and not l.lstrip().startswith("#")]
    print(f"审计 {len(texs)} 个 tex, 加载 {len(words)} 个自定义词表, 禁词 {len(banned)} 条")
    texts = {t: load(t) for t in texs}
    code = 0
    labels = []
    for s in texts.values():
        labels += re.findall(r'\\label\{([^}]+)\}', s)
    dups = sorted({l for l in labels if labels.count(l) > 1})
    if dups:
        print(f"[FAIL] duplicate labels across files: {dups}")
        code = 1
    for prefix in ("Finding", "RQ"):
        nums = sorted({int(n) for s in texts.values() for n in re.findall(prefix + r'\s+(\d+)', s)})
        if nums and nums != list(range(1, nums[-1] + 1)):
            print(f"[FAIL] {prefix} numbering not contiguous from 1: {nums} (正文附录要一起传)")
            code = 1
    for t in texs:
        code = max(code, audit(t, texts[t], banned, set(labels), show_hints))
    sys.exit(code)

#!/usr/bin/env python3
"""润色自检。扫 .docx / .pptx / .md / .txt 里的 AI 腔痕迹，中英文都查，润色后应当零红线。

红线(计入失败，退出码 1)
  硬禁令      破折号、分号、花引号、emoji (writing-deai.md 第 2 节)
  强痕迹      膨胀反转、单句收尾套话、故作深刻、铺垫与元话术、和不存在的人争论、
              夸大意义、聊天客套、知识边界声明、拟人、高频 AI 词、生硬词与口语比喻词
  弱词成群    同一段出现 3 个以上不同的弱 AI 词
提示(不计入失败，人工判断)
  X rather than Y、「不是 A 而是 B」、叠加限定、含糊关联、-ing 尾巴、推销语、借来的权威、
  回避「是」「有」、写文档本身、名词后的连字符、单句段落、连续同一句首、加粗标签列表、
  标题每词大写、说明性冒号、斜杠除法

编号对应 writing-deai.md 第 4 节的模式编号。.tex 的结构与禁词审计用 audit_tex.py。

  python polish_check.py <file> [--max-examples 3]
"""
import argparse
import html
import re
import sys
import zipfile
from collections import defaultdict

# ---------------------------------------------------------------- text extraction


def text_of(path):
    """Return the text with one paragraph per block separated by blank lines."""
    if path.endswith(".docx"):
        xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8", "ignore")
        # 只取正文 w:t 文本，排除 m:t 数学公式(公式里的分号是数学记号)
        paras = ["".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)) for p in xml.split("</w:p>")]
        return html.unescape("\n\n".join(p for p in paras if p.strip()))
    if path.endswith(".pptx"):
        z = zipfile.ZipFile(path)
        out = []
        names = sorted((n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                       key=lambda n: int(re.findall(r"\d+", n)[-1]))
        for n in names:
            raw = z.read(n).decode("utf-8", "ignore")
            for p in raw.split("</a:p>"):
                t = html.unescape("".join(re.findall(r"<a:t>([^<]*)</a:t>", p)))
                if t.strip():
                    out.append(t)
        return "\n\n".join(out)
    s = open(path, encoding="utf-8", errors="ignore").read()
    if path.endswith(".md"):
        s = re.sub(r"```.*?```", "", s, flags=re.S)        # fenced code
        s = re.sub(r"`[^`\n]+`", "", s)                     # inline code
        s = re.sub(r"\]\([^)]*\)", "]", s)                  # link targets
        s = re.sub(r"https?://\S+", "", s)
        s = re.sub(r"^\s*\|?\s*:?-{3,}.*$", "", s, flags=re.M)  # table separator rows
    return s


def paragraphs(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


# ---------------------------------------------------------------- red lines

PUNCT = {
    "8 破折号": re.compile(r"——|—|―|–|(?<=\w) -- (?=\w)"),
    "硬禁令 分号": re.compile(r"[；;]"),
    "21 花引号": re.compile(r"[“”‘’]"),
    # emoji 与装饰符号。表格里的对勾与叉号(U+2713、U+2717)不算
    "硬禁令 emoji": re.compile("[\U0001F300-\U0001FAFF\U0001F000-\U0001F2FF\u2600-\u26FF\u2705\u274C\u2728\u2B50]"),
}

ZH_META = [  # 第 4 条，元话术，先宣布再说
    "需要诚实指出", "需要指出的是", "需要强调的是", "需要说明的是", "需要注意的是",
    "值得注意的是", "值得一提的是", "值得强调的是", "值得深思",
    "诚实地指出", "诚实地承认", "我们诚实地",
    "综上所述", "总而言之", "总的来说", "总体而言", "一言以蔽之",
    "换言之", "换句话说", "不难看出", "不难发现", "显而易见", "众所周知",
    "在一定程度上", "某种意义上", "从某种程度上",
    "问题的本质在于", "归根结底", "从根本上说",
]

WEIRD = {  # 第 12、29 条，生硬词、口语比喻词、中文 AI 词(值为建议)
    "通吃": "通用/处处最优", "崩盘": "大幅退化/失效", "冷宫": "最差", "王座": "居首/最优",
    "垫底": "最差/居末", "死穴": "症结/根本局限", "翻盘": "反超", "卖点": "核心贡献",
    "无敌": "严谨/最优", "打脸": "被推翻", "饿死": "得不到预算", "抢光": "挤占",
    "有的放矢": "有针对性", "用武之地": "适用场景", "大概率": "很可能", "秒过": "顺利通过",
    "夺冠": "最优", "称王": "最优", "登顶": "居首", "问鼎": "居首", "称霸": "最优",
    "碾压": "大幅领先", "吊打": "大幅领先", "完胜": "显著优于", "秒杀": "大幅领先",
    "跌破": "低于", "落入末位": "居末", "末位": "最差", "跌入": "落到", "反超": "超过",
    "驾驶位": "主导", "翻车": "失败", "拉胯": "表现差", "遥遥领先": "显著领先", "一骑绝尘": "显著领先",
    "审计": "核查/审查", "平局组": "并列梯队", "平局": "并列/持平", "证据组": "证据/依据",
    "诚实边界": "局限性", "口径": "表述/说法", "稳健": "鲁棒/稳定", "主张": "论点/核心结论",
    "闭环": "写出具体反馈路径", "闸门": "规则/判定条件", "门控": "规则/判定条件",
    "赋能": "写出具体作用", "落地": "部署", "抓手": "写出具体手段", "深度融合": "写出怎样结合",
}

STRONG = {  # (编号 名称) -> 正则
    "1 不是A而是B(英文膨胀反转)": r"\bnot\s+(?:merely|just|simply|only)\b[^.\n]{1,80}?\bbut\b|\bit'?s not\b[^.\n]{1,60}?,\s*it'?s\b",
    "1 不仅…更是/而且": r"不仅(?:仅)?[^。\n]{1,60}?(?:而且|更是|还是)|不只是[^。\n]{1,40}?更是|与其说[^。\n]{1,40}?不如说",
    "2 收尾套话": r"(?i)\b(?:that is the real win|let that sink in|read that again|that distinction matters|this is the key insight)\b|这正是问题的关键|这就是答案",
    "3 故作深刻": r"(?i)\b(?:at its core|the real question is|what really matters|the heart of the matter|the deeper issue)\b",
    "4 铺垫开场": r"(?i)\b(?:let'?s (?:dive|explore|break (?:this|it) down|take a look)|here'?s (?:the thing|what you need to know)|without further ado|real talk)\b",
    "5 和不存在的人争论": r"(?i)\b(?:to be clear|don'?t get me wrong|this is not to say|i'?m not saying|a tempting approach would be|one might be tempted to)\b|本文并不声称|我们并不是说",
    "13 夸大意义": r"(?i)\b(?:stands? as a testament|a pivotal moment|marks? a (?:pivotal|turning)|plays? a (?:key|crucial|pivotal|vital) role|paves? the way|sets? the stage for|evolving landscape|indelible mark|the future looks bright)\b|具有里程碑意义|开创了[^。\n]{0,10}先河",
    "22 聊天客套": r"(?i)\b(?:i hope this helps|great question|certainly!|of course!|you'?re absolutely right|let me know if)\b|希望(?:这)?对你有(?:所)?帮助",
    "23 知识边界声明": r"(?i)\b(?:as of my (?:last|latest) (?:update|training)|up to my last training|based on (?:the )?available information)\b",
    "27 拟人(中文)": r"(?:模型|方法|系统|算法|网络|策略|智能体)(?:会|能|已经|逐渐)?(?:认为|察觉|意识到|知道|关心|拒绝|想要|学会|诚实)",
    "27 拟人(英文)": r"(?i)\b(?:model|method|system|algorithm|network|agent|policy)\s+(?:believes|realizes|knows|cares|refuses|wants|understands|is honest)\b",
    "12 高频 AI 词": r"(?i)\b(?:delve[sd]?|delving|tapestry|testament|showcas(?:e|es|ed|ing)|underscor(?:e|es|ed|ing)|pivotal|crucially|notably|leverag(?:e|es|ed|ing)|it is worth noting|meticulous(?:ly)?)\b",
}

WEAK_WORDS = [  # 第 12 条，单独出现不算，同段成群才算
    "additionally", "enhance", "enhances", "enhanced", "crucial", "robust", "key", "valuable", "highlight",
    "highlights", "align with", "aligns with", "intricate", "interplay", "landscape", "vibrant", "garner",
    "bolster", "bolstered", "enduring", "seamless", "seamlessly", "groundbreaking", "cutting-edge",
    "remarkable", "unprecedented", "comprehensive", "holistic",
]

# ---------------------------------------------------------------- hints

HINTS = {
    "1 X rather than Y": r"(?i)\brather than\b",
    "1 不是A而是B(短对照同位语可保留)": r"(?:并?不是|并非)[^。\n]{1,30}而是",
    "9 叠加限定": r"(?i)\b(?:could potentially|might arguably|may possibly|could possibly|it is also possible that)\b|在一定程度上可能",
    "14 含糊关联": r"(?i)\b(?:(?:is|are|was|were) (?:closely )?(?:associated|linked|tied) (?:with|to)|in connection with)\b|与[^。\n]{1,20}密切相关",
    "15 -ing 尾巴": r"(?i),\s*(?:highlighting|underscoring|emphasizing|showcasing|reflecting|ensuring|fostering|symbolizing)\b|(?:从而|进一步|充分)(?:凸显|彰显|体现)",
    "16 推销语": r"全面提升|大幅超越|性能卓越|效果显著|极大地|显著地",
    "17 借来的权威": r"(?i)\b(?:studies have shown|experts (?:argue|believe|say)|it is widely believed|research shows)\b|大量研究表明|业界普遍认为|研究表明",
    "18 回避是与有": r"(?i)\b(?:serves as|stands as|functions as|boasts)\b|扮演着?[^。\n]{1,20}角色|起到了?[^。\n]{1,20}作用",
    "25 写文档本身": r"(?i)\b(?:the rest of this paper is organized|the table below|this section is organized)\b|本文其余部分安排如下|下表比较了",
    "10 名词后的连字符": r"(?i)\b(?:is|are|was|were|be)\s+(?:high|low|well|long|short|real)-[a-z]+\b",
    "说明性冒号": r"(?<![0-9一二三四五六七八九十义理])：",
    "斜杠除法": r"(?<![\w/.])\d+(?:\.\d+)?/\d+(?:\.\d+)?(?![\w/])",
}


def first_token(sentence):
    s = sentence.strip()
    m = re.match(r"[A-Za-z]+", s)
    return m.group(0).lower() if m else s[:2]


def structural_hints(text, md):
    out = defaultdict(list)
    paras = paragraphs(text)
    for i, p in enumerate(paras):
        lines = [ln for ln in p.splitlines() if ln.strip()]
        if any(re.match(r"^\s*(?:[-*+]\s|\d+[.)]\s|\||#|>|\*\*)", ln) for ln in lines):
            continue                                          # lists, tables, headings, quotes and bold heads are not prose
        sents = [x for x in re.split(r"(?<=[.!?。！？])\s*", p) if x.strip()]
        # 7 连续三句以上同一句首
        run = 1
        for a, b in zip(sents, sents[1:]):
            run = run + 1 if first_token(a) == first_token(b) and len(first_token(a)) > 0 else 1
            if run == 3:
                out["7 连续同一句首"].append(p[:60])
        # 2 单句短段落紧跟长段落
        if i > 0 and len(sents) == 1 and len(p) < 40 and len(paras[i - 1]) > 120 and not p.startswith("#") \
                and not p.startswith("|") and not p.startswith("-") and not p.startswith(">"):
            out["2 单句短段落(检查是否复述上段)"].append(p[:60])
    if md:
        for line in text.splitlines():
            if re.match(r"^\s*[-*]\s+\*\*[^*]*[:：]\*\*|^\s*[-*]\s+\*\*[^*]+\*\*\s*[:：]", line):
                out["19 加粗标签列表"].append(line.strip()[:60])
            m = re.match(r"^#{1,6}\s+(.+)$", line)
            if m:
                words = re.findall(r"[A-Za-z]+", m.group(1))
                long_words = [w for w in words if len(w) > 3]
                if len(long_words) >= 3 and all(w[0].isupper() for w in long_words):
                    out["20 标题每词大写"].append(m.group(1)[:60])
    return out


# ---------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(description="润色自检，零红线才算过")
    ap.add_argument("file")
    ap.add_argument("--max-examples", type=int, default=3)
    a = ap.parse_args()
    path = a.file
    text = text_of(path)
    k = a.max_examples
    red, hint = defaultdict(list), defaultdict(list)

    for name, pat in PUNCT.items():
        red[name] += pat.findall(text)
    for ph in ZH_META:
        if ph in text:
            red["4 元话术 " + ph] += [ph] * text.count(ph)
    for w, sug in WEIRD.items():
        if w in text:
            red["29 生硬词 %s -> %s" % (w, sug)] += [w] * text.count(w)
    for name, pat in STRONG.items():
        red[name] += [m.group(0) for m in re.finditer(pat, text)]
    for p in paragraphs(text):
        low = p.lower()
        found = sorted({w for w in WEAK_WORDS if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", low)})
        if len(found) >= 3:
            red["12 弱 AI 词成群"].append(", ".join(found))
    for name, pat in HINTS.items():
        hint[name] += [m.group(0) for m in re.finditer(pat, text)]
    for name, items in structural_hints(text, path.endswith(".md")).items():
        hint[name] += items

    total = sum(len(v) for v in red.values())
    nhint = sum(len(v) for v in hint.values())
    for name, items in red.items():
        if items:
            print("  [红线 %s] %d 处: %s" % (name, len(items), items[:k]))
    for name, items in hint.items():
        if items:
            print("  [提示 %s] %d 处: %s" % (name, len(items), items[:k]))
    if total == 0 and nhint == 0:
        print("OK 无红线，无提示")
    elif total == 0:
        print("无红线命中，另有 %d 处提示待人工判断(见 writing-deai.md 对应编号)" % nhint)
    else:
        print("共 %d 处红线需清理，另有 %d 处提示" % (total, nhint))
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())

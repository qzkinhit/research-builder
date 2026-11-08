# rebuttal-kit

审稿回复与修订稿的工作套件。作者决定回复的内容与取舍，模板和脚本负责排版、导出、计数和核对。示例内容全部虚构，主题是预算受限的重复记录检测，系统和基线叫 OurSys、L-Boost、L-Forest，是一套独立于手册 PairSift 例子的示例，换成自己的内容后删掉。

| 目录 | 内容 |
|---|---|
| `project/` | 中英对照回复的 LaTeX 工程，导出 OpenReview Markdown，逐条统计字符数并生成 (k of n) 标题 |
| `revision/` | 修订稿标记样式 `revmark.sty` 与单页示例，改动红色，页边编号按审稿人分色，图表内同样可用 |
| `scripts/` | 全精度舍入、区间对照、措辞轮不变量、一览表、页边编号、交付打包六个检查脚本 |
| `example/` | 虚构的运行记录、数字表与比较表，脚本在其上演示 |

## 依赖

| 依赖 | 用途 | 是否必需 |
|---|---|---|
| Python 3.9 以上 | 导出与全部脚本，只用标准库 | 必需 |
| XeLaTeX（ctexart、tcolorbox、tikz 等 TeX Live 常见宏包） | 编译两份示例 | 必需 |
| PyMuPDF（`pip install -r requirements.txt`） | `check_margin_tags.py` 的 PDF 部分 | 查页边编号时需要 |
| node 与 markdown-it、katex | `make render` 离线渲染检查 | 可选 |

## 试运行

```
make test                      # 导出脚本与检查脚本的自测
make demo PDFPY=<装有pymupdf的python>   # 在示例上跑完整流程，产物在 project/ 与 revision/
make clean                     # 恢复到复制时的状态
```

## 开始一篇新回复

1. 把 `project/` 复制进论文仓库，例如放成 `rebuttal/`。`scripts/` 不用复制，按路径调用即可。
2. 改 `reviewers.tex`，每位审稿人一行 `\RevReviewer{编号}{颜色HTML}`，这个文件是编号与颜色的唯一来源，回复工程和修订稿都读它。改 `kit.json`，写上主文件名、每条评论的字符上限和各文件路径。
3. 把审稿意见逐字存入 `source/reviews.md`，给每条意见加编号，格式见下节。运行 `python3 tools/gen_reviews_tex.py` 生成 `reviews_bilingual.tex`，只在其中填写中文译文，`make verify` 核对英文原文逐字未变。
4. 在 `rebuttal_main.tex` 里按审稿人写回复。每组意见是一个 `rbgroup`，里面一个 `responseen` 与一个 `responsezh`。`make` 导出并编译，`make check` 只导出并统计，`make strict` 在粘贴前运行，有未填写项、超限或编号不一致时返回非零。
5. 实验出结果后，用 `example/claims.csv` 的形式写下回复里的每个数字及其统计方式，用 `check_rounding.py` 与 `build_interval_map.py` 核对。
6. 修订稿中按下文用 `revmark.sty` 标记改动，用 `check_margin_tags.py` 核对。
7. 全部定稿后运行 `check_glance_table.py` 与 `build_deliverables.py`，把要发的文本和文件收进一个目录。

## 回复工程

### 文件

| 文件 | 作用 | 是否手改 |
|---|---|---|
| `rebuttal_main.tex` | 主文件，分组与全部回复 | 改 |
| `reviews_bilingual.tex` | 审稿意见原文与中文译文，每条一个 `\DefConcern` | 只改译文 |
| `rebuttal_preamble.tex` | 版式、配色与命令定义 | 一般不改 |
| `reviewers.tex` | 审稿人编号与颜色 | 改 |
| `kit.json` | 主文件名、字符上限、评论标题格式、文件路径、交付清单 | 改 |
| `source/reviews.md` | 审稿意见逐字原文 | 只加编号 |
| `templates/` | 上传后跟帖与讨论期结束前催复的模板 | 改 |
| `tools/export_openreview.py` | 导出 Markdown，写字符数与发帖顺序 | 不改 |
| `tools/check_markdown.py` | 检查导出文本里 OpenReview 可能渲染错的写法 | 不改 |
| `tools/render_check.js` | 可选，用 markdown-it 与 KaTeX 离线渲染 | 不改 |
| `tools/check_reviews.py`、`tools/reviews_source.py` | 核对英文原文逐字一致 | 不改 |
| `tools/gen_reviews_tex.py` | 从 `reviews.md` 生成 `reviews_bilingual.tex`，已有译文保留 | 不改 |
| `tools/sync_drafts.py` | 把主文件各节写成 `drafts/<节>.tex` 供单独阅读 | 不改 |
| `openreview/*.md`、`openreview/index.json`、`counts.tex` | 导出结果 | 自动生成 |

### 命令

```
make               # 导出 openreview/*.md 与 counts.tex，再 xelatex 编译两遍
make check         # 只导出并打印每条评论的字符数、标题、回填后估计字符数与全部未回填项
make strict        # 同 check，并在超限、有 \pending、有待填写回复块、(k of n) 标签或审稿人列表不一致、Markdown 有隐患时返回非零
make test          # 导出脚本自测
make verify        # 核对 reviews_bilingual.tex 中的英文原文与 source/reviews.md 逐字一致
make drafts        # 写出 drafts/<节>.tex
make drafts-check  # 核对 drafts 与主文件一致
make render NM=<node_modules目录>   # 可选，渲染检查
```

### reviews.md 的格式

```
## Reviewer R1  (Rating 3: Weak reject; Confidence 4)

### Summary
段落原文。

### Strengths
段落或项目符号，每段一个单元，编号自动派生为 R1-S1、R1-S2。

### Weaknesses
(R1-W1) 带编号的段落。
- (R1-W2) 也可以写成项目符号。
没有编号的收尾段自动派生为 R1-W2-end。

### Questions
(R1-Q1) 问题原文。

---
```

`## Context: ...` 开头的块里的项目符号派生为 `REF-1`、`REF-2`，用于附录中不需要回复的参考意见。编号以外的文字逐字保留，直引号在 tex 里存为 `\textquotedbl{}`，以免排版时变成弯引号。

### 写回复

- 总回复写在 `\GeneralSection` 之后，每位审稿人的回复写在 `\ReviewerSection{编号}` 之后。
- 分组用 `\begin{rbgroup}[可选标题]{编号1, 编号2}`，先排所列意见的原文与译文，再写回复。带星号的 `rbgroup*` 只列编号，用于总回复。编号列表可以为空。
- 还没有结果的数字写成 `\pending{说明}`，PDF 中显示为红字，导出时变成 `**[PENDING: 说明]**`，`make check` 列出每一处的文件与行号。占位命令 `\respTBD` 写入正文后删掉。
- 一位审稿人的回复超过一条评论的上限时，在两个 `rbgroup` 之间写一行 `\CommentBreak{(2 of 3)}`，第一组的可选标题写 `(1 of 3)`。之后的回复块导出到 `<编号>_part2.md`，每条各自计数，标题写成 `Response to Reviewer R1 (2 of 3)`。标签与实际条数不一致时 `make strict` 报错。
- 改译文只改 `\DefConcern` 的第四个参数。

### 英文回复可用的写法

`responseen` 里只能用下表的写法，其他命令（如 `\cite`、`\ref`、`\,`、`$$...$$`、`---`）导出时报错并给出文件与行号，不会被静默丢弃。

| LaTeX | 导出的 Markdown |
|---|---|
| 空行分段 | 空行 |
| `\textbf{x}` | `**x**` |
| `\textit{x}`、`\emph{x}` | `*x*` |
| `\texttt{x}` | `` `x` `` |
| `$...$` | 原样保留，OpenReview 按行内公式渲染 |
| `\[ ... \]` | 单独成段的 `$$...$$`，OpenReview 按独立公式渲染 |
| `\%` `\&` `\_` `\#` `\{` `\}` | 对应字符 |
| `\$` | `\$`（避免 OpenReview 把它当作公式起点） |
| `~` | 空格 |
| `--`（数值区间） | 短横 |
| ` ``x'' ` | `"x"` |
| `\ldots` | `...` |
| `\url{u}`、`\href{u}{t}` | `u`、`[t](u)` |
| `\rhead{x}`（小标题行） | `#### x` |
| `itemize`、`enumerate` 与 `\item`，可嵌套 | `- ` 与 `1. ` 列表 |
| `rtable` 环境 | Markdown 管道表 |
| `\pending{说明}` | `**[PENDING: 说明]**` |
| `\respTBD` | 不输出，该回复块记为待填写 |
| `%` 注释 | 删除 |

表格列格式只能用 `l`、`c`、`r`，第一行是表头，`\toprule`、`\midrule`、`\bottomrule`、`\hline` 在导出时忽略。单元格内的 `|` 自动转义，但公式里的 `|` 会把单元格切开，导出时报错，写成 `\mid` 或 `\vert`。列格式恰为 `lll` 的表在 PDF 中按行宽折行，作为每位审稿人第一条的一览表，其余表整表缩放到行宽。

### OpenReview 的公式

OpenReview 先跑 Markdown 再跑 TeX，官方文档也写明 Markdown 会吃掉 TeX 里的反斜杠，词首词尾的下划线需要转义。`make strict` 运行 `check_markdown.py`，报告下面几类写法，改写后更稳，发帖前仍在评论框的 Preview 里看一眼。

| 写法 | 问题 | 改写 |
|---|---|---|
| `\{`、`\}` | Markdown 去掉反斜杠，花括号变成 TeX 分组 | `\lbrace`、`\rbrace` |
| `\,`、`\;`、`\!` | 反斜杠被去掉，字符留在公式里 | `\thinspace`、`\thickspace`、`\negthinspace` |
| `\\`（多行公式） | 变成单个反斜杠，换行失效 | 一行写一个公式 |
| `}_k` 之后又有 `x_{i}` | 两个下划线可能配成斜体，吃掉公式 | 避免紧跟右花括号的下标，或拆到两段 |
| `a*b` | 星号可能配成强调 | `\ast` 或 `\cdot` |

除法一律写成分式 `\frac{a}{b}` 或 `\tfrac{a}{b}`，不写斜杠。

### 字符数

计数对象是每个导出文件的全文，不含文件末尾的换行，方法是 Python 的 `len`，一个汉字、一个字母、一个换行都算 1。上限在 `kit.json` 的 `comment_limit` 里设置。换行按两个字符计时若超过上限，`build_deliverables.py` 在该条后面标出，这时建议把这一条再压短一点。字符数显示在 PDF 首页的评分一览表、每节开头与每个分界框中，PDF 里的数字来自上一次 `make check` 或 `make` 生成的 `counts.tex`。

## 修订稿标记

把 `revision/revmark.sty` 放到论文目录，在模板与 hyperref 之后加入下面几行。中英两版修订稿都可以用，两版共用同一份 `reviewers.tex`。

```latex
\usepackage{revmark}
\input{rebuttal/reviewers}
\RevSetup{link color=2F3FAF}     % 可选，引用统一成一种颜色，版心内只留正文黑、引用色、修订红三种颜色
```

| 命令 | 用途 |
|---|---|
| `\rev{文字}{R1-W1, R1-Q1}` | 红色文字，首行旁的右侧页边按审稿人分色写 `R1-W1`，用于正文段落 |
| `\revred{文字}` | 红色文字，不写批注，用于共用一条批注的段落和节标题 |
| `\revcap{文字}{R1-W1}` | 红色文字，首行旁写批注，用 TikZ overlay，用于图题、表题和表格单元，需要编译两遍 |
| `\revnote{R1-W1}`、`\revfloatnote{R1-W1}` | 只写批注，用于已经是红色的内容 |

`\RevSetup` 的选项有 `note width`、`note sep`、`note push`、`note font`、`tag prefix`、`change color`、`link color`、`float xshift`、`float yshift`、`final`。默认批注字号 `\small`，出界或重叠时退到 `\footnotesize`。`final=true` 去掉全部颜色与批注，文字保留。

约定如下，便于审稿人对照。

- 红色只给实质改动，新结果、更正的论断、整段新增、整表整图。几个词的小改不标不上色。
- 批注只写编号，一处最多叠两个。需要前缀时用 `tag prefix` 选项自行设置，默认不加前缀。
- 不改版心、字号与行距，只调页边参数，正文不超页。版心被改过容易被认为绕过页数限制。
- 回复里写修订稿的节号、表号与页边编号，审稿人下载 PDF 后可以逐条对照。

本样式不支持双面排版，双栏模板的 `\marginpar` 落在就近的外侧页边，图表内的批注固定在右页边，这两种情况用 `float xshift` 调整或改写在正文里。

## 检查脚本

每个脚本的完整选项见文件开头的说明，或运行 `python3 scripts/<脚本> --help`。退出码非零表示有问题。

| 脚本 | 做什么 |
|---|---|
| `check_rounding.py` | 每个印出的数字从逐次运行记录按精确分数重算，只舍入一次。`within X` 与 `at or above` 这类说法按全精度逐表判断。四位小数的汇总再舍入会出错的数字标为 DOUBLE ROUNDING 或 trap |
| `build_interval_map.py` | 列出回复与修订稿里每个区间、对应的比较和重算值。每个比较按筛选条件、指标与方法的哈希取独立随机种子，加数据不漂移。先写好 `comparisons.json`，未映射或值变了的区间列出待处理 |
| `check_invariants.py` | 改措辞前后各 dump 一次再 compare，数字、数词、节表图引用、文献键、审稿人编号、哪份文稿的用词都不能变，块外文字也不能变。`lint` 列出破折号、分号、冒号和套话 |
| `check_glance_table.py` | 一览表每个数字都要在同一位审稿人的正文中出现，中英两张表的数字相同，第三列写清位置和页边编号。加 `--revision` 时公式里的数字要在修订稿中出现 |
| `check_margin_tags.py` | PDF 上核对批注颜色、位置、重叠、与红色文字的距离和全稿颜色。源文件上核对编号属于审稿意见、一条批注不超过两个编号、回复引用的编号在修订稿里都有。`--original` 与 `--revised` 列出未标记的改动 |
| `build_deliverables.py` | 按发帖顺序编号复制粘贴文本，逐字节比对，写 README 与 SHA256SUMS。有旧文件残留、未就绪或仍有 `<占位>` 时停止 |

用示例跑一遍的命令都在顶层 `Makefile` 的 `demo` 目标里。

`fullprec.py` 是公共库。默认聚合是运行取均值、数据划分取均值、数据集等权平均，指标可以写成 `n_found/n_true`，两列相除得到精确分数。记录格式不同时改 `read_runs` 或 `build_interval_map.py` 的 `load_values`。

## 交付与发帖

`build_deliverables.py` 按 `openreview/index.json` 的顺序编号，`README.md` 列出每个文件对应的 OpenReview 评论标题与字符数。建议的节奏如下。

1. 先按编号发回复，选好可见范围。
2. 过几天再上传修订稿 PDF 与补充材料，让修订稿吸收第一轮回复后的反馈。回复里的位置写成 In the revision，区分 the submission 与 the revision，修订稿上传前这样写同样成立。
3. 上传后发 `followup_after_upload` 里的英文跟帖，列出新增内容和回应的意见。
4. 讨论期结束前约两天，对还没回应的审稿人按 `reminder_before_deadline.md` 发一条，发帖前按上传的 PDF 再核一次节号表号。审稿人回应后按同一文件末尾的模板致谢，如有新问题先逐条作答。

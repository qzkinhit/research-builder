# tools · 检查与出稿脚本

| 脚本 | 用途 | 依赖 |
|---|---|---|
| `polish_check.py` | docx、pptx、md、txt 的去 AI 腔自检。红线计入失败，提示交给人工判断，编号对应 `writing-deai.md` 第 4 节 | 标准库 |
| `audit_tex.py` | LaTeX 投稿前核查。禁词、强痕迹、正文的破折号分号花引号、`$` 配对、花括号与环境配平、引用闭合、重复 label、Finding 与 RQ 编号 | 标准库，与 `polish_check.py` 共用模式表 |
| `docx_deai.py` | 在 Word 稿里就地替换生硬词、元话术、分号和花引号，保留格式，默认只预演 | python-docx |
| `build_docx.py` | 把 Markdown 章节汇编成带原生 OMML 公式的 Word 稿 | python-docx、latex2mathml、mathml2omml、lxml |
| `docx_layout_check.py` | 生成后的 docx 排版体检，查表格单元格首行缩进、标题居中、参考文献编号 | 标准库 |
| `layout_diff.py` | 比对同一篇双栏稿两次编译的版面，逐页逐栏比较全部行的纵坐标、末行和最大空隙，用于确认改字没有挪动浮动体或撑开空白 | 标准库，poppler 的 pdftotext |
| `acronym_check.py` | 读入 `\input` 的文件并展开稿件里定义的宏，再列出从没解释也没引用过的缩写(never)、只在后文才解释的缩写(later)和在正文里定义了不止一次的缩写(twice)，摘要、题注和表图不计入 twice，大同行可读性检查用 | 标准库，与 `abstract_words.py` 共用宏展开 |
| `abstract_words.py` | 展开数字宏后数摘要字数，对照投稿上限。`--plain` 输出投稿系统用的纯文本摘要，`--compare` 与系统里已有的版本逐词比对 | 标准库 |
| `page_fit.py` | 页数卡在上限时查固定点：参考文献起始页、大表所在页、各栏栏底、指定标题上方的空隙、正文末页末行 | 标准库，poppler 的 pdftotext |
| `short_ends.py` | 列出末行很短、值得试 `\looseness=-1` 的段落 | 标准库，poppler 的 pdftotext |
| `log_diff.py` | 比对同一篇稿件两次编译的警告、pdfTeX 警告和错误，作业名、行号和页码先换成占位符，新增的逐条列出。改前版本要按正式稿的完整步骤编译 | 标准库 |
| `pkg_check.py` | 把源码包解压到空目录，删掉主文件的 `.bbl`、`.aux` 和 PDF，屏蔽个人 texmf 目录后从零编译，与要上传的 PDF 逐页比对文字和像素，并核对重新生成的 `.bbl`。`--bib none` 用于只带 `.bbl` 的包 | 标准库，TeX，poppler 的 pdftotext 与 pdftoppm |
| `anon_check.py` | 双盲投稿前查 PDF 的元信息(含 XMP 和插入图片自带的元信息)、未嵌入的字体，以及名单里的姓名、单位、基金号和账号在正文与链接目标里的出现，命中处标出是否在参考文献里。参考文献之后的附录、checklist 和致谢按正文算，标题认不出时用 `--refs-end` 指定 | 标准库，poppler 的 pdfinfo、pdffonts 与 pdftotext |
| `server_plan_template.md` | 只剩大规模实验时的交接三件套模板 | |
| `test_pptx_skill_install.py` | 安装脚本与 PPT 技能素材的回归测试 | 标准库 |

## 用法

```bash
python3 -m venv venv && venv/bin/pip install -r tools/requirements.txt

python tools/polish_check.py 稿件.docx                       # 零红线才算过
python tools/audit_tex.py main.tex appendix.tex banned_words.txt   # 正文与附录一起传
python tools/docx_deai.py 稿件.docx                         # 预演，确认后加 --apply，原件备份为 .bak

venv/bin/python tools/build_docx.py --sections sections/ --meta meta.json --out 论文稿.docx --toc
python tools/docx_layout_check.py 论文稿.docx

python tools/layout_diff.py 改前.pdf 改后.pdf               # 逐栏一致才退出码为 0
python tools/acronym_check.py main.tex                      # never 与 twice 两栏逐个处理
python tools/abstract_words.py main.tex --limit 250
python tools/abstract_words.py main.tex --plain > abstract.txt      # 贴进投稿系统的纯文本
python tools/abstract_words.py main.tex --compare submitted.txt     # 与系统里的版本逐词比对
python tools/page_fit.py paper.pdf --heading "PROBLEM STATEMENT" --captions "Table 1,Table 4" --last-body-page 12
python tools/short_ends.py paper.pdf --pages 3-5                    # 试 \looseness=-1 之前先列候选
python tools/log_diff.py old.log new.log                            # 新增警告为零才退出码为 0
python tools/pkg_check.py package.zip en/main.tex submitted.pdf     # 源码包从零编译后逐页与正文一致
python tools/anon_check.py submitted.pdf --names names.txt         # 名单文件不进仓库
```

`build_docx.py` 的 `meta.json` 含 `title_zh`、`title_en`、可选的 `subtitle`、`references`(字符串列表)和 `glossary`(含 en、zh、def 的对象列表)。`--template` 给出期刊或学校的 docx 模板时继承其页面、网格与样式，不给时生成带行网格的 A4 模板。`--figs` 是一个 JSON，键为章节文件名，值为图片路径与图注。

## 出 Word 稿踩过的坑

以下几条已在 `build_docx.py` 里处理，改脚本时不要改回去。

- `mathml2omml` 会用 `</m:groupChr>` 错误地闭合 `<m:groupChrPr>`，影响 `\underbrace`、`\bar` 等，`fix_omml` 修正它。
- 段落不设倍数行距。倍数行距会被文档网格吸附成双倍行距，页数暴涨。行距交给页面网格。
- 首行缩进用 `firstLineChars`(200 表示两个字符)，不用空格。表格单元格清零缩进。
- 以模板 docx 为底板填内容(读入后清空正文再写)，这样继承页面与网格。
- 章节标题左对齐，钳到 Heading 1 到 4，不映射到居中的 Title 样式，中文用宋体黑字。
- 参考文献列表编号为 [1] [2]，正文引用与之对应。同时出 LaTeX 稿时，以 tex 为源，改 tex 后重建 docx。
- 系统 pip 常被 PEP 668 拦住，所以用隔离的 venv。公式必须是原生 OMML，不留图片或 LaTeX 源码，转换失败的公式才退回 xelatex 渲染的图片。

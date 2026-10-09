# tools · 检查与出稿脚本

| 脚本 | 用途 | 依赖 |
|---|---|---|
| `polish_check.py` | docx、pptx、md、txt 的去 AI 腔自检。红线计入失败，提示交给人工判断，编号对应 `writing-deai.md` 第 4 节 | 标准库 |
| `audit_tex.py` | LaTeX 投稿前核查。禁词、强痕迹、正文的破折号分号花引号、`$` 配对、花括号与环境配平、引用闭合、重复 label、Finding 与 RQ 编号 | 标准库，与 `polish_check.py` 共用模式表 |
| `docx_deai.py` | 在 Word 稿里就地替换生硬词、元话术、分号和花引号，保留格式，默认只预演 | python-docx |
| `build_docx.py` | 把 Markdown 章节汇编成带原生 OMML 公式的 Word 稿 | python-docx、latex2mathml、mathml2omml、lxml |
| `docx_layout_check.py` | 生成后的 docx 排版体检，查表格单元格首行缩进、标题居中、参考文献编号 | 标准库 |
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

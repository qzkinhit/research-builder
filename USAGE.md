# 使用说明

给第一次上手的人。安装见 [README](README.md)，规则全文见 `SKILL.md` 与各手册。下面按用途给出说法、它会做什么和你得到什么。

## 主要用法，把半成品论文推到只剩大规模实验

**说法。**「按 research-builder 改进我这篇论文，位置在 <路径>，做到只剩大规模实验」。

**它会做什么。** 开工先列可核验的待办，然后不停地推进到判据为止。

1. 清遗留。正文引用的图加入 git，缺图补上，真编译两遍确认没有未解析的引用，再提交。
2. 深读全文，扫出所有 `\pending`、占位和 TBD。
3. 调用 `paper-survey` 调研最强的 baseline 和可借鉴的改进点。
4. 忠实复现已命名的和调研新增的 baseline，全部跑通。
5. 改进方法，做完多种子的小规模实验与消融，按 `diagnostic-playbook.md` 诊断，退化和不进论文的结果也记档。
6. 按手册写完文稿，由回填脚本写入真数字，补附录与图，统一术语与文风。
7. 列出必须大规模 GPU 的实验，交付 `runall.sh`，需要交接时按 `tools/server_plan_template.md` 出三份文档。

**停止判据。** 除大规模 GPU 实验外，论文、系统、baseline 与小规模实验全部完成且可跑。

## 写论文(中英文 LaTeX 两稿，可另出 Word)

**说法。**「按我素材的词写引言」「回填实验章，排主表，画实验图」。

它先读 `writing-playbook.md` 与 `writing-deai.md`，再按 `knowledge/paper-anatomy.md` 的骨架写。新论文从 `templates/latex-bilingual/` 起步，一种语言一个入口文件，中文镜像逐段对应。数字由 `templates/backfill/backfill.py` 写入，表照 `figure-style/tables/README.md` 排，图照 `figure-style/README.md` 画。强项放在强调位，弱项写进给导师的内部报告。要 Word 稿时用 `tools/build_docx.py` 出原生公式的 docx。

## 去 AI 腔与润色

**说法。**「按 writing-deai 把这段改一遍」「按我的讲法润色这个 Word，别造新词」「投稿前把这篇论文核一遍」。

- 贴一段文字时，它返回草稿、剩余痕迹清单和定稿，论文段落附不超过三行的改动理由，英文稿加中文对照。
- 给文件时，它就地改文字，不动版式、公式、数字、引用和标签，最后给一份改了哪些、为什么的清单。
- 你在 `materials/writing-samples/` 放了声音样本时，它按样本的句长、用词、段首和过渡改写。
- 改完跑检查脚本，Word、PPT、Markdown 用 `tools/polish_check.py`，LaTeX 用 `tools/audit_tex.py`，都要零红线。

## 写本子

**说法。**「按 research-builder 写青年基金的研究内容」「把这三个研究点的技术路线写出来」。

它按 `knowledge/grant-proposal.md` 的提纲和段落模式写，挑战、研究点、关键科学问题和创新点四处的数目与顺序对齐。你在 `materials/general/` 放了以往的本子时，句式和锁定词从那里取。研究内容关系图与技术路线图交给 `paper-figure-pptx`。

## 写 rebuttal

**说法。**「按 research-builder 写 rebuttal，审稿意见在 <路径>」。

它按 `knowledge/rebuttal.md` 组织，用 `templates/rebuttal/rebuttal_template.tex` 排版。共同的问题进 General Response，每条意见一个编号标签，第一句直接回答，新实验的头条数字加粗，修订承诺具体到节和图表编号。

## 画图

- **实验图。** 说「按我的风格画一行四图和雷达消融」。它把 `figure-style/figstyle.py` 复制到绘图脚本旁边，从样例改数据，按印刷尺寸输出 PDF、SVG 和 PNG。
- **实验表。** 说「排能力表、数据集表和主表」。主表表体由 `shade_and_rank.py` 或回填脚本生成，前两名底色和排名按印出的数值计算。
- **动机图、系统图与本子图。** 说「按 paper-figure-pptx 画一张系统图」。它按 `knowledge/figure-archetypes.md` 或你放在 `materials/figures/` 的参考图选版式，交付可编辑的 PPT，并实际渲染检查。

## 调研

**说法。**「按 paper-survey 调研这个选题的 baseline，只调研」或「调研完直接写」。

它按子方向并行检索，优先 CCF-A、权威和已开源的工作，用 `paper-survey/tools/fetch_arxiv.sh` 抓 arXiv 的 LaTeX 源与 HTML，产出 `survey.md`。

## 可以直接跑的检查

```bash
python3 tools/polish_check.py 你的文稿.docx
python3 tools/audit_tex.py main.tex appendix.tex
python3 templates/latex-bilingual/check_mirror.py main_en.tex main_zh.tex
python3 templates/backfill/backfill.py --registry templates/backfill/registry.example.json --paper-dir templates/latex-bilingual --dry-run
bash paper-survey/tools/fetch_arxiv.sh 2302.03169 researched_papers
```

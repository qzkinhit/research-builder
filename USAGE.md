# 使用说明

给第一次上手的人。安装见 [README](README.md)，规则全文见 `SKILL.md` 与各手册。下面按用途给出说法、它会做什么和你得到什么。

## 开始之前

研究由你主导，skill 按你的五阶段流程辅助。开工前请准备三样东西。

1. 你调研并读过的文献，LaTeX 源或 PDF 都可以，放进 `researched_papers/`，在 `notes.md` 里写下你对每篇的判断。
2. 你的研究方向和核心想法，一句话的核心论点，服务什么下游。
3. 你自己的素材，包括已发表论文、本子、写作样本、满意的图表，放进 `materials/` 对应的子目录。

## 主要用法，按五阶段推进一个课题或一篇已有稿件

**说法。**「我的调研文献在 researched_papers，研究方向是某某，按 research-builder 的五阶段从对齐开始」，已有稿件时加上「稿件在 <路径>」。

**每个阶段交什么、你确认什么。**

| 阶段 | 交付物 | 由你确认 |
|---|---|---|
| 0 对齐 | 概念表、锁定术语表、每篇文献的借鉴点与超越点、稿件的待办清单 | 核心论点、术语、baseline 名单 |
| 1 搭系统 | 纯方法包、应用层薄壳、能跑通的最小流程 | 实现是否符合你的方法设计 |
| 2 忠实 baseline | 每个 baseline 的实现、冒烟测试、忠实度记录 | 复现是否公平，哪些进对照表 |
| 3 实验 | 多种子、等预算的实验与完整日志 | 数据集与实验设置 |
| 4 诊断与改方法 | 排查报告、改进变体及其对比 | 改动是否合理，留哪个方法 |
| 5 回填论文 | 由回填脚本写入数字的中英文稿件、给导师的内部报告、投稿前核查结果 | 核心论述与每一个论断 |

需要大规模算力的实验，它会列清单并按 `tools/server_plan_template.md` 写交接文档。负结果、退化和没进论文的结果都记进 `docs/`，供你判断。

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

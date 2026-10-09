# research-builder

research-builder 是一套给 Claude Code 与 Codex 用的科研辅助 skill。它把一位研究者在数据质量与数据准备方向写顶会与汇刊论文时形成的五阶段工作流程、写作纪律和检查工具整理成规则，让 AI 在研究者的主导下承担其中的工程实现、实验记录、排版、润色和核查。

研究由你主导。选题、文献调研与精读、核心想法、baseline 的取舍、方法改动和论文里的每一个论断，都由你提出或确认。skill 按五个阶段推进，每个阶段结束时交出可核验的产物，等你确认后再进入下一阶段。所有数字只来自真实的实验记录，它不会也不应该替你编造结果。

它适用于「提出方法，用理论与实验证明它更好」的实证型研究。你放进来的素材越多(你读过的文献、你的论文、你的图表与文字)，它的产出越贴近你的研究与风格。

*English summary.* research-builder is a Claude Code and Codex skill set that assists a researcher through a five-stage workflow for empirical papers. The researcher chooses the topic, reads the literature, proposes the idea and approves every stage. The skill helps turn the researcher's surveyed related work into a runnable system, faithfully reproduced baselines, multi-seed experiments and a bilingual (English and Chinese) LaTeX paper whose numbers are filled in by a backfill script from the experiment records. It ships a writing manual with 32 AI-writing patterns adapted from [humanizer](https://github.com/blader/humanizer) for academic prose, checkers for LaTeX, Word and PowerPoint, a matplotlib module for print-size experiment figures, LaTeX table macros, a bilingual paper skeleton, rebuttal and grant-proposal guides, and an editable-PPT figure skill with a starter SVG icon set. The documents are written in Chinese.

## 能做什么

| 能力 | 内容 |
|---|---|
| 科研五阶段 | 对齐 → 搭系统(纯方法与应用薄壳分离) → 忠实复现 baseline(三层忠实度认证) → 实验(公认数据集、等预算、多种子) → 诊断改方法 → 回填论文 |
| 写作与去 AI 腔 | 叙事与取舍手册，以及改编自 humanizer 的 32 条 AI 腔模式、改写流程和声音匹配。检查脚本覆盖 LaTeX、Word、PowerPoint 和 Markdown |
| 论文骨架 | 方法论文从标题到附录的逐节写法和中英文句式，benchmark 论文的叙事，基金本子与 rebuttal 的写法 |
| 实验图与表 | 按印刷尺寸出图的绘图模块和四个样例，能力表、数据集表和主表的宏与生成脚本 |
| 学术插图 | 独立的 `paper-figure-pptx` 技能，做可编辑的动机图、系统图与本子图，带 16 个自绘 SVG 入门图标 |
| 模板 | 中英镜像的 LaTeX 骨架、镜像核对脚本、数字回填脚本、rebuttal 模板 |
| 调研 | 独立的 `paper-survey` 技能，优先抓 arXiv 的 LaTeX 源与 HTML，按权威与开源筛选 |

## 快速开始

**第一步，安装。** 克隆到 Claude Code 的 skill 目录并运行安装脚本，它会把 `paper-survey` 和 `paper-figure-pptx` 也部署成独立 skill。

```bash
git clone https://github.com/qzkinhit/research-builder.git ~/.claude/skills/research-builder
bash ~/.claude/skills/research-builder/install.sh
python3 -m venv ~/.venvs/rb && ~/.venvs/rb/bin/pip install -r ~/.claude/skills/research-builder/tools/requirements.txt
```

**第二步，放你调研并读过的文献(必需)。** 把相关工作的 LaTeX 源或 PDF 放进 `researched_papers/`，并在 `researched_papers/notes.md` 写下你对每篇的判断，比如能否当 baseline、借鉴哪一点、要超越哪一点。`paper-survey` 可以帮你检索和下载候选论文，但读哪些、信哪些、选谁当 baseline 由你决定。

**第三步，放你自己的素材(强烈建议)。** skill 写出来像不像你，取决于这一步。

| 放什么 | 放哪 | 作用 |
|---|---|---|
| 你已发表或定稿的论文，最好是 LaTeX 源 | `materials/domain/` | 术语、记号、立场、结构与句式的模仿对象 |
| 你的本子、项目申请书 | `materials/general/` | 本子的句式与论证逻辑 |
| 最能代表你行文声音的中英文文字 | `materials/writing-samples/` | 去 AI 腔改写时的声音样本 |
| 你满意的系统图、动机图、实验图与表 | `materials/figures/` | 画新图时沿用的结构、配色与版式 |
| 你的图标库与汇报 PPT | `materials/icons/`、`materials/ppt/` | 学术插图与汇报的素材 |

这些文件默认不进 git，只留在你的电脑上，详见 [materials/README.md](materials/README.md)。不放素材时，skill 只能按 `knowledge/` 的通用骨架写，产出会比较平。

**第四步，从对齐阶段开始。** 在 Claude Code 里说「按 research-builder 的五阶段，从对齐开始」，告诉它你的研究方向与核心想法、代码仓库与论文目录、实验服务器、投稿目标。它先读完你的文献与素材，交出概念表、锁定术语表和每篇文献的借鉴点与超越点，等你确认后再进入下一阶段。

## 五个阶段与你的角色

| 阶段 | skill 做什么 | 你做什么 |
|---|---|---|
| 0 对齐 | 读你的文献与素材，整理概念表、术语表、借鉴点与超越点 | 给出研究方向与核心想法，确认术语和 baseline 名单 |
| 1 搭系统 | 按你的方法设计写纯方法包与应用层薄壳，跑通最小流程 | 审阅方法实现是否符合你的设计 |
| 2 忠实 baseline | 按原论文复现 baseline，做三层忠实度认证并留记录 | 核对复现是否公平，决定哪些进对照表 |
| 3 实验 | 在你的服务器上跑公认数据集、等预算、多种子的实验并记录 | 决定数据集与实验设置，检查日志 |
| 4 诊断与改方法 | 按排查清单查原因，把改进做成可对比的变体 | 判断改动是否合理，决定留哪个方法 |
| 5 回填论文 | 用回填脚本把实验记录写进中英文稿件，按你的风格排版与润色，做投稿前核查 | 写或改定核心论述，逐段审稿，对每个论断负责 |

## 常用说法

| 想做的事 | 对 Claude 说 | 你会得到 |
|---|---|---|
| 按五阶段推进自己的课题 | 「我的调研文献在 researched_papers，研究方向是某某，按 research-builder 的五阶段从对齐开始」 | 每个阶段的产物与检查点(概念表、系统骨架、baseline 忠实度记录、实验记录、诊断报告、回填稿件)，每阶段结束等你确认 |
| 按五阶段推进已有的稿件 | 「按 research-builder 的五阶段推进我这篇论文，位置在某某，先从对齐阶段读稿」 | 稿件的待办清单，逐阶段补齐的系统、baseline 与小规模实验，需要大规模算力时的交接文档 |
| 调研相关工作 | 「按 paper-survey 调研这个选题的 baseline」 | 下载好的论文源文件和一份 `survey.md` |
| 复现 baseline | 「忠实复现 researched_papers 里这几个方法，在同一协议下跟我的方法比」 | 每个 baseline 的实现、冒烟测试和忠实度记录 |
| 结果不好时排查 | 「诊断一下为什么输给某 baseline」 | 按 `diagnostic-playbook.md` 查出的原因和修改后的重跑结果 |
| 回填论文 | 「回填实验章，排主表，画实验图」 | 数字由回填脚本写入的中英文两稿 |
| 去 AI 腔 | 「按 writing-deai 把这段改一遍」 | 草稿、剩余痕迹清单和定稿 |
| 润色文档 | 「按我的讲法润色这个 Word，别造新词」 | 就地改好文字的文档和一份改动清单 |
| 写本子或 rebuttal | 「按 research-builder 写本子的研究内容」「写 rebuttal」 | 按 `knowledge/` 的结构写好的文字或可编译的 rebuttal |
| 画系统图 | 「按 paper-figure-pptx 画一张系统图」 | 可编辑的 PPT、矢量素材和渲染检查记录 |
| 投稿前检查 | 「投稿前把数字、术语、版面核一遍」 | 检查清单的结果和按清单改好的稿件 |

## 目录

| 路径 | 内容 |
|---|---|
| `SKILL.md` | 入口。文件分工、素材、编排、五阶段工作流、实验与架构纪律 |
| `writing-playbook.md` | 论文叙事、取舍、数字与术语、版面、表、图、交稿前检查 |
| `writing-deai.md` | 标点与句式的硬禁令，32 条 AI 腔模式，改写流程与声音匹配 |
| `diagnostic-playbook.md` | 方法低于 baseline、基线数值异常、作业崩溃时的排查顺序 |
| `knowledge/` | 讲故事的套路、论文骨架、benchmark 论文、基金本子、rebuttal、图的版式原型 |
| `templates/` | 中英镜像 LaTeX 骨架、数字回填脚本、rebuttal 模板 |
| `figure-style/` | 实验图模块、样例与渲染图，`tables/` 是实验表的宏与生成脚本 |
| `tools/` | `polish_check.py`、`audit_tex.py`、`docx_deai.py`、`build_docx.py`、`docx_layout_check.py`、交接文档模板 |
| `paper-survey/` | 调研 skill，安装时单独部署 |
| `paper-figure-pptx/` | 学术插图 skill、入门图标库与对象处理脚本，安装时单独部署 |
| `materials/` | 你自己的素材，除 README 外不进 git |
| `researched_papers/` | 调研投递夹，论文文件不进 git |
| `codex/` | Codex 版的同步脚本、自定义 prompt 与 AGENTS.md 片段 |
| `dist/` | claude.ai 网页版上传包与构建脚本 |

## Codex 与网页版

**Codex CLI。** 运行 `bash codex/sync_codex_skills.sh`，生成 `~/.codex/skills/` 下的三个 skill，旧版本先备份。Codex 没有子代理，需要并行的步骤改为按顺序执行。详见 [codex/README.md](codex/README.md)。

**claude.ai 网页版。** 在 Settings 的 Skills 页面上传 `dist/research-builder-web.zip`，需要打开代码执行。详见 [dist/README.md](dist/README.md)。

## 检查一下装好了

```bash
python3 tools/polish_check.py README.md                     # 去 AI 腔自检
python3 tools/audit_tex.py templates/latex-bilingual/sections_en/*.tex
python3 templates/latex-bilingual/check_mirror.py            # 中英镜像核对
python3 paper-figure-pptx/scripts/tests_native_objects.py    # PPT 原生对象测试
python3 tools/test_pptx_skill_install.py                     # 安装脚本测试
```

## 维护

一条规则只写在一处。写作规则进 `writing-playbook.md`，AI 腔模式进 `writing-deai.md`，排查经验进 `diagnostic-playbook.md`，流程进 `SKILL.md`，图表样式进 `figure-style/`，并删掉被新规则取代的旧规则。改完运行 `bash codex/sync_codex_skills.sh` 与 `bash dist/build_web_zip.sh`，让三个版本保持一致。

## 致谢与许可

本仓库以 MIT 许可发布，见 [LICENSE](LICENSE)。`writing-deai.md` 改编自 [blader/humanizer](https://github.com/blader/humanizer)(MIT，Siqi Chen)，其模式来自 Wikipedia 的 [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)，声明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。这些规则用来让文字准确、具体、读起来像作者本人写的，规避 AI 检测器不在设计目标之内。

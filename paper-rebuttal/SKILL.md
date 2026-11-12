---
name: paper-rebuttal
description: 在研究者主导下，辅助 OpenReview 式讨论期的审稿回复与修订稿，分对齐、实验、拟稿、修订稿、核对润色、打包六阶段，每阶段结束等研究者确认，发帖与上传由作者本人完成。提供手册、英文句式、中英对照回复工程、OpenReview Markdown 导出和全精度数字核对脚本，修订稿改动标红并按审稿人分色写页边或段末编号。Use when the user says 「写 rebuttal」「按 paper-rebuttal 回复审稿人」「讨论期回复」「OpenReview 评论」「导出 OpenReview 楼层」「修订稿标红」「页边批注」「核对回复里的数字」「催审稿人回复」「author response」「reply to reviewers」「rebuttal」「respond to reviews」「mark the revised PDF」「OpenReview comments」.
---

# paper-rebuttal

本技能辅助作者完成一轮审稿讨论，产出是可粘贴的回复文本、标注好的修订稿和核对记录。研究由研究者主导，回应什么、哪些结果写入、文字是否发出都由研究者决定。本技能负责起草、核对和排版，所有数字只来自真实的实验记录。发帖、上传和匿名镜像的更新由作者本人完成。

规则来自一轮 OpenReview 讨论期的实际工作，例子是虚构的 PairSift 任务，数字都是示意。

## 文件分工

| 文件 | 内容 | 何时读 |
|---|---|---|
| `SKILL.md` | 路由、输入、阶段与工具的对应 | 每次启动 |
| `playbook.md` | 二十节手册（第 0 到 19 节），从策略、读意见、实验排期到发帖和打包，第 18 节是定稿轮的行文与交付，第 19 节是回复发出之后的修改轮 | 每个阶段开始前读对应小节 |
| `phrases.md` | 回复各部分的英文句式，带槽位和虚构例子 | 拟稿时 |
| `kit/` | 中英对照回复的 LaTeX 工程、OpenReview 导出、修订稿标记样式、检查脚本和虚构示例，用法见 `kit/README.md` | 建工程和核对时 |

文字规则沿用 `research-builder` 技能，包括 `writing-deai.md`（第 0 节是研究者定的两段写作总则，回复与修订稿的每一句都适用）、`writing-playbook.md`（第 13 节是重跑与修订轮的数字规则和修订标记）和 `tools/polish_check.py`。安装后该技能在同级目录 `../research-builder/`，直接在仓库里使用时在上一级目录 `../`。

## 先判断是哪一种回复

| 情形 | 用什么 |
|---|---|
| 讨论期楼层制回复，可以补实验、可以上传修订稿（OpenReview 式） | 本技能全流程 |
| 篇幅固定的一次性回复，例如两页 PDF 的 author feedback | `research-builder` 的 `knowledge/rebuttal.md` 与 `templates/rebuttal/rebuttal_template.tex`，数字核对仍可用 `kit/scripts/` |
| 只需要核对回复里的数字或导出已有 LaTeX | 直接用 `kit/` 的对应脚本 |

## 开工前要齐的输入（缺则先问）

1. 审稿意见原文、评分和讨论期截止日期。
2. 目标会议的规则，包括能否上传修订稿、页数上限、匿名要求和生成式工具的声明要求。规则以官网和表单实测为准。
3. 论文源文件，审稿人已经能看到的补充材料与匿名仓库。
4. 实验记录的位置，以及研究者打算回应的方向和不打算做的事。

## 阶段

六个阶段的分工表在 `playbook.md` 第 0 节。每个阶段结束时交出可核验的产物并停下，研究者确认后再进入下一阶段。

| 阶段 | 读手册 | 用到的工具 |
|---|---|---|
| 0 对齐 | 第 0 到 2 节 | `kit/project/source/reviews.md` 存档原文并编号，`make -C project verify` 逐字核对 |
| 1 实验 | 第 3 到 5 节 | 运行记录的格式参考 `kit/example/runs.csv`，实验在服务器上跑 |
| 2 拟稿 | 第 6 到 8 节、第 10 节、`phrases.md` | `make -C project check`，`scripts/check_rounding.py`，`scripts/build_interval_map.py` |
| 3 修订稿 | 第 11 节、`writing-playbook.md` 第 13 节 | `kit/revision/revmark.sty`，`scripts/check_margin_tags.py` |
| 4 核对与润色 | 第 9 节、第 12、13 节 | `make -C project strict`，`scripts/check_glance_table.py`，`scripts/check_invariants.py`，`tools/polish_check.py` |
| 5 打包 | 第 14、15 节 | `scripts/build_deliverables.py` |
| 发出后的修改 | 第 18、19 节 | `scripts/tokdiff.py`、`scripts/sentcheck.py`、`make -C project strict`、`scripts/check_margin_tags.py` |

命令在 `kit/` 下运行。第一次使用时先跑 `make test` 和 `make demo`，确认本机的 Python 与 XeLaTeX 可用，然后按 `kit/README.md` 把 `kit/project/` 复制进论文仓库。不要在技能目录里写项目内容。

## 红线

动笔前读 `playbook.md` 第 1 节末尾的红线。数字能从落盘记录重算，种子事先固定并全部报告，原始记录不删不改，双盲期间不暴露身份，不写不属实的内容。审稿人问到的数字如实回答。

## 触发条件

- 「写 rebuttal」「回复审稿人」「讨论期回复」「把回复导出成 OpenReview 楼层」
- 「修订稿标红」「按审稿人分色写页边批注」
- 「核对回复里的数字」「区间对齐」「催审稿人回复」
- 「author response」「reply to reviewers」「mark the revised PDF」「OpenReview comments」

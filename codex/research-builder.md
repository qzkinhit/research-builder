# /research-builder （Codex 版）

把「我调研好的相关论文 + 研究方向 + 素材」变成能跑、忠实、诚实的研究产出。四类活是科研、论文写作与投稿前审校、改写润色、画图做 PPT。规则本体在 `~/.codex/skills/research-builder/`(由 `codex/sync_codex_skills.sh` 生成，没有就改成你的 clone 路径)，本文件只给 Codex 入口与顺序，不重复规则。

Codex 没有子进程，各阶段顺序做，或开多个 codex 会话并行。一个文件同一时间只让一个会话写。

## 先读哪个文件

| 要做的事 | 读 |
|---|---|
| 任何任务的流程、实验纪律、架构纪律 | `SKILL.md` |
| 写或改论文文字、表、图，润色，投稿前检查 | `writing-playbook.md` 与 `writing-deai.md` |
| 论文骨架、本子、rebuttal、讲故事套路、图的版式 | `knowledge/` |
| 中英镜像 LaTeX 骨架、数字回填、rebuttal 模板 | `templates/` |
| 方法低于 baseline、基线数值异常、作业崩溃 | `diagnostic-playbook.md` |
| 画实验图(折线、条形、雷达消融、动机图) | `figure-style/README.md`，模块 `figure-style/figstyle.py` |
| 出 Word 稿，跑检查脚本 | `tools/README.md` |
| 只剩大规模实验时的交接 | `tools/server_plan_template.md` |
| 写作、画图、做 PPT 的素材 | `materials/README.md` |

## 不读文件也必须守的几条

- 中英文都不用破折号、分号、花引号。说明性行文不用冒号，不拟人，不写元话术。32 条 AI 腔模式见 `writing-deai.md`。
- 只用素材里的锁定词，不造新术语。
- 数值只向实验记录对齐，不为前后一致而改数。论文不展示弱项，也不写不属实的内容，弱项写进给导师的内部报告。
- 实验都在服务器上跑。数字只经一个回填脚本进入中英文两稿。
- 系统(`src` 纯方法)与应用(`run_*` 薄壳)分离，baseline 对称镜像并产出同一 manifest。

## 科研五阶段(细则见 `SKILL.md`)

0. 对齐。读素材与调研论文，建概念表与锁定术语表。
1. 搭系统。`src` 纯方法加 `run_*` 薄壳加统一 manifest，先跑通最小全流程。
2. 忠实复现 baseline。按原论文实现，所有方法共用一条校准规则，过 T1、T2、T3 三层忠实度认证，三层都不过的不进对照表。
3. 实验。公认数据集与 baseline，质量波动池，等预算，三隔离，至少 3 个种子。
4. 诊断与改方法。先按 `diagnostic-playbook.md` 查原因并重跑，再取百家所长，有效才留。
5. 回填论文。先读 `writing-playbook.md`，一种语言一个 tex，交稿前跑完其第 9 节的检查。

## 改进现有论文

给一篇半成品论文的位置，推到除大规模实验外全部完成且可跑。七步与 `runall.sh` 的四档见 `SKILL.md`「改进现有论文」。动仓库前确认没有并发会话在改同一仓库。

## 画图与润色

- 实验图沿用 `figure-style/` 的风格。先读 `figure-style/README.md`，把 `figure-style/figstyle.py` 复制到论文绘图脚本旁边，从 `figure-style/examples/` 挑最接近的样例改数据。
- 本子图、动机图与系统图用独立的 `paper-figure-pptx` 技能，版式原型见 `knowledge/figure-archetypes.md`，规则都在该技能里。
- 润色 PPT 或 Word 时就地改文字，不动版式。讲故事方式照 `knowledge/storytelling.md`，按 `writing-deai.md` 第 3 节的流程改写，改完跑 `tools/polish_check.py` 到零红线，并列出改了哪些、为什么。

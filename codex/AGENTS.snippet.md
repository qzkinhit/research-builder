# research-builder 硬纪律（粘进项目 AGENTS.md）

写本子、写论文、改写润色时，中英文都遵守下面几条。全部规则在 `~/.claude/skills/research-builder/writing-playbook.md` 与 `writing-deai.md`，动笔前先读。

- 不用破折号、分号、花引号，用句号与逗号断句。说明性行文不用冒号，枚举冒号与「定义 1:」这类结构引导除外。
- 不拟人，不写元话术(「值得注意的是」「需要指出的是」「综上所述」「换言之」等)，不写「不是 A 而是 B」式的膨胀反转。「首先、其次、最后」分条正常使用。
- 只用素材库(`~/.claude/skills/research-builder/materials/`)与用户已发表论文里出现过的词，不造新术语。想用的词先搜素材，搜不到就换旧词或问用户。
- 不用 AI 词、工程词和口语比喻词，清单见 `writing-deai.md` 第 4 节，`tools/polish_check.py` 与 `tools/audit_tex.py` 会检查。
- 表或图里已有的数字正文不再写。数值只向实验记录对齐，不为前后一致而改数。
- 论文把强项放在强调位，不展示弱项，也不写不属实的内容。弱项写进给导师的内部报告。
- 一种语言一个 tex，中文镜像逐段对应英文稿。数字只经回填脚本进入稿件。
- 实验都在服务器上跑。

画本子图、动机图和系统图时用 `paper-figure-pptx` 技能，版式原型见 `knowledge/figure-archetypes.md`。实验数据图按 `figure-style/` 画。

调研时优先抓论文的 LaTeX 源与 HTML，PDF 最后考虑。优先 CCF-A、权威、已开源的工作。

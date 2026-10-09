# 中英镜像论文骨架

一种语言一个入口文件，两稿共用导言、label、定理计数和数字宏。英文稿是提交版，中文稿只做内容镜像，逐段对应。逐节怎么写见 `knowledge/paper-anatomy.md`。

## 文件

| 文件 | 内容 |
|---|---|
| `main_en.tex`、`main_zh.tex` | 两个入口。中文入口先定义中文的定理名，再读共享导言，所以两稿的编号一致 |
| `preamble_shared.tex` | 宏包、定理与 Finding 环境、`\sys`、`\num` 数字宏、红色占位宏、记号 |
| `table_macros.tex` | 表格配色与宏，正本在 `figure-style/tables/table_macros.tex` |
| `numbers_en.tex`、`numbers_zh.tex` | 由 `templates/backfill/backfill.py` 生成，不手改 |
| `sections_en/`、`sections_zh/` | 逐节对应的章节文件，文件名相同 |
| `check_mirror.py` | 比对两稿的 label、引用、文献键、数字宏键、环境数和标题数 |
| `BACKFILL.md` | 回填脚本输出的记录，列出每个数字的值、状态和来源 |

## 用法

1. 把整个目录复制成新论文仓库的论文目录，`figures/` 放图。
2. 第一行注释里的编译命令换成投稿模板，`\documentclass` 和样式文件按刊物替换。
3. 正文里每个实测数字写成 `\num{键}`。键没有值时印成红色的 `[键]`，交稿前必须清零。
4. 主表的表体放在 `%%BEGIN-MAINROWS` 与 `%%END-MAINROWS` 之间，由回填脚本写入。
5. 每次改完跑一遍下面的命令。

```bash
python ../backfill/backfill.py --registry registry.json --paper-dir .
pdflatex main_en && bibtex main_en && pdflatex main_en && pdflatex main_en
xelatex main_zh && bibtex main_zh && xelatex main_zh && xelatex main_zh
python check_mirror.py
python ../../tools/audit_tex.py sections_en/*.tex
```

`\num` 与 siunitx 的同名命令冲突。要用 siunitx 时，把 `preamble_shared.tex` 里的 `\num` 改名，例如 `\val`，并同步改回填脚本输出的宏名。

# researched_papers · 调研的相关工作

把调研好的相关工作放进这个文件夹，然后在 Claude Code 里说「按 research-builder 启动」。还没调研时，说「按 paper-survey 调研这个选题的 baseline」，它会把 arXiv 的 LaTeX 源与 HTML 下载到这里。

skill 会做三件事。

1. 读这里的每篇论文(优先读 LaTeX 源与 HTML)，产出「借鉴它什么、比它强在哪」的结构化摘要。
2. 把超越点对应的方法做成忠实 baseline，把借鉴点做成改进变体。
3. 配合 `../materials/` 和 `../knowledge/` 搭系统、跑实验、回填论文。

约定如下。

- 一篇一个文件或文件夹，名字能认出方法名最好。
- 可以放一个 `notes.md`，写你对每篇的定位(要不要当 baseline、借鉴哪一点)。
- 这里的论文文件默认不进 git。

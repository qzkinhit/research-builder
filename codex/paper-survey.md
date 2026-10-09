# /paper-survey （Codex 版）

LaTeX/HTML 优先的论文调研工作流。用户指定研究内容，去找齐该选题需要的 baseline 与相关工作，优先抓 arXiv LaTeX 源与 ar5iv HTML(模型读 PDF 不准)，按 CCF-A/权威/已开源 筛选，下载进 `researched_papers/`，产出 `survey.md`。

Codex 适配：没有子进程，**各阶段顺序做**(或开多个 codex 会话手动并行)。

## 两种模式（先问清）
- A 只调研：产出 `researched_papers/` 下载件 + `survey.md`，停。
- B 调研+写：A 完了接力 `/research-builder` 写论文，目标 ICLR oral 水平。

## 原则
- **LaTeX/HTML 优先，PDF 最后考虑**。用 `~/.claude/skills/research-builder/paper-survey/tools/fetch_arxiv.sh`。
- **广撒网严筛选**：优先 CCF-A(NeurIPS/ICML/ICLR/ACL/CVPR/SIGMOD/VLDB 等)、高引权威 arXiv、**已开源**(有 GitHub)。
- 每篇标 借鉴点/超越点/能否当 baseline/代码链接。不臆造，全部基于真抓到的内容。
- 对标 ICLR oral：覆盖最强对手与最新进展，不滥竽充数弱 baseline。

## 工作流
1. 拆题：选题拆子方向 + 必需 baseline 类别。
2. 搜：每个子方向搜候选(标题/arXiv id/venue/年份/引用量级/是否开源/一句话方法)，宁多勿漏。
3. 筛排：去重，按 CCF-A/开源/相关性 排序，定精读名单 8 到 15 篇。
4. 抓取(LaTeX/HTML 优先)：`bash fetch_arxiv.sh <id> researched_papers` 拿 LaTeX 源与 ar5iv HTML，不下 PDF。非 arXiv 的论文用网页抓 HTML。
5. 精读抽取：逐篇读 LaTeX/HTML，出卡片(方法/公式/实验/能否当 baseline/借鉴点/超越点/代码/复现难度)。
6. 汇总 `survey.md`：按子方向组织 + baseline 短名单(标 CCF-A/开源) + 空白点分析。
7. (仅模式 B) 接力 `/research-builder` 写论文。

## fetch_arxiv.sh
```bash
bash ~/.claude/skills/research-builder/paper-survey/tools/fetch_arxiv.sh <arxiv_id|url> researched_papers
# 默认只下 LaTeX 源与 ar5iv HTML，加 --pdf 才下 PDF
```

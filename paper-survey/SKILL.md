---
name: paper-survey
description: LaTeX/HTML 优先的论文调研工作流。用户指定研究内容，多子进程并行去搜该选题需要的 baseline 与相关工作，优先抓 arXiv LaTeX 源与 HTML(因为模型读 PDF 不准)，按 CCF-A/权威/已开源 筛选排序，下载进 researched_papers/，产出调研报告。两种模式，(A)只调研出报告，(B)调研完接力 research-builder 写论文(目标 ICLR oral 水平)。Use when the user says 「帮我调研这个选题的 baseline 和相关工作」「广泛调研这篇论文需要的相关文章」「优先 latex/html 下载论文」「调研完直接帮我写论文」「只调研不写」「survey related work for my paper」.
---

# paper-survey

用户**指定要做的研究内容**，本 skill 多子进程并行去**找齐这篇论文需要的 baseline 与相关工作**，优先抓 LaTeX 源与 HTML 下载，筛出 CCF-A/权威/已开源 的，产出调研报告，并可接力 [[research-builder]] 写成论文。

核心原则：
- **LaTeX/HTML 优先，PDF 最后考虑**。模型读 arXiv LaTeX 源与 ar5iv HTML 远准于 PDF。只有都拿不到才下 PDF。用 `tools/fetch_arxiv.sh`。
- **广撒网 + 严筛选**。多搜，但优先留 **CCF-A 会议/期刊、被广泛引用的权威 arXiv、且已开源(有 GitHub)** 的。
- **结论导向**。每篇都标"我们借鉴它什么 / 我们要比它强在哪 / 能否当 baseline / 有无代码"。
- **目标对标 ICLR oral**：调研要足够广足够深，覆盖最强的对手与最新进展，不能只找弱 baseline。

## 两种模式（开工先问清是哪种）
- **模式 A · 只调研**：产出 `researched_papers/` 里的下载件 + `survey.md` 调研报告，停在这里。
- **模式 B · 调研 + 写论文**：A 做完后，自动接力 `research-builder`(把 `researched_papers/` 当输入)写论文，目标 ICLR oral 水平。

## 开工前要齐
1. **研究内容与选题**。要写的这篇论文做什么、核心论点、属于哪条研究线(如数据质量、数据选择)。
2. **目标产出**：模式 A 还是 B。
3. **存放位置**。下载与报告放哪个仓库的 `researched_papers/`(默认配合 research-builder 的投递夹)。
4. **规模**：要多广(默认 ≥ 20 篇候选，留 8 到 15 篇精读)。

## 工作流（多子进程并行）

主 agent 当编排者，能并行的派 subagent 并行，结论上浮。

### Phase 1 · 拆题
把选题拆成若干子方向和必需的 **baseline 类别**(例如数据选择课题的分布匹配类、影响力类、质量过滤类、融合类)。列出要覆盖的最强对手与最新工作。

### Phase 2 · 搜（并行 slice）
**按模态/任务切成若干 slice，每个 slice 一个 subagent 并行搜**(实战证明 10 个并行 slice 很顺手)。给每个 subagent 同一段共享上下文(选题、我们的定位、要找哪类对手)再加它负责的 slice。各回一张候选表，每篇用这套**固定字段**：
```
{title, arxiv_id, venue, year, open_source(bool), code_url, why_relevant,
 method_type, is_baseline(可否当我们baseline), borrow(借鉴点), surpass(超越点)}
```
**arxiv_id 必须核验真实存在**(能 resolve 到 arxiv.org/abs/<id>)，**绝不臆造 id 或引用**。多搜，宁多勿漏。

> 并行规模大时，把本阶段写成一个 Workflow，每个 slice 一个 agent 并行，用 schema 约束输出字段。

### Phase 3 · 筛与排
合并去重，按优先级排序并标注：
- 优先 **CCF-A**(NeurIPS/ICML/ICLR/ACL/CVPR/SIGMOD/VLDB 等) 与高引权威 arXiv。
- 优先 **已开源**(给出 repo 链接)。
- 标"当 baseline / 当相关工作 / 当思路来源"。
- 砍掉弱、旧、无关、无法复现的。给出最终精读名单(8 到 15 篇)。

### Phase 4 · 抓取（并行，LaTeX/HTML 优先）
对名单里每篇 arXiv 论文，并行跑 `bash tools/fetch_arxiv.sh <id> <researched_papers_dir>`，拿 **LaTeX 源 + ar5iv HTML**(不下 PDF)。非 arXiv 的用 WebFetch 抓 HTML/出版社页。下载件落到 `researched_papers/<id>/`。

### Phase 5 · 精读抽取（并行）
**每篇派一个 subagent** 读其 LaTeX/HTML，回一份结构化卡片：方法要点、关键公式/设定、实验与指标、**是否可当我们的 baseline、借鉴点、超越点**、代码链接、复现难度。读 LaTeX/HTML，不读 PDF。

### Phase 6 · 汇总调研报告
产出 `survey.md`：按子方向组织，每篇给卡片摘要 + 借鉴/超越标注，附 **baseline 短名单**(标 CCF-A/开源) 与 **空白点分析**(我们的机会)。这份报告同时是论文相关工作章与实验 baseline 选型的依据。

### Phase 7 · 接力写论文（仅模式 B）
调用 `research-builder`，把 `researched_papers/` 与 `survey.md` 当输入，按其五阶段写论文，目标 **ICLR oral 水平**(强动机、广对比、诚实强势的结果、扎实消融)。模式 A 到 Phase 6 即止。

## 硬纪律
- LaTeX/HTML 优先，PDF 只在拿不到前两者时下载。下载统一进 `researched_papers/`。
- 只收 CCF-A/权威/可复现/优先开源 的，弱 baseline 不滥竽充数。
- 每篇必标 借鉴点/超越点/能否当 baseline/代码链接。
- 不臆造引用与结论，所有判断基于真实抓到的 LaTeX/HTML 内容。

## 触发条件
- 「调研这个选题的 baseline 和相关工作」「广泛调研这篇论文的相关文章」
- 「优先 latex/html 下载这些论文」「下载下来精读」
- 「只调研出报告」(模式 A) /「调研完直接写论文」(模式 B)
- 「survey related work / find baselines for my paper」

> 配套工具 `tools/fetch_arxiv.sh`。下游写作交给 `research-builder`(同一 `researched_papers/` 投递夹)。

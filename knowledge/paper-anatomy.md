# 论文骨架

本文件把一篇实证型方法论文从标题到附录逐节拆开，每节给出要完成的任务、段落顺序和可套用的中英文句式。它从数据管理与机器学习顶会和 IEEE 汇刊上已发表或在投的系统论文中归纳而来，适用于「提出一个方法或系统，用理论和实验证明它更好」这一类论文。benchmark 类论文另见 `benchmark-papers.md`。

句式框架里的尖括号是要替换的槽位。文中的贯穿例子是虚构的，用来演示句式怎样落到具体内容上。

**贯穿例子。** 系统名记为 `\sys{}`。任务是在人工标注预算有限时检测表格中的重复记录。候选记录对的数量随表的规模平方增长，人工只能确认其中很小一部分，问题是把有限的标注花在哪些候选对上。

## 0. 动笔前

1. 查清投稿的页数上限、是否双盲、参考文献是否计入页数、能否放补充材料。按上限规划每节的篇幅。
2. 建概念表。每个概念对应唯一的中文名、英文名和记号，写进 `docs/CONCEPTS.md`，全文只用表内名。
3. 写一句话核心论点，形式是「在 <条件> 下，<方法> 以 <代价> 达到 <效果>」。摘要末句、第一条贡献、第一条 Finding 都从这句展开。
4. 定贯穿例子。选一个公开数据集的小切片，它要能同时引出全部挑战。

## 1. 标题与摘要

**标题。** 写成「系统名: 一句点明主要结果的话」，不超过两行。数据类型和领域的关键词同时出现在标题和关键词里。

> PairSift: Budgeted Duplicate Detection that Matches Full Labeling at a Twentieth of the Cost

**摘要。** 六到八句，每句对应正文一处内容。

| 句 | 任务 | 英文框架 |
|---|---|---|
| 1 | 对象与背景 | `<Object> is <role> in <setting>, where <property that creates the problem>.` |
| 2 | 难点 | `<Naive approach> does not show that <desired outcome>, so <decision> should be judged by <right criterion> rather than by <wrong criterion>.` |
| 3 | 方法 | `We present \sys{}, which <step 1>, <step 2>, and <step 3>.` |
| 4 | 理论 | `We prove that, under <condition>, <guarantee>.` |
| 5 | 主结果 | `On <N> datasets, \sys{} <metric> <number>, against <number> for <strongest baseline> among <M> baselines.` |
| 6 | 泛化或附加结果 | `The same <mechanism> carries over to <second setting>, where <result>.` |

- 摘要里的数据集数、baseline 数与 Setup 一致。
- 最强的事实放在第 5 或第 6 句，这是摘要末尾的强调位。
- 不写「本文首次」「大量实验表明」这类没有内容的句子，直接给数字。

## 2. 引言

引言分五步，按顺序写。页数紧张的会议稿不设小标题，用 `\paragraph{}` 作段首标题，因为小标题在页数受限时多占三行。

### 2.1 代价

第一段用一个真实事故或一个调查数字开头，说明问题的规模与代价，末句把问题收成一个开放问题。

> `<Problem> is pervasive and costly~\cite{...}. In <year>, <concrete incident with a number>~\cite{...}. The impact is compounded in <setting>, where <survey statistic>~\cite{...}. How to <goal> when only <constraint> therefore remains an open problem.`

> `<问题>普遍存在且代价高昂~\cite{...}。<年份>，<带数字的具体事故>~\cite{...}。在 <场景> 中这一代价进一步放大，<调查数字>~\cite{...}。如何在只有 <约束> 时 <目标>，仍是一个开放问题。`

### 2.2 视角转换

第二段说明现有目标为什么不够，提出新的视角，并引入一到两个命名的性质，每个性质用一句话给出直观定义。性质之间的张力是后文的主线。

> `Yet <traditional objective> does not guarantee <downstream goal>, as <reason>~\cite{...}. The objective must therefore shift from <old> to <new>. Under this view, we identify two complementary properties that jointly govern <outcome>. \emph{<Property A>} measures <...>. In contrast, \emph{<Property B>} measures <...>. <Operation 1> raises A but lowers B, while <operation 2> does the opposite. Figure~\ref{fig:motivation} and the examples below make this trade-off concrete on a real <task>.`

### 2.3 实例与 Observation

用 Example 环境在一个真实数据集上演示问题，给出数据规模、任务、模型、划分和搜索空间，再列出编号的 Observation。Observation 这个名字与实验章的 Finding 区分开。

```latex
\begin{example}[<短标题>]\label{ex:motivation}
We illustrate with a subset of the public <Dataset>~\cite{...}. <What each row is, what the task is,
which model>. <Split and sizes>. For each of the <K> <units>, we consider <m> actions, which yields a
space of size $m^{K}$. <How the space was sampled and what Figure 1(a) shows>.
\end{example}

\textbf{Observations.} Two observations follow from this space.
\textbf{(1) <一句话论断>.} <证据，带数字>.
\textbf{(2) <一句话论断>.} <证据，带数字>.
```

第二个 Example 常用来比较几种极端策略与本文方法，每种策略给出两个性质的取值、下游效果和代价，最后写本文方法的数字。

> 贯穿例子。在一个 2,000 条记录的商品表上，候选对有约两百万个，人工预算是 1,000 对。全部标注候选对中相似度最高的 1,000 对时，召回率停在 0.61，因为高相似的候选对大多是同一批重复记录的不同组合。按簇覆盖分配同样的 1,000 对时召回率达到 0.83。(示意数字)

### 2.4 挑战

先用一个问句承上启下，再列编号的挑战。每条挑战是加粗的一句论断，随后给出原因、引用例子，并点名现有方法族为什么解决不了。困难段只讲困难，本文的做法留到贡献段。

> `The observations above suggest that <requirement>. Why, then, have existing methods not addressed <problem>? We trace this to three challenges.`

> `\textbf{(1) <Benefit is non-intuitive and task-dependent>.} <Why>. As Example~\ref{ex:motivation} shows, <evidence>. Existing <family A>~\cite{...} and <family B>~\cite{...} lack <capability>.`

> `上述观察说明 <要求>。那么现有方法为何没有解决 <问题>?原因可归结为三项挑战。`

挑战的数目与贡献的数目对应，常见是三条。典型的三类挑战是收益难以预先判断、决策空间组合爆炸、学到的决策难以迁移。

### 2.5 贡献

> `To address these shortcomings, we propose \sys{}, <one-line definition>, with the following contributions.`

- 每条贡献以加粗的名称开头，写做了什么、为什么有效，并指向对应的定理或小节。
- 第一条贡献承载核心论点，是强调位。
- 最后一条贡献讲实验，写数据集数、baseline 数、最强的数字和一个反直觉的发现。

> `(4) \textbf{Results.} We evaluate \sys{} on <N> real-world datasets against <M> baselines. \sys{} <headline result>, using <cost>. <One counter-intuitive finding>.`

## 3. 相关工作

- 按方法族组织，每段以加粗的族名开头，写代表方法和它缺少的能力。
- 段落顺序与能力表的族顺序、主表的行分组顺序相同。
- 末尾放能力表，每个对比方法占一行，能力列选能把本文方法区分出来的性质。表的写法见 `../figure-style/tables/README.md`。
- 每个族的最后一句写它缺什么，不写「与本文不同」。

> `\textbf{Rule-based methods.} <Representative methods>~\cite{...} <what they do>. They <what they cannot do>, so <consequence for the problem>.`

## 4. 问题定义

- 先定义输入对象，再定义动作或决策，再定义策略，最后给出优化问题。每个定义后跟一个用贯穿例子写的 Example。
- 优化问题写成一个带预算约束的目标，变量、约束和目标各占一行公式。
- 给一个复杂度结果说明为什么需要近似或学习，例如在一般代价下判定版本是 NP 完全的。证明放附录，正文写一句话说明它的含义。

```latex
\begin{definition}[<名称>]\label{def:...}
Given <input>, a <object> is <definition>.
\end{definition}
\begin{example}\label{ex:def-...}
In Example~\ref{ex:motivation}, <the defined object on the running example>.
\end{example}
```

## 5. 方法

- 方法章跟着系统图走。开头一段对照系统图概述全部步骤，然后每步一个小节，标题写成「Step k: 名称」或直接写步骤名。
- 每个小节的顺序是目的(一句话) → 定义 → 算法 → 保证 → 复杂度。更细的话题用加粗的段首短语引出。
- 算法框只放决策逻辑，输入输出用 `Input` 和 `Output`，阶段名用斜体。
- 每一步用贯穿例子演示一次，读者能看出输入怎样变成输出。
- 实现不满足定理的全部前提时，定理写成条件保证，方法节平实地写实际做法。

> `\sys{} consists of three steps (Figure~\ref{fig:framework}). Step~1 <...>. Step~2 <...>. Step~3 <...>, and its output feeds back into Step~1 for the next round.`

## 6. 定理与证明

- 核心论点由带完整陈述的定理或命题支撑。名字在正文和附录逐字一致。
- 方法的核心贡献是「不低于每个 baseline」时，把方法设计成可证明如此，例如把每个 baseline 纳入方法自身的候选集合。
- 定理写完先让一个批判者逐条找反例和边界情形，再收紧前提，留修订记录在 `docs/`。
- 附录里的重要定理在正文被索引，并用一句话说明内容，否则没人会读到。
- 由理论导出可检验的预测，例如收益随某个量线性缩放，并在实验里验证。

## 7. 实验

开头一段列出研究问题并对应到贡献，写明方法族数、baseline 数和数据集数。之后只有 Setup 和 Findings and Results 两个小节。

> `We answer three research questions. RQ1: <...> (Contribution 1). RQ2: <...>. RQ3: <...>. Findings~1 and~2 address RQ1 and RQ2, Finding~3 explains <...>, and Finding~4 addresses RQ3.`

### 7.1 Setup

用编号加粗的段首短语分三到四段。

- **(1) Datasets.** 首句说数据集表列出了各数据集的任务、错误类型与规模，然后交代数据从哪来、错误从哪来。人工注入的错误只写注入到哪些数据集、怎么注入，不写种子和运行配对这类工程说法。
- **(2) Baselines.** 一小段。说明与能力表中的全部方法比较、所有方法从什么数据学习、本文方法有何不同。
- **(3) Metrics.** 每个指标只出现一次，写成「全称(加粗缩写)」并带行内公式。
- **(4) Studies.** 可选。列出主比较之外的扫描、消融和机制研究分别在哪张图或附录。

### 7.2 Findings and Results

- 每条 Finding 是一句具体的强论断，用定理式环境或加粗句开头，证据紧跟其后。每个研究问题一到两条，全文七条左右。
- 证据段先给相对主表的结论(相对提升、倍数)，再给机理解释，最后给反例或边界并说明原因。
- 消融写成若干个「Variant k: 名称(去掉了什么)」，每个变体说明它在哪些数据上退化、为什么。
- 效率单独一条 Finding，说明开销主要来自哪一步，以及它随规模怎样增长。
- 新实验或规模扩展并入已有 Finding，不另起一条。

```latex
\begin{finding}\label{find:main}
\sys{} <strong claim with the comparison it wins>.
\end{finding}
<Evidence: relative gain over the strongest baseline, computed from Table~\ref{tab:main}>.
<Mechanism: why this happens, tied to Observation (k) of the introduction>.
<Boundary: the one dataset where it does not hold and the measured reason>.
```

贯穿例子里的一条 Finding 可以写成「在全部八个数据集上，\sys{} 以五分之一的标注达到全量标注 98% 以上的召回率」，证据段给出它与最强 baseline 的相对差距，机理段回到引言的 Observation (2)。

## 8. 结论

- 从实验事实起手，写本文证明了什么，然后写方法的适用条件和下一步。
- 不复述数字，不逐字重复摘要，不写「未来前景广阔」这类送别段。

## 9. 附录

| 部分 | 内容 |
|---|---|
| 证明 | 每个定理一节，标题与正文定理同名，开头一句话复述结论 |
| 参数表 | 全部超参数、划分、种子数和硬件，正文不写这些 |
| 补充结果 | 正文放不下的分解、扫描和全部种子的结果 |
| baseline 适配 | 每个 baseline 的实现来源、适配方式和与原文协议的差异 |
| 复现说明 | 代码与数据的位置、运行命令，会议要求时写 Reproducibility Statement |

## 10. 不同刊物的差异

| 类型 | 典型做法 |
|---|---|
| 数据库顶会长文(双栏) | 引言含 Example 环境与 Observation，实验用编号的 Finding 小节，系统图横跨双栏 |
| 机器学习顶会(单栏) | 引言用 `\paragraph{}`，理论与附录占比大，正文末尾有伦理与复现声明 |
| IEEE 汇刊(双栏) | 带关键词，Finding 用定理式环境，页数严格，部分刊物不允许用补充材料放证明 |

## 11. 双语稿与数字

- 一种语言一个入口文件，两稿共用导言、label、定理计数和数字宏，模板见 `../templates/latex-bilingual/`。
- 每个实测数字是一个宏，由回填脚本从实验记录写入，模板见 `../templates/backfill/`。
- 待回填的位置用红色宏预填，交稿前清零。

# 审稿回复的写法

本文件归纳数据库与机器学习顶会审稿回复(rebuttal、author feedback、revision plan)的结构和句式。可编译的模板在 `../templates/rebuttal/rebuttal_template.tex`。

## 1. 版面结构

1. 一段致谢加总述。说明各审稿人的共同肯定，给出审稿人与颜色的对应，说明新增实验放在哪里(例如匿名仓库)。
2. 一个灰底框的 General Response。多位审稿人共同提出的问题在这里统一回答，每条标注它回应了哪些编号。
3. 按审稿人分块。每块以带颜色的审稿人标签开头，每条意见一个编号标签，沿用审稿表里的编号，例如 `#R1O1` 表示审稿人 1 的第 1 条主要意见，`#R1M1` 表示该审稿人的第 1 条次要意见。
4. 至多一张新结果表，放各审稿人都关心的新增实验。
5. 末尾列出本回复新增的参考文献，正文里沿用原稿的引用编号。

两页上限时字号可以缩小到 8.8 pt 左右，但不改页边距。

## 2. 每条回复的写法

每条回复的第一句直接回答，后面给证据，最后写修订动作。

| 意见类型 | 第一句怎么写 | 后面跟什么 |
|---|---|---|
| 审稿人说得对 | `You are right.` 或 `The count discrepancy is correct.` | 承认的范围、修正后的表述(例如把定理的一部分改成带明确前提的命题)、修订位置 |
| 审稿人误读 | 直接陈述正确的事实，例如 `Finding 1 and Finding 3 measure different objects.` | 两者各自测什么、为什么不矛盾、修订时如何避免误读 |
| 要求新实验 | 先给新结果的结论，结论里的头条数字加粗 | 实验设置一句话、数字、它说明了什么 |
| 要求新 baseline | `We reproduced <method> (<venue year>) on <datasets>.` 加结论 | 逐数据集对比、成本对比 |
| 表述与排版问题 | `These are presentation issues, and we accept every one.` | 一句话列完全部修改 |
| 已被别处回答 | `Addressed in the General Response and #R3O3.` | 不重复 |

## 3. 原则

- 每条都给可核验的事实。数字来自实验记录，新实验的代码和结果放进匿名仓库并在第一段说明。
- 承认错误时说清改了什么，同时说明结论是否受影响。例如更正两个过期的表格数值后，说明两者仍高于对照。
- 收窄论断时写清新的适用范围，不写泛泛的道歉。
- 交叉引用其他审稿人的条目，避免重复。用审稿人颜色的编号标签指过去。
- 修订承诺要具体到节、图、表或定义的编号。
- 不写「我们相信」「我们希望」这类没有信息量的句子，不与审稿人争论措辞。
- 回复里的术语与原稿一致，原稿有错的术语在回复里说明将统一成哪个。

## 4. 常用句式

> `We thank the reviewers for their careful reading. All three find the approach novel. Responses below are coded by reviewer: Reviewer 1 = blue, Reviewer 2 = green, Reviewer 3 = purple.`

> `\textit{<Topic>} (for #R1O5, #R3O5). <Direct answer>. <Evidence>. We rewrite <section> and <appendix>, and the repository is already corrected.`

> `Parts <i> and <ii> hold unconditionally and remain in Theorem <k>. Part <iii> needs <condition>, so we move it to a separate proposition that states <assumption 1> and <assumption 2> explicitly.`

> `The difference reflects <quantity>, which <our measure> captures, and we narrow the claim to <scope>.`

## 5. 交稿前

- 每条意见都有对应编号的回复，没有遗漏。用脚本数一遍原意见编号与回复标签。
- 回复里的每个数字能在仓库的结果文件里找到。
- 承诺的修订在修订稿里全部兑现，修订稿交稿时逐条核对。
- 跑 `../tools/polish_check.py` 检查标点与句式。

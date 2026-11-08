# 回复句式

本文件给出讨论期回复各部分的英文句式。尖括号是要替换的槽位，例子沿用 `playbook.md` 的虚构系统 PairSift，数字都是示意。句式只定结构，数字和论断由研究者按实验记录确认。结构和语气的规则在 `playbook.md` 第 7、8、10、14 节，这里不重复。可直接改用的跟帖与催复文件在 `kit/project/templates/`。

## 1. 公共回复的第 1 楼

写给 AC 和全体审稿人。"All requested experiments are finished" 只在逐项核对过之后写。

```text
Our thanks go to the <number> reviewers for their detailed feedback. All requested experiments are finished and reported here.

<Two or three sentences on what the paper shows, with numbers.>

<Number> questions recur across the reviews, <question 1>, <question 2> and <question 3>, and the sections below take them in turn.

A new PDF will follow before the discussion closes. Red text marks each substantive edit, with the number of the related comment beside it in the right margin, using <color 1> for <R1>, <color 2> for <R2> and <color 3> for <R3>.

**<Topic 1 as a result sentence>.** <Evidence and Table G1.>
```

> 例子。"Our thanks go to the three reviewers for their detailed feedback. All requested experiments are finished and reported here. The choice of candidate pairs that receive labels determines recall. Adding cluster coverage to BlockFirst reduces its missed duplicate clusters from 31 to 12, and threshold tuning alone leaves that count unchanged."

## 2. 公共回复的主题段与末楼

按主题写，表按块编号 G1、G2，末楼总述修订位置。

```text
**<Topic as a result sentence>.** <What was run, in one plain sentence.> <Numbers and how they are counted.>

Table G<k>. <What the table compares, under which budget, and over which runs.>

In the revision, <what changed> (<Section and Table>), <what changed> (<Section and Table>), and <what moved> (<Appendix Table>).

Please tell us if anything remains unclear.
```

## 3. 审稿人的第 1 楼开头

致谢取自审稿人自己写的优点或摘要，关切用中性的话概括，随后接一览表。

```text
We are grateful for <specific point the reviewer praised>. Three issues stand out, <concern 1> (W1), <concern 2> (W2), and <concern 3> (Q3). Replies follow point by point, and the end of each reply gives the corresponding place in the revision.
```

> 例子。"We are grateful for the remark that the evaluation measures downstream recall over a broad set of baselines. Three issues stand out, the separation of the gain from seed variance (W1), the sufficiency of a similarity baseline at larger budgets (W2), and the effect of class imbalance on Parcels (Q3). Replies follow point by point, and the end of each reply gives the corresponding place in the revision."

## 4. 回答单元

一个单元五段，标签、复述、论点、证据、修订句。同义的 W 与 Q 合并。

```text
**<W1 and Q1>, <short topic>.** <One sentence restating the reviewer's point in our own words.> **<Direct answer with the headline number.>** <Numbers, table, and how they are counted.> <At most two sentences of reason.> In the revision, <what changed> (<Section and Table>, margin note <R1-W1a>).
```

论点句按问题类型选开头。

| 问题类型 | 论点句的写法 |
|---|---|
| 是否问题 | `Yes, <result with number>.` 或 `No, <result with number>.` |
| 计数问题 | `<Count> of the <total> <units> <property>.` |
| 对照或消融 | `<Variant A> changes <metric> by <number> relative to <variant B> ([<low>, <high>]).` |
| 新基线 | `We ran <method> on <datasets> under the same budget, and <result with number>.` |
| 更大范围的实验 | `<Result with number>, on <new range>.` 随后写结论不成立的区间 |
| 事实更正 | `Section <k> now states <corrected statement>.` 随后写查了什么 |
| 澄清 | `We checked <what>, and <measured result>.` |
| 表述问题 | `The revision makes these changes, <change 1>, <change 2> and <change 3>.` |
| 公共回复已答 | `Table G<k> of our general comment reports <result>.` 随后写这位审稿人特有的部分 |

> 例子。"**W1 and Q1, stability across seeds.** The request is for multi-seed averages with paired intervals. **PairSift leads TopSim on seven of the eight tables over five seeds, with a mean gain of 4.2 F1 points ([2.1, 6.3]).** TopSim is 0.4 points higher on Recipes. In the revision, the five-seed averages with intervals are in Table 1 (Section 4.2, margin note R1-W1a), and Appendix Table 12 keeps Table 1 of the submission."

收尾只用下面一句，放在每位审稿人的最后一楼。

```text
Please tell us if anything remains unclear.
```

## 5. 一览表

放在开头段与第一个回答单元之间，每位审稿人 4 到 6 行。用工具包时写成列格式为 `lll` 的 `rtable`。

```text
Results per comment, with the matching place in the revised PDF.

| Comment | Finding | Location (margin note) |
|---|---|---|
| <W1, Q1, short topic> | **<headline number>** <what it measures> | <Table and Section> (<R1-W1a>) |
| <Q2, short topic> | <result, including the part that is less favorable> | <Section and Appendix Table> (<R1-Q2>) |
```

> 例子。一行写成 `| Q2, larger budgets | PairSift leads below 3,000 pairs, TopSim is 0.3 points higher at 5,000 pairs | Section 4.3 and Appendix Table 13 (R1-Q2) |`。

## 6. 上传修订稿后的跟帖

作为新的顶层评论发给全体，英文不超过 1,000 字符，按修订稿的实际编号写。

```text
Thank you all once more for the feedback. The updated PDF is now online. Red text marks each substantive edit, with the number of the related comment beside it in the right margin, using <color 1> for <R1>, <color 2> for <R2> and <color 3> for <R3>. Principal edits follow.

- <Location>, <what is new or replaced> (<R1-W1a>, <R2-Q1>)
- <Location>, <what is new or replaced> (<R3-Q1>)

Code and run-level results for the new experiments are in the supplementary archive.
```

> 例子。`- Table 1, five-seed means with intervals (R1-W1a, R1-Q1)`。`- Appendix Table 13, budgets up to 5,000 pairs (R1-Q2)`。

## 7. 催复

讨论期结束前约两天，发给还没有回应的审稿人，修订稿上传之后才发，发前按上传的 PDF 再核一次编号。形容词取属实的词，例如 detailed、constructive。

```text
Thanks again for your <adjective> review. The discussion ends on <date>. Did our responses and the updated PDF resolve your questions, <topic 1> (<location>) and <topic 2> (<location>) above all? If so, we hope you might reconsider your score. We remain available for any follow-up.
```

## 8. 致谢

审稿人回应之后发。回应里有新问题时先逐条作答，不单发致谢。

| 情形 | 句式 |
|---|---|
| 审稿人表示认可 | `We appreciate your reply and your support for the paper.` |
| 审稿人提高评分，修订稿已上传 | `We appreciate the quick reply and the updated score. The updated PDF now contains these clarifications.` |
| 审稿人提高评分，修订稿未上传 | `We appreciate the quick reply and the updated score. The next PDF will contain these clarifications.` |

## 9. 表题与修订句

| 用途 | 句式 |
|---|---|
| 差值的取整 | `All differences are calculated from unrounded values.` |
| 区间的统计方式，每条评论写一次 | `95% bootstrap interval over seeds.` |
| 实验确实跑完，同一楼写一次 | `These runs are complete.` |
| 修订句 | `In the revision, <what changed> (<Section and Table>, margin note <R1-W1a>).` |
| 指代两个版本 | `Table 1 of the submission`，`Table 1 of the revision` |
| 引用公共回复的表 | `Table G1 of our general comment` |
| 消融或扩展实验的题注 | `Rerun at <the protocol of this figure>, applied identically to all variants and the complete system, with <number> runs per cell.` |

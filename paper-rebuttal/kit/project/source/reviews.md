# Verbatim official reviews (fictional demonstration)

This file holds the reviews word for word, copied from the review site. The text below is invented for the kit and belongs to no real submission. The numbering (R1-W1) is added by the authors when the reviews are copied.

---

## Reviewer R1  (Rating 3: Weak reject; Confidence 4; Soundness 2; Presentation 3)

### Summary
The paper studies duplicate record detection under a labeling budget. OurSys chooses which candidate pairs to send for labeling and reports recall on three datasets.

### Strengths
The budget constraint matches how labeling is paid for in practice.

The comparison covers rule-based and learning-based matchers.

### Weaknesses
(R1-W1) Each dataset is evaluated on a single data split, so the gain over L-Boost cannot be separated from split variance.

(R1-W2) The selection score of Section 3.2 is described only in words, which makes the method hard to reproduce.

### Questions
(R1-Q1) What are the averages and paired intervals when several data splits are used?

---

## Reviewer R2  (Rating 4: Weak accept; Confidence 3; Soundness 3; Presentation 3)

### Summary
OurSys is a budgeted labeling policy for duplicate detection, compared with four matchers on three datasets.

### Strengths
The problem is practical and the evaluation is easy to follow.

### Weaknesses
(R2-W1) The evaluation fixes the labeling budget at 5% of the candidate pairs, and it is unclear how the gain changes when the budget is smaller.

### Questions
(R2-Q1) How does the running time of OurSys compare with the baselines at the same labeling budget?

# 数字回填

数字只经一个脚本进入稿件。`backfill.py` 按登记表从结果文件取数，写中英两份数字宏文件，改写稿件里带标记的主表块，并输出回填记录 `BACKFILL.md`。重跑实验后再跑一次脚本即可，不手改数字。

## 文件

| 文件 | 内容 |
|---|---|
| `backfill.py` | 回填脚本，只依赖 Python 标准库和 `figure-style/tables/shade_and_rank.py` |
| `registry.example.json` | 登记表样例。每个数字一项，写明来源文件与键、格式、缩放或由其他数字算出的表达式 |
| `demo_results/` | 演示用的结果文件，其中运行时间的文件故意缺失，用来展示红色占位 |

## 用法

```bash
python backfill.py --registry registry.example.json --paper-dir ../latex-bilingual
python backfill.py --registry registry.example.json --paper-dir ../latex-bilingual --dry-run   # 只看记录，不写文件
```

在论文仓库里使用时，把 `backfill.py` 与 `figure-style/tables/shade_and_rank.py` 一起复制到 `tools/`，登记表放在仓库根，`source` 指向服务器同步回来的结果目录。

## 规则

- 结果文件缺失、键缺失或值为空时，该数字不写入宏文件，稿件里印成红色，`BACKFILL.md` 列为等待。
- 由其他数字算出的量(相对提升、倍数)用 `expr` 写在登记表里，依赖的数字缺失时它也保持等待。
- 主表的前两名底色和排名按印出的数值计算，审稿人能用表内数字复算。
- 回填记录随稿件提交，给导师的内部报告引用它说明每个数字的出处。

# 实验图风格

本目录把作者多篇数据管理与机器学习论文的实验图风格做成了一个绘图模块和四个可运行的样例。新论文画图时复制模块、挑一个样例改数据即可。实验表的逻辑与模板在 `tables/README.md`。样例里的方法、数据集和数值都是虚构的演示数据。

## 文件

| 路径 | 内容 |
|---|---|
| `figstyle.py` | 绘图模块，只依赖 matplotlib 与 numpy，接受 pandas 对象 |
| `examples/` | 四个样例脚本和 `data/` 下的演示数据 |
| `gallery/` | 四个样例的渲染图 |
| `tables/` | 实验表的逻辑、LaTeX 宏、样例表和主表生成脚本 |

## 怎么用

1. 把 `figstyle.py` 复制到论文的绘图脚本目录。
2. 在全篇共用的一处调用 `fs.set_methods("本文方法名", {族名: [方法, ...]})`，族的顺序与主表的行分组一致。这样每个方法在所有图里的颜色、标记和填充纹理都相同。
3. 从 `examples/` 挑最接近的样例改数据。图数据只从实验记录或回填脚本写出的 CSV 读。
4. 用 `fs.save(fig, "路径/图名")` 出图。它会写出 PDF、SVG 和 PNG，返回印刷宽度与最小字号，并在图例压住数据、文字越出画布或题注重叠时报错。

```python
import figstyle as fs
fs.set_methods("Ours", {"Statistical": ["A1", "A2"], "Deep": ["B1", "B2"]})
fig = fs.canvas("ieee", "text", height=2.6)          # 画布宽度等于 IEEE 的页宽
ax = fs.box(fig, 0.45, 0.50, 1.20, 1.18)             # 以英寸给出面板位置与大小
handles = fs.line_panel(ax, [1, 2, 3, 4], {"Ours": ours, "A1": a1, "B1": b1},
                        xlabel="Error types per record", ylabel="F1")
fs.panel_caption(ax, "(a) Mixed errors")
fs.shared_legend(fig, handles)
fs.save(fig, "out/fig_results")
```

## 样例

| 样例 | 图型 | 仿照的图 | 渲染图 |
|---|---|---|---|
| `ex_a_results_row.py` | 双栏一行四面板，三个折线面板加一个分组条形面板，方法图例在上方排成一行 | 主结果图 | `gallery/ex_a_results_row.png` |
| `ex_b_bars_radar.py` | 单栏双面板，分组条形图加雷达消融图 | 对比与消融图 | `gallery/ex_b_bars_radar.png` |
| `ex_c_motivation.py` | 单栏动机图，注入错误的运行与配对的干净运行的时序对比，加堆叠条形图 | 时序类论文的图 1 | `gallery/ex_c_motivation.png` |
| `ex_d_dose_heatmap.py` | 单栏双面板，剂量曲线加发散色热图 | 剂量与分区面板 | `gallery/ex_d_dose_heatmap.png` |

每个样例都能直接运行，例如 `python examples/ex_a_results_row.py`，输出在 `examples/out/`。加 `--gallery` 会同时更新 `gallery/` 里的渲染图。

## 规则

**画布与版式**
- 按印刷尺寸画。画布宽度等于投稿模板的栏宽或页宽，插入论文时不缩放。`fs.width(venue, kind)` 给出 IEEE、ACM、VLDB、AAAI、ICML、ICLR、NeurIPS 的宽度。
- 主结果图是一张双栏图，一行四个面板。次要对比与消融拼成一张单栏双面板图。
- 面板题注写成「(a) 名称」，放在面板下方。

**线、标记与颜色**
- 四边闭合边框，刻度朝内，沿一个坐标轴画浅色网格。
- 本文方法用红色、星形标记和黑色细描边，线最粗，最后画，压在其他曲线之上。
- baseline 每个方法族一种颜色，族内每个方法一种标记，标记用白色细描边。条形图用同一套颜色，再加填充纹理区分。
- 参照曲线用深色虚线和空心圆，上界类的参照用绿色虚线和方块。
- 同一批方法的第二种条件用虚线和空心标记，面板内另放一个说明线型的小图例。

**图例**
- 多个面板画同一批方法时，共用一条图例，排成一行放在这些面板上方(`shared_legend`)。
- 只属于一个面板的图例放在该面板内不压数据的位置(`inside_legend`)。找不到空位时扩大坐标范围，仍放不下就报错。
- 图例只列实际画出的方法。

**坐标与字号**
- 坐标范围按数据设定，让曲线彼此分开(`zoom_ylim`)。不用断轴。
- 轴标签与面板题注 8.7 pt，刻度 8.0 pt，图例 7.0 到 7.8 pt，最小不低于 6.3 pt。字体用 DejaVu Sans，输出的 PDF 内嵌 TrueType 字体。

**各图型**
- 雷达消融图每个轴单独定范围，范围写在轴名下面，完整方法是最外层的多边形，顶点标记与图例一致，线型全用实线(`radar`)。
- 时序动机图画带故障运行与配对的无故障运行，故障注入时刻用竖直虚线标出，两条曲线之间的区域涂浅红并标注效应(`ts_effect_panel`)。
- 热图用以零为中心的发散色，单元格之间留白线，数值大的单元格印出数字，色条横放在面板上方(`heatmap` 与 `colorbar_key`)。

**出图**
- 定稿图不带水印，不留占位数据。
- 用于 PPT 的图用 SVG 或 PDF 矢量，关键数字与结论标红。

画什么内容、放哪些 baseline、哪些图不放，属于取舍规则，见 `writing-playbook.md` 第 8 节。

## 表

实验表的分类逻辑、三张表的写法、前两名深浅底色和排名规则都在 `tables/README.md`，配色与宏在 `tables/table_macros.tex`。

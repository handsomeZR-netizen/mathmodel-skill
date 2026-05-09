---
stage: 8
name: writing
duration_h: 12-16
inputs: [decision_log.stages.0-7]
outputs: [stage.8.{section_word_counts, figures_per_subproblem, tables_per_subproblem, abstract_drafts, anchor_phrase_hits, danger_phrase_hits}, paper.tex]
loads_reference: [winning_patterns.md, phrase_bank.md, anti_patterns.md§A_I]
loads_template: [paper_skeleton.md, abstract_template.md, cumcmthesis/]
feedback: [L1, L2_at_end]
next: stage_09_review
---

# Stage 8 — 论文写作 (摘要最后写)

**时长**: 12-16h | **反馈层**: L1 | **占整个 skill 时间约 25%**

---

## 目标

把前面 0-7 阶段的产出**装配**成 22-25 页国赛论文。**不重新建模, 不重新求解**(若发现需要, 触发 L2 而非自行回退)。

---

## 输入

- stage 0-7 全部 decision_log 内容
- `templates/paper_skeleton.md` (论文骨架)
- `templates/abstract_template.md` (5 段式摘要模板)
- `templates/cumcmthesis/` (LaTeX 模板)
- `references/winning_patterns.md` (写作时打开)
- `references/phrase_bank.md` (写作时打开)

## 产出

- `paper.tex` (或 markdown 中间产物 + 转 tex)
- `figures/` 全部图 (统一配色)
- `tables/` 全部表 (LaTeX booktabs)
- 最终 PDF (xelatex 编译)

---

## 写作顺序 (反直觉但有效)

**摘要最后写。**

```
1. 写正文 §1 问题重述         (30 min)
2. 写正文 §2 问题分析         (1h)
3. 写正文 §3 模型假设         (30 min, 复用 stage 4)
4. 写正文 §4 符号说明         (15 min, 复用 stage 4)
5. 写正文 §5.1 Q1 模型与求解 (2-3h, 用 stage 5 产出)
6. 写正文 §5.2 Q2            (2-3h)
7. 写正文 §5.3 Q3            (2-3h)
8. 写正文 §6 灵敏度          (1h, 复用 stage 6)
9. 写正文 §7 评价与推广       (1h, 复用 stage 7)
10. 写正文 §8 参考文献        (30 min, 整理)
11. 写附录 (代码 + 数据表)    (30 min)
12. ⭐ 最后写摘要 + 摘要专项 loop  (60-90 min, 见下方"摘要专项 loop")
13. ⭐ 整篇 L1 自评 + 修订           (1-2h)
```

理由: 摘要是浓缩,只有正文写完才能精确浓缩。先写摘要会导致后续被自己摘要"绑架"。

**摘要权重事实上 ≈ 30%** (评委先看摘要决定是否细看), 因此摘要在通用 stage 8 的 5 维评分之外, **额外**跑独立的"摘要专项 loop", `variant=abstract`, 阈值收紧到 min≥9 mean≥9, 不允许 carryover。详见 §"摘要专项 loop"。

---

## 各节写作详细 prompt

### §1 问题重述 (1-2 页, 30 min)

**关键**: 不要原文照抄, 要用自己语言提炼。

模板:
```
1. 问题背景

随着 <领域>的不断发展, <问题>已成为亟需解决的关键问题。
本题以 <具体场景>为背景, ...

2. 问题描述

题目给出了 <数据资源>, 要求解决以下三个子问题:

问题一: <自己语言重述, 不直接抄题>
问题二: ...
问题三: ...
```

字数: 600-1200 字。
**禁止**: 大段抄题。**禁止**: 仅用 1 句话重述 (信息密度太低)。

### §2 问题分析 (2-3 页, 1h)

每子问题一段:
```
2.1 问题一分析

本质上, 问题一是一个 <类型>问题。需要在 <约束>下, 寻找 <决策变量>使 
<目标函数>取得最优。

由于 <难点>, 直接求解较为困难。本文采用 <策略>: ...
图 1 给出了问题一的求解流程。

[流程图占位]

(衔接到 §5.1)
```

**关键加分**: 流程图 (mermaid 转 PNG / TikZ)。

### §3 模型假设 (0.5-1 页, 30 min)

直接复用 `decision_log.stages.4.assumptions`:

```
3. 模型假设

为简化模型并保证可解性, 本文做出如下假设:

(1) **短期内市场需求服从泊松分布。**
    依据: 文献 [3] 表明零售业短期需求服从泊松; 附件 1 数据 χ² 检验 p=0.34 不拒绝。

(2) ...

(3) ...
```

3-7 条, 每条带支撑 (winning_patterns §6)。

### §4 符号说明 (0.5-1 页, 15 min)

LaTeX 表格 (booktabs):

```latex
\begin{table}[h]
\centering
\caption{符号说明}
\begin{tabular}{cccl}
\toprule
符号 & 含义 & 单位 & 类型 \\
\midrule
$x_i$ & 第 $i$ 个产品产量 & 件 & 决策变量 \\
$p_i$ & 第 $i$ 个产品单价 & 元/件 & 参数 (附件 1) \\
$d_i$ & 第 $i$ 个产品需求 & 件 & 随机变量 \\
\bottomrule
\end{tabular}
\end{table}
```

≥10 行, 全单位 (anti_pattern B5)。

### §5 模型建立与求解 (12-16 页, 6-9h, 主体)

每子问题 4-6 页, 结构严格:

```
5.1 问题一: <模型族变体名>

5.1.1 模型建立

本节针对问题一建立 <动态权重 AHP-熵权混合评价> 模型 (winning_patterns §4 命名变体).

设 <决策变量, 引用 §4>。
目标函数: ...
$$\max f(x) = \sum_i (p_i - c_i) x_i \quad \text{(5.1)}$$

约束条件:
$$\text{(C1)} \quad \sum_i c_i x_i \leq B \quad \text{(5.2)}$$
$$\text{(C2)} \quad x_i \in \{0, 1, ..., 50\} \quad \text{(5.3)}$$

5.1.2 求解算法

针对 (5.1)-(5.3), 我们采用 Lagrangian 松弛, 具体步骤如下:
**Step 1**: ...
**Step 2**: ...

算法流程见图 2。

[流程图]

5.1.3 求解结果与分析

通过 Python 调用 cvxpy + GUROBI 求解, 经 4.2 秒收敛, 得到最优解 x* = (12, 0, 25, ...), 
最优利润 87234 元 (相比贪心基线 +12.3%)。

[图 3: x* 分布柱状图]
[图 4: 与基线对比]

求解结果显示, ... <stage 5 物理意义讨论, 复用>。
```

**强制 checklist** (winning_patterns §3, §4, §5, §8):
- [ ] 模型有命名变体
- [ ] 公式编号 ≥5 个 (整个 §5.1)
- [ ] 流程图 + 结果图 + 灵敏度图 ≥3 张
- [ ] 数据表 ≥1
- [ ] 物理意义段 ≥1
- [ ] (Q3) 显式引用 Q1/Q2 结果

### §6 灵敏度分析 (2-3 页, 1h)

直接复用 `decision_log.stages.6`:

```
6. 灵敏度分析与稳健性检验

6.1 分析方法

为评估模型对参数变化的敏感程度, 本文采用拉丁超立方抽样 (LHS) 
对 ($p, c, B$) 进行联合扰动, 在 ±5%, ±10%, ±20% 三档下各抽样 200 个点。

6.2 分析结果

[表 N: 稳健区间]
[图 N: pairs plot]
[图 N: tornado]

6.3 失稳预警

实验进一步发现, 当预算 $B$ 减少 30% 以上时, 最优解切换为 ... 
(从 stage 6 直接复用)
```

### §7 模型评价与推广 (1-2 页, 1h)

直接复用 `decision_log.stages.7`:

```
7. 模型评价与推广

7.1 模型优点
(1) **<优点 1>**: <证据>。
(2) ...
(3) ...

7.2 模型缺点

(1) **<缺点 1>**: 当前 <现象>。若改用 <替代方法>, 在 <指标> 上可提升 X%, 
    但需 <代价>。
(2) ...
(3) ...

7.3 模型改进方向
(1) **<改进 1>**: ...

7.4 模型推广

本模型可推广至 **<场景 1>**, 适配方式: ...
也可推广至 **<场景 2>**, 适配方式: ...
```

### §8 参考文献 (0.5-1 页, 30 min)

**国赛要求 ≥10 条**, 用 GB/T 7714 格式:

```
[1] 张三, 李四. 基于 ... 的 ... 研究 [J]. 系统工程学报, 2023, 38(4): 567-580.
[2] Smith J, Doe A. A novel approach to ... [J]. Operations Research, 2024, 72(3): 1234-1250.
[3] ...
```

类型混合: ≥4 中文期刊, ≥3 英文期刊, ≥1 教材或工具书。

### 附录 A: 程序代码 (30 min)

每段代码 (anti_pattern D1):
- 中文注释
- 首行 "对应 §X.Y.Z"
- 删除 print 调试残留

```python
# Q1 求解 - 对应论文 §5.1.2
# Lagrangian 松弛混合整数线性规划
import numpy as np
import cvxpy as cp

# 加载数据
...
```

### ⭐ 摘要 (45 min, 最后写)

调用 `templates/abstract_template.md`:

```
本文针对 <核心任务>, 综合考虑 <因素 1, 2, 3>, 建立了 <核心模型族>模型, 
通过 <求解方法> 求解, 得到 <总体定量结果>。

针对问题一, ... 得到 <定量结果 1>。
针对问题二, ... 得到 <定量结果 2>。
针对问题三, ... 得到 <定量结果 3>。

对模型进行了多变量联合灵敏度分析, 在参数 ±10% 扰动内, 输出指标偏差小于 X%, 
验证了模型的稳健性。

本文创新点在于: 
① <创新点 1>; 
② <创新点 2>; 
③ <创新点 3>。

所建模型可推广至 <场景 1> 和 <场景 2>。

**关键词**: <核心问题>, <核心方法>, <辅助方法>, <分析手段>, <应用领域>
```

**严格自检**:
- 字数 600-900 (anti_pattern A5)
- ≥3 个定量结果 (anti_pattern A1)
- 5 段顺序正确 (anti_pattern A2)
- 与正文一致 (anti_pattern A3)
- 关键词 4-6 个高质量 (anti_pattern A4)

---

## 摘要专项 loop (P1-9, ⭐ 一等奖关键)

整篇 L1 通过后, 对摘要单独跑 ≥3 轮专项 critic, 阈值 **min≥9 mean≥9**, 5 维全是可机检指标:

| 维度 | dim key | 检查方法 |
|------|---------|---------|
| 1 | `1_paragraph_structure` | 5 段顺序 + 字数 600-900 + 段长 ∈ 推荐区间 |
| 2 | `2_quant_results` | grep 段 3 数字 (含 % / 元 / 件 / σ / 倍率), count ≥3 |
| 3 | `3_named_variant` | 段 1 模型名是否含修饰词 (`改进/动态/混合/广义/双层/...`) |
| 4 | `4_per_qi_main_result` | 段 3 每 Qi 至少一句, 句中含数, 与 §5 主结论一致 |
| 5 | `5_keywords_quality` | 4-6 个, 每个 ≤8 字, 排除空泛词 (如"研究/分析") |

**调用流程**:

```python
# 1. 写完摘要初稿 abstract_v0.md
# 2. 让 critic 输出 critique_abs_v0.json (variant=abstract)
# 3. 喂给打分脚本:
python scripts/score_artifact.py --stage 8 --variant abstract \
    --critique state/critique_abs_v0.json
# 4. 若 verdict != pass / pass_early → diff-only 精修, iter+=1
# 5. 摘要 loop 不允许 carryover; iter==3 仍未 pass 强制 block, 用户介入
# 6. 写入 decision_log.stages.8.abstract_meta.iters[]
# 7. decision_log.scores["8_abstract"] 留下完整迭代轨迹
```

**block 触发条件** (与 anti_patterns 联动):
- 段 3 量化数 < 3 (anti_pattern A1)
- 5 段顺序错乱或缺段 (A2)
- 命名变体缺失 (winning_patterns §4 反模式)
- 摘要数值与 §5 / §6 主结论不一致 (A3, 严重)
- phrase_bank §10 危险句式 ≥1 命中

通过摘要 loop 的产物写入:
- `decision_log.stages.8.abstract_meta.final_word_count`
- `decision_log.stages.8.abstract_meta.final_quant_count`
- `decision_log.stages.8.abstract_meta.final_keywords`
- `decision_log.stages.8.abstract_drafts.append(<本轮 final 文本>)`

---

## L1 Rubric

| 维度 | 满分行为 |
|------|---------|
| 1. 摘要 5 段式 | 完整 5 段, 600-900 字, 定量 ≥3 |
| 2. 章节完整性 | 8 章 + 附录全到位 |
| 3. 公式 / 图表 / 引用 | 编号规范, 引用 ≥10 |
| 4. 语言质量 | 摘要 5 段全部命中 phrase_bank §12 anchor + 危险句式零命中 |
| 5. 视觉一致性 | 字号/配色/字体全文统一 |

## 常见坑

- A1-A5 摘要类全部 → 摘要最后写 + 自检 5 项
- D1 代码无注释 → 中文注释 (附录)
- I1-I5 写作呈现 → cumcmthesis 模板自动统一格式

## 退出条件

1. 8 章 + 附录全部完成
2. 总页数 22-25
3. 公式编号 60-100
4. 图表 18-25
5. 引用 ≥10 条 GB/T 7714
6. xelatex 编译无错
7. L1 全维 ≥7
8. **摘要专项 loop**: `decision_log.scores["8_abstract"]` 最后一项 verdict ∈ {pass, pass_early}, min≥9 mean≥9
9. **L2 跨阶段回检**: 论文内容与 decision_log 0-7 一致, 无新增内容偏离

→ 跳转 `stage_09_review.md`

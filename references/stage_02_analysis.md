---
stage: 2
name: analysis
duration_h: 2.5-3.5
inputs: [stage.1.selected, problem_pdf, attachment_data_paths]
outputs: [stage.2.{decomposition, key_variables, key_constraints, objective_per_subproblem, data_schema, subproblem_dependency, eda_report_path, eda_findings}]
loads_reference: [rubrics.md§Stage_2]
loads_template: [scripts/run_eda.py]
feedback: [L1]
next: stage_03_model_selection
---

# Stage 2 — 问题深度解析与分解

**时长**: 2-3h | **反馈层**: L1

---

## 目标

把题目从**自然语言描述**转化为**数学语言骨架**: 识别决策变量、目标函数、约束、子问题间关系。这一步质量决定后续 5/6/8 阶段的天花板。

---

## 输入

- stage 1 输出: 选定题号 + 子问题清单 + 数据路径
- 题目原文 (再读一次)
- 附件数据 (用 pandas/Read 扫一遍 schema)

## 产出

- 子问题分解树 (Q1/Q2/Q3 的输入/输出/约束/目标)
- 关键变量清单 (≥10 个,标注决策/状态/参数)
- 子问题间关联图 (谁依赖谁的结果)
- 目标函数雏形 (符号级,不必精确)
- 数据 schema 与变量映射

---

## 操作流程

### Step 1: 题目精读 (30 min)

**精读三遍,每遍不同任务:**

第一遍 (10 min): 抓动词。题目让你做什么? "求最优..." / "预测..." / "评价..." → 决定问题类型。

第二遍 (10 min): 抓约束。哪些条件不能违反? 列出来。

第三遍 (10 min): 抓数据接口。哪些参数题目会给? 哪些要从附件提? 哪些要假设?

### Step 2: 子问题正式分解 (45 min)

对每个 sub-problem Qi,填写卡片:

```
Q1 卡片
├── 自然语言描述: <一句话提炼>
├── 输入:
│   - 题目给定参数: ...
│   - 附件数据: 附件 1 第 X 列
│   - 上游问题结果: 无 (Q1 是入口)
├── 输出 (最终决策变量):
│   - x_1, x_2, ... (含义、单位)
├── 约束:
│   - C1: ...
│   - C2: ...
├── 目标:
│   - 最小化/最大化 <什么>
├── 问题类型: <model_catalog 第几类>
└── 难度估计: easy / medium / hard
```

**关键**: Q3 卡片的"上游依赖"列必须明确写: 是否依赖 Q1 / Q2 结果?
若题目允许且没明示,**默认要求 Q3 复用 Q1/Q2 结果** (winning_patterns §5)。

### Step 3: 关键变量统一编号 (30 min)

跨子问题统一符号 (anti_pattern B4: 符号重复定义):

```
全局变量表 (stage 4 会复制到论文)

| 符号 | 含义 | 单位 | 类型 | 出现于 |
|------|-----|------|------|-------|
| x_i | 第 i 个产品的产量 | 件 | 决策变量 | Q1, Q2 |
| p_i | 第 i 个产品的单价 | 元/件 | 参数 (附件 1) | Q1, Q3 |
| α  | 折扣率 | 无量纲 | 参数 | Q3 |
| ξ  | 需求随机扰动 | 件 | 随机变量 | Q3 |
| ... |
```

≥10 个变量。

### Step 4: 数据 EDA 报告 (60 min, ⭐ P1-10)

> B/C 题没 EDA = 后续 stage 5 在裸跑。即便 A 题数据少, 也强制扫一遍 (题面给的常数 / 表 / 几何信息也算)。
> **不通过本步骤不进 stage 3。**

不直接打开 pandas, **先调脚本**生成结构化 EDA 报告:

```bash
python <skill>/scripts/run_eda.py \
    --data-dir cwd/data/ \
    --out cwd/eda_report.md \
    --decision-log cwd/state/decision_log.json
```

脚本产出 `cwd/eda_report.md` 含 5 个必填板块, 同时把摘要回写到 `decision_log.stages.2.eda_findings`:

```markdown
## 1. Schema (每附件一段)
- 行数 / 列数 / 列名 / dtypes / 时间跨度 / 单位

## 2. 缺失值矩阵
- 每列缺失比例; 是否随机缺失; 是否成块缺失 (前 N 行 / 后 N 行)
- 提议处理: 列删除 / 行删除 / 插补方法 (均值 / 前向 / KNN)

## 3. 分布与异常
- 数值列: mean/std/min/p25/p50/p75/max/skew/kurt
- 异常: > 3σ 或 IQR 1.5× 外的样本数, 列出索引
- 分布检验: 正态 / 泊松 / 重尾 (Anderson-Darling 或 KS, p 值)
- 配套图: histograms.png, boxplots.png

## 4. 相关性 / 依赖
- Pearson + Spearman 矩阵 (前 30 列), corr_heatmap.png
- 高相关对 (|r|>0.7) 列出, 提示多重共线性

## 5. 数据 ↔ 假设/变量对账
- 对 stage 2 全局变量表的每个变量, 标注: "数据列 X 提供" / "需要假设" / "需要外部参考"
- 对 stage 4 (尚未做但可预判) 候选假设逐条注: "数据是否支撑?"
```

**关键产出 (写 decision_log.stages.2.eda_findings)**:
```json
{
  "missing_pct_per_col": {"附件1.价格": 0.0, "附件1.需求量": 0.05},
  "outliers_count_per_col": {"附件1.价格": 3, "附件1.需求量": 0},
  "key_correlations": [{"a": "p", "b": "d", "r": -0.62, "method": "pearson"}],
  "distribution_summary": {"附件1.需求量": "right-skewed, kurt=2.1, 不拒绝泊松 p=0.34"},
  "data_assumption_alignment": {
     "x_i": {"source": "决策变量, 无需数据"},
     "p_i": {"source": "附件1.价格", "完整": true},
     "d_i": {"source": "附件1.需求量", "完整": false, "missing": 0.05},
     "α": {"source": "需要假设", "support": "文献 [1] 给 0.1-0.2"}
  },
  "report_path": "cwd/eda_report.md"
}
```

**block 触发** (high-severity issue, 不进 stage 3):
- 题目附件存在但 `eda_findings` 为空
- 全局变量表中有 ≥1 个变量在 `data_assumption_alignment` 既非"数据"也非"假设"也非"外部参考"
- 关键变量缺失 >30% 但无插补方案

若题目无附件 (e.g. 部分 A 题): 仍要写 EDA 简版 (题面常数表 + 几何参数表 + 单位表), 至少 1 页。

### Step 5: 子问题关系图 (15 min)

以 mermaid / ASCII 表达:

```
Q1 (求最优生产计划) 
  ↓ x_i*
Q2 (考虑库存约束)
  ↓ 库存阈值 K*
Q3 (随机需求下的稳健决策)
  ↓ 引用 Q1 的 x_i* 与 Q2 的 K* 
最终: 决策方案 + 风险评估
```

写入 `decision_log.stages.2.decomposition`。

### Step 6: 目标函数雏形 (30 min)

每个 Qi 写出符号化目标 (不必完整,要框架):

```
Q1: max  Σ_i p_i * x_i  - C(x)
    s.t. Σ_i x_i ≤ B (预算)
         x_i ≥ 0, x_i ∈ Z

Q2: 在 Q1 基础上加约束 K_i ≤ K_max
    
Q3: max E_ξ [ Σ_i p_i * x_i - C(x) - λ * Var(...) ]
    使用 Q1 的 x* 作为 warm start
```

### Step 7: 输出移交 (5 min)

写入 `decision_log.stages.2`:
```json
{
  "decomposition": [...],
  "key_variables": [...],
  "key_constraints": [...],
  "objective_per_subproblem": {"Q1": "...", "Q2": "...", "Q3": "..."},
  "data_schema": {...},
  "subproblem_dependency": {"Q1": [], "Q2": ["Q1"], "Q3": ["Q1", "Q2"]},
  "eda_report_path": "cwd/eda_report.md",
  "eda_findings": { /* Step 4 已写 */ }
}
```

---

## L1 Rubric (`rubrics.md` Stage 2)

| 维度 | 满分行为 |
|------|---------|
| 1. 子问题分解清晰度 | 每 Qi 卡片完整 |
| 2. 关键变量识别 | ≥10,标注类型 |
| 3. 数学化程度 | 每 Qi 有目标雏形 |
| 4. 数据契合度 | EDA 报告 5 板块齐, `data_assumption_alignment` 全部变量已分类 |
| 5. 子问题关联性 | Q3 是否依赖 Q1/Q2 已识别 |

---

## 常见坑

- 题目仅读一次就开干 → 强制读 3 遍
- 子问题间符号不统一 (B4) → 统一变量表
- 附件数据没扫 → strictly 必做 Step 4
- Q3 没考虑复用 Q1/Q2 (G1) → Step 2 卡片"上游依赖"列硬要求

---

## 退出条件

1. 三个子问题卡片完整
2. 全局变量表 ≥10 项
3. **EDA 报告 5 板块齐, eda_findings 已写入 decision_log** (P1-10)
4. **data_assumption_alignment 中所有变量已三分类 (数据 / 假设 / 外部参考), 无未归类**
5. Q3 复用关系明确 (是 / 否,有理由)
6. L1 rubric 全维 ≥7

→ 跳转 `stage_03_model_selection.md`

---
stage: 6
name: robustness
duration_h: 2-3
inputs: [stage.5.sub_problems.{Qi}.{code_path, key_metrics}, stage.4.{assumptions, symbols}, stage.3.selected_per_subproblem]
outputs: [stage.6.{params_varied_jointly, method, deltas, robust_intervals, stability_verdict, failure_warning, L2_backtrack, figures}]
loads_reference: [winning_patterns.md§7, rubrics.md§Stage_6, anti_patterns.md§F]
loads_template: [code_starter/simulation.py, sensitivity_table.md]
feedback: [L1, L2_cross_stage]
next: stage_07_evaluation
---

# Stage 6 — 全局灵敏度 / 稳健性分析

**时长**: 2-3h | **反馈层**: L1 + L2 (跨阶段回检触发点)

---

## 目标

证明你的模型**不是过拟合到题目附件数据的脆弱产物**。一等奖与二等奖在此处的差距最大: 二等奖只做 OAT (one-at-a-time), 一等奖做**多变量联合扰动**并给出**定量稳健区间**。

---

## 输入

- stage 5 各 Qi 的求解器代码 (复用)
- stage 4 符号表 + 假设
- stage 3 模型选择 (本节会触发对其的 L2 回检)

## 产出

- 灵敏度分析报告 (≥3 参数联合扰动 + ≥1 张联合扰动图 + 稳健区间表)
- 稳健性结论 (write to `decision_log.stages.6.stability_verdict`)
- 失稳预警 (≥1 个临界参数)
- L2 回检报告: 模型选择前提是否被推翻

---

## 操作流程

### Step 1: 选定扰动参数 (15 min)

从 stage 4 符号表的"参数"行中选: ≥3 个**对结果影响可能最大**的参数。

判断标准:
- 出现在目标函数中的系数 (高优先级)
- 出现在多个约束中的参数 (高)
- 来自附件数据且数据本身有不确定性 (高)
- 决策者可调控 (中)

选 3-5 个,写入 `decision_log.stages.6.params_varied_jointly`。

### Step 2: 选定扰动方法 (10 min)

| 方法 | 适用 | Python |
|------|-----|--------|
| **OAT** (一变一) | 三等奖水平,**禁用为唯一方法** | 自实现 for 循环 |
| **LHS** (拉丁超立方) | ≥3 参数,样本数 100-1000 | `scipy.stats.qmc.LatinHypercube` |
| **Sobol** (索博尔) | 严格定量贡献度 | `SALib` 库 |
| **Morris** (莫里斯) | 大量参数 (>10) 筛选 | `SALib` |

国赛标准: **LHS** 是性价比最高的, 推荐默认。
Sobol 在时间允许时升级 (championship 模式)。

### Step 3: 扰动幅度三档 (10 min)

```
档位 1: ±5%  (轻度, 反映测量误差)
档位 2: ±10% (中度, 反映正常波动)
档位 3: ±20% (重度, 反映极端情景)
```

每档 LHS 采 200 个样本点。

### Step 4: 运行扰动求解 (1-2h)

```python
from scipy.stats.qmc import LatinHypercube
import numpy as np

# 选 3 个参数: p (单价), c (成本), B (预算)
n_samples = 200
sampler = LatinHypercube(d=3, seed=42)
unit_samples = sampler.random(n=n_samples)

# 三档扰动
for level, delta in [("low", 0.05), ("med", 0.10), ("high", 0.20)]:
    objectives = []
    decision_changes = []
    for s in unit_samples:
        # s ∈ [0,1]^3 → 缩放到 [1-delta, 1+delta]^3
        factors = 1 + (2*s - 1) * delta
        p_pert = p * factors[0]
        c_pert = c * factors[1]
        B_pert = B * factors[2]
        # 重新求解 (复用 stage 5 代码)
        result = solve_Q1(p_pert, c_pert, B_pert)
        objectives.append(result.value)
        decision_changes.append(np.linalg.norm(result.x - x_star_baseline))
    
    # 报告
    obj_arr = np.array(objectives)
    print(f"档位 {level} (±{delta*100:.0f}%):")
    print(f"  目标函数 5%-95% 区间: [{np.percentile(obj_arr, 5):.2f}, {np.percentile(obj_arr, 95):.2f}]")
    print(f"  相对基线偏差: {(obj_arr.std() / obj_arr.mean()) * 100:.2f}%")
```

总计 600 次求解 (3 档 × 200 样本)。如单次求解 >30s, 降到 100 样本。

### Step 5: 可视化 (30 min)

至少 2 张图:

**图 1: 联合扰动散点矩阵 (pairs plot)**

```python
import seaborn as sns
import pandas as pd
df_sens = pd.DataFrame({
    "p_factor": p_factors, "c_factor": c_factors, "B_factor": B_factors,
    "objective": objectives
})
sns.pairplot(df_sens, hue="objective", diag_kind="kde")
plt.savefig("figures/sensitivity_pairs.png", dpi=300)
```

**图 2: 龙卷风图 / Tornado** (单参数贡献度排序)

```python
contributions = {p: corr(p_factor, objective), c: corr(...), B: corr(...)}
sorted_contrib = sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)
# 横向 bar
```

(championship) **图 3: Sobol 一阶 + 总效应指数**

### Step 6: 稳健区间报告表 (15 min)

```
表 N. 多变量联合灵敏度分析结果

| 扰动幅度 | 目标函数 [5%, 95%] | 决策变量 L2 范数偏差 | 稳健性 |
|---------|------------------|-------------------|-------|
| ±5%    | [85800, 88600]   | < 2 件            | 极稳健 |
| ±10%   | [83200, 91100]   | < 5 件            | 较稳健 |
| ±20%   | [76400, 96800]   | < 12 件           | 临界稳健 |
```

### Step 7: 失稳预警 (15 min) ⭐

**强制找出 ≥1 个临界参数**: 越过某阈值后模型显著失效。

例:
```
失稳警告: 当预算 B 减少 30% 以上时, 最优解切换为完全不同的产品组合 (Hamming 距 > 50%), 
表明 B = 70k 是模型相变点。建议在评价节 §7 讨论该警告, 
并提议改用鲁棒优化 (anti_pattern H1, 自我批判要具体)。
```

写入 `decision_log.stages.6.failure_warning`。

### Step 8: L2 跨阶段回检 (15 min) ⭐

读 `decision_log`, 验证:

1. **stage 3 模型选择是否仍合理?**
   - 例: stage 3 选 LP 假设线性, 但本节 ±20% 下结果非线性 → 应在 stage 7 评价节显式讨论, 或考虑回 stage 3 升级为 NLP/鲁棒
   - 不退回 (除非完全推翻), 但**记录到 stage 7 评价**

2. **stage 4 假设是否被本节挑战?**
   - 例: 假设 "需求服从泊松", 本节扰动表明非泊松也成立 → 假设非必要, 可放宽

3. **stage 5 子问题间复用是否在扰动下崩溃?**
   - 例: Q3 用 Q1 的 x* 作为 warm start, 但 Q1 在 ±10% 下解集已切换 → Q3 也需重做, 或显式说明 Q3 在哪些参数范围内仍成立

L2 输出:
```json
{
  "backtrack_targets": ["stage_3", "stage_5_Q3"],
  "verdict": "no_revert | revise_stage_7 | full_revert",
  "notes": "..."
}
```

`verdict` 通常是 `revise_stage_7` (在评价节讨论限制), `full_revert` 极少触发。

### Step 9: 输出移交 (10 min)

写入 `decision_log.stages.6`:
```json
{
  "params_varied_jointly": ["p", "c", "B"],
  "method": "LHS, n=200/档",
  "deltas": [0.05, 0.10, 0.20],
  "robust_intervals": {...},
  "stability_verdict": "在 ±10% 扰动内极稳健, ±20% 临界稳健",
  "failure_warning": "B 降 30%+ 触发解集切换",
  "L2_backtrack": {...},
  "figures": ["..."]
}
```

---

## L1 Rubric

| 维度 | 满分行为 |
|------|---------|
| 1. 多变量联合扰动 | ≥3 参数同时变 + LHS 或更高级 |
| 2. 扰动幅度合理 | 三档 + 对应实际不确定性 |
| 3. 输出指标完备 | 目标函数 + 决策变量偏差 |
| 4. 稳健区间定量 | 表格 + 5%/95% 分位数 |
| 5. 失稳预警 | ≥1 临界参数 |

## 常见坑

- F1 不做灵敏度 → 阻塞,必须做
- F2 仅 OAT → 强制 ≥3 参数联合
- F3 扰动幅度不切实际 → 三档硬约束
- F4 不报稳健区间 → Step 6 表格

## 退出条件

1. ≥3 参数 LHS 联合扰动完成
2. 稳健区间表 + 龙卷风图齐全
3. ≥1 失稳预警
4. L2 回检完成 (verdict 写入)
5. L1 全维 ≥7

→ 跳转 `stage_07_evaluation.md`

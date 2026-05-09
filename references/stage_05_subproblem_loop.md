---
stage: 5
name: subproblem_loop
duration_h: 6-12 per Qi
inputs: [stage.2.subproblem_cards, stage.3.selected_per_subproblem, stage.4.{assumptions, symbols}]
outputs: [stage.5.sub_problems.{Qi}.{model_name, math_formulation_path, code_path, results_path, figures, key_metrics, physical_meaning_summary, scores, iterations}, stage.5.cross_reference_chain, stage.5.assumption_change_history]
loads_reference: [model_catalog.md, winning_patterns.md§5, rubrics.md§Stage_5]
loads_template: [code_starter/<problem_type>.py]
feedback: [L1_per_Qi, sub_checkpoint, L2_at_end_for_stage_3_4_consistency]
next: stage_06_robustness
---

# Stage 5 — 递归子问题循环 (Q1..Qn)

**时长**: 6-12h × n 个子问题 | **反馈层**: L1 + 子检查点 | **占整个 skill 时间约 50%**

---

## 目标

为每个子问题 Qi 跑一遍完整的 mini-pipeline: **建模 → 求解 → 子结果分析 → 子灵敏度**, 同时**强制建立子问题间的复用链** (winning_patterns §5)。这是论文的主体, 也是最容易翻车的阶段。

---

## 输入

- stage 2 子问题卡片
- stage 3 选定模型 + toy demo 通过
- stage 4 假设/符号/术语
- (Q2 / Q3 进入时) 上游 Qi-1 的结果

## 产出

- 每 Qi 的: 数学模型完整公式 + 求解代码 + 数值结果 + ≥2 张图 + 物理意义讨论
- 跨子问题: 复用链显式建立 (Q3 引用 Q1/Q2)
- 写入 `decision_log.stages.5.sub_problems.{Q1, Q2, Q3, ...}`

---

## 递归循环结构

```
for Qi in [Q1, Q2, ..., Qn]:
    A.   模型完整化 (45 min)
    A.5. ⭐ Pre-mortem: 预填 expected_range (15 min, P1-11)
    B.   求解实现 (2-4h)
    C.   ⭐ 自动 sanity (run_solver.py 比对 expected_range, 30 min)
    D.   子灵敏度 (1h, optional 但建议)
    E.   物理意义 (15 min)
    F.   L1 自评 + 必要时 diff-only 精修
    G.   输出移交 (写 decision_log)
    H.   子检查点: Qi 是否引用上游? 符号是否与 stage 4 一致?
```

---

## 单 Qi 操作流程详解

### A. 模型完整化 (45 min)

把 stage 2 的目标雏形 + stage 3 的命名变体, 升级为正式数学公式:

```
问题 Q1 数学模型 (基于 Lagrangian 松弛的混合整数线性规划):

Decision Variables:
  x_i ∈ {0, 1, ..., 50}, i = 1, ..., 100

Parameters:
  p_i: 单价 (元/件), 来自附件 1 列 P
  c_i: 成本 (元/件), 来自附件 1 列 C
  B: 总预算 (元), B = 100000

Objective:
  max f(x) = Σ_i (p_i - c_i) x_i

Constraints:
  C1: Σ_i x_i ≤ B / mean(c)        (预算近似)
  C2: x_i ≤ 50                     (单品上限)
  C3: x_i ≥ 0, integer

Lagrangian Relaxation 改进:
  L(x, λ) = f(x) + λ * (B/mean(c) - Σ_i x_i)
  使用次梯度法迭代求 λ*
```

要求:
- 每个变量、参数、约束都有编号
- 公式用 LaTeX (即使现在是 markdown, stage 8 直接复制)
- "改进点" 用粗体强调

### A.5. ⭐ Pre-mortem: 预填 expected_range (15 min, P1-11)

**写代码之前**, 必须先回答: "我预期答案大概什么样?"。这是反 D2/D3 (量级离谱) 的硬手段——**不写下预期, 跑出来的鬼东西也会自我说服**。

把每个关键输出写成 `expected_range`, 落盘到 `cwd/state/Q1_expected.json`:

```json
{
  "objective":     {"min": 1e3, "max": 1e6, "unit": "元"},
  "x_star":        {"shape": [100], "dtype": "int", "min": 0, "max": 50},
  "solve_time_s":  {"max": 120}
}
```

**填法**:
- 量级: 物理直觉 + 题面常数 + 贪心 baseline 的 0.5×~2× 区间
- shape: 应该有几个变量、几个时段、几条路径
- 单位: **必填**, 防止 `元` 写成 `万元` 之类的低级错
- 时间: 求解器单次预算; 超时即 fallback

预期与最终结果的容差不必苛刻, 但**两个数量级以上偏差就该 block**。

同时把 `expected_range` 写入 `decision_log.stages.5.sub_problems.Q1.expected_range` (decision_log 模板已留位)。

### B. 求解实现 (2-4h)

用 Python (numpy/scipy/sklearn/cvxpy) 实现。**约定**:

```python
"""
Q1 求解 - 对应论文 §5.1
基于 Lagrangian 松弛的混合整数线性规划
"""
import numpy as np
import pandas as pd
import cvxpy as cp
import matplotlib.pyplot as plt
np.random.seed(42)  # 可复现性

# Step 1: 加载数据
df = pd.read_excel("data/附件1.xlsx")
p = df["price"].values
c = df["cost"].values
n = len(p)
B = 100000

# Step 2: 建模
x = cp.Variable(n, integer=True)
profit = (p - c) @ x
constraints = [
    cp.sum(c * x) <= B,
    x >= 0,
    x <= 50
]
prob = cp.Problem(cp.Maximize(profit), constraints)

# Step 3: 求解
prob.solve(solver=cp.GLPK_MI)
print(f"Q1 求解状态: {prob.status}")
print(f"目标函数值: {prob.value:.2f}")
print(f"求解时间: {prob.solver_stats.solve_time:.2f} s")

# Step 4: 保存结果 (二进制 + JSON 摘要, 后者供 run_solver.py 校验)
x_star = x.value.astype(int)
np.save("results/Q1_x.npy", x_star)

import json
results = {
    "objective": float(prob.value),
    "x_star": x_star.tolist(),
    "solve_time_s": float(prob.solver_stats.solve_time),
    "status": prob.status,
}
with open("results/Q1_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
```

**关键**: 关键标量+数组以 JSON 写入 `results/Qi_results.json`, 这是 Step C 自动 sanity 的输入。

代码要求:
- 中文注释 (anti_pattern D1)
- 首行明确 "对应论文 §X" (winning_patterns §10)
- 设 random seed (anti_pattern D4)
- `print` 关键状态 (sanity check)
- 结果保存到 `results/Qi_*.npy` 或 `.csv`

### C. ⭐ 自动 sanity (30 min, P1-11)

**不再手 print 看, 用脚本卡点**。`run_solver.py` 把 Step A.5 写的 `expected_range` 与求解器写出的 `Qi_results.json` 自动比对。

```bash
python <skill>/scripts/run_solver.py \
    --qi Q1 \
    --code cwd/results/Q1_solve.py \
    --expected cwd/state/Q1_expected.json \
    --results cwd/results/Q1_results.json \
    --timeout 120
```

退出码语义:

| 退出码 | 含义 | 处理 |
|---|---|---|
| 0 | 全部 in-range | 进 D |
| 1 | 有 out-of-range | block, 回 A 重审建模 (anti_pattern D2/D3) |
| 2 | 求解器崩溃 / timeout | block, 回 stage 3 fallback (anti_pattern J3) |
| 3 | 文件 / schema 错误 | 修补脚本输出 |

工具自动写入:
- `decision_log.stages.5.sub_problems.Q1.actual_results` (字段摘要 + shape)
- `decision_log.stages.5.sub_problems.Q1.sanity_check_status` ∈ {ok, warn, block, timeout, crashed, no_results_file}
- `decision_log.stages.5.sub_problems.Q1.sanity_issues` (issues list)

**额外手工 4 项** (单元/边界/基线/单调性):

1. 单位与符号: 每输出有单位; 现金流 ≥ 0 ?
2. 边界 case: 输入零成本时是否取上限?
3. 基线对比: 贪心 vs 本模型, 提升 >0%?
4. 单调性: 涨价 → 利润涨? 不涨说明模型有 bug

```python
# 基线对比 (写进 Q1_solve.py 末尾)
x_greedy = np.minimum(50, B // np.maximum(c, 1))
profit_greedy = ((p - c) * x_greedy).sum()
print(f"贪心基线利润: {profit_greedy:.2f}")
print(f"本模型利润: {prob.value:.2f}")
print(f"相对提升: {(prob.value - profit_greedy) / profit_greedy * 100:.2f}%")
```

任一项失败 → 回 A 检查模型。

### D. 子灵敏度 (1h, 强烈建议)

只对本子问题做局部灵敏度 (全局留 stage 6):

```python
# 对单价 p 做 ±10% 扰动
deltas = [-0.1, -0.05, 0, 0.05, 0.1]
profits = []
for d in deltas:
    p_perturb = p * (1 + d)
    # 重新求解
    profit_d = (p_perturb - c) @ x_star  # 用同一 x*, 看新参数下利润
    profits.append(profit_d)

plt.plot(deltas, profits, 'o-')
plt.xlabel("p 扰动比例")
plt.ylabel("利润 (元)")
plt.title("Q1 子灵敏度: 单价扰动")
plt.savefig("figures/Q1_sensitivity.png", dpi=300)
```

### E. 物理意义讨论 (15 min)

写 1 段 (winning_patterns §8):

```
求解结果显示, 最优生产计划为 x* = (12, 0, 25, ...), 总利润 87234 元。
其中产品 1 (高单价低成本) 与产品 5 (低成本高需求) 占据主要产能, 
产品 2 因利润率仅 5% 而被全部跳过。这与零售行业 80/20 规律一致, 
即少数高利润 SKU 贡献主要收益。

相比贪心基线, 本模型利润提升 12.3%。
提升主要来自 Lagrangian 松弛对预算约束的精细处理, 
使总成本接近预算上限 (达到 99.4% 预算利用率), 而贪心仅 87.5%。
```

### F. L1 自评 + diff-only 精修

调用 `feedback_layer1_critic.md` 协议:
- 输出 5 维 JSON 评分
- 若任一维 <7 → diff-only 精修, iter+=1, 上限 3
- 全维 ≥9 → 早退

### G. 输出移交

写入 `decision_log.stages.5.sub_problems.Q1`:
```json
{
  "model_name": "...",
  "math_formulation_path": "results/Q1_model.tex",
  "code_path": "results/Q1_solve.py",
  "results_path": "results/Q1_x.npy",
  "figures": ["figures/Q1_flow.png", "figures/Q1_results.png", "figures/Q1_sensitivity.png"],
  "key_metrics": {"objective": 87234, "solve_time_s": 12.3, "improvement_vs_baseline": "12.3%"},
  "physical_meaning_summary": "...",
  "scores": {...},
  "iterations": 1
}
```

### H. 子检查点 (跨 Qi 后)

进入 Qi+1 之前,**自检**:

1. **复用链**: Q2 是否要用 Q1 的 x_star?
   - 题目要求? → 必须用
   - 题目允许? → 一等奖建议用 (winning_patterns §5)
   - 题目禁止? → 跳过

2. **符号一致**: Qi 中用的 x, p, c 是否与 stage 4 符号表一致?
   - 不一致 → 立即更新本 Qi 或更新符号表 (二选一并记录)

3. **假设一致**: Qi 模型是否引入了新假设?
   - 是 → 回 stage 4 加假设, 写入 decision_log
   - 否则 → 继续

4. **假设变更历史检查** (P2-3 新增) ⭐: 若 stage 4 的某假设在已完成 Qi 之后被 patch (L2 触发), 自检该 Qi 是否依赖被改假设。
   - **依赖** → 重跑该 Qi 的 Step C (sanity check) + Step D (子灵敏度), 不重跑完整 5 步
   - **不依赖** → 在 `decision_log.stages.5.assumption_change_history` 标记 "Qi 不受 patch X 影响, 跳过重跑"
   - 检查方法: 读 `decision_log.events.log` 找 `type=L2_backtrack` 且 `target=stage.4.assumptions[k]` 的记录, 然后 grep Qi 的代码与 math_formulation 是否引用 assumption k

---

## L1 Rubric (Per-Qi)

| 维度 | 满分行为 |
|------|---------|
| 1. 模型与问题契合 | 目标/变量/约束 与题面 1:1 |
| 2. 数学严谨性 | 符号一致, 推导无跳跃 |
| 3. 求解正确性 | 代码运行 + sanity check 通过 |
| 4. 结果可视化 | ≥2 图 (流程+结果) + 1 表 |
| 5. 物理意义讨论 | ≥1 段, 含 baseline 对比 |

## L1 Rubric (Stage-level)

| 维度 | 满分行为 |
|------|---------|
| 1. 子问题完整性 | 所有 Qi 都跑完 |
| 2. 复用链 | Q3 显式引用 Q1/Q2 (若题目允许) |
| 3. 符号一致 | 全 Qi 用同一套 stage 4 符号 |
| 4. 视觉密度 | 每 Qi ≥2 图 + 1 表 |
| 5. 时间预算 | 未超 stage 5 预算 30% |

## 常见坑

- D1-D5 求解类全部 → Step B/C 严格执行
- E1-E4 结果分析类 → Step E 物理意义必写
- G1 子问题各做各 → Step H 子检查点强制
- G2 子问题模型族突变 → 切换需在 H 显式记录触发条件

## 退出条件 (整个 stage 5)

1. 所有 Qi 通过 per-Qi rubric (全维 ≥7)
2. Stage-level rubric 全维 ≥7
3. 复用链满足 (题目允许时强制)
4. **每个 Qi 的 `sanity_check_status == "ok"`** (run_solver.py 自动校验通过)
5. (championship) red-team 一次,针对最弱的 Qi
6. 触发 L2: 跨阶段回检 stage 3 (模型选择前提是否被结果推翻) + stage 4 (符号一致性)

→ 跳转 `stage_06_robustness.md`

---

## 与 stage 6/8 的衔接

stage 6 全局灵敏度需要本节的求解器代码 (重用)。
stage 8 写论文 §5 直接基于本节产出, 每 Qi 一个小节。

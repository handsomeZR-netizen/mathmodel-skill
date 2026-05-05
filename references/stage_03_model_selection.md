---
stage: 3
name: model_selection
duration_h: 2-3
inputs: [stage.2.{decomposition, objective_per_subproblem, data_schema}]
outputs: [stage.3.{candidate_models, selected_per_subproblem, rejection_log, toy_demos_passed, red_team, model_family_consistency}]
loads_reference: [model_catalog.md, rubrics.md§Stage_3, winning_patterns.md§4]
loads_template: [code_starter/<problem_type>.py]
feedback: [L1, counterfactual_exploration_in_championship]
next: stage_04_foundation
---

# Stage 3 — 模型选型 (≥3 结构性不同候选)

**时长**: 2-3h | **反馈层**: L1 + 反事实探索 (championship 强制 ≥3 族不同)

---

## 目标

为每个子问题选定**1 个主模型 + ≥2 个明确否决的候选**,且主模型有命名变体 (winning_patterns §4)。整个论文的模型族保持一致(避免 stage 5 突然换库)。

---

## 输入

- stage 2 输出: 子问题卡片 + 目标函数雏形 + 数据 schema
- `references/model_catalog.md` 必读

## 产出

- 每个 Qi 的主模型 + 命名变体 + 选型理由
- 每个 Qi 的 ≥2 个否决候选 + 否决理由
- 求解可行性 50-line toy demo (Python)
- (championship) red-team 攻击与回应

---

## 操作流程

### Step 1: 问题类型映射 (10 min)

对每个 Qi,查 `model_catalog.md` §0 速查表:

```
Q1: "求最优生产计划" → 优化类 (LP/IP)
Q2: "考虑库存约束" → 优化类 (MIP) + 启发式
Q3: "随机需求下的稳健决策" → 鲁棒优化 / 随机规划 / 蒙特卡罗
```

### Step 2: 候选生成 ≥3 (45 min)

为每个 Qi 列 ≥3 个候选,**结构性不同**(championship 模式硬要求):

```
Q1 候选:
  候选 A: 整数线性规划 (优化族)
    - Python: cvxpy + GUROBI/CBC
    - 时间复杂度: 多项式可解
    - 优势: 解析解, 严谨
    - 风险: 数据规模大时求解慢
  
  候选 B: 遗传算法 (启发式族)
    - Python: deap
    - 时间: O(代数 × 种群)
    - 优势: 大规模可扩展
    - 风险: 不保证最优, 需调参
  
  候选 C: 拉格朗日松弛 + 列生成 (优化族变体)
    - 自实现
    - 优势: 大规模也能找到强对偶界
    - 风险: 实现复杂, 时间不够
```

**反模式 C3 检查**: 若三个候选都是同族 (都是优化 / 都是 ML),championship 模式 reject,要求换族。

### Step 3: 选型决策矩阵 (30 min)

为每个 Qi 做加权评分:

| 维度 | 权重 | 候选A | 候选B | 候选C |
|------|-----|------|------|------|
| 1. 适配度 (与问题契合) | 0.30 | 9 | 7 | 9 |
| 2. 求解可行性 (库支持/复杂度) | 0.25 | 8 | 9 | 5 |
| 3. 时间预算 (实施所需 h) | 0.20 | 8 | 7 | 4 |
| 4. 创新空间 (变体可能性) | 0.15 | 6 | 8 | 9 |
| 5. 文献支持 (参考资料) | 0.10 | 9 | 9 | 6 |
| **加权** | | **8.05** | **7.85** | **6.45** |

→ 选 候选 A (整数线性规划)。

### Step 4: 命名变体 (15 min) ⭐ 关键

不要用 "整数线性规划"。要起**改进名**:

模式: `<改进/限定词> + <核心模型> + <可选复合>`

候选名:
- "基于 Lagrangian 松弛的混合整数线性规划模型"
- "考虑动态约束的 MILP 优化模型"
- "二阶锥松弛改进 MILP"

最终选 1 个写入 `decision_log.stages.3.selected_per_subproblem.Q1`。

### Step 5: Toy Demo 验证 (45 min)

为每个 Qi 写 50 行 Python toy demo (用题目数据的 5% 子集):

```python
# Q1 toy demo - 验证 cvxpy 能跑通
import cvxpy as cp
import numpy as np

# 模拟参数
n = 5  # 真实是 100,这里用 5
p = np.random.rand(n) * 100
B = 200

x = cp.Variable(n, integer=True)
objective = cp.Maximize(p @ x)
constraints = [cp.sum(x) <= B, x >= 0, x <= 50]
prob = cp.Problem(objective, constraints)
prob.solve(solver=cp.GLPK_MI)

print("Q1 toy demo 通过, 求解时间:", prob.solver_stats.solve_time)
print("最优解:", x.value)
```

要求:
- 能跑通 (solver 找到解)
- 时间 < 30 秒
- 结果数量级合理

不通过 → 候选无效,回 Step 2 换。

### Step 6: 跨子问题模型族协调 (10 min)

检查三个 Qi 的主模型是否能"和谐共处":
- 都用 cvxpy 还是要换库? (统一更好)
- 都是优化族还是优化+仿真混合? (混合需要在 stage 5 显式说明触发条件)

写入 `decision_log.stages.3` 的 "model_family_consistency" 字段。

### Step 7 (championship 模式): Red-team 攻击 (30 min)

> 假装最严苛评委,列出本模型选择被 reject 的 ≥3 个最强理由,并给出**可信回应**。

例:
```
攻击 1: "你说用 MILP 但数据规模 1000+, 求解时间不可控"
回应: "已做 toy demo, 1000 规模在 GUROBI 下 < 5min;
      备用方案: GA 启发式 (候选 B) 已实现, 可作为 fallback"

攻击 2: "Q3 用蒙特卡罗, 但样本数 N 没说"
回应: "stage 5 会做 N=1000/5000/10000 收敛性测试, 
      取首个稳定 N (估计 2000) "

攻击 3: "命名 '改进 MILP', 改进点是什么?"
回应: "(a) Lagrangian 松弛降低规模, 
       (b) warm start 复用 Q1 解, 
       (c) 添加 Benders 切平面"
```

写入 `decision_log.stages.3.red_team`。

### Step 8: 输出移交 (10 min)

写入 `decision_log.stages.3`:
```json
{
  "candidate_models": [...],
  "selected_per_subproblem": {
    "Q1": {"name": "...", "library": "cvxpy", "rationale": "..."},
    "Q2": {...},
    "Q3": {...}
  },
  "rejection_log": [...],
  "toy_demos_passed": true,
  "red_team": [...],
  "model_family_consistency": "..."
}
```

---

## L1 Rubric

| 维度 | 满分行为 |
|------|---------|
| 1. 候选数量与多样性 | ≥3 + 结构性不同 |
| 2. 选型理由 | 每候选有适配 + 不选原因 |
| 3. 命名变体 | 入选模型 ≥1 修饰词 |
| 4. 求解可行性 | toy demo 通过 |
| 5. 文献支撑 | ≥2 篇引用 |

championship 额外: red_team 必须 ≥3 攻击且每个有可信回应。

## 常见坑

- C1 直接抄 textbook → Step 4 强制变体命名
- C2 模型不匹配 → Step 1 速查表对照
- C3 候选同族 → championship 强制
- C4 选型理由薄弱 → Step 3 5 维矩阵
- C5 不验证可行性 → Step 5 toy demo

## 退出条件

1. 每 Qi 选型完成 + 命名变体
2. 每 Qi 否决候选 ≥2 + 理由
3. toy demo 通过
4. (championship) red-team ≥3 攻击 + 回应
5. L1 全维 ≥7

→ 跳转 `stage_04_foundation.md`

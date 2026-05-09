"""
优化类 code starter — 对应论文 §5.x.2 求解算法
适用: 线性规划 (LP) / 整数规划 (IP/MILP) / 二次规划 (QP) / 凸优化

库依赖:
- cvxpy (DSL, 自动选择 solver)
- scipy.optimize (轻量级)
- pulp (MILP 备选)

国赛常见用法: 调度、配比、选址、组合优化
"""

import numpy as np
import pandas as pd
import cvxpy as cp
from scipy.optimize import linprog, minimize
import matplotlib.pyplot as plt
from pathlib import Path

# ---- 全局可复现性 ----
np.random.seed(42)

# ---- 输出目录自动创建 (P2-5 修复) ----
Path("results").mkdir(exist_ok=True)
Path("figures").mkdir(exist_ok=True)


# ============================================================
# 1. LP / MILP 模板 (cvxpy)
# ============================================================
def solve_milp_template(p, c, B, x_max=50):
    """
    最大化 sum_i (p_i - c_i) * x_i
    s.t.  sum_i c_i * x_i <= B
          0 <= x_i <= x_max, integer

    Args:
        p: ndarray (n,) 单价
        c: ndarray (n,) 成本
        B: float 总预算
        x_max: int 单品上限

    Returns:
        dict with keys: x_star, obj, status, solve_time
    """
    n = len(p)
    x = cp.Variable(n, integer=True)
    objective = cp.Maximize((p - c) @ x)
    constraints = [
        c @ x <= B,
        x >= 0,
        x <= x_max,
    ]
    prob = cp.Problem(objective, constraints)
    prob.solve(solver=cp.GLPK_MI)  # 也可用 cp.GUROBI / cp.CBC

    return {
        "x_star": x.value.astype(int) if x.value is not None else None,
        "obj": prob.value,
        "status": prob.status,
        "solve_time_s": prob.solver_stats.solve_time,
    }


# ============================================================
# 2. 凸优化模板 (cvxpy)
# ============================================================
def solve_convex_template(A, b, lambda_reg=0.1):
    """
    Ridge 回归示例:
    minimize ||A x - b||_2^2 + lambda * ||x||_2^2
    """
    n = A.shape[1]
    x = cp.Variable(n)
    objective = cp.Minimize(cp.sum_squares(A @ x - b) + lambda_reg * cp.sum_squares(x))
    prob = cp.Problem(objective)
    prob.solve()
    return {"x_star": x.value, "obj": prob.value, "status": prob.status}


# ============================================================
# 3. 多目标 (加权法) 模板
# ============================================================
def solve_multiobjective_weighted(objs, constraints, weights):
    """
    minimize sum_k w_k * f_k(x)

    Args:
        objs: list of cvxpy expressions, 每个是一个目标
        constraints: list of cvxpy constraints
        weights: list of float, 加权 (∑=1)
    """
    weighted_obj = sum(w * o for w, o in zip(weights, objs))
    prob = cp.Problem(cp.Minimize(weighted_obj), constraints)
    prob.solve()
    return prob


# ============================================================
# 4. 启发式 (遗传算法 GA, 自实现简化版)
# ============================================================
def genetic_algorithm(fitness, n_vars, bounds, n_pop=100, n_gen=200,
                      crossover_rate=0.8, mutation_rate=0.1):
    """
    自适应交叉率 GA (winning_patterns §4 命名变体写法)
    """
    pop = np.random.uniform(bounds[0], bounds[1], (n_pop, n_vars))
    best_history = []

    for gen in range(n_gen):
        scores = np.array([fitness(ind) for ind in pop])
        # 轮盘赌选择
        probs = scores / scores.sum() if scores.sum() > 0 else np.ones(n_pop) / n_pop
        indices = np.random.choice(n_pop, n_pop, p=probs)
        new_pop = pop[indices].copy()
        # 交叉
        for i in range(0, n_pop - 1, 2):
            if np.random.random() < crossover_rate:
                point = np.random.randint(1, n_vars)
                new_pop[i, point:], new_pop[i+1, point:] = \
                    new_pop[i+1, point:].copy(), new_pop[i, point:].copy()
        # 变异
        mask = np.random.random((n_pop, n_vars)) < mutation_rate
        noise = np.random.normal(0, 0.1, (n_pop, n_vars))
        new_pop = np.where(mask, new_pop + noise, new_pop)
        new_pop = np.clip(new_pop, bounds[0], bounds[1])
        pop = new_pop
        best_history.append(scores.max())

    best_idx = np.argmax([fitness(ind) for ind in pop])
    return {"x_star": pop[best_idx], "obj": fitness(pop[best_idx]), "history": best_history}


# ============================================================
# 5. Sanity check 套件 (anti_pattern D2)
# ============================================================
def sanity_check(result, expected_range=None, baseline=None):
    """
    四步 sanity check:
    1. 状态正常?
    2. 数量级合理?
    3. 边界 case?
    4. 比 baseline 强?
    """
    checks = {}
    checks["status_ok"] = result.get("status", "").lower() in ["optimal", "ok", "success"]
    if expected_range:
        x = result["x_star"]
        checks["range_ok"] = bool(np.all((x >= expected_range[0]) & (x <= expected_range[1])))
    if baseline is not None:
        checks["beats_baseline"] = result["obj"] > baseline
    return checks


# ============================================================
# 6. 主流程示例 (Q1 求解, 对应论文 §5.1)
# ============================================================
if __name__ == "__main__":
    # 加载数据 (示例数据, 实际从附件读)
    n = 100
    p = np.random.uniform(50, 200, n)
    c = np.random.uniform(20, 100, n)
    B = 100000

    # 求解
    result = solve_milp_template(p, c, B, x_max=50)
    print(f"Q1 状态: {result['status']}")
    print(f"Q1 最优利润: {result['obj']:.2f} 元")
    print(f"Q1 求解时间: {result['solve_time_s']:.2f} s")

    # Sanity check
    baseline_profit = ((p - c) * np.minimum(50, B // np.maximum(c, 1))).sum()
    checks = sanity_check(result, expected_range=(0, 50), baseline=baseline_profit)
    print(f"Sanity checks: {checks}")
    print(f"相对贪心 baseline 提升: {(result['obj'] - baseline_profit) / baseline_profit * 100:.2f}%")

    # 保存结果 (供 stage 6 灵敏度复用)
    np.save("results/Q1_x_star.npy", result["x_star"])

    # 可视化
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(range(n), result["x_star"], color='steelblue')
    ax.set_xlabel("产品编号")
    ax.set_ylabel("最优产量 (件)")
    ax.set_title("Q1 最优生产计划")
    plt.tight_layout()
    plt.savefig("figures/Q1_x_star.png", dpi=300)
    print("已保存 figures/Q1_x_star.png")

"""
仿真类 code starter — 对应论文 §5.x 仿真 / §6 灵敏度
适用: 蒙特卡罗 / 拉丁超立方采样 (LHS) / 系统动力学 ODE / Agent-based

国赛超高频: 与灵敏度分析联用 (winning_patterns §7 多变量联合扰动)
变体名建议: "拉丁超立方蒙特卡罗稳健性仿真"
"""

import numpy as np
import pandas as pd
from scipy.stats import qmc
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt
from pathlib import Path

np.random.seed(42)
Path("results").mkdir(exist_ok=True)
Path("figures").mkdir(exist_ok=True)


# ============================================================
# 1. 蒙特卡罗 (Monte Carlo) 基本框架
# ============================================================
def monte_carlo(simulator, n_samples=1000, **distributions):
    """
    Args:
        simulator: 单次仿真函数, 接受关键字参数, 返回标量或 dict
        n_samples: 样本数
        distributions: dict of {param_name: callable returning ndarray of size n}
    Returns:
        list of simulator return values
    """
    samples = {k: dist(n_samples) for k, dist in distributions.items()}
    results = []
    for i in range(n_samples):
        kwargs = {k: samples[k][i] for k in distributions}
        results.append(simulator(**kwargs))
    return results, samples


# ============================================================
# 2. 拉丁超立方采样 LHS  ⭐ 一等奖标配
# ============================================================
def lhs_sampling(d, n, bounds=None, seed=42):
    """
    Args:
        d: 维度 (扰动参数数量)
        n: 样本数
        bounds: list of (low, high) tuples, 长度 d. 默认 [0, 1]
    Returns:
        ndarray (n, d)
    """
    sampler = qmc.LatinHypercube(d=d, seed=seed)
    unit = sampler.random(n=n)  # ∈ [0, 1]^d
    if bounds is None:
        return unit
    lows = np.array([b[0] for b in bounds])
    highs = np.array([b[1] for b in bounds])
    return lows + unit * (highs - lows)


def joint_sensitivity_lhs(simulator, baseline_params, perturbation_levels=None, n_samples=200):
    """
    对所有 baseline_params 做联合 LHS 扰动 (winning_patterns §7)

    Args:
        simulator: callable(**params) -> scalar
        baseline_params: dict {param: baseline_value}
        perturbation_levels: list of perturbation ratios, e.g., [0.05, 0.10, 0.20]
        n_samples: per level
    Returns:
        dict {level: {"samples": ndarray, "outputs": ndarray, "stats": dict}}
    """
    if perturbation_levels is None:
        perturbation_levels = [0.05, 0.10, 0.20]

    param_names = list(baseline_params.keys())
    d = len(param_names)
    baseline_values = np.array([baseline_params[k] for k in param_names])

    results = {}
    for level in perturbation_levels:
        bounds = [(v * (1 - level), v * (1 + level)) for v in baseline_values]
        samples = lhs_sampling(d, n_samples, bounds)
        outputs = []
        for i in range(n_samples):
            params = {k: samples[i, j] for j, k in enumerate(param_names)}
            outputs.append(simulator(**params))
        outputs = np.array(outputs)
        stats = {
            "mean": outputs.mean(),
            "std": outputs.std(),
            "p5": np.percentile(outputs, 5),
            "p95": np.percentile(outputs, 95),
            "cv": outputs.std() / abs(outputs.mean() + 1e-12),
        }
        results[level] = {"samples": samples, "outputs": outputs, "stats": stats}
    return results, param_names


# ============================================================
# 3. Sobol 全局灵敏度 (championship 升级)
# ============================================================
def sobol_indices(simulator, param_names, baseline_params, n_samples=1024):
    """
    需要 SALib 库
    Returns: dict {param: {S1, ST}}
    """
    try:
        from SALib.sample import saltelli
        from SALib.analyze import sobol
    except ImportError:
        print("⚠ SALib 未安装, 跳过 Sobol")
        return None

    bounds = [[v * 0.8, v * 1.2] for v in baseline_params.values()]
    problem = {
        "num_vars": len(param_names),
        "names": param_names,
        "bounds": bounds,
    }
    samples = saltelli.sample(problem, n_samples)
    outputs = np.array([simulator(**dict(zip(param_names, s))) for s in samples])
    Si = sobol.analyze(problem, outputs, print_to_console=False)
    return {param: {"S1": float(Si["S1"][i]), "ST": float(Si["ST"][i])}
            for i, param in enumerate(param_names)}


# ============================================================
# 4. ODE 系统仿真 (e.g., 改进 SEIR, 国赛传染病题)
# ============================================================
def seir_with_quarantine(t, y, beta, sigma, gamma, kappa):
    """
    改进 SEIR 含潜伏期与隔离 (winning_patterns §4 命名变体)

    y = [S, E, I, R]
    """
    S, E, I, R = y
    N = S + E + I + R
    dS = -beta * S * I / N
    dE = beta * S * I / N - sigma * E
    dI = sigma * E - gamma * I - kappa * I  # kappa 是隔离率
    dR = gamma * I + kappa * I
    return [dS, dE, dI, dR]


def simulate_seir(N=10000, I0=10, beta=0.3, sigma=0.2, gamma=0.1, kappa=0.05, T=180):
    y0 = [N - I0, 0, I0, 0]
    sol = solve_ivp(seir_with_quarantine, (0, T), y0,
                     args=(beta, sigma, gamma, kappa), dense_output=True,
                     t_eval=np.arange(0, T + 1))
    return {"t": sol.t, "S": sol.y[0], "E": sol.y[1], "I": sol.y[2], "R": sol.y[3],
            "peak_I": sol.y[2].max(), "peak_t": sol.t[sol.y[2].argmax()]}


# ============================================================
# 5. 可视化辅助
# ============================================================
def plot_lhs_pairs(samples, outputs, param_names):
    """
    pairs plot (sensitivity_table.md 图 1)
    """
    df = pd.DataFrame(samples, columns=param_names)
    df["output"] = outputs
    try:
        import seaborn as sns
        g = sns.pairplot(df, diag_kind="kde", plot_kws={"alpha": 0.4})
        return g.fig
    except ImportError:
        # 备用: 简单矩阵
        d = len(param_names)
        fig, axes = plt.subplots(d, d, figsize=(d*3, d*3))
        for i in range(d):
            for j in range(d):
                if i == j:
                    axes[i, j].hist(samples[:, i], bins=20, color='steelblue')
                else:
                    axes[i, j].scatter(samples[:, j], samples[:, i],
                                        c=outputs, cmap='viridis', s=10, alpha=0.5)
                if i == d - 1:
                    axes[i, j].set_xlabel(param_names[j])
                if j == 0:
                    axes[i, j].set_ylabel(param_names[i])
        plt.tight_layout()
        return fig


def plot_tornado(sobol_result, output_label="目标函数"):
    """
    Tornado 图 (sensitivity_table.md 图 2)
    """
    sorted_items = sorted(sobol_result.items(), key=lambda x: x[1]["S1"])
    names = [item[0] for item in sorted_items]
    s1s = [item[1]["S1"] for item in sorted_items]
    sts = [item[1]["ST"] for item in sorted_items]

    y = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(y - 0.2, s1s, 0.4, label="一阶 $S_1$", color="steelblue")
    ax.barh(y + 0.2, sts, 0.4, label="总指数 $S_T$", color="orangered")
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlabel("Sobol 灵敏度指数")
    ax.set_title(f"{output_label} 单参数灵敏度排序")
    ax.legend()
    plt.tight_layout()
    return fig


# ============================================================
# 主流程示例 (对应论文 §5.x + §6)
# ============================================================
if __name__ == "__main__":
    # SEIR 仿真示例
    result = simulate_seir(N=10000, I0=10, beta=0.3, sigma=0.2, gamma=0.1, kappa=0.05)
    print(f"峰值感染数: {result['peak_I']:.0f}")
    print(f"峰值时间: 第 {result['peak_t']:.1f} 天")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(result["t"], result["S"], label="易感 S")
    ax.plot(result["t"], result["E"], label="潜伏 E")
    ax.plot(result["t"], result["I"], label="感染 I", color='red', lw=2)
    ax.plot(result["t"], result["R"], label="康复 R")
    ax.set_xlabel("时间 (天)")
    ax.set_ylabel("人数")
    ax.set_title("改进 SEIR 模型仿真")
    ax.legend()
    plt.tight_layout()
    plt.savefig("figures/simulation_seir.png", dpi=300)

    # LHS 联合灵敏度
    def simulator(beta, sigma, gamma, kappa):
        r = simulate_seir(beta=beta, sigma=sigma, gamma=gamma, kappa=kappa)
        return r["peak_I"]

    baseline = {"beta": 0.3, "sigma": 0.2, "gamma": 0.1, "kappa": 0.05}
    sens_results, param_names = joint_sensitivity_lhs(
        simulator, baseline, perturbation_levels=[0.05, 0.10, 0.20], n_samples=100
    )
    for level, r in sens_results.items():
        print(f"\n扰动 ±{level*100:.0f}%:")
        print(f"  Peak I 5%-95% 区间: [{r['stats']['p5']:.0f}, {r['stats']['p95']:.0f}]")
        print(f"  CV: {r['stats']['cv']*100:.2f}%")

    # 画 LHS pairs (取 ±10% 档)
    fig = plot_lhs_pairs(sens_results[0.10]["samples"],
                          sens_results[0.10]["outputs"], param_names)
    plt.savefig("figures/simulation_lhs_pairs.png", dpi=300)
    print("\n所有图已保存 figures/")

# 数学模型目录 (model_catalog)

> 60+ 常用数学建模方法,按问题类型组织。stage 3 模型选型时按"问题类型 → 候选族"映射查阅。每个模型给出: 适用场景 / 关键 Python 实现 / 命名变体示例 / 国赛常见用法。

---

## 0. 问题类型 → 模型族 速查表 (stage 3 第一步必查)

| 题目特征 | 推荐模型族 |
|---------|----------|
| "求最优..." / "如何分配..." / "在约束下使...最大" | **优化类** (LP/IP/NLP/启发式) |
| "预测..." / "未来..." / "时间序列" | **预测类** (回归/ARIMA/灰色/LSTM) |
| "评价..." / "排名..." / "综合得分" | **评价类** (AHP/TOPSIS/熵权/模糊) |
| "判断..." / "归类..." / "识别..." | **分类类** (Logistic/SVM/决策树/NN) |
| "模拟..." / "如果...会怎样" / "随机..." | **仿真类** (蒙特卡罗/系统动力学/ABM) |
| "网络中..." / "路径..." / "流量..." | **图论类** (最短路/最大流/最小生成树) |
| "概率..." / "分布..." / "假设检验" | **统计类** (描述统计/检验/方差分析) |
| "动态..." / "随时间..." | **动力系统类** (ODE/PDE/差分方程) |

---

## 1. 优化类 (Optimization)

### 1.1 线性规划 LP
- **适用**: 目标 + 约束都线性
- **Python**: `scipy.optimize.linprog`, `cvxpy`, `pulp`
- **变体名**: "考虑动态权重的多目标线性规划", "鲁棒线性规划"
- **国赛常见**: 调度、配送、资源分配 (e.g., 2023 B 题)

### 1.2 整数规划 IP / 0-1 规划
- **适用**: 决策变量取整数 / 0-1
- **Python**: `cvxpy + GUROBI/CBC`, `pulp`
- **变体名**: "基于分支定界的混合整数规划", "Lagrangian 松弛 IP"
- **国赛常见**: 选址、路径、组合 (e.g., 2024 B 题路径优化)

### 1.3 非线性规划 NLP
- **适用**: 目标或约束含非线性
- **Python**: `scipy.optimize.minimize` (SLSQP, trust-constr), `cvxpy` (DCP)
- **变体名**: "凸近似 NLP", "二阶锥规划 SOCP"

### 1.4 多目标规划
- **适用**: 多个相互冲突目标
- **方法**: 加权法 / ε-约束法 / NSGA-II
- **Python**: `pymoo`, `deap`
- **变体名**: "基于熵权的多目标规划", "Pareto-NSGA-II"
- **国赛常见**: 几乎每年出现

### 1.5 动态规划 DP
- **适用**: 阶段决策、最优子结构
- **Python**: 自实现 (numpy + memoization)
- **变体名**: "状态压缩动态规划", "近似动态规划 ADP"

### 1.6 启发式算法
- **遗传算法 GA**: `deap`, `pygad` — "自适应交叉率 GA"
- **粒子群 PSO**: `pyswarms` — "改进惯性权重 PSO"
- **模拟退火 SA**: 自实现 — "自适应温度 SA"
- **蚁群 ACO**: 自实现 — "信息素改进 ACO"
- **国赛常见**: 大规模组合优化、多峰目标

### 1.7 鲁棒优化 / 随机规划
- **适用**: 参数不确定
- **Python**: `cvxpy` (robust constraints), `Pyomo`
- **变体名**: "基于场景的随机规划", "Wasserstein 鲁棒优化"
- **国赛加分项**: 在灵敏度章节升级为正式建模

---

## 2. 预测类 (Prediction)

### 2.1 回归
- 线性: `sklearn.linear_model.LinearRegression`
- 多项式: `PolynomialFeatures + LinearRegression`
- 岭回归 / Lasso: `Ridge`, `Lasso`
- **变体名**: "弹性网回归", "贝叶斯线性回归"

### 2.2 时间序列经典
- ARIMA: `statsmodels.tsa.arima.model.ARIMA`
- SARIMA: 季节性 ARIMA
- 指数平滑 (Holt-Winters): `statsmodels.tsa.holtwinters`
- **变体名**: "差分整合移动平均自回归模型 (ARIMA)", "Holt-Winters 三参数指数平滑"

### 2.3 灰色预测
- GM(1,1): 自实现 (国赛常用,小样本预测)
- **变体名**: "残差修正 GM(1,1)", "GM(1,N) 多变量灰色模型"
- **国赛加分**: 与 ARIMA 对比验证

### 2.4 机器学习预测
- 随机森林: `sklearn.ensemble.RandomForestRegressor`
- XGBoost: `xgboost`
- LSTM: `tensorflow.keras` / `torch`
- **变体名**: "改进 LSTM-Attention 时序预测", "XGBoost-LightGBM Stacking"

### 2.5 组合预测
- **核心思想**: 多模型加权 (权重由误差倒数 / 熵权 / AHP 给出)
- **变体名**: "基于熵权的 ARIMA-LSTM 组合预测"
- **国赛加分**: 单一模型 → 组合,几乎是基础动作

---

## 3. 评价类 (Evaluation)

### 3.1 层次分析 AHP
- **核心**: 主观赋权,构造判断矩阵
- **Python**: 自实现 (numpy: 几何平均 + 一致性检验)
- **变体名**: "群决策 AHP", "动态权重 AHP"
- **国赛**: 90% 评价题会用,但单独用 = 平庸,需配 TOPSIS / 熵权

### 3.2 熵权法
- **核心**: 客观赋权,基于指标方差
- **Python**: 自实现 (numpy)
- **变体名**: "改进熵权法 (考虑指标相关性)"

### 3.3 TOPSIS
- **核心**: 与正负理想解的距离
- **Python**: 自实现
- **变体名**: "灰色关联 TOPSIS", "熵权 TOPSIS"
- **国赛常见**: 与 AHP/熵权组合 → "熵权-TOPSIS 综合评价模型"

### 3.4 模糊综合评价
- **适用**: 评价对象边界模糊
- **Python**: 自实现 (隶属函数 + 模糊矩阵)
- **变体名**: "二级模糊综合评价"

### 3.5 主成分分析 PCA
- **Python**: `sklearn.decomposition.PCA`
- **作用**: 降维 / 因子提取
- **变体名**: "鲁棒 PCA", "稀疏 PCA"

### 3.6 因子分析 / 聚类评价
- **Python**: `sklearn.cluster.KMeans`, `factor_analyzer`
- **变体名**: "基于 K-Means++ 的聚类评价"

---

## 4. 分类类 (Classification)

### 4.1 Logistic 回归
- **Python**: `sklearn.linear_model.LogisticRegression`
- **变体名**: "L1 正则化 Logistic", "多项 Logit"

### 4.2 支持向量机 SVM
- **Python**: `sklearn.svm.SVC`
- **变体名**: "RBF 核 SVM", "多分类 OVR-SVM"

### 4.3 决策树 / 随机森林 / GBDT
- **Python**: `sklearn.tree`, `sklearn.ensemble`, `xgboost`, `lightgbm`
- **变体名**: "代价敏感随机森林"

### 4.4 神经网络
- **Python**: `tensorflow.keras`, `torch`
- **变体名**: "ResNet 改进结构", "BP-Adam 反向传播"

### 4.5 朴素贝叶斯 / KNN
- **Python**: `sklearn.naive_bayes`, `sklearn.neighbors`
- 简单但 sanity check 用得上

---

## 5. 仿真类 (Simulation)

### 5.1 蒙特卡罗 MC
- **核心**: 大量随机采样估计
- **Python**: `numpy.random` + `scipy.stats`
- **变体名**: "拉丁超立方蒙特卡罗", "马尔可夫链 MCMC"
- **国赛**: 与灵敏度分析联用是基础

### 5.2 系统动力学 SD
- **适用**: 反馈、库存、流速
- **Python**: 自实现 (ODE) 或 Vensim
- **变体名**: "因果回路图 + 库存流图 SD 模型"

### 5.3 元胞自动机 CA
- **适用**: 空间扩散、交通流
- **Python**: 自实现 (numpy 数组迭代)
- **变体名**: "Nagel-Schreckenberg 交通流 CA"

### 5.4 Agent-Based Modeling ABM
- **Python**: `mesa`
- **变体名**: "基于学习智能体的 ABM"

### 5.5 离散事件仿真 DES
- **Python**: `simpy`
- **变体名**: "基于排队论的 DES"

---

## 6. 图论类 (Graph)

### 6.1 最短路
- Dijkstra / Floyd / A*
- **Python**: `networkx.shortest_path`

### 6.2 最大流 / 最小费用流
- **Python**: `networkx.maximum_flow`, `networkx.min_cost_flow`

### 6.3 最小生成树 MST
- Kruskal / Prim
- **Python**: `networkx.minimum_spanning_tree`

### 6.4 网络中心性 / 社团检测
- PageRank / Betweenness
- **Python**: `networkx.pagerank`, `community-louvain`

### 6.5 旅行商 TSP / VRP
- **Python**: `networkx.approximation.traveling_salesman`, `OR-Tools`
- **变体名**: "考虑时间窗的 VRPTW", "蚁群 VRP"

---

## 7. 统计类 (Statistics)

### 7.1 描述性统计
- 均值、方差、偏度、峰度、相关性
- **Python**: `pandas.describe`, `scipy.stats`

### 7.2 假设检验
- t 检验 / χ² / F 检验 / 秩和
- **Python**: `scipy.stats.ttest_*`, `chisquare`

### 7.3 方差分析 ANOVA
- 单因素 / 双因素 / 协方差
- **Python**: `scipy.stats.f_oneway`, `statsmodels.stats.anova`

### 7.4 相关与回归
- Pearson / Spearman / Kendall
- **Python**: `scipy.stats.pearsonr`

### 7.5 分布拟合
- 用 KS 检验拟合优度
- **Python**: `scipy.stats.kstest`, `fitter`

---

## 8. 动力系统类

### 8.1 常微分方程 ODE
- **Python**: `scipy.integrate.solve_ivp`
- 经典: SIR/SEIR (传染病)、Lotka-Volterra (生态)
- **变体名**: "改进 SEIR 含潜伏期与隔离", "随机 SDE"

### 8.2 偏微分方程 PDE
- **Python**: `fipy`, `fenics`, 自实现有限差分
- **国赛少见**, 但热扩散 / 流体题会用

### 8.3 差分方程
- 自实现迭代

---

## 9. 信号处理 / 时频分析

### 9.1 傅里叶变换 FFT
- **Python**: `numpy.fft`, `scipy.fft`

### 9.2 小波分析
- **Python**: `pywt`

---

## 10. 决策类

### 10.1 博弈论
- 纳什均衡: `nashpy`
- 多人合作博弈
- **变体名**: "Stackelberg 博弈"

### 10.2 决策树 (决策分析,非 ML)
- 期望效用 / 风险敏感

### 10.3 马尔可夫决策过程 MDP
- **Python**: `mdptoolbox`
- 强化学习: `stable-baselines3`

---

## 模型组合"加分公式" (一等奖常见 hybrid)

```
评价类: AHP + 熵权 + TOPSIS = "AHP-熵权-TOPSIS 综合评价"
预测类: ARIMA + 灰色 + LSTM = "ARIMA-GM-LSTM 组合预测"
优化类: 启发式 + 鲁棒 = "鲁棒-NSGA-II 多目标优化"
分类类: Stacking 集成 = "RF-XGBoost-LightGBM Stacking 分类"
仿真类: 蒙特卡罗 + 灵敏度 = "LHS-蒙特卡罗稳健性仿真"
```

---

## stage 3 选型 checklist

每个候选模型必须填:
- [ ] 来自哪个族 (1-10)
- [ ] 适配理由 (3 行)
- [ ] Python 实现路径 (库/自实现)
- [ ] 时间复杂度估算
- [ ] 命名变体 (≥1 修饰词)
- [ ] 不选的反候选 + 不选理由

3 个候选必须**结构性不同** (championship 模式强制)。

---

## §11 2023-2025 国赛历年题速查 (基于本地 91 篇 PDF)

**用法**: stage 1 选题 + stage 3 模型选型时, 若题目类型与历年相近, 优先参考下表 (本地 PDF 在 `references/papers/`)。

| 年份 | 题号 | 题目主题 | 核心问题类型 | 推荐模型族 | 本地 PDF 文件名前缀 (papers/) |
|------|------|---------|------------|----------|----------------------------|
| 2025 | A | 无人机烟幕干扰 | 优化 + 仿真 + 几何 | 三维几何 + 启发式 (PSO/GA) + 蒙特卡罗 | `2025-A*` |
| 2025 | B | 用户拉新 | 优化 + 网络 + 决策 | 整数规划 + 网络流 + 博弈 | `2025-B*` |
| 2025 | C | NIPT 时点选择 | 决策 + 概率 + 序贯 | 贝叶斯决策 + 序贯检验 + 蒙特卡罗 | `2025-C*` |
| 2025 | D | 钢板订单 | 优化 + 切割 | MILP + 二维 bin-packing + 启发式 | `2025-D*` |
| 2025 | E | 农作物种植 | 优化 + 多目标 + 鲁棒 | 多目标 LP + 鲁棒优化 + AHP-熵权 | `2025-E*` |
| 2024 | A | (具体题面见展廊) | 优化 + 仿真 | LP/MILP + 蒙特卡罗 | `2024-A*` |
| 2024 | B | (展廊) | 优化 + 启发式 | NSGA-II + 整数规划 | `2024-B*` |
| 2024 | C | (展廊) | 预测 + 评价 | ARIMA-LSTM 组合 + AHP-TOPSIS | `2024-C*` |
| 2024 | D | (展廊) | 优化 + 网络 | MILP + 图论 | `2024-D*` |
| 2024 | E | (展廊) | 评价 + 预测 | 熵权-TOPSIS + 灰色 GM(1,1) | `2024-E*` |
| 2023 | A | 表面温度场 / 几何优化 | 几何优化 + ODE | NLP + 有限差分 | `2023-A*` |
| 2023 | B | 多波束测线 | 几何 + 优化 | 几何模型 + 启发式 | `2023-B*` |
| 2023 | C | 蔬菜定价 | 预测 + 优化 | ARIMA + LP | `2023-C*` |
| 2023 | D | 圆形物体识别 (大数据组) | 图像处理 + 分类 | CNN + 形态学 | `2023-D*` |
| 2023 | E | 黄河水沙 | 预测 + 优化 | GM(1,1) + 多元回归 | `2023-E*` |
| 2023 | F | (大数据组) | 数据挖掘 | 多种 | `2023-F*` |

**注意**: 上表"题目主题"对 2024 仅给方向 (具体题面见教育部展廊 2024 PDF), 因为 2024 年部分题面未公开标准答案。建议直接打开对应 PDF 查阅。

**速查指引**:
1. 题目动词含"最优分配/调度/路径" → 看 2025-D / 2024-A/B/D / 2023-B
2. 题目动词含"预测/未来" → 看 2024-C / 2023-C/E
3. 题目动词含"评价/排名/打分" → 看 2024-E + AHP-TOPSIS 模板
4. 题目含"概率/不确定性/风险" → 看 2025-C/E + 2025-A 烟幕仿真
5. 题目含"图像/识别" → 看 2023-D (本年度大数据组特色)

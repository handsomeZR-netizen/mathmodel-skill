# 评分细则 (rubrics)

> 国赛官方评分维度 + 每个阶段的内部 5 维 rubric。L1 Critic 直接 JSON 化使用。

---

## 国赛官方评分维度 (论文最终态,占总分权重)

来源: 国赛组委会公布 + 评委复盘文章。

| 维度 | 权重 | 关键检查项 |
|------|-----|----------|
| **摘要质量** | 30% | 5 段结构 / 量化结果 / 创新表述 / 字数 600-900 |
| **模型建立** | 25% | 与问题契合 / 假设有支撑 / 数学严谨 / 命名变体 |
| **求解与结果** | 20% | 算法合理 / 代码可复现 / 结果可视化 / 物理意义 |
| **写作呈现** | 15% | 章节完整 / 公式编号规范 / 图表清晰 / 语言流畅 |
| **创新性** | 10% | 模型变体命名 / 跨学科融合 / 子问题复用 |

(注: 不同年份权重微调 ±5%,但摘要 ≥25%、模型 ≥20% 是稳定的。)

---

## L1 阶段级 rubric (5 维 × 1-10)

每阶段产出后,Critic 输出以下 JSON:

```json
{
  "stage_id": 0-9,
  "iteration": 0-3,
  "scores": {
    "<dim_key_snake_case>": {"name": "中文名称", "score": 1-10, "evidence": "≤30字"},
    ...
  },
  "min_score": <number>,
  "mean_score": <number>,
  "issues": [
    {"severity": "high|medium|low", "where": "...", "anti_pattern_id": "A1|null", "fix": "..."},
    ...
  ],
  "verdict": "block | pass_early | pass | refine"
}
```

**dim key 命名约定**: 各 stage 的 5 个 `scores` 字段必须用**英文 snake_case**, 与 `feedback_layer1_critic.md §6` 各 stage 列出的固定集合精确一致 (`scripts/score_artifact.py` 加白名单校验)。下面各 stage 表第一列写中文是为了人读, 实际 JSON 输出用英文 key, **中文写在 `name` 子字段**。

退出条件: 见本文件末尾"阈值汇总"节, 与 SKILL.md / feedback_layer1_critic.md / score_artifact.py 三处统一。

---

### Stage 0 — 团队启动

| 维度 | 满分行为 (10) | 失败行为 (1) |
|------|-------------|-------------|
| 1. 角色分工明确性 | 建模/编程/写作 三人各有主责且互备 | 全员都"什么都做" |
| 2. 工具就绪度 | Python/LaTeX/Git/通讯工具 全员可用 | 临场装环境 |
| 3. 时间盒规划 | 3 天每 6h 一个 milestone,有 buffer | 无计划 |
| 4. 题目预扫信号 | 已识别问题域 (优化/预测/评价等) | 未读题 |
| 5. 协作约定 | 命名规范、版本控制、daily standup 时间 | 无规范 |

---

### Stage 1 — 选题

| 维度 | 满分行为 |
|------|---------|
| 1. 三题对比深度 | 三题各列 5+ 评估点 (难度/数据/契合度/工具/参考资料) |
| 2. 团队优势匹配 | 选题理由含"我们擅长 X,本题需要 X" |
| 3. 风险识别 | 列出 ≥3 个本题潜在坑及预案 |
| 4. 时间可行性 | 已估各阶段所需 h,合计 ≤72h |
| 5. 决策记录质量 | rationale + rejected_alternatives 都有 ≥3 行依据 |

退出条件: 选定题号 + decision_log.json stage 1 节点完整 + 全维 ≥7。

---

### Stage 2 — 问题深度解析

| 维度 | 满分行为 |
|------|---------|
| 1. 子问题分解清晰度 | 每个 sub-problem 的输入/输出/约束明确 |
| 2. 关键变量识别 | 列出 ≥10 个变量,标注决策变量/状态变量/参数 |
| 3. 数学化程度 | 每个 sub-problem 至少有目标函数雏形 (符号级,不必精确) |
| 4. 数据契合度 | 题目附件数据已扫描,与变量映射清楚 |
| 5. 子问题关联性 | 已识别 Q3 是否依赖 Q1/Q2 (一等奖必查) |

---

### Stage 3 — 模型选型

| 维度 | 满分行为 |
|------|---------|
| 1. 候选数量与多样性 | ≥3 个候选,且**结构性不同** (e.g., 优化 vs 仿真 vs 统计) |
| 2. 选型理由 | 每个候选有 (a) 适配理由 (b) 不选的原因 |
| 3. 命名变体 | 入选模型有 ≥1 修饰词 (e.g., "改进的"/"动态的"/"混合的") |
| 4. 求解可行性 | 已确认 Python 库存在 + 时间复杂度可承受 |
| 5. 文献支撑 | 至少 2 篇引用支持选型 (题目领域内) |

championship 模式额外: red-team "假装最严苛评委,本模型选择被 reject 的最强理由?" → 必须有可信回应。

---

### Stage 4 — Foundation (假设 + 符号 + 术语)

| 维度 | 满分行为 |
|------|---------|
| 1. 假设数量 | 3-7 条 (太少→不严谨,太多→模型脆弱) |
| 2. 假设支撑 | 每条配 (a) 文献 / (b) 数据观察 / (c) 物理意义 三选一 |
| 3. 符号唯一性 | 同一符号不同含义 = 0 分;每符号有单位 |
| 4. 与模型一致性 | stage 5 后回检,无矛盾 |
| 5. 术语规范 | 专业术语首次出现给定义,中英对照 |

---

### Stage 5 — 子问题递归循环 (per Qi)

每个 sub-problem 跑一次 5 维 rubric,**外加** stage-level overall:

#### Per-Qi rubric:

| 维度 | 满分行为 |
|------|---------|
| 1. 模型与问题契合 | 目标函数 / 决策变量 / 约束 与题面一一对应 |
| 2. 数学严谨性 | 推导无跳跃,符号一致,边界条件齐全 |
| 3. 求解正确性 | 代码可运行,结果数量级合理,通过 sanity check |
| 4. 结果可视化 | ≥2 图 (流程图 + 结果图) + 1 表 |
| 5. 物理意义讨论 | 数值 → 现实含义 (≥1 段文字) |

#### Stage-level (跨子问题):

- **复用链**: Q3 是否调用 Q1/Q2 结果?题目允许时**强制要求**
- **变量一致性**: 不同子问题间变量符号统一

退出条件: 所有 Qi 通过 + 复用链满足 + 全维 ≥7。

---

### Stage 6 — 全局灵敏度 / 稳健性

| 维度 | 满分行为 |
|------|---------|
| 1. 多变量联合扰动 | ≥3 参数同时变化,使用拉丁超立方或 Sobol |
| 2. 扰动幅度合理 | ±5%/±10%/±20% 三档,且最大档对应实际不确定性范围 |
| 3. 输出指标完备 | 关键决策变量 + 关键性能指标都报告 |
| 4. 稳健区间定量 | 给出 "在 X 范围内变化 → 结果偏差 < Y" |
| 5. 失稳预警 | 识别 ≥1 个临界参数 (越过则模型失效),并在评价节讨论 |

L2 触发: 末尾跨阶段回检 stage 3 的模型选择前提是否被本节结果推翻。

---

### Stage 7 — 模型评价 + 推广

| 维度 | 满分行为 |
|------|---------|
| 1. 优点具体 | ≥3 条优点,每条配 1 个具体证据 (数据/实验/对比) |
| 2. 缺点真实 | ≥3 条缺点,每条 (a) 命名替代方法 (b) 估算改进幅度 (c) 说明代价 |
| 3. 改进方向 | 给出 ≥2 条可执行的改进路径 (含数据/算力/时间需求估算) |
| 4. 推广场景 | ≥2 个跨领域应用举例 + 适配性说明 |
| 5. 自我批判可信度 | 不写"假设理想化"等套话 (anti_patterns.md 自动检) |

---

### Stage 8 — 论文写作

| 维度 | 满分行为 |
|------|---------|
| 1. 摘要 5 段式 | 完整 5 段,字数 600-900,定量结果 ≥3 |
| 2. 章节完整性 | 8 章 + 附录全到位,无空节 |
| 3. 公式 / 图表 / 引用 | 编号规范,首次引用先解释,GB/T 7714 引用格式 |
| 4. 语言质量 | 句长适度,无明显语病 (phrase_bank 关键词命中率) |
| 5. 视觉一致性 | 字号/配色/字体 全文统一,无 Word/Excel 默认输出 |

---

### Stage 9 — 终稿审核

5 视角 panel (Layer 3),每个 panelist 独立打分:

| Panelist | 关注 |
|----------|------|
| **数学严谨** | 定理引用、推导、边界条件、单位 |
| **模型创新** | 命名变体、跨学科、文献新颖度 |
| **代码正确** | 复现性、注释、变量名、可读性 |
| **写作呈现** | 摘要、章节、图表、引用、配色 |
| **评委视角** | 30 秒能不能 get 到核心? "想给一等奖的冲动" |

每位 panelist 输出:
```json
{"panelist": "...", "scores": {dim1..dim5}, "verdict": "first|second|third|sub_award", "must_fix": [...]}
```

聚合器:
- 找最低分 panelist 的 must_fix
- 定向重跑对应阶段一次
- 重跑后再次 panel,若仍未达标则提交 (时间预算优先)

---

## 阈值汇总 (与 SKILL.md / feedback_layer1_critic.md / score_artifact.py 统一)

**verdict 优先级 (从高到低)**:

| verdict | 触发条件 | 行为 |
|---------|---------|-----|
| `block` | issues 含 ≥1 high-severity | 暂停 skill, 用户介入 |
| `pass_early` | min ≥ 9 AND mean ≥ 9 | iter-1 早退, 节省 token |
| `pass` | min ≥ 7 AND mean ≥ 8 | 进下一阶段 |
| `refine` | 其他 | section-patch 精修, iter+=1 (cap 3) |
| `carryover` | iter == 3 仍 refine | 进下一阶段, 标记由 L2 处理 |

**与等级对应** (用于评估 / 不直接驱动 verdict):
| 大致等级 | 单维最低 | 均值 |
|---------|---------|------|
| 一等奖 | ≥8 | ≥9 |
| 二等奖 | ≥7 | ≥8 |
| 三等奖 | ≥6 | ≥7 |
| 不达标 | <6 | - |

---

## 与 winning_patterns / anti_patterns / empirical_distribution 的对应

本文件 rubric 项 ↔ `winning_patterns.md` 段落 (各 stage rubric 表后已 inline 标注):
- abstract.* (stage 8 dim 1) → patterns §1, §9 + anti_patterns §A
- paper.section_completeness (stage 8 dim 2) → patterns §2 + anti_patterns §I
- paper.figure_density → patterns §3 + anti_patterns §E
- model.naming (stage 3 dim 3) → patterns §4 + anti_patterns §C1
- subproblems.cross_reference (stage 5 stage-level dim 2) → patterns §5 + anti_patterns §G
- assumptions.support (stage 4 dim 2) → patterns §6 + anti_patterns §B
- sensitivity.multivariate (stage 6 dim 1) → patterns §7 + anti_patterns §F
- evaluation.limitations_real (stage 7 dim 2) → patterns §8 + anti_patterns §H

**硬阈值** (字数/图表数/公式数) 评分时, evidence 字段引用 `empirical_distribution.md` 实测 p25/p50/p75 而非估计值。
- evaluation.real_critique → patterns §8

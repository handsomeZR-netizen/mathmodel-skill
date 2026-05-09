---
name: mathmodel-skill
description: 数学建模竞赛端到端工作流, 三竞赛通用 (CUMCM 国赛 / MCM 美赛 / 电工杯). 10 阶段 + 4 反馈层, 题型 dim 加权, per-Qi 差异化降级, 实测分位锚定打分. 三种模式 fast(2h)/standard(6h)/championship(12h). 触发: 用户提到 "建模/数模/CUMCM/国赛/MCM/ICM/美赛/电工杯/A题/B题/C题/cumcm-modeling", 或在 mathmodel-skill 目录下工作.
---

# mathmodel-skill — 数学建模 三竞赛通用 Skill

10 阶段把"3-4 天打 1 篇竞赛论文"工程化。每阶段产出经过 rubric 自评 + section-level patch 精修, 跨阶段一致性回检, 终局多视角 panel。三竞赛通用框架 + 国赛 91 篇真烘焙 + MCM/电工杯 seed v0.1。

---

## 路径解析协议 (任何阶段必读)

| 类型 | 位置 | 例 |
|------|------|-----|
| skill 内通用 | skill 根目录的相对路径 | `references/stage_05.md`, `templates/shared/decision_log.json` |
| **竞赛特化** | `competitions/<comp>/...` 按 decision_log.competition dispatch | `competitions/cumcm/winning_patterns.md`, `competitions/mcm/abstract_template.md` |
| **LaTeX 模板** | `templates/latex/<comp>/` | `templates/latex/cumcm/cumcmthesis/`, `templates/latex/mcm/main.tex` |
| 用户产物 | 用户 `cwd/` 相对路径 | `cwd/state/`, `cwd/results/`, `cwd/figures/`, `cwd/paper_workspace/` |
| state 持久化 | `cwd/state/decision_log.json` | 各 stage 必读必写 |
| 环境变量 | `MATHMODEL_STATE_DIR` (兼容 `CUMCM_STATE_DIR`) / `MATHMODEL_COMPETITION` 可覆盖 | scripts 用此变量 |

约定: `<skill>/` = skill 安装目录, `<cwd>/` = 用户 cwd, `<comp>/` = 当前竞赛 (cumcm | mcm | diangong)。

---

## Quick Start (用户首次说"开始建模")

```
1. 一段话介绍 (≤50 字): "启动数学建模工作流, 10 阶段 + 三竞赛."

2. 一次性 5 问 (用 AskUserQuestion 单条消息):
   - 竞赛 (cumcm 国赛 / mcm 美赛 / diangong 电工杯, 默认 cumcm)
   - 题号 (依竞赛: cumcm A-E / mcm A-F / diangong A-B)
   - 队员数 + 各人擅长 (建模/编程/写作)
   - 截止时间 (ISO 字符串)
   - 题目 PDF 路径 ("未公布"亦可)

3. 自动初始化:
   - 不存在 cwd/state/decision_log.json → cp <skill>/templates/shared/decision_log.json
   - 写入 decision_log.competition = <选定竞赛>
   - 已存在 → 读 current_stage 字段决定恢复点

4. 加载 competitions/<comp>/winning_patterns.md 一次 (建立基线), 后续不再读

5. 进入 Stage 0 (references/stage_00_kickoff.md), 不重复问已问过的问题
```

**已有 state 触发** (用户中途回到 skill):
```
1. 读 cwd/state/decision_log.json 的 competition 与 current_stage
2. 加载对应 stage_NN.md (按需结合 competitions/<comp>/* 内容)
3. 不重复读 winning_patterns
```

---

## 三竞赛 × 三模式 矩阵

时长 / 语言 / 模板 / 数据状态 由 competition 决定; token 预算 / 反馈深度由 mode 决定。两者**正交组合**。

| Competition | 时长 | 语言 | LaTeX | 子问数 IQR | 数据状态 |
|---|---|---|---|---|---|
| cumcm | 72h | 中文 | xelatex / cumcmthesis | [3, 5] | stable (91 篇 2023-2025) |
| mcm | 96h | English | pdflatex / article | [3, 6] | seed v0.1 |
| diangong | 72h | 中文 | xelatex / ctex | [6, 8] | seed v0.1 |

| Mode | Token | 反馈层 | 用途 |
|---|---|---|---|
| fast | ≤ 50k | L1 单次 | 选题试跑 / sanity check |
| standard | ≤ 200k | L1+L2 | 默认主流程 |
| championship | ≤ 500k | L1+L2+L3+L4 + red-team | 提交前最后冲刺 |

模式自动推荐 (按距 deadline 剩余):
- > 60h: standard (最后 6h 升 championship)
- 24-60h: standard
- 6-24h: fast 关键阶段 + championship 终审
- < 6h: 直接进 stage 9 (championship)

---

## 10 阶段索引

| # | 阶段 | reference | 时长 | 反馈 | 竞赛差异点 |
|---|------|-----------|------|------|-----------|
| 0 | 团队启动 + 资料预扫 | `stage_00_kickoff.md` | 1h | L1 | 时长 / 语言 / 编译器 / 题号体系 |
| 1 | 选题 (多题对比 → 1) | `stage_01_problem_selection.md` | 2-4h | L1 | 题号体系 (A-E/A-F/A-B) + task_type 写入 |
| 2 | 问题深度解析与分解 | `stage_02_analysis.md` | 2-3h | L1 | 通用 |
| 3 | 模型选型 (≥3 候选) | `stage_03_model_selection.md` | 2-4h | L1 + 反事实 | 通用 |
| 4 | Foundation (假设+符号+术语) | `stage_04_foundation.md` | 1h | L1 | 通用 |
| 5 | **递归子问题循环** Q1..Qn + per-Qi 加权聚合 | `stage_05_subproblem_loop.md` | 6-12h × n | L1 + 子检查点 | 子问数差异 (cumcm 4 / mcm 4 / diangong 7); per-Qi 加权 |
| 6 | 全局灵敏度 / 稳健性 | `stage_06_robustness.md` | 2-3h | L1 + L2 | 工程参数 (diangong) vs 数学参数 (cumcm/mcm) |
| 7 | 模型评价 + 推广 | `stage_07_evaluation.md` | 1-2h | L1 | 通用 |
| 8 | 论文写作 | `stage_08_writing.md` | 12-30h | L1 | 摘要类型 (5段 / 1-page+Letter / 4段) + LaTeX 模板 |
| 9 | 终稿审核 + Panel | `stage_09_review.md` | 2-6h | L1 + L3 panel | anti_patterns + panel personas 各异 |

---

## 加载协议 (节省 token 的关键)

**只在进入阶段 N 时加载** `references/stage_NN_*.md`。**切勿**一次性全读。

各阶段额外加载 (按需 + 按 competition 切换):
- 每阶段开头: `cwd/state/decision_log.json` 必读
- 每阶段结尾: `cwd/state/decision_log.json` 必写 (核心决策 + 5 维评分)
- stage 1-9: `references/rubrics.md` 对应章节 (L1 评分用)
- **stage 1**: `competitions/<comp>/topic_specs.json` (题号 → task_type 映射)
- stage 3, 5: `references/model_catalog.md` (跨竞赛通用)
- **stage 5**: per-Qi 评分跑完后调 `scripts/score_artifact.py --mode aggregate_qi` 聚合
- **stage 8**: `competitions/<comp>/{winning_patterns, phrase_bank, abstract_template, paper_skeleton}.md`
- **stage 8 硬阈值评分**: `competitions/<comp>/empirical.json` 注入 evidence (cumcm 真值; mcm/diangong seed 自动带 [seed: ...] 标记)
- **stage 9**: `competitions/<comp>/anti_patterns.md` (逐条对照) + `rubric_overlay.json` 的 panel_personas
- 触发反馈时: 对应 `references/feedback_layer*.md`

---

## 收敛准则 (统一定义, 三处一致)

**verdict 优先级 (从高到低)**:

| verdict | 触发 | 行为 |
|---------|------|------|
| `block` | issues 含 ≥1 high-severity | 暂停 skill, 用户介入 |
| `pass_early` | raw_min ≥ 9 AND weighted_mean ≥ 9 | iter-1 早退 |
| `pass` | raw_min ≥ 7 AND weighted_mean ≥ 8 | 进下一阶段 |
| `pass_with_review` *(stage 5)* | 任 Qi mark_for_review 但加权阈值满足 | 进 stage 6, L2 必读 review_qis |
| `refine` | 其他 | section-patch 精修, iter+=1 (cap 3) |
| `refine_partial` *(stage 5)* | 任 Qi.min < 7, 其他 Qi 已 pass | 仅 refine 该 Qi, 不动其他 |
| `carryover` | iter == 3 仍 refine | 进下一阶段, 标记由 L2 处理 |

`weighted_mean` = Σ(s_i × w_i) / Σ(w_i), 权重来自 `config/dim_weights.json[<comp>][<task_type>]` (clamp [0.7, 1.5]); `task_type=default` 全 1.0 等价老逻辑。

此定义在 `feedback_layer1_critic.md` / `rubrics.md` / `scripts/score_artifact.py` 三处必须**完全一致**。

---

## 状态持久化

每阶段:
- 开头: `Read cwd/state/decision_log.json`, 核对 current_stage 与上下文
- 结尾: 更新 stage 节点 (核心决策 + 摒弃方案 + 评分), `current_stage += 1`

`decision_log.json` v3.0 schema 关键字段 (与 `templates/shared/decision_log.json` 对齐):
- root: `competition`, `task_type`, `mode`, `current_stage`, `budget`, `events`
- stage_5 扩展: `qi_count`, `qi_weights`, `qi_status`
- scores 扩展: 含 `weighted_mean`, `review_qis`, `refine_qis` (stage 5 加权聚合用)

L2 跨阶段回检 (stage 5/6/8 末尾) 读这个文件主动找冲突, 触发**定向回滚**: 不重做整阶段, 只针对冲突点。

---

## Token 预算纪律

- L1 Critic 强制 JSON 输出, ~500 token/次
- 精修策略: section-level patch (`scripts/extract_diff.py`), 不重传完整 artifact (省 ~60% token)
- references/ 与 competitions/ 文件**懒加载**, 本 SKILL.md 主体 ≤ 6k tokens
- 阶段完成后, artifact 摘要 + 关键数据 + 路径写入 decision_log, 不在上下文保留全文
- 超预算 30% → 自动降级 (championship → standard, standard → fast)

---

## 用户指令快捷

- "进入 stage N" / "重做 stage N" → 跳转
- "切到 mcm" / "切到 cumcm" / "切到 diangong" → 改 decision_log.competition (注意已有 state 兼容性)
- "升级到 championship" → 启用 L3 + L4 + red-team
- "切到 fast" → 关闭迭代
- "回退到 stage M" → 读 decision_log, 回退 current_stage 并清理 ≥M 节点
- "做 L2 回检" → 立即触发 cross-stage backtrack
- "看进度" → 输出 decision_log 摘要 + 当前评分

---

## 数据来源声明

- `competitions/cumcm/`: 91 篇真国赛 2023-2025 PDF 烘焙 (`empirical.json` 含 11 维 p25/p50/p75); 91 PDF 已存档不读, 仅蒸馏 markdown
- `competitions/mcm/`: SEED v0.1, 基于 COMAP 公开 scoring rubric + Outstanding Winner 公开模式手写; empirical 占位
- `competitions/diangong/`: SEED v0.1, 基于历年题量 + 公开评审标准估算; empirical 占位
- 通用模型清单 `references/model_catalog.md` 跨竞赛复用

后续如有 30+ MCM Outstanding 或电工杯一等奖 PDF, 可用 `scripts/ingest_papers.py --competition <comp>` 重新烘焙覆盖 seed。

---

## 与外部资源的关系

skill 自包含, 运行时不联网。下列离线资源可作人工补充:
- 国赛: `personqianduixue/Math_Model`, `datawhalechina/intro-mathmodel`, `dxs.moe.gov.cn` 优秀论文展廊
- 美赛: COMAP 官网 `comap.com`, `MCM Tutorial` (Frank Giordano)
- 电工杯: 中国电机工程学会论文集

---
name: cumcm-modeling
description: 全国大学生数学建模竞赛 (国赛 CUMCM) 端到端工作流。从选题到终稿审核共 10 个阶段, 每阶段带 rubric 自评迭代, 跨阶段一致性回检, 终局 5 视角 panel。三种模式 fast(2h)/standard(6h, 默认)/championship(12h, 含红队对抗)。触发: 用户提到"国赛/数模/CUMCM/数学建模/A题/B题/C题", 或在数学建模skill 目录下工作。
---

# CUMCM 数学建模 全流程 Skill

10 阶段把"3 天打一篇国赛一等奖论文"工程化。每阶段产出经过 rubric 自评 + section-level patch 精修, 跨阶段一致性回检, 终局 5 视角 panel。一等奖共性已预先 anchored, 避免 rubric 漂移。**实测分布数据见 `references/empirical_distribution.md`** (从 91 篇真国赛获奖论文烘焙)。

---

## 路径解析协议 (任何阶段必读)

| 类型 | 位置 | 例 |
|------|------|-----|
| **skill 内文件** | skill 根目录的相对路径 | `references/winning_patterns.md`, `templates/decision_log.json` |
| **用户产物** | 用户 `cwd/` 相对路径 | `cwd/state/`, `cwd/results/`, `cwd/figures/`, `cwd/paper_workspace/` |
| **state 持久化** | `cwd/state/decision_log.json` | 各 stage 必读必写 |
| **环境变量** | `CUMCM_STATE_DIR` 可覆盖 cwd/state/ | scripts 用此变量 |

约定: `<skill>/` = skill 安装目录, `<cwd>/` = 用户当前工作目录。

---

## Quick Start (用户首次说"开始建模")

**严格按此状态机**, 不要重复问问题:

```
1. 一段话介绍 (≤50 字): "启动 CUMCM 建模工作流, 10 阶段含自反馈循环。"

2. 一次性 4 问 (用 AskUserQuestion 单条消息):
   - 题号 (A/B/C/D/E)
   - 队员数 + 各人擅长 (建模/编程/写作)
   - 截止时间 (ISO 字符串)
   - 题目 PDF 路径 (没有则填 "未公布")

3. 自动初始化:
   - 检查 cwd/state/decision_log.json 是否存在
   - 不存在 → cp <skill>/templates/decision_log.json cwd/state/decision_log.json
   - 已存在 → 读 current_stage 字段决定恢复点

4. 读 references/winning_patterns.md 一次 (建立基线), 后续不再读

5. 进入 Stage 0 (references/stage_00_kickoff.md), 不要再问任何已问过的问题
```

**已有 state 触发** (用户中途回到 skill):
```
1. 读 cwd/state/decision_log.json 的 current_stage
2. 加载对应 stage_NN.md
3. 不重复读 winning_patterns
```

---

## 模式自动推荐 (按距 deadline 剩余小时数)

| 剩余 | 推荐 |
|------|------|
| > 60h | standard (最后 6h 升 championship) |
| 24-60h | standard |
| 6-24h | fast 关键阶段 + championship 终审 |
| < 6h | 直接进 stage 9 终审 (championship) |

---

## 三种运行模式

### `fast` — ~2h, 预算 ≤ 50k tokens
- L1 单次 critic, 不迭代
- 不加载 phrase_bank.md / anti_patterns.md
- 用途: 选题阶段试跑 / Q1 sanity check / 备选方案快速对比

### `standard` (默认) — ~6h, 预算 ≤ 200k tokens
- **L1**: 每阶段最多 3 次迭代, iter-1 全维 ≥9 即早退
- **L2**: 在 stage 5/6/8 末尾跑跨阶段一致性回检
- **L3 panel**: stage 9 末尾跑一次, 5 视角独立打分, 定向重跑最弱阶段一次

### `championship` — ~12h, 预算 ≤ 500k tokens
- L1 + L2 同 standard
- **+ Adversarial red-team**: stage 3、5、9 各一次"假装最严苛评委"
- **+ L4 校准**: 在 stage 3/5/6/8/9 各抽查 1 个 rubric 维度, Δ>2 则该维度被 gamed, 重置
- **+ 反事实探索**: stage 3 强制生成 ≥3 种**结构性不同**模型族
- 用途: 提交前最后 6 小时全力打磨

---

## 10 阶段索引

| # | 阶段 | reference 文件 | 时长 | 反馈层 |
|---|------|---------------|------|--------|
| 0 | 团队启动 + 资料预扫 | `references/stage_00_kickoff.md` | 1h | L1 |
| 1 | 选题 (3 题对比 → 1) | `references/stage_01_problem_selection.md` | 2-3h | L1 |
| 2 | 问题深度解析与分解 | `references/stage_02_analysis.md` | 2-3h | L1 |
| 3 | 模型选型 (≥3 结构性不同候选) | `references/stage_03_model_selection.md` | 2-3h | L1 + 反事实 |
| 4 | Foundation (假设+符号+术语) | `references/stage_04_foundation.md` | 1h | L1 |
| 5 | **递归子问题循环** Q1..Qn | `references/stage_05_subproblem_loop.md` | 6-12h × n | L1 + 子检查点 |
| 6 | 全局灵敏度 / 稳健性 | `references/stage_06_robustness.md` | 2-3h | L1 + L2 |
| 7 | 模型评价 + 推广 + 自批判 | `references/stage_07_evaluation.md` | 1-2h | L1 |
| 8 | 论文写作 (摘要最后写) | `references/stage_08_writing.md` | 12-16h | L1 |
| 9 | 终稿审核 + 视觉化润色 | `references/stage_09_review.md` | 2-4h | L1 + L3 panel |

每个 stage 文档头部含 YAML frontmatter (inputs/outputs/loads/next), Claude 进入时只需读 frontmatter 即可知加载什么。

---

## 加载协议 (节省 token 的关键)

**只在进入阶段 N 时加载** `references/stage_NN_*.md`。**切勿**一次性全读。

各阶段额外加载 (按需):
- **每个阶段开头**: `cwd/state/decision_log.json` 必读
- **每个阶段结尾**: `cwd/state/decision_log.json` 必写 (核心决策 + 5 维评分)
- **stage 1-9**: `references/rubrics.md` 对应章节 (L1 评分用)
- **stage 3, 5**: `references/model_catalog.md` (含 §11 历年题速查)
- **stage 8**: `references/winning_patterns.md` + `references/phrase_bank.md`
- **stage 9**: `references/anti_patterns.md` (逐条对照)
- **触发反馈时**: 对应 `references/feedback_layer*.md`
- **硬阈值评分时** (字数/图表数等): 引用 `references/empirical_distribution.md` 的实测 p 分位

---

## 收敛准则 (统一定义)

**verdict 优先级 (从高到低)**:
```
1. block:        critique.issues 含 high-severity → 必须修, 暂停 skill
2. pass_early:   min ≥ 9 且 mean ≥ 9             → iter-1 早退
3. pass:         min ≥ 7 且 mean ≥ 8             → 进下一阶段
4. refine:       否则                            → diff/section-patch 精修, iter+=1, cap 3
5. carryover:    iter == 3 仍未 pass             → 标记, 进下一阶段, L2 处理
```

此定义在 `feedback_layer1_critic.md` / `rubrics.md` / `scripts/score_artifact.py` 三处必须**完全一致**。

---

## 状态持久化 (跨阶段一致性的命脉)

每个阶段:
- **开头**: `Read cwd/state/decision_log.json`, 核对 current_stage 与上下文
- **结尾**: 更新 `cwd/state/decision_log.json` 当前 stage 节点 (核心决策 + 摒弃方案 + 评分), `current_stage += 1`

`decision_log.json` schema 包含每个 stage_NN 文档实际写入的所有字段 (`templates/decision_log.json` 已对齐)。

L2 跨阶段回检 (stage 5/6/8 末尾) 读这个文件, 主动找冲突:
- stage 4 假设的某个变量在 stage 5 被改名 / 改含义?
- stage 3 模型选型前提在 stage 6 灵敏度结果中被推翻?
- stage 5 各 Qi 之间是否复用了变量?

冲突触发**定向回滚**: 不重做整阶段, 只针对冲突点。

---

## Token 预算纪律

- **L1 Critic** 强制 JSON 输出 (`feedback_layer1_critic.md` 给出 schema), ~500 token/次
- **精修策略**: section-level patch 模式 (extract_diff.py), 不重传完整 artifact (省 ~60% token)
- references/ 文件**懒加载**, 本 SKILL.md 主体保持 < 5k tokens
- 阶段完成后, 把 artifact "摘要 + 关键数据 + 路径"写入 decision_log, 不在上下文保留全文

超预算 30% → 自动降级 (championship → standard, standard → fast)。

---

## 一等奖差异化能力 (Skill 主动驱动的 7 个高杠杆)

beginners 与 一等奖论文的 7 个差距, 每个都映射到 `rubrics.md` 具体 rubric 项, Skill 在对应阶段主动 push:

1. **量化的摘要** (stage 8): 摘要必须含 ≥3 个具体数值结果
2. **命名的模型变体** (stage 3): 即使经典模型, 起改进名 ("动态权重 AHP" 而非 "AHP")
3. **多变量联合灵敏度** (stage 6): ≥3 个参数同时变化, 不只 OAT
4. **子问题复用** (stage 5): Q3 必须在某处调用 Q1 或 Q2 的结果
5. **每子问题视觉三件套** (stage 5/8): 流程图 + 结果图 + 灵敏度图
6. **真实自我批判** (stage 7): ≥3 条真实局限性, 不写套话
7. **物理意义讨论** (stage 5/8): 数值结果 → 现实含义, 不只"误差 < X"

---

## 用户指令快捷

- "进入 stage N" / "重做 stage N" → 跳转
- "升级到 championship" → 启用 L3 + L4 + red-team
- "切到 fast" → 关闭迭代
- "回退到 stage M" → 读 decision_log, 回退 current_stage 并清理 ≥M 的 stage 节点
- "做 L2 回检" → 立即触发 cross-stage backtrack
- "看进度" → 输出 decision_log 摘要 + 当前评分

---

## 与外部资源的关系

本 skill 自包含, 运行时不联网。下列离线资源可作人工补充:
- `personqianduixue/Math_Model` (LaTeX + 算法)
- `datawhalechina/intro-mathmodel` (10 章建模教程)
- `zhanwen/MathModel` (按模型分类的论文集)
- 教育部 `dxs.moe.gov.cn` (优秀论文展廊)
- 国赛官网 `mcm.edu.cn` (评分细则、历年题)

`references/papers/` 已含 91 篇真国赛 PDF (2023-2025), 仅做静态资料 + 一次性烘焙到 `empirical_distribution.md`, **运行时不读**避免污染上下文。

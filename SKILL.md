---
name: mathmodel-skill
description: CUMCM 国赛、MCM/ICM 美赛与电工杯数学建模竞赛的端到端协作工作流。Use when a user explicitly works on one of these modeling contests or asks to run/review a modeling-competition paper from problem selection through modeling, solving, robustness, writing, compliance, and final submission review. Provides 10 stages, persistent decision state, competition-specific rules/templates, deterministic scoring helpers, numbered decisions, and Codex/Claude Code handoff. Do not trigger for generic model selection, ordinary data analysis, or non-competition paper review.
---

# mathmodel-skill — 数学建模三竞赛工作流 (v6.2)

10 阶段把 72–96 小时的竞赛协作变成可恢复、可检查的流程。用户回答关键问题，agent 维护状态与脚本。每阶段产出经过 rubric 自评、定向精修与跨阶段一致性回检；Stage 8–9 先遵守当届官方规则，再做多视角终审。CUMCM 包含 91 份来源文档，其中 59 份进入文本统计；MCM/电工杯经验统计明确为 `n=0`，不提供合成分位。

**v6.2 更新**: 新增 `scripts/init_workspace.py`（只创建、不覆盖的工作区初始化）与 `scripts/status.py`（只读进度看板：阶段 verdict、per-Qi、合规门、截止倒计时、模式建议与下一步）；启动与“看进度”改由脚本确定性完成。v6.1 的规则基线、AI 披露链路、fail-closed 模板与 doctor 预检保持不变。

---

## Codex 原生入口

Codex 优先按 skill 目录发现本文件:

- 用户级安装: `$HOME/.agents/skills/mathmodel-skill/`
- 项目级安装: `<repo>/.agents/skills/mathmodel-skill/`
- UI 元数据: `agents/openai.yaml`
- 插件分发元数据: `.codex-plugin/plugin.json` + `skills/mathmodel-skill/SKILL.md` shim
- 项目指导: `AGENTS.md` 仍可作为 repo / workspace 级 instructions, 但不是唯一入口

当 skill 已安装后, 用户可直接说"开始建模"或显式说"使用 `$mathmodel-skill` 开始建模"。

---

## Harness 兼容 (Claude Code / Codex)

本 skill v6.2 以 Codex Skills 为一等入口, 同时保持 harness-agnostic 设计:

| harness | 入口文件 | 用户交互工具 | 状态文件 |
|---------|---------|-------------|---------|
| Claude Code | `SKILL.md` (本文件) | `AskUserQuestion` 工具 | `<cwd>/state/decision_log.json` |
| Codex CLI / Codex app | skill 目录中的 `SKILL.md` + 可选 `AGENTS.md` | markdown 编号列表 | 同上 (**互通**) |

跨 harness 互通: day 1 用 Codex 跑 stage 0-2, day 2 切回 Claude Code 接着 stage 3+, 状态完全保留。详见 `references/harness_compat.md`。

---

## 问答式优先 (Friendly Mode)

**核心原则**: 用户只需回答**编号问题**, 不应被要求手敲 bash / python / json。

- 离散选项 (选竞赛 / 选题 / 选模型 / verdict 决策) → **必须**用问答式
- 自由文本 (PDF 路径 / 截止时间) → 单行回复
- 状态读写 (decision_log.json) → agent 自动完成
- 每个 stage 的关键决策点都有 "让我决定 (推荐 X)" 兜底选项

优先使用当前 harness 可用的原生选择 UI；没有时回退到 markdown 编号列表。两者语义等价，见 `references/harness_compat.md` §1。

---

## 路径解析协议 (任何阶段必读)

| 类型 | 位置 | 例 |
|------|------|-----|
| skill 内通用 | skill 根目录的相对路径 | `references/stage_05_subproblem_loop.md`, `templates/shared/decision_log.json` |
| **竞赛特化** | `competitions/<comp>/...` 按 decision_log.competition dispatch | `competitions/cumcm/winning_patterns.md`, `competitions/mcm/abstract_template.md` |
| **LaTeX 模板** | `templates/latex/<comp>/main.tex` | `templates/latex/cumcm/main.tex`, `templates/latex/mcm/main.tex` |
| 用户产物 | 用户工作目录的相对路径 | `<cwd>/state/`, `<cwd>/results/`, `<cwd>/figures/`, `<cwd>/paper_workspace/` |
| state 持久化 | `<cwd>/state/decision_log.json` | 各 stage 必读必写 |
| 环境变量 | `MATHMODEL_STATE_DIR` (兼容 `CUMCM_STATE_DIR`) / `MATHMODEL_COMPETITION` 可覆盖 | scripts 用此变量 |

约定: `<skill>/` = skill 安装目录, `<cwd>/` = 用户 cwd, `<comp>/` = 当前竞赛 (cumcm | mcm | diangong)。

---

## Quick Start (用户首次说"开始建模")

```
1. 一段话介绍 (≤50 字): "启动数学建模工作流, 10 阶段 + 三竞赛, 全程问答式."

2. 收集下列 5 个启动字段；用户已经提供或 state 已记录的字段不再询问，只把尚缺字段合并成一轮问答 (Claude Code: AskUserQuestion; Codex: 编号列表):
   - 竞赛 (cumcm 国赛 / mcm 美赛 / diangong 电工杯, 默认 cumcm)
   - 题号 (依竞赛: cumcm A-E / mcm A-F / diangong A-B; "未公布"亦可)
   - 队员数 + 各人擅长 (建模/编程/写作)
   - 截止时间 (ISO 字符串或 "距现在 X 小时")
   - 题目 PDF 路径 ("未公布"亦可)

3. 自动初始化 (agent 自动完成, 不要让用户编辑 json):
   - 运行 `python <skill>/scripts/init_workspace.py --competition <comp> --workspace <cwd>`，按已知答案追加 `--problem <题号|未公布>`、`--team-size N`、`--deadline <ISO>` 或 `--hours-left H`、`--problem-pdf <path>`
   - 脚本创建 `state/ results/ figures/ paper_workspace/ paper_output/ support_materials/`，从模板生成 state 并写入 competition 与 problem_meta
   - state 已存在时脚本**不修改**任何内容，只报告 competition 与 current_stage；竞赛不一致时失败，按“切到 <comp>”处理
   - 脚本输出的模式建议只是建议；与用户确认后才改 mode 并写入 events
   - 无法运行 Python 时，才手动复制 `<skill>/templates/shared/decision_log.json` 并写入 competition

4. 加载 `competitions/<comp>/current_rules.md`（若存在），打开其中官方链接核对当届规则并写入 compliance；再按需加载 winning patterns

5. 进入 Stage 0 (`references/stage_00_kickoff.md`), 不重复问已知字段；若题面未公布，完成环境与协作准备后保持 `qi_count=null` 并等待题面，不进入 Stage 1
```

**已有 state 触发** (用户中途回到 skill):
```
1. 运行 `python <skill>/scripts/status.py --workspace <cwd> --json` 取得 competition、current_stage、最新 verdict 与下一步；需要细节时再读 `<cwd>/state/decision_log.json`
2. 加载对应 stage_NN.md (按需结合 competitions/<comp>/* 内容)
3. 不重复读 winning_patterns
```

---

## 三竞赛 × 三模式 矩阵

时长 / 语言 / 模板 / 数据状态 由 competition 决定; token 预算 / 反馈深度由 mode 决定。两者**正交组合**。

| Competition | 时长 | 语言 | LaTeX | 规则基线 | 经验数据状态 |
|---|---|---|---|---|---|
| cumcm | 72h | 中文 | xelatex / 原创 ctexart | CUMCM 2026 | 91 来源文档 / 59 可提取样本 |
| mcm | 96h | English | pdflatex / article | COMAP 2027 | `n=0`，无论文分位 |
| diangong | 72h | 中文 | xelatex / ctex | 官网 2026-03-21 页面 | `n=0`，无论文分位 |

| Mode | 上下文策略 | 反馈层 | 用途 |
|---|---|---|---|
| fast | 只保留当前阻断项与最小证据 | L1 单次 | 选题试跑 / sanity check |
| standard | 按阶段加载并保留决策摘要 | L1+L2 | 默认主流程 |
| championship | 在终审阶段扩展证据与独立视角 | L1+L2+L3+L4 + red-team | 提交前最后冲刺 |

模式自动推荐 (按距 deadline 剩余；`scripts/status.py` 按同一规则计算，仅作建议):
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
| 3 | 模型选型 (证据驱动的候选比较) | `stage_03_model_selection.md` | 2-4h | L1 + 反事实 | 通用 |
| 4 | Foundation (假设+符号+术语) | `stage_04_foundation.md` | 1h | L1 | 通用 |
| 5 | **递归子问题循环** Q1..Qn + per-Qi 加权聚合 | `stage_05_subproblem_loop.md` | 按题目分配 | L1 + 子检查点 | 从题面提取实际子问数；per-Qi 加权 |
| 6 | 全局灵敏度 / 稳健性 | `stage_06_robustness.md` | 2-3h | L1 + L2 | 工程参数 (diangong) vs 数学参数 (cumcm/mcm) |
| 7 | 模型评价 + 推广 | `stage_07_evaluation.md` | 1-2h | L1 | 通用 |
| 8 | 论文写作 + 合规装配 | `stage_08_writing.md` | 12-30h | L1 + L2 | 当届规则、AI 披露、摘要类型与 LaTeX 模板 |
| 9 | 提交合规 + Panel | `stage_09_review.md` | 2-6h | L1 + L3 panel | 页数/匿名/披露 + anti-patterns + personas |

---

## 加载协议 (节省 token 的关键)

**只在进入阶段 N 时加载** `references/stage_NN_*.md`。**切勿**一次性全读。

各阶段额外加载 (按需 + 按 competition 切换):
- 每阶段开头: `<cwd>/state/decision_log.json` 必读
- 每阶段结尾: `<cwd>/state/decision_log.json` 必写 (核心决策 + 5 维评分)
- stage 1-9: `references/rubrics.md` 对应章节 (L1 评分用)
- **stage 1**: `competitions/<comp>/topic_specs.json` (题号 → task_type 映射)
- stage 3, 5: `references/model_catalog.md` (跨竞赛通用)
- **stage 5**: per-Qi 评分跑完后调 `scripts/score_artifact.py --mode aggregate_qi` 聚合
- **stage 0 / 8 / 9**: `competitions/<comp>/current_rules.md` 存在时读取，并核对其中官方链接
- **stage 8**: `competitions/<comp>/{winning_patterns, phrase_bank, abstract_template, paper_skeleton}.md`
- **stage 8 经验锚点**: `competitions/<comp>/empirical.json` 只作评分前参考；CUMCM 为 59 份可提取样本的观察分位，MCM/电工杯为 `n=0` 占位且不得推断数值门槛
- **stage 9**: 先做规则合规门，再用 `anti_patterns.md` 与 `rubric_overlay.json` 的 panel personas
- 触发反馈时: 对应 `references/feedback_layer*.md`
- harness 适配差异 (Codex 用户必读): `references/harness_compat.md`

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
- 开头: 读取 `<cwd>/state/decision_log.json`, 核对 current_stage 与上下文
- 结尾: 更新 stage 节点 (核心决策 + 摒弃方案 + 评分), `current_stage += 1`

`decision_log.json` v3.1 schema 关键字段 (与 `templates/shared/decision_log.json` 对齐):
- root: `competition`, `task_type`, `mode`, `current_stage`, `budget`, `events`, `compliance`
- stage_5 扩展: `qi_count`, `qi_weights`, `qi_status`
- scores 扩展: 含 `weighted_mean`, `review_qis`, `refine_qis` (stage 5 加权聚合用)

L2 跨阶段回检 (stage 5/6/8 末尾) 读这个文件主动找冲突, 触发**定向回滚**: 不重做整阶段, 只针对冲突点。

---

## 上下文预算纪律

- L1 Critic 强制 JSON 输出, ~500 token/次
- 精修策略: section-level patch (`scripts/extract_diff.py`), 优先只传相关 section
- references/ 与 competitions/ 文件**懒加载**, 本 SKILL.md 主体 ≤ 6k tokens
- 阶段完成后, artifact 摘要 + 关键数据 + 路径写入 decision_log, 不在上下文保留全文
- 只有当前 harness / API 提供可靠 usage 时才记录 token 消耗；不可观测时保留为 `null`，不得估算成已用额度
- 上下文压力或剩余时间不足时，向用户建议从 championship → standard → fast 降级，并把确认后的 mode change 写入 events；不要声称已自动计量或静默切换

---

## 用户指令快捷

- "进入 stage N" / "重做 stage N" → 跳转
- "切到 mcm" / "切到 cumcm" / "切到 diangong" → 改 decision_log.competition (注意已有 state 兼容性)
- "升级到 championship" → 启用 L3 + L4 + red-team
- "切到 fast" → 关闭迭代
- "回退到 stage M" → 读 decision_log, 回退 current_stage 并清理 ≥M 节点
- "做 L2 回检" → 立即触发 cross-stage backtrack
- "看进度" → 运行 `python <skill>/scripts/status.py --workspace <cwd> --markdown`，原样展示看板与下一步 (只读，不改 state)

---

## 数据来源声明

- `competitions/cumcm/`: 91 份来源文档，59 份成功文本提取并进入观察分位；现有提取有局限，不能解释为官方阈值或获奖预测
- `competitions/mcm/`: 规则基线已按 COMAP 2027 核对；经验模式是维护者启发，empirical 为 `n=0`
- `competitions/diangong/`: 官网参赛规则与论文规范已于 2026-07-22 核对；经验模式是维护者启发，empirical 为 `n=0`
- 通用模型清单 `references/model_catalog.md` 跨竞赛复用

当前 `scripts/ingest_papers.py` 是维护期归档工具，不能直接重建三个竞赛包的 `empirical.json`。新增语料前先补来源 provenance、提取 QA 与分组样本量。

---

## 与外部资源的关系

核心工作流可离线运行；当届规则与问题要求必须从官方来源重新核对。下列资源可作人工补充:
- 国赛: `personqianduixue/Math_Model`, `datawhalechina/intro-mathmodel`, `dxs.moe.gov.cn` 优秀论文展廊
- 美赛: COMAP 官网 `comap.com`, `MCM Tutorial` (Frank Giordano)
- 电工杯: 中国电机工程学会论文集

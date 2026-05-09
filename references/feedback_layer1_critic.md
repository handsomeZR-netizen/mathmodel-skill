# Feedback Layer 1 — 阶段级 Critic + diff-only 精修

> 每阶段产出后立即触发。强制结构化 JSON 输出。预算: ~500 token/次评分, 最多迭代 3 次。

---

## 协议

### 1. 触发时机

每个 stage_NN 走完 Step "输出移交" 后, 进入 L1:

```
artifact_v0 = current_stage_output
critique_v0 = layer1_critic(artifact_v0, rubric=rubrics.md[stage_NN])

if critique_v0.verdict == "pass":
    save & next stage
elif critique_v0.verdict == "refine":
    for i in 1..3:
        artifact_vi = refine_with_diff_only(artifact_v(i-1), critique_v(i-1))
        critique_vi = layer1_critic(artifact_vi, rubric)
        if critique_vi.verdict == "pass": break
        if iter == 3: mark_as_carryover & next stage  # 留给 L2
elif critique_v0.verdict == "block":
    halt & report to user (high-severity 必须人工介入)
```

### 2. Critic Prompt 模板

```
You are a strict {competition_label} grader for stage {stage_id} ({stage_name}).
Score the artifact below against the 5-dim rubric.

Competition: {competition} (cumcm | mcm | diangong)
Task type: {task_type} (e.g. A_optimization, C_data, F_policy)
{task_type_weighting_hint}   # 见 §3.6, e.g. "重点考察 X (×1.4), 次要 Y (×0.8)"

Rubric (from `references/rubrics.md` + `competitions/{competition}/rubric_overlay.json`):
{rubric_5_dims}

Reference patterns (from `competitions/{competition}/winning_patterns.md`):
{relevant_patterns}

Anti-patterns to check (from `competitions/{competition}/anti_patterns.md`):
{relevant_anti_patterns}

{empirical_hint}   # 见 §3.5, 评硬阈值时拉 competitions/{competition}/empirical.json 注入

Artifact:
{artifact_content_or_path}

OUTPUT EXACTLY THIS JSON, NO OTHER TEXT:
{
  "stage_id": <int>,
  "iteration": <int>,
  "variant": "stage_level" | "per_qi",   // stage 5 必填; 其他阶段可省, 默认 "stage_level"
  "qi_id": "Q1" | "Q2" | ... | null,      // 仅 variant="per_qi" 时必填
  "scores": {
    "1_<dim_name>": {"score": <int 1-10>, "evidence": "<≤30字>"},
    "2_<dim_name>": {...},
    "3_<dim_name>": {...},
    "4_<dim_name>": {...},
    "5_<dim_name>": {...}
  },
  "min_score": <int>,
  "mean_score": <float>,
  "issues": [
    {
      "severity": "high" | "medium" | "low",
      "where": "<具体定位, e.g. §5.1.2 公式 (5.3)>",
      "anti_pattern_id": "<e.g. A1, B5>" | null,
      "fix": "<≤50 字, 具体可执行>"
    }
    // 0-5 个
  ],
  "evidence_metrics": {            // 可选, 见 §3.5; 评硬阈值维度时填.
    "abstract_chars": <int>,        // critic 实测的 artifact 摘要字数
    "formula_count": <int>,         // 公式数, 等等
    "figure_count": <int>,
    "reference_count": <int>
    // 仅评 stage 8 / 9 时填; 其他 stage 留空
  },
  "verdict": "pass_early" | "pass" | "pass_with_review" | "refine" | "refine_partial" | "block"
}
```

**dim key 命名**: 形如 `1_role_clarity`、`2_tools_ready` ……, 数字前缀固定 1-5, 后接 §6 对应 stage 给的英文 snake_case 名。`scripts/score_artifact.py:DIM_WHITELIST` 严格按此校验, 写错即报 "dim key 不匹配"。

### 3. Verdict 规则

**优先级从高到低 (顺序不可变, 否则 pass_early 永远不触发)**:

```python
def verdict(scores, issues, weights=None):
    """
    weights: 题型 dim 权重表 (e.g. config/dim_weights.json[cumcm][A_optimization]["3"]).
             dim 不在表中时按 1.0 处理. 加权 mean = Σ(s_i × w_i) / Σ(w_i).
             min 不加权 (仍是 'any dim too low' 触发器).
             权重 clamp 到 [0.7, 1.5] 防过激.
    """
    raw_min = min(scores.values())
    if weights:
        weighted_mean = sum(s * weights.get(d, 1.0) for d, s in scores.items()) / sum(weights.get(d, 1.0) for d in scores)
    else:
        weighted_mean = mean(scores.values())
    high_issues = [i for i in issues if i["severity"] == "high"]

    if len(high_issues) >= 1:
        return "block"               # 含高严重 issue, 暂停 skill
    if raw_min >= 9 and weighted_mean >= 9:
        return "pass_early"          # iter-1 早退, 节省 token
    if raw_min >= 7 and weighted_mean >= 8:
        return "pass"                # 进下一阶段
    return "refine"                  # section-patch 精修, iter+=1
```

**Stage 5 多 Qi 场景额外 verdict** (由 `compute_stage5_verdict` 聚合, 见 §6 Stage 5):
| verdict | 触发条件 | 行为 |
|---------|---------|------|
| `pass_with_review` | 任 Qi.min ≥ 7 且 Qi.mean < 8 (mark_for_review), 但加权 stage_min ≥ 7 且 weighted_mean ≥ 8 | 进 stage 6, L2 必读 review_qis |
| `refine_partial` | 任 Qi.min < 7, 但其他 Qi 已 pass | 只 refine 该 Qi, 不动其他 Qi |

**carryover 规则** (在 iter == max_iter 即 3 次后由调度器决定, critic 不直接输出此 verdict):
```
if iter == 3 and verdict in ("refine", "refine_partial"): → 标记 carryover, 进下一阶段, L2 处理
```

此定义与 `SKILL.md` "收敛准则" / `rubrics.md` 阈值汇总 / `scripts/score_artifact.py compute_verdict` + `compute_stage5_verdict` **必须完全一致**。

### 3.5. 实测分位注入协议 (empirical injection)

L1 critic 评硬阈值维度时 (字数 / 公式数 / 图表数 / 引用数), evidence 字段不再写"推荐 600-900 字"这种估计值, 改注入 `competitions/<competition>/empirical.json` 的实测 p25/p50/p75:

**critic 输入扩展**: `score_artifact.py` 在 evaluate 时若 critique 含 `evidence_metrics: {dim_key: value}`, 自动调用 `inject_evidence(dim_key, value, empirical, by_topic)`。

**注入格式**:
```
abstract_chars: value=720, p50=992, IQR=[748, 1146] (by topic A), status=低于 p25
```

种子版本 (mcm / diangong empirical.source.status="seed_v0.1") 自动追加 `[seed: 阈值未实测分位]` 标记, critic 见此应**弱化数值评判, 强化模式匹配**。

**字段映射** (示例 stage 8):
| critic dim | empirical.json key | 由 by_topic 进一步细化 |
|---|---|---|
| 1_abstract_5_paragraph (字数维度) | abstract_chars | 是 (A/B/C/D/E/F) |
| 3_formulas_figures_citations (公式数) | formula_count | 是 |
| 3_formulas_figures_citations (图数) | figure_count | 是 |
| 3_formulas_figures_citations (引用数) | reference_count | 否 |

### 3.6. 题型加权协议 (task_type dim weights)

`decision_log.task_type` 由 stage 1 选题后填入 (e.g. `A_optimization` / `C_data` / `mcm:F_policy`)。`score_artifact.py` 加载 `config/dim_weights.json[competition][task_type]` 拿到 stage→dim→weight 表, 应用到 verdict 计算。

**critic prompt 扩展** (在 stage 评分时, prompt 模板自动附加):
```
本题为 {competition}/{task_type}, 重点考察:
- {dim_with_high_weight_1} (×{weight_1})
- {dim_with_high_weight_2} (×{weight_2})
次要: {dim_with_low_weight_1} (×{weight_1})
其他维度按默认 1.0 评估。
```

**示例** (cumcm/C_data, stage 6):
> 本题为 cumcm/C_data, 重点考察: 多变量灵敏度 (×1.4), 输出完备性 (×1.2). 其他维度按默认 1.0 评估。

权重 clamp 到 [0.7, 1.5] 防止过激扭曲分布。`task_type=default` 全 1.0, 等价老逻辑。

### 4. Diff-only 精修协议

**关键**: 不要把整个 artifact 重新生成! 只精修 issues 指出的部分。

精修 prompt:
```
The previous artifact had these issues:
{issues_json}

Generate a UNIFIED DIFF (git-style) that fixes them.
Do not rewrite anything not directly mentioned in issues.

Output format:
```diff
--- artifact_v{i-1}
+++ artifact_v{i}
@@ -section_anchor @@
- old_line
+ new_line
```
```

应用 diff 后得到 `artifact_v{i}`, 重新跑 critic。

**Token 节省**: diff 通常 < 500 tokens, 远小于完整 artifact 的 5-20k。

### 5. 与 anti_patterns.md 的联动

Critic 在 `issues` 数组中可以直接引用 anti_pattern ID:

```json
{
  "severity": "high",
  "where": "§5.1.3 物理意义段",
  "anti_pattern_id": "E1",
  "fix": "数值结果后增加 1 段现实含义讨论, 至少 80 字"
}
```

`E1` 自动展开为 `anti_patterns.md` 里的完整描述与修复路径。

### 6. 各阶段 Critic 模板细节

#### Stage 0
```json
"scores": {
  "1_role_clarity": {...},
  "2_tools_ready": {...},
  "3_time_planning": {...},
  "4_problem_scan": {...},
  "5_collab_protocol": {...}
}
```
关键 anti_patterns: J1, J2, J3

#### Stage 1
```json
"scores": {
  "1_three_options_depth": {...},
  "2_team_strength_match": {...},
  "3_risk_identification": {...},
  "4_time_feasibility": {...},
  "5_decision_record_quality": {...}
}
```
关键: 决策记录质量

#### Stage 2
```json
"scores": {
  "1_subproblem_decomposition": {...},
  "2_key_variables_count": {...},
  "3_math_skeleton_present": {...},
  "4_data_alignment": {...},
  "5_subproblem_dependency_identified": {...}
}
```
关键: G1 (子问题各做各)

#### Stage 3
```json
"scores": {
  "1_candidate_diversity": {...},
  "2_selection_rationale": {...},
  "3_naming_variant": {...},
  "4_solver_feasibility": {...},
  "5_literature_support": {...}
}
```
关键: C1 (无改进), C3 (候选同族), C5 (不验证可行性)

#### Stage 4
```json
"scores": {
  "1_assumption_count": {...},
  "2_assumption_support": {...},
  "3_symbol_uniqueness": {...},
  "4_consistency_with_model": {...},
  "5_terminology_standard": {...}
}
```
关键: B1, B4, B5

#### Stage 5 (Per-Qi) — `variant: "per_qi"`, 每个子问题 Qi 各跑一次
```json
{
  "stage_id": 5,
  "variant": "per_qi",
  "qi_id": "Q1",
  "scores": {
    "1_problem_fit": {...},
    "2_math_rigor": {...},
    "3_solve_correctness": {...},
    "4_visualization": {...},
    "5_physical_meaning": {...}
  }
}
```
关键: D1-D5 全套, E1-E4

#### Stage 5 (Stage-level) — `variant: "stage_level"`, 所有 Qi 跑完后 1 次
```json
{
  "stage_id": 5,
  "variant": "stage_level",
  "scores": {
    "1_subproblem_completeness": {...},
    "2_cross_reference_chain": {...},
    "3_symbol_consistency": {...},
    "4_visual_density": {...},
    "5_time_budget": {...}
  }
}
```
关键: G1, G2

**Stage 5 调用顺序**: 先对每个 Qi 跑 per-Qi critic (写入 `decision_log.scores["5_per_qi"]`, 标 qi_id), 全部 Qi pass 后再跑 stage-level critic (写入 `decision_log.scores["5"]`)。两轨互不覆盖。

**Stage 5 per-Qi 加权聚合** (v3.0 新增): 当所有 per-Qi critic 跑完, 调用 `score_artifact.py --mode aggregate_qi --qi-results qi_results.json`:

```python
# 输入: qi_results = [{qi: 'Q1', min: 8, mean: 8.5}, {qi: 'Q2', min: 7, mean: 7.2}, {qi: 'Q3', min: 8, mean: 8.8}]
#      qi_weights = [1.0, 1.0, 1.0]   # 默认均匀, decision_log.stages.5.qi_weights 可定制
# 聚合规则:
weighted_mean = Σ(qi.mean × weight) / Σ(weight)   # 8.17
weighted_min  = min(qi.min for qi in qi_results)  # 7
# Qi 状态判定:
for qi in qi_results:
    if qi.min >= 7 and qi.mean >= 8: qi.status = "pass"
    elif qi.min >= 7:                qi.status = "mark_for_review"   # 该 Qi 需复核
    else:                            qi.status = "refine"            # 该 Qi 需重做
# verdict 决策:
if any(refine):       verdict = "refine_partial"   # 只 refine 标记 Qi, 不动其他
elif any(review):     verdict = "pass_with_review" if weighted 满足阈值 else "refine"
else:                 verdict = "pass"             # 全 Qi pass, 进 stage 6
```

**差异化降级**: per-Qi mark_for_review 不阻塞其他 Qi (即"Q2 单独 refine 不动 Q1/Q3"), 显著优于老的"全 stage 平均掩盖单 Qi 弱点"。

#### Stage 6
```json
"scores": {
  "1_multivariate_perturbation": {...},
  "2_perturbation_realism": {...},
  "3_output_completeness": {...},
  "4_robust_interval_quantitative": {...},
  "5_failure_warning": {...}
}
```
关键: F1-F4

#### Stage 7
```json
"scores": {
  "1_strengths_specific": {...},
  "2_weaknesses_real": {...},
  "3_improvements_actionable": {...},
  "4_generalization_concrete": {...},
  "5_self_critique_credibility": {...}
}
```
关键: H1-H3

#### Stage 8
```json
"scores": {
  "1_abstract_5_paragraph": {...},
  "2_section_completeness": {...},
  "3_formulas_figures_citations": {...},
  "4_language_quality": {...},
  "5_visual_consistency": {...}
}
```
关键: A1-A5, I1-I5

#### Stage 9
```json
"scores": {
  "1_anti_pattern_coverage": {...},
  "2_visual_polish": {...},
  "3_panel_consensus": {...},
  "4_bottleneck_addressed": {...},
  "5_pdf_compile_clean": {...}
}
```
关键: 全部

---

## 实现要点

- **JSON 必须可解析**: 用 Python `json.loads` 验证
- **issues 长度 ≤ 5**: 太多说明需要回 stage 重做, 不是精修
- **iteration cap = 3**: 第 4 次直接 carryover
- **early exit at iter-1 ≥ 9**: 多数阶段会触发, 节省 token
- **block 必须人工介入**: Skill 暂停, 输出 issues 等用户确认

---

## 与其他层的接口

- **L1 通过** → 写 decision_log + 进下一阶段
- **L1 carryover** → 写 decision_log + 标记 issue, 在 stage 5/6/8 末尾由 L2 优先回检
- **L1 block** → 暂停 Skill, 用户决定: revise 还是放弃该阶段

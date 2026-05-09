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
You are a strict CUMCM grader for stage {stage_id} ({stage_name}).
Score the artifact below against the 5-dim rubric.

Rubric (from `references/rubrics.md`):
{rubric_5_dims}

Reference patterns (from `references/winning_patterns.md`):
{relevant_patterns}

Anti-patterns to check (from `references/anti_patterns.md`):
{relevant_anti_patterns}

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
  "verdict": "pass_early" | "pass" | "refine" | "block"
}
```

**dim key 命名**: 形如 `1_role_clarity`、`2_tools_ready` ……, 数字前缀固定 1-5, 后接 §6 对应 stage 给的英文 snake_case 名。`scripts/score_artifact.py:DIM_WHITELIST` 严格按此校验, 写错即报 "dim key 不匹配"。

### 3. Verdict 规则

**优先级从高到低 (顺序不可变, 否则 pass_early 永远不触发)**:

```python
def verdict(scores, issues):
    min_s = min(scores.values())
    mean_s = mean(scores.values())
    high_issues = [i for i in issues if i["severity"] == "high"]
    
    if len(high_issues) >= 1:
        return "block"          # 含高严重 issue, 暂停 skill
    if min_s >= 9 and mean_s >= 9:
        return "pass_early"     # iter-1 早退, 节省 token
    if min_s >= 7 and mean_s >= 8:
        return "pass"           # 进下一阶段
    return "refine"             # section-patch 精修, iter+=1
```

**carryover 规则** (在 iter == max_iter 即 3 次后由调度器决定, critic 不直接输出此 verdict):
```
if iter == 3 and verdict == "refine": → 标记 carryover, 进下一阶段, L2 处理
```

此定义与 `SKILL.md` "收敛准则" / `rubrics.md` 阈值汇总 / `scripts/score_artifact.py compute_verdict` **必须完全一致**。

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

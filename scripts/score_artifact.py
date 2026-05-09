"""
score_artifact.py — L1 Critic 输出后的本地处理脚本 (v3.0 三竞赛版)

功能:
1. 读取 critique JSON
2. 验证 schema (5 维 + verdict + dim key 白名单, 含竞赛 overlay)
3. 决定下一步: block / pass_early / pass / pass_with_review / refine / refine_partial / carryover
4. 写入 cwd/state/decision_log.scores
5. 注入实测分位 (empirical injection) 到 evidence
6. 题型 dim 权重 (task_type weighting)
7. Stage 5 per-Qi 加权聚合 (compute_stage5_verdict)

路径协议:
- decision_log: 默认 cwd/state/decision_log.json, 可用 MATHMODEL_STATE_DIR (兼容老 CUMCM_STATE_DIR) 或 --decision-log 覆盖
- competition: 默认从 decision_log.competition 读, 缺失则 cumcm; 可用 --competition 或 MATHMODEL_COMPETITION env 覆盖
- task_type: 默认从 decision_log.task_type 读, null 则 default 全 1.0; 可用 --task-type 覆盖

用法:
    python scripts/score_artifact.py --stage 1 --critique state/critique_v0.json
    python scripts/score_artifact.py --competition mcm --task-type A_continuous --stage 3 --critique c.json
    # stage 5 per-Qi 评分:
    python scripts/score_artifact.py --stage 5 --variant per_qi --qi-id Q1 --critique critique_q1_v0.json
    # stage 5 多 Qi 聚合:
    python scripts/score_artifact.py --stage 5 --mode aggregate_qi --qi-results qi_results.json
"""

import json
import os
import argparse
from pathlib import Path
from datetime import datetime


VALID_VERDICTS = {
    "block", "pass_early", "pass", "pass_with_review",
    "refine", "refine_partial", "carryover"
}

VALID_VARIANTS = {"stage_level", "per_qi"}

# Baseline DIM_WHITELIST (cumcm-flavored; 其他竞赛通过 rubric_overlay.json dim_whitelist 覆盖)
DIM_WHITELIST = {
    0: {"1_role_clarity", "2_tools_ready", "3_time_planning", "4_problem_scan", "5_collab_protocol"},
    1: {"1_three_options_depth", "2_team_strength_match", "3_risk_identification",
        "4_time_feasibility", "5_decision_record_quality"},
    2: {"1_subproblem_decomposition", "2_key_variables_count", "3_math_skeleton_present",
        "4_data_alignment", "5_subproblem_dependency_identified"},
    3: {"1_candidate_diversity", "2_selection_rationale", "3_naming_variant",
        "4_solver_feasibility", "5_literature_support"},
    4: {"1_assumption_count", "2_assumption_support", "3_symbol_uniqueness",
        "4_consistency_with_model", "5_terminology_standard"},
    5: {"1_subproblem_completeness", "2_cross_reference_chain", "3_symbol_consistency",
        "4_visual_density", "5_time_budget"},
    "5_per_qi": {"1_problem_fit", "2_math_rigor", "3_solve_correctness",
                 "4_visualization", "5_physical_meaning"},
    6: {"1_multivariate_perturbation", "2_perturbation_realism", "3_output_completeness",
        "4_robust_interval_quantitative", "5_failure_warning"},
    7: {"1_strengths_specific", "2_weaknesses_real", "3_improvements_actionable",
        "4_generalization_concrete", "5_self_critique_credibility"},
    8: {"1_abstract_5_paragraph", "2_section_completeness", "3_formulas_figures_citations",
        "4_language_quality", "5_visual_consistency"},
    9: {"1_anti_pattern_coverage", "2_visual_polish", "3_panel_consensus",
        "4_bottleneck_addressed", "5_pdf_compile_clean"},
}

WEIGHT_CLAMP_MIN = 0.7
WEIGHT_CLAMP_MAX = 1.5

# 路径解析使用 skill 根目录, 因为 competitions/ 与 config/ 都在 skill 内
_SKILL_ROOT = Path(__file__).resolve().parent.parent


# ============================================================================
# 路径与配置加载
# ============================================================================

def resolve_decision_log_path(cli_arg: str = None) -> Path:
    """路径解析协议: CLI > MATHMODEL_STATE_DIR > CUMCM_STATE_DIR (兼容) > cwd/state/decision_log.json"""
    if cli_arg:
        return Path(cli_arg)
    env_dir = os.environ.get("MATHMODEL_STATE_DIR") or os.environ.get("CUMCM_STATE_DIR")
    if env_dir:
        return Path(env_dir) / "decision_log.json"
    return Path.cwd() / "state" / "decision_log.json"


def resolve_competition(cli_arg: str = None, decision_log: dict = None) -> str:
    """优先级: CLI > env MATHMODEL_COMPETITION > decision_log.competition > 'cumcm'"""
    if cli_arg:
        return cli_arg
    env = os.environ.get("MATHMODEL_COMPETITION")
    if env:
        return env
    if decision_log and decision_log.get("competition"):
        return decision_log["competition"]
    return "cumcm"


def resolve_task_type(cli_arg: str = None, decision_log: dict = None) -> str:
    """优先级: CLI > decision_log.task_type > 'default'"""
    if cli_arg:
        return cli_arg
    if decision_log and decision_log.get("task_type"):
        return decision_log["task_type"]
    return "default"


def load_rubric_overlay(competition: str) -> dict:
    """加载 competitions/<comp>/rubric_overlay.json. 缺失返回空 dict."""
    path = _SKILL_ROOT / "competitions" / competition / "rubric_overlay.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_empirical(competition: str) -> dict:
    """加载 competitions/<comp>/empirical.json. 缺失返回空 dict."""
    path = _SKILL_ROOT / "competitions" / competition / "empirical.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_dim_weights_table(competition: str, task_type: str) -> dict:
    """
    加载 config/dim_weights.json 中 (competition, task_type) 的 stage→dim→weight 表.
    fallback 链: task_type → competition.default → 全 1.0.
    返回 {stage_str: {dim_name: weight}} (stage_str = "3" / "5" / "8" 等).
    """
    path = _SKILL_ROOT / "config" / "dim_weights.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        table = json.load(f)
    comp_table = table.get(competition, {})
    if not comp_table:
        return {}
    # 优先 task_type, 缺失则 default
    weights = comp_table.get(task_type)
    if weights is None or weights == {} or list(weights.keys()) == ["_note"]:
        weights = comp_table.get("default", {})
    # 过滤掉以 _ 开头的元字段
    return {k: v for k, v in weights.items() if not k.startswith("_")}


def load_dim_whitelist(competition: str, stage_id, variant: str = "stage_level") -> set:
    """
    加载竞赛特化 dim_whitelist; 缺失则 fallback 到 baseline DIM_WHITELIST.
    stage_id 可以是 int 或 str (如 "5_per_qi").
    """
    wl_key = "5_per_qi" if (stage_id == 5 and variant == "per_qi") else stage_id
    overlay = load_rubric_overlay(competition)
    overlay_wl = overlay.get("dim_whitelist", {})
    # JSON 中 key 是 str
    overlay_dims = overlay_wl.get(str(wl_key))
    if overlay_dims:
        return set(overlay_dims)
    return DIM_WHITELIST.get(wl_key, set())


def load_competition_config(competition: str, task_type: str = "default") -> dict:
    """聚合加载: overlay + empirical + dim weights table"""
    return {
        "competition": competition,
        "task_type": task_type,
        "overlay": load_rubric_overlay(competition),
        "empirical": load_empirical(competition),
        "weights": load_dim_weights_table(competition, task_type),
    }


# ============================================================================
# 评分核心: 实测注入 / 题型加权 / per-Qi 聚合
# ============================================================================

def inject_evidence(dim_key: str, value: float, empirical: dict, by_topic: str = None) -> str:
    """
    把 empirical p25/p50/p75 注入 evidence 字符串.
    dim_key: empirical.json dims 字段的 key (如 abstract_chars / formula_count)
    value: 当前实测值
    by_topic: 若提供 (e.g. "A"), 优先用 empirical.by_topic[A][dim_key]

    Returns:
        "value=720, p50=992, IQR=[748, 1146], status=低于 p25 [seed: ...]" 形式
    """
    if not empirical:
        return f"value={value} [empirical 数据缺失]"

    # 优先 by_topic, 缺失则 dims (整体)
    dim_data = None
    if by_topic and "by_topic" in empirical:
        dim_data = empirical.get("by_topic", {}).get(by_topic, {}).get(dim_key)
    if dim_data is None:
        dim_data = empirical.get("dims", {}).get(dim_key)

    if dim_data is None:
        return f"value={value} [{dim_key} 不在 empirical 字段]"

    p25, p50, p75 = dim_data.get("p25"), dim_data.get("p50"), dim_data.get("p75")
    if p25 is None or p75 is None:
        return f"value={value} [empirical 分位缺失]"

    if value > p75:
        status = "高于 p75"
    elif value < p25:
        status = "低于 p25"
    else:
        status = "IQR 内"

    seed_tag = ""
    if empirical.get("source", {}).get("status", "").startswith("seed"):
        seed_tag = " [seed: 阈值未实测分位]"

    return (f"value={value}, p50={p50}, IQR=[{p25}, {p75}]"
            f"{' (by topic ' + by_topic + ')' if by_topic else ''}, status={status}{seed_tag}")


def apply_dim_weights(scores: dict, weights_for_stage: dict) -> dict:
    """
    weighted_score[dim] = clamp(weight, [WEIGHT_CLAMP_MIN, WEIGHT_CLAMP_MAX]).
    返回 {dim: weight} (1.0 if not in table); 给 compute_verdict 用.

    分离 weight 与 score 是为了:
    - 加权 mean = sum(score * weight) / sum(weight)
    - 加权 min = min(score) (不加权, 仍用作 'any dim too low' 触发)
    """
    out = {}
    for dim_name in scores:
        w = weights_for_stage.get(dim_name, 1.0)
        w_clamped = max(WEIGHT_CLAMP_MIN, min(WEIGHT_CLAMP_MAX, w))
        out[dim_name] = w_clamped
    return out


def compute_verdict(critique: dict, weights_for_stage: dict = None) -> str:
    """
    根据分数与 issues 重算 verdict (覆盖 critic 的 verdict 字段, 防 gaming).
    优先级 (高→低): block > pass_early > pass > refine
    支持题型 dim 权重 (weights_for_stage; None = 全 1.0).

    与 SKILL.md / feedback_layer1_critic.md 三处一致.
    """
    score_values = {k: d["score"] for k, d in critique["scores"].items()}
    raw_min = min(score_values.values())
    raw_mean = sum(score_values.values()) / len(score_values)

    if weights_for_stage:
        w_table = apply_dim_weights(score_values, weights_for_stage)
        weighted_sum = sum(score_values[d] * w_table[d] for d in score_values)
        weight_total = sum(w_table.values())
        weighted_mean = weighted_sum / weight_total if weight_total else raw_mean
    else:
        weighted_mean = raw_mean

    high_issues = [i for i in critique["issues"] if i.get("severity") == "high"]

    if len(high_issues) >= 1:
        return "block"
    if raw_min >= 9 and weighted_mean >= 9:
        return "pass_early"
    if raw_min >= 7 and weighted_mean >= 8:
        return "pass"
    return "refine"


def compute_stage5_verdict(qi_results: list, qi_weights: list = None) -> dict:
    """
    Stage 5 per-Qi 加权聚合.
    qi_results: [{qi: 'Q1', min: int, mean: float, scores: {...}}]
    qi_weights: [1.0, 1.0, 1.0]; None → 均匀

    Returns:
        {
          "verdict": "pass" | "pass_with_review" | "refine_partial" | "refine",
          "weighted_min": int,  # min over Qi.min
          "weighted_mean": float,
          "qi_status": {"Q1": "pass"|"mark_for_review"|"refine", ...},
          "review_qis": [...],  # mark_for_review 的 Qi
          "refine_qis": [...]   # 需要重做的 Qi (min < 7 且整体不 pass)
        }
    """
    if not qi_results:
        return {"verdict": "refine", "qi_status": {}, "review_qis": [], "refine_qis": []}

    n = len(qi_results)
    if qi_weights is None or len(qi_weights) != n:
        qi_weights = [1.0] * n

    qi_status = {}
    for qi in qi_results:
        if qi["min"] >= 7 and qi["mean"] >= 8:
            qi_status[qi["qi"]] = "pass"
        elif qi["min"] >= 7:
            qi_status[qi["qi"]] = "mark_for_review"
        else:
            qi_status[qi["qi"]] = "refine"

    weight_total = sum(qi_weights)
    weighted_mean = sum(q["mean"] * w for q, w in zip(qi_results, qi_weights)) / weight_total
    weighted_min = min(q["min"] for q in qi_results)

    review_qis = [q for q, s in qi_status.items() if s == "mark_for_review"]
    refine_qis = [q for q, s in qi_status.items() if s == "refine"]

    if refine_qis:
        # 部分 Qi 需 refine; 不阻塞其他 Qi
        if weighted_min >= 7 and weighted_mean >= 8:
            # 不太可能但理论存在: refine Qi 拖低但加权后仍 pass → refine_partial
            verdict = "refine_partial"
        else:
            verdict = "refine_partial"
    elif review_qis:
        if weighted_min >= 7 and weighted_mean >= 8:
            verdict = "pass_with_review"
        else:
            verdict = "refine"
    else:
        # 全 Qi pass
        if weighted_min >= 9 and weighted_mean >= 9:
            verdict = "pass_early"
        elif weighted_min >= 7 and weighted_mean >= 8:
            verdict = "pass"
        else:
            verdict = "refine"

    return {
        "verdict": verdict,
        "weighted_min": weighted_min,
        "weighted_mean": round(weighted_mean, 2),
        "qi_status": qi_status,
        "review_qis": review_qis,
        "refine_qis": refine_qis,
    }


# ============================================================================
# Schema 校验
# ============================================================================

def resolve_whitelist_key(stage_id: int, variant: str):
    if stage_id == 5 and variant == "per_qi":
        return "5_per_qi"
    return stage_id


def validate_critique(critique: dict, stage_id: int, competition: str = "cumcm",
                      variant: str = "stage_level") -> tuple[bool, str]:
    """
    验证 critique JSON 是否符合 L1 schema, 含竞赛 overlay-aware 的 dim key 白名单
    """
    required_keys = {"stage_id", "iteration", "scores", "min_score",
                     "mean_score", "issues", "verdict"}
    missing = required_keys - critique.keys()
    if missing:
        return False, f"缺少 keys: {missing}"

    if critique["verdict"] not in VALID_VERDICTS:
        return False, f"verdict 必须 ∈ {VALID_VERDICTS}, 实际: {critique['verdict']}"

    if variant not in VALID_VARIANTS:
        return False, f"variant 必须 ∈ {VALID_VARIANTS}, 实际: {variant}"

    if variant == "per_qi" and stage_id != 5:
        return False, f"variant=per_qi 仅适用于 stage 5, 实际 stage {stage_id}"

    if not isinstance(critique["scores"], dict) or len(critique["scores"]) != 5:
        return False, "scores 必须是 5 维 dict"

    expected_dims = load_dim_whitelist(competition, stage_id, variant)
    if not expected_dims:
        return False, f"未知 stage_id: {stage_id} (competition={competition}, variant={variant})"
    actual_dims = set(critique["scores"].keys())
    if actual_dims != expected_dims:
        unexpected = actual_dims - expected_dims
        missing_dims = expected_dims - actual_dims
        msg = f"dim key 不匹配 (competition {competition}, stage {stage_id}, variant {variant}). "
        if unexpected:
            msg += f"未预期 keys: {unexpected}. "
        if missing_dims:
            msg += f"缺失 keys: {missing_dims}."
        return False, msg

    for dim_name, dim in critique["scores"].items():
        if not isinstance(dim, dict) or "score" not in dim:
            return False, f"scores.{dim_name} 缺 score 字段"
        if not (1 <= dim["score"] <= 10):
            return False, f"scores.{dim_name}.score 超出 [1,10]"

    if not isinstance(critique["issues"], list):
        return False, "issues 必须是 list"
    if len(critique["issues"]) > 5:
        return False, f"issues 长度 {len(critique['issues'])} > 5, 应回 stage 重做而非精修"

    return True, "ok"


# ============================================================================
# decision_log 写入
# ============================================================================

def update_decision_log(stage_id: int, critique: dict, decision_log_path: Path,
                        variant: str = "stage_level", qi_id: str = None,
                        weighted_mean: float = None, extra: dict = None):
    """
    把 critique 写入 decision_log.scores[stage_key]
    - stage_level: stage_key = str(stage_id)
    - per_qi:      stage_key = "5_per_qi", entry 含 qi_id 字段
    - extra:       附加字段 (e.g., review_qis, refine_qis from compute_stage5_verdict)
    """
    if not decision_log_path.exists():
        raise FileNotFoundError(
            f"{decision_log_path} 不存在。"
            f"请先 stage 0 初始化 (cp <skill>/templates/shared/decision_log.json {decision_log_path})"
        )

    with open(decision_log_path, "r", encoding="utf-8") as f:
        log = json.load(f)

    stage_key = "5_per_qi" if variant == "per_qi" else str(stage_id)

    if stage_key not in log["scores"] or not isinstance(log["scores"][stage_key], list):
        log["scores"][stage_key] = []

    entry = {
        "iteration": critique["iteration"],
        "scores": {k: v["score"] for k, v in critique["scores"].items()},
        "min": critique["min_score"],
        "mean": critique["mean_score"],
        "verdict": critique["verdict"],
        "ts": datetime.now().isoformat(),
    }
    if variant == "per_qi":
        entry["qi_id"] = qi_id
    if weighted_mean is not None:
        entry["weighted_mean"] = round(weighted_mean, 2)
    if extra:
        for k, v in extra.items():
            if k not in entry:
                entry[k] = v
    log["scores"][stage_key].append(entry)

    if "iterations" not in log:
        log["iterations"] = {}
    log["iterations"][stage_key] = critique["iteration"] + 1

    with open(decision_log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def read_decision_log(decision_log_path: Path) -> dict:
    """读 decision_log; 不存在返回空 dict 不抛错 (用于 resolve_competition)"""
    if not decision_log_path.exists():
        return {}
    with open(decision_log_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================================
# 决策
# ============================================================================

def decide_next_action(critique: dict, max_iter: int = 3,
                       weights_for_stage: dict = None) -> dict:
    """返回下一步行为"""
    actual_verdict = compute_verdict(critique, weights_for_stage)
    if actual_verdict != critique.get("verdict"):
        critique["verdict"] = actual_verdict

    iter_num = critique["iteration"]

    if actual_verdict == "block":
        return {"action": "halt", "verdict": "block",
                "reason": "critique.issues 含 high-severity, 需用户介入",
                "issues": [i for i in critique["issues"] if i.get("severity") == "high"]}
    if actual_verdict in ("pass", "pass_early", "pass_with_review"):
        return {"action": "next_stage", "verdict": actual_verdict}
    if iter_num >= max_iter:
        return {"action": "carryover", "verdict": "carryover",
                "reason": f"已迭代 {iter_num}+1 次仍未达标, 标记 carryover, L2 回检处理"}
    return {"action": "section_patch", "verdict": "refine",
            "issues": critique["issues"],
            "next_iteration": iter_num + 1}


# ============================================================================
# CLI
# ============================================================================

def cmd_aggregate_qi(args):
    """子命令: stage 5 多 Qi 聚合"""
    qi_results_path = Path(args.qi_results)
    if not qi_results_path.exists():
        print(f"[FAIL] {qi_results_path} 不存在")
        return 1

    with open(qi_results_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    qi_results = data.get("qi_results", [])
    qi_weights = data.get("qi_weights")

    result = compute_stage5_verdict(qi_results, qi_weights)
    print(f"Stage 5 per-Qi 聚合 (n={len(qi_results)})")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, help="阶段编号 0-9 (mode=normal/aggregate_qi 必填)")
    parser.add_argument("--critique", type=str, help="critique JSON 文件路径 (mode=normal 必填)")
    parser.add_argument("--variant", choices=sorted(VALID_VARIANTS), default=None,
                        help="stage 5 区分 per-Qi vs stage-level; 默认读 critique.variant 或 stage_level")
    parser.add_argument("--qi-id", type=str, default=None,
                        help="per_qi variant 必填, e.g. Q1/Q2")
    parser.add_argument("--max-iter", type=int, default=3)
    parser.add_argument("--decision-log", type=str, default=None,
                        help="覆盖路径解析协议; 默认 cwd/state/decision_log.json")
    parser.add_argument("--competition", type=str, default=None,
                        help="cumcm | mcm | diangong (默认从 decision_log 读, 缺失则 cumcm)")
    parser.add_argument("--task-type", type=str, default=None,
                        help="题型 e.g. A_optimization (默认 default 全 1.0)")
    parser.add_argument("--mode", choices=["normal", "aggregate_qi"], default="normal",
                        help="aggregate_qi: stage 5 多 Qi 加权聚合 (需 --qi-results)")
    parser.add_argument("--qi-results", type=str,
                        help="aggregate_qi 模式: {qi_results: [...], qi_weights: [...]} JSON 文件")
    args = parser.parse_args()

    if args.mode == "aggregate_qi":
        if not args.qi_results:
            print("[FAIL] mode=aggregate_qi 需 --qi-results")
            return 1
        return cmd_aggregate_qi(args)

    # mode=normal: 单 critique 评分
    if args.stage is None or args.critique is None:
        print("[FAIL] mode=normal 需 --stage 与 --critique")
        return 1

    decision_log_path = resolve_decision_log_path(args.decision_log)
    decision_log = read_decision_log(decision_log_path)

    competition = resolve_competition(args.competition, decision_log)
    task_type = resolve_task_type(args.task_type, decision_log)

    with open(args.critique, "r", encoding="utf-8") as f:
        critique = json.load(f)

    variant = args.variant or critique.get("variant", "stage_level")
    qi_id = args.qi_id or critique.get("qi_id")

    if variant == "per_qi" and not qi_id:
        print("[FAIL] variant=per_qi 必须提供 --qi-id 或 critique.qi_id (e.g. Q1)")
        return 1

    ok, msg = validate_critique(critique, args.stage, competition, variant)
    if not ok:
        print(f"[FAIL] Schema error: {msg}")
        return 1

    # 加载 dim weights 给该 stage
    weights_table = load_dim_weights_table(competition, task_type)
    weights_for_stage = weights_table.get(str(args.stage), {})
    # 过滤 _note 等元字段
    weights_for_stage = {k: v for k, v in weights_for_stage.items() if not k.startswith("_")}

    # 注入实测分位 (若 critique 有 evidence_metrics 字段)
    empirical = load_empirical(competition)
    if "evidence_metrics" in critique and empirical:
        topic = (decision_log.get("problem_meta", {}) or {}).get("letter")
        for metric_dim, value in critique["evidence_metrics"].items():
            evidence_str = inject_evidence(metric_dim, value, empirical, by_topic=topic)
            print(f"  [empirical] {metric_dim}: {evidence_str}")

    actual_verdict = compute_verdict(critique, weights_for_stage)
    label = f"stage {args.stage}" + (f" / {qi_id}" if variant == "per_qi" else "")
    print(f"{label}, iter {critique['iteration']}, variant {variant}, "
          f"competition {competition}, task_type {task_type}")
    print(f"  Min score: {critique['min_score']}, Mean: {critique['mean_score']:.2f}")
    if weights_for_stage:
        weighted_score = sum(critique["scores"][d]["score"] * weights_for_stage.get(d, 1.0)
                             for d in critique["scores"])
        weight_total = sum(weights_for_stage.get(d, 1.0) for d in critique["scores"])
        weighted_mean = weighted_score / weight_total if weight_total else critique["mean_score"]
        print(f"  Weighted mean (task_type={task_type}): {weighted_mean:.2f}")
    else:
        weighted_mean = None
    print(f"  Critic verdict: {critique['verdict']} -> Actual: {actual_verdict}")
    print(f"  decision_log: {decision_log_path}")

    update_decision_log(args.stage, critique, decision_log_path,
                        variant, qi_id, weighted_mean=weighted_mean)
    print(f"  [OK] written")

    action = decide_next_action(critique, args.max_iter, weights_for_stage)
    print(f"\n下一步: {action['action']}")
    print(json.dumps(action, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

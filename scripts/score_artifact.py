"""
score_artifact.py — L1 Critic 输出后的本地处理脚本

功能:
1. 读取 critique JSON
2. 验证 schema (5 维 + verdict + dim key 白名单)
3. 决定下一步: block / pass_early / pass / refine / carryover
4. 写入 cwd/state/decision_log.scores

路径协议: 默认从 cwd/state/decision_log.json 读写, 可用 CUMCM_STATE_DIR env var 或 --decision-log 覆盖。

用法:
    python scripts/score_artifact.py --stage 1 --critique state/critique_v0.json
    CUMCM_STATE_DIR=/tmp/state python scripts/score_artifact.py --stage 1 --critique critique.json
"""

import json
import os
import argparse
from pathlib import Path
from datetime import datetime


VALID_VERDICTS = {"block", "pass_early", "pass", "refine", "carryover"}

# 各 stage 的 5 维 dim key 白名单 (与 feedback_layer1_critic.md §6 对齐, 英文 snake_case)
DIM_WHITELIST = {
    0: {"role_clarity", "tools_ready", "time_planning", "problem_scan", "collab_protocol"},
    1: {"three_options_depth", "team_strength_match", "risk_identification",
        "time_feasibility", "decision_record_quality"},
    2: {"subproblem_decomposition", "key_variables_count", "math_skeleton_present",
        "data_alignment", "subproblem_dependency_identified"},
    3: {"candidate_diversity", "selection_rationale", "naming_variant",
        "solver_feasibility", "literature_support"},
    4: {"assumption_count", "assumption_support", "symbol_uniqueness",
        "consistency_with_model", "terminology_standard"},
    # stage 5 有 per-Qi 与 stage-level 两套, 用 stage-level 作主校验
    5: {"subproblem_completeness", "cross_reference_chain", "symbol_consistency",
        "visual_density", "time_budget"},
    "5_per_qi": {"problem_fit", "math_rigor", "solve_correctness",
                  "visualization", "physical_meaning"},
    6: {"multivariate_perturbation", "perturbation_realism", "output_completeness",
        "robust_interval_quantitative", "failure_warning"},
    7: {"strengths_specific", "weaknesses_real", "improvements_actionable",
        "generalization_concrete", "self_critique_credibility"},
    8: {"abstract_5_paragraph", "section_completeness", "formulas_figures_citations",
        "language_quality", "visual_consistency"},
    9: {"anti_pattern_coverage", "visual_polish", "panel_consensus",
        "bottleneck_addressed", "pdf_compile_clean"},
}


def resolve_decision_log_path(cli_arg: str = None) -> Path:
    """路径解析协议: CLI > env var > cwd/state/decision_log.json"""
    if cli_arg:
        return Path(cli_arg)
    env_dir = os.environ.get("CUMCM_STATE_DIR")
    if env_dir:
        return Path(env_dir) / "decision_log.json"
    return Path.cwd() / "state" / "decision_log.json"


def validate_critique(critique: dict, stage_id: int) -> tuple[bool, str]:
    """
    验证 critique JSON 是否符合 L1 schema, 含 dim key 白名单
    """
    required_keys = {"stage_id", "iteration", "scores", "min_score",
                     "mean_score", "issues", "verdict"}
    missing = required_keys - critique.keys()
    if missing:
        return False, f"缺少 keys: {missing}"

    if critique["verdict"] not in VALID_VERDICTS:
        return False, f"verdict 必须 ∈ {VALID_VERDICTS}, 实际: {critique['verdict']}"

    if not isinstance(critique["scores"], dict) or len(critique["scores"]) != 5:
        return False, "scores 必须是 5 维 dict"

    # P1-8: dim key 白名单校验
    expected_dims = DIM_WHITELIST.get(stage_id)
    if expected_dims is None:
        return False, f"未知 stage_id: {stage_id}"
    actual_dims = set(critique["scores"].keys())
    if actual_dims != expected_dims:
        unexpected = actual_dims - expected_dims
        missing_dims = expected_dims - actual_dims
        msg = f"dim key 不匹配 (stage {stage_id}). "
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


def compute_verdict(critique: dict) -> str:
    """
    根据分数与 issues 重算 verdict (覆盖 critic 的 verdict 字段, 防 gaming)。
    优先级 (高→低): block > pass_early > pass > refine
    与 SKILL.md / feedback_layer1_critic.md 三处一致。
    """
    scores = [d["score"] for d in critique["scores"].values()]
    min_s = min(scores)
    mean_s = sum(scores) / len(scores)
    high_issues = [i for i in critique["issues"] if i.get("severity") == "high"]

    if len(high_issues) >= 1:
        return "block"
    if min_s >= 9 and mean_s >= 9:
        return "pass_early"
    if min_s >= 7 and mean_s >= 8:
        return "pass"
    return "refine"


def update_decision_log(stage_id: int, critique: dict, decision_log_path: Path):
    """
    把 critique 写入 decision_log.scores[stage_id]
    """
    if not decision_log_path.exists():
        raise FileNotFoundError(
            f"{decision_log_path} 不存在。"
            f"请先 stage 0 初始化 (cp <skill>/templates/decision_log.json {decision_log_path})"
        )

    with open(decision_log_path, "r", encoding="utf-8") as f:
        log = json.load(f)

    stage_key = str(stage_id)
    if stage_key not in log["scores"]:
        log["scores"][stage_key] = []

    log["scores"][stage_key].append({
        "iteration": critique["iteration"],
        "scores": {k: v["score"] for k, v in critique["scores"].items()},
        "min": critique["min_score"],
        "mean": critique["mean_score"],
        "verdict": critique["verdict"],
        "ts": datetime.now().isoformat(),
    })

    log["iterations"][stage_key] = critique["iteration"] + 1

    with open(decision_log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def decide_next_action(critique: dict, max_iter: int = 3) -> dict:
    """
    返回下一步行为
    """
    actual_verdict = compute_verdict(critique)
    if actual_verdict != critique.get("verdict"):
        critique["verdict"] = actual_verdict

    iter_num = critique["iteration"]

    if actual_verdict == "block":
        return {"action": "halt", "verdict": "block",
                "reason": "critique.issues 含 high-severity, 需用户介入",
                "issues": [i for i in critique["issues"] if i.get("severity") == "high"]}
    if actual_verdict in ("pass", "pass_early"):
        return {"action": "next_stage", "verdict": actual_verdict}
    if iter_num >= max_iter:
        return {"action": "carryover", "verdict": "carryover",
                "reason": f"已迭代 {iter_num}+1 次仍未达标, 标记 carryover, L2 回检处理"}
    return {"action": "section_patch", "verdict": "refine",
            "issues": critique["issues"],
            "next_iteration": iter_num + 1}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, required=True, help="阶段编号 0-9")
    parser.add_argument("--critique", type=str, required=True, help="critique JSON 文件路径")
    parser.add_argument("--max-iter", type=int, default=3)
    parser.add_argument("--decision-log", type=str, default=None,
                        help="覆盖路径解析协议; 默认 cwd/state/decision_log.json 或 $CUMCM_STATE_DIR")
    args = parser.parse_args()

    decision_log_path = resolve_decision_log_path(args.decision_log)

    with open(args.critique, "r", encoding="utf-8") as f:
        critique = json.load(f)

    ok, msg = validate_critique(critique, args.stage)
    if not ok:
        print(f"[FAIL] Schema error: {msg}")
        return 1

    actual_verdict = compute_verdict(critique)
    print(f"Stage {args.stage}, iter {critique['iteration']}")
    print(f"  Min score: {critique['min_score']}, Mean: {critique['mean_score']:.2f}")
    print(f"  Critic verdict: {critique['verdict']} -> Actual: {actual_verdict}")
    print(f"  decision_log: {decision_log_path}")

    update_decision_log(args.stage, critique, decision_log_path)
    print(f"  [OK] written")

    action = decide_next_action(critique, args.max_iter)
    print(f"\n下一步: {action['action']}")
    print(json.dumps(action, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

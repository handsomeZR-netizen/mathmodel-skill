#!/usr/bin/env python3
"""Read-only progress dashboard for a mathmodel-skill workspace ("看进度").

The dashboard summarizes ``state/decision_log.json`` without modifying it:
current stage, latest verdict per stage, Stage 5 per-Qi state, compliance
gates, deadline countdown, the deadline-based mode recommendation from
SKILL.md, and one concrete next action.

Usage:
    python scripts/status.py --workspace /path/to/project
    python scripts/status.py --workspace /path/to/project --markdown
    python scripts/status.py --decision-log /path/to/state/decision_log.json --json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
COMPETITION_LABELS = {"cumcm": "CUMCM 国赛", "mcm": "MCM/ICM 美赛", "diangong": "电工杯"}
VALID_MODES = ("fast", "standard", "championship")

# (stage, reference key, human label). The key matches both the frontmatter
# ``name`` and the ``references/stage_NN_<key>.md`` filename; tests enforce it.
STAGES = (
    (0, "kickoff", "团队启动与资料预扫"),
    (1, "problem_selection", "多题比较与选题"),
    (2, "analysis", "问题拆解"),
    (3, "model_selection", "模型选型"),
    (4, "foundation", "假设·符号·术语"),
    (5, "subproblem_loop", "递归求解 Q1…Qn"),
    (6, "robustness", "稳健性分析"),
    (7, "evaluation", "模型评价"),
    (8, "writing", "论文装配"),
    (9, "review", "提交前终审"),
)
PASSING_VERDICTS = {"pass", "pass_early", "pass_with_review"}
STAGE9_GATES = (
    ("rules_verified", "当届规则"),
    ("anonymity_passed", "匿名"),
    ("page_limit_passed", "页数"),
    ("ai_disclosure_passed", "AI 披露"),
    ("supporting_materials_passed", "支撑材料"),
)


# ---------------------------------------------------------------------------
# Paths and parsing
# ---------------------------------------------------------------------------

def resolve_decision_log(decision_log: str | None, workspace: str | None) -> Path:
    """CLI --decision-log > --workspace > MATHMODEL_STATE_DIR > CUMCM_STATE_DIR > <cwd>/state."""
    if decision_log:
        return Path(decision_log)
    if workspace:
        return Path(workspace) / "state" / "decision_log.json"
    env_dir = os.environ.get("MATHMODEL_STATE_DIR") or os.environ.get("CUMCM_STATE_DIR")
    if env_dir:
        return Path(env_dir) / "decision_log.json"
    return Path.cwd() / "state" / "decision_log.json"


def parse_datetime(value: object) -> datetime | None:
    """Parse an ISO timestamp; naive values are interpreted in local time."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.astimezone()


def recommend_mode(hours_left: float | None) -> dict:
    """Deadline-based recommendation, mirroring SKILL.md "模式自动推荐"."""
    if hours_left is None:
        return {"mode": None, "note": "未记录截止时间，无法按剩余时间推荐模式"}
    if hours_left <= 0:
        return {"mode": None, "note": "已超过记录的截止时间；请先核对 deadline 是否正确"}
    if hours_left < 6:
        return {"mode": "championship", "note": "< 6h：建议直接进入 Stage 9 终审"}
    if hours_left < 24:
        return {"mode": "fast", "note": "6–24h：关键阶段用 fast，终审升 championship"}
    if hours_left <= 60:
        return {"mode": "standard", "note": "24–60h：standard"}
    return {"mode": "standard", "note": "> 60h：standard，最后 6h 升 championship"}


def _stage_reference(stage: int, key: str) -> str:
    return f"references/stage_{stage:02d}_{key}.md"


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def _latest_entry(entries: object) -> dict | None:
    if not isinstance(entries, list):
        return None
    for entry in reversed(entries):
        if isinstance(entry, dict):
            return entry
    return None


# ---------------------------------------------------------------------------
# Status model
# ---------------------------------------------------------------------------

def build_status(log: dict, now: datetime | None = None) -> dict:
    """Condense a decision log into a JSON-serializable dashboard model."""
    if not isinstance(log, dict):
        raise ValueError("decision_log 根节点必须是 object")
    current = log.get("current_stage")
    if isinstance(current, bool) or not isinstance(current, int) or not 0 <= current <= 9:
        raise ValueError(f"current_stage 必须是 0–9 的整数，实际为 {current!r}")

    now = now or datetime.now(timezone.utc)
    stages_state = log.get("stages") if isinstance(log.get("stages"), dict) else {}
    scores = log.get("scores") if isinstance(log.get("scores"), dict) else {}
    stage9 = stages_state.get("9") if isinstance(stages_state.get("9"), dict) else {}
    submission_ready = stage9.get("submission_ready") is True

    stages = []
    for number, key, label in STAGES:
        entries = scores.get(str(number))
        latest = _latest_entry(entries)
        if number < current or (number == 9 and submission_ready):
            state = "done"
        elif number == current:
            state = "current"
        else:
            state = "pending"
        stages.append({
            "stage": number,
            "key": key,
            "label": label,
            "reference": _stage_reference(number, key),
            "state": state,
            "evaluations": len(entries) if isinstance(entries, list) else 0,
            "latest": None if latest is None else {
                "iteration": latest.get("iteration"),
                "verdict": latest.get("verdict"),
                "min": _number(latest.get("min")),
                "mean": _number(latest.get("mean")),
                "weighted_mean": _number(latest.get("weighted_mean")),
            },
        })
    completed = sum(item["state"] == "done" for item in stages)

    stage5 = stages_state.get("5") if isinstance(stages_state.get("5"), dict) else {}
    aggregate = stage5.get("aggregate") if isinstance(stage5.get("aggregate"), dict) else {}
    qi_status = stage5.get("qi_status") if isinstance(stage5.get("qi_status"), dict) else {}
    subproblems = {
        "qi_count": stage5.get("qi_count"),
        "qi_status": {str(k): v for k, v in qi_status.items() if not str(k).startswith("_")},
        "review_qis": list(stage5.get("review_qis") or []),
        "refine_qis": list(stage5.get("refine_qis") or []),
        "block_qis": list(stage5.get("block_qis") or []),
        "aggregate_verdict": aggregate.get("verdict"),
    }

    compliance = log.get("compliance") if isinstance(log.get("compliance"), dict) else {}
    ruleset = compliance.get("ruleset") if isinstance(compliance.get("ruleset"), dict) else {}
    ai_usage = compliance.get("ai_usage")
    checks = stage9.get("compliance_checks")
    checks = checks if isinstance(checks, dict) else {}
    gates = {
        "rules_baseline": {
            "label": "规则基线",
            "ok": bool(ruleset.get("verified_at")),
            "detail": f"核对于 {ruleset['verified_at']}" if ruleset.get("verified_at") else "未记录核对日期",
        },
        "ai_ledger": {
            "label": "AI 台账",
            "ok": isinstance(ai_usage, list),
            "detail": (
                "未核对（null 不等于未使用）" if not isinstance(ai_usage, list)
                else "已确认未使用 AI" if not ai_usage
                else f"{len(ai_usage)} 条使用记录"
            ),
        },
    }
    for key, label in STAGE9_GATES:
        passed = checks.get(key) is True
        gates[key] = {"label": label, "ok": passed, "detail": "已通过" if passed else "待检查"}

    meta = log.get("problem_meta") if isinstance(log.get("problem_meta"), dict) else {}
    deadline = parse_datetime(meta.get("deadline_iso"))
    hours_left = None
    if deadline is not None:
        hours_left = round((deadline - now).total_seconds() / 3600, 1)
    mode = log.get("mode")
    recommendation = recommend_mode(hours_left)

    competition = log.get("competition")
    status = {
        "competition": competition,
        "competition_label": COMPETITION_LABELS.get(competition, str(competition)),
        "problem": {
            "year": meta.get("year"),
            "letter": meta.get("letter"),
            "title": meta.get("title"),
            "team_size": meta.get("team_size"),
        },
        "task_type": log.get("task_type"),
        "mode": mode,
        "current_stage": current,
        "progress": {"completed": completed, "total": len(STAGES),
                     "percent": round(100 * completed / len(STAGES))},
        "deadline": {
            "iso": meta.get("deadline_iso"),
            "valid": deadline is not None,
            "hours_left": hours_left,
            "recommended_mode": recommendation["mode"],
            "note": recommendation["note"],
            "mode_mismatch": bool(recommendation["mode"] and mode and recommendation["mode"] != mode),
        },
        "stages": stages,
        "subproblems": subproblems,
        "compliance": gates,
        "submission_ready": submission_ready,
    }
    status["next_action"] = next_action(status)
    return status


def next_action(status: dict) -> str:
    """One deterministic, human-readable next step."""
    if status["submission_ready"]:
        return "已标记 submission_ready：按当届官方渠道提交，并保留最终 PDF 与支撑材料。"
    hours_left = status["deadline"]["hours_left"]
    if hours_left is not None and hours_left <= 0:
        return "已超过记录的截止时间：先与团队核对 deadline 与提交状态。"

    stage = status["stages"][status["current_stage"]]
    number, label, reference = stage["stage"], stage["label"], stage["reference"]
    latest = stage["latest"] or {}
    verdict = latest.get("verdict")
    iteration = latest.get("iteration")
    subproblems = status["subproblems"]

    if verdict is None:
        action = f"执行 Stage {number}「{label}」：加载 {reference}"
    elif verdict == "block":
        action = f"Stage {number} 被 high-severity 问题阻断：由团队处理 issues 后重新评分"
    elif verdict == "refine_partial":
        targets = "、".join(subproblems["refine_qis"]) or "未通过的 Qi"
        action = f"只精修 {targets}，其余 Qi 保持不动，然后重新聚合 Stage 5"
    elif verdict == "refine":
        shown = iteration + 1 if isinstance(iteration, int) else "?"
        action = f"Stage {number} 需要精修（第 {shown} 轮评审未过）：用 extract_diff.py 做 section patch"
    elif verdict == "carryover":
        action = f"Stage {number} 已达迭代上限：进入下一阶段，并由 L2 回检处理遗留问题"
    elif verdict in PASSING_VERDICTS and number < 9:
        nxt = status["stages"][number + 1]
        action = f"Stage {number} 已通过：推进 current_stage，进入 Stage {nxt['stage']}「{nxt['label']}」"
        if verdict == "pass_with_review" and subproblems["review_qis"]:
            action += f"；L2 必读 {'、'.join(subproblems['review_qis'])}"
    elif verdict in PASSING_VERDICTS:
        failing = [
            status["compliance"][key]["label"] for key, _ in STAGE9_GATES
            if not status["compliance"][key]["ok"]
        ]
        action = (
            f"终审评分已通过；仍需补齐合规门：{'、'.join(failing)}" if failing
            else "终审与合规门均已通过：由团队确认后写入 submission_ready"
        )
    else:
        action = f"Stage {number} 的最新 verdict {verdict!r} 无法识别：请重新运行 score_artifact.py"

    if status["deadline"]["mode_mismatch"]:
        action += (
            f"。按剩余时间建议与团队确认是否切换到 {status['deadline']['recommended_mode']}"
            "（确认后再写入 events）"
        )
    return action


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def display_width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def pad(text: str, width: int) -> str:
    return text + " " * max(0, width - display_width(text))


def progress_bar(percent: int, width: int = 20) -> str:
    filled = round(width * percent / 100)
    return "█" * filled + "░" * (width - filled)


def _fmt_score(value: float | None) -> str:
    return "—" if value is None else f"{value:g}"


def _problem_line(status: dict) -> str:
    problem = status["problem"]
    parts = [status["competition_label"]]
    if problem.get("year") or problem.get("letter"):
        parts.append(f"{problem.get('year') or '????'}-{problem.get('letter') or '?'}")
    if problem.get("title"):
        parts.append(str(problem["title"]))
    parts.append(f"{status['mode'] or '未设置'} 模式")
    return " · ".join(parts)


def _deadline_line(status: dict) -> str:
    deadline = status["deadline"]
    if not deadline["iso"]:
        return "未记录"
    if not deadline["valid"]:
        return f"{deadline['iso']}（无法解析，请使用 ISO 8601）"
    left = deadline["hours_left"]
    remaining = f"剩余 {left:g}h" if left > 0 else f"已超时 {abs(left):g}h"
    recommended = deadline["recommended_mode"] or "—"
    return f"{deadline['iso']} · {remaining} · 推荐 {recommended}"


STAGE_GLYPHS = {"done": "✓", "current": "▶", "pending": "○"}


def render_text(status: dict) -> str:
    lines = [
        "mathmodel-skill · 进度看板",
        _problem_line(status),
        f"截止  {_deadline_line(status)}",
        f"进度  {progress_bar(status['progress']['percent'])} "
        f"{status['progress']['percent']}% ({status['progress']['completed']}/{status['progress']['total']})",
        "",
    ]
    for stage in status["stages"]:
        latest = stage["latest"]
        row = f"  {STAGE_GLYPHS[stage['state']]} {stage['stage']} {pad(stage['label'], 20)}"
        if latest:
            row += (
                f" {pad(str(latest['verdict']), 16)} min {_fmt_score(latest['min'])}"
                f" · mean {_fmt_score(latest['mean'])}"
            )
            if latest["weighted_mean"] is not None:
                row += f" · w {_fmt_score(latest['weighted_mean'])}"
        lines.append(row.rstrip())

    qi_status = status["subproblems"]["qi_status"]
    if qi_status:
        lines.append("")
        lines.append("Stage 5 子问  " + " · ".join(f"{qi} {state}" for qi, state in qi_status.items()))

    gates = status["compliance"]
    baseline = [gates["rules_baseline"], gates["ai_ledger"]]
    final = [gates[key] for key, _ in STAGE9_GATES]
    lines.append("")
    lines.append("合规门  " + " · ".join(
        f"{'✓' if gate['ok'] else '○'} {gate['label']}：{gate['detail']}" for gate in baseline
    ))
    lines.append("终审门  " + " · ".join(
        f"{'✓' if gate['ok'] else '○'} {gate['label']}" for gate in final
    ))
    lines.append("")
    lines.append(f"下一步  {status['next_action']}")
    return "\n".join(lines)


def render_markdown(status: dict) -> str:
    lines = [
        f"**{_problem_line(status)}**",
        "",
        f"- 截止：{_deadline_line(status)}",
        f"- 进度：`{progress_bar(status['progress']['percent'], 10)}` "
        f"{status['progress']['percent']}%（{status['progress']['completed']}/{status['progress']['total']}）",
        "",
        "| | Stage | 最新 verdict | min | mean | 评审次数 |",
        "|---|---|---|---:|---:|---:|",
    ]
    for stage in status["stages"]:
        latest = stage["latest"] or {}
        lines.append(
            f"| {STAGE_GLYPHS[stage['state']]} | {stage['stage']} {stage['label']} | "
            f"{latest.get('verdict') or '—'} | {_fmt_score(latest.get('min'))} | "
            f"{_fmt_score(latest.get('mean'))} | {stage['evaluations']} |"
        )
    qi_status = status["subproblems"]["qi_status"]
    if qi_status:
        lines += ["", "Stage 5 子问：" + "，".join(f"`{qi}` {state}" for qi, state in qi_status.items())]
    gates = status["compliance"]
    lines += [
        "",
        "合规门：" + "，".join(
            f"{'✓' if gate['ok'] else '○'} {gate['label']}" for gate in gates.values()
        ),
        "",
        f"**下一步**：{status['next_action']}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show mathmodel-skill workspace progress (read-only).")
    location = parser.add_mutually_exclusive_group()
    location.add_argument("--workspace", help="项目目录；读取其中的 state/decision_log.json")
    location.add_argument("--decision-log", help="直接指定 decision_log.json 路径")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", dest="as_json", help="输出 JSON")
    output.add_argument("--markdown", action="store_true", help="输出适合贴进对话的 Markdown")
    parser.add_argument("--now", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    path = resolve_decision_log(args.decision_log, args.workspace)
    if not path.is_file():
        print(
            f"[FAIL] 未找到 {path}。先运行 scripts/init_workspace.py，或让 agent 从 Stage 0 初始化。",
            file=sys.stderr,
        )
        return 1
    try:
        log = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[FAIL] decision_log 无法读取: {exc}", file=sys.stderr)
        return 1

    now = None
    if args.now:
        now = parse_datetime(args.now)
        if now is None:
            parser.error("--now 必须是 ISO 8601 时间")
    try:
        status = build_status(log, now)
    except ValueError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    if args.as_json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    elif args.markdown:
        print(render_markdown(status))
    else:
        print(render_text(status))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

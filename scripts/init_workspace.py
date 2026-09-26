#!/usr/bin/env python3
"""Create a mathmodel-skill project workspace, or report where to resume.

The initializer is create-only: when ``state/decision_log.json`` already exists
it never rewrites it, and only reports the saved competition and stage. A new
state is copied from ``templates/shared/decision_log.json`` and filled with the
kickoff fields the team has already answered.

Usage:
    python scripts/init_workspace.py --competition cumcm --workspace .
    python scripts/init_workspace.py --competition mcm --workspace my-project \\
        --problem C --team-size 3 --hours-left 96
    python scripts/init_workspace.py --competition diangong --workspace . \\
        --problem 未公布 --deadline 2027-05-24T08:00+08:00 --json
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from status import VALID_MODES, parse_datetime, recommend_mode  # noqa: E402


SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = SKILL_ROOT / "templates" / "shared" / "decision_log.json"
COMPETITIONS = ("cumcm", "mcm", "diangong")
WORKSPACE_DIRS = (
    "state",
    "results",
    "figures",
    "paper_workspace",
    "paper_output",
    "support_materials",
)
UNPUBLISHED = {"", "未公布", "unknown", "tbd", "none"}


def topic_letters(competition: str) -> list[str]:
    specs = json.loads(
        (SKILL_ROOT / "competitions" / competition / "topic_specs.json").read_text(encoding="utf-8")
    )
    return sorted(specs.get("topics", {}))


def normalize_problem(competition: str, value: str | None) -> str | None:
    if value is None or value.strip().lower() in UNPUBLISHED:
        return None
    letter = value.strip().upper()
    allowed = topic_letters(competition)
    if letter not in allowed:
        raise ValueError(f"{competition} 的题号只能是 {'/'.join(allowed)} 或“未公布”，收到 {value!r}")
    return letter


def _write_new_json(path: Path, value: dict) -> None:
    """Write through a sibling temp file; refuse to replace an existing state."""
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        umask = os.umask(0)
        os.umask(umask)
        os.chmod(temp_path, 0o666 & ~umask)
        if path.exists():
            raise FileExistsError(f"{path} 已存在，拒绝覆盖")
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def build_state(
    competition: str,
    now: datetime,
    problem: str | None = None,
    year: int | None = None,
    team_size: int | None = None,
    deadline: datetime | None = None,
    mode: str | None = None,
    problem_pdf: str | None = None,
) -> dict:
    """Return a fresh decision log populated with the known kickoff fields."""
    state = copy.deepcopy(json.loads(TEMPLATE_PATH.read_text(encoding="utf-8")))
    state["competition"] = competition
    state["started_at"] = now.isoformat(timespec="seconds")
    if mode:
        state["mode"] = mode

    meta = state["problem_meta"]
    meta["letter"] = problem
    meta["team_size"] = team_size
    if deadline is not None:
        meta["deadline_iso"] = deadline.isoformat(timespec="minutes")
    meta["year"] = year if year is not None else (deadline.year if deadline is not None else None)

    detail = {
        "competition": competition,
        "problem": problem,
        "problem_pdf": problem_pdf,
        "created_dirs": list(WORKSPACE_DIRS),
    }
    state["events"]["log"].append({
        "type": "workspace_init",
        "ts": state["started_at"],
        "detail": detail,
    })
    return state


def initialize(
    workspace: Path,
    competition: str,
    now: datetime,
    **fields,
) -> dict:
    """Create directories and a new state, or report the existing resume point."""
    for name in WORKSPACE_DIRS:
        (workspace / name).mkdir(parents=True, exist_ok=True)
    state_path = workspace / "state" / "decision_log.json"

    if state_path.exists():
        try:
            existing = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"已有 {state_path} 但无法解析，未做任何修改: {exc}") from exc
        if not isinstance(existing, dict):
            raise ValueError(f"已有 {state_path} 的根节点不是 object，未做任何修改")
        saved = existing.get("competition")
        if saved != competition:
            raise ValueError(
                f"已有 state 的竞赛是 {saved!r}，与 --competition {competition} 不一致；"
                "未做任何修改。若确需切换竞赛，请按 SKILL.md 的“切到 <comp>”流程处理。"
            )
        return {
            "action": "resumed",
            "state_path": str(state_path),
            "competition": saved,
            "current_stage": existing.get("current_stage"),
            "mode": existing.get("mode"),
        }

    state = build_state(competition, now, **fields)
    _write_new_json(state_path, state)
    deadline = parse_datetime(state["problem_meta"]["deadline_iso"])
    hours_left = None if deadline is None else round((deadline - now).total_seconds() / 3600, 1)
    return {
        "action": "created",
        "state_path": str(state_path),
        "competition": competition,
        "current_stage": state["current_stage"],
        "mode": state["mode"],
        "problem": state["problem_meta"]["letter"],
        "deadline_iso": state["problem_meta"]["deadline_iso"],
        "hours_left": hours_left,
        "recommendation": recommend_mode(hours_left),
        "directories": list(WORKSPACE_DIRS),
    }


def _print_human(result: dict) -> None:
    if result["action"] == "resumed":
        print(f"✓ 已有工作区状态，未做任何修改: {result['state_path']}")
        print(f"  竞赛 {result['competition']} · 当前 Stage {result['current_stage']} · {result['mode']} 模式")
        print("  ↳ 从 current_stage 继续；运行 scripts/status.py 查看进度看板。")
        return
    print(f"✓ 已创建工作区状态: {result['state_path']}")
    print(f"  目录: {', '.join(result['directories'])}")
    print(f"  竞赛 {result['competition']} · 题号 {result['problem'] or '未公布'} · {result['mode']} 模式")
    recommendation = result["recommendation"]
    if result["deadline_iso"]:
        print(f"  截止 {result['deadline_iso']} · 剩余 {result['hours_left']:g}h")
    print(f"  模式建议: {recommendation['note']}")
    if recommendation["mode"] and recommendation["mode"] != result["mode"]:
        print(f"  ↳ 建议与团队确认是否切换到 {recommendation['mode']}；确认后再写入 events。")
    print("  ↳ 下一步: Stage 0 团队启动（references/stage_00_kickoff.md）")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Initialize a mathmodel-skill workspace (create-only).")
    parser.add_argument("--competition", choices=COMPETITIONS, required=True)
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="项目目录，默认当前目录")
    parser.add_argument("--problem", help="题号，如 A/B/C；题目未公布时填“未公布”")
    parser.add_argument("--year", type=int, help="竞赛年份；缺省时取截止时间所在年份")
    parser.add_argument("--team-size", type=int)
    timing = parser.add_mutually_exclusive_group()
    timing.add_argument("--deadline", help="ISO 8601 截止时间，如 2026-09-13T20:00+08:00")
    timing.add_argument("--hours-left", type=float, help="距现在的小时数")
    parser.add_argument("--mode", choices=VALID_MODES, help="显式设置模式；缺省沿用模板的 standard")
    parser.add_argument("--problem-pdf", help="题面 PDF 路径，记录到 events.log")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--now", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    now = parse_datetime(args.now) if args.now else datetime.now(timezone.utc).astimezone()
    if now is None:
        parser.error("--now 必须是 ISO 8601 时间")
    if args.team_size is not None and args.team_size < 1:
        parser.error("--team-size 必须是正整数")
    deadline = None
    if args.deadline:
        deadline = parse_datetime(args.deadline)
        if deadline is None:
            parser.error("--deadline 必须是 ISO 8601 时间，如 2026-09-13T20:00+08:00")
    elif args.hours_left is not None:
        if args.hours_left <= 0:
            parser.error("--hours-left 必须大于 0")
        deadline = now + timedelta(hours=args.hours_left)

    try:
        problem = normalize_problem(args.competition, args.problem)
        result = initialize(
            args.workspace.resolve(),
            args.competition,
            now,
            problem=problem,
            year=args.year,
            team_size=args.team_size,
            deadline=deadline,
            mode=args.mode,
            problem_pdf=args.problem_pdf,
        )
    except (OSError, ValueError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

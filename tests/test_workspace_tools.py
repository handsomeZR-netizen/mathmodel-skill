#!/usr/bin/env python3
"""Regression tests for workspace initialization and the progress dashboard."""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 11, 20, 0, tzinfo=timezone(timedelta(hours=8)))


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"mathmodel_workspace_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


doctor = load_script("doctor")
init_workspace = load_script("init_workspace")
status = load_script("status")


def template_state() -> dict:
    return json.loads(
        (ROOT / "templates" / "shared" / "decision_log.json").read_text(encoding="utf-8")
    )


def score_entry(verdict: str, minimum: float, mean: float, iteration: int = 0) -> dict:
    return {"iteration": iteration, "scores": {}, "min": minimum, "mean": mean,
            "verdict": verdict, "issues": [], "ts": "2026-09-11T10:00:00"}


def midway_state() -> dict:
    """A CUMCM state paused inside Stage 5 with one sub-question to refine."""
    state = template_state()
    state["problem_meta"].update({
        "year": 2026, "letter": "A", "team_size": 3,
        "deadline_iso": "2026-09-13T20:00+08:00",
    })
    state["current_stage"] = 5
    for stage in range(5):
        state["scores"][str(stage)].append(score_entry("pass", 7, 8.2))
    state["scores"]["5"].append(score_entry("refine_partial", 6, 7.9, iteration=1))
    state["stages"]["5"].update({
        "qi_count": 3,
        "qi_status": {"Q1": "pass", "Q2": "refine", "Q3": "mark_for_review"},
        "refine_qis": ["Q2"],
        "review_qis": ["Q3"],
    })
    state["compliance"]["ruleset"]["verified_at"] = "2026-09-10"
    return state


class InitWorkspaceTests(unittest.TestCase):
    def test_creates_directories_and_valid_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            result = init_workspace.initialize(
                workspace, "mcm", NOW,
                problem=init_workspace.normalize_problem("mcm", "c"),
                team_size=3, deadline=NOW + timedelta(hours=96),
            )
            self.assertEqual(result["action"], "created")
            for name in init_workspace.WORKSPACE_DIRS:
                self.assertTrue((workspace / name).is_dir(), name)

            state = json.loads((workspace / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual(state["competition"], "mcm")
            self.assertEqual(state["current_stage"], 0)
            self.assertEqual(state["problem_meta"]["letter"], "C")
            self.assertEqual(state["problem_meta"]["team_size"], 3)
            self.assertEqual(state["problem_meta"]["year"], 2026)
            self.assertEqual(state["problem_meta"]["deadline_iso"], "2026-09-15T20:00+08:00")
            self.assertEqual(state["events"]["log"][-1]["type"], "workspace_init")
            self.assertIsNone(state["compliance"]["ai_usage"])
            self.assertEqual(result["recommendation"]["mode"], "standard")

            checks = doctor.run_checks("mcm", workspace=workspace, check_tools=False)
            workspace_check = next(item for item in checks if item.name == "workspace-state")
            self.assertEqual(workspace_check.status, "pass")

    def test_existing_state_is_never_rewritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            init_workspace.initialize(workspace, "cumcm", NOW)
            state_path = workspace / "state" / "decision_log.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["current_stage"] = 4
            state_path.write_text(json.dumps(state), encoding="utf-8")
            before = state_path.read_bytes()

            result = init_workspace.initialize(workspace, "cumcm", NOW, team_size=5)
            self.assertEqual(result["action"], "resumed")
            self.assertEqual(result["current_stage"], 4)
            self.assertEqual(state_path.read_bytes(), before)

            with self.assertRaisesRegex(ValueError, "不一致"):
                init_workspace.initialize(workspace, "mcm", NOW)
            self.assertEqual(state_path.read_bytes(), before)

    def test_unparseable_existing_state_is_reported_not_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            (workspace / "state").mkdir()
            state_path = workspace / "state" / "decision_log.json"
            state_path.write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "无法解析"):
                init_workspace.initialize(workspace, "cumcm", NOW)
            self.assertEqual(state_path.read_text(encoding="utf-8"), "{broken")

    def test_problem_letters_follow_competition_topic_specs(self) -> None:
        self.assertEqual(init_workspace.normalize_problem("diangong", "b"), "B")
        self.assertIsNone(init_workspace.normalize_problem("cumcm", "未公布"))
        self.assertIsNone(init_workspace.normalize_problem("cumcm", None))
        with self.assertRaisesRegex(ValueError, "A/B"):
            init_workspace.normalize_problem("diangong", "C")

    def test_cli_rejects_conflicting_or_invalid_timing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            for argv in (
                ["--competition", "cumcm", "--workspace", temp,
                 "--deadline", "2026-09-13T20:00+08:00", "--hours-left", "5"],
                ["--competition", "cumcm", "--workspace", temp, "--hours-left", "0"],
                ["--competition", "cumcm", "--workspace", temp, "--deadline", "next friday"],
            ):
                with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as raised:
                        init_workspace.main(argv)
                    self.assertEqual(raised.exception.code, 2)
            self.assertFalse((Path(temp) / "state" / "decision_log.json").exists())

    def test_cli_reports_bad_problem_letter_without_creating_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = init_workspace.main(
                    ["--competition", "diangong", "--workspace", temp, "--problem", "E"]
                )
            self.assertEqual(code, 1)
            self.assertIn("A/B", stderr.getvalue())
            self.assertFalse((Path(temp) / "state" / "decision_log.json").exists())


class ModeRecommendationTests(unittest.TestCase):
    def test_boundaries_mirror_skill_md(self) -> None:
        cases = {
            None: None, -1: None, 0: None, 3: "championship", 5.9: "championship",
            6: "fast", 23.9: "fast", 24: "standard", 60: "standard", 72: "standard",
        }
        for hours, expected in cases.items():
            with self.subTest(hours=hours):
                self.assertEqual(status.recommend_mode(hours)["mode"], expected)

    def test_naive_and_zulu_timestamps_are_timezone_aware(self) -> None:
        self.assertIsNotNone(status.parse_datetime("2026-09-13T20:00").tzinfo)
        self.assertEqual(
            status.parse_datetime("2026-09-13T12:00Z"),
            status.parse_datetime("2026-09-13T20:00+08:00"),
        )
        self.assertIsNone(status.parse_datetime("soon"))
        self.assertIsNone(status.parse_datetime(None))


class StatusDashboardTests(unittest.TestCase):
    def test_stage_table_matches_reference_files(self) -> None:
        for number, key, _ in status.STAGES:
            with self.subTest(stage=number):
                path = ROOT / status._stage_reference(number, key)
                self.assertTrue(path.is_file(), path)
                _, frontmatter, _ = path.read_text(encoding="utf-8").split("---", 2)
                metadata = yaml.safe_load(frontmatter)
                self.assertEqual((metadata["stage"], metadata["name"]), (number, key))

    def test_fresh_state_points_to_stage_zero(self) -> None:
        result = status.build_status(template_state(), NOW)
        self.assertEqual(result["progress"]["completed"], 0)
        self.assertEqual(result["stages"][0]["state"], "current")
        self.assertIn("references/stage_00_kickoff.md", result["next_action"])
        self.assertFalse(result["compliance"]["ai_ledger"]["ok"])
        self.assertIsNone(result["deadline"]["hours_left"])

    def test_midway_state_summarizes_scores_subproblems_and_gates(self) -> None:
        result = status.build_status(midway_state(), NOW)
        self.assertEqual(result["progress"], {"completed": 5, "total": 10, "percent": 50})
        self.assertEqual(result["stages"][5]["latest"]["verdict"], "refine_partial")
        self.assertEqual(result["stages"][6]["state"], "pending")
        self.assertEqual(result["deadline"]["hours_left"], 48.0)
        self.assertEqual(result["deadline"]["recommended_mode"], "standard")
        self.assertFalse(result["deadline"]["mode_mismatch"])
        self.assertIn("Q2", result["next_action"])
        self.assertTrue(result["compliance"]["rules_baseline"]["ok"])
        self.assertEqual(result["subproblems"]["qi_status"]["Q3"], "mark_for_review")

        text = status.render_text(result)
        self.assertIn("50% (5/10)", text)
        self.assertIn("Q2 refine", text)
        markdown = status.render_markdown(result)
        self.assertIn("| ▶ | 5 递归求解 Q1…Qn | refine_partial | 6 | 7.9 | 1 |", markdown)

    def test_next_action_follows_the_current_verdict(self) -> None:
        cases = {
            "block": "high-severity",
            "refine": "section patch",
            "carryover": "L2",
            "pass": "Stage 6「稳健性分析」",
        }
        for verdict, expected in cases.items():
            with self.subTest(verdict=verdict):
                state = midway_state()
                state["scores"]["5"][-1]["verdict"] = verdict
                self.assertIn(expected, status.build_status(state, NOW)["next_action"])

    def test_pass_with_review_names_the_review_questions(self) -> None:
        state = midway_state()
        state["scores"]["5"][-1]["verdict"] = "pass_with_review"
        self.assertIn("L2 必读 Q3", status.build_status(state, NOW)["next_action"])

    def test_stage_nine_lists_open_gates_until_submission_ready(self) -> None:
        state = midway_state()
        state["current_stage"] = 9
        state["scores"]["9"].append(score_entry("pass", 8, 8.5))
        checks = state["stages"]["9"]["compliance_checks"]
        checks.update({"rules_verified": True, "anonymity_passed": True,
                       "page_limit_passed": True})
        action = status.build_status(state, NOW)["next_action"]
        self.assertIn("AI 披露", action)
        self.assertIn("支撑材料", action)
        self.assertNotIn("匿名", action)

        checks.update({"ai_disclosure_passed": True, "supporting_materials_passed": True})
        self.assertIn("submission_ready", status.build_status(state, NOW)["next_action"])

        state["stages"]["9"]["submission_ready"] = True
        result = status.build_status(state, NOW)
        self.assertEqual(result["progress"]["percent"], 100)
        self.assertIn("按当届官方渠道提交", result["next_action"])

    def test_deadline_pressure_suggests_but_never_switches_mode(self) -> None:
        state = midway_state()
        state["problem_meta"]["deadline_iso"] = "2026-09-12T08:00+08:00"
        result = status.build_status(state, NOW)
        self.assertEqual(result["deadline"]["recommended_mode"], "fast")
        self.assertTrue(result["deadline"]["mode_mismatch"])
        self.assertEqual(result["mode"], "standard")
        self.assertIn("确认", result["next_action"])

        state["problem_meta"]["deadline_iso"] = "2026-09-11T08:00+08:00"
        self.assertIn("已超过", status.build_status(state, NOW)["next_action"])

    def test_invalid_current_stage_is_rejected(self) -> None:
        for value in (None, True, -1, 10, "5"):
            state = template_state()
            state["current_stage"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "current_stage"):
                status.build_status(state, NOW)

    def test_display_width_pads_cjk_labels(self) -> None:
        self.assertEqual(status.display_width("选题A"), 5)
        self.assertEqual(status.display_width(status.pad("选题", 8)), 8)

    def test_cli_is_read_only_and_supports_all_formats(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state_dir = Path(temp) / "state"
            state_dir.mkdir()
            state_path = state_dir / "decision_log.json"
            state_path.write_text(json.dumps(midway_state(), ensure_ascii=False), encoding="utf-8")
            before = state_path.read_bytes()

            base = [sys.executable, str(ROOT / "scripts" / "status.py"),
                    "--workspace", temp, "--now", NOW.isoformat()]
            as_json = subprocess.run(base + ["--json"], capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(as_json.stdout)["current_stage"], 5)
            markdown = subprocess.run(base + ["--markdown"], capture_output=True, text=True, check=True)
            self.assertIn("**下一步**", markdown.stdout)
            text = subprocess.run(base, capture_output=True, text=True, check=True)
            self.assertIn("进度看板", text.stdout)
            self.assertEqual(state_path.read_bytes(), before)

    def test_cli_fails_cleanly_without_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "status.py"), "--workspace", temp],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("init_workspace.py", result.stderr)

    def test_init_then_status_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            init = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "init_workspace.py"),
                 "--competition", "diangong", "--workspace", temp, "--problem", "B",
                 "--hours-left", "5", "--json"],
                capture_output=True, text=True, check=True,
            )
            created = json.loads(init.stdout)
            self.assertEqual(created["action"], "created")
            self.assertEqual(created["recommendation"]["mode"], "championship")
            self.assertEqual(created["mode"], "standard")

            shown = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "status.py"), "--workspace", temp, "--json"],
                capture_output=True, text=True, check=True,
            )
            result = json.loads(shown.stdout)
            self.assertEqual(result["competition_label"], "电工杯")
            self.assertEqual(result["problem"]["letter"], "B")
            self.assertTrue(result["deadline"]["mode_mismatch"])


if __name__ == "__main__":
    unittest.main()

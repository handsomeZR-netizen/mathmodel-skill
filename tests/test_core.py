#!/usr/bin/env python3
"""Core regression tests for package integrity and deterministic workflow tools."""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"mathmodel_test_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


doctor = load_script("doctor")
extract_diff = load_script("extract_diff")
render_ai_usage = load_script("render_ai_usage")
render_paper = load_script("render_paper")
score_artifact = load_script("score_artifact")


def load_fixture(filename: str) -> dict:
    return json.loads(
        (ROOT / "tests" / "fixtures" / filename).read_text(encoding="utf-8")
    )


def write_required_paper_workspace(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    for section, filename in render_paper.SECTION_TO_FILE.items():
        content = f"Rendered {section}.\n" if section == "abstract" else (
            f"# {section}\n\nRendered {section}.\n"
        )
        (workspace / filename).write_text(content, encoding="utf-8")


class PackageIntegrityTests(unittest.TestCase):
    def test_all_json_and_yaml_files_parse(self) -> None:
        json_paths = sorted(
            path for path in ROOT.rglob("*.json")
            if ".git" not in path.parts
        )
        yaml_paths = sorted(
            path for pattern in ("*.yaml", "*.yml")
            for path in ROOT.rglob(pattern)
            if ".git" not in path.parts
        )

        self.assertTrue(json_paths)
        self.assertTrue(yaml_paths)
        for path in json_paths:
            with self.subTest(path=path.relative_to(ROOT)):
                json.loads(path.read_text(encoding="utf-8"))
        for path in yaml_paths:
            with self.subTest(path=path.relative_to(ROOT)):
                parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
                self.assertIsNotNone(parsed)

    def test_all_stage_frontmatters_are_valid_yaml(self) -> None:
        stages = []
        paths = sorted((ROOT / "references").glob("stage_[0-9][0-9]_*.md"))
        self.assertEqual(len(paths), 10)

        for path in paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("---\n"))
                _, frontmatter, _ = text.split("---", 2)
                metadata = yaml.safe_load(frontmatter)
                self.assertIsInstance(metadata, dict)
                self.assertIsInstance(metadata.get("inputs"), list)
                self.assertIsInstance(metadata.get("outputs"), list)
                stages.append(metadata["stage"])

        self.assertEqual(stages, list(range(10)))

    def test_anti_pattern_counts_and_deferred_state(self) -> None:
        expected = {"cumcm": 42, "mcm": 16, "diangong": 12}
        pattern = re.compile(r"^###\s+([A-Z]\d+)\.\s", re.MULTILINE)

        for competition, count in expected.items():
            with self.subTest(competition=competition):
                text = (
                    ROOT / "competitions" / competition / "anti_patterns.md"
                ).read_text(encoding="utf-8")
                identifiers = pattern.findall(text)
                self.assertEqual(len(identifiers), count)
                self.assertEqual(len(set(identifiers)), count)

        decision_log = json.loads(
            (ROOT / "templates" / "shared" / "decision_log.json").read_text(
                encoding="utf-8"
            )
        )
        declared = decision_log["stages"]["9"]["anti_patterns_check"]["total"]
        self.assertIsNone(declared)

    def test_release_version_is_consistent_across_entrypoints(self) -> None:
        plugin = json.loads(
            (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        version = plugin["version"]
        major_minor = ".".join(version.split(".")[:2])
        self.assertIn(f"(v{major_minor})", (ROOT / "SKILL.md").read_text(encoding="utf-8"))
        self.assertIn(
            f"version-v{version}-", (ROOT / "README.md").read_text(encoding="utf-8")
        )
        self.assertIn(
            f"v{major_minor}", (ROOT / "assets" / "banner.svg").read_text(encoding="utf-8")
        )

    def test_readme_local_links_and_images_exist(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        targets = set(re.findall(r'(?:src|href)="\./([^"#]+)"', readme))
        targets |= set(re.findall(r"\]\(\./([^)#]+)\)", readme))
        self.assertIn("assets/banner.svg", targets)
        for target in sorted(targets):
            with self.subTest(target=target):
                self.assertTrue((ROOT / target).exists())

    def test_effective_dimension_weights_only_use_valid_dimensions(self) -> None:
        table = json.loads(
            (ROOT / "config" / "dim_weights.json").read_text(encoding="utf-8")
        )
        for competition, competition_table in table.items():
            if competition.startswith("_") or not isinstance(competition_table, dict):
                continue
            for task_type in competition_table:
                if task_type.startswith("_"):
                    continue
                effective = score_artifact.load_dim_weights_table(competition, task_type)
                for stage, dimensions in effective.items():
                    with self.subTest(
                        competition=competition, task_type=task_type, stage=stage
                    ):
                        whitelist = score_artifact.load_dim_whitelist(
                            competition, int(stage)
                        )
                        configured = {
                            key for key in dimensions if not key.startswith("_")
                        }
                        self.assertLessEqual(configured, whitelist)


class ScoreArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.good = load_fixture("test_critique_good.json")

    def test_good_critique_validates(self) -> None:
        ok, message = score_artifact.validate_critique(self.good, 1, "cumcm")
        self.assertTrue(ok, message)

    def test_existing_competition_and_empirical_fixtures(self) -> None:
        cases = (
            ("mcm_smoke.json", "mcm", "A_continuous", "pass"),
            ("diangong_smoke.json", "diangong", "A_engineering", "refine"),
        )
        for filename, competition, task_type, expected_verdict in cases:
            with self.subTest(filename=filename):
                critique = load_fixture(filename)
                ok, message = score_artifact.validate_critique(
                    critique, critique["stage_id"], competition
                )
                self.assertTrue(ok, message)
                weights = score_artifact.load_dim_weights_table(
                    competition, task_type
                ).get(str(critique["stage_id"]), {})
                self.assertEqual(
                    score_artifact.compute_verdict(critique, weights),
                    expected_verdict,
                )

        diangong = score_artifact.load_empirical("diangong")
        self.assertEqual(diangong["source"]["papers_total"], 0)
        self.assertEqual(diangong["dims"], {})
        self.assertIn(
            "不在 empirical 字段",
            score_artifact.inject_evidence("abstract_chars", 700, diangong),
        )

        empirical_fixture = load_fixture("cumcm_empirical_inject.json")
        ok, message = score_artifact.validate_critique(
            empirical_fixture, 8, "cumcm"
        )
        self.assertTrue(ok, message)
        evidence = score_artifact.inject_evidence(
            "abstract_chars",
            empirical_fixture["evidence_metrics"]["abstract_chars"],
            score_artifact.load_empirical("cumcm"),
        )
        self.assertIn(empirical_fixture["_expected_output_contains"], evidence)
        self.assertIn("status=低于 p25", evidence)

    def test_bad_dimension_fixture_is_rejected(self) -> None:
        critique = load_fixture("test_critique_bad_keys.json")
        ok, message = score_artifact.validate_critique(critique, 1, "cumcm")
        self.assertFalse(ok)
        self.assertIn("dim key 不匹配", message)

    def test_inconsistent_or_invalid_score_inputs_are_rejected(self) -> None:
        cases = []

        wrong_stage = copy.deepcopy(self.good)
        wrong_stage["stage_id"] = 2
        cases.append(("stage", wrong_stage, "stage_id 不一致"))

        boolean_stage = copy.deepcopy(self.good)
        boolean_stage["stage_id"] = True
        cases.append(("boolean stage", boolean_stage, "stage_id 不一致"))

        wrong_minimum = copy.deepcopy(self.good)
        wrong_minimum["min_score"] = 8
        cases.append(("minimum", wrong_minimum, "min_score 与 scores 不一致"))

        boolean_minimum = copy.deepcopy(self.good)
        boolean_minimum["min_score"] = True
        cases.append(("boolean minimum", boolean_minimum, "min_score 与 scores 不一致"))

        wrong_mean = copy.deepcopy(self.good)
        wrong_mean["mean_score"] = 7.9
        cases.append(("mean", wrong_mean, "mean_score 与 scores 不一致"))

        invalid_iteration = copy.deepcopy(self.good)
        invalid_iteration["iteration"] = -1
        cases.append(("iteration", invalid_iteration, "iteration 必须是非负整数"))

        invalid_dimension_score = copy.deepcopy(self.good)
        invalid_dimension_score["scores"]["1_three_options_depth"]["score"] = True
        cases.append(("dimension score", invalid_dimension_score, "超出 [1,10]"))

        missing_evidence = copy.deepcopy(self.good)
        missing_evidence["scores"]["1_three_options_depth"].pop("evidence")
        cases.append(("evidence", missing_evidence, "evidence 必须是非空字符串"))

        malformed_issue = copy.deepcopy(self.good)
        malformed_issue["issues"] = [{
            "severity": "urgent",
            "where": "§1",
            "anti_pattern_id": None,
            "fix": "Repair the section.",
        }]
        cases.append(("issue", malformed_issue, "severity 必须是"))

        for name, critique, expected_message in cases:
            with self.subTest(name=name):
                ok, message = score_artifact.validate_critique(
                    critique, 1, "cumcm"
                )
                self.assertFalse(ok)
                self.assertIn(expected_message, message)

        ok, message = score_artifact.validate_critique([], 1, "cumcm")
        self.assertFalse(ok)
        self.assertIn("根节点", message)

    def test_cli_persists_recomputed_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            decision_log_path = temp_path / "decision_log.json"
            critique_path = temp_path / "critique.json"
            decision_log_path.write_text(
                (ROOT / "templates" / "shared" / "decision_log.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            critique = copy.deepcopy(self.good)
            critique["verdict"] = "pass_early"
            critique_path.write_text(
                json.dumps(critique, ensure_ascii=False), encoding="utf-8"
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "score_artifact.py"),
                    "--stage",
                    "1",
                    "--critique",
                    str(critique_path),
                    "--decision-log",
                    str(decision_log_path),
                    "--competition",
                    "cumcm",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Actual: pass", result.stdout)
            persisted = json.loads(decision_log_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["scores"]["1"][-1]["verdict"], "pass")
            self.assertEqual(persisted["iterations"]["1"], 1)
            self.assertEqual(list(temp_path.glob(".decision_log.json.*.tmp")), [])

    def test_cli_persists_carryover_at_iteration_cap(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            decision_log_path = temp_path / "decision_log.json"
            critique_path = temp_path / "critique.json"
            decision_log_path.write_text(
                (ROOT / "templates" / "shared" / "decision_log.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            critique = copy.deepcopy(self.good)
            for dim in critique["scores"].values():
                dim["score"] = 7
            critique.update({
                "iteration": 3,
                "min_score": 7,
                "mean_score": 7.0,
                "verdict": "refine",
            })
            critique_path.write_text(
                json.dumps(critique, ensure_ascii=False), encoding="utf-8"
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "score_artifact.py"),
                    "--stage",
                    "1",
                    "--critique",
                    str(critique_path),
                    "--decision-log",
                    str(decision_log_path),
                    "--competition",
                    "cumcm",
                    "--max-iter",
                    "3",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("下一步: carryover", result.stdout)
            persisted = json.loads(decision_log_path.read_text(encoding="utf-8"))
            self.assertEqual(
                persisted["scores"]["1"][-1]["verdict"], "carryover"
            )

    def test_cli_fails_cleanly_on_malformed_json_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            decision_log_path = temp_path / "decision_log.json"
            critique_path = temp_path / "critique.json"
            template = (
                ROOT / "templates" / "shared" / "decision_log.json"
            ).read_text(encoding="utf-8")

            cases = (
                (template, "[]", "critique 根节点必须是 object"),
                (template, "{", "critique 无法读取"),
                ("[]", json.dumps(self.good), "decision_log 根节点必须是 object"),
                ("{", json.dumps(self.good), "decision_log 无法读取"),
            )
            for decision_text, critique_text, expected in cases:
                with self.subTest(expected=expected):
                    decision_log_path.write_text(decision_text, encoding="utf-8")
                    critique_path.write_text(critique_text, encoding="utf-8")
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(ROOT / "scripts" / "score_artifact.py"),
                            "--stage",
                            "1",
                            "--critique",
                            str(critique_path),
                            "--decision-log",
                            str(decision_log_path),
                            "--competition",
                            "cumcm",
                        ],
                        cwd=ROOT,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                    )
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(expected, result.stdout)
                    self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_decision_log_replace_is_atomic_and_in_same_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            decision_log_path = Path(temp) / "decision_log.json"
            decision_log_path.write_text(
                (ROOT / "templates" / "shared" / "decision_log.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            critique = copy.deepcopy(self.good)
            original_replace = os.replace
            with mock.patch.object(
                score_artifact.os, "replace", wraps=original_replace
            ) as replace:
                score_artifact.update_decision_log(
                    1, critique, decision_log_path
                )

            replace.assert_called_once()
            source, destination = map(Path, replace.call_args.args)
            self.assertEqual(source.parent, decision_log_path.parent)
            self.assertEqual(destination, decision_log_path)
            self.assertFalse(source.exists())

    def test_atomic_json_rejects_non_finite_values_without_replacing_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            decision_log_path = Path(temp) / "decision_log.json"
            original = '{"safe": true}\n'
            decision_log_path.write_text(original, encoding="utf-8")

            with self.assertRaises(ValueError):
                score_artifact._atomic_write_json(
                    decision_log_path, {"unsafe": math.nan}
                )

            self.assertEqual(
                decision_log_path.read_text(encoding="utf-8"), original
            )
            self.assertEqual(
                list(decision_log_path.parent.glob(".decision_log.json.*.tmp")), []
            )

    def test_stage5_aggregate_fixtures_and_persistence(self) -> None:
        passing = load_fixture("cumcm_stage5_per_qi.json")
        result = score_artifact.compute_stage5_verdict(
            passing["qi_results"], passing["qi_weights"]
        )
        expected = passing["_expected_output"]
        self.assertEqual(result["verdict"], expected["verdict"])
        self.assertEqual(result["review_qis"], expected["review_qis"])
        self.assertEqual(result["refine_qis"], expected["refine_qis"])
        self.assertEqual(result["weighted_min"], expected["weighted_min"])
        self.assertAlmostEqual(
            result["weighted_mean"], expected["weighted_mean_approx"], places=2
        )

        partial = load_fixture("cumcm_stage5_refine_partial.json")
        partial_result = score_artifact.compute_stage5_verdict(
            partial["qi_results"], partial["qi_weights"]
        )
        self.assertEqual(
            partial_result["verdict"], partial["_expected_output"]["verdict"]
        )
        self.assertEqual(
            partial_result["refine_qis"], partial["_expected_output"]["refine_qis"]
        )

        qi_results = passing["qi_results"][:2]
        result = score_artifact.compute_stage5_verdict(qi_results, None)
        self.assertEqual(result["qi_weights"], [1.0, 1.0])
        with tempfile.TemporaryDirectory() as temp:
            decision_log_path = Path(temp) / "decision_log.json"
            decision_log_path.write_text(
                (ROOT / "templates" / "shared" / "decision_log.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            score_artifact.update_stage5_aggregate(
                result, qi_results, None, decision_log_path
            )
            persisted = json.loads(decision_log_path.read_text(encoding="utf-8"))
            stage5 = persisted["stages"]["5"]
            self.assertEqual(stage5["qi_status"], result["qi_status"])
            self.assertEqual(stage5["aggregate"]["verdict"], result["verdict"])
            self.assertEqual(stage5["qi_weights"], [1.0, 1.0])

        with self.assertRaisesRegex(ValueError, "重复子问"):
            score_artifact.compute_stage5_verdict(
                [qi_results[0], dict(qi_results[0])]
            )

    def test_stage5_aggregate_rejects_inconsistent_or_non_finite_input(self) -> None:
        good = [
            {"qi": "Q1", "min": 7, "mean": 8.0, "issues": []},
            {"qi": "Q2", "min": 8, "mean": 8.4, "issues": []},
        ]
        cases = [
            ([], None, "至少包含一个"),
            ([{"qi": "Q1", "min": 9, "mean": 8}], None, "不能大于"),
            (good, [1.0], "长度"),
            (good, [1.0, math.nan], "有限正数"),
            (good, [1.0, math.inf], "有限正数"),
        ]
        inconsistent_scores = copy.deepcopy(good)
        inconsistent_scores[0]["scores"] = {
            f"dim_{index}": {"score": score}
            for index, score in enumerate((7, 8, 8, 8, 8), 1)
        }
        inconsistent_scores[0]["mean"] = 9.0
        cases.append((inconsistent_scores, None, "mean 与 scores 不一致"))

        for qi_results, qi_weights, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    score_artifact.compute_stage5_verdict(
                        qi_results, qi_weights
                    )


class RenderPaperTests(unittest.TestCase):
    def write_ai_log(self, root: Path, competition: str, entries: list) -> Path:
        path = root / "state" / "decision_log.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"competition": competition, "compliance": {"ai_usage": entries}},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return path

    def test_mcm_without_ai_report_removes_the_entire_optional_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            workspace = temp_path / "paper_workspace"
            output = temp_path / "paper_output"
            write_required_paper_workspace(workspace)

            with contextlib.redirect_stdout(io.StringIO()):
                main_path, _ = render_paper.fill_template(
                    "mcm", workspace, output, prefer_pandoc=False
                )

            main_text = main_path.read_text(encoding="utf-8")
            self.assertIsNone(render_paper.SECTION_MARKER_RE.search(main_text))
            self.assertNotIn("Report on Use of AI", main_text)
            self.assertNotIn(r"\input{sections/ai_use_report}", main_text)
            self.assertFalse((output / "sections" / "ai_use_report.tex").exists())
            for section in render_paper.SECTION_TO_FILE:
                self.assertIn(rf"\input{{sections/{section}}}", main_text)

    def test_mcm_generated_ai_report_is_wired_without_duplicate_heading(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            workspace = temp_path / "paper_workspace"
            output = temp_path / "paper_output"
            support = temp_path / "support_materials"
            write_required_paper_workspace(workspace)
            decision_log = self.write_ai_log(temp_path, "mcm", [])
            report = render_ai_usage.render_reports(
                decision_log, workspace, support, "mcm"
            )[0]
            self.assertNotIn("# Report on Use of AI", report.read_text(encoding="utf-8"))

            with contextlib.redirect_stdout(io.StringIO()):
                main_path, _ = render_paper.fill_template(
                    "mcm", workspace, output, prefer_pandoc=False
                )

            main_text = main_path.read_text(encoding="utf-8")
            self.assertEqual(main_text.count(r"\section*{Report on Use of AI}"), 1)
            self.assertIn(r"\input{sections/ai_use_report}", main_text)
            report_tex = (output / "sections" / "ai_use_report.tex").read_text(
                encoding="utf-8"
            )
            self.assertNotIn(r"\section{Report on Use of AI", report_tex)

    def test_diangong_template_wires_all_ten_markers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            workspace = temp_path / "paper_workspace"
            output = temp_path / "paper_output"
            write_required_paper_workspace(workspace)

            with contextlib.redirect_stdout(io.StringIO()):
                main_path, _ = render_paper.fill_template(
                    "diangong", workspace, output, prefer_pandoc=False
                )

            main_text = main_path.read_text(encoding="utf-8")
            self.assertIsNone(render_paper.SECTION_MARKER_RE.search(main_text))
            for section in render_paper.SECTION_TO_FILE:
                self.assertIn(rf"\input{{sections/{section}}}", main_text)

    def test_cumcm_no_ai_statement_is_inserted_after_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            workspace = temp_path / "paper_workspace"
            output = temp_path / "paper_output"
            support = temp_path / "support_materials"
            write_required_paper_workspace(workspace)
            decision_log = self.write_ai_log(temp_path, "cumcm", [])
            outputs = render_ai_usage.render_reports(
                decision_log, workspace, support, "cumcm"
            )
            self.assertEqual(
                outputs, [workspace / render_ai_usage.CUMCM_NO_USE_FILENAME]
            )
            self.assertFalse(support.exists())

            with contextlib.redirect_stdout(io.StringIO()):
                main_path, _ = render_paper.fill_template(
                    "cumcm", workspace, output, prefer_pandoc=False
                )

            main_text = main_path.read_text(encoding="utf-8")
            statement = "本参赛队未使用任何 AI 工具。"
            statement_input = r"\input{sections/cumcm_no_ai_statement}"
            statement_tex = output / "sections" / "cumcm_no_ai_statement.tex"
            self.assertTrue(statement_tex.is_file())
            self.assertIn(statement, statement_tex.read_text(encoding="utf-8"))
            self.assertIn(statement_input, main_text)
            self.assertLess(
                main_text.index(r"\input{sections/8_references}"),
                main_text.index(statement_input),
            )
            self.assertLess(main_text.index(statement_input), main_text.index(r"\appendix"))

    def test_cumcm_without_no_ai_statement_removes_optional_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            workspace = temp_path / "paper_workspace"
            output = temp_path / "paper_output"
            write_required_paper_workspace(workspace)

            with contextlib.redirect_stdout(io.StringIO()):
                main_path, _ = render_paper.fill_template(
                    "cumcm",
                    workspace,
                    output,
                    prefer_pandoc=False,
                    allow_placeholders=True,
                )

            main_text = main_path.read_text(encoding="utf-8")
            self.assertNotIn("MATHMODEL:OPTIONAL cumcm_no_ai_statement", main_text)
            self.assertNotIn(r"\input{sections/cumcm_no_ai_statement}", main_text)
            self.assertFalse(
                (output / "sections" / "cumcm_no_ai_statement.tex").exists()
            )
            for section in render_paper.SECTION_TO_FILE:
                self.assertIn(rf"\input{{sections/{section}}}", main_text)

    def test_missing_required_workspace_section_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            workspace = temp_path / "paper_workspace"
            write_required_paper_workspace(workspace)
            (workspace / "06_models.md").unlink()

            with self.assertRaisesRegex(FileNotFoundError, "06_models.md"):
                render_paper.fill_template(
                    "mcm", workspace, temp_path / "out", prefer_pandoc=False
                )


class ExtractDiffTests(unittest.TestCase):
    def test_apply_mode_does_not_require_critique(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            artifact = temp_path / "artifact.md"
            patch = temp_path / "patch.txt"
            artifact.write_text(
                "# Paper\n\nIntro.\n\n## Model\n\nOld text.\n", encoding="utf-8"
            )
            patch.write_text(
                "<<< SECTION_PATCH issue_0\n"
                "## Model\n\nNew text.\n"
                ">>>\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "extract_diff.py"),
                    "--artifact",
                    str(artifact),
                    "--mode",
                    "section",
                    "--apply",
                    str(patch),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("## Model\n\nNew text.", result.stdout)
            self.assertNotIn("Old text.", result.stdout)

    def test_unknown_patch_heading_fails(self) -> None:
        artifact = "# Paper\n\nText.\n"
        patch = "<<< SECTION_PATCH issue_0\n## Missing\n\nNew.\n>>>"
        with self.assertRaisesRegex(ValueError, "无法定位"):
            extract_diff.apply_section_patches(artifact, patch)

    def test_duplicate_artifact_heading_fails_as_ambiguous(self) -> None:
        artifact = "## Model\n\nOne.\n\n## Model\n\nTwo.\n"
        patch = "<<< SECTION_PATCH issue_0\n## Model\n\nNew.\n>>>"
        with self.assertRaisesRegex(ValueError, "重复"):
            extract_diff.apply_section_patches(artifact, patch)


class DoctorTests(unittest.TestCase):
    def test_all_three_competition_preflights_pass(self) -> None:
        for competition in doctor.COMPETITIONS:
            with self.subTest(competition=competition):
                checks = doctor.run_checks(competition, check_tools=False)
                failures = [
                    f"{item.name}: {item.detail}"
                    for item in checks
                    if item.status == "fail"
                ]
                self.assertEqual(failures, [])

    def test_mcm_doctor_expects_ai_report_marker(self) -> None:
        checks = doctor.run_checks("mcm", check_tools=False)
        marker_check = next(item for item in checks if item.name == "render-markers")
        self.assertEqual(marker_check.status, "pass")
        self.assertEqual(marker_check.detail, "mcm: 11/11 section markers")

    def test_cumcm_doctor_expects_no_ai_statement_marker(self) -> None:
        checks = doctor.run_checks("cumcm", check_tools=False)
        marker_check = next(item for item in checks if item.name == "render-markers")
        self.assertEqual(marker_check.status, "pass")
        self.assertEqual(marker_check.detail, "cumcm: 11/11 section markers")

    def test_workspace_state_requires_v31_and_matching_competition(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            state_path = workspace / "state" / "decision_log.json"
            state_path.parent.mkdir()
            state = json.loads(
                (ROOT / "templates" / "shared" / "decision_log.json").read_text(
                    encoding="utf-8"
                )
            )
            state["competition"] = "mcm"
            state_path.write_text(json.dumps(state), encoding="utf-8")

            checks = doctor.run_checks(
                "mcm", workspace=workspace, check_tools=False
            )
            workspace_check = next(
                item for item in checks if item.name == "workspace-state"
            )
            self.assertEqual(workspace_check.status, "pass")

            mismatch = doctor.run_checks(
                "cumcm", workspace=workspace, check_tools=False
            )
            mismatch_check = next(
                item for item in mismatch if item.name == "workspace-state"
            )
            self.assertEqual(mismatch_check.status, "fail")

            state["competition"] = "mcm"
            state["current_stage"] = True
            state_path.write_text(json.dumps(state), encoding="utf-8")
            boolean_stage = doctor.run_checks(
                "mcm", workspace=workspace, check_tools=False
            )
            boolean_check = next(
                item for item in boolean_stage if item.name == "workspace-state"
            )
            self.assertEqual(boolean_check.status, "fail")

    def test_require_renderer_and_skip_tools_are_mutually_exclusive(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "doctor.py"),
                "--competition",
                "mcm",
                "--skip-tools",
                "--require-renderer",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("不能与", result.stderr)

    def test_require_renderer_makes_missing_pandoc_a_failure(self) -> None:
        def fake_which(command: str) -> str | None:
            return None if command == "pandoc" else f"/usr/bin/{command}"

        with mock.patch.object(doctor.shutil, "which", side_effect=fake_which):
            checks = doctor.run_checks(
                "mcm", check_tools=True, require_renderer=True
            )

        pandoc_check = next(item for item in checks if item.name == "pandoc")
        self.assertEqual(pandoc_check.status, "fail")
        self.assertIn("formal compilation is unavailable", pandoc_check.detail)

    def test_require_renderer_detects_missing_competition_tex_support(self) -> None:
        with (
            mock.patch.object(doctor.shutil, "which", return_value="/usr/bin/tool"),
            mock.patch.object(doctor, "_tex_file_available", return_value=False),
        ):
            checks = doctor.run_checks(
                "cumcm", check_tools=True, require_renderer=True
            )

        support_check = next(
            item for item in checks if item.name == "latex-support"
        )
        self.assertEqual(support_check.status, "fail")
        self.assertIn("ctexart.cls", support_check.detail)


if __name__ == "__main__":
    unittest.main()

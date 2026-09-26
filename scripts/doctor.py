#!/usr/bin/env python3
"""Preflight checks for the mathmodel-skill package and local toolchain."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
COMPETITIONS = ("cumcm", "mcm", "diangong")
COMPETITION_FILES = (
    "README.md",
    "winning_patterns.md",
    "phrase_bank.md",
    "anti_patterns.md",
    "abstract_template.md",
    "paper_skeleton.md",
    "rubric_overlay.json",
    "topic_specs.json",
    "empirical.json",
    "current_rules.md",
)
RENDER_ENGINES = {"cumcm": "xelatex", "mcm": "pdflatex", "diangong": "xelatex"}
REQUIRED_TEX_FILES = {
    "cumcm": ("ctexart.cls",),
    "mcm": (),
    "diangong": ("ctexart.cls",),
}
MODELING_MODULES = ("numpy", "scipy", "pandas", "matplotlib", "sklearn")
CORE_SECTION_MARKERS = {
    "abstract",
    "1_problem_restate",
    "2_problem_analysis",
    "3_assumptions",
    "4_notation",
    "5_models",
    "6_sensitivity",
    "7_evaluation",
    "8_references",
    "appendix_code",
}
EXPECTED_RENDER_MARKERS = {
    "cumcm": CORE_SECTION_MARKERS | {"cumcm_no_ai_statement"},
    "mcm": CORE_SECTION_MARKERS | {"ai_use_report"},
    "diangong": CORE_SECTION_MARKERS,
}


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str
    fix: str | None = None


def _check(name: str, ok: bool, detail: str, fix: str | None = None) -> Check:
    return Check(name=name, status="pass" if ok else "fail", detail=detail, fix=fix)


def _optional(name: str, ok: bool, detail: str, fix: str | None = None) -> Check:
    return Check(name=name, status="pass" if ok else "warn", detail=detail, fix=fix)


def _load_json(path: Path) -> tuple[bool, object | str]:
    try:
        return True, json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, str(exc)


def _frontmatter_name(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"\A---\s*\n.*?^name:\s*[\"']?([^\n\"']+)", text, re.DOTALL | re.MULTILINE)
    return match.group(1).strip() if match else None


def _anti_pattern_count(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return len(re.findall(r"^###\s+[A-Z]\d+\.\s", text, re.MULTILINE))


def _tex_file_available(filename: str) -> bool:
    """Ask the active TeX distribution whether a required class/package exists."""
    kpsewhich = shutil.which("kpsewhich")
    if not kpsewhich:
        return False
    try:
        result = subprocess.run(
            [kpsewhich, filename], capture_output=True, text=True, check=False
        )
    except OSError:
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def run_checks(
    competition: str,
    workspace: Path | None = None,
    check_tools: bool = True,
    require_renderer: bool = False,
    require_modeling: bool = False,
) -> list[Check]:
    checks: list[Check] = []

    py_ok = sys.version_info >= (3, 10)
    checks.append(_check(
        "python",
        py_ok,
        f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "Install Python 3.10 or newer." if not py_ok else None,
    ))

    required_paths = (
        "SKILL.md",
        "AGENTS.md",
        "agents/openai.yaml",
        ".codex-plugin/plugin.json",
        "config/dim_weights.json",
        "templates/shared/decision_log.json",
        "scripts/score_artifact.py",
        "scripts/extract_diff.py",
        "scripts/render_paper.py",
        "scripts/render_ai_usage.py",
        "scripts/init_workspace.py",
        "scripts/status.py",
        "templates/shared/ai_usage_ledger.json",
        "templates/latex/cumcm/main.tex",
        "templates/latex/mcm/main.tex",
        "templates/latex/diangong/main.tex",
    )
    missing = [item for item in required_paths if not (SKILL_ROOT / item).is_file()]
    checks.append(_check(
        "package-structure",
        not missing,
        "all core entrypoints present" if not missing else f"missing: {', '.join(missing)}",
    ))

    skill_name = _frontmatter_name(SKILL_ROOT / "SKILL.md")
    shim_name = _frontmatter_name(SKILL_ROOT / "skills" / "mathmodel-skill" / "SKILL.md")
    checks.append(_check(
        "skill-metadata",
        skill_name == "mathmodel-skill" and shim_name == "mathmodel-skill",
        f"root={skill_name!r}, plugin-shim={shim_name!r}",
    ))

    json_paths = [
        SKILL_ROOT / ".codex-plugin" / "plugin.json",
        SKILL_ROOT / "config" / "dim_weights.json",
        SKILL_ROOT / "templates" / "shared" / "decision_log.json",
        SKILL_ROOT / "templates" / "shared" / "ai_usage_ledger.json",
    ]
    for comp in COMPETITIONS:
        json_paths.extend((
            SKILL_ROOT / "competitions" / comp / "rubric_overlay.json",
            SKILL_ROOT / "competitions" / comp / "topic_specs.json",
            SKILL_ROOT / "competitions" / comp / "empirical.json",
        ))
    invalid_json = []
    parsed: dict[Path, object] = {}
    for path in json_paths:
        ok, value = _load_json(path)
        if ok:
            parsed[path] = value
        else:
            invalid_json.append(f"{path.relative_to(SKILL_ROOT)}: {value}")
    checks.append(_check(
        "json-config",
        not invalid_json,
        f"{len(json_paths)} files parsed" if not invalid_json else "; ".join(invalid_json),
    ))

    decision_path = SKILL_ROOT / "templates" / "shared" / "decision_log.json"
    decision = parsed.get(decision_path, {})
    decision_schema_ok = (
        isinstance(decision, dict)
        and decision.get("_schema_version") == "3.1"
        and isinstance(decision.get("stages"), dict)
        and isinstance(decision.get("scores"), dict)
        and isinstance(decision.get("iterations"), dict)
        and isinstance(decision.get("compliance"), dict)
        and isinstance(decision.get("compliance", {}).get("ruleset"), dict)
        and "ai_usage" in decision.get("compliance", {})
    )
    checks.append(_check(
        "decision-log-schema",
        decision_schema_ok,
        "decision_log schema 3.1 with compliance state"
        if decision_schema_ok else "decision_log template is not a complete v3.1 state",
        "Restore the v3.1 decision-log template before using the workflow."
        if not decision_schema_ok else None,
    ))

    comp_dir = SKILL_ROOT / "competitions" / competition
    missing_comp = [name for name in COMPETITION_FILES if not (comp_dir / name).is_file()]
    checks.append(_check(
        "competition-pack",
        not missing_comp,
        f"{competition}: {len(COMPETITION_FILES)} required files"
        if not missing_comp else f"{competition} missing: {', '.join(missing_comp)}",
    ))

    anti_path = comp_dir / "anti_patterns.md"
    if anti_path.is_file():
        anti_count = _anti_pattern_count(anti_path)
        checks.append(_check(
            "anti-pattern-index",
            anti_count > 0,
            f"{competition}: {anti_count} indexed checks",
        ))
        declared = (
            decision.get("stages", {}).get("9", {})
            .get("anti_patterns_check", {}).get("total")
            if isinstance(decision, dict) else None
        )
        checks.append(_check(
            "anti-pattern-state-init",
            declared is None,
            f"template defers total; {competition} source currently has {anti_count}",
            "Keep the shared template total null; Stage 9 initializes it from the active competition pack."
            if declared is not None else None,
        ))

    if competition in EXPECTED_RENDER_MARKERS:
        template = SKILL_ROOT / "templates" / "latex" / competition / "main.tex"
        markers = re.findall(
            r"^\s*%\s*MATHMODEL:SECTION\s+([A-Za-z0-9_]+)\s*$",
            template.read_text(encoding="utf-8"),
            re.MULTILINE,
        ) if template.is_file() else []
        expected = EXPECTED_RENDER_MARKERS[competition]
        actual = set(markers)
        duplicates = sorted({marker for marker in markers if markers.count(marker) > 1})
        missing_markers = sorted(expected - actual)
        unexpected_markers = sorted(actual - expected)
        markers_ok = (
            not duplicates
            and not missing_markers
            and not unexpected_markers
            and len(markers) == len(expected)
        )
        if markers_ok:
            marker_detail = f"{competition}: {len(markers)}/{len(expected)} section markers"
        else:
            marker_detail = (
                f"{competition}: missing={missing_markers}, "
                f"unexpected={unexpected_markers}, duplicates={duplicates}"
            )
        checks.append(_check(
            "render-markers",
            markers_ok,
            marker_detail,
            "Restore the exact unique MATHMODEL section-marker set."
            if not markers_ok else None,
        ))

    if workspace:
        decision_path = workspace / "state" / "decision_log.json"
        if decision_path.is_file():
            ok, value = _load_json(decision_path)
            compliance = value.get("compliance") if isinstance(value, dict) else None
            valid = (
                ok and isinstance(value, dict)
                and value.get("_schema_version") == "3.1"
                and value.get("competition") == competition
                and isinstance(value.get("current_stage"), int)
                and not isinstance(value.get("current_stage"), bool)
                and 0 <= value["current_stage"] <= 9
                and isinstance(value.get("stages"), dict)
                and isinstance(value.get("scores"), dict)
                and isinstance(value.get("iterations"), dict)
                and isinstance(compliance, dict)
                and isinstance(compliance.get("ruleset"), dict)
                and "ai_usage" in compliance
            )
            checks.append(_check(
                "workspace-state",
                valid,
                str(decision_path) if valid else f"invalid state: {value}",
            ))
        else:
            checks.append(_optional(
                "workspace-state",
                False,
                f"not initialized: {decision_path}",
                "Run scripts/init_workspace.py, or start the skill once and let the agent initialize state.",
            ))

    if check_tools:
        engine = RENDER_ENGINES[competition]
        engine_ok = shutil.which(engine) is not None
        engine_check = _check if require_renderer else _optional
        checks.append(engine_check(
            "latex-engine",
            engine_ok,
            f"{engine} {'found' if engine_ok else 'not found'}",
            f"Install a TeX distribution that provides {engine}." if not engine_ok else None,
        ))
        required_tex_files = REQUIRED_TEX_FILES[competition]
        if required_tex_files:
            missing_tex_files = [
                filename for filename in required_tex_files
                if not _tex_file_available(filename)
            ]
            checks.append(engine_check(
                "latex-support",
                not missing_tex_files,
                "required TeX classes/packages found" if not missing_tex_files
                else f"missing TeX support: {', '.join(missing_tex_files)}",
                "Install the TeX distribution's Chinese-language/ctex package set."
                if missing_tex_files else None,
            ))
        pandoc_ok = shutil.which("pandoc") is not None
        pandoc_check = _check if require_renderer else _optional
        checks.append(pandoc_check(
            "pandoc",
            pandoc_ok,
            "pandoc found" if pandoc_ok else (
                "pandoc not found; formal compilation is unavailable "
                "(structural --no-compile remains available)"
            ),
            "Install Pandoc before formal paper compilation."
            if not pandoc_ok else None,
        ))

    if require_modeling:
        missing_modules = [name for name in MODELING_MODULES if importlib.util.find_spec(name) is None]
        checks.append(_check(
            "modeling-stack",
            not missing_modules,
            "core modeling modules found" if not missing_modules else f"missing: {', '.join(missing_modules)}",
            "Install templates/shared/requirements.txt." if missing_modules else None,
        ))

    return checks


def _print_human(checks: list[Check]) -> None:
    symbols = {"pass": "✓", "warn": "!", "fail": "✗"}
    for item in checks:
        print(f"{symbols[item.status]} {item.name}: {item.detail}")
        if item.fix and item.status != "pass":
            print(f"  ↳ {item.fix}")
    counts = {status: sum(item.status == status for item in checks) for status in symbols}
    print(
        f"\nSummary: {counts['pass']} passed, "
        f"{counts['warn']} optional warnings, {counts['fail']} failed"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check mathmodel-skill readiness.")
    parser.add_argument("--competition", choices=COMPETITIONS, default="cumcm")
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--skip-tools", action="store_true", help="skip local Pandoc/TeX checks")
    parser.add_argument("--require-renderer", action="store_true")
    parser.add_argument("--require-modeling", action="store_true")
    args = parser.parse_args()

    if args.skip_tools and args.require_renderer:
        parser.error("--require-renderer 不能与 --skip-tools 同时使用")

    checks = run_checks(
        competition=args.competition,
        workspace=args.workspace.resolve() if args.workspace else None,
        check_tools=not args.skip_tools,
        require_renderer=args.require_renderer,
        require_modeling=args.require_modeling,
    )
    if args.as_json:
        print(json.dumps([asdict(item) for item in checks], ensure_ascii=False, indent=2))
    else:
        _print_human(checks)
    return 1 if any(item.status == "fail" for item in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())

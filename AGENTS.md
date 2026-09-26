# Repository instructions

This repository contains the `mathmodel-skill` product. When working inside this repository, act as a maintainer: do not start the ten-stage contest workflow merely because modeling-related files are present.

## Sources of truth

- `SKILL.md` defines runtime behavior and trigger boundaries.
- `references/stage_00_kickoff.md` through `references/stage_09_review.md` contain stage details and must be loaded lazily at runtime.
- `competitions/<competition>/` contains competition-specific rules, heuristics, overlays, and paper structures.
- `templates/shared/decision_log.json` is the canonical persistent-state template.
- `.codex-plugin/plugin.json`, `agents/openai.yaml`, and `skills/mathmodel-skill/SKILL.md` are packaging metadata or thin discovery shims. Do not duplicate the workflow into them.

## Maintenance rules

- Preserve the trigger boundary: this skill is for CUMCM, MCM/ICM, and Diangong Cup contest work, not generic data analysis or ordinary paper review.
- Treat official contest rules as time-sensitive. Keep a verification date and primary source in `competitions/<competition>/current_rules.md`; official current-year material always overrides repository guidance.
- Treat empirical distributions and `winning_patterns.md` as observations or maintainer heuristics, never official thresholds or award predictors.
- Keep user artifacts relative to the user's working directory (`state/`, `results/`, `figures/`, `paper_workspace/`, `paper_output/`). Resolve repository resources relative to the installed skill root.
- Keep `SKILL.md` concise and dispatch stage-specific detail into `references/`.
- Do not add runtime claims about awards, token savings, or elapsed time without a reproducible benchmark.
- When changing behavior, update the README, tests, plugin version, state schema, and relevant competition docs together.
- README visuals in `assets/` are original SVGs. Keep their version, stage names, and example data consistent with `SKILL.md` and `scripts/status.py` when those change.
- Do not vendor or reintroduce templates, examples, papers, or binary assets without a clear redistribution license. Keep runtime dependencies and external-source boundaries accurate in `THIRD_PARTY_NOTICES.md`.

## Verification

Run the checks proportionate to the change. Before a release, run all of them:

```bash
python -m compileall -q scripts templates/shared/code_starter
python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/doctor.py --competition cumcm --skip-tools
python scripts/doctor.py --competition mcm --skip-tools
python scripts/doctor.py --competition diangong --skip-tools
git diff --check
```

Maintainers with the Codex skill/plugin creator tooling installed should also run its current `quick_validate.py` and `validate_plugin.py` entrypoints. Do not hard-code a machine-specific installation path into contributor commands.

Runtime evaluation prompts should explicitly invoke `$mathmodel-skill`. Negative-trigger tests should confirm that generic model-selection and non-competition writing requests do not invoke it.

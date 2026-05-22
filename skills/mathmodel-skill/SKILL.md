---
name: mathmodel-skill
description: Plugin shim for mathmodel-skill. Use when Codex invokes the math modeling plugin for CUMCM, MCM/ICM, Diangong Cup, 建模, 数模, 竞赛论文, model selection, robustness analysis, paper writing, or final review.
---

# mathmodel-skill plugin shim

This wrapper exists so Codex plugins can discover the skill from the official `./skills/` plugin layout.

Before doing any work, read `../../SKILL.md` and treat it as the primary workflow. Resolve `references/`, `competitions/`, `templates/`, `scripts/`, and `config/` relative to `../..`.

Do not duplicate workflow rules here; the root `SKILL.md` is the source of truth.

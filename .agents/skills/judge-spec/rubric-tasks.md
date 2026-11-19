---
title: rubric-tasks — quality dimensions for tasks artifacts (bidirectional traceability)
updated: 2026-11-17
related:
  - ./SKILL.md
---

# Rubric — `tasks`

> [!info] When to load
> Load to gate `breakdown-tasks` output (`tasks.md`). Verifies bidirectional traceability, atomic sizing, and zero-question agent startability.

## Quality dimensions

| # | Dimension | Pass criterion | Block on fail? |
|---|---|---|---|
| 1 | **AC coverage (no orphan ACs)** | EVERY acceptance criterion of the specification is served by >= 1 task (tagged `-> AC-n`) | Yes |
| 2 | **No orphan tasks** | EVERY task traces back to an AC, an NFR, or the standard tail (`close-spec`) | Yes |
| 3 | **Verify lifted from plan §5** | Each task's `Verify:` clause comes from `plan.md` §5 / `test-plan.md` — never invented | Yes |
| 4 | **Verify observable** | Each `Verify:` is a concrete observable check — never "it works" / "looks good" | Yes |
| 5 | **NFR coverage** | Every `plan.md` §5 NFR is served by a task | Yes |
| 6 | **Atomic & single-repo** | Each task fits one commit / turn (<= ~300 changed lines, <= ~5 files), spans one repo, and carries its `repo` tag | Yes |
| 7 | **Runtime & impact markers present** | Each task is tagged with impact (`accion` / `analisis` / `verificacion`) and runtime (`[I]` / `[A]` / `[*]`) | No — flag |
| 8 | **Grouped & ordered by repo** | Tasks grouped by `repo` in a single `tasks.md` and ordered by dependency within each repo | No — flag |
| 9 | **Standard tail present** | Final task runs `close-spec` | No — flag |
| 10 | **Traceability table** | Explicit `AC / NFR -> Tareas` matrix is present | No — flag |
| 11 | **Agent-startable (self-contained)** | Each active task points to its `plan.md` §3 change + companion section + observable `Verify:` so an agent starts with zero further questions; blocked items are quarantined under `## Bloqueadas` | Yes |
| 12 | **Each step integrates (no orphan code)** | No task leaves unwired dead code; `after: T0x` dependencies are explicit where ordering matters | No — flag |

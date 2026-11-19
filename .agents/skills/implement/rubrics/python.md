---
title: implement juez rubric — Python stack
updated: 2026-11-17
related:
  - ../SKILL.md
---

# Juez rubric — `python`

> [!info] When to load
> Load during `implement` (or a Lightweight-lane change) to score a **Python** code diff before committing and checking off a task.

## Quality dimensions

| # | Dimension | Pass criterion | Block on fail? |
|---|---|---|---|
| 1 | **Test exists & is observable** | The task's Verify is a real test (`pytest` / `unittest`) with concrete inputs + expected output; it **fails before** the change and **passes after** | Yes |
| 2 | **Test + lint/typecheck green** | The task's test and the repo's lint/typecheck pass locally — cite exact command and result | Yes |
| 3 | **Minimal diff & Zero Duplication** | Only the code needed for the task; reuses existing repository/shared utilities instead of duplicating helpers; no speculative abstraction or unrelated edits | Yes |
| 4 | **Matches repo conventions** | Follows the repository's module structure (`AGENTS.md`, hexagonal/DDD layers, or configured context) and cited golden-example | Yes |
| 5 | **Type hints & signature** | Public functions carry PEP 484 type hints; signature matches the plan companion field-for-field (zero invention) | Yes |
| 6 | **Pure / testable where claimed** | Pure functions have no hidden I/O, global state, or clock coupling; dependencies are injectable | Yes — if applicable |
| 7 | **Error handling scoped** | Edge/error cases from the task are handled; no bare `except:`, no swallowed exceptions, and no silent default fallbacks masking bugs | Yes — if applicable |
| 8 | **No secrets / no PII leak** | No hardcoded secrets/tokens; no PII in logs; boundary input validated | Yes — if applicable |
| 9 | **No drive-by or test weakening** | No unrelated reformatting/renaming; no weakened, skipped, or deleted existing tests | Yes |
| 10 | **Traceability** | Commit message references the task ID (`T0x`) and diff maps to `plan.md` §3 | No — flag |

## Verdict

- **APROBADO** = all `"Block on fail? Yes"` dimensions met -> commit + mark `[x]`.
- **RECHAZADO** = any blocking dimension unmet -> iterate with concrete fixes (circuit breaker stops after 2 failed attempts).

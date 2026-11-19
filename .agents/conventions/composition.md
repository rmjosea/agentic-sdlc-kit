---
title: Composition — valid skill chains, recovery loops, and routing
updated: 2026-11-17
related:
  - ./conventions.md
  - ./how-to-invoke-skills.md
  - ./loading-recipes.md
  - ./change-lanes.md
---

# Composition

> [!info] When to load
> Load when chaining skills end-to-end (`drill-docs -> save-output -> judge-spec -> plan-feature -> breakdown-tasks -> implement -> close-spec`) or recovering from a blocked iteration. Prerequisites: `AGENTS.md`.

## Two layers, one pipeline

Skills split into two pipelines that meet at `judge-spec -> plan-feature`:

| Pipeline | Skills | Output |
|---|---|---|
| **Definition** (the WHAT) | `drill-docs -> save-output -> judge-spec` (loop) | An approved artifact (`user-journey`, `user-story`, `spec`, `adr`, `decision`, `business-context`) |
| **Implementation** (the HOW) | `plan-feature -> breakdown-tasks -> implement -> close-spec` | Implemented + validated change(s) in the target code repo(s) |

**Skills are independent.** Invoke any skill on its own and **stop when you have what you need**. No skill automatically invokes the next one without user confirmation.

## Canonical chain (Spec lane — M / L / XL)

```text
unstructured input
    │
    ▼
drill-docs (extract structure in chat — no file written yet)
    │
    ▼
save-output (write artifact + Shape A frontmatter to disk; split if >~3000 tokens)
    │
    ▼
judge-spec <────────────┐
    │                   │ status: needs-work
    │                   │ user answers clarifying Qs (1 blocker at a time)
    │                   │ judge applies surgical edits
    ▼ status: approved  │
    ├───────────────────┘ (max 5 iterations before escalating)
    │
    ▼
plan-feature (Explore -> Interrogate -> Plan -> Verify; records target_repos + zero-invention companions)
    │
    ▼
breakdown-tasks (atomic 'Do X -> Verify Y' tasks grouped by repo in a single tasks.md)
    │
    ▼
implement <─────────────┐  per repo, cold-start per task
    │                   │  task fails test/lint/juez -> iterate (max 2 attempts, then stop)
    │ all tasks [x]     │  feature-level juez / AC gate fails -> reopen offending tasks
    ▼ verdict APROBADO  │
    ├───────────────────┘
    │  (all tasks [x] — the implicit APROBADO signal)
    ▼
close-spec (notary: verify tasks [x] + plan coverage + sync check -> status: implemented + handoff record)
```

## How to know which skill is next

Read the specification's frontmatter `status` and inspect which files exist in `features/{NNN}-{slug}/`:

| Spec status | Other signal | Next skill |
|---|---|---|
| *(no file yet, unstructured idea)* | — | `drill-docs` -> `save-output` |
| *(no file yet, structured draft ready)* | — | `save-output` |
| `draft` / `review` / `needs-work` / `legacy-pending-review` | — | `judge-spec` (loop) |
| `approved` | no `plan.md` yet | `plan-feature` |
| `approved` | `plan.md` exists + human reviewed, no `tasks.md` | `breakdown-tasks` |
| `approved` | `tasks.md` exists, not all tasks `[x]` | `implement` (per repo) |
| `approved` | `tasks.md` all `[x]` + implementation merged | `close-spec` |
| `implemented` | — | done — specification sealed |

## Recovery paths

- **`judge-spec` returns `needs-work` repeatedly** -> stop after 5 iterations and escalate to a human reviewer.
- **Specification needs substantial rework during `plan-feature` or `implement`** -> flip specification status back to `needs-work` and re-run `judge-spec` before continuing.
- **A task fails twice in `implement`** -> circuit breaker triggers: stop without committing or marking `[x]`, emit a structured diagnosis (code, test, task, or plan gap), and resume from a clean context.
- **Feature-level AC gate fails in `implement`** -> reopen the offending task(s) in `tasks.md` and return to the per-task loop.

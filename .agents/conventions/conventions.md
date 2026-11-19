---
title: Project conventions — index and artifact rules
updated: 2026-11-17
related:
  - ./naming-and-language.md
  - ./progressive-disclosure.md
  - ./context-cleanup.md
  - ./frontmatter-schema.md
  - ./output-splitting.md
  - ./change-lanes.md
---

# Conventions

> [!info] When to load
> Load when generating or editing any artifact, file, or content. Prerequisites: `AGENTS.md`. Next level: the specific convention file from the table below.

## Convention files (load on demand)

| File | When to load |
|---|---|
| `naming-and-language.md` | Before creating files, folders, or writing prose |
| `progressive-disclosure.md` | Before structuring any multi-file or long document |
| `context-cleanup.md` | After running any skill that loaded significant context |
| `frontmatter-schema.md` | Before creating any artifact or `SKILL.md` |
| `output-splitting.md` | Before saving any generated artifact larger than ~2000 tokens |
| `change-lanes.md` | When sizing a change (XS–XL) or choosing Lightweight vs Spec lane |
| `loading-recipes.md` | When starting a skill and selecting the minimum context to load |
| `runtimes.md` | When tagging tasks (`[I]` / `[A]` / `[*]`) or selecting clean-context execution |
| `composition.md` | When chaining skills or recovering from a blocked iteration |
| `security.md` | Before reading untrusted external content or performing external writes |
| `how-to-invoke-skills.md` | When guiding a human on how to invoke or compose skills |
| `skill-schema.md` | When authoring, reviewing, or calibrating a `SKILL.md` |

## Document language (two tiers)

The kit applies a **two-tier language policy** (full detail in `naming-and-language.md`):

- **Harness infrastructure** (`AGENTS.md`, `.agents/**`, `scripts/**`, root `README.md`) -> **English**.
- **Business artifacts** (`features/`, `journeys/`, `personas/`, `business-context/`, `architecture/adr/`, `estimaciones/`) -> **Project business language** (Spanish by default, or as configured in `.agents/project.json`).
- **Operational chats** (PR comments, conversation between human and agent) -> Speaker's choice.

YAML frontmatter keys and reserved string values (`type`, `status`) are **always English**, regardless of the artifact's content tier.

## Artifact categories

All project artifacts fall into one of three **sibling** categories (see `frontmatter-schema.md` Shape A type vocabulary):

| Category | Purpose | Types |
|---|---|---|
| **definition** (the WHAT) | Parallel ways to define what to build. Pick the form that fits the abstraction level. | `user-persona`, `user-journey`, `user-story`, `spec`, `adr`, `decision`, `business-context` |
| **implementation** (the HOW) | Materialize how to build a definition. Co-located in `features/{NNN}-{slug}/`. | `plan`, `tasks` |
| **estimation** (the HOW MUCH) | Effort and sprints of a journey or feature, produced by `estimate-effort` and kept apart in `estimaciones/`. | `estimate` |

## Specification (format-agnostic, Delta model)

**Executable code and passing tests in the base branch are the single source of truth for current system behavior.** Never read old, sealed specifications to infer how production currently works; inspect the live codebase (accelerated by any configured domain context or `vault/` index).

A **specification** is any approved `definition` artifact that carries **testable acceptance criteria** — a `user-journey`, a `user-story`, or a `spec`. It acts as a **Delta contract** for the current change (defining what must be added or modified relative to current code). The three are **interchangeable formats** of the same intent at different abstraction levels; none is a prerequisite of another.

The **implementation** skills operate on the specification regardless of its format:

- `plan-feature` plans from any approved specification (`user-journey` / `user-story` / `spec`), contrasts against the live codebase, and records `target_repos`.
- `breakdown-tasks` breaks down the resulting plan into atomic tasks tagged by `repo`.
- `implement` executes the tasks repo by repo in clean context (on standard Git branches by default; `git worktree` is optional only when running concurrent autonomous agents on the same repository checkout) and owns validation (task + feature juez + 3-ring verification).
- `close-spec` seals whichever specification drove the work (`status: implemented`), leaving the committed tests in the repository as the permanent regression guard.

The universal gate that makes a specification plannable is **testable ACs**. The implementation bundle (`plan.md`, companions, `tasks.md`, `implementation-report.md`) lives co-located in `features/{NNN}-{slug}/` and references its source specification via the plan's `spec:` frontmatter field.

## Plan with supporting files (Zero-Invention Companions)

A plan MAY be a **single file** (`plan.md`) or carry **co-located companion files** in `features/{NNN}-{slug}/` (or under `plan/` when split). **Two independent decisions** govern this:

- **Create a companion — invention-driven.** Whenever the change **introduces a new interface** (a persisted structure, an API endpoint, an event/message, or any externally visible contract), define it field-by-field in the matching companion — **regardless of plan size**.
- **Split into a `plan/` folder — size-driven.** Only when the plan crosses the `output-splitting.md` threshold (**>=3 genuinely independent concerns OR >~3000 tokens**). Below it, keep `plan.md` + companions flat in `features/{NNN}-{slug}/`.

**Zero-invention bar.** Every NEW interface the plan introduces MUST be defined at **field level** — names, types, enums, defaults, required/optional, error cases — so the downstream coding agent invents **nothing**. Any field that genuinely cannot be pinned is marked `[NEEDS CLARIFICATION]` **with an owner**, never silently assumed.

**Standard companion files** (co-located next to `plan.md`):

| File | Purpose |
|---|---|
| `data-model.md` | Each new/changed persisted structure: field, type, required, default, classification (PII?), retention, invariants. |
| `api.md` (or `contracts/`) | Each new/changed endpoint: method, path, auth, request, response, error cases. |
| `event.md` | Each new/changed event or message: transport, name, payload fields, fan-out, idempotency, PII. |
| `test-plan.md` | Each AC + NFR as Given/When/Then with concrete **inputs + expected output**, mapped to the repo's real test stack. Consumed by `implement` for validation. |

Create only the companions the change actually needs — never create an empty companion.

## Slug and path conventions for artifacts

| Category | Type | Default path pattern |
|---|---|---|
| definition | `user-persona` | `personas/{kebab-slug}.md` |
| definition | `user-journey` | `journeys/{feature}/{ID-prefix}-{NN}-{kebab-slug}.md` (single) or `.../{kebab-slug}/00-overview.md` (split) |
| definition | `user-story` | `features/{NNN}-{feature-slug}/stories/US-{N}-{kebab-slug}.md` |
| definition | `spec` | `features/{NNN}-{feature-slug}/spec.md` (single) or `.../spec/00-overview.md` (split) |
| definition | `business-context` | `business-context/{kebab-slug}.md` |
| definition | `adr` | `architecture/adr/adr-{NNNN}-{kebab-slug}.md` |
| definition | `decision` | `features/{NNN}-{feature-slug}/decisions.md` (appended) |
| implementation | `plan` | `features/{NNN}-{feature-slug}/plan.md` (single) or `.../plan/00-overview.md` (split) |
| implementation | `tasks` | `features/{NNN}-{feature-slug}/tasks.md` |
| estimation | `estimate` | `estimaciones/{slug}/estimacion.md` (+ optional `presentacion.html`) |

## Reserved status vocabulary

The `status` frontmatter field in Shape A uses a closed vocabulary:

```text
draft | review | needs-work | approved | implemented | archived | superseded | legacy-pending-review
```

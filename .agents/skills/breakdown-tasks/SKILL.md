---
name: breakdown-tasks
description: Use when a reviewed plan.md must become tasks.md containing atomic 'Do X -> Verify Y' tasks numbered T01..Tn, tagged and grouped by target repo, with impact class (accion/analisis/verificacion), runtime modality ([I]/[A]/[*]), and source pointers to plan §3 and companions so a coding agent starts with zero questions. Do NOT use if the plan is unreviewed or if tasks.md already exists (use implement).
---

# breakdown-tasks

Decompose a human-reviewed technical plan into a single, repo-grouped `tasks.md` where every task is atomic, traceable, and immediately executable with zero further decisions.

## When to use

- A `plan.md` exists in `features/{NNN}-{slug}/`, passes `rubric-plan`, has been reviewed by the human, and its parent specification is `approved`.
- A reviewed plan changed materially and its task list must be regenerated.

## When NOT to use

- The plan has not been reviewed by a human yet -> review `plan.md` first.
- `tasks.md` already exists and is ready for execution -> use `implement`.

## Resolve configured roots

Before writing, inspect `.agents/project.md`; if it exists, report it as unsupported and stop. If `.agents/project.json` exists, validate it with `.agents/skills/setup/assets/project.schema.json` and apply `.agents/skills/setup/references/project-config.md`; stop on any invalid config. Write `tasks.md` alongside `plan.md` in `features/{NNN}-{slug}/`.

## Inputs

- Path to the reviewed `features/{NNN}-{slug}/plan.md` (and its co-located companions `data-model.md`, `api.md`, `event.md`, `test-plan.md`).

## Outputs

- `features/{NNN}-{slug}/tasks.md` using [assets/tasks.template.md](assets/tasks.template.md) — **a single file**, tasks grouped by `repo` (no per-repo duplication -> no drift).
- Shape A frontmatter (`type: tasks`, `status: draft`, `updated: YYYY-MM-DD`, `spec: ./spec.md`, `target_repos: [...]`).
- Numbered tasks `T01`, `T02`, ... each carrying:
  - **Do** clause (concrete, atomic, single-repo action that integrates cleanly)
  - `repo` tag (from `target_repos`)
  - **Impact class**: `accion` (writes/changes code) · `analisis` (investigation only) · `verificacion` (test/validation)
  - **Runtime marker**: `[A]` (autonomous/mechanical) · `[I]` (interactive/UX/a11y) · `[*]` (either), per `.agents/conventions/runtimes.md`
  - `-> AC-n` traceability tag
  - **Verify:** observable check lifted directly from `plan.md` §5 / `test-plan.md` (never invented)
  - **Source:** pointer to `plan.md` §3 + exact companion section (`api.md` §..., `data-model.md` §..., `event.md` §...)

## Process — Gate -> Derive -> Tag & Classify -> Order -> Write & Validate

### 1. Gate and read the plan

1. Confirm the parent specification is `approved`, the plan satisfies `.agents/skills/judge-spec/rubric-plan.md`, and the human has reviewed the plan.
2. Read `plan.md`, `target_repos`, §3 Changes per repo, §5 Verification, and all co-located companions.

### 2. Derive atomic, self-contained tasks

3. Turn each §3 change into the smallest task completable in one commit or agent turn (**size ceiling: <= ~300 changed lines across <= ~5 files**). Split any task that crosses two repositories. Every step must wire into the feature (no orphaned dead code).
4. Point each task to its exact **Source** (`plan §3` + companion section) so the coding agent makes **zero decisions**. If a detail is blocked on an open question, quarantine the task under `## Bloqueadas` with its question and `@owner`.
5. Lift each task's **Verify** clause directly from `plan.md` §5 / `test-plan.md` (named test + concrete inputs/expected output). If a change lacks a §5 entry, flag the plan gap rather than inventing a check.

### 3. Tag repo, classify impact, mark runtime, and order for parallel Front/Back work

6. Tag each task with its `repo`, impact class (`accion` | `analisis` | `verificacion`), runtime marker (`[A]` | `[I]` | `[*]`), and `-> AC-n`.
7. Group tasks by `### {repo}` and order by dependency within each repo (model/schema -> domain/service -> controller/route -> event -> tests). Because cross-repo contracts (`api.md`, `event.md`) are already pinned field-by-field in `plan-feature`, Backend and Frontend repo groups can be executed **in parallel** (e.g., via `implement --repo <repo>`) without waiting on each other; only the final cross-repo integration / E2E verification task carries `after:` dependencies across both repos, followed by the standard tail (`close-spec`). When a feature changes user-visible flows or crosses repos (M/L/XL), include an explicit Feature E2E `verificacion` task (and full-app E2E regression gate when L/XL or shared-surface) lifted from `test-plan.md`.

### 4. Write and validate against `rubric-tasks`

8. Write `features/{NNN}-{slug}/tasks.md` using [assets/tasks.template.md](assets/tasks.template.md), including the bidirectional `## Trazabilidad (AC / NFR -> tarea)` table and `## Dependencias` graph.
9. Verify against `.agents/skills/judge-spec/rubric-tasks.md` (every AC -> >=1 task; every task -> AC/NFR/tail + Source + observable Verify). Recommend `implement` as the next step.

## Anti-patterns

- Vague verify clauses ("funciona", "se ve bien") or invented checks absent from `plan.md` §5.
- Tasks spanning multiple repositories or exceeding ~300 lines / ~5 files.
- Duplicating task text into separate per-repo files (if an autonomous runner needs a repo index, emit only a link pointer to the canonical `tasks.md`).
- Leaving architectural or contract decisions for the task to resolve.

## References

- [assets/tasks.template.md](assets/tasks.template.md)
- `.agents/conventions/runtimes.md`
- `.agents/skills/judge-spec/rubric-tasks.md`

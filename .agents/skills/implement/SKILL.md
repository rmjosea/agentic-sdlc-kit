---
name: implement
description: Use when building a change from a reviewed tasks.md or a confirmed Lightweight-lane (XS/S) request: runs repo by repo, one task per clean context, writes the failing test first, implements minimal code until test + lint/build pass, audits the test diff, runs the per-stack juez rubric (APROBADO -> commit + check off [x]), and enforces the feature-level regression + AC gate. Do NOT use on an unapproved spec or to seal a finished spec (use close-spec).
---

# implement

Execute one bounded task or Lightweight-lane change at a time in a clean context. `implement` **owns validation** at both the task level (test-first + per-stack juez rubric) and the feature level (full regression + AC gate).

## Select and bound

1. Read `AGENTS.md`, the selected `features/{NNN}-{slug}/tasks.md`, `plan.md`, and co-located companions (`data-model.md`, `api.md`, `event.md`, `test-plan.md`), or confirm Lightweight-lane conditions (`.agents/conventions/change-lanes.md` XS/S) and state `Intent`, `Change`, and `Verification` inline.
2. **Select scope and execution mode (Interactive vs. Clean-Context Loop `.sh`):**
   - Support filtering `tasks.md` by repository (`--repo <repo-id>`), by specific task IDs (`--tasks T01,T02`), or by autonomous modality (`--only-autonomous`, running `[A]`/`[*]` tasks and pausing before `[I]` tasks).
   - When multiple unchecked `[ ]` tasks are in scope and execution mode was not specified, ask the user once (per `AGENTS.md` human decision protocol) whether to **(A — Recommended for `[A]`/`[*]` batches)** run via the clean-context loop script (`.sh`, one fresh session per task) or **(B)** execute the next ready task interactively in the current session.
   - Within a repository, execute tasks **sequentially** on a standard Git branch (`git-conventions`); `git worktree` is optional and needed only when running concurrent autonomous agents on the same local checkout. Across independent repositories, groups may run in parallel because contracts are pinned in `api.md` / `event.md`.
3. Respect the review queue and WIP capacity (maximum one active task per context when unconfigured). Do not start blocked tasks (`## Bloqueadas`).
4. Load the target repository's `AGENTS.md` (or configured domain context / `vault/` of any layout + cited golden-example file in the live codebase) and the matching stack juez rubric from `rubrics/`:
   - [rubrics/python.md](rubrics/python.md)
   - [rubrics/node-ts.md](rubrics/node-ts.md)
   - [rubrics/java.md](rubrics/java.md)
   - [rubrics/frontend.md](rubrics/frontend.md)
   When the `evidence` module is active under `AGENTS.md`, load its `MODULE.md` and update its existing or warranted lazy record from directly observed work. When `multi-repo` is installed and enabled in the recognized configuration, load its `MODULE.md` before working in the assigned Repository ID.
5. Restate or link the concise change contract: what, authoritative why, scope, evidence, risk, agent roles, and review focus. Stop immediately on material ambiguity; never invent product or architecture decisions in code.

## Resolve the work root

Resolve locations when inspecting a plan, task graph, or writing a handoff or `implementation-report.md`. Reject any `.agents/project.md` as unsupported before writing. If `.agents/project.json` is absent, use `features/{NNN}-{slug}/` (or `.work/` fallback for standalone graphs). If `.agents/project.json` exists, validate it with `.agents/skills/setup/assets/project.schema.json` and apply `.agents/skills/setup/references/project-config.md`. Stop on any invalid config rather than guessing. Use recognized `roots.work` as `<work-root>/` when configured.

## Per-task gen-eval loop (Cold start)

Exploration is read-only. Implementation mutates only the assigned outcome. Validation is non-mutating and fresh by default. For each unchecked task:

1. **Read the task**: its `Do` clause, the `plan.md` §3 change, the exact companion section (`api.md`, `data-model.md`, `event.md`), and its `Verify` clause (`test-plan.md` / `plan.md` §5).
2. **Test first (red)**: write or locate the test specified by `Verify` with concrete inputs and expected output in the repo's real test stack. Confirm it **fails first** to prove it exercises the new behavior. Read [references/testing.md](references/testing.md) when selecting test seams.
3. **Implement (minimal diff & Zero Duplication)**: write the minimum code to make the test pass, reusing existing repository utilities and UI design-system components cited in `plan.md` and matching the cited golden-example. Never duplicate existing helpers or swallow errors with empty catches/silent defaults.
4. **Run test + lint/build (green)**: execute the task's test and the repo's linter/typecheck/build in short feedback loops (0 new errors relative to baseline). Read [references/debugging.md](references/debugging.md) when a failure is non-obvious.
5. **Audit the diff and run the Juez rubric**:
   - Inspect the real `git diff`, then make a **separate pass over test changes only** (`git diff -- <test paths>`): any deleted, skipped, or weakened assertion, or mocking of the unit under test, is an automatic **RECHAZADO**.
   - Score the diff against the active stack's rubric (`rubrics/{stack}.md`).
   - **APROBADO** -> commit following `.agents/skills/git-conventions/SKILL.md` (referencing the task ID `T0x`), flip the task checkbox to `[x]` in `tasks.md` (or record exact `Result` and mark `done`), and move to the next task in a clean context.
   - **RECHAZADO** -> iterate with concrete file:line failure evidence; never check off a failed or rejected task.

### Circuit breaker (Attempt cap = 2)

One attempt is one `implement -> run -> juez` cycle. After the **2nd failed attempt** on a task (red test/lint/build or `RECHAZADO` verdict), **STOP**: do not commit, do not mark `[x]`, leave the diff uncommitted, and report a structured 5-line failure diagnosis (command run, exit code, exact `file:line`, expected vs observed, root cause in code/test/task/plan). Resume only from a **fresh clean context**.

### Spec and plan sync first

When implementation reality forces a divergence from `plan.md` or a companion (field, contract, or behaviour), stop and update `plan.md` / the companion first — or return the specification to `judge-spec` if an AC or observable behaviour changes — get human confirmation, and only then update the code.

## Feature gate (3-Ring Verification) and close

When every task in `tasks.md` is `[x]` (or `done`):

1. **Ring 1 & 2 (Repo Regression + Feature E2E):** Run the **full repository regression suite** for each target repo and the feature's focused **E2E check** (e.g., Playwright / live API harness over `data-testid` selectors) when applicable.
2. **Ring 3 (Full-App E2E Regression Gate for L/XL or shared surfaces):** When the feature is tier `L`/`XL` or modifies shared cross-cutting flows (auth, navigation, core search/checkout/apply, shared UI library), require the application-wide E2E regression suite to pass before closure.
3. **AC gate**: verify that every specification AC maps to passing observed evidence from `test-plan.md`. If any AC lacks passing evidence, **reopen** the offending task(s) in `tasks.md` and return to the per-task loop.
4. Run the **feature-level juez** over the combined diff and write the verdict + AC->evidence map to `features/{NNN}-{slug}/implementation-report.md` (or `<work-root>/<feature>/handoff.md` using [assets/handoff.template.md](assets/handoff.template.md) if stopping mid-flight).
5. Recommend `close-spec` (notary) to seal the specification (`status: implemented`), leaving the committed tests as the permanent source of truth in the codebase.

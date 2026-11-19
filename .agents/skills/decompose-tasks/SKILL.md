---
name: decompose-tasks
description: Convert an approved technical plan into an atomic, traceable dependency graph of implementation tasks, classifying task purpose, risk, execution order, conflicts, safe parallelism, and bounded agent execution. Use when a confirmed plan must be broken down, scheduled, prepared for multiple agents, or made ready for incremental implementation. Do not redesign the approved solution or implement code.
---

# Decompose an Approved Plan

Turn a confirmed design into the smallest useful executable task graph. Do not
modify production code or reopen settled technical decisions.

## Preconditions

1. Read `AGENTS.md`, the approved plan, its source intent, and only the
   contracts needed to understand delivery boundaries.
2. Require the plan status to be `approved` with no material open technical
   decision.
3. Return upstream to `plan` if decomposition exposes a missing or contradictory
   design; return to the source owner for contradictory or changed accepted
   behavior.
4. Trace to the plan and authoritative source. Do not copy or invent their
   rationale, and do not reinterpret repository evidence as intent.

## Resolve the work root

Resolve work locations only when finding the approved plan or writing its task
graph. Reject any `.agents/project.md` as unsupported before writing. If
`.agents/project.json` is absent, use `.work/`. If it exists, validate it with
`.agents/skills/setup/assets/project.schema.json` and apply
`.agents/skills/setup/references/project-config.md`. Stop on any invalid config
rather than guessing or falling back. Use recognized `roots.work` as
`<work-root>`.

## Build the graph

1. Map each non-trivial source item to one or more observable delivery outcomes.
2. Create vertical tasks that each produce one coherent, verifiable result.
3. Add enabling work only when a delivery task cannot safely absorb it.
4. Identify dependencies from contracts, data flow, migrations, shared state,
   and required validation—not from an assumed coding order.
5. Identify change-surface conflicts before marking tasks parallel.
6. Confirm every source item is covered and every task supports one or an
   explicit plan obligation.

Avoid tasks named only after layers such as "backend", "frontend", or
"database". Split a task when it has multiple outcomes, independent failure
modes, unrelated change surfaces, or cannot fit one focused agent session.
Do not split work that must change atomically to remain correct.

## Select planned execution once

Use an approved project preference when repository guidance provides one;
otherwise ask once before writing the graph. Record exactly one topology for the
planned execution:

- `primary agent`: the primary agent explores, implements assigned tasks, and
  validates its own work;
- `fresh implementer per task`: the primary agent coordinates, but each assigned
  task starts with a fresh implementation context;
- `implementer + fresh validator`: an assigned implementer changes the task,
  then a separate fresh validator checks it.

Do not switch topology task by task without a new human decision. Topology does
not imply concurrency. Use subagents only when they add value.
Exploration is read-only; implementation changes only the assigned outcome;
validation is non-mutating and fresh by default, reports evidence or failures,
and returns any fix to implementation.

These are bounded execution controls, not a scheduler or permission for a
daemon, unattended run, automatic push, deployment, or rules change.

## Apply review backpressure

Record the human review/integration capacity, maximum active work, and review
queue in the execution controls. If capacity is not configured, use a
conservative maximum one `in-progress` task. Stop starting work whenever the
review queue is non-empty or the maximum is reached.

A `parallel-safe` task may run concurrently only after explicit assignment,
with isolated worktrees, branches, or non-overlapping change surfaces, and with
no dependency, file, generated artifact, or mutable-resource conflict. Otherwise
use `exclusive`. Never increase WIP merely because tasks are parallel-safe.

## Classify each task

Choose one primary type:

- `feature`: delivers observable behavior;
- `bugfix`: restores accepted behavior by correcting a defect;
- `enabler`: unlocks later delivery without standalone product behavior;
- `migration`: changes persisted data, contracts, or compatibility state;
- `verification`: provides independent evidence not owned by another task;
- `operations`: changes build, deployment, observability, or runtime controls;
- `maintenance`: improves internals without changing accepted behavior;
- `documentation`: updates durable user or engineering guidance.

Assign risk as `low`, `medium`, or `high` using `AGENTS.md` and record one-line
rationale. Inherit the plan risk unless the task has a clear reason to differ.
Task rationale fields explain execution and risk, never the product why; link to
source and plan items rather than copying their rationale.

Assign execution policy:

- `parallel-safe`: eligible for concurrent assignment only under the isolation
  and capacity controls above after every dependency is done;
- `exclusive`: must run alone because shared mutation or coordination makes
  concurrency unsafe.

Keep dependency order only in `Depends on`; do not duplicate it in execution
policy. Record task conflicts symmetrically. When uncertain, prefer `exclusive`
and state the reason. A human or external orchestrator assigns work; Markdown
state is not an atomic claim.

## Write

Use [assets/tasks.template.md](assets/tasks.template.md) and write
`<work-root>/<feature>/tasks.md`. If the `evidence` module is active under
`AGENTS.md`, load its `MODULE.md` and link requirement and expected-check
coverage without making evidence a second source of task state. If `multi-repo`
is installed and enabled in the recognized configuration, load its `MODULE.md`
and focused task snippet; assign exactly one primary Repository ID and record
cross-repository dependency and integration fields there rather than changing
the core template. Preserve the selected topology and capacity once, then give each task:

- stable ID and outcome, source and plan links, type, risk, and state;
- dependencies, blocker, execution policy and rationale, change surface, and
  symmetric conflicts;
- a concise change contract covering what, linked why, scope, evidence, risk,
  agent roles, and review focus;
- prospective acceptance evidence, validation commands, and actual result,
  initially `pending`.

Use only `blocked`, `ready`, `in-progress`, `done`, or `stale` as task states.
Maintain concise coverage from each source and plan item to task IDs. If accepted
what or how changes, return upstream, then mark only affected tasks stale;
unrelated tasks remain valid.

Only dependency-free, decision-complete tasks may start as `ready`; dependent
tasks start `blocked` with dependency IDs as the blocker. A decision, safety, or
external blocker requires an explicit reason and resolution; it is never cleared
merely because dependencies finish.

## Quality gate

Verify:

- all source items and plan obligations are covered without invented rationale;
- the coverage map supports partial invalidation;
- the graph is acyclic and has at least one ready task;
- each task is independently understandable and verifiable;
- no task contains a hidden product or architecture decision;
- topology, roles, capacity, review queue, assignment, isolation, dependencies,
  and conflicts agree;
- the graph contains no speculative infrastructure or process work.

---
name: plan
description: Design how an approved specification should be implemented in an existing or new codebase, resolving material technical decisions with the user one clear question at a time before writing implementation-ready tasks. Use when the user asks for architecture, technical design, task decomposition, an implementation plan, data model, API contract, migration plan, or test strategy.
---

# Plan an Implementation

Convert approved product behavior into a technically coherent, executable plan.
Do not modify production code.

## Discover

1. Read only the relevant specs and repository guidance.
2. Inspect the codebase, tests, dependencies, and established conventions.
3. Identify constraints, reusable components, trust boundaries, and unknowns.
4. Separate repository facts, confirmed constraints, assumptions, and choices.

## Resolve decisions conversationally

For every material uncertainty, apply the human decision protocol in
`AGENTS.md`:

- ask one clear, self-contained question at a time;
- offer distinct alternatives with consequences;
- mark and justify the recommended option;
- update the confirmed design after each answer.

Ask when a choice materially affects architecture, data, APIs, security, cost,
operability, compatibility, reversibility, or task structure. Decide trivial,
reversible, repository-standard details directly and record the rationale.

Do not write the final plan until material decisions are resolved and the user
has confirmed the proposed technical direction.

## Design

Cover only what the change needs:

- components and responsibilities;
- interfaces and integration points;
- data ownership, model, and migration;
- security and privacy boundaries;
- failure handling and recovery;
- compatibility and rollout;
- observability;
- verification strategy.

Create a separate technical artifact only when several tasks share it, it needs
independent review, or moving it out materially reduces task context. Possible
artifacts include `architecture.md`, `data-model.md`, `api-contract.md`,
`migration.md`, and `test-strategy.md`.

## Decompose

Create small vertical tasks that produce observable progress. Each task must
have:

- stable ID and outcome;
- dependencies;
- expected change surface;
- acceptance or completion evidence;
- validation commands or method;
- state: `blocked`, `ready`, `in-progress`, or `done`.

Prefer tasks that fit one focused agent session. Mark safe parallel work and
shared-file conflicts explicitly. Avoid tasks named only after horizontal
layers such as "do backend" or "add frontend".

Use [assets/plan.template.md](assets/plan.template.md) and write temporary
planning artifacts under `.work/<feature>/`.

## Quality gate

Verify that:

- every task traces to a requirement;
- every requirement is covered;
- dependencies form an executable order;
- tasks have observable completion evidence;
- no unresolved material decision is hidden inside a task;
- the plan introduces no unnecessary infrastructure or abstraction.


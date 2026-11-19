---
name: plan
description: Design how accepted product intent should be implemented in an existing or new codebase, resolving material technical decisions with the user one clear question at a time. Use when the user asks for architecture, technical design, an implementation plan, data model, API contract, migration plan, or test strategy, or when medium/high risk requires a durable plan. Accept a spec, issue, contract, or confirmed request as source intent. Do not decompose the design into executable tasks.
---

# Plan an Implementation

Convert approved product behavior into a technically coherent design.
Do not modify production code.

## Discover

1. Read only the authoritative source intent and relevant repository guidance;
   preserve links to every source.
2. Inspect the codebase, tests, dependencies, and established conventions.
3. Separate repository findings/facts, confirmed constraints, assumptions, agent
   inferences, unknowns, and proposed technical choices. Code shows the current
   implementation, not product intent or decision rationale.
4. Return upstream when source intent contradicts itself or repository evidence
   exposes a material product ambiguity.

## Resolve the work root

Resolve the destination only when this operation will inspect or write planning
artifacts. Reject any `.agents/project.md` as unsupported before writing. If
`.agents/project.json` is absent, use the `.work/` fallback. If it exists,
validate it with `.agents/skills/setup/assets/project.schema.json` and apply
`.agents/skills/setup/references/project-config.md`. Stop on any invalid config
rather than guessing or falling back. Use recognized `roots.work` as
`<work-root>`.

## Resolve decisions conversationally

For every material uncertainty, apply the human decision protocol in
`AGENTS.md`:

- ask one clear, self-contained question at a time;
- offer distinct alternatives with consequences;
- mark and justify the recommended option;
- update the confirmed design after each answer.

Ask when a choice materially affects architecture, data, APIs, security, cost,
operability, compatibility, reversibility, or task structure. Decide trivial,
reversible, repository-standard details directly. Record concise rationale only
for material technical decisions and link supporting sources instead of copying
narratives.

An agent inference never silently becomes a confirmed decision. Keep it labeled
until the user confirms the choice; if its basis or rationale remains missing,
record an unknown. Do not write the final plan until material decisions are
resolved and the user has confirmed the proposed technical direction. Record
conclusions, not private chain-of-thought.

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

Use [assets/plan.template.md](assets/plan.template.md) and write temporary
planning artifacts under `<work-root>/<feature>/`.
If the `evidence` module is active under `AGENTS.md` and duration, coordination,
or risk warrants a record, load
its `MODULE.md` and initialize only its plan-relevant contract and sources. If
`multi-repo` is installed and enabled in the same recognized configuration,
load its `MODULE.md` and focused plan snippet to map components and checks to
stable Repository IDs.
Keep source coverage as a small
impact map from source items through plan areas. On a confirmed change, mark only
affected map rows and downstream tasks stale; unrelated rows remain valid. Keep
the plan `draft` while a material decision or user confirmation is pending; set
it to `approved` only after the user confirms the complete technical direction.

## Quality gate

Verify that:

- the plan preserves every authoritative source and separates repository facts,
  constraints, assumptions, inferences, unknowns, and confirmed decisions;
- each material confirmed technical decision has source-linked rationale, while
  no inference is presented as confirmation;
- requirements have a coherent implementation path and impact-map coverage;
- risk is classified as `low`, `medium`, or `high`;
- no unresolved material decision is hidden in the design;
- the plan introduces no unnecessary infrastructure or abstraction.

When an approved plan fully covers a source spec, report that it supports the
spec's `planned` transition and update it only when artifact maintenance is
authorized. Do not create executable tasks. Use `decompose-tasks` only when the
plan contains multiple independently executable tasks, requires cross-session
handoff, or benefits from parallel execution.

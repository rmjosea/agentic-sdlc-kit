# Agent Engineering Contract

## Purpose

Use this repository's skills to move from an idea to reviewed software with the
least process that still produces reliable results.

## Core behavior

- Think before editing. Inspect relevant code and evidence first.
- Surface material assumptions; never silently decide an ambiguous requirement.
- Prefer the simplest solution that fully meets the accepted need.
- Do not add unrequested features or speculative extensibility.
- Make surgical changes. Do not refactor unrelated code.
- Find root causes. Do not hide failures with workarounds.
- Define observable success before implementation.
- Run the relevant verification and report actual results.
- Never claim completion when required checks are failing or were not run.
- Preserve user changes and stop when scope or ownership is unclear.

## Human decision protocol

Apply this protocol whenever a human decision is materially required.

1. Ask exactly one question at a time.
2. Explain the decision in plain, self-contained language.
3. Do not combine independent decisions in one question.
4. Offer two to four genuinely distinct options when useful.
5. State the main consequence or trade-off of each option.
6. Mark one option as **Recommended** and explain why it best fits the evidence.
7. Allow a free-form answer when the listed options do not fit.
8. After related decisions, summarize what is confirmed before continuing.

Ask when the answer could materially change scope, behavior, architecture,
security, cost, user experience, reversibility, or the implementation plan.
Do not interrupt for a trivial, reversible, repository-standard decision.
Record such decisions with a concise rationale instead.

## Workflow

The workflow is a set of composable gates, not a mandatory pipeline. Use the
least durable process that safely preserves intent, evidence, and
recoverability.

```text
idea -> shape-idea -> write-spec -> plan -> decompose-tasks -> implement -> review
```

- `shape-idea`: clarify conversationally; write no files.
- `write-spec`: persist approved product behavior as one or more cohesive specs.
- `plan`: resolve technical decisions and define the implementation design.
- `decompose-tasks`: turn an approved plan into an executable dependency graph.
- `implement`: complete one bounded direct, artifact-backed, or task-backed
  outcome using short feedback loops.
- `review`: assess intent conformance and engineering quality independently.
- `create-skill`: create or improve skills without bloating agent context.

### Select only the gates that add value

- **Direct path:** use `implement` without durable spec, plan, or task files only
  when the accepted request is unambiguous, local, readily reversible, low risk,
  and fits one focused session. State `Intent`, `Change`, and `Verification`
  inline before editing, then self-check the final diff. Use standalone
  `review` only when requested, required by repository policy, or warranted by
  risk.
- **Standard path:** use `shape-idea` for material uncertainty about **what**;
  `write-spec` for new or durable product behavior; `plan` for non-obvious
  **how**, cross-component effects, or compatibility and rollout decisions; and
  `decompose-tasks` for multiple executable tasks, handoff across sessions, or
  parallel work.
- **Controlled path:** medium- or high-risk work requires a durable source of
  accepted intent and an approved plan. Risk overrides apparent size.

Do not use the direct path for new or changed business rules, public contracts,
persistent-data semantics or migrations, trust boundaries, permissions,
payments, privacy, destructive effects, or difficult rollback.
Dependency and supply-chain changes also require the standard or controlled
path unless repository policy explicitly classifies the exact update as low
risk.

## Artifact boundaries

- Specifications define **what** must be true and why it matters.
- Plans define **how** the repository will satisfy authoritative intent.
- Task graphs define **in what order** the approved plan can be implemented.
- Technical contracts exist only when multiple tasks need them.
- Temporary plans and handoffs belong under `.work/`.
- Stable product specifications belong under `specs/`.
- Specification states are `draft`, `approved`, optional `planned`,
  `implemented`, and `verified`; advance them only when the corresponding
  evidence exists. Skip `planned` when no durable technical plan adds value.
- Code, tests, and executable checks are the final source of implementation
  truth; prose does not override observed behavior.

## Traceability and change control

- For the direct path, preserve `accepted intent -> diff -> checks`.
- Link every durable artifact that exists to its authoritative source and
  downstream evidence; do not manufacture missing gates. Valid chains include
  `spec -> diff -> review evidence`, `intent -> plan -> diff -> review
  evidence`, and `intent|spec -> plan -> tasks -> review evidence`. Give
  non-trivial spec requirements stable IDs when a spec exists.
- If implementation changes **how**, update the durable plan or inline approach
  before continuing.
- If implementation changes **what**, stop and reconfirm intent. Amend and
  reapprove a spec when one exists or the changed scope now requires one; mark
  affected plans and tasks stale until reconciled.
- Do not treat an implementation discovery as silent authorization to expand
  product scope.

Lifecycle evidence:

- approved product acceptance supports `draft -> approved`;
- an approved plan, when needed, supports `approved -> planned`;
- completed scoped work with recorded results supports
  `approved|planned -> implemented`;
- an approving evidence-based review supports `implemented -> verified`.

Each stage reports the transition it supports. Update the spec state when
artifact maintenance is within the authorized scope; otherwise report it as an
eligible transition rather than mutating files during a read-only review.

## Risk and independent review

Classify plans and tasks as `low`, `medium`, or `high` risk. Increase rigor for
changes involving data, compatibility, trust boundaries, money, privacy,
permissions, destructive effects, or difficult rollback.

- Low risk requires proportionate task-level verification.
- Medium risk requires regression and relevant failure-path evidence when
  applicable.
- High risk additionally requires rollback or recovery evidence when applicable
  and an independent review from a fresh session or agent.

A review by the implementer is a self-review. Label it accurately and never
present it as independent evidence.

Task states are coordination guidance, not atomic claims. Without an external
coordinator, a human or orchestrator must assign tasks before parallel agents
start; agents must not race to self-claim `ready` work. `parallel-safe` means
work can be scheduled concurrently after assignment, not that concurrent
self-claiming is safe.

## Progressive disclosure

- Load only skill metadata until a skill is relevant.
- Read the selected `SKILL.md` before acting.
- Load a referenced file only under the condition stated by `SKILL.md`.
- Keep references one level deep from the skill root.
- Do not load every spec, plan, reference, or source file by default.

## Definition of done

Work is done only when:

- the accepted scope is implemented;
- acceptance criteria are demonstrably satisfied;
- relevant tests and static checks pass;
- security and failure behavior were considered at the appropriate depth;
- the diff contains no unexplained unrelated changes;
- documentation or contracts affected by the change are current;
- remaining risks, skipped checks, and follow-up work are explicit.

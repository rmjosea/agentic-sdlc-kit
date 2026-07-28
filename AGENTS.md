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

```text
idea -> shape-idea -> write-spec -> plan -> decompose-tasks -> implement -> review
```

- `shape-idea`: clarify conversationally; write no files.
- `write-spec`: persist approved product behavior as one or more cohesive specs.
- `plan`: resolve technical decisions and define the implementation design.
- `decompose-tasks`: turn an approved plan into an executable dependency graph.
- `implement`: complete one ready task using short feedback loops.
- `review`: assess spec conformance and engineering quality independently.
- `create-skill`: create or improve skills without bloating agent context.

Do not skip a stage for non-trivial work unless the required artifact or
decision already exists. Trivial changes may use a lightweight inline plan.

## Artifact boundaries

- Specifications define **what** must be true and why it matters.
- Plans define **how** the repository will satisfy approved specifications.
- Task graphs define **in what order** the approved plan can be implemented.
- Technical contracts exist only when multiple tasks need them.
- Temporary plans and handoffs belong under `.work/`.
- Stable product specifications belong under `specs/`.
- Specification states are `draft`, `approved`, `planned`, `implemented`, and
  `verified`; advance them only when the corresponding evidence exists.
- Code, tests, and executable checks are the final source of implementation
  truth; prose does not override observed behavior.

## Traceability and change control

- Give non-trivial requirements stable IDs and link every task to the
  requirements it advances.
- Link plans to their source specs and reviews to the requirements they verify.
- If implementation changes **how**, update the plan before continuing.
- If implementation changes **what**, stop, amend and reapprove the spec, then
  mark affected plans and tasks stale until they are reconciled.
- Do not treat an implementation discovery as silent authorization to expand
  product scope.

## Risk and independent review

Classify plans and tasks as `low`, `medium`, or `high` risk. Increase rigor for
changes involving data, compatibility, trust boundaries, money, privacy,
permissions, destructive effects, or difficult rollback.

- Low risk requires proportionate task-level verification.
- Medium risk requires regression and failure-path evidence.
- High risk requires an independent review from a fresh session or agent.

A review by the implementer is a self-review. Label it accurately and never
present it as independent evidence.

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

---
id: SPEC-001
title: Agentic SDLC Kit v1
status: verified
depends_on: []
---

# Agentic SDLC Kit v1

## Context

Coding agents can generate code quickly, but keeping them aligned with product
intent, repository conventions, risk, and observable quality across multiple
sessions is harder. Heavyweight process frameworks slow small changes; ad-hoc
prompts are unreliable. Teams need a lightweight, portable harness that agents
can follow without becoming a framework themselves.

## Outcome

Provide a repository-level engineering contract and a set of composable skills
that move a work request from accepted intent to verified software using the
least durable process that still produces reliable results. The kit keeps a
small, provider-agnostic core and makes advanced assurance features opt-in.

## Actors and scenarios

- **Developer or team**: wants reliable agent assistance for new or existing
  projects without being forced into a rigid pipeline.
- **Coding agent**: needs clear rules for when to ask, what evidence to produce,
  and how to hand off work safely.
- **Reviewer or teammate**: needs traceability from intent to diff to evidence,
  and confidence that the work matches the approved scope.

## Scope

### In scope

- `AGENTS.md` as the repository engineering contract.
- Six core workflow skills: `shape-idea`, `write-spec`, `plan`,
  `decompose-tasks`, `implement`, `review`.
- Default utility skills: `create-skill`, `setup`, and `ask-kit`.
- Optional skill: `domain-model`.
- Conservative installer and structural validator.
- Developer guide and behavioral evaluation scenarios.
- Optional assurance modules: durable evidence, enforceable rules,
  multi-repository support, and compliance/auditable traceability.

### Out of scope

- Provider-specific adapters, plugins, or slash commands.
- Orchestration framework, scheduler, daemon, or proactive long-running agents.
- Automatic commit, push, merge, release, or deployment.
- Legal certification, compliance guarantees, or external audit services.
- Mandatory use of every workflow gate for every change.

## Requirements

### Core workflow

**REQ-001**: The kit must provide the six core skills `shape-idea`,
`write-spec`, `plan`, `decompose-tasks`, `implement`, and `review` as portable
Agent Skills under `.agents/skills/`.

**REQ-002**: `shape-idea` must resolve material product ambiguity through a
conversational, one-question-at-a-time process and must not write files.

**REQ-003**: `write-spec` must persist approved product behavior as one or more
atomic specifications, keeping implementation choices out unless they are
confirmed constraints.

**REQ-004**: `plan` must resolve material technical decisions with the user and
produce a durable implementation design when the change needs one.

**REQ-005**: `decompose-tasks` must turn an approved plan into an executable
and traceable dependency graph.

**REQ-006**: `implement` must complete one bounded outcome, run relevant
verification, and report actual evidence before claiming completion.

**REQ-007**: `review` must assess the diff and observed behavior against
authoritative intent and repository standards, distinguishing observed evidence
from unverified claims.

### Utility and optional skills

**REQ-008**: The default-installed `create-skill` utility must allow the user to
create or improve portable Agent Skills without loading its body until relevant.

**REQ-009**: `domain-model` must optionally build and maintain a project
language glossary (`CONTEXT.md`) and architectural decision records (ADRs)
when decisions are hard to reverse, surprising without context, and the product
of a real trade-off.

**REQ-010**: The default-installed `setup` utility must guide the user on demand
to configure the kit for a project, recording where issues live, which triage
labels to use, and where domain documentation belongs.

**REQ-011**: The default-installed `ask-kit` utility must help the user on demand
choose the right installed skill for a given request.

### Installation and validation

**REQ-012**: The installer must copy the canonical skills into the target
repository and install `AGENTS.md` only when it does not already exist.

**REQ-013**: The installer must not overwrite user-modified content without an
explicit user decision.

**REQ-014**: The validator must check skill set, metadata, size budgets,
local references, required artifact fields, and provider neutrality.

### Decision, risk, and evidence

**REQ-015**: The kit must apply the human decision protocol for material
ambiguity: one clear question at a time, with distinct options, consequences,
and a justified recommendation.

**REQ-016**: Work must be classified as `low`, `medium`, or `high` risk, with
independent review required for high-risk changes.

**REQ-017**: No skill or agent may claim completion when required checks are
failing or were not run.

**REQ-018**: The kit must preserve the chain from accepted intent to diff to
evidence, and must not manufacture missing gates.

**REQ-019**: The kit must be provider-agnostic: compatibility is based on
observable capabilities and public tests, not on specific tool brands.

### Addy Osmani improvements

**REQ-020**: The kit must preserve the source and the confirmed rationale
behind decisions, distinguishing confirmed reasoning from repository evidence,
agent inference, and unknown origin.

**REQ-021**: Each non-trivial change must leave a concise contract that states
what changes, why, scope, evidence, risk, and what the reviewer should focus on.

**REQ-022**: Quality review must select from a set of observable signals
including correctness, security, compatibility, maintainability, performance,
accessibility, observability, cost, and understandability.

**REQ-023**: The workflow must apply backpressure: a state may not advance
without required evidence, cheap checks run first, and work-in-progress must
shrink if human review becomes a bottleneck.

**REQ-024**: Work in progress must not exceed the review and integration
capacity of the people responsible for the work.

**REQ-025**: Handoffs across sessions or agents must include objective state,
evidence, consumed budget, reason for stopping, and the next safe action.

**REQ-026**: Recurring failures must be addressed by deterministic tests,
analyzers, or controls rather than by ad-hoc rules, and any new rule must name
the failure it prevents.

**REQ-027**: The kit must be evaluable against a baseline that compares the
agent without the kit, with the current version, and with the proposed version,
measuring real success, false completion, scope creep, human fixes, cost, and
escaped defects.

### Matt Pocock improvements

**REQ-028**: The optional `domain-model` skill must update `CONTEXT.md`
lazily, only when a domain term is resolved, and must keep it free of
implementation details.

**REQ-029**: The optional `domain-model` skill must create an ADR only when a
decision is hard to reverse, surprising without context, and the result of a
real trade-off.

**REQ-030**: The `implement` testing reference must describe red-green-refactor
through stable public seams, and must name and avoid tautological tests,
implementation-coupled tests, and horizontal slicing.

### Optional assurance modules

**REQ-031**: Durable evidence must be preserved when duration, coordination, or
risk make it necessary, including approved specs, plan and task state, and
final verification evidence.

**REQ-032**: The kit must provide a neutral, executable command that flags
inconsistencies or missing evidence, and may be integrated optionally with CI
or local actions.

**REQ-033**: Multi-repository support must be an optional module that extends
core skills with repository-targeting metadata, not part of the core.

**REQ-034**: Compliance and auditable traceability must be an optional module
with approvals and durable audit logs, without promising legal certification.

### Harness discovery and configured roots

**REQ-035**: `AGENTS.md` must act as the concise session bootstrap and point to
the canonical `.agents/` catalog, installed capability metadata, project
configuration, ownership manifest, module contracts, validation commands, and
full source documentation without copying their detailed content.

**REQ-036**: When `.agents/project.md` is recognized, `roots.specs` and
`roots.work` must override the conventional `specs/` and `.work/` locations in
the core workflow; when configuration is absent, the conventional paths remain
the fallback.

## Business rules

- Specifications define **what** must be true; plans define **how** intent will
  be satisfied; task graphs define **in what order** work executes; code,
  tests, and checks are the final source of implementation truth.
- A skill may not claim completion without the required observable evidence.
- A human must confirm medium, high, or ambiguous risk before proceeding.
- The kit may only modify content it can identify as its own; conflicts with
  user-modified content must stop and ask.
- The agent must use the direct path only for unambiguous, local, reversible,
  low-risk changes that fit one session.
- Subagents are used only when they add value, such as independent exploration,
  isolated implementation, or independent validation.
- No skill may automatically push, deploy, merge, publish, or modify the kit's
  own rules, skills, or controls during unattended execution.
- Work-in-progress must not grow beyond the capacity of the people who must
  review and integrate it.
- The catalog defines distribution membership and profiles, the ownership
  manifest records installer-managed content, and safe filesystem presence
  establishes current capability availability; disagreements must be reported.
- A recognized project configuration overrides conventional artifact roots only
  for fields the consuming workflow explicitly supports.

## Failure behavior and edge cases

- **Missing `AGENTS.md`**: the installer adds the canonical contract if none
  exists; if one exists, it never overwrites without explicit user action.
- **Missing or malformed skills**: the validator reports the problem and exits
  non-zero, with a clear list of what is missing or invalid.
- **No verification evidence**: `implement` must report `not done`, record what
  was missing, and ask whether to continue, adjust scope, or stop.
- **Change of intent during implementation**: the agent must stop, reconfirm
  the new intent, and mark affected plans and tasks stale.
- **User-modified file conflict during install**: the installer halts and asks
  whether to keep the user's version, keep the kit's version, or merge.
- **Direct path misused**: the agent must stop and propose the standard or
  controlled path, explaining why.
- **High risk without independent review**: `review` must report `blocked` and
  require an independent fresh review before approval.

## Quality constraints

- The kit must remain provider-agnostic and portable across coding agents that
  can read markdown and follow instructions.
- Skills must be small, composable, and load progressively: metadata first,
  `SKILL.md` when relevant, references only under declared conditions.
- The core must work without optional modules; optional modules must not
  introduce dependencies into the core.
- No speculative abstraction, orchestration framework, or persistent background
  process may be introduced.
- The validator must be deterministic and runnable locally without external
  secrets.
- Documentation must be concise and discoverable from `AGENTS.md`.

## Dependencies and confirmed constraints

- Python 3 for the installer and validator.
- Git for branch-based traceability and recovery.
- The target repository must allow the kit to write `.agents/skills/`,
  `AGENTS.md`, and optional artifacts under recognized configured roots or the
  conventional `specs/` and `.work/` fallbacks.
- Optional modules may depend on additional project-specific tools, but the
  core must not.

## Acceptance criteria

**AC-001**: The kit source checkout passes `python3 scripts/validate.py`; a
target installation that includes `enforcement` can run its installed read-only
checker without requiring the source-only validator.

**AC-002**: A developer can request a trivial, local, reversible, low-risk
change and the agent uses the direct path without creating durable workflow
artifacts.

**AC-003**: A developer can request a durable feature and the agent follows the
standard or controlled path through the relevant workflow gates, producing
linked spec, plan, tasks, and review evidence as needed.

**AC-004**: The installer does not replace an existing `AGENTS.md` or
user-modified skill files without an explicit user decision.

**AC-005**: The validator detects a missing skill, malformed skill metadata,
broken local reference, or missing required artifact field.

**AC-006**: A high-risk change is not marked `verified` without independent
review evidence.

**AC-007**: `domain-model`, when invoked, can produce or update a `CONTEXT.md`
glossary and create an ADR that satisfies the three ADR conditions.

**AC-008**: `setup`, when invoked, can record the project's issue tracker,
triage labels, and domain documentation layout.

**AC-009**: `ask-kit`, when invoked, can recommend the most appropriate skill
for a user request.

**AC-010**: The `implement` testing reference explains stable public seams,
tautological tests, implementation-coupled tests, and horizontal slicing, and
advises against them.

**AC-011**: An agent starting from `AGENTS.md` can locate the canonical catalog,
installed skill and module entry points, optional project configuration,
ownership claims, source and installed validation commands, artifact roots, and
source documentation while loading only the relevant detail.

**AC-012**: With a recognized project configuration, `write-spec`, `plan`,
`decompose-tasks`, and `implement` use configured specs/work roots; without one,
they use `specs/` and `.work/`.

## Open questions

None for v1.

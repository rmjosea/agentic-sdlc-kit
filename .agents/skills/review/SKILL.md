---
name: review
description: Review a completed or in-progress change against authoritative intent and engineering standards using the actual scoped diff and executed checks. Use when the user asks for code review, implementation verification, acceptance review, pre-merge review, or an independent readiness assessment, with or without a formal spec.
---

# Review an Implementation

Review is non-mutating unless the user separately authorizes fixes. Inspect the
change itself; never treat the implementer's summary as evidence.

## Fix scope, role, and sources

1. Resolve immutable identifiers for the fixed base and head. Record the exact
   committed range plus included staged, unstaged, and untracked changes. If the
   worktree changes during review, re-fix the scope before concluding.
2. Record reviewer identity or role, implementer(s), prior participation,
   independence classification, and its factual basis. Independent means a
   fresh session or agent that did not implement the change. A review by any
   implementer is a self-review; self-review is never independent.
3. Classify reviewer-assessed risk as `low`, `medium`, or `high` from affected
   behavior, data, compatibility, trust, money, privacy, permissions,
   destructive effects, and reversibility. Risk, not diff size, determines
   review depth. High risk needs a fresh non-implementer; without one the verdict
   is `blocked`.
4. Identify and rank authoritative sources: accepted request or issue, spec,
   approved plan, task, and repository guidance as applicable. Plans define
   approved how and tasks define bounded execution; code shows current behavior
   but cannot supply product intent or rationale.
5. Consume an available concise change contract: what, authoritative why,
   scope, expected evidence, Contract risk, agent roles, and review focus. Keep
   Contract risk separate from reviewer-assessed risk; compare them and report
   any deviation and its impact. Record missing fields as unknown and report the
   gap in proportion to its effect; do not invent intent or automatically block
   a low-risk review whose scope, intent, and evidence are otherwise reliable.

Review the actual fixed range and uncommitted scope, then derive checks from the
authoritative acceptance criteria and risk. Do not trust claimed files, behavior,
or checks until observed.

## Keep two review axes separate

### Intent conformance

Map each available source item to implementation and evidence. Check required
behavior, acceptance criteria, business and failure rules, deviations from
confirmed scope, and missing, partial, or extra behavior. Passing tests cannot
establish conformance when acceptance behavior is absent or untested. If no
reliable product source exists, say what conformance could not be assessed
rather than inventing it.

### Engineering quality

Assess implementation quality and regression risk independently of conformance.
A change can match intent but be unsafe, or be well engineered but implement the
wrong behavior. Check unrelated changes and repository conventions as part of
this axis.

## Select quality signals

Select only applicable signals. For each selected signal, state its trigger and
evidence; mark every other signal `N/A` with one concise reason. Do not perform a
ritual checklist.

- **Correctness** — required behavior, invariants, edge or failure paths changed;
  use source inspection plus direct behavioral checks.
- **Security** — a trust boundary, permission, untrusted input, secret, personal
  data, payment, dependency, or external/destructive action changed; inspect the
  affected abuse paths and controls.
- **Compatibility** — a public interface, persisted data, dependency, client, or
  rollout contract changed; use old/new consumer, migration, or fixture evidence.
- **Maintainability** — ownership, coupling, duplication, or future change cost
  is materially affected; compare repository patterns and focused source paths.
- **Performance** — a hot path, volume, latency, memory, or resource bound may
  change; use representative measurement or explain the bounded inference.
- **Accessibility** — user interaction, semantics, focus, input, or rendered
  content changed; use applicable automated and manual interaction evidence.
- **Observability** — an operational, asynchronous, external, or failure path
  changed; inspect actionable logs, metrics, traces, and failure diagnosis.
- **Cost** — metered compute, storage, network, model, or vendor use may change;
  use representative usage or an explicit estimate with assumptions.
- **Understandability** — behavior or control flow is complex, surprising, or
  easy to misuse; inspect naming, locality, comments, and affected documentation.

Read [references/security.md](references/security.md) only when the security
trigger applies. It narrows that signal; it does not turn the review into a
full security audit.

## Build evidence

Run the smallest set of acceptance, regression, failure-path, static, and
operational checks required by intent and risk when safe and available. Record
commands or procedures, scope, actual result, and one evidence class:

- **observed evidence**: the reviewer directly inspected or executed it in the
  fixed scope and records the result;
- **source-based inference**: a conclusion tied to identified source lines or
  artifacts but not directly exercised;
- **unverified claim**: a summary, reported check, or behavior the reviewer did
  not independently inspect.

Treat implementer and CI summaries as unverified until their underlying scope
and result are inspected. Tests green alone are insufficient: verify that tests
exercise authoritative acceptance behavior and relevant risks. Failed or unrun
required evidence prevents `approved`.

## Findings and verdict

When converting findings into comments or evaluating an author response, load
[the comment reference](references/review-comments.md) only for that action.
Impact severity and comment disposition are separate axes; `Optional`, `Nit`,
`Question`, and `FYI` cannot alone produce `changes-required`.

Report only actionable, evidence-backed findings, ordered `critical`, `high`,
`medium`, then `low`. Include evidence class and result, precise location,
impact, and the minimal action needed. Do not add filler or combine unrelated
problems. Report acceptance coverage and residual or unverified risk separately.

Finish with exactly one verdict:

- `approved`: no unresolved implementation correction or acceptance failure,
  all risk-required evidence is available, and high-risk independence is met;
- `changes-required`: an implementation defect is established, including
  observed failed behavior, a regression, or missing/extra acceptance behavior;
- `blocked`: required evidence, access, stable scope, authoritative intent, or
  high-risk independence is unavailable, so a reliable approval decision cannot
  be made. Missing evidence alone is not an implementation defect.

Missing high-risk independence always takes precedence: return `blocked` and
label any defects found by the self-review as preliminary findings.

An approving evidence-based review may support a source spec's `verified`
transition. Update an artifact only when maintenance is explicitly authorized.
Before using project preferences, module activation, configured repositories, or
a configured work root, reject `.agents/project.md` as unsupported; validate
`.agents/project.json` with `.agents/skills/setup/assets/project.schema.json` and
apply `.agents/skills/setup/references/project-config.md`. Stop on invalid config.
Use recognized `roots.work` as `<work-root>/` for a persisted standalone report,
with `.work/` only when both config files are absent.

Use [assets/review.template.md](assets/review.template.md) for the report. If the
`evidence` module is active under `AGENTS.md`, load its `MODULE.md`, produce its
`review.md` through this report contract, and link the verdict without copying
the machine record into prose. When `multi-repo` is installed and enabled in a
recognized configuration, also load its `MODULE.md` and focused review snippet;
fix and report base/head and uncommitted scope separately per Repository ID.

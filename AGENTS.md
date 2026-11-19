# Agent Engineering Contract

## Purpose

Use this repository's skills to move from an idea to reviewed software with the
least process that still produces reliable results.

## Core behavior

- Think before editing: inspect relevant code, trace dependencies, and form an explicit mental model first.
- Surface material assumptions; never silently decide an ambiguous requirement.
- Surgical simplicity: prefer the simplest solution meeting accepted need; avoid speculative extensibility.
- Minimal diff: make surgical changes; do not refactor unrelated code. Find root causes, not workarounds.
- Execution-grounded truth: define observable success before editing; run checks and report actual results. Never claim completion when required checks fail or were not run.
- Counter-factual self-critique: actively evaluate failure paths and edge cases before considering work done.
- Circuit breaker: if a fix fails twice consecutively, stop editing; inspect runtime state before a 3rd attempt.
- Test preservation: never delete, comment out, or weaken existing tests to pass checks; treat failures as regressions.
- Preserve user changes and stop when scope or ownership is unclear.
- Prevent communication failures caused by ambiguous questions or explanations. Address people in simple, clear, friendly, and respectful language; use direct sentences and concrete words, and define necessary jargon.
- Make each question and explanation self-contained and unambiguous: state the relevant context, needed decision or action, and material constraints or consequences. If a material interpretation remains uncertain, ask for confirmation rather than guessing.
- Whenever you present alternatives or need a human decision, follow the Human decision protocol below: always, in every skill and message, without exception.
- Two-tier language policy (`.agents/conventions/naming-and-language.md`): harness infrastructure (`AGENTS.md`, `.agents/**`, `scripts/**`) in English; business artifacts (`features/`, `journeys/`, `personas/`, `business-context/`, `architecture/adr/`, `estimaciones/`) in the project's business language (Spanish by default); frontmatter keys and reserved values always in English.

## Repository discovery

Use this navigation by intent. Follow the load rule and stop as soon as the
request is addressable; do not preload the listed files.

| Need | Canonical path | Load rule |
| --- | --- | --- |
| Distribution membership and profiles | `.agents/kit-catalog.json` | Read only for installation, capability selection, or mismatch diagnosis. |
| Candidate skill procedure | `.agents/skills/<name>/SKILL.md` | Check safe file presence; inspect skill metadata first, then the selected body and only its one-level conditional resources. |
| Common conventions, lanes, and schemas | `.agents/conventions/conventions.md` | Load on demand per `.agents/conventions/loading-recipes.md`; never preload all convention files. |
| Project choices and schema | `.agents/project.json`, `.agents/skills/setup/assets/project.schema.json`, and `.agents/skills/setup/references/project-config.md` | Only when config exists and the request depends on it; validate before use. Any `.agents/project.md` is unsupported. |
| Installer-managed ownership | `.agents/agentic-sdlc-kit.json` | Read only to check ownership or installation claims; absence is valid. |
| Candidate module contract | `.agents/modules/<name>/MODULE.md` | Check safe file presence; read only at a relevant integration point. |
| Distribution validation | `scripts/validate.py` | Source checkout only: run `python3 scripts/validate.py`. |
| Installed consistency | `.agents/modules/enforcement/check.py` | When installed, callable directly as a read-only target checker. |
| Artifact destinations | `features/{NNN}-{slug}/` (or recognized `roots.specs` / `roots.work`; otherwise `specs/` / `.work/`) | Apply only the artifact boundary rules below. |
| Detailed operating guide | `docs/usage-guide.md` | Source checkout only; installed repositories use `AGENTS.md` and installed contracts. |

Precedence is narrow: catalog membership and profiles define the distribution;
the manifest records installer-managed ownership; safe filesystem presence of a
candidate `SKILL.md` or `MODULE.md` establishes current availability. Report the
mismatch whenever these sources disagree. A module must be installed, enabled in
recognized `.agents/project.json`, and have required settings; otherwise core
behavior is unchanged. An installed enforcement checker is always
callable read-only while its extensions remain conditional. Module instructions
may supplement but never replace authoritative intent, artifacts, code, checks,
or this contract.

## Change and control contracts

- Before each non-trivial change, state a concise contract covering what will
  change, why it is needed, scope, expected evidence, risk, agent roles, and the
  review focus. Link to authoritative rationale rather than inventing it.
- When a failure recurs, prefer a deterministic test, analyzer, or check that
  reproduces or prevents it.
- Add a prose rule only with a named motivating failure and human approval.
  Do not automatically modify repository rules or CI.

## Human decision protocol

Apply this protocol every time you present alternatives or a human decision is materially required, in any skill or message, without exception.

1. Ask exactly one question at a time in plain, self-contained language without combining independent decisions.
2. Offer two to four genuinely distinct options, stating the main consequence or trade-off of each option.
3. Mark one option as **Recommended** and explain why it best fits the evidence.
4. Allow a free-form answer when the listed options do not fit.
5. After related decisions, summarize what is confirmed before continuing.

Ask when the answer could materially change scope, behavior, architecture,
security, cost, user experience, reversibility, or the implementation plan.
Do not interrupt or record rationale for a trivial, reversible,
repository-standard decision. Record concise rationale for material decisions.

## Workflow and change lanes (XS–XL)

The workflow diagram is the delivery chain, not the complete capability
inventory. Its gates are composable, not a mandatory pipeline. Use the least
durable process that safely preserves intent, evidence, and recoverability.

```text
Definition:     drill-docs -> save-output -> judge-spec (loop)            -> approved artifact
Implementation: plan-feature -> breakdown-tasks -> implement -> close-spec -> implemented + validated change
```

- `drill-docs` (or `shape-idea`): extract structure conversationally in chat; write no files.
- `save-output` (or `write-spec`): materialize a draft to disk with Shape A frontmatter and split past ~3000 tokens.
- `judge-spec`: score and clarify a definition artifact against its `rubric-{type}.md` until explicit `approved` status.
- `plan-feature` (or `plan`): Explore -> Interrogate -> Plan -> Verify; record `target_repos` and field-level zero-invention companions (`data-model.md`, `api.md`, `event.md`, `test-plan.md`).
- `breakdown-tasks` (or `decompose-tasks`): turn a reviewed plan into atomic `T01..Tn` tasks grouped by `repo` with impact (`accion`/`analisis`/`verificacion`) and runtime (`[A]`/`[I]`/`[*]`) markers.
- `implement`: cold-start per-task gen-eval loop (test-first red -> minimal code -> green -> audit test diff -> stack juez rubric `rubrics/{stack}.md` -> `APROBADO` commit + `[x]`), plus feature-level regression and AC gate.
- `close-spec` (or `review`): notary closure once all tasks are `[x]` and merged, verifying AC coverage and diff sync before flipping `status: implemented`.
- `create-skill` and `agents-creator`: author or improve portable skills and repository `AGENTS.md` files.

`git-conventions`, `setup`, `ask-kit`, and `contribute` are default utility examples; `estimate-effort` and `domain-model` are optional.
These examples are not the full installed-capability or profile inventory.

### Select the lane by size tier and risk (`.agents/conventions/change-lanes.md`)

- **Lightweight lane (XS / S — Direct path):** use `implement` without durable spec, plan, or task files only when all 5 checks pass: no new interface, no behaviour/AC change, no sensitive surface, no ADR-level dependency, and one focused PR. State `Intent`, `Change`, and `Verification` inline, write the reproduction test first, apply the stack juez rubric over the diff, and use traceable commits (`git-conventions`).
- **Spec lane (M / L / XL — Standard and Controlled paths):** use `drill-docs -> save-output -> judge-spec` for new or changed product behavior; `plan-feature` for technical design, `target_repos`, and zero-invention companions; and `breakdown-tasks` for repo-grouped tasks. Medium- or high-risk work requires a durable source of accepted intent and an approved plan. Risk overrides apparent size: security, auth, permissions, persistent-data migrations, payments, privacy/PII, AI/eval, destructive effects, or difficult rollback never use the Lightweight/direct path (escape hatch: stop and switch to the Spec lane if discovered mid-change).

## Artifact boundaries

- **Code as Source of Truth, Spec as Delta:** Executable code and passing tests in the base branch are the single source of truth for current system behavior; domain context (`roots.domain_context`, `vault/`, or `AGENTS.md`) is a derived index of that code, never an authority above it. Specifications (`spec`, `user-journey`, `user-story`) define the approved delta (**what** must change and why); plans define **how**; tasks define **in what order**. Once a specification is implemented and sealed (`status: implemented`), committed tests carry the living behavioral contract and the specification remains a historical change record.
- By default, feature artifacts co-locate in `features/{NNN}-{slug}/` (`spec.md`, `plan.md`, companions, `tasks.md`, `implementation-report.md`) using Shape A frontmatter (`type`, `status`, `updated: YYYY-MM-DD`; see `.agents/conventions/frontmatter-schema.md`).
- If `.agents/project.md` exists, it is unsupported legacy input: stop before parsing configuration or writing any file. Never convert or overwrite it.
- If `.agents/project.json` exists and an artifact consumer needs it, validate it with `.agents/skills/setup/assets/project.schema.json` and apply `.agents/skills/setup/references/project-config.md`. An invalid configuration blocks that operation; stop rather than guessing a root.
- In recognized configuration, `roots.specs` is authoritative for `write-spec`; `roots.work` is authoritative for planning, task graphs, implementation handoffs, and other work artifacts. With neither project configuration file, `features/{NNN}-{slug}/` (or `specs/` and `.work/` for classic v2 artifacts) is used.
- Shape A definition states are `draft -> review -> needs-work -> approved -> implemented -> archived | superseded` (classic v2 specs also support `draft`, `approved`, optional `planned`, `implemented`, and `verified`). Advance states only when the required evidence and human confirmation exist.
- Code, tests, and executable checks are the final source of implementation truth; prose does not override observed behavior.

## Provenance

Classify material claims consistently:

- **Authoritative source/input**: accepted intent from an accountable person or identified source artifact.
- **Confirmed rationale**: a sourced product or technical why for a confirmed behavior, constraint, or decision.
- **Repository evidence/fact**: observed implementation state. It is evidence of what exists, not product or decision authority.
- **Confirmed constraint**: a sourced limit the work must honor.
- **Assumption**: an unverified premise carried transparently.
- **Agent inference**: a conclusion derived from sources or evidence but not confirmed by an authority.
- **Unknown**: material information that is unavailable or unresolved.

Never infer why from code, repository history, naming, or an outcome. Keep an
unconfirmed inference separate until an authority confirms it; otherwise retain
it as an inference or unknown. Record rationale only when material to behavior,
constraints, architecture, security, or reversibility. Prefer links to sources
over copied narratives. Record concise conclusions, not private chain-of-thought.

## Traceability and change control

- For the Lightweight/direct path, preserve `accepted intent -> diff -> checks`.
- Link every durable artifact that exists to its authoritative source and downstream evidence; do not manufacture missing gates. Valid chains include `spec -> diff -> review evidence`, `intent -> plan -> diff -> review evidence`, and `intent|spec -> plan -> tasks -> review evidence`.
- Maintain a source-to-plan-to-task coverage or impact map. When **what** or **how** changes, mark only affected downstream plan areas and tasks stale; unrelated artifacts remain valid.
- If implementation changes **how**, confirm material technical decisions and update `plan.md` / companions or inline approach before continuing.
- If implementation changes **what**, stop and reconfirm intent via `judge-spec` before reconciling affected plans and tasks.
- Do not treat an implementation discovery or agent inference as silent authorization to expand product scope or change the design.

Lifecycle evidence: approved product acceptance supports `draft -> approved`; an approved plan supports `approved -> planned`; completed scoped work with passing juez/checks supports `approved|planned -> implemented`; an approving evidence-based review supports `implemented -> verified`. Update spec state when within authorized scope; otherwise report it as an eligible transition.

## Risk and independent review

Classify plans and tasks as `low`, `medium`, or `high` risk. Increase rigor for changes involving data, compatibility, trust boundaries, money, privacy, permissions, destructive effects, or difficult rollback.

- Low risk requires proportionate task-level verification.
- Medium risk requires regression and relevant failure-path evidence when applicable.
- High risk additionally requires rollback or recovery evidence when applicable and an independent review from a fresh session or agent that did not implement the change. Without that independence, the review is blocked.

A review by the implementer is a self-review. Self-review is never independent; label it accurately and never present it as independent evidence. Task states are coordination guidance, not atomic claims: without an external coordinator, a human or orchestrator must assign tasks before parallel agents start; agents must not race to self-claim `ready` work. `parallel-safe` means work can be scheduled concurrently after assignment, not that concurrent self-claiming is safe.

## Source code documentation

Motivating failure: changes could be done while externally consumed behavior or non-obvious constraints remained undocumented.

- Apply this rule to source code in any language. Use the repository's canonical format; otherwise use an established ecosystem convention such as [PEP 257](https://peps.python.org/pep-0257/), [Javadoc](https://docs.oracle.com/en/java/javase/21/docs/specs/javadoc/doc-comment-spec.html), [Go doc comments](https://go.dev/doc/comment), [rustdoc](https://doc.rust-lang.org/rustdoc/), [TSDoc](https://tsdoc.org/), or the [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html).
- For externally consumable APIs and user- or operator-facing entry points, add documentation when introduced or when their observable contract changes. Cover applicable purpose, inputs, outputs, failures, side effects, constraints, and usage; for commands and scripts also cover invocation, environment, and exits.
- Keep documentation current. Follow Google style principles: internal comments explain confirmed non-obvious rationale and invariants (why, not what); never invent why or narrate obvious code, delete dead code, and avoid unassigned TODOs. Edit a generator, schema, or template instead of generated output; do not edit vendored code.
- Run applicable safe existing documentation checks and report their results; otherwise record a focused manual review for accuracy, completeness, and freshness.

## Definition of done

Work is done only when: the accepted scope is implemented; acceptance criteria are demonstrably satisfied; relevant tests, static checks, and stack juez rubrics pass; existing tests were preserved and not weakened or bypassed; security and failure behavior were considered at the appropriate depth; the diff contains no unexplained unrelated changes; documentation or contracts affected by the change are current; and remaining risks, skipped checks, and follow-up work are explicit.

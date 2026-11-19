---
id: PLAN-001
sources:
  - SPEC-001
  - specs/001-agentic-sdlc-kit-v1/spec.md
status: approved
risk: medium
risk_rationale: The installer writes agent configuration into existing repositories. Incorrect ownership or conflict handling could overwrite project-specific instructions or skills. The design mitigates this with preflight planning, content hashes, explicit conflict decisions, transactional writes, dry runs, and repository-level regression tests.
---

# Agentic SDLC Kit v1 implementation plan

## Goal and source intent

Implement the approved `SPEC-001` product definition as a lightweight,
provider-agnostic kit with a reliable default installation and complete opt-in
assurance capabilities. Preserve the existing separation between product
intent, technical design, execution state, and observed evidence.

The default installation must remain useful without optional modules. Advanced
capabilities must be discoverable, independently selectable, and inactive until
installed and enabled.

## Repository findings

- The repository currently contains seven sibling skills under
  `.agents/skills/`: the six workflow skills plus `create-skill`.
- `scripts/install.py` discovers every source skill directory and copies all of
  them. It has no component catalog, profiles, module selection, or ownership
  record.
- Existing conflict detection compares complete directory trees. With
  `--force-skills`, it removes and replaces a conflicting directory without
  knowing whether the target content came from the kit.
- Existing `AGENTS.md` files are preserved for manual semantic merge. This
  behavior is safe and remains the baseline.
- `scripts/validate.py` requires one exact seven-skill set and validates source
  structure, metadata, local links, size limits, provider neutrality, and
  selected template fields.
- `tests/scenarios.md` provides behavioral forward-evaluation scenarios but
  there are no executable installer, validator, configuration, or assurance
  tests.
- `.work/` is ignored by Git and is appropriate for the local plan and task
  graph, but not for shared final evidence.
- No project configuration, domain glossary, ADR convention, module system,
  installed-content manifest, durable evidence schema, audit schema, or
  multi-repository schema currently exists.

## Confirmed technical decisions

1. The default installation contains the six core skills plus `setup`,
   `ask-kit`, and `create-skill`.
2. `domain-model` is an optional skill, installed only when selected.
3. All skills remain sibling directories under `.agents/skills/`.
4. Cross-cutting optional capabilities live under
   `.agents/modules/<module>/` and are enabled through `.agents/project.md`.
5. The installer presents an interactive menu when connected to a terminal.
   Equivalent `--with` and `--profile` arguments support CI and scripted use.
6. The default durable evidence location is `evidence/<change>/`; `setup` may
   configure another repository-relative path.
7. Auditability in v1 means structured, schema-validated records versioned in
   Git. It does not imply cryptographic immutability, authenticated identity, or
   legal certification.
8. Multi-repository support coordinates declared, already available checkouts.
   It does not clone repositories, create worktrees, or manage credentials.
9. `implement` does not define a long-running or unattended execution policy.
   Runtime limits remain the responsibility of the user or agent provider.
10. The implementation risk is medium.
11. The installer is a local repository tool, not a security boundary against
    concurrent writers. It assumes exclusive write access while running and
    does not add platform-specific race-free filesystem confinement.
12. `AGENTS.md` is the concise, automatically loaded bootstrap. It contains a
    short navigation-by-intent index and precedence rules, while catalog,
    skill/module bodies, schemas, and the full guide remain canonical detail
    loaded on demand. Do not add a second `.agents/README.md` or loading-recipes
    layer.
13. A recognized `.agents/project.md` makes `roots.specs` and `roots.work`
    authoritative for their consumers. Without recognized configuration, core
    skills use `specs/` and `.work/`.

## Design summary

### Distribution catalog

Add a single machine-readable catalog at `.agents/kit-catalog.json`. It is the
source of truth for distributable components and contains:

- catalog schema version and kit version;
- skill groups: `core`, `utilities`, and `optional`;
- module names and descriptions;
- module dependencies;
- default and full profile selections.

The catalog, not directory discovery, drives installation and validation.
`README.md`, the developer guide, and `ask-kit` describe the same public groups;
source validation detects catalog/filesystem drift.

The initial groups are:

- core skills: `shape-idea`, `write-spec`, `plan`, `decompose-tasks`,
  `implement`, `review`;
- utility skills: `setup`, `ask-kit`, `create-skill`;
- optional skills: `domain-model`;
- modules: `evidence`, `enforcement`, `multi-repo`, `compliance`.

`compliance` declares dependencies on `evidence` and `enforcement`. Selecting a
component resolves its dependencies before showing the final installation
plan.

### Safe installer and ownership model

Refactor `scripts/install.py` around four phases:

1. **Selection**: read the catalog; use the interactive menu when appropriate or
   resolve `--profile` and `--with` arguments. In a non-interactive environment
   with no explicit selection, install the default profile.
2. **Preflight**: validate the target, resolve dependencies, inspect every
   destination, compare it with prior ownership hashes, and calculate all
   actions without writing.
3. **Conflict resolution**: show unknown or user-modified components and obtain
   an explicit `keep`, `replace`, or `abort` decision. Non-interactive conflicts
   fail unless an explicit conflict argument authorizes the selected outcome.
4. **Transactional application**: stage selected content, preserve affected
   destinations during the transaction, atomically move staged content into
   place, write the ownership manifest last, and restore prior content if any
   step fails.

Keep `--dry-run`. Preserve `--force-skills` as a documented compatibility alias
for explicit replacement, but do not let it bypass preflight visibility or
replace unselected paths.

Write `.agents/agentic-sdlc-kit.json` in the target repository with:

- manifest schema and kit version;
- installed component names;
- relative managed paths;
- SHA-256 tree hashes for the installed version.

A component is safely replaceable only when the destination still matches the
recorded hash. Unknown or changed content is never overwritten silently. A
component kept during a conflict is not claimed as managed. `.agents/project.md`
is always project-owned and is never added to the ownership manifest.

For `AGENTS.md`:

- copy and manage it when absent;
- leave an identical managed copy unchanged or update it when its recorded hash
  still matches;
- preserve an untracked or changed file and require semantic merge;
- never perform an automatic textual merge.

### Project configuration

The installed `setup` skill owns the guided workflow for creating or amending
`.agents/project.md`. It first inspects repository evidence, asks only for
values that cannot be inferred safely, presents the complete proposed change,
and writes only after explicit approval.

Use constrained YAML frontmatter whose compound values use JSON-compatible
syntax, allowing deterministic parsing with the Python standard library. The
schema supports:

- `schema_version`;
- issue tracker kind and location;
- triage-label mapping;
- specification, work, ADR, and evidence roots;
- installed and enabled module names;
- declared repositories for multi-repo operation;
- implementation-mode and review preferences when the user chooses defaults.

The Markdown body explains project vocabulary and human guidance but is not a
machine source of configuration. The file must contain no credentials, tokens,
or secret values. Multi-repo paths must be repository-relative or use declared
environment-variable placeholders.

If configuration is absent, all core skills continue to work with repository
defaults and no module behavior. If a configured module is not installed, the
consumer reports the mismatch and asks the user to install or disable it.

### Repository bootstrap and configured roots

Add one compact navigation-by-intent table to `AGENTS.md`. It points to the
catalog, skill metadata and bodies, project configuration and schema, ownership
manifest, module contracts, source validator, installed enforcement checker,
artifact roots, and source guide. It also states:

- the workflow diagram is the delivery chain, not the complete capability list;
- catalog membership and profiles do not prove current installation;
- the ownership manifest corroborates installer-managed content;
- safe `SKILL.md` or `MODULE.md` presence establishes current availability;
- optional module behavior needs enablement and required configuration, while
  an installed enforcement checker remains directly runnable read-only;
- each target is loaded only when the current request needs it.

Do not copy profile membership, schemas, skill descriptions, or module rules
into the entrypoint. Do not add `.agents/README.md` or a global loading-recipes
file; each skill keeps its own conditional resources.

When `.agents/project.md` exists, core consumers recognize it through the setup
schema contract. `write-spec` uses `roots.specs`; `plan`, `decompose-tasks`, and
`implement` use `roots.work`. If configuration is absent they retain `specs/`
and `.work/`. An unrecognized configuration blocks use of configured roots
rather than being silently ignored or guessed.

### Optional skills

#### `setup`

Provide the configuration flow above plus a template and field reference.
`setup` may update an existing kit-shaped configuration after approval, but it
must not overwrite an unrecognized `.agents/project.md`.

#### `ask-kit`

Act as a non-mutating router over installed skills and enabled modules. It
selects the least durable safe route using risk, ambiguity, expected lifetime,
and coordination needs. It explains why alternatives are unnecessary and does
not invoke another skill automatically.

#### `domain-model`

Read the configured domain-context and ADR roots. Create files lazily:

- `CONTEXT.md` contains only canonical domain terms, concise meanings,
  relationships, and explicitly rejected ambiguous synonyms;
- ADRs record context, considered alternatives, decision, rationale, and
  consequences.

Create an ADR only when all are true: the decision is costly to reverse,
surprising without context, and the result of a real trade-off. Repository
facts that contradict the proposed vocabulary or decision are surfaced rather
than silently reconciled.

### Conditional module loading

Extend the progressive-disclosure contract so a core skill:

1. reads `.agents/project.md` only when it exists and the current operation can
   depend on project configuration;
2. checks enabled module names;
3. reads only the applicable `.agents/modules/<name>/MODULE.md`;
4. loads module assets only under conditions declared by that module.

Module guidance is not duplicated into every core skill. Core skills contain
only the conditional loading contract and the points at which module controls
apply.

### Evidence module

The default layout is:

```text
evidence/<change-id>/
├── evidence.json
└── review.md
```

`evidence.json` is the deterministic source for assurance checks. Schema v1
contains:

- change identifier, authoritative source references, status, and risk;
- concise change contract: intent, confirmed rationale, scope, agent roles, and
  review focus;
- repository/base/head scope for every affected checkout;
- requirement coverage and evidence references;
- required, executed, skipped, and failed checks with observed results;
- review kind, reviewer declaration, verdict, and approval reference;
- remaining risks and follow-up items.

`review.md` remains the human-readable evidence-based report. Raw command output
is referenced rather than copied by default, reducing secret leakage and file
size. An absent provider budget is recorded as `not-tracked`; the kit must not
invent cost, time, or turn counts.

The module defines risk-proportionate completeness:

- low: scoped checks and self-review evidence;
- medium: regression and relevant failure-path evidence;
- high: recovery or rollback evidence when applicable plus independent review.

State transitions fail when their required evidence is absent. This is the
primary workflow backpressure mechanism.

### Enforcement module

Provide a dependency-free command:

```text
python3 .agents/modules/enforcement/check.py
```

It validates the target repository rather than the kit distribution. It checks:

- project-configuration syntax and supported schema version;
- installed/enabled component consistency and module dependencies;
- artifact IDs, lifecycle states, and source references;
- evidence schema, requirement coverage, check results, and risk-required
  review evidence;
- repository declarations when multi-repo is active;
- compliance-event schema and approval requirements when compliance is active.

The command does not execute project commands, infer that a claimed result is
true, access the network, or inspect secrets. It validates recorded consistency
and required evidence only. Support human-readable output and JSON output with
stable exit codes: success, validation failure, and invocation/configuration
error.

`scripts/validate.py` remains the distribution validator for this kit and also
checks that the catalog, optional skills, modules, templates, and test fixtures
are internally coherent. It is not replaced by the installed enforcement
command.

### Multi-repo module

The `repositories` configuration assigns each checkout a stable logical ID,
path expression, and optional role. Before planning or execution, resolve only
declared paths, verify that each checkout exists and is a Git repository, and
record its base revision.

When enabled:

- plans map design surfaces and verification to repository IDs;
- tasks contain exactly one primary repository and may declare cross-repo
  dependencies or integration evidence;
- implementation changes one assigned repository at a time unless explicit
  isolation and ownership are established;
- reviews fix base/head scope independently for every repository;
- evidence records requirement and check coverage per repository.

The module coordinates existing checkouts only. Missing paths, unresolved
environment placeholders, dirty conflicting worktrees, or ambiguous ownership
block execution rather than triggering clone, checkout, reset, or cleanup.

### Compliance module

Add `audit.jsonl` under the selected change evidence directory when compliance
is active. Each append-only-by-convention event contains:

- schema version, event ID, timestamp, and change ID;
- declared actor and role;
- action and prior/new lifecycle state when applicable;
- authoritative source and evidence references;
- approval role/reference when required;
- affected repository revisions.

`.agents/project.md` contains a compact approval policy mapping risk or action
to required declared roles. The enforcement checker validates event ordering,
required fields, referenced evidence, allowed state transitions, and approval
presence. Git history supplies reviewable provenance; documentation explicitly
states that actor identity is declared, the log remains editable, and no
cryptographic or legal guarantee is provided.

The module never sends events externally and never records credentials or raw
secret-bearing command output.

### Core workflow refinements

Update the engineering contract, skills, templates, and guide without merging
artifact responsibilities:

- specs record authoritative source and confirmed rationale; unknown rationale
  remains explicitly unknown;
- plans distinguish repository facts, confirmed constraints, assumptions, and
  design choices;
- task graphs record review/integration capacity and do not schedule more work
  than can be reviewed;
- `implement` documents three selectable topologies: primary agent, fresh
  implementer per task, and implementer plus fresh validator; the user chooses
  once for a planned execution unless project configuration already contains an
  approved preference;
- `implement` retains short edit-run-observe loops but gains no unattended
  execution policy;
- the testing reference defines stable public seams, vertical test slices, and
  tautological, implementation-coupled, and horizontal-slicing anti-patterns;
- handoffs add objective last progress, provider limits consumed when known,
  reason for stopping, and next safe action;
- `review` selects applicable quality signals: correctness, security,
  compatibility, maintainability, performance, accessibility, observability,
  cost, and understandability;
- recurring agent failures produce deterministic tests, analyzers, or checks
  where possible; new prose rules name their motivating failure and require
  human approval.

### Compatibility and rollout

Existing repositories with the seven-skill installation remain valid inputs.
On the first v1 update they have no ownership manifest, so the installer treats
existing content as unowned: identical content can be reported as adoptable,
while differences require an explicit decision. No file is removed merely
because a profile no longer selects it.

The source repository migrates its validator from the fixed `EXPECTED` set to
the catalog. README badges, skill counts, installation examples, and behavioral
scenarios are updated together. The installer exposes a `full` profile as a
convenience while preserving individual interactive and `--with` selection.

### Security and privacy boundaries

- No external Python package, network call, credential manager, or provider API
  is introduced.
- Paths are normalized before use; managed writes remain within the declared
  target repository except read-only checks of explicitly declared multi-repo
  paths during normal exclusive execution.
- The installer rejects observed symlinks and path traversal and revalidates
  managed paths before mutation. It does not claim race-free confinement
  against another process that modifies the filesystem concurrently.
- Manifests contain paths, component names, versions, and hashes only.
- Project configuration, evidence, and audit schemas prohibit secrets and warn
  against storing raw command output.
- Replace decisions are explicit and visible before the transaction begins.
- The enforcement checker is read-only.

### Failure handling and recovery

- Invalid catalog, unknown component, dependency cycle, malformed project
  configuration, or unsafe path fails before writes.
- Interactive cancellation performs no writes.
- Non-interactive conflicts return a stable non-zero code and list all
  unresolved paths.
- Transaction failure restores prior destinations and leaves diagnostic output;
  the ownership manifest is written only after success.
- Kept conflicts remain user-owned and are excluded from future automatic
  updates.
- Missing evidence, required approval, independent review, or repository scope
  blocks state advancement without changing implementation files.

### Observability

Installer and check commands report selected profile/components, planned or
applied action per path, conflicts, dependency expansion, and final status.
Machine-readable JSON output uses stable keys so CI can consume it. Human output
never claims checks were executed by the consistency checker.

## Source coverage

| Source item | Design response |
|---|---|
| REQ-001–REQ-007 | Preserve six core skills and refine their contracts, templates, conditional module loading, evidence, and review behavior. |
| REQ-008 | Keep `create-skill` as a default-installed utility while retaining opt-in invocation. |
| REQ-009, REQ-028, REQ-029 | Add optional `domain-model` with lazy glossary creation and the three-condition ADR gate. |
| REQ-010 | Add default-installed `setup` and `.agents/project.md` schema with preview and approval. |
| REQ-011 | Add default-installed non-mutating `ask-kit` router over installed capabilities. |
| REQ-012–REQ-014 | Catalog-driven installer, ownership manifest, transaction model, and expanded source validator. |
| REQ-015 | Preserve the one-question human decision protocol in the contract and all decision-making skills. |
| REQ-016 | Keep risk levels, require user confirmation for medium/high/ambiguous classification, and enforce independent high-risk review. |
| REQ-017–REQ-018 | Evidence schema and enforcement checks block unsupported completion and preserve real artifact chains. |
| REQ-019 | Standard-library implementation, canonical paths, capability contracts, and no provider adapters. |
| REQ-020 | Add source/rationale provenance and explicit fact/constraint/assumption/inference distinctions. |
| REQ-021 | Add the concise change contract to evidence and implementation/review outputs. |
| REQ-022 | Add selectable quality signals to planning, evidence, and review. |
| REQ-023–REQ-024 | Risk-required evidence, early checks, review-capacity metadata, and WIP backpressure. |
| REQ-025 | Expand handoff and evidence schemas; unknown runtime budget is recorded as `not-tracked`, not inferred. |
| REQ-026 | Add harness-improvement rule and executable regression coverage for recurrent failures. |
| REQ-027 | Add baseline evaluation guidance and scenarios for no-kit, current-kit, and v1 comparisons. |
| REQ-030 | Expand the existing testing reference without adding a TDD skill. |
| REQ-031 | Implement `evidence` module and versionable `evidence/<change>/` schema. |
| REQ-032 | Implement target-side `enforcement` command plus CI-oriented JSON output and exit codes. |
| REQ-033 | Implement checkout-coordination `multi-repo` module without repository lifecycle management. |
| REQ-034 | Implement Git-versioned `compliance` event log and approval-policy validation with explicit guarantee limits. |
| REQ-035 | Add a concise AGENTS-only bootstrap index, source precedence, validation distinction, and lazy loading rules without duplicating the catalog. |
| REQ-036 | Make recognized configured specs/work roots authoritative in the four core artifact consumers with conventional fallbacks. |

## Verification strategy

Use only the Python standard library. Add executable `unittest` coverage for:

- catalog parsing, profile expansion, individual selection, dependencies, and
  dependency-cycle rejection;
- TTY menu choices and equivalent non-interactive arguments;
- clean install, default install, full install, dry-run, and idempotent rerun;
- initial unowned content, managed unchanged content, user-modified content,
  keep/replace/abort decisions, and compatibility alias behavior;
- traversal and symlink rejection;
- transactional rollback under an injected copy/write failure;
- `AGENTS.md` preservation and managed update behavior;
- valid, absent, malformed, unsupported, and secret-like project configuration;
- enabled-but-missing modules and compliance dependency resolution;
- evidence completeness at low, medium, and high risk;
- failed/skipped checks, missing independent high-risk review, and invalid
  lifecycle advancement;
- single- and multi-repository scope, missing checkouts, unresolved environment
  placeholders, and per-repo evidence coverage;
- audit-event schema, ordering, references, and approval-policy requirements;
- human and JSON enforcement output plus stable exit codes.

Extend `tests/scenarios.md` for agent behavior involving setup, routing, domain
language, provenance, WIP backpressure, implementation topology, module
loading, evidence, audit, multi-repository work, an AGENTS-only session
bootstrap, and configured-root fallback/override behavior. Add deterministic
entrypoint tests that derive canonical paths from the catalog and reject copied
profile/detail tables in `AGENTS.md`.

Required verification commands:

```text
python3 -m unittest discover
python3 scripts/validate.py
python3 .agents/modules/enforcement/check.py --root .
```

The third command applies whenever the enforcement module is installed; its
project-specific extensions require recognized configuration and enablement.
Run installer tests exclusively against temporary Git repositories; never use a
real external project as a destructive test target.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Installer overwrites project-owned content | Ownership hashes, complete preflight, explicit conflict decisions, managed-path boundary, transaction rollback. |
| Optional behavior bloats every skill | Separate modules, conditional loading, concise core integration points, catalog-driven discovery. |
| Configuration becomes a second complex framework | One constrained project file, JSON-compatible values, no arbitrary code, optional absence supported. |
| Evidence records claims rather than reality | Label observed vs declared data, reference external output, never execute or certify checks in the consistency checker. |
| Audit language overstates guarantees | Explicitly declare actors as unauthenticated and Git history as provenance, not immutable or legally certified audit. |
| Multi-repo support causes unsafe Git operations | Coordinate existing declared checkouts only; block on missing, dirty, or ambiguous state; no clone/reset/checkout automation. |
| Module dependencies drift | Canonical catalog, dependency expansion, source validation, target enforcement, executable tests. |
| Documentation and installation counts diverge | Derive validation from catalog and test every documented profile. |
| Broad v1 scope delays reliable core | Implement by independently verifiable vertical capabilities and keep optional modules isolated from the default runtime path. |

## Open questions

None.

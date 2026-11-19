---
schema_version: 2
id: "SPEC-002"
type: "specification"
sources: ["confirmed user request for structured harness, artifact formats, and contribution rules","Conventional Commits 1.0.0","Git SubmittingPatches and Pro Git contribution guidance","Google Engineering Practices for CL descriptions, small changes, and review comments","GitHub guidance for reviewable pull requests and templates","Agent Skills progressive-disclosure guidance","Michael Nygard architecture decision records","JSON Schema 2020-12","reusable patterns audited from unh-susoa-specs"]
status: "implemented"
depends_on: ["SPEC-001"]
---

# Agentic SDLC Kit v2 harness architecture

## Context

Agentic SDLC Kit v1 provides a verified workflow, installer, validators, skills,
and optional assurance modules. Its artifact contracts are nevertheless spread
across skill assets, module schemas, prose, and two large validators. It also
lacks a portable contribution workflow for branches, commits, pull requests,
and review conversations.

The v2 change is a deliberate major-version redesign. No external project has
installed v1, so v2 does not need permanent legacy readers or an automatic v1
migration path. Existing repository content and user changes must still be
preserved while this repository migrates.

## Confirmed rationale

- Keep Agent Skills self-contained and progressively disclosed rather than
  centralizing all templates.
- Give humans and validators one declarative map of artifact contracts.
- Use Markdown for deliberative records and JSON Schema for machine records.
- Make contribution rules adapt to the target repository instead of imposing a
  release convention globally.
- Keep small, low-risk work on a direct path; the artifact lifecycle must not
  turn the SDLC into a mandatory pipeline.
- Treat a verified spec as closed historical alignment evidence. Current code,
  tests, and executable contracts remain the implementation truth afterward.

## Outcome

Release a clean Agentic SDLC Kit 2.0.0 architecture with indexed, versioned
artifact contracts; uniform minimal Markdown metadata; coherent type-specific
lifecycles; a project JSON schema; contribution and review-comment guidance;
and catalog-driven validation that reduces duplicated structural knowledge.

## Actors and scenarios

- **Developer:** selects the smallest safe route, creates only useful artifacts,
  and prepares reviewable contributions that follow the target repository.
- **Coding agent:** discovers artifact and contribution contracts on demand and
  never invents missing repository policy.
- **Reviewer:** receives focused pull requests and writes clearly classified,
  actionable comments.
- **Maintainer:** evolves templates and schemas from one declared authority and
  detects drift deterministically.
- **Existing kit contributor:** retains uncommitted or project-owned changes
  during the v2 restructuring.

## Scope

### In scope

- Separate machine-readable catalogs for distribution and artifacts.
- One non-authoritative human index organized by intent.
- A canonical `.agents/project.json` validated by JSON Schema.
- Minimal shared frontmatter for every generated Markdown artifact.
- Type-specific lifecycles and qualified cross-artifact references.
- A default-installed `contribute` utility.
- Pull-request preparation and review-comment conventions.
- Catalog/schema-driven installer and validators.
- Manifest and kit schema version 2.
- Migration of this repository's current artifacts and tests.
- Existing confirmed communication and source-documentation rules.

### Out of scope

- A vault, DeepWiki, Ralph, or organization-specific knowledge layer.
- Centralizing skill assets outside their owning skill or module.
- GitHub-, GitLab-, or provider-specific APIs in the portable core.
- Automatic push, pull-request publication, comment publication, merge, release,
  force-push, or branch deletion.
- Mandatory Conventional Commits when the target repository does not require it.
- Universal limits for lines, files, commits, approvals, coverage, or review
  duration.
- Permanent v1 configuration or manifest compatibility for external projects.
- Treating Git history or audit JSONL as cryptographic or legal proof.

## Requirements

### Harness structure and authorities

**REQ-001**: Skills and modules must retain their own `SKILL.md` or `MODULE.md`
and co-located conditional `assets`, `references`, and `scripts`.

**REQ-002**: `.agents/kit-catalog.json` must remain the authority for skills,
modules, profiles, and module dependencies.

**REQ-003**: `.agents/artifact-catalog.json` must be the authority mapping each
artifact type to its contract owner, format, template, schema, lifecycle,
location policy, split policy, and supported schema version.

**REQ-004**: `.agents/indexes/by-intent.md` must provide a concise,
non-authoritative navigation view that links to canonical contracts without
copying their rules or state.

**REQ-005**: `AGENTS.md` must remain the automatically loaded behavioral and
precedence contract and point to the two catalogs and intent index without
becoming a complete catalog itself.

**REQ-006**: Catalog pointers must resolve in the source distribution. In an
installed target, artifact availability must depend on physical presence of its
owner and, for modules, required enablement and configuration.

### Common artifact format

**REQ-007**: Every generated Markdown artifact must use frontmatter containing
`schema_version`, immutable `id`, closed `type`, and non-empty `sources`; it must
include `status` only when its artifact type owns a lifecycle.

**REQ-008**: The Markdown H1 must carry the human title. Author and file update
time must be derived from Git unless a date has domain meaning for the artifact.

**REQ-009**: Machine-readable configuration, catalogs, evidence, policies, and
audit events must use JSON or JSONL with versioned JSON Schema 2020-12 contracts.
Closed records must reject unknown fields and duplicate keys.

**REQ-010**: Templates must remain beside their owning skill or module. The
artifact catalog points to them and must not duplicate their body structure.

**REQ-011**: Human-readable indexes must be generated or deterministically
validated against canonical metadata and must not become a second source of
status or ownership.

### IDs, references, and splitting

**REQ-012**: Requirements, acceptance criteria, and tasks may use readable local
IDs such as `REQ-001`, `AC-001`, and `TASK-001` inside their parent artifact.

**REQ-013**: Every external reference to a local item must be qualified by its
parent, such as `SPEC-002#REQ-001` or `PLAN-002#TASK-001`.

**REQ-014**: Parent artifact IDs must be globally unique and immutable. Local
IDs must be unique within their parent; issued IDs must not be renumbered or
reused.

**REQ-015**: A cohesive artifact remains one file. Split it only when fragments
are genuinely independent or when a large document needs navigational help;
size thresholds are warnings rather than universal gates.

**REQ-016**: Split artifacts must have one lifecycle-owning overview and
children that reference their parent without duplicating lifecycle state.

**REQ-017**: New machine-consumed interfaces should use their native contract
format, such as OpenAPI, AsyncAPI, or JSON Schema, when a real consumer exists;
no empty companion artifact may be created speculatively.

### Type-specific lifecycles

**REQ-018**: A spec lifecycle must be `draft -> approved -> implemented ->
verified`. `verified` is terminal: the spec becomes closed historical evidence
and must not be amended for later product changes.

**REQ-019**: Whether approved intent is planned must be derived from an approved
plan whose recorded source revision or digest matches the current source; it
must not be persisted as a spec state.

**REQ-020**: A plan lifecycle must support `draft`, `approved`, `stale`, and
`implemented`, with stale derived when its source revision no longer matches.

**REQ-021**: Task states must remain `blocked`, `ready`, `in-progress`, `done`,
and `stale`; task state remains authoritative in the task graph.

**REQ-022**: An ADR lifecycle must be `proposed -> accepted -> deprecated |
superseded`. A superseded ADR remains present and references its replacement.

**REQ-023**: A glossary lifecycle must support `draft`, `active`, and
`archived`; evidence must retain `in-progress`, `blocked`, and `complete`.

**REQ-024**: Review must use a verdict rather than a second lifecycle. Handoff
must be an operational snapshot without lifecycle state.

**REQ-025**: Small, clear, reversible, low-risk work must continue to use the
direct path without a spec, plan, task graph, or durable evidence unless policy
requires one.

**REQ-026**: Partial and controlled paths must continue to select only the gates
required by ambiguity, durability, coordination, and risk.

### Project configuration v2

**REQ-027**: `.agents/project.json` must be the only canonical project
configuration written by v2 and must validate against
`.agents/skills/setup/assets/project.schema.json`.

**REQ-028**: Project configuration must retain roots, repositories, enabled
modules, review and agent preferences, tracker metadata, and approval policy as
closed, versioned fields without secrets.

**REQ-029**: The setup utility must inspect, preview, and request exact approval
before creating or modifying `project.json`.

**REQ-030**: No permanent reader or writer for `.agents/project.md` is required.
If encountered, v2 must report it as unsupported rather than silently interpret
or overwrite it.

### Review and evidence

**REQ-031**: Without the evidence module, `review.md` must be a standalone report
containing fixed scope, reviewer participation, checks, findings, acceptance
gaps, residual risks, and verdict.

**REQ-032**: With evidence active, `evidence.json` must own machine-readable
scope, participation, checks, and coverage; `review.md` must contain findings,
acceptance gaps, residual risks, verdict rationale, and a reference to evidence
without copying its records.

**REQ-033**: The artifact catalog must declare the standalone and evidence-backed
review variants and their activation condition.

### Contribution workflow

**REQ-034**: A default-installed `contribute` utility must handle author-side
branch preparation, coherent staging and commits, pull-request drafts, and
responses to review feedback without becoming an implementation or review gate.

**REQ-035**: Contribution policy precedence must be: explicit repository
instructions; executable hooks/lint/CI; contribution and PR templates plus merge
strategy; consistent relevant history; then the kit fallback.

**REQ-036**: A conflict between explicit policy and executable checks must stop
the contribution workflow. The skill must never bypass hooks or weaken checks.

**REQ-037**: The fallback commit format must use a concrete, standalone,
imperative subject and an optional body separated by a blank line that explains
material what and why rather than narrating the diff.

**REQ-038**: Conventional Commits must never be the kit fallback. It must be
used only when explicit repository policy or executable tooling requires it.

**REQ-039**: Each commit must be one coherent logical change, exclude unrelated
work, include closely related tests, and pass staged-diff inspection and
applicable checks. No fixed task-to-commit ratio may be imposed.

**REQ-040**: Branch names must follow repository policy. Without one, the skill
must propose a descriptive valid Git ref without inventing a type prefix or
issue ID.

**REQ-041**: Pull-request drafts must respect local templates and include the
purpose and why, major change, scope, authoritative context, applicable risks
and operational impact, observed and omitted checks, requested feedback, and
review order when useful.

**REQ-042**: Pull requests must be conceptually focused on one self-contained
purpose and include related tests; size must not be approved or rejected from a
universal line/file/commit threshold.

**REQ-043**: The skill may inspect and prepare without additional approval. It
may create a commit only when the user requested it. Push, opening or editing a
pull request, and publishing a review response require explicit approval for
that action.

**REQ-044**: The portable core must not depend on `gh`, provider APIs, remote
branch protection, or authenticated review state. It may prepare provider-neutral
drafts or consume normalized data from a separately accepted adapter.

### Review comments

**REQ-045**: The review skill must keep impact severity separate from comment
disposition. Dispositions must be `Required`, `Optional`, `Nit`, `Question`, and
`FYI`.

**REQ-046**: A review comment must address the code rather than the person, be
respectful, specific, and actionable, and explain reason and impact when not
obvious. It should contain one problem per comment.

**REQ-047**: `Nit`, `Optional`, `Question`, or `FYI` comments must not alone
produce `changes-required`. A required material defect may block according to
its demonstrated impact.

**REQ-048**: Responses to feedback must state the change and evidence, ask when
a comment is unclear, or provide a reasoned technical disagreement. A thread
must not be marked resolved before the issue is actually addressed under local
policy.

### Communication and source documentation

**REQ-049**: Agent questions and explanations must be self-contained, direct,
unambiguous, friendly, and respectful; necessary jargon must be defined, and a
materially ambiguous interpretation must be confirmed rather than guessed.

**REQ-050**: Externally consumed APIs and user/operator entry points must use the
repository's canonical documentation format or an established ecosystem
convention and cover applicable purpose, inputs, outputs, failures, side
effects, constraints, invocation, environment, and exit behavior.

**REQ-051**: Internal source comments must preserve only confirmed non-obvious
rationale or invariants, not narrate obvious code or invent intent. Generated
and vendored outputs must not be edited in place.

### Validation and release

**REQ-052**: The source validator and installed checker must consume artifact
catalog and JSON schemas for structural rules. Code must retain semantic checks
that cannot be expressed clearly or safely as schema assertions.

**REQ-053**: The installer and source validator may share a source-only catalog
contract implementation. The installed checker must remain self-contained,
read-only, standard-library-only, and independent from source scripts.

**REQ-054**: Structural contract knowledge must not be reimplemented as three
independent hardcoded field/path lists. Equivalence tests must compare source and
installed validation decisions for shared records.

**REQ-055**: The installer must write kit and manifest schema version 2, manage
the artifact catalog and intent index atomically, and preserve unknown or
project-owned content through explicit conflicts.

**REQ-056**: V2 need not read or migrate v1 project configuration or manifests
for external installations because none exist. It must migrate this source
repository's own artifacts and fail clearly on unsupported legacy files.

**REQ-057**: Source validation must verify catalog pointers, owner boundaries,
template/schema compatibility, lifecycle definitions, qualified references,
index consistency, contribution-script read-only behavior, and absence of
provider coupling.

**REQ-058**: The installed checker must validate project config, artifact graph,
lifecycle evidence, qualified references, and enabled module extensions without
executing project code, Git mutations, network requests, or contribution
actions.

**REQ-059**: The release must identify itself as `2.0.0`, and all public counts,
profiles, templates, examples, schemas, manifests, and evidence must agree with
that version.

## Business rules

- Code, tests, and executable contracts are current implementation truth.
- A spec is temporary alignment authority only while its accepted change is
  active; verified specs are immutable historical records.
- No workflow gate is created merely because an artifact type exists.
- Every artifact has one contract owner and every status has one authority.
- Human indexes point to canonical metadata and never own mutable state.
- Repository policy overrides kit fallbacks but cannot weaken non-negotiable
  safety or evidence requirements.
- Semantic qualities such as atomicity, reviewability, clarity, and courtesy are
  assessed with evidence and judgment, not simplistic numeric gates.
- User-owned and uncommitted changes must be preserved throughout the v2
  migration.

## Failure behavior and edge cases

- Missing or invalid catalogs, schemas, templates, or owner pointers fail source
  validation before installation.
- An unsupported `.agents/project.md` or v1 manifest is reported clearly and is
  never converted or overwritten silently.
- Duplicate parent IDs or local IDs fail validation; an unqualified external
  reference is rejected with its expected qualified form.
- A plan whose source revision changed becomes stale; it does not mutate the
  source spec.
- A verified spec containing material placeholders or later edits fails
  validation.
- A contribution policy conflict, failed hook, unrelated staged change, invalid
  branch, unresolved placeholder, or unobserved required check blocks the
  corresponding action.
- Lack of provider authentication returns a draft or explicit blocked action;
  it never causes credential discovery or guessed identity.
- Review comments without location, evidence, impact, or disposition remain
  findings in the report rather than being published as authoritative feedback.

## Quality constraints

- Default startup context remains limited to AGENTS and installed skill metadata.
- Indexes and catalogs stay compact and load only when relevant.
- No new runtime service, background process, vector store, or orchestration
  framework is introduced.
- The portable runtime remains provider-neutral and uses no external network.
- JSON schemas declare their dialect and stable versioned IDs.
- Validators provide deterministic, redacted, actionable errors and no traceback
  for malformed input.
- The source checkout and default/full temporary installations are reproducibly
  testable using the Python standard library.

## Dependencies and confirmed constraints

- Python 3 and Git remain the only required local executables.
- Existing skill/module resources stay co-located with their owners.
- V1 has no external installations requiring backward compatibility.
- Existing local communication and source-documentation changes are preserved
  and incorporated.
- External publication always remains an explicit user action.

## Acceptance criteria

**AC-001**: A source validation command proves that both catalogs, all owner
pointers, templates, schemas, indexes, and public documentation agree with
version 2.0.0.

**AC-002**: A default install contains the declared core and utility skills,
including `contribute`, both catalogs, the intent index, AGENTS, and a v2
ownership manifest, without creating project configuration or optional modules.

**AC-003**: A full install contains every declared skill and module; its installed
checker validates the empty target without source-only scripts.

**AC-004**: `setup` creates only a schema-valid `project.json` after exact preview
and approval, and rejects unsupported `project.md` without modifying it.

**AC-005**: Every generated Markdown template validates against the common
frontmatter contract and its type-specific lifecycle.

**AC-006**: Two specs may each contain `REQ-001`, and two plans may each contain
`TASK-001`, while qualified external references resolve without collision.

**AC-007**: An approved plan with a matching source revision derives a planned
relationship; a changed source revision makes only the plan and affected tasks
stale.

**AC-008**: A verified spec cannot be amended and does not override current code,
tests, or executable contracts.

**AC-009**: Review works standalone without evidence and produces a reduced,
linked report without duplicated machine fields when evidence is active.

**AC-010**: Contribution fixtures cover a repository with no convention, a
classic-message convention, required Conventional Commits, failing hooks,
invalid branch names, unrelated staged work, local PR templates, squash-title
policy, omitted checks, and unauthorized external actions.

**AC-011**: Pull-request drafts contain the required contextual and verification
sections without imposing a provider-specific file or API.

**AC-012**: Review-comment scenarios prove independent impact severity and
comment disposition, actionable wording, non-blocking nits, reasoned responses,
and correct resolution behavior.

**AC-013**: Source and installed validators make equivalent accept/reject
decisions for shared project, evidence, audit, artifact-reference, and lifecycle
fixtures.

**AC-014**: Structural mutation tests fail when an artifact owner, template,
schema, root, lifecycle, index entry, profile, version, or contribution contract
drifts.

**AC-015**: The current repository's v2 spec, plan, task, handoff, review, ADR,
glossary, project-config examples, evidence, and audit fixtures validate in their
new formats.

**AC-016**: The full regression suite, source validator, installed checker,
default/full installation smoke, read-only contribution checker, and diff checks
all pass with no untracked migration output.

## Open questions

None.

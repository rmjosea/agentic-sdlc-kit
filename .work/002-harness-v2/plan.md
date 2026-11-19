---
schema_version: 2
id: "PLAN-002"
type: "plan"
sources: ["SPEC-002"]
source_revisions: {"SPEC-002":{"source_revision":"sha256:8d411302e1f1fe44028e6110820bc35b5ce777676e1e044a0c905dc6ab4f1626","source_items":"source-items.json"}}
status: "implemented"
risk: "high"
risk_rationale: "The redesign changes every writable artifact contract, project configuration, installation ownership, contribution workflow, and both source and installed validators."
---

# Agentic SDLC Kit v2 implementation plan

## Goal and source intent

Implement approved SPEC-002 as a clean Agentic SDLC Kit 2.0.0 redesign. Keep
the proportional route selection and self-contained Agent Skills from v1 while
making artifact formats, contribution behavior, and validation authorities
explicit, versioned, and machine-readable.

No external v1 installation exists. V2 therefore rejects v1 project config and
manifest rather than carrying permanent migration code. The three committed v1
historical acceptance files in this source repository remain byte-for-byte
immutable and are handled only by source-test exceptions.

## Repository findings and facts

- V1 is verified at SPEC-001 with durable evidence and 196 current tests.
- The user confirmed that no other project has installed v1.
- Skills and modules already co-locate their resources correctly.
- `kit-catalog.json` governs distribution but does not describe artifact types.
- Artifact owner, template, schema, lifecycle, root, and split rules are spread
  across AGENTS, skills, modules, docs, and Python constants.
- `scripts/validate.py` and the installed checker duplicate project, catalog,
  artifact, evidence, and compliance structural knowledge.
- Markdown artifacts use inconsistent metadata and parsing conventions.
- Review and evidence duplicate machine facts when evidence is active.
- No portable capability owns branch, commit, pull-request, or review-response
  preparation.
- Existing communication and source-documentation rules are committed on the v2
  branch and form part of SPEC-002.
- The SOA harness demonstrates useful intent indexes, source-of-truth links, and
  load-on-demand patterns. Its vault, Ralph, central templates, language tiers,
  path-derived identities, and commitlint assumptions are not portable.

## Confirmed constraints

- Kit release: `2.0.0`; kit catalog schema 2; manifest schema 2.
- Python 3 and Git are the only required executables.
- No third-party Python runtime dependency is introduced.
- The installed checker remains standard-library-only, read-only, offline, and
  independent from source-only scripts.
- Skill and module resources remain co-located with their contract owner.
- `.agents/project.json` is the only v2 project configuration.
- V1 `project.md` and manifest are unsupported and never silently parsed.
- Verified v1 historical files remain unchanged.
- No provider API, automatic push, PR/comment publication, merge, release,
  force-push, or branch deletion enters the portable core.
- Conventional Commits is never the fallback; it is honored only when explicit
  policy or executable tooling requires it.
- Risk is high and final approval requires a fresh independent reviewer plus
  recovery evidence.

## Assumptions

- Local Git inspection is available without provider authentication.
- Repository contribution policy may be unavailable; classic Git fallback must
  therefore produce complete offline drafts.
- The existing bounded JSON Schema evaluator can be made explicit and shared as
  data-driven behavior without claiming full JSON Schema 2020-12 support.
- Semantic qualities such as conceptual atomicity and respectful wording remain
  agent/reviewer judgments exercised by scenarios, not regex gates.

## Agent inferences

- A separate artifact catalog is clearer than adding artifacts to distribution
  profiles.
- Splitting only the source validator and enforcement checker by responsibility
  will reduce review cost; splitting the mature installer transaction now would
  add risk without satisfying a distinct requirement.
- A single `contribute` skill is more coherent than branch, commit, PR, and
  feedback micro-skills because all share policy discovery and action approval.

## Unknowns

Provider-side PR state, protected branches, authenticated identities, required
remote reviews, and actual merge strategy may be unavailable locally. The skill
must report those values as unknown unless repository evidence confirms them.

## Confirmed technical decisions and rationale

| Decision | Material rationale | Source |
|---|---|---|
| Separate artifact catalog | Distribution and artifact contracts have different owners and evolution | SPEC-002; architecture review |
| Co-locate owner resources | Preserves Agent Skills progressive disclosure | Agent Skills guidance |
| Use project.json only | Removes the custom Markdown parser for machine configuration | User decision |
| Qualify cross-artifact IDs | Prevents local REQ/TASK collisions without noisy headings | User decision |
| Derive planned from semantic source revision | Avoids duplicating a relationship in spec lifecycle | User decision |
| Make verified spec terminal | Code, tests, and executable contracts become current truth | User decision |
| Use two review variants | Keeps evidence opt-in without duplicate machine facts | User decision |
| Add contribute as default utility | Loads contribution behavior only when relevant | User decision |
| Use classic fallback | Respects target policy and avoids imposing release semantics | User decision |
| Make a clean v2 break | No external v1 consumers exist | User confirmation |
| Keep installer transaction in one module | Existing transaction behavior is mature; only manifest/global inputs change | Independent plan review |
| Use source-only exact v1 fixture exceptions | Preserves verified history without shipping general v1 compatibility | Independent plan review |

## Design summary

### 1. Authority and directory model

```text
.agents/
├── kit-catalog.json
├── artifact-catalog.json
├── indexes/by-intent.md
├── schemas/
│   ├── kit-catalog.schema.json
│   ├── artifact-catalog.schema.json
│   ├── manifest.schema.json
│   └── markdown-document.schema.json
├── tools/check_artifact_ids.py
├── tools/fingerprint_artifact.py
├── skills/<owner>/{SKILL.md,assets,references,scripts}
├── modules/<owner>/{MODULE.md,assets,lib}
├── project.json                  # target only; project-owned
└── agentic-sdlc-kit.json        # target only; installer-generated
```

Authority order:

1. `AGENTS.md`: behavior, risk, precedence, and route boundaries.
2. `kit-catalog.json`: skills, modules, profiles, dependencies, global files.
3. `artifact-catalog.json`: artifact contracts and owner pointers.
4. Owner `SKILL.md`/`MODULE.md`: procedures and semantics.
5. Owner template/schema: materialized shape.
6. `project.json`: project-owned configuration values.
7. Installer manifest: installation ownership.
8. Generated artifact: project-owned instance state.
9. Code, tests, and executable contracts: current implementation truth.

`indexes/by-intent.md` is a validated navigation view, never an authority. AGENTS
points to it instead of copying artifact or contribution details.

### 2. Distribution catalog and global schemas

Upgrade `kit-catalog.json` to schema 2 and `kit_version: 2.0.0`. It declares:

- six core skills;
- default utilities: `create-skill`, `setup`, `ask-kit`, `contribute`;
- optional `domain-model`;
- the four v1 assurance modules and dependencies;
- individually managed global files;
- default and full profiles.

`kit-catalog.schema.json` validates the catalog. `artifact-catalog.schema.json`
validates artifact metadata. `manifest.schema.json` validates installed
ownership. `markdown-document.schema.json` validates the common normalized
Markdown model.

Installer and source validator share source-only parsers in
`scripts/contracts/catalog.py`. The installed checker has a local parser and is
compared through differential fixtures rather than importing source code.

### 3. Implementable Markdown grammar

V2 frontmatter is a strict YAML-compatible subset where every value is valid JSON
on one line:

```markdown
---
schema_version: 2
id: "SPEC-002"
type: "specification"
sources: ["confirmed-request"]
status: "approved"
---
```

Rules:

- one `key: JSON-value` per line;
- no multiline values, YAML lists/maps, aliases, tags, implicit strings, or
  comments;
- duplicate and unknown keys rejected;
- UTF-8 only;
- exact opening/closing delimiters;
- Markdown body begins with one H1.

The H1 is the human title. General artifacts do not store author or updated time;
Git supplies them. ADRs retain a decision `date` and handoffs retain
`snapshot_at` because those timestamps have artifact semantics. No other type
adds dates without a declared consumer.

The parser normalizes each document to:

```json
{
  "metadata": {},
  "h1": "...",
  "sections": ["..."],
  "local_ids": [{"kind":"requirement","id":"REQ-001"}],
  "references": ["SPEC-002#REQ-001"],
  "placeholders": []
}
```

JSON Schema validates this normalized model, not raw Markdown. Python extracts
H1, sections, local IDs, references, and placeholders and performs semantic
checks.

Schemas compose only through absolute versioned URN `$ref` values loaded into a
safe registry from catalog-declared source files. No owner schema mirrors common
fields and no project-owned URI or path can load code or remote content.

Supported JSON Schema keyword profile:

- `$schema`, `$id`, `$defs`, `$ref` to loaded URNs;
- `type`, `properties`, `required`, `additionalProperties`;
- `const`, `enum`, `oneOf`, `anyOf`, `allOf`, `not`;
- `if`, `then`, `else`;
- `items`, `minItems`, `maxItems`, `uniqueItems`;
- `pattern`, `minLength`, `maxLength`, `minimum`, `maximum`.

The evaluator rejects unsupported keywords rather than ignoring them. Date and
date-time formats remain semantic Python checks.

Template mode permits declared placeholder tokens. Rendered mode rejects raw
placeholders. Approved or terminal artifacts additionally reject `TODO`,
documented clarification markers, and incomplete required sections.

### 4. Complete artifact catalog contract

Each entry has exact fields:

```json
{
  "id": "specification",
  "format": "markdown",
  "owner": {"kind": "skill", "name": "write-spec"},
  "template": "skills/write-spec/assets/spec.template.md",
  "schema": "skills/write-spec/assets/spec.schema.json",
  "lifecycle": "spec-v2",
  "root": {"mode": "project", "key": "specs", "fallback": "specs"},
  "path_patterns": ["<root>/<NNN-slug>/spec.md"],
  "split": {"mode": "semantic", "warning_tokens": 3000},
  "writable_schema_version": 2,
  "requires_modules": [],
  "variants": []
}
```

`warning_tokens` is advisory and cannot fail an artifact by itself.

Catalog entries:

| Artifact ID | Contract owner | Key behavior |
|---|---|---|
| project-config | setup | fixed `.agents/project.json`; JSON |
| specification | write-spec | lifecycle owner; specs root |
| specification-fragment | write-spec | parent required; no lifecycle |
| specification-index | write-spec | generated/validated view |
| plan | plan | plan lifecycle; work root |
| plan-fragment | plan | parent required; no lifecycle |
| source-fingerprint-map | plan | JSON companion co-located with plan |
| task-graph | decompose-tasks | artifact ID plus plan namespace |
| handoff | implement | snapshot, no lifecycle |
| review-report | review | standalone under work root; evidence variant co-located |
| domain-context | domain-model | glossary lifecycle |
| architecture-decision | domain-model | ADR lifecycle |
| evidence-record | evidence | JSON schema |
| compliance-event | compliance | JSONL event schema |
| approval-policy | setup | embedded project-config shape; compliance consumes semantics |
| pull-request-draft | contribute | chat-only by default; saved form uses work root |

`approval-policy` shape is owned by setup as part of project config. Compliance
owns only the semantics applied when enabled.

Variant activation uses closed data:

```json
{"requires_modules":["evidence"],"forbids_sections":["Scope","Reviewer role and independence","Authoritative sources","Risk","Change contract and review focus","Selected quality signals","Checks and evidence","Acceptance coverage"]}
```

Owner availability:

- Source distribution: every pointer resolves.
- Target: type-specific generation requires physical owner presence.
- Module owner generation additionally requires module enablement and required
  configuration.
- Existing project-owned artifacts whose optional owner is absent receive common
  syntax validation plus an `owner-unavailable` warning; mutation is blocked.
- Caller-selected paths must be explicit, repository-relative, non-symlink, and
  inside an allowed configured root.

PR drafts are chat output by default and therefore not a stored artifact. If the
user requests persistence, `pull-request-draft` common metadata and schema apply.

### 5. IDs, namespaces, fragments, and issuance

Parent IDs are globally unique by artifact type prefix. The task graph has its
own ID and explicit namespace:

```yaml
id: "TASKS-002"
type: "task-graph"
sources: ["PLAN-002"]
namespace: "PLAN-002"
```

Task headings remain `TASK-001`; external references remain
`PLAN-002#TASK-001`. The namespace must resolve to the graph's source plan.

Spec requirements and ACs are qualified by their spec parent. A local ID can
repeat under a different parent.

Split child contract:

```yaml
schema_version: 2
id: "SPEC-002-FRAG-001"
type: "specification-fragment"
sources: ["SPEC-002"]
parent: "SPEC-002"
fragment_id: "FRAG-001"
```

Plan fragments use `PLAN-002-FRAG-001` and `plan-fragment`. Children have no
status; the overview owns lifecycle. Parent/child links are reciprocal and child
IDs are global and immutable.

An ID becomes issued when it first appears in any reachable committed
repository revision. Current-tree validators enforce uniqueness and exactly one
task graph per plan namespace.

A global managed read-only helper,
`.agents/tools/check_artifact_ids.py`, is available independently of
`contribute`. Every artifact-writing skill invokes it before persisting a new or
renamed ID. It scans all locally reachable refs with allowlisted read-only Git
commands and compares current candidates with historical appearances, including
IDs issued and deleted before the proposed base. `contribute` reuses the same
helper for commit/PR readiness but is not itself an artifact-generation gate.

The helper reports history completeness. An unborn Git repository with no
commits and no refs is a verified empty history and may issue its first IDs. A
shallow repository, unreadable refs, or Git inspection failure makes historical
non-reuse `unverified` and blocks issuing or renaming a numeric ID; reading and
editing an already-issued current artifact remains possible. No append-only ID registry or second status authority
is added. Tests cover pre-base deletion/reuse, renumbering, duplicate task
namespaces, direct artifact creation without `contribute`, shallow history, and
one task graph per plan.

### 6. Semantic source revisions, staleness, and verified seals

A Markdown source revision is computed from one exact canonical projection:

1. decode strict UTF-8 and normalize Unicode to NFC;
2. convert CRLF/CR to LF;
3. remove trailing spaces/tabs from every line;
4. remove only leading and trailing blank lines; preserve internal blank lines,
   heading order, list order, and section order;
5. parse restricted frontmatter and exclude only `status`;
6. let `body` be the normalized Markdown after frontmatter, including the H1;
7. build exactly `{"metadata": <metadata-without-status>, "body": <body>}`;
8. serialize with UTF-8, `ensure_ascii=false`, sorted object keys, separators
   `,` and `:`, and no terminal newline;
9. hash those bytes with SHA-256 and prefix `sha256:`.

Parent/fragment relationships participate through metadata; all local items
participate through body. No second copy of H1, sections, relationships, or item
maps enters the overall projection.

A local REQ/AC item starts at its marker and ends before the next local marker or
next level-two heading, whichever comes first. Its projection is exactly
`{"parent_id":"SPEC-002","item_id":"SPEC-002#REQ-001","text":<normalized-item>}`
with the real IDs substituted and the same canonical JSON serialization. Moving
a section changes the overall revision; syntax-only frontmatter formatting and
status-only changes do not; an item unchanged by unrelated items keeps its
fingerprint.

An approved plan stores one exact per-source shape and points to an owner-local
machine companion:

```json
"source_revisions": {
  "SPEC-002": {
    "source_revision": "sha256:<overall>",
    "source_items": "source-items.json"
  }
}
```

`source-items.json` is a cataloged `source-fingerprint-map` artifact containing
`schema_version`, `source_id`, `source_revision`, and a closed
`item_revisions` object of qualified IDs to digests. PLAN-002 uses this exact
shape in its own frontmatter and carries the calculated companion.

The current planning companion was computed from that exact projection; plan
review independently recomputes it from the documented object. The
additive-contract slice then implements `.agents/tools/fingerprint_artifact.py`
with human/JSON output and makes current SPEC-002 plus `source-items.json` its
golden fixture. A mismatch makes the plan stale and blocks later slices. Parity
tests cover LF/CRLF, NFC-equivalent Unicode, trailing whitespace, internal blank
lines, section movement, status-only changes, and syntax-only frontmatter
formatting.

A status-only source transition does not change either digest. Before
implementation, an overall mismatch marks the plan `stale`. The impact map
compares item fingerprints:

- changed/removed source items mark only mapped plan rows and tasks stale;
- new source items block until mapped;
- unchanged task rows retain their state;
- no new task begins while the plan is globally stale;
- an implemented plan is historical and is not reopened by later source work;
- editing a verified spec is independently forbidden.

V2 evidence adds `source_seals` containing artifact ID, canonical overall digest,
and item fingerprints. Non-circular closure:

1. approved spec content is fingerprinted;
2. approved plan records the fingerprint;
3. implementation evidence records source seals while spec is approved;
4. spec moves to implemented; status exclusion keeps the digest stable;
5. fresh review approves the fixed implementation and source seal;
6. evidence becomes complete and spec moves to verified;
7. future validation recomputes the status-excluding digest and compares it with
   the sealed value.

Tests cover status-only transitions, one-item change, added/removed items,
unrelated tasks, stale reconciliation, implemented plans, and verified seals.

### 7. Type-specific lifecycles

Catalog lifecycle profiles:

- spec: `draft -> approved -> implemented -> verified`;
- plan: `draft -> approved`, `approved -> stale`, `stale -> approved`, and
  `approved -> implemented`;
- task: `blocked | ready | in-progress | done | stale` under graph rules;
- ADR: `proposed -> accepted`, then `deprecated` or `superseded`;
- glossary: `draft -> active -> archived`;
- evidence: `in-progress | blocked | complete`.

Review has a verdict and handoff has snapshot metadata, not lifecycle. Verified
specs cannot transition or be edited. Superseded ADRs remain and reference their
replacement; IDs are not reused.

### 8. Project JSON field contract

`.agents/skills/setup/assets/project.schema.json` owns this closed object:

```json
{
  "schema_version": 2,
  "roots": {
    "specs": "specs",
    "work": ".work",
    "adrs": null,
    "evidence": null,
    "domain_context": null
  },
  "repositories": [],
  "enabled_modules": [],
  "tracker": {"kind": "none", "location": null, "labels": {}},
  "agent": {"mode": "guided"},
  "review": {"mode": "risk-based"},
  "approval_policy": {"rules": []},
  "contribution": {
    "commit_mode": "discover",
    "base_branch": null,
    "required_trailers": [],
    "pull_request_template": null,
    "merge_strategy": "unknown"
  }
}
```

Exact nested contract:

- `roots` has exactly `specs`, `work`, `adrs`, `evidence`, and
  `domain_context`. Specs/work are non-empty safe repository-relative strings;
  the others are the same or null.
- `repositories` contains unique closed objects:

```json
{"id":"current","path":".","remote":null}
```

  `id` is unique kebab-case; `path` is `.`, a safe repository-relative path, or
  one `${UPPER_ENV}/safe/relative` form; `remote` is null or a sanitized
  single-line identifier. V1 `name` is deliberately renamed to `id`.
- `enabled_modules` contains unique module names present in the kit catalog.
- `tracker` is exactly:

```json
{"kind":"none","location":null,"labels":{}}
```

  `kind` is a non-empty slug; `location` is null when kind is none, otherwise a
  sanitized single-line string; labels is a closed string-to-string map with
  non-empty unique keys.
- `agent.mode` is `guided | autonomous-within-rules`.
- `review.mode` is `risk-based | always-independent`.
- `approval_policy.rules` preserves the confirmed v1 semantics and contains
  unique `(risk, action)` closed records:

```json
{"risk":"high","action":"verified","required_roles":[{"role":"reviewer","minimum":1}],"independent":true}
```

  risk is low/medium/high; action is a non-empty kebab-case lifecycle or
  contribution action; `required_roles` contains unique roles and is non-empty
  when a rule exists; role is a non-empty slug; minimum is integer 1..100;
  `independent` is rule-level and high-risk rules cannot set it false. Setup owns
  this shape and compliance owns enabled semantic evaluation.
- `contribution` is closed. `commit_mode` is
  `discover | classic | conventional`; `base_branch` is a valid Git ref name or
  null; `required_trailers` contains unique tokens matching
  `[A-Za-z0-9-]+`; `pull_request_template` is a safe repository-relative path or
  null; `merge_strategy` is `unknown | merge | squash | rebase`.

All project-config strings are 1..500 characters unless null is explicitly
allowed, single-line, control-character-free, and redacted in errors. IDs,
enums, trailer tokens, and paths also obey their narrower patterns. Cross-field constraints are semantic checks; shape and enums live in the
project schema.

No arbitrary regex, command, hook, plugin, or executable path can be configured.
Project JSON is an explicit repository instruction and precedes history-based
fallback. If it conflicts with a hook/linter, contribution stops and reports the
conflict.

`setup` writes only `project.json` after exact preview and recheck. Any
`project.md` produces an unsupported-v1 diagnostic and remains untouched.

### 9. Review variants and evidence ownership

Owner-local templates:

```text
review/assets/review-standalone.template.md
review/assets/review-with-evidence.template.md
```

Standalone owns fixed scope, participation, risk, quality dispositions, checks,
findings, acceptance gaps, residual risk, and verdict.

Evidence-backed owns only:

- evidence record qualified reference;
- findings;
- acceptance gaps;
- residual risks;
- verdict and rationale.

The artifact catalog declares the evidence-backed variant with
`requires_modules: ["evidence"]`. Evidence v2 owns scope, participation, risk,
change contract, nine quality-signal dispositions, checks, coverage, and source
seals. The checker rejects every catalog-declared forbidden duplicate section in
the reduced report and verifies its verdict/reference matches evidence.

A standalone saved review uses `roots.work`, falling back to `.work/`, under a
caller-selected feature directory. An evidence-backed review is co-located with
its evidence record. A saved PR draft also uses `roots.work`/`.work/`; when that
root cannot be recognized, contribute returns chat output only and does not
persist a file. Paths outside the selected root are rejected.

### 10. Contribution skill and deterministic CLI

Add default utility:

```text
.agents/skills/contribute/
├── SKILL.md
├── references/commits.md
├── references/pull-requests.md
├── references/review-responses.md
├── assets/pull-request.template.md
└── scripts/check_contribution.py
```

References load independently only for the requested action. The skill includes
positive/adjacent-negative activation scenarios, line/context budgets, source
attribution, and no duplicated guidance.

Policy precedence is exact and stops at the first authoritative level that
settles a field:

1. applicable repository instructions and project.json contribution overrides;
2. executable hook, lint, commit-message, and CI configuration;
3. contribution/PR templates and confirmed merge-strategy settings;
4. consistent relevant non-generated history as style evidence only;
5. classic kit fallback.

Machine-readable `project.json` and clearly structured executable configuration
may settle a field directly. Free-form AGENTS/CONTRIBUTING prose is never parsed
as a mandatory mode or prefix: `inspect` reports the relevant source and marks
the field `confirmation-required`. The skill interprets the prose with the user
when material, then passes the confirmed value plus its safe repository-relative
source path. The checker verifies that source exists and records it, but does not
claim its regex understood natural language.

A lower level never overrides a higher one. Contradictions within one level or
between a confirmed prose decision and executable checks block the affected
action and report both sources. A contradiction between structured project.json
policy and a clear executable check also blocks the affected action and reports
both sources; the skill must never weaken an executable check. History can
suggest style but cannot invent mandatory policy. Confirmed values without a
source, or a source with no relevant contribution text, are invalid.

The checker is read-only and has subcommands:

```text
check_contribution.py inspect --root PATH [--base-ref REF] [--expected-path PATH ...] [--format human|json]
check_contribution.py branch --root PATH --name NAME [--confirmed-branch-prefix PREFIX --policy-source PATH] [--format human|json]
check_contribution.py commit --root PATH --message-file FILE|- [--confirmed-commit-mode classic|conventional --policy-source PATH] [--base-ref REF] [--expected-path PATH ...] [--format human|json]
check_contribution.py pull-request --root PATH --draft-file FILE|- [--confirmed-commit-mode classic|conventional --policy-source PATH] [--base-ref REF] [--expected-path PATH ...] [--observations FILE|-] [--format human|json]
```

`-` reads one bounded UTF-8 input from stdin, allowing drafts without creating
repository files. `pull-request` rejects simultaneous `--draft-file -` and
`--observations -`; at most one document may consume stdin. A file argument must
be repository-relative, regular, non-symlink, and explicitly supplied. Repeated `--expected-path` values define
the intended file scope; the checker reports staged files outside it but leaves
semantic relatedness to review.

`.agents/skills/contribute/assets/observations.schema.json` defines a closed
input:

```json
{"schema_version":2,"checks":[{"name":"tests","scope":"fixed range","status":"passed","evidence_reference":"local result"}]}
```

Check status is `passed | failed | not-run`; evidence reference is string or
null. The checker never executes observations.

`.agents/skills/contribute/assets/contribution-report.schema.json` defines the
closed human-equivalent JSON report shown below. Both schemas reject duplicate
keys, unknown fields, multiline secrets, and unsafe paths.

JSON output:

```json
{
  "schema_version": 2,
  "valid": true,
  "errors": [],
  "warnings": [],
  "advice": [],
  "policy_sources": [],
  "scope": {"base_ref": null, "staged": [], "unstaged": [], "untracked": []},
  "summary": "validation passed"
}
```

Each issue contains code, path, field, and redacted message. Human output carries
the same findings. Exit codes: `0` valid, `1` policy/validation failure, `2`
invalid invocation or unsafe/uninspectable input. Output order is deterministic.

Public command contracts are maintained in the owning `SKILL.md`/`MODULE.md` and
source docstrings, with concise examples in README and the source usage guide.
For install, source validation, enforcement, artifact-ID checking, and
contribution checking, documentation states invocation, inputs, output, side
effects, environment assumptions, failure modes, and exits. Mutation tests
remove or contradict each command contract and require source validation to
fail.

Allowed Git subprocesses use argument arrays and read-only modes only:

- `git check-ref-format --branch`;
- `git status --porcelain=v1 -z`;
- `git diff --check` and `git diff --cached --check`;
- `git diff --name-only` / `--cached --name-only`;
- `git log`, `git show`, `git merge-base`, and `git rev-parse` for explicit local
  scope/history.

No hook is executed by the checker. Hook/lint files are policy evidence only.
When `contribute` executes an explicitly requested `git commit`, Git runs its
normal hooks; the skill records the observed exit/result and stops on failure.
It never claims a hook passed from static discovery.

Semantic unrelated-work and commit atomicity are reviewer/agent judgments. The
checker reports staged/unstaged/untracked scope and mismatches with explicitly
supplied expected paths; it does not infer conceptual coherence from counts.

Action boundaries:

| Action | Required authority |
|---|---|
| inspect policy/status and prepare draft | none beyond the user request |
| propose branch/message/PR/response | none beyond the user request |
| create or switch branch | exact action requested after preview |
| stage paths | exact paths requested after preview |
| create commit | exact commit requested; preview message and staged scope first |
| push | fresh explicit approval of ref/remote |
| open or edit PR | fresh explicit approval of exact title/body/base/head |
| publish review response | fresh explicit approval of exact comment/thread |
| resolve thread | fresh explicit approval and local-policy compliance |
| merge/release/force-push/delete branch | outside skill; never implied |

An initial exact command such as “commit these staged files with this message”
authorizes that commit after the skill verifies the same scope/message; a broad
“finish the change” does not. Any preview change invalidates approval.

Classic fallback: imperative standalone subject, blank line before optional
body, material what/why, no diff narration, no invented trailers. The checker
rejects closed known placeholders and reports heuristic generic wording, but
whether arbitrary natural-language wording is genuinely concrete and imperative
remains an agent/reviewer judgment rather than a claim of complete NLP. The
commonly cited 50/72 widths are advice only and never errors unless repository
policy sets limits. Conventional Commits grammar is checked only when configured or
required by observed executable policy.

PR drafts respect local templates and contain purpose, change, scope, context,
applicable risk/operations, observed and omitted checks, requested feedback, and
review order. Draft persistence is caller-selected; chat rendering writes no
artifact.

### 11. Review comments and author responses

`review/references/review-comments.md` loads only when converting findings into
comments or evaluating review responses.

Each comment separates:

- impact: `critical | high | medium | low`;
- disposition: `Required | Optional | Nit | Question | FYI`;
- evidence/location;
- reason/impact;
- smallest useful action or question.

`Optional`, `Nit`, `Question`, and `FYI` cannot independently cause
`changes-required`. A `Required` comment needs a demonstrated material defect or
missing required evidence. Courtesy, conceptual focus, and one-problem clarity
are scenario-evaluated judgments, not deterministic regex approval.

`contribute` prepares author responses: changed with evidence, clarification
request, or reasoned technical disagreement. Remote publication and thread
resolution remain separately approved actions.

### 12. Source and installed code organization

Refactor source validator only after additive contracts pass:

```text
scripts/
├── install.py
├── contracts/
│   ├── artifacts.py
│   └── catalog.py
├── validate.py
└── validation/
    ├── artifacts.py
    ├── distribution.py
    ├── documentation.py
    └── semantics.py
```

Keep installer transaction, rollback, and action model in `install.py`. Extract
only catalog/schema parsing shared with source validation. Preserve installer
CLI and exit-code behavior through contract tests.

Split enforcement internally:

```text
.agents/modules/enforcement/
├── check.py
└── lib/
    ├── artifacts.py
    ├── compliance.py
    ├── evidence.py
    ├── paths.py
    ├── project.py
    └── report.py
```

`check.py` is a small CLI. Local imports resolve only inside its installed module
package. All files are covered by read-only AST and snapshot tests. Catalogs
contain data, never executable validator entrypoints.

Schemas own structural fields/types/enums. Python owns safe parsing, paths,
digests, graph references, cycles, staleness, coverage, task readiness,
independence, risk, multi-repo/compliance relationships, and redaction.

Static checks validate grammar and deterministic properties. Scenario
evaluations cover semantic splitting, real-consumer decisions, logical commit
atomicity, PR focus, and respectful comments. Reports never present scenario
judgment as mechanical proof.

### 13. Exact manifest v2 contract

```json
{
  "schema_version": 2,
  "kit_version": "2.0.0",
  "request": {
    "profile": "default",
    "explicit_components": []
  },
  "components": [
    {
      "kind": "skill",
      "name": "implement",
      "path": ".agents/skills/implement",
      "ownership": "managed",
      "sha256": "<tree-sha256>"
    }
  ],
  "global_resources": [
    {
      "path": ".agents/artifact-catalog.json",
      "ownership": "managed",
      "sha256": "<file-sha256>"
    }
  ]
}
```

Closed semantics:

- request records the latest requested profile/additions;
- components records the complete physically present selected and previously
  retained component set;
- ownership is `managed | project-owned`;
- managed records require canonical current hash;
- project-owned records arise only from explicit keep and use current observed
  hash; they are never auto-updated;
- global resources are individual files, never a directory tree;
- AGENTS appears only when managed; an existing project AGENTS remains absent;
- manifest never records itself;
- removed/unselected previously installed components remain recorded and
  untouched;
- unknown files inside `.agents/schemas/` remain project-owned and untouched.

Individually managed global files:

- AGENTS when installer-owned;
- kit catalog;
- artifact catalog;
- intent index;
- each global schema file;
- `.agents/tools/check_artifact_ids.py`;
- `.agents/tools/fingerprint_artifact.py`.

A kept divergent mandatory catalog/schema/index/tool yields exit `3` and an invalid
installation requiring reconciliation; it is not silently described as valid.
Kept project-owned skill/module content remains available by filesystem presence
but is not kit-managed.

Installer stages all selected components and individual globals together,
publishes manifest last, and preserves keep/replace/abort and rollback. V1
manifest or `project.md` fails before staging. Fault injection covers before and
after each global publication, component publication, and manifest publication;
rollback and abandoned-transaction diagnostics must preserve user files.

### 14. Exact source-only historical v1 boundary

No installed catalog or checker advertises v1 artifact support. Source tests alone
preserve and recognize these exact files and SHA-256 values:

| Historical file | SHA-256 |
|---|---|
| `specs/001-agentic-sdlc-kit-v1/spec.md` | `1afd103327ff8bbbb66ffdee9387c0e169a2b7aded1de04c8cdb5c91a0669804` |
| `evidence/spec-001/evidence.json` | `b7b924cd8c802df1e0ea25b417e4f68e38850465f1b3177a26d6b6deff016e53` |
| `evidence/spec-001/review.md` | `70b81a774d9bdb91ace5277f1a1e6fc85deaabc07bbfe25a91434b2a8b337f14` |

The local ignored v1 plan/handoff are outside the byte-preservation guarantee
and are not shipped. Tests verify exact bytes and readable historical reporting,
reject arbitrary v1 artifacts elsewhere, and prove installed targets contain no
v1 reader.

### 15. Incremental rollout with green gates

Each slice has one rollback point and must leave the previous public commands
green. A slice may contain multiple focused implementation tasks when its
surfaces have independent failure modes; the slice gate passes only after every
task in that slice has fresh validation, while the ordered slice boundary and
rollback point remain singular:

1. **Baseline seal** — record clean status, 196 tests, v1 historical hashes;
   rollback: no writes.
2. **Additive contracts** — add global schemas, artifact catalog, intent index,
   strict parser, normalized model and tests without changing writers; rollback:
   remove additive files.
3. **Artifact formats** — add v2 owner schemas/templates and parallel fixtures;
   old writers still active; rollback: remove v2 variants.
4. **Project JSON** — switch setup and all root consumers atomically; reject
   project.md; rollback: revert this slice while additive schemas remain.
5. **Contribution/review** — add contribute and review variants/comments;
   rollback: remove catalog entries/skill and retain old review.
6. **Source validator refactor** — route structural checks through catalogs and
   schemas, run old/new differential assertions, then remove superseded branches;
   rollback: restore old entrypoint modules.
7. **Installed checker refactor** — split local package and validate differential
   decisions/read-only snapshot; rollback: restore monolithic checker.
8. **Installer/manifest flip** — switch version/catalog globals/manifest v2 in
   one transaction with exhaustive fault injection; rollback: transaction restores
   v1 source distribution state, not an external v1 install.
9. **Repository migration** — emit only v2 writable examples, SPEC-002 plan/tasks
   and docs; preserve exact v1 historical files; rollback: revert migration
   commit.
10. **Legacy removal/release** — remove project.md/manifest-v1 writers and temporary
    parallel fixtures; run full default/full installs and unsupported-v1 tests.
11. **Final acceptance** — recovery matrix, source/installed differential suite,
    contribution checker, no untracked output, and fresh independent review.

Do not start a slice while the previous slice has failing checks. Before the
manifest flip, create a source snapshot commit. Recovery tests inject failure at
every new global/component/manifest boundary and compare user-owned/uncommitted
content before and after.

## Compatibility and release

This is a clean-break source migration branch. Version 2.0.0 communicates
breaking writable artifact, project config, and manifest contracts.

The source repository retains only exact v1 historical acceptance fixtures. V1
project config, manifest, and arbitrary writable artifacts are unsupported.
Default/full v2 targets never receive general v1 readers.

Provider adapters may be separately accepted later. They cannot change the
portable contribution artifact or authorization contract.

## Security and privacy boundaries

- Catalogs, schemas, drafts, and project config are untrusted input.
- Reject duplicate keys, unknown fields, traversal, symlinks, unsafe owner
  pointers, and unsupported schema keywords.
- Safe `$ref` resolution uses preloaded catalog URNs only; no file/network fetch.
- No project-owned field can specify executable code, command, hook, plugin, or
  validator.
- Contribution checker uses read-only Git allowlists and argument arrays, never
  shell interpolation.
- Static hook discovery is not evidence of hook execution.
- No credential discovery, remote probing, authenticated identity inference, or
  provider API use.
- Errors identify fields and paths without echoing sensitive values.

## Failure handling and recovery

- Invalid catalog/schema/owner/index fails before writing.
- Project.md or manifest v1 fails before staging and remains untouched.
- Manifest/global conflict decisions are explicit; mandatory kept metadata is
  reported as incomplete rather than valid.
- Transaction failure restores previous managed paths or leaves a precise
  recovery location.
- Digest mismatch marks plan and mapped affected tasks stale without changing
  source intent.
- Verified source mutation fails against its evidence seal.
- Policy/check disagreement or failed hooks blocks contribution; no bypass.
- Shallow or unreadable history blocks new ID issuance; an unborn repository is
  verified empty history. A missing explicit base ref affects PR scope checks,
  not the all-ref historical ID scan, and permits only a clearly labeled draft.
- Missing provider state returns offline draft or blocked external action.

## Observability

- Installer reports v2 profile, individual globals, component ownership,
  conflict decisions, unsupported versions and recovery state.
- Source validator retains its deterministic human CLI and exit 0/1 contract;
  no new JSON mode is introduced.
- Installed enforcement and contribution checkers provide deterministic human
  and JSON reports with documented exit contracts.
- Contribution checker reports policy sources, scope, deterministic checks,
  advisory judgments and action boundary.
- Artifact errors name owner, schema, ID/qualified reference, lifecycle or source
  revision, and smallest correction.

## Source coverage and impact map

| Source item | Design area | Implementation surface | Verification | State |
|---|---|---|---|---|
| REQ-001 | Owner co-location | skill/module directories | owner-boundary tests | valid |
| REQ-002 | Distribution authority | kit catalog/schema | catalog mutations | valid |
| REQ-003 | Artifact authority | artifact catalog/schema | pointer/field mutations | valid |
| REQ-004 | Human navigation | indexes/by-intent | index drift tests | valid |
| REQ-005 | Bootstrap | AGENTS discovery | AGENTS-only scenarios | valid |
| REQ-006 | Availability | catalog/owner resolver | source/default/full fixtures | valid |
| REQ-007 | Markdown metadata | parser/common schema | every template/instance | valid |
| REQ-008 | H1/Git metadata | normalized Markdown model | title/date omission tests | valid |
| REQ-009 | Machine records | JSON schemas/evaluator | schema/meta tests | valid |
| REQ-010 | Template ownership | artifact catalog pointers | owner escape tests | valid |
| REQ-011 | Index authority | index generator/validator | status drift mutations | valid |
| REQ-012 | Local IDs | artifact semantic validator | repeated local-ID fixtures | valid |
| REQ-013 | Qualified refs | artifact graph | unqualified/qualified fixtures | valid |
| REQ-014 | Issued IDs | global artifact-ID history helper | deletion/reuse/all-ref/unborn/shallow tests | valid |
| REQ-015 | Cohesive split | owner skills/scenarios | semantic scenarios/warnings | valid |
| REQ-016 | Split contract | fragment schemas | reciprocity/lifecycle tests | valid |
| REQ-017 | Native contracts | plan guidance/catalog | consumer scenarios | valid |
| REQ-018 | Spec lifecycle | lifecycle catalog/validator | transition matrix | valid |
| REQ-019 | Derived planned | source fingerprint/plan | status-only/digest tests | valid |
| REQ-020 | Plan lifecycle | plan schema/staleness | transition/reconciliation tests | valid |
| REQ-021 | Task states | task graph schema/semantics | task matrix | valid |
| REQ-022 | ADR lifecycle | ADR schema/domain-model | supersession tests | valid |
| REQ-023 | Glossary/evidence | owner schemas | lifecycle matrices | valid |
| REQ-024 | Review/handoff | variant/snapshot schemas | no-lifecycle assertions | valid |
| REQ-025 | Direct path | AGENTS/implement | no-artifact scenarios | valid |
| REQ-026 | Partial/controlled | ask-kit/AGENTS | route scenarios | valid |
| REQ-027 | Project JSON | setup schema/template | valid/invalid config | valid |
| REQ-028 | Config fields | project schema/semantics | roots/modules/policy tests | valid |
| REQ-029 | Setup approval | setup skill | preview/recheck scenarios | valid |
| REQ-030 | Legacy config | setup/installer/checker | project.md rejection | valid |
| REQ-031 | Standalone review | review template | standalone fixtures | valid |
| REQ-032 | Evidence review | reduced template/evidence | duplication/parity tests | valid |
| REQ-033 | Review activation | artifact catalog variants | enabled/disabled tests | valid |
| REQ-034 | Contribute utility | contribute skill/catalog | activation/nonactivation | valid |
| REQ-035 | Policy precedence | contribute skill/checker | precedence fixtures | valid |
| REQ-036 | Policy conflict | contribute skill | hook/lint conflict tests | valid |
| REQ-037 | Classic message | commits reference/checker | message fixtures | valid |
| REQ-038 | Conditional CC | contribution policy | classic/CC fixtures | valid |
| REQ-039 | Logical commits | contribute guidance | scope checks/scenario judgment | valid |
| REQ-040 | Branch fallback | branch subcommand | ref fixtures | valid |
| REQ-041 | PR draft | PR template/checker | purpose/check/risk fixtures | valid |
| REQ-042 | PR focus | contribute guidance | scenario evaluation | valid |
| REQ-043 | Action approval | contribute skill | authorization matrix | valid |
| REQ-044 | Provider neutrality | checker imports/actions | AST/network snapshots | valid |
| REQ-045 | Comment disposition | review reference/template | disposition matrix | valid |
| REQ-046 | Comment quality | review reference | scenario evaluation | valid |
| REQ-047 | Verdict effect | review semantics | nonblocking comment tests | valid |
| REQ-048 | Feedback response | contribute reference | response/resolution scenarios | valid |
| REQ-049 | Communication | AGENTS/scenarios | mutation/scenario tests | valid |
| REQ-050 | Public docs | AGENTS/entrypoints | language-neutral fixtures | valid |
| REQ-051 | Internal comments | AGENTS/review | rationale/generated tests | valid |
| REQ-052 | Catalog-driven structure | both validators | path/field deletion tests | valid |
| REQ-053 | Runtime boundaries | source contracts/checker lib | import/install smoke | valid |
| REQ-054 | No triple hardcoding | code architecture | differential/static scan | valid |
| REQ-055 | Manifest v2 | installer/schema | ownership/conflict/fault tests | valid |
| REQ-056 | Clean break | installer/setup/source fixtures | unsupported-v1 tests | valid |
| REQ-057 | Source validation | validation package | mutation suite | valid |
| REQ-058 | Installed validation | enforcement package | target fixtures/snapshot | valid |
| REQ-059 | Release version | catalogs/docs/manifests | version consistency | valid |
| AC-001 | Source distribution | source validator | complete validation | valid |
| AC-002 | Default install | installer | clean default smoke | valid |
| AC-003 | Full install | installer/checker | clean full smoke | valid |
| AC-004 | Setup | project JSON | approval/legacy tests | valid |
| AC-005 | Markdown templates | owner schemas | all template fixtures | valid |
| AC-006 | Qualified IDs | graph validator | repeated local IDs | valid |
| AC-007 | Staleness | fingerprints/coverage | item-change tests | valid |
| AC-008 | Verified spec | evidence seal | mutation rejection | valid |
| AC-009 | Review variants | review/evidence | variant tests | valid |
| AC-010 | Contribution cases | contribute/checker | policy fixture matrix | valid |
| AC-011 | PR draft | template/checker | offline draft fixtures | valid |
| AC-012 | Review comments | review/contribute | disposition/response tests | valid |
| AC-013 | Validator parity | shared fixtures | source/target differential | valid |
| AC-014 | Drift mutation | catalogs/schemas/index | mutation matrix | valid |
| AC-015 | Repository migration | writable v2 artifacts | source scan/historical hashes | valid |
| AC-016 | Release acceptance | all surfaces | full regression/review | valid |

## Verification strategy

### Deterministic static/schema checks

- restricted frontmatter parser and normalized Markdown model;
- schema keyword allowlist and URN registry;
- closed catalogs/config/manifests/records;
- owner, template, schema, lifecycle, root, path and variant pointers;
- current IDs, qualified references, graph cycles, source digests, task readiness;
- contribution branch/message/trailer/draft syntax and observed scope;
- source/installed differential decisions;
- read-only AST, command allowlist, no-network and snapshot checks.

### Scenario/agent judgment checks

- semantic split and real native-contract consumer;
- logical commit atomicity and PR conceptual focus;
- quality of what/why explanations;
- respectful, one-problem, actionable review comments;
- reasoned response and substantive resolution;
- skill activation/nonactivation and conditional reference loading;
- clear communication and language-neutral source documentation.

Scenario results are evidence of evaluated behavior, not deterministic proof from
regex or file counts.

### Contribution fixture matrix

AC-010 requires all of these cases:

- repository with no convention uses classic fallback;
- explicit classic policy;
- required Conventional Commits with scope and breaking change;
- explicit instructions conflicting with hook/lint configuration;
- a requested commit whose real hook fails and is not bypassed;
- invalid branch refs;
- unrelated staged files outside repeated `--expected-path` inputs;
- staged/unstaged/untracked scope, diff-check and conflict-marker failures;
- required trailers and observed/not-run checks;
- local PR template with unresolved placeholders;
- squash-title policy applied to the persisted commit-message convention;
- unauthorized branch, stage, commit, push, PR, comment, and thread-resolution
  actions;
- malformed stdin/file/observations input and redacted human/JSON errors;
- read-only command allowlist plus Git/filesystem snapshot.

### Rollout gates

Every rollout slice runs its focused tests, the previous complete suite,
`python3 scripts/validate.py`, source enforcement, pycompile, and diff checks.
Installer/checker slices additionally run default/full target smoke. Manifest
slice runs all fault-injection and recovery fixtures. Final acceptance runs all
commands from a clean checkout and an independent high-risk review.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Catalog duplicates owner rules | Catalog stores pointers and closed metadata only. |
| Markdown subset is mistaken for full YAML | Explicit JSON-value grammar and parser tests. |
| Schema evaluator silently ignores behavior | Closed keyword allowlist; unsupported keyword errors. |
| Whole-source digest over-invalidates work | Status-excluding overall and per-item fingerprints. |
| Local IDs are reused after deletion | Global read-only history helper scans all reachable refs; shallow history blocks issuance. |
| Optional owner is absent | Common validation plus warning; mutation blocked. |
| Review/evidence diverge | Two catalog variants and duplicate-section rejection. |
| Contribution checker runs hooks or mutates Git | Read-only subcommands/allowlist/snapshot tests; hooks only through requested commit. |
| Manifest globals overwrite project files | Individual file ownership; unknown children untouched. |
| Installer transaction regresses | Keep mature transaction code; fault-test only new publications. |
| V1 compatibility leaks into targets | Exact source-only path/hash fixtures; no installed reader. |
| Migration diff becomes unreviewable | Eleven green rollout slices and atomic commits. |
| Semantic qualities become fake gates | Separate deterministic checks from scenario judgment. |
| High-risk migration lacks recovery | Source snapshot, rollback injection, historical hashes, independent review. |

## Open questions

None.

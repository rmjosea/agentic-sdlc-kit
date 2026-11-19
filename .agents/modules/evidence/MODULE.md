# Evidence module

Persist concise, structured evidence for changes whose duration, coordination, or
risk warrants a durable record.

## Activation

Apply this module only when all of the following are true:

1. this `MODULE.md` is installed;
2. `evidence` appears in `enabled_modules` in recognized
   `.agents/project.json` (legacy `.agents/project.md` is unsupported); and
3. `roots.evidence` is a configured repository-relative path, including the
   explicitly confirmed default `evidence`.

If any condition is missing, stop applying this module. Do not add a fallback,
artifact, gate, or burden to the core workflow. Use `setup` separately when the
user wants to recognize configuration, enable the installed module, or confirm
the default root.

## Create only when useful

Create `evidence/<change-id>/evidence.json` and `review.md` lazily, substituting
the configured evidence root. Duration across sessions, coordination or
handoff, and medium/high risk are reasons to persist them. Do not create an
evidence artifact for a trivial direct-path change unless an authoritative
source or repository policy requires one.

Evidence supplements accepted intent, plans, tasks, code, and review; it never
replaces them. `tasks.md` remains task-state authority. Specs define what, plans
define how, and tasks define execution order.

## Maintain the deterministic record

Start from [the evidence template](assets/evidence.template.json) and keep it
valid against [schema version 1](assets/evidence.schema.json). Use stable array
order from authoritative source order, requirement order, then check execution
order. Update one record for the change rather than creating competing sources.

Record:

- change ID, source references, lifecycle status, status evidence, and risk;
- the concise change contract: intent, confirmed-why reference, scope, expected
  evidence, agent roles, and review focus;
- the exact non-empty `repository_scope` array: one unique repository ID with
  immutable base/head and committed range when fixed, plus exact uncommitted
  path/state/content hashes and its snapshot hash;
- requirement coverage, its non-empty repository-ID subset, and
  implementation/evidence references;
- each check's non-empty covered requirement IDs and repository-ID subset, kind,
  applicability, status,
  concise observed result, evidence class, and optional output reference;
- declared reviewer role/ID, declared implementers, prior participation, fresh
  context, factual independence basis/classification, verdict, and `review.md`
  reference;
- known limits (or `not-tracked`), remaining risks, and follow-ups.

A single-repository change uses one scope entry such as repository ID `current`;
multiple repositories use additional entries in that same array, never a
competing field. While work is `in-progress`, use explicit `null` revision and
snapshot identifiers and an empty uncommitted list when the fixed snapshot is
pending. Before `implemented` or
`verified`, replace placeholders with immutable identifiers and the exact
committed range, or explicit `not-applicable` when revisions do not exist. Add a
SHA-256 snapshot over uncommitted entries ordered by path then state. Hash
compact canonical JSON with lexicographically sorted object
keys and no insignificant whitespace.

Every coverage item and check links a non-empty subset of repository scope IDs;
every check also links a non-empty subset of `requirement_coverage` IDs. For
`passed` or `failed`, record a concise result and `observed evidence`; an output
reference is optional and never inline output. For `skipped` or `not-run`, keep
result, class, and output reference `null`.

Do not advance a lifecycle status without cited evidence. A failed, skipped, or
unrun applicable required check prevents completion and advancement. An
`approved` verdict is valid only with lifecycle `complete` after every required
check, review, and risk rule passes; an `in-progress` or `blocked` record cannot
be approved. Keep an incomplete record `in-progress` or `blocked`.

## Apply risk completeness

Any review classified `independent`, at every risk and lifecycle state, requires
fresh context, no prior implementation participation, a reviewer ID different
from every declared implementer, and a non-empty independence basis. A
`self-review` requires its reviewer ID among implementers and prior
`implementation` participation; fresh context never changes that classification.

- Low risk: applicable required scoped checks must pass, followed by an
  accurately labeled self-review.
- Medium risk: also require passing regression evidence and an explicit
  failure-path applicability decision. Applicable failure-path checks must
  pass; `not-applicable` needs a concise reason.
- High risk: also record recovery/rollback applicability. Applicable checks
  must pass; `not-applicable` needs a reason. Approval additionally requires the
  independent classification above.

Never infer applicability from omission. Record an explicit applicable or
not-applicable decision for every risk-required check kind.

## Produce the review report

Produce `review.md` through the core review report contract and template. Keep
`evidence.json` as the deterministic machine source and link the report through
`review.reference`; do not duplicate the machine record as prose. A reviewer
records a role and factual participation basis, not authenticated identity.
Never claim that a check ran unless its execution and fixed scope were directly
observed.

## Safety

Keep every machine string single-line, free of control characters, and at most
500 characters. Store concise results and references, never raw command output,
by default. Never put secrets, credentials, or personal data in either artifact.
Source validation rejects common credential assignments and plausibly sized
standalone `ghp_`, `github_pat_`, and `sk-` tokens without treating tiny examples
as secrets. This bounded heuristic is not a universal detector.

If an authoritative policy requires sensitive evidence, follow its approved
safe storage and place only a non-sensitive reference here. Reviewer and
implementer identifiers are declarations, not authenticated identities. Do not
treat the schema as authentication, policy enforcement, or proof that a named
person performed work.

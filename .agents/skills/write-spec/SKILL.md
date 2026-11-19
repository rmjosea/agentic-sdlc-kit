---
name: write-spec
description: Persist an approved understanding of what a product or software change must do as one cohesive specification or several atomic capability specifications. Use when ideation or requirements have been confirmed and the user asks to write, store, generate, split, or update specs. Keep implementation choices out unless they are confirmed constraints.
---

# Write Product Specifications

Create the first stable artifact in the workflow. Define **what** must be true,
not the implementation that will make it true.

Do not create a spec merely because code will change. Use one when product
behavior needs a durable acceptance contract; use the direct or plan-only path
from `AGENTS.md` when that contract would add no value.

## Preconditions

Require an explicitly approved conversational understanding or equivalent
source authority. Identify and link every authoritative input; do not treat
repository behavior as product authority. If sources contradict or material
product ambiguity remains, return to `shape-idea`.

## Choose spec boundaries

Prefer one specification when the change has one cohesive outcome and shared
rules. Split into multiple specifications when capabilities:

- deliver independent user value;
- can be accepted or released separately;
- have distinct actors, rules, or lifecycles;
- require independent planning;
- would force multiple primary objectives into one document.

Split by capability, never by technical layer. Do not create separate frontend,
backend, database, or API specs for one product capability.

Before writing multiple specs, show the proposed boundaries, dependencies, and
rationale. Ask for confirmation when the decomposition materially affects scope
or delivery.

## Resolve the specification root

Resolve the destination only when this operation will inspect or write specs.
Reject any `.agents/project.md` as unsupported before writing. If
`.agents/project.json` is absent, use `specs/`. If it exists, validate it with
`.agents/skills/setup/assets/project.schema.json` and apply
`.agents/skills/setup/references/project-config.md`. Stop on any invalid config
rather than guessing or falling back. Use recognized `roots.specs` as
`<specs-root>`.

## Write

Use [assets/spec.template.md](assets/spec.template.md). Remove sections that do
not add information. Store:

```text
<specs-root>/<NNN-capability>/spec.md
```

When more than one spec exists, maintain a concise `<specs-root>/README.md`
containing only the capability list, state, and functional dependencies. Use
[assets/spec-index.template.md](assets/spec-index.template.md).

Assign each spec a stable ID and one lifecycle state:

```text
draft -> approved -> [planned] -> implemented -> verified
```

- `draft`: still being authored or awaiting product approval.
- `approved`: product behavior and acceptance criteria are confirmed.
- `planned`: an approved technical plan covers the spec.
- `implemented`: the implementation is complete but not yet verified by review
  evidence.
- `verified`: review evidence confirms the acceptance criteria.

Only advance a state when its evidence exists. Do not renumber an existing spec
after its ID has been referenced by a plan, task, commit, or review.
This skill owns `draft -> approved`; later workflow skills own subsequent
transitions defined in `AGENTS.md`.

`planned` is optional. Move directly from `approved` to `implemented` when the
spec is simple enough that a durable technical plan would add no value.

## Provenance rules

Preserve source links in frontmatter and put only material, source-confirmed
product why under `Confirmed rationale`; do not include implementation
rationale. If why is unconfirmed, state `Unknown` rather than deriving it from
code or outcomes. Keep repository evidence, assumptions, and agent inferences
separate when they add useful context, and never promote them to requirements
without confirmation. Do not copy source narratives or private chain-of-thought.

## Content rules

Include as relevant:

- context and problem;
- outcome and actors;
- in-scope and out-of-scope behavior;
- functional requirements and business rules;
- externally observable quality constraints;
- scenarios, errors, and edge cases;
- acceptance criteria and verification signals;
- confirmed constraints and dependencies.

Exclude unless explicitly imposed:

- framework or library choices;
- internal module or directory structure;
- concrete tables, classes, and functions;
- endpoint design;
- deployment topology;
- implementation tasks.

Express acceptance criteria as observable outcomes. Give each non-trivial,
implementation-relevant requirement a stable ID such as `REQ-001` so plans,
tasks, and reviews can trace it without copying its text.

## Quality gate

Before finishing, verify:

- every requirement supports the stated outcome and an authoritative source;
- sources and material confirmed rationale are linked, and unknown why is
  explicit;
- each acceptance criterion can be observed or tested;
- terms are consistent and unambiguous;
- no implementation preference is disguised as a requirement;
- spec boundaries are cohesive and minimally coupled;
- open questions are explicit and block planning when material.
- frontmatter uses a stable ID, normalized state, source links, and explicit
  dependencies;
- the index matches the specs on disk when more than one spec exists.

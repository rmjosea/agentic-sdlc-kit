---
name: write-spec
description: Persist an approved understanding of what a product or software change must do as one cohesive specification or several atomic capability specifications. Use when ideation or requirements have been confirmed and the user asks to write, store, generate, split, or update specs. Keep implementation choices out unless they are confirmed constraints.
---

# Write Product Specifications

Create the first stable artifact in the workflow. Define **what** must be true,
not the implementation that will make it true.

## Preconditions

Require an explicitly approved conversational understanding or equivalent
authoritative input. If material product ambiguity remains, return to
`shape-idea`.

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

## Write

Use [assets/spec.template.md](assets/spec.template.md). Remove sections that do
not add information. Store:

```text
specs/<NNN-capability>/spec.md
```

When more than one spec exists, maintain a concise `specs/README.md` containing
only the capability list, state, and functional dependencies. Use
[assets/spec-index.template.md](assets/spec-index.template.md).

Assign each spec a stable ID and one lifecycle state:

```text
draft -> approved -> planned -> implemented -> verified
```

- `draft`: still being authored or awaiting product approval.
- `approved`: product behavior and acceptance criteria are confirmed.
- `planned`: an approved technical plan covers the spec.
- `implemented`: the implementation is complete but not independently verified.
- `verified`: review evidence confirms the acceptance criteria.

Only advance a state when its evidence exists. Do not renumber an existing spec
after its ID has been referenced by a plan, task, commit, or review.

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

Express acceptance criteria as observable outcomes. Use stable requirement IDs
only when they improve traceability.

## Quality gate

Before finishing, verify:

- every requirement supports the stated outcome;
- each acceptance criterion can be observed or tested;
- terms are consistent and unambiguous;
- no implementation preference is disguised as a requirement;
- spec boundaries are cohesive and minimally coupled;
- open questions are explicit and block planning when material.
- frontmatter uses a stable ID, normalized state, and explicit dependencies;
- the index matches the specs on disk when more than one spec exists.

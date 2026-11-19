---
name: domain-model
description: Clarify and normalize domain terms, maintain a glossary or CONTEXT.md, and evaluate or record an ADR. Use when discussing domain terms, resolving a glossary or CONTEXT.md meaning, or registering an architectural decision. Do not use for product requirements or specs, an implementation plan, general documentation, or a code rename without a domain decision.
---

# Maintain Domain Language and Decisions

Resolve one durable meaning or qualifying architectural decision without turning
working discussion into premature documentation.

## Boundaries and locations

- Follow applicable `AGENTS.md`; this optional skill does not replace product
  specification, technical planning, implementation, or general documentation.
- Reject any `.agents/project.md` as unsupported before writing. When
  `.agents/project.json` exists, validate it with the setup-owned schema and
  apply `.agents/skills/setup/references/project-config.md` before use. Require
  closed strict JSON with duplicate-key rejection. If the setup contract is
  unavailable or config is invalid, stop without using a configured root.
- Do not modify project configuration. For glossary work use only
  `roots.domain_context`; for ADR work use only `roots.adrs` from recognized
  project JSON. If config is absent, the needed root is unconfigured.
- Limit writes to one approved glossary diff or one approved ADR. Never change
  code, specs, plans, project rules, or unrelated documentation.

## Resolve the configured destination

Inspect the configured path without creating anything:

- For `roots.domain_context`, an existing file is the glossary destination; for
  an existing directory, use `<directory>/CONTEXT.md`. If the configured path is
  absent, does not exist, is unsafe, has another file type, or remains ambiguous,
  ask exactly one question for the intended repository-relative glossary path,
  then stop before writing.
- When `roots.adrs` is an existing directory, use
  `<directory>/<next-id>-<slug>.md`. Derive `<next-id>` by advancing the
  established numeric filename sequence without changing its width, and derive
  `<slug>` from the confirmed decision title under the observed naming
  convention. If either value or a collision is ambiguous, ask one question.
- When `roots.adrs` is an existing file, use it only if inspected records provide
  evidence of a multi-record ADR ledger convention. Otherwise ask exactly one
  question before writing. For an absent, nonexistent, unsafe, or ambiguous ADR
  path, also ask one path question and stop.

Never invent a destination or naming convention. A confirmed answer selects the
path for this operation only; it does not authorize a project-config change.

## Inspect and classify evidence

1. Read the target glossary or ADR collection if it exists, preserving its
   organization, naming, status vocabulary, and formatting.
2. Inspect only repository facts, code, tests, history, and product artifacts
   relevant to the term or decision. Code describes implemented behavior; it
   does not by itself define intended meaning or rationale.
3. Compare the request with existing glossary definitions and repository usage.
   Surface contradictions rather than silently reconciling them.
4. For ADR work, classify material inputs as **Confirmed rationale**,
   **Repository evidence**, **Agent inference**, or **Unknowns**. Never present
   inference or an unknown as confirmed rationale.
5. Retain a snapshot of every prospective destination before preparing a write.

## Resolve one domain term

- Work on one term at a time. Never batch unresolved terms.
- Challenge vague, overloaded, conflicting, or circular language. Identify who
  uses the term and what distinctions it must preserve.
- Test candidate meanings with at least one concrete scenario and a boundary or
  counterexample. Compare the result with both glossary language and code.
- When code contradicts the intended meaning, report the mismatch and ask which
  meaning is authoritative; do not redefine the term from implementation alone.
- A term is resolved only after the user clearly confirms its canonical meaning,
  relationships, boundaries, and any ambiguous synonyms to reject.

## Update the glossary after approval

For a resolved term, show the exact minimal insertion or replacement in context
and ask for clear confirmation before writing. Earlier discussion or agreement
on the meaning is not write approval.

Keep `CONTEXT.md` only for canonical term meanings, relationships, and rejected
ambiguous synonyms. Exclude implementation details, product requirements,
specifications, plans, scratch notes, open questions, evidence logs, and
rationale dumps. Preserve the existing format and content.

Load [the glossary asset](assets/glossary.template.md) only when the confirmed
domain-context file does not exist. Create it lazily only after one term is
resolved and its exact initial content is approved; replace all placeholders.

## Apply the ADR gate

Create no ADR unless repository evidence and confirmed statements establish all
three conditions:

1. the decision is **costly to reverse**;
2. it would be **surprising without context**;
3. it reflects a **real trade-off** between available alternatives.

If any condition is missing, do not create an ADR. Explain the failed gate and,
when durability is still useful, place product behavior in a spec,
implementation design in a plan, or a routine operating rule in the applicable
project documentation. Do not use an ADR as a substitute.

## Draft and approve an ADR

- State the proposed decision and obtain confirmation before drafting a record.
- Describe alternatives actually considered, not invented straw options.
- Keep `Confirmed rationale`, `Repository evidence`, `Agent inference`, and
  `Unknowns` as separate sections. Never infer rationale from code or the chosen
  outcome. If no source confirms it, put the gap under `Unknowns`, never under
  `Confirmed rationale`; use `None confirmed` in the latter when appropriate.
- Record status, date, context, decision, alternatives, all four evidence
  sections, and consequences. Include adverse consequences; omit private
  chain-of-thought.
- Make no legal or compliance claim. Report only supported engineering facts.

Load [the ADR asset](assets/adr.template.md) only after the decision qualifies
and is confirmed. Follow existing ADR naming and format when present. Show the
exact record and destination, then ask for approval to write that exact record.
Any changed record requires renewed approval.

## Write safely

Immediately before writing, re-read the destination and its parent collection.
Stop on any concurrent change, merge conflict, new competing record, unexpected
file type, or mismatch with the retained snapshot; never overwrite or merge by
guess. After approval and a clean recheck, create only the needed file or apply
the smallest approved edit.

## Quality gate

Re-read the result and verify that it matches the approved preview, uses the
confirmed root and existing format, contains only allowed content and evidence
labels, and leaves unrelated paths unchanged. Inspect the diff for accidental
implementation detail, invented rationale, unresolved terms, or unsupported
claims.

Report the resolved term or ADR gate result, evidence classification, exact file
change if any, checks performed, and remaining unknowns.

## Stop conditions

Stop without writing when a root, authority, term, decision, rationale,
alternative, approval, destination state, or existing convention is materially
ambiguous; any ADR gate fails; the requested content belongs to another
artifact; the destination changed concurrently; or the quality gate cannot
pass. Never repair a failed check with an unapproved second write.

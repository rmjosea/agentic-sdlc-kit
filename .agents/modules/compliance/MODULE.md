# Compliance module

Preserve declared approvals and a durable, reviewable event history for changes
that require auditable traceability.

## Activation

Apply this module only when all of the following are true:

1. this `MODULE.md`, the `evidence` module, and the `enforcement` module are
   installed;
2. `compliance`, `evidence`, and `enforcement` all appear in `enabled_modules`
   in recognized `.agents/project.json` (legacy `.agents/project.md` is
   unsupported and blocks the operation); and
3. `roots.evidence` is configured as required by the evidence module.

If any condition is absent, compliance is inactive. Do not create an audit log,
request an approval, or add a workflow burden. Use `setup` separately to inspect,
question, and preview module enablement, the evidence root, and approval policy.

## Keep one deterministic event log

For each evidence record that warrants compliance traceability, keep
`audit.jsonl` beside `evidence.json` and `review.md`. Start each event from
[the event template](assets/audit-event.template.json) and keep every line valid
against [event schema version 1](assets/audit-event.schema.json).

Write exactly one compact JSON object per line with canonical field order for
the event and each actor, approval, and repository object, following schema
`required` order. Use a stable event ID, strictly increasing unique integer sequence, and strictly
increasing unique RFC3339 UTC timestamp. Keep all lines on the same change ID.
Order source and evidence references lexically, approvals by role then actor ID,
and repositories by Repository ID. Record lifecycle fields only for
`lifecycle-transition` events.

Allowed lifecycle transitions follow the core specification and evidence
lifecycle:

- `draft -> approved`;
- `approved -> planned`;
- `approved -> implemented`;
- `planned -> implemented`; and
- `implemented -> verified`.

Every applicable source reference must resolve to an authoritative source or
match a source declared by `evidence.json`. Every evidence, review, and approval
reference must resolve to a regular non-symlink file. `implemented` and
`verified` events must agree with the evidence lifecycle. Repository IDs and
immutable revisions must agree with the evidence scope and, while multi-repo is
active, with configured Repository IDs.

## Apply the approval policy

Recognized `.agents/project.json` schema version 2 carries the closed
`approval_policy`; no legacy configuration is read. Setup owns its shape and
this module owns enabled evaluation. Use [the policy schema](assets/approval-policy.schema.json) and
[empty policy template](assets/approval-policy.template.json). Each rule maps one
risk and action to declared roles, minimum unique actor counts, and whether
independence is required.

The policy only adds requirements. It never weakens `AGENTS.md`: high-risk
approval still requires independent review. An approval actor used to satisfy an
independence requirement cannot be an implementer declared by `evidence.json` or
by any audit event whose role is `implementer` or `implementation`; this includes
the event's own actor. Missing approvals are validation failures; never
manufacture an approval or take an automatic action.
Actor IDs and roles are declarations only, not authenticated identity.

## Workflow and safety boundaries

Treat events as append-only by workflow convention and keep them versioned in
Git with the repository. This is declared, editable Git provenance: events
remain ordinary editable files so a reviewed correction is possible, and
identities, roles, revisions, and approvals are declarations. The checker
validates current content only; it does not inspect Git history or prove who made
one.
Do not run Git or project commands.

Keep every string non-empty where required, single-line, free of control
characters, and at most 500 characters. Store references and concise
declarations only: never secrets, credentials, raw command output, or personal
data.

This module provides no cryptographic chain, signature, authenticated identity,
legal certification, compliance guarantee, or external publication. It uses no network,
credentials, signing service, external storage, or background process.

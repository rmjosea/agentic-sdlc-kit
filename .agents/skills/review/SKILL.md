---
name: review
description: Review a completed or in-progress change against both its originating specification and the repository's engineering standards, using diff evidence and executed checks. Use when the user asks for code review, implementation verification, acceptance review, pre-merge review, or an independent assessment of whether a change is correct and ready.
---

# Review an Implementation

Review the actual diff and observed behavior. Do not rely on the implementer's
summary as evidence.

State whether the review is independent or a self-review. Treat only a fresh
session or agent that did not implement the change as independent. High-risk
work cannot receive an `approved` verdict without independent review.

## Establish scope

1. Resolve the comparison base or ask for it.
2. Capture the diff, changed files, and commits from that fixed point.
3. Locate the originating spec, plan, and relevant repository guidance.
4. Identify checks that can verify the acceptance criteria.

If no specification exists, say so and review engineering quality without
inventing product intent.

## Axis 1: specification conformance

Check:

- required behavior and acceptance criteria;
- traceability from requirement IDs to tasks and evidence;
- missing, partial, or extra behavior;
- business rules, failures, and edge cases;
- externally observable quality constraints;
- unexplained deviation from confirmed scope.

## Axis 2: engineering quality

Check:

- correctness and regression risk;
- simplicity and unnecessary abstraction;
- unrelated or overly broad changes;
- data integrity and compatibility;
- trust boundaries, authorization, secrets, and unsafe effects;
- error handling, recovery, and observability;
- tests, static checks, and documentation;
- maintainability within repository conventions.

Read [references/security.md](references/security.md) only when the change
handles authentication, authorization, untrusted input, secrets, personal data,
payments, external actions, or another trust boundary.

## Validate

Run relevant checks when safe and available. Distinguish:

- observed evidence;
- source-based inference;
- unverified claim.

Do not approve solely because tests pass; tests may not cover the spec.

## Report

Order findings by severity: `critical`, `high`, `medium`, `low`. Each finding
must include evidence, location, impact, and the smallest recommended action.
Do not invent findings to fill categories.

Finish with one verdict:

- `approved`
- `changes-required`
- `blocked`

Use [assets/review.template.md](assets/review.template.md).

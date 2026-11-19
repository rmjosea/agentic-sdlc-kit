---
title: rubric-spec — quality dimensions for spec artifacts
updated: 2026-11-17
related:
  - ./SKILL.md
---

# Rubric — `spec`

> [!info] When to load
> Load when `judge-spec` evaluates a `type: spec` artifact. Dim 14 (Grounding / feasibility) is a non-blocking advisory owned downstream by `plan-feature`.

## Quality dimensions

| # | Dimension | Pass criterion | Block on fail? |
|---|---|---|---|
| 1 | **Problem stated** | 2–4 sentences from the user's POV, not the system's | Yes |
| 2 | **Evidence cited** | >= 2 evidence points (persona quote, usage data, user test, documented team decision/rationale, or described failure mechanism) | Yes |
| 3 | **Cohort identified** | Who is affected (linked persona, segment, % or volume of users) | Yes |
| 4 | **Scope IN explicit** | Numbered or checkable capabilities, verb-led, observable | Yes |
| 5 | **Scope OUT explicit** | What is NOT in scope, with link/reference to the artifact or iteration that covers it | Yes |
| 6 | **ACs in Given/When/Then** | Each acceptance criterion is independently verifiable in Gherkin or Given/When/Then table | Yes |
| 7 | **Constraints listed** | Regulatory (PII, GDPR), security, accessibility, i18n, or performance constraints stated | Yes — if applicable |
| 8 | **Dependencies named** | Upstream / downstream services or teams + owners | Yes |
| 9 | **Success metrics quantified** | >= 1 quantified target (number + timeframe, or explicit PO exemption documented) | Yes |
| 10 | **Open questions tracked** | Outstanding `[ ]` items carry `[NEEDS CLARIFICATION]` and an `@owner` | No — flag |
| 11 | **Org-standards alignment** | If touching auth, PII/privacy, AI, security boundaries, persistence/schema, or observability/errors, the relevant organization standard is referenced | Yes — if applicable |
| 12 | **No HOW leakage** | The spec does NOT prescribe internal technical implementation (HOW belongs in `plan.md`) | Yes |
| 13 | **Length / split** | Single cohesive spec stays single-file; split only when grouping >=3 independent specs OR >~3000 tokens | Yes — trigger split |
| 14 | **Grounding & glossary (advisory)** | L1 codebase/context pre-check (any configured context/`vault/` or repo `AGENTS.md`) + domain glossary consistency; flags likely NEW capability, contradiction, or stale downstream plan for `plan-feature` | No — flag (advisory) |

## Pass / fail

- **Pass** = all dimensions with `"Block on fail? Yes"` are met -> ready for human approval (`status: approved`).
- **Fail** = any blocking dimension unmet -> `status: needs-work`, ask one blocker at a time, loop.

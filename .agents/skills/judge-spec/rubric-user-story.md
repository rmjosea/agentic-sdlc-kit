---
title: rubric-user-story — quality dimensions for user-story artifacts
updated: 2026-11-17
related:
  - ./SKILL.md
---

# Rubric — `user-story`

> [!info] When to load
> Load when `judge-spec` evaluates a `type: user-story` artifact.

## Quality dimensions

| # | Dimension | Pass criterion | Block on fail? |
|---|---|---|---|
| 1 | **Story format** | `Como [persona], quiero [capacidad], para [resultado]` — all three elements present | Yes |
| 2 | **Persona linked** | Persona file in `personas/{slug}.md` is linked | Yes |
| 3 | **Acceptance criteria** | 1–5 ACs in Given/When/Then (BDD Gherkin) | Yes |
| 4 | **INVEST — Independent** | No hidden dependency on another in-flight story | Yes |
| 5 | **INVEST — Negotiable** | Leaves room for technical design choices in `plan-feature` | No — flag |
| 6 | **INVEST — Valuable** | Outcome benefits the persona | Yes |
| 7 | **INVEST — Estimable** | Engineering can size it without blocking unknown unknowns | Yes |
| 8 | **INVEST — Small** | Fits in one sprint (<= 5 days of focused work) | Yes |
| 9 | **INVEST — Testable** | Every AC is independently verifiable | Yes |
| 10 | **Out of scope** | Explicit list of deferred items | No — flag |
| 11 | **Definition of Done** | DoD checklist present (tests, security/PII, a11y, telemetry) | No — flag |
| 12 | **Grounding / feasibility (advisory)** | L1 repo/vault pre-check flags likely NEW capability or contradiction for `plan-feature` | No — flag (advisory) |

---
title: rubric-user-journey — quality dimensions for user-journey artifacts
updated: 2026-11-17
related:
  - ./SKILL.md
---

# Rubric — `user-journey`

> [!info] When to load
> Load when `judge-spec` evaluates a `type: user-journey` artifact.

## Quality dimensions

| # | Dimension | Pass criterion | Block on fail? |
|---|---|---|---|
| 1 | **Persona named** | Single primary persona linked to `personas/{slug}.md`, never a generic "usuario" | Yes |
| 2 | **Scenario sentence** | One sentence describes what the persona accomplishes and the value gained | Yes |
| 3 | **Trigger named** | The exact event that starts the journey is explicit | Yes |
| 4 | **Steps ordered** | Steps in chronological order with no gaps (interaction table or experience phases) | No — flag |
| 5 | **Experience captured** | Each step has actor + action + observable expected result | No — flag |
| 6 | **Touchpoints listed** | Frontend surfaces + backend services/events + tracking identified | No — flag |
| 7 | **Success signals quantified** | At least one quantified metric | Yes |
| 8 | **Out of scope explicit** | What this journey does NOT cover | No — flag |
| 9 | **Related artifacts linked** | Persona, related journeys/features, and RBAC noted | No — flag |
| 10 | **Length / split** | Single cohesive journey stays single-file; split only when >=3 independent journeys OR >~3000 tokens | No — flag |
| 11 | **Implementation-sufficiency & consistency** | Every AC is testable (Given/When/Then); every happy + alt/edge flow has a defined expected result; no internal contradictions | Yes |
| 12 | **Grounding & glossary (advisory)** | L1 codebase/context pre-check (any configured context/`vault/` or repo `AGENTS.md`) + domain glossary and existing UI design-system component check; flags NEW capability or contradiction for `plan-feature` | No — flag (advisory) |

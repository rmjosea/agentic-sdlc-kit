---
title: rubric-adr — quality dimensions for ADR artifacts
updated: 2026-11-17
related:
  - ./SKILL.md
---

# Rubric — `adr`

> [!info] When to load
> Load when `judge-spec` evaluates a `type: adr` artifact.

## Quality dimensions

| # | Dimension | Pass criterion | Block on fail? |
|---|---|---|---|
| 1 | **Numbering** | 4-digit zero-padded, sequential in `architecture/adr/adr-{NNNN}-{slug}.md` | Yes |
| 2 | **Status named** | One of: `draft`, `review`, `approved`, `implemented`, `superseded`, `archived` | Yes |
| 3 | **Context — forces** | 2–4 paragraphs describing forces at play, constraints, and prior work | Yes |
| 4 | **Decision sentence** | One declarative sentence in active voice ("Usaremos ...") | Yes |
| 5 | **Decision expanded** | Specific shape and boundaries of the decision in 1–2 paragraphs | Yes |
| 6 | **Consequences — positive** | At least 1 concrete benefit listed | Yes |
| 7 | **Consequences — negative** | At least 1 cost or trade-off listed (no decision is free) | Yes |
| 8 | **Alternatives considered** | >= 2 alternatives with pros, cons, and rejection reason (including "do nothing") | Yes |
| 9 | **Affects** | Concrete list of repositories, services, or contracts impacted | Yes |
| 10 | **Migration / rollback** | If existing systems change: migration path + rollback strategy (or explicit N/A) | Yes — if applicable |
| 11 | **References** | Originating spec, journey, or standard linked | No — flag |
| 12 | **Supersedes / superseded by** | Reciprocal links when replacing a prior ADR | Yes — if applicable |

---
title: Progressive Disclosure — Agent Context Loading (L0–L4)
updated: 2026-11-17
related:
  - ./output-splitting.md
  - ./conventions.md
---

# Progressive Disclosure — Agent Context Loading

> [!info] When to load
> Load when designing multi-file documentation, skills, or repository knowledge layers. Prerequisites: `AGENTS.md`.

All content in the harness and specification layer is structured for **progressive disclosure**: agents load a small overview first and descend into detail only when the task requires it.

## 5 levels of disclosure

```text
LEVEL 0  README.md + AGENTS.md                       ~1k tokens   always loaded
LEVEL 1  .agents/indexes/by-intent.md or area README ~2–3k tokens loaded when entering an area
LEVEL 2  Catalog / 00-overview.md                    ~3–5k tokens loaded to route or list options
LEVEL 3  SKILL.md / convention / artifact detail     bounded      loaded for a specific task
LEVEL 4  Templates, rubrics, JSON schemas, scripts   on-demand    loaded only by the active step
```

**Load one level at a time. Stop as soon as the request is addressable.**

## Required header callout

Every L1/L2/L3 reference or split document starts with:

```markdown
> [!info] When to load
> Load this file when [trigger]. Prerequisites: [L0/L1 files]. Next level: [detail file].
```

## Rationale

- **Attention budget**: LLM instruction-following degrades as simultaneous instructions grow (IFScale `arXiv:2507.11538`; Gloaguen et al. ICLR 2026 `arXiv:2602.11988`).
- **Predictable navigation**: uniform L0–L4 tiers let agents self-route without brute-force file reads.
- **Lower latency and cost**: loading only the active skill and the one rubric or template needed cuts per-turn token overhead by 60–80%.

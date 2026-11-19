---
title: Output splitting — progressive disclosure for generated artifacts
updated: 2026-11-17
related:
  - ./progressive-disclosure.md
  - ./frontmatter-schema.md
---

# Output splitting

> [!info] When to load
> Load before saving any generated artifact in `save-output`, `judge-spec`, or `plan-feature`. Prerequisites: `progressive-disclosure.md` and `frontmatter-schema.md`.

## Rule

**Split into a folder only when the artifact (a) groups >=3 genuinely independent artifacts (e.g., 3 separate user-journeys for one feature) OR (b) exceeds ~3000 tokens estimated (`file_size_bytes / 4`). A single cohesive artifact — one journey or spec with its happy path plus alternative, error, and edge flows — stays single-file even above 2000 tokens, because those flows are tightly coupled.**

Count **independent concerns**, not template headings (`## Problema`, `## Alcance`, etc.) and not the error/edge flows of a single journey.

## Single-file form (under threshold)

```text
features/001-feed-personalizado/spec.md
```

All content in one file with Shape A frontmatter.

## Split form (over threshold)

```text
features/001-feed-personalizado/spec/
├── 00-overview.md          <- L1 index (<= 500 tokens, carries `children: [...]`)
├── 01-elegibilidad.md      <- L3 detail (self-contained, carries `parent: ./00-overview.md`)
├── 02-ranking.md           <- L3 detail (self-contained, carries `parent: ./00-overview.md`)
└── 03-composicion-feed.md  <- L3 detail (self-contained, carries `parent: ./00-overview.md`)
```

### L1 overview file (`00-overview.md`)

- **File name**: `00-overview.md`
- **Content**: <= 500 tokens (2–3 lines of context + table of children + prerequisites)
- **Frontmatter**: Shape A with `children: [./01-..., ./02-...]`

### L3 detail file (`NN-{section-slug}.md`)

- **File name**: zero-padded numeric prefix (`01-`, `02-`, ...)
- **Content**: self-contained, starting with `> [!info] When to load`
- **Frontmatter**: Shape A with `parent: ./00-overview.md`

## When to re-split

If an artifact grows past ~3000 tokens during `judge-spec` iteration:

1. Ask the user for confirmation before splitting into `00-overview.md` + `NN-*.md` sections.
2. On approval, execute the split, set reciprocal `children` and `parent` frontmatter links, and continue on the relevant child.

## Anti-patterns

- Splitting a cohesive 1500-token artifact "just in case".
- Creating L1 overviews longer than 500 tokens.
- Missing reciprocal `parent` or `children` links in frontmatter.
- Naming children without zero-padding (`1-section.md` instead of `01-section.md`).

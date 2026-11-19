---
title: Frontmatter shapes — minimal YAML for artifacts, skills, and infrastructure
updated: 2026-11-17
related:
  - ./conventions.md
  - ./output-splitting.md
---

# Frontmatter shapes

> [!info] When to load
> Load when creating or validating any artifact, `SKILL.md`, or infrastructure document. Prerequisites: `.agents/conventions/conventions.md`.

## Three shapes

The kit uses **three frontmatter shapes**, one per purpose. Each is as small as possible to minimize standing context cost.

| Shape | Files | Required fields |
|---|---|---|
| **A — Project artifact** | `personas/`, `journeys/`, `features/`, `business-context/`, `architecture/`, `estimaciones/` | `type`, `status`, `updated` |
| **B — Skill** | `.agents/skills/{name}/SKILL.md` | `name`, `description` |
| **C — Agent infrastructure** | `.agents/conventions/*.md`, skill `rubrics/` and `rubric-*.md` | `title`, `updated` |

> **Language note:** frontmatter keys and reserved values (`type`, `status`) are **always English**. The artifact *body* follows the two-tier policy (`naming-and-language.md`).

---

## Shape A — Project artifact

### Minimal

```yaml
---
type: spec
status: approved
updated: 2026-11-17
---
```

### Type vocabulary

| Category | `type` values | Purpose |
|---|---|---|
| **definition** (the WHAT) | `user-persona`, `user-journey`, `user-story`, `spec`, `adr`, `decision`, `business-context` | Parallel ways to define what to build |
| **implementation** (the HOW) | `plan`, `tasks` | Materialize how to build the definition |
| **estimation** (the HOW MUCH) | `estimate` | Effort and sprints of a journey or feature in `estimaciones/` |

> **Plan companions.** The field-level companions a plan may carry (`data-model.md`, `api.md`, `event.md`, `test-plan.md`, co-located with `plan.md`) are **plan fragments**, not a separate artifact kind. They carry **`type: plan`** (optionally `parent: ./plan.md`).

### Status vocabulary and state machine

Closed set:

```text
draft | review | needs-work | approved | implemented | archived | superseded | legacy-pending-review
```

State machine:

```text
draft ──> review ──> needs-work ──> review ──> approved ──> implemented
                                                  │
                                                  ▼
                                            archived | superseded

(initial for migrated content)
legacy-pending-review ──> review (when judge-spec starts processing)
```

**Scope:** this machine governs **definition artifacts** (`spec`, `user-journey`, `user-story`, `adr`, `decision`, `user-persona`, `business-context`) — the artifacts `judge-spec` approves. **Implementation artifacts** (`plan`, `tasks`) are derived from an already-approved specification and use a minimal lifecycle (`draft` -> human review -> consumed by the next skill); they carry no separate approval flip. **The specification is the approval spine.**

### Optional fields (add only when they aid)

```yaml
version: 1.0.0                 # bump on intentional iteration
owner: "@handle"               # if not implicit from path
related: [...]                 # cross-refs not obvious from markdown links
parent: ./00-overview.md       # split-child only
children: [...]                # split-overview only
spec: ./spec.md                # plan/tasks only — pointer to the source specification
target_repos: [...]            # plan/tasks — repos the feature touches
spec_version: 1.0.0            # plan/tasks — the spec version or updated date this plan was built from (staleness guard)
vault_provenance: 2026-11-17   # plan — date of the vault/repo snapshot the plan was grounded on
```

---

## Shape B — Skill

### Minimal

```yaml
---
name: drill-docs
description: |
  Use when unstructured input (idea, brain dump, doc, transcript, research
  notes) must become a candidate artifact (user-journey, user-story, spec,
  ADR, decision, business-context). Runs an iterative Q&A drill; the draft
  stays in chat for save-output. Do NOT use if the artifact is already on
  disk (judge-spec) or for implementation planning (plan-feature).
---
```

Aligned with the open Agent Skills specification: `name` + `description` are the only required fields.

### Optional fields

```yaml
version: 1.0.0
runtime: interactive | autonomous | both | agnostic
allowed-tools: [...]
triggers: [user]
```

---

## Shape C — Agent infrastructure

For `.agents/conventions/*.md`, skill `rubrics/*.md`, and `rubric-*.md`:

```yaml
---
title: <Human-readable title>
updated: YYYY-MM-DD
related:
  - ./conventions.md
---
```

## Anti-patterns

- Adding fields without a concrete consumer (e.g., manual SHA-256 item maps or token counts in frontmatter).
- Inventing new `type` or `status` values outside the closed vocabulary.
- Writing frontmatter keys or reserved values in Spanish — they are always English.

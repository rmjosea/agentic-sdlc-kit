---
title: SKILL.md schema — canonical skill format and limits
updated: 2026-11-17
related:
  - ./frontmatter-schema.md
  - ./composition.md
---

# SKILL.md schema

> [!info] When to load
> Load when authoring a new skill with `create-skill` or reviewing changes to any `.agents/skills/{name}/SKILL.md`. Prerequisites: `frontmatter-schema.md` (Shape B).

## Minimal SKILL.md

```markdown
---
name: <skill-name-kebab>
description: |
  Use when <concrete triggers and problem solved>. Do NOT use when
  <non-triggers and alternative skill to use instead>.
---

# <Skill Title>

## When to use
## When NOT to use
## Inputs
## Outputs
## Process
## Anti-patterns
## References
```

## Hard limits

- **`name` <= 64 chars**, kebab-case, matching the directory name `.agents/skills/{name}/`.
- **`description` <= 1024 chars**, must include `"Use when"` and explicit non-triggers (`"Do NOT use..."`).
- **Body <= 200 lines target** (500 lines hard limit in the Agent Skills specification). Move deep tables, rubrics, and templates to `references/`, `rubrics/`, or `assets/`.
- **Local links stay inside the skill directory.** Links `[label](<relative-path>)` inside `SKILL.md` must resolve within `.agents/skills/{name}/`. Reference global files using inline code paths such as `` `.agents/conventions/conventions.md` ``.

## Two rubric homes by purpose

1. **Artifact rubrics** (`.agents/skills/judge-spec/rubric-{type}.md`) — score definition and derived artifacts (`spec`, `user-journey`, `user-story`, `adr`, `plan`, `tasks`). Owned by `judge-spec`.
2. **Juez code rubrics** (`.agents/skills/implement/rubrics/{stack}.md`) — score generated code diffs per stack (`python`, `node-ts`, `java`, `frontend`). Owned by `implement`.

Both validate as **Shape C** (`title` + `updated`).

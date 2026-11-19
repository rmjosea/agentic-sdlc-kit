---
title: How to invoke skills
updated: 2026-11-17
related:
  - ./composition.md
  - ./conventions.md
---

# How to invoke skills

> [!info] When to load
> Load when helping a user trigger, chain, or troubleshoot Agent Skills. Prerequisites: `AGENTS.md`.

## Three ways to trigger a skill

### Option 1 — Implicit (description match)
Describe what you want in natural language. The agent matches your request against each `.agents/skills/{name}/SKILL.md` `description` and loads only the matching skill:

```text
> Tengo este documento sin estructurar, ayúdame a sacar la spec.
```

*(Note: skills with `triggers: [user]` in frontmatter require explicit invocation via Option 2).*

### Option 2 — Explicit (recommended when in doubt)
Name the skill or use `/<skill-name>`:

```text
> Invoca la skill drill-docs sobre este texto: ...
> Usa judge-spec sobre features/005-cambio-iban/spec.md
> Ejecuta plan-feature sobre features/005-cambio-iban/spec.md
> Ejecuta breakdown-tasks sobre features/005-cambio-iban/plan.md
> Ejecuta implement sobre features/005-cambio-iban/tasks.md
> Ejecuta close-spec sobre features/005-cambio-iban/spec.md
```

### Option 3 — Composed chain
Declare the desired chain upfront; the agent runs one gate at a time and asks for confirmation at each approval boundary:

```text
> Quiero ir de esta nota al spec aprobado: drill-docs -> save-output -> judge-spec.
```

## When manual edits are allowed vs discouraged

- **Allowed without a skill:** fixing a typo, updating a link, or minor formatting while keeping `updated: YYYY-MM-DD` current.
- **Do not bypass skills for:** flipping `status` (`judge-spec` or `close-spec`), adding/removing acceptance criteria (`judge-spec`), generating a technical plan (`plan-feature`), decomposing tasks (`breakdown-tasks`), or implementing and validating tasks (`implement`).

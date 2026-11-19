---
name: save-output
description: Use when a chat-resident draft (typically from drill-docs or a user-supplied structured draft) must be materialized to disk with canonical Shape A frontmatter, applying the matching template and splitting per output-splitting rules when large. Do NOT use to edit or judge an existing on-disk artifact (use judge-spec) or to write an implementation plan (use plan-feature).
---

# save-output

Materialize an approved or structured chat draft into the canonical repository path with Shape A frontmatter and progressive-disclosure splitting when warranted.

## When to use

- A `drill-docs` session produced a structured draft in chat that is ready to persist.
- The user provides a structured draft and asks to save it as a `spec`, `user-journey`, `user-story`, `adr`, `decision`, `user-persona`, or `business-context` file.
- An existing artifact crossed the ~3000-token split threshold and needs reorganization into `00-overview.md` + `NN-*.md`.

## When NOT to use

- Iteratively clarifying, scoring, or editing an existing artifact on disk -> use `judge-spec`.
- Designing how to implement an approved specification -> use `plan-feature`.

## Resolve configured roots

Before writing, inspect `.agents/project.md`; if it exists, report it as unsupported and stop. If `.agents/project.json` exists, validate it with `.agents/skills/setup/assets/project.schema.json` and apply `.agents/skills/setup/references/project-config.md`; stop on any invalid config. Use configured roots when present, or the standard defaults below (`features/`, `journeys/`, `personas/`, `business-context/`, `architecture/adr/`).

## Inputs

- The chat-resident structured draft.
- Target artifact `type`, feature number/slug, or path (confirmed with the user when not obvious).

## Outputs

- Artifact file(s) written under the canonical path per `.agents/conventions/conventions.md`:
  - `features/{NNN}-{feature-slug}/spec.md` (single) or `features/{NNN}-{feature-slug}/spec/00-overview.md` + `NN-*.md` (split)
  - `features/{NNN}-{feature-slug}/stories/US-{N}-{kebab-slug}.md`
  - `journeys/{feature}/{ID-prefix}-{NN}-{kebab-slug}.md` (single) or `.../{kebab-slug}/00-overview.md` (split)
  - `personas/{kebab-slug}.md`
  - `business-context/{kebab-slug}.md`
  - `architecture/adr/adr-{NNNN}-{kebab-slug}.md`
  - `features/{NNN}-{feature-slug}/decisions.md`
- Shape A minimal frontmatter (`type`, `status: draft`, `updated: YYYY-MM-DD`).

## Process — Confirm -> Template -> Fill -> Frontmatter -> Split check -> Write

### 1. Confirm type and target path

1. Confirm the artifact `type` and target path with the user when any ambiguity exists, following the `AGENTS.md` human decision protocol (one question at a time, options with one marked **Recommended**).
2. Format slugs in kebab-case in the project's business language per `.agents/conventions/naming-and-language.md`.

### 2. Apply template and fill content

3. Load the matching template from this skill's assets:
   - [assets/spec.template.md](assets/spec.template.md) for `type: spec`
   - [assets/user-journey.template.md](assets/user-journey.template.md) for `type: user-journey`
   - [assets/user-story.template.md](assets/user-story.template.md) for `type: user-story`
   - [assets/adr.template.md](assets/adr.template.md) for `type: adr`
4. Fill placeholders from the draft and remove HTML guidance comments (`<!-- ... -->`). **Preserve every unresolved question as `[NEEDS CLARIFICATION]` with an owner** — never fabricate metrics, personas, or requirements.

### 3. Prepend Shape A frontmatter and check split threshold

5. Set Shape A frontmatter (`type`, `status: draft`, `updated: YYYY-MM-DD`).
6. Check `.agents/conventions/output-splitting.md`: estimate tokens as `bytes / 4`. Keep a single cohesive artifact in one file unless it groups **>=3 genuinely independent artifacts OR exceeds ~3000 tokens**. When splitting, write `00-overview.md` (`children: [...]`) and zero-padded `NN-{slug}.md` children (`parent: ./00-overview.md`).

### 4. Write safely

7. If the destination file already exists, ask for explicit confirmation before overwriting.
8. Report the written path(s), `status: draft`, and any `[NEEDS CLARIFICATION]` items. Recommend `judge-spec` as the next step.

## Anti-patterns

- Overwriting an existing file without explicit user confirmation.
- Inventing content to fill template sections instead of marking `[NEEDS CLARIFICATION]`.
- Splitting a cohesive <3000-token artifact into multiple fragments unnecessarily.
- Writing frontmatter keys or reserved `type`/`status` values in Spanish.

## References

- [assets/spec.template.md](assets/spec.template.md)
- [assets/user-journey.template.md](assets/user-journey.template.md)
- [assets/user-story.template.md](assets/user-story.template.md)
- [assets/adr.template.md](assets/adr.template.md)
- `.agents/conventions/frontmatter-schema.md` (Shape A)
- `.agents/conventions/output-splitting.md`

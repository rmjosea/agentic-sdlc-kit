---
title: Naming and Language — Content Conventions
updated: 2026-11-17
related:
  - ./conventions.md
---

# Naming and Language — Content Conventions

> [!info] When to load
> Load before creating files or folders, renaming artifacts, or writing prose across harness and business layers. Prerequisites: `.agents/conventions/conventions.md`.

Two paired conventions apply across the repository: how files and directories are **named** on the filesystem and what **language** their content is written in.

## 1. Naming — kebab-case

All file and folder names **must use kebab-case**: lowercase letters and digits only, words joined by single hyphens (`-`), no spaces, underscores, capitals, or special characters. Numeric prefixes are encouraged for ordering (e.g., `001-onboarding/`, `01-camino-feliz.md`).

### Naming exceptions

- **Dot-prefixed config dirs and files**: `.git/`, `.github/`, `.agents/`, `.gitignore`.
- **Standard convention files**: `README.md`, `AGENTS.md`, `SKILL.md`, `MODULE.md`, `CHANGELOG.md`, `CODEOWNERS`, `LICENSE`, `Makefile`, `Dockerfile`.
- **External knowledge vaults (`vault/`)**: managed by external deepwiki/indexing tooling.
- **Uppercase ID prefixes** (e.g., `DF-T0-01-ver-tutorial.md`, `US-1-primer-acceso.md`, `ADR-0001-decision.md`): stable identifiers may keep their uppercase prefix while the slug stays kebab-case.

### Renaming workflow

1. Use `git mv` to preserve history.
2. On case-insensitive filesystems (macOS/Windows), use a temporary intermediate name for case-only renames (`git mv Plan __tmp__ && git mv __tmp__ plan`).
3. Update all Markdown, JSON, and HTML references across the repository.

## 2. Language — two tiers (infra EN / business project language)

Pick the language tier by what the file *is*:

| Tier | Scope | Language |
|---|---|---|
| **Harness infrastructure** | `AGENTS.md`, `.agents/**`, `scripts/**`, root `README.md` | **English** |
| **Business artifacts** | `personas/`, `journeys/`, `features/`, `business-context/`, `architecture/adr/`, `estimaciones/` | **Spanish** (default, or configured project business language) |
| **Conversation** | Chat between human and agent, PR comments | Speaker's choice |

- **Frontmatter** (YAML keys and reserved values like `type` and `status`) is **always English**, regardless of the artifact's content tier.
- **Filename slugs** follow kebab-case in both tiers: business slugs use the business language (`005-cambio-iban`), infrastructure slugs use English (`loading-recipes.md`).

### Language exceptions (within a tier)

- **Proper nouns**: product, persona, organization, or brand names.
- **Canonical technical terms** inside Spanish artifacts: keep standard technical terms (*endpoint*, *deploy*, *rollback*, *payload*, *mock*) rather than forcing unnatural translations.
- **Quotes** from regulations or user research: preserve verbatim in the original language.
- **Machine-readable contracts** (`openapi.yaml`, AsyncAPI, JSON Schema, Proto): follow upstream code/schema conventions.

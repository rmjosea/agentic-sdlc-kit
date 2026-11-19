---
title: Loading recipes — what to load per skill and task type
updated: 2026-11-17
related:
  - ./conventions.md
  - ./frontmatter-schema.md
  - ./runtimes.md
---

# Loading recipes

> [!info] When to load
> Load when starting a skill and deciding which files to pull into context. Prerequisites: `AGENTS.md`.

## Universal context discovery (Zero-Lock-in, 3 levels)

The kit never requires a specific `vault/` folder layout. Resolve codebase context in this order:

| Level | When used | What to read |
|---|---|---|
| **1. Configured context or `vault/` (any layout)** | When `roots.domain_context` is set in `.agents/project.json` or a `vault/` directory exists (whether organized as `vault/20-Repos/`, `vault/repositorios/`, `vault/componentes/`, or flat Markdown) | Query matching repo/component/architecture summaries first to narrow scope, then **verify cited file paths against the live codebase** (code is the source of truth if the index is stale). |
| **2. Standard repository (no `vault/`)** | Default for any repository without a separate knowledge vault | Read the target repository's `AGENTS.md`, package/build manifests (`package.json`, `pyproject.toml`, `pom.xml`, `go.mod`), and focused module/test files. |
| **3. Iterative Retrieval (max 3 cycles)** | Whenever `drill-docs`, `plan-feature`, or `implement` needs to locate existing behavior or components across a codebase | **Cycle 1 (Dispatch):** Search broad domain/feature keywords.<br>**Cycle 2 (Evaluate & Refine):** Score candidates (`0.0–1.0`), learn the repository's actual naming/terminology, drop `<0.2` noise, and query missing gaps.<br>**Cycle 3 (Stop at Good Enough):** Stop as soon as **3–5 high-relevance (`>= 0.7`) files** are identified. Never dump whole directories into context. |

## Search-First rule (Adopt -> Extend -> Compose -> Build)

Before proposing or writing any new utility, helper, service, or UI component:

1. **Repo & internal catalog first:** Check whether the repository or its installed internal libraries/design system already provide the function or component. Reuse it (**Zero Duplication**).
2. **Governed external search (only if missing internally):** When a capability does not exist in the codebase, search official registries/docs, require a release published **>= 7 days ago** with **0 known vulnerabilities (OSV.dev)**, and present 2–3 options with **1 Recommended** (triggering an ADR if costly to reverse).

## Reading a big file

Never read a large file (>2 KB) whole to answer one question:

1. List its headings with line numbers (`grep` for `^#`).
2. Read only the section needed using line `offset` and `limit`.
3. Widen to a neighboring section only if the step is still not addressable.
4. Use content-hash (`SHA-256` via `.agents/tools/fingerprint_artifact.py`) to skip re-processing unchanged files during batch or vault updates.

## Context budget

- **One task per session.** Start a new session for an unrelated task, carrying only a short summary.
- **Broad exploration -> read-only subagent** when supported and explicitly requested, keeping only its concise summary.
- **Bulk operations -> deterministic script** in the skill's `scripts/` folder rather than repeated chat turns.

---

## Recipes by skill

### Recipe — `drill-docs`
1. `.agents/conventions/conventions.md` § Artifact categories
2. `.agents/conventions/frontmatter-schema.md` § Type vocabulary
3. `.agents/skills/save-output/assets/` (candidate templates to recommend a type)
4. **Brownfield L1 check (when modifying an existing product):** 1-cycle Iterative Retrieval over Level 1/2 context to detect existing capabilities or contradictions before asking questions

### Recipe — `save-output`
1. `.agents/conventions/frontmatter-schema.md` § Shape A
2. `.agents/conventions/output-splitting.md` § Rule + § Split form
3. `.agents/conventions/conventions.md` § Slug and path conventions
4. `.agents/skills/save-output/assets/{type}.template.md`

### Recipe — `judge-spec`
1. The artifact being judged
2. `.agents/skills/judge-spec/rubric-{type}.md` (only the matching rubric)
3. `.agents/conventions/frontmatter-schema.md` § Status vocabulary
4. Optional L1 repo/context summary (Level 1/2 above) + project glossary for advisory grounding and terminology checks

### Recipe — `plan-feature`
1. The approved specification (`features/{NNN}-{slug}/spec.md`, story, or journey)
2. `.agents/skills/plan-feature/assets/plan.template.md`
3. `.agents/conventions/conventions.md` § Plan with supporting files
4. Target repo context via Universal Context Discovery (Level 1/2 + Iterative Retrieval max 3 cycles + Search-First)
5. `.agents/skills/judge-spec/rubric-plan.md` (to verify before handoff)

### Recipe — `breakdown-tasks`
1. The reviewed plan (`features/{NNN}-{slug}/plan.md` + companions)
2. `.agents/skills/breakdown-tasks/assets/tasks.template.md`
3. `.agents/conventions/runtimes.md` (to tag `[I]` / `[A]` / `[*]`)
4. `.agents/skills/judge-spec/rubric-tasks.md` (to verify bidirectional traceability)

### Recipe — `implement`
1. The `tasks.md` group for the active target repo (`--repo <id>` or selected `T0x`)
2. `features/{NNN}-{slug}/plan.md` + companions (`data-model.md`, `api.md`, `event.md`, `test-plan.md`)
3. `.agents/skills/implement/rubrics/{stack}.md` (only the active stack's juez rubric)
4. Target repo `AGENTS.md` (or Level 1/2 context + cited golden-example file in the codebase)

### Recipe — `close-spec`
1. The source specification (`features/{NNN}-{slug}/spec.md`, story, or journey)
2. `features/{NNN}-{slug}/tasks.md` (confirm all tasks `[x]`)
3. `features/{NNN}-{slug}/plan.md` (§5 coverage spine)

---

## Org-standards trigger policy

If the repository provides organization-wide standards (such as `.agent/reference/org-standards.md` or `.agents/conventions/org-standards.md`), **never preload them by default**. Load only the triggered section when the artifact touches one of these sensitive areas:

| Area | Trigger keywords in the artifact |
|---|---|
| Authentication / authorization | login, JWT, OAuth, Keycloak, session, multi-tenant scope, role, RBAC |
| PII / data privacy | email, DNI, NIF, IBAN, name, address, phone, payment, GDPR, consent, retention |
| AI features | prompt, LLM, eval, scoring, golden dataset, hallucination, PII in prompts |
| Security boundaries | input validation, sanitization, file upload, shell exec, deserialization |
| Persistence / schema | new collection/table, migration, data classification, encryption at rest |
| Observability / errors | error response, stack trace, log content, correlation id |

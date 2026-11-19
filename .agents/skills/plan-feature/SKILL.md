---
name: plan-feature
description: Use when an approved specification (spec, user-story, or user-journey with testable ACs) must become a technical plan (plan.md with file changes, NFRs, decisions, risks, verification per AC) plus field-level zero-invention companions (data-model.md, api.md, event.md, test-plan.md) for new interfaces, detecting target_repos. Do NOT use while the spec is draft/review (use judge-spec) or if the plan is already reviewed (use breakdown-tasks).
---

# plan-feature

Convert an approved specification into an execution-ready technical plan with zero-invention field-level companions and explicit `target_repos`.

## When to use

- A specification on disk (`features/{NNN}-{slug}/spec.md`, a `user-story`, or a `user-journey`) has `status: approved` and testable acceptance criteria.
- A previously approved specification was amended and re-approved, requiring a refreshed technical plan.

## When NOT to use

- The specification is still `draft`, `review`, or `needs-work` -> use `judge-spec` first.
- A reviewed `plan.md` already exists -> use `breakdown-tasks`.
- The change is XS/S with no new interface, behaviour change, or sensitive surface -> use the Lightweight lane (`.agents/conventions/change-lanes.md`).

## Resolve configured roots

Before writing, inspect `.agents/project.md`; if it exists, report it as unsupported and stop. If `.agents/project.json` exists, validate it with `.agents/skills/setup/assets/project.schema.json` and apply `.agents/skills/setup/references/project-config.md`; stop on any invalid config. Write co-located inside `features/{NNN}-{slug}/` (or the configured work/features root).

## Inputs

- Path to the approved specification (`spec.md`, `user-story`, or `user-journey`).
- Optional known `target_repos` (otherwise detected via Universal Context Discovery).
- Optional technical direction, architecture constraints, or technology choices specified by the technical lead.

## Outputs

- `features/{NNN}-{slug}/plan.md` using [assets/plan.template.md](assets/plan.template.md) (or `plan/00-overview.md` + `NN-*.md` if crossing the ~3000-token split threshold in `.agents/conventions/output-splitting.md`).
- **Field-level companions (zero-invention, invention-driven):** co-located in `features/{NNN}-{slug}/`, one per NEW interface type the change introduces (`data-model.md`, `api.md`, `event.md`, `test-plan.md`). Never create an empty companion.
- Shape A frontmatter (`type: plan`, `status: draft`, `updated: YYYY-MM-DD`, `spec: ./spec.md`, `spec_version`, `vault_provenance`, `target_repos: [...]`).

## Process — Explore -> Interrogate -> Plan -> Verify

### 1. Explore (Code as Source of Truth, Iterative Retrieval & Search-First)

1. Read the approved specification (the Delta contract) and extract the complete **AC list**, constraints, and any user-supplied technical direction.
2. **Detect `target_repos` and ground in the live codebase (`.agents/conventions/loading-recipes.md`):**
   - **Executable code in the base branch is the source of truth.** Never rely on old specifications to infer current behavior.
   - Use **Universal Context Discovery** (configured `roots.domain_context` / `vault/` of any layout if present, or target repo `AGENTS.md` + package/build manifests) combined with **Iterative Retrieval (max 3 cycles)** to locate the 3–5 high-relevance (`>= 0.7`) files owning the behavior and verify cited paths in the repo.
3. **Apply Search-First (Adopt -> Extend -> Compose -> Build):**
   - Check whether required utilities, domain services, or UI design-system components already exist in the repository or shared internal libraries so the plan reuses them (**Zero Duplication**).
   - If the user specified a technology/architecture choice, contrast it against the repository's existing stack: adopt it directly if aligned, or flag any conflict/trade-off for step 2.
   - If a needed capability does **not** exist in the project and was not specified, perform a governed external search (official docs/registries, release published **>= 7 days ago**, **0 known CVEs in OSV.dev**) to prepare 2–3 candidate options for step 2.

### 2. Interrogate (close unknowns one question at a time)

4. Build a **decision ledger** of material unknowns: missing interface fields, contract divergences, NFR targets, scope edges, repo ownership, or new technology proposals.
5. Resolve the ledger with the human **one question at a time, each building on the last**, following the `AGENTS.md` human decision protocol (plain language, why it matters, 2–4 options with one **Recommended** grounded in repo evidence or governed search). When a new dependency or costly-to-reverse architectural choice is confirmed, record the ADR obligation.
6. Record every confirmed answer + rationale + rejected alternative in plan **§4**. Keep `[NEEDS CLARIFICATION]` only for genuinely deferred items (with `@owner` + default + impact).
7. **Mutual-understanding checkpoint:** read back a 4–6 line plain-language summary of WHAT will be built, key decisions, reused components, and `target_repos`, and wait for explicit human confirmation before writing the plan.

### 3. Plan (fill template and zero-invention companions)

8. Apply [assets/plan.template.md](assets/plan.template.md). Cite the repository source (manifest, `AGENTS.md`, or verified context card) for every stack/library value in **§2 Technical Context** — never invent libraries or versions.
9. Fill **§3 Changes per repo**, listing existing functions/services/UI design-system components to reuse and citing a proven golden-example file in each repo. For every NEW interface (persisted model, API endpoint, event), create its matching companion (`data-model.md`, `api.md`, `event.md`) defined **field-by-field** (names, types, enums, validation, defaults, error codes, and deterministic UI `data-testid` selectors when UI changes) so Backend and Frontend teams can implement in parallel without blocking each other.
10. State **cross-cutting concerns** in **§4** (security and privacy/PII/consent are mandatory; add a11y, i18n, observability, performance, compatibility, rollout when applicable).

### 4. Verify (AC -> 3-ring check matrix and `test-plan.md`)

11. Map **every AC and NFR** to a concrete observable check in **§5** and `test-plan.md` as Given/When/Then with concrete **inputs + expected output** across up to **3 verification rings**:
    - **Ring 1 (Task/Unit & Contract):** unit/integration/property tests (or differential tests using the old implementation as oracle during migrations) + field-level contract conformance (`api.md`/`event.md`).
    - **Ring 2 (Feature E2E):** focused end-to-end test (e.g., Playwright / browser / live API harness over `data-testid` selectors) when the feature changes user flows or crosses repos.
    - **Ring 3 (Full-App E2E Regression):** full application E2E regression gate required when tier is `L`/`XL` or the change touches shared cross-cutting surfaces.
12. Self-check against `.agents/skills/judge-spec/rubric-plan.md` (zero orphan ACs, zero invented interfaces, security/privacy stated, rollback in §6). Leave `status: draft` for human review and recommend `breakdown-tasks` once reviewed.

## Anti-patterns

- Planning from an unapproved specification (`draft`, `review`, or `needs-work`).
- Leaving new API/data/event fields unspecified for the coding agent to invent.
- Skipping `test-plan.md` or writing vague §5 checks ("funciona").
- Duplicating per-repo plans instead of listing `target_repos` in one canonical plan.

## References

- [assets/plan.template.md](assets/plan.template.md)
- `.agents/conventions/conventions.md` (§ Plan with supporting files)
- `.agents/conventions/loading-recipes.md` (§ Recipe `plan-feature`)
- `.agents/skills/judge-spec/rubric-plan.md`

---
title: rubric-plan — quality dimensions for plan artifacts (coverage and grounding)
updated: 2026-11-17
related:
  - ./SKILL.md
---

# Rubric — `plan`

> [!info] When to load
> Load to gate `plan-feature` output (`plan.md` and its field-level companions). Judges coverage, repository grounding, and zero-invention interface completeness.

## Quality dimensions

| # | Dimension | Pass criterion | Block on fail? |
|---|---|---|---|
| 1 | **Source provenance & freshness** | Frontmatter `spec:` points to the approved specification; `spec_version` and `target_repos` are set and current | Yes |
| 2 | **AC coverage (no orphan ACs)** | EVERY acceptance criterion of the specification appears in §1 "ACs cubiertos" AND has a verification row in §5 | Yes |
| 3 | **NFR / constraint coverage** | Every quantifiable NFR, security, or privacy constraint from the specification has a §5 check | Yes |
| 4 | **No scope drift** | The plan implements the approved WHAT without adding unapproved features or scope | Yes |
| 5 | **Technical Context grounded** | Every §2 stack/version value cites its repository source (live repo manifests/`AGENTS.md` or configured domain context/`vault/`) — no unverified or invented libraries | Yes |
| 6 | **Changes grounded & Search-First** | §3 targets real repos/modules, cites existing utilities/UI design-system components to reuse (**Zero Duplication**) plus a golden-example file; `target_repos` matches impacted repos | Yes |
| 7 | **Material unknowns resolved** | Material decisions are resolved with the human and recorded in §4; only genuinely deferred items remain `[NEEDS CLARIFICATION]` with owner + default + impact | Yes |
| 8 | **Verification observable** | Every §5 row is a concrete observable check (named test + inputs/expected in `test-plan.md`, or metric/review), never "works" | Yes |
| 9 | **Decisions justified** | §4 non-obvious decisions state *why* + *rejected alternative* | No — flag |
| 10 | **Rollback present** | §6 states a safe rollback path (feature flag, migration reversal, or revert) | No — flag |
| 11 | **Lean & scoped** | Single file unless crossing ~3000 tokens or >=3 independent concerns | No — flag |
| 12 | **Interface completeness (zero-invention)** | Every NEW persisted structure, endpoint, or event is defined field-by-field in `data-model.md`, `api.md`, or `event.md`; cross-repo contracts are pinned to the owning repo's schema | Yes |
| 13 | **Security & privacy stated** | Security and privacy/PII/consent are explicitly addressed in §4 (or justified N/A) | Yes |

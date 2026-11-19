---
title: Change lanes — full spec chain vs the lightweight lane (XS–XL)
updated: 2026-11-17
related:
  - ./conventions.md
  - ./composition.md
  - ./loading-recipes.md
---

# Change lanes

> [!info] When to load
> Load when sizing a request (XS–XL) or deciding whether a task requires the full specification chain vs the lightweight fast path. Prerequisites: `AGENTS.md`.

Not every change deserves the full `SPECIFY -> PLAN -> IMPLEMENT -> CLOSE` chain. Forcing a one-line copy fix or bounded bug-fix through `drill-docs -> save-output -> judge-spec -> plan-feature -> breakdown-tasks -> implement -> close-spec` is process theater. Pick the **smallest lane that safely fits**.

## Every task has a verifiable "done"

Whatever the lane or task type — code, bug-fix, research, documentation, or architectural decision — a task is not finished until it meets a **verifiable "done"**: a passing test, a checked acceptance criterion, or an explicit review sign-off. The lanes below only decide *how much durable process* wraps around that verification net.

## Size tiers (tallas XS–XL)

Every change is sized with a **tier** (XS–XL, "tallas") that maps directly onto two lanes:

- **XS / S -> Lightweight lane** (spec-free; the PR is the artifact).
- **M / L / XL -> Spec lane** (`drill-docs -> save-output -> judge-spec -> plan-feature -> breakdown-tasks -> implement -> close-spec`).

| Tier | Typical change | Lane | Required artifacts + skills | Gates |
|---|---|---|---|---|
| **XS** | Copy/i18n, config within policy, comments/docs, lint/format, dependency **patch** bump | **Lightweight** | **The PR is the artifact** (title + one-line rationale). No spec, no plan, no `tasks.md`. | Normal code review + existing checks green |
| **S** | Small bug-fix, bounded refactor — no interface or AC change | **Lightweight** | PR is the artifact; for a bug-fix, a failing **reproduction test first** (Karpathy #4) + per-stack juez rubric over the diff. **Spec-free.** | Code review + reproduction test green + juez APROBADO |
| **M** | Single-repo feature / observable functional change | **Spec** | `spec` (`save-output`) + `plan` (`plan-feature`) + `tasks` (`breakdown-tasks`) + PR (`implement`) | `judge-spec` approval + `close-spec` notary + Spec Review |
| **L** | Multi-repo or complex feature | **Spec** | M artifacts + `plan` with multiple `target_repos`, `tasks` tagged per `repo`, one PR per repo | M gates + Plan Review + repo-by-repo validation owned by `implement` |
| **XL** | Architectural change, high-risk / AI / regulated feature | **Spec** | L artifacts + ADR / governance record | L gates + org-standards triggers (`loading-recipes.md`) + independent review |

### Sizing a spec split across multiple tracker stories

When a specification ships as several issue-tracker stories, state its size as the **sum of the tiers of its stories**, each attributed to its issue key:

```markdown
**Talla: S (PROJ-101) + L (PROJ-102) + M (PROJ-103) — Spec lane.**
```

The lane is set by the **largest tier in the sum** (`S + M` rides the Spec lane because of `M`).

## The decision (30 seconds)

Use the **Lightweight lane** only if **ALL** five conditions are true:

- [ ] **No new interface** — no new/changed API endpoint, persisted field, event/message, or cross-service contract.
- [ ] **No behaviour / AC change** — nothing a user or external consumer can observe changes; no acceptance criterion is added or altered.
- [ ] **No sensitive surface** — does not touch security, auth, privacy/PII, consent, AI/eval, money, destructive operations, or data classification (`loading-recipes.md` § Org-standards trigger policy).
- [ ] **No new dependency** that requires an architectural decision (ADR).
- [ ] **Small** — one focused PR a reviewer can fully reason about in one session.

If **any** box is unchecked -> **Spec lane**.

## Developer fast path (Lightweight lane) — keep the quality net

Taking a task straight to code without a spec does **not** relax code quality. Three safeguards travel with every Lightweight change:

1. **Verifiable "done" (Test-first, Karpathy #4):** for a bug-fix, write a reproduction test that fails before the fix and passes after; for a bounded change, run the relevant test and lint suite.
2. **Per-stack juez rubric:** apply `.agents/skills/implement/rubrics/{stack}.md` over the `git diff` as a standalone quality checklist (no `tasks.md` required).
3. **Traceable commits:** follow `.agents/skills/git-conventions/SKILL.md`.

## Escape hatch

If, **mid-change**, you discover that a "trivial" Lightweight change actually touches an interface, changes observable behaviour/ACs, or hits a sensitive surface -> **STOP and switch to the Spec lane** (Karpathy #1: surface it immediately; never sneak a behaviour or contract change through a chore PR).

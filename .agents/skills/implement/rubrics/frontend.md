---
title: implement juez rubric — Frontend (Angular / TypeScript / Web + WCAG a11y)
updated: 2026-11-17
related:
  - ../SKILL.md
---

# Juez rubric — `frontend`

> [!info] When to load
> Load during `implement` (or a Lightweight-lane change) to score a **Frontend (Angular / TypeScript / Web component)** diff before committing and checking off a task.

## Quality dimensions

| # | Dimension | Pass criterion | Block on fail? |
|---|---|---|---|
| 1 | **Test exists & is observable** | The task's Verify is a real test in the repo's stack (Vitest, Karma/Jasmine, Jest, or Playwright) with concrete inputs + expected output; **fails before** and **passes after** | Yes |
| 2 | **Test + lint/build green** | `npm run test`, `npm run lint`, and `npm run build` (plus `tsc --noEmit` where strict TS is used) pass locally — cite exact command and result | Yes |
| 3 | **Minimal diff & Component Reuse** | Only the code the task requires; reuses components from the project's existing UI design system / shared component catalog before creating new ones; no unrelated template/style churn | Yes |
| 4 | **Matches repo conventions** | Follows the repo's architecture (`AGENTS.md` or configured context): standalone + `OnPush` + Signals in modern Angular repos, existing module/RxJS style in legacy modules, or the project's framework standard | Yes |
| 5 | **Types, `data-testid` & signature** | TypeScript strictness holds — no implicit `any`, inputs/outputs and services typed; matches plan companion field-for-field (including required `data-testid` selectors for E2E) | Yes |
| 6 | **Reactivity & lifecycle safety** | Signals/computed used cleanly or RxJS subscriptions cleaned up (`async` pipe / `takeUntilDestroyed`); no memory leaks | Yes — if applicable |
| 7 | **Accessibility (WCAG 2.1/2.2 AA)** | Semantic HTML/ARIA roles, keyboard operability, associated form labels, visible focus and error states; no critical/serious axe violations | Yes — if applicable |
| 8 | **i18n (no hardcoded copy)** | User-facing strings use the repository's localization mechanism (`@angular/localize` XLIFF, `ngx-translate` JSON, etc.) across required locales | Yes — if applicable |
| 9 | **No secrets / no PII leak** | No hardcoded tokens/endpoints; no PII in analytics payloads or `console.log` | Yes — if applicable |
| 10 | **No drive-by or shared-artifact mutation** | No unrelated reformatting; does not mutate external/shared design-system packages without explicit authorization; no weakened tests | Yes |
| 11 | **Traceability** | Commit follows repo convention (`git-conventions`), references task ID (`T0x`), and maps to `plan.md` §3 | No — flag |

## Verdict

- **APROBADO** = all `"Block on fail? Yes"` dimensions met -> commit + mark `[x]`.
- **RECHAZADO** = any blocking dimension unmet -> iterate with concrete fixes (circuit breaker stops after 2 failed attempts).

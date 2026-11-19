---
title: implement juez rubric — Node.js (Express / NestJS / TypeScript / JavaScript) stack
updated: 2026-11-18
related:
  - ../SKILL.md
---

# Juez rubric — `node-ts`

> [!info] When to load
> Load during `implement` (or a Lightweight-lane change) to score a **Node.js (Express, NestJS, Fastify, or hexagonal TypeScript/JavaScript)** backend diff before committing and checking off a task.

## Quality dimensions

| # | Dimension | Pass criterion | Block on fail? |
|---|---|---|---|
| 1 | **Test exists & is observable** | The task's Verify is a real test (Jest/Vitest + Supertest, `@nestjs/testing` `TestingModule`, or repo test runner) with concrete inputs + expected output; **fails before** and **passes after** | Yes |
| 2 | **Test + lint/build green** | Test + `npm run lint` (and `tsc --noEmit` / `npm run build` where TypeScript is used) pass locally — cite exact command and result | Yes |
| 3 | **Minimal diff & Zero Duplication** | Only the code the task requires; reuses existing repository utilities/providers/modules instead of duplicating logic; no speculative abstraction | Yes |
| 4 | **Matches repo conventions** | Follows the repository's architecture (`AGENTS.md` or configured context): NestJS (`@Module`, `@Controller`, `@Injectable` services, TypeORM/Prisma repositories) or Express/layered (`routes -> controller/domain -> db`) matching the cited golden-example | Yes |
| 5 | **Types, DTOs & signature** | Where TS: strict mode holds (no implicit `any`, public functions/DTOs typed). Signature and payload fields match the plan companion (`api.md`, `event.md`, `data-model.md`) field-for-field (zero invention) | Yes |
| 6 | **Injectable / testable** | Dependencies follow the repo's DI pattern (NestJS providers or constructor/factory injection) so unit tests do not mock the unit under test | Yes — if applicable |
| 7 | **Error handling & edge validation** | Request params/body validated at the edge (`class-validator`/`ValidationPipe`, Zod, Joi, or AJV); domain errors mapped cleanly; no empty `catch` blocks or silent fallback values hiding failures | Yes — if applicable |
| 8 | **No secrets / no PII leak** | No hardcoded secrets/tokens; sensitive fields (passwords, tokens, IBAN/PII) never logged or leaked in events | Yes — if applicable |
| 9 | **No drive-by or test weakening** | No unrelated reformatting/renaming; no weakened, skipped, or deleted existing tests | Yes |
| 10 | **Traceability** | Commit follows repo commit policy (`git-conventions`), references task ID (`T0x`), and maps to `plan.md` §3 | No — flag |

## Verdict

- **APROBADO** = all `"Block on fail? Yes"` dimensions met -> commit + mark `[x]`.
- **RECHAZADO** = any blocking dimension unmet -> iterate with concrete fixes (circuit breaker stops after 2 failed attempts).

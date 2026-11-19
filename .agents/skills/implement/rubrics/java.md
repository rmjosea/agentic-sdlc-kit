---
title: implement juez rubric — Java (Maven / Gradle / AEM / Spring) stack
updated: 2026-11-17
related:
  - ../SKILL.md
---

# Juez rubric — `java`

> [!info] When to load
> Load during `implement` (or a Lightweight-lane change) to score a **Java** diff (AEM/OSGi/Sling or Spring/Maven) before committing and checking off a task.

## Quality dimensions

| # | Dimension | Pass criterion | Block on fail? |
|---|---|---|---|
| 1 | **Test exists & is observable** | The task's Verify is a real test (JUnit 5 + Mockito / AEM Mocks) with concrete inputs + expected output; **fails before** and **passes after** | Yes |
| 2 | **Test + build green** | `mvn clean test` (or Gradle equivalent) and bundle/package verification pass locally — cite exact command and result | Yes |
| 3 | **Minimal diff & Zero Duplication** | Only the code the task requires; reuses existing repository utilities/services instead of duplicating logic; no speculative services or unrelated config edits | Yes |
| 4 | **Correct module + placement** | Classes and configs land in the right module/package per `AGENTS.md` (or configured project context) and cited golden-example | Yes |
| 5 | **DI / component wiring & signature** | Services registered behind interfaces and injected via `@Reference` / constructor DI (never ad-hoc `new` of managed services); signature matches plan companion | Yes |
| 6 | **Resource safety & idempotency** | Opened resources (`ResourceResolver`, `Session`, streams, connections) closed safely (`try-with-resources`); deterministic for test inputs | Yes — if applicable |
| 7 | **Error handling & input safety** | Edge cases handled; request parameters validated and XSS-encoded where applicable; no broad `catch (Exception)` swallowing errors | Yes — if applicable |
| 8 | **No secrets / no PII leak** | No hardcoded credentials/hosts in code; no PII in SLF4J logs | Yes — if applicable |
| 9 | **No drive-by or test weakening** | No unrelated reformatting; no weakened, skipped, or deleted existing tests | Yes |
| 10 | **Traceability** | Commit references task ID (`T0x`) and diff maps to `plan.md` §3 | No — flag |

## Verdict

- **APROBADO** = all `"Block on fail? Yes"` dimensions met -> commit + mark `[x]`.
- **RECHAZADO** = any blocking dimension unmet -> iterate with concrete fixes (circuit breaker stops after 2 failed attempts).

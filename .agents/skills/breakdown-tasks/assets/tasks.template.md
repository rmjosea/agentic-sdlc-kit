---
type: tasks
status: draft
updated: YYYY-MM-DD
spec: ./spec.md
target_repos:
  - {repo-backend}
  - {repo-frontend}
---

<!--
TEMPLATE — tasks (implementation / the HOW). Written by `breakdown-tasks`; gated by `rubric-tasks.md`; consumed by `implement`.
LANGUAGE: body in Spanish (business tier — lives in features/); keep canonical technical terms. Frontmatter keys + reserved values (type, status) in English.
PATH: features/{NNN}-{feature-slug}/tasks.md — a SINGLE file, tasks grouped by `repo`.
EACH TASK carries: `repo` tag · impact class (`accion` | `analisis` | `verificacion`) · runtime marker (`[A]` | `[I]` | `[*]`) · `-> AC-n` · `Verify:` lifted from plan §5 / test-plan.md · `Source:` pointer to plan §3 + companion section.
Fill every {placeholder} and delete these guidance comments before saving.
-->

# Tareas — {NNN}-{feature-slug}: {Título de la feature}

> Generado desde [`plan.md`](plan.md). Una tarea por iteración en contexto limpio de `implement`; marcar `[x]` solo tras veredicto APROBADO del juez.

## Tareas

### `{repo-backend}`

- [ ] **T01** — {Do: acción atómica y concreta} · `{repo-backend}` · accion · [A] · -> AC-1
  - **Verify:** {check observable tomado de plan §5 / test-plan.md — nunca inventado}
  - **Source:** plan §3 (`{repo-backend}`) + `api.md` §{sección}

### `{repo-frontend}`

- [ ] **T02** — {Do} · `{repo-frontend}` · accion · [I] · -> AC-2 · after: T01
  - **Verify:** {check observable de plan §5 / test-plan.md}
  - **Source:** plan §3 (`{repo-frontend}`)

## Bloqueadas

- [ ] **T{n}** — {Do} — **BLOCKED**: {pregunta} — owner: {@handle}

## Cola estándar

- [ ] **T{n}** — Cerrar la spec: verificar todas las tareas `[x]` + cobertura AC y registrar handoff · verificacion · [I] (`close-spec`)

## Trazabilidad (AC / NFR -> tarea)

| AC / NFR | Tareas |
|----------|--------|
| AC-1 | T01 |
| AC-2 | T02 |
| NFR — {métrica} | {tarea} |

## Dependencias

```text
T01 -> T02
```

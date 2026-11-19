---
type: spec
status: draft
updated: YYYY-MM-DD
---

<!--
TEMPLATE — spec (definition / the WHAT). Written by `save-output`; judged by `judge-spec` against rubric-spec.md.
LANGUAGE: body in Spanish (business tier); frontmatter keys + reserved values (type, status) in English.
PATH: features/{NNN}-{feature-slug}/spec.md (single) OR features/{NNN}-{feature-slug}/spec/00-overview.md + NN-*.md when grouping >=3 independent specs OR > ~3000 tokens (.agents/conventions/output-splitting.md).
RULE: a spec states QUÉ and POR QUÉ — never CÓMO. Technical approach, files and quantified NFRs belong in plan.md (rubric dim 12 — no HOW leakage).
Fill every {placeholder} and delete these guidance comments before saving.
-->

# Spec — {NNN}-{feature-slug}: {Título de la feature}

## Talla y lane

**Talla: {M / L / XL} — Spec lane.** Ver `.agents/conventions/change-lanes.md`.

## Problema

<!-- 2-4 frases desde el punto de vista del usuario, no del sistema (rubric dim 1). -->
{Qué problema del usuario resuelve esta feature.}

**Evidencia:**
<!-- >= 2 puntos de evidencia: cita de persona, dato de uso, decisión documentada o mecanismo de fallo (rubric dim 2). -->
- {evidencia 1}
- {evidencia 2}

**Personas / cohorte afectada:**
<!-- Quién se ve afectado y con qué alcance (rubric dim 3). -->
- [{persona}](../../personas/{persona-slug}.md) — {impacto}; alcance estimado: {N usuarios / % / volumen}

## Alcance

**EN scope (esta iteración):**
<!-- Capacidades numeradas, lideradas por verbo, observables (rubric dim 4). -->
- [ ] {capacidad 1}

**FUERA de scope (explícitamente excluido):**
<!-- Cada exclusión con enlace al artefacto que la cubre, si existe (rubric dim 5). -->
- {capacidad excluida} — cubierto por {artefacto/iteración}

## Constraints conocidos

<!-- Regulatorios (PII/GDPR), seguridad, accesibilidad, rendimiento, i18n (rubric dim 7, dim 11). -->
- {constraint regulatorio / seguridad / a11y / rendimiento}

## Dependencias

<!-- Servicios upstream / downstream y sus owners (rubric dim 8). -->
| Dependencia | Tipo | Owner |
|-------------|------|-------|
| {servicio / equipo} | upstream / downstream | {owner} |

## Criterios de aceptación

<!-- Formato Given/When/Then, cada AC verificable de forma independiente (rubric dim 6). Cubre happy path, casos de error y casos borde. -->
### {Capacidad o escenario 1}

```gherkin
Scenario: {título del escenario}
  Given {contexto, incluye rol RBAC si es relevante}
  When {acción}
  Then {resultado verificable}
```

## Métricas de éxito

<!-- >= 1 objetivo cuantificado (número + ventana temporal) (rubric dim 9). -->
| Métrica | Objetivo | Medición |
|---------|----------|----------|
| {métrica} | {objetivo cuantificado} | {evento / fuente} |

## Preguntas abiertas

<!-- Items pendientes con owner; se marcan [NEEDS CLARIFICATION] hasta resolverse (rubric dim 10). -->
- [ ] {pregunta abierta} — owner: {@handle}

## Referencias

- **Journeys**: {enlace a journeys/{feature}/}
- **Personas**: [{persona}](../../personas/{persona-slug}.md)
- **ADRs relacionadas**: {enlace a architecture/adr/adr-{NNNN}-{slug}.md}
- **Glosario**: {término(s) de business-context/glossary.md}

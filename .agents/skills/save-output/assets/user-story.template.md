---
type: user-story
status: draft
updated: YYYY-MM-DD
---

<!--
TEMPLATE — user-story (definition / the WHAT). Written by `save-output`; judged by `judge-spec` against rubric-user-story.md.
LANGUAGE: body in Spanish (business tier); frontmatter keys + reserved values (type, status) in English.
PATH: features/{NNN}-{feature-slug}/stories/US-{N}-{kebab-slug}.md
SCOPE: one INVEST story — Independent, Negotiable, Valuable, Estimable, Small (<= 1 sprint), Testable.
Fill every {placeholder} and delete these guidance comments before saving.
-->

# US-{N} — {Título de la historia}

## Historia

**Como** [{persona}](../../../personas/{persona-slug}.md) ({rol}),
**quiero** {capacidad},
**para** {resultado / valor}.

## Criterios de aceptación

### AC-1 — {nombre corto}

```gherkin
Scenario: {título del escenario}
  Given {contexto, incluye rol si es relevante}
  When {acción}
  Then {resultado verificable}
```

## Fuera de alcance

- {capacidad excluida} — cubierto por {historia/spec que lo trata}

## Notas INVEST

- **Independiente de**: {dependencias con otras historias en curso, o "ninguna"}
- **Tamaño estimado**: {cabe en un sprint — sí / partir en N historias}

## Definition of Done

- [ ] Tests cubren cada AC
- [ ] Seguridad / privacidad (PII) revisadas o N/A justificado
- [ ] Accesibilidad (WCAG 2.2 AA) si hay UI
- [ ] Telemetría / tracking instrumentado

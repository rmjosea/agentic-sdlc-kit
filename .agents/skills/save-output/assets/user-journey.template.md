---
type: user-journey
status: draft
updated: YYYY-MM-DD
---

<!--
TEMPLATE — user-journey (definition / the WHAT). Written by `save-output`; judged by `judge-spec` against rubric-user-journey.md.
LANGUAGE: body in Spanish (business tier); frontmatter keys + reserved values (type, status) in English.
PATH: journeys/{feature}/{ID}-{NN}-{kebab-slug}.md for a single cohesive journey.
SPLIT (only when grouping >=3 independent journeys OR > ~3000 tokens, per .agents/conventions/output-splitting.md): journeys/{feature}/{slug}/00-overview.md + NN-*.md.
Fill every {placeholder} and delete these guidance comments before saving.
-->

# {ID} — {Título del journey}

> **Feature**: {nombre de la feature} ({feature-slug}) | **Acción**: {qué consigue la persona}
> **Persona primaria**: [{persona}](../../personas/{persona-slug}.md)

## Introducción

{Contexto narrativo del journey en 2-4 frases.}

## Objetivo

{El/la {persona} consigue {resultado}, de modo que {valor}.}

## Persona

| Campo | Valor |
|-------|-------|
| **Persona primaria** | [{persona}](../../personas/{persona-slug}.md) — {rol} |
| **Rol / RBAC** | {rol en la plataforma} |
| **Contexto** | {situación, dispositivo, momento}. |

## Precondiciones

| # | Precondición |
|---|-------------|
| 1 | {estado previo necesario / trigger explícito} |

## Interacciones

### Interacción 1 — {nombre del paso}

| Paso | Actor | Acción | Resultado esperado |
|------|-------|--------|--------------------|
| 1.1 | {persona / Sistema} | {acción} | {resultado observable} |

## Flujos alternativos

| ID | Condición | Comportamiento |
|----|-----------|----------------|
| ALT-1 | {condición} | {comportamiento esperado} |

## Criterios de aceptación

| # | Given | When | Then |
|---|-------|------|------|
| AC-1 | {contexto, incluye rol si es relevante} | {acción} | {resultado verificable} |

## Métricas de éxito

| Métrica | Tipo | Objetivo |
|---------|------|----------|
| {métrica} | {eficiencia / conversión} | {objetivo cuantificado} |

## Notas y dependencias

| Tipo | Detalle |
|------|---------|
| **Componentes UI** | {superficies de frontend} |
| **Dependencias de servicio** | {servicios backend / eventos} |
| **Tracking** | {eventos de analítica} |
| **Fuera de alcance** | {qué NO cubre} — cubierto por {journey/spec} |
| **Journeys relacionados** | {ID y enlace a journeys hermanos} |
| **Permisos / RBAC** | {rol con acceso} |

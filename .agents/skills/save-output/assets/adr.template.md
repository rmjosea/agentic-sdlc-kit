---
type: adr
status: draft
updated: YYYY-MM-DD
---

<!--
TEMPLATE — adr (Architecture Decision Record · definition / the WHAT). Written by `save-output`; judged by `judge-spec` against rubric-adr.md.
LANGUAGE: body in Spanish (business tier); frontmatter keys + reserved values (type, status) in English.
PATH: architecture/adr/adr-{NNNN}-{kebab-slug}.md — {NNNN} 4-digit, zero-padded, sequential.
Fill every {placeholder} and delete these guidance comments before saving.
-->

# ADR-{NNNN} — {Título de la decisión}

> **Estado**: refleja el campo `status` del frontmatter (draft -> review -> approved -> implemented -> superseded -> archived).

## Contexto

{Fuerzas, constraints y antecedentes que motivan la decisión en 2-4 párrafos.}

## Decisión

**Usaremos {decisión}.**

{Detalle de la decisión: alcance, forma concreta, límites.}

## Consecuencias

### Positivas
- {beneficio}

### Negativas
- {coste / tradeoff aceptado}

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
|-------------|------|---------|---------------------|
| {alternativa A} | {pros} | {contras} | {motivo} |
| No hacer nada | {pros} | {contras} | {motivo} |

## Afecta a

- {repo / servicio / contrato}

## Migración y rollback

{Plan de migración y cómo revertir, o "N/A — decisión nueva sin sistemas afectados".}

## Referencias

- **Spec / journey origen**: {enlace}
- **Sustituye a / sustituida por**: {ADR relacionada, o "N/A"}

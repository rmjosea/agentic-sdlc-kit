---
type: plan
status: draft
updated: YYYY-MM-DD
spec: ./spec.md
spec_version: 0.0.0
vault_provenance: YYYY-MM-DD
target_repos:
  - {repo}
---

<!--
TEMPLATE — plan (implementation / the HOW). Written by `plan-feature`; gated against rubric-plan.md.
LANGUAGE: body in Spanish (business tier — lives in features/); keep canonical technical terms (endpoint, NFR, rollback). Frontmatter keys + reserved values (type, status) in English.
PATH: features/{NNN}-{feature-slug}/plan.md (single) OR a plan/ folder (00-overview.md + children) when crossing ~3000 tokens (.agents/conventions/output-splitting.md). Companions (data-model.md / api.md / event.md / test-plan.md) are added per new interface — invention-driven (.agents/conventions/conventions.md).
Fill every {placeholder} and delete these guidance comments before saving.
-->

# Plan — {NNN}-{feature-slug}: {Título de la feature}

## §1 Resumen

{Resumen del cambio en 3-5 líneas.} · Talla: **{M/L/XL}** · Repos: {lista de target_repos}.

**ACs cubiertos:**
- AC-1 — {resumen}

## §2 Contexto técnico

| Repo | Rol | Stack (versión) | Fuente (código / manifiesto / contexto) |
|------|-----|-----------------|-----------------------------------------|
| {repo} | {backend / frontend / lib} | {stack y versión} | {AGENTS.md / manifest / ficha de contexto} |

**Módulos afectados / restricted areas:**
- {módulo a tocar} ({repo})
- **NO TOCAR**: {área restringida} ({repo})

## §3 Cambios por repo

### {repo}

- **Reutilización (Search-First / Zero Duplication)**: {utilidades, servicios o componentes UI del sistema de diseño existentes que se reutilizan}
- {cambio concreto} — patrón: {golden-example citado en el repositorio}
- **Interfaz nueva** ({estructura persistida / endpoint / evento}): definir en {data-model.md / api.md / event.md} §{sección}; contrato cross-repo fijado al schema real de {repo owner}.

## §4 Decisiones y guardarraíles

### D1 — {decisión}
- **Decisión**: {qué se elige}
- **Por qué / alternativa rechazada**: {razón} / {alternativa descartada}

**Concerns transversales** (seguridad y privacidad/PII/consentimiento son obligatorios; el resto solo si aplica):
- **Seguridad / privacidad (PII)**: {cómo se aborda, o N/A justificado}
- **Otros** (observabilidad / a11y / i18n / rendimiento / compatibilidad / rollout): {si aplica}

**Blockers y riesgos:**
| # | Blocker / riesgo | Owner | Mitigación |
|---|------------------|-------|-----------|
| B1 | {blocker} | {@owner} | {acción} |

## §5 Verificación

| AC / NFR | Cómo se verifica (observable) | Repo |
|----------|------------------------------|------|
| AC-1 | {test nombrado + inputs/esperado en test-plan.md, o métrica/revisión} | {repo} |
| NFR — {métrica} | {medición} | {repo} |

## §6 Rollback

{Cómo revertir el cambio de forma segura: feature flag, reversión de migración o revert de deploy.}

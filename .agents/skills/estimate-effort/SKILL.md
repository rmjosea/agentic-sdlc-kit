---
name: estimate-effort
description: Use when the user asks to estimate effort, story points, or sprints for a journey, feature, or spec ("¿cuánto cuesta esto?", "¿cuántos sprints son?", "estima este journey/spec"), from real tallas (S/M/L) or a hypothetical S/M/L breakdown grounded in the repositories. Writes estimaciones/{slug}/estimacion.md (and optional HTML presentation) on confirmation. Do NOT use to change tallas or point individual stories in refinement.
---

# estimate-effort

Turn a feature or user journey into a transparent two-view effort and sprint estimate (`Optimista` and `Conservador`) grounded in calibrated size tiers (`tallas S / M / L`).

## The model

```text
Σ SP      = Σ (SP of each talla)               -> two views: optimistic and conservative
Σ SP      × (1 + journey extra)                -> only for multi-spec user journeys, never single features
sprints   = Σ SP / team capacity (range)       -> at 100% full-team dedication
```

Read [references/calibration.md](references/calibration.md) on **every** run; never hardcode Story Point or capacity numbers in memory.

## When to use

- User asks what a feature or journey costs in Story Points or sprints.
- A specification has sized stories (`Talla: S + M + L`) and needs a consolidated sprint projection.
- A `user-journey` exists before individual specs are written and needs an order-of-magnitude hypothetical S/M/L breakdown grounded in the affected repositories.

## When NOT to use

- Assigning or changing a change's tier/lane -> follow `.agents/conventions/change-lanes.md`.
- Unstructured idea with no scope yet -> run `drill-docs` first.

## Inputs

- **Mode A (Real tallas):** a specification or journey with declared story tiers (`S`, `M`, `L`).
- **Mode B (Hypothetical breakdown):** an on-disk `user-journey` or `spec` without story breakdown yet, plus repository context via Universal Context Discovery (configured `roots.domain_context` / `vault/` of any layout or target repo `AGENTS.md` + manifests).
- Calibration parameters in [references/calibration.md](references/calibration.md).

## Outputs

1. **Chat report:** breakdown of tallas, both views (`Optimista` and `Conservador`), journey extra (if journey), sprints at full team with capacity range, and any sizing warnings.
2. **On explicit user confirmation:** `estimaciones/{slug}/estimacion.md` with Shape A frontmatter (`type: estimate`, `status: draft`, `updated: YYYY-MM-DD`) and an updated row in `estimaciones/README.md`.

## Process

1. **Identify input mode (A or B) and work kind (`journey` vs `feature`):**
   - For Mode A, list each story and its tier (`S`, `M`, `L`). `XS` rides the Lightweight lane (0 SP); `XL` must be split into `S/M/L` before estimating.
   - For Mode B, inspect the affected repositories and split the journey into functional blocks of hypothetical HU-sized tasks (`S`, `M`, `L` — none `XL`), naming the target repo(s) per block.
2. **Optional sizing consistency check (warnings only):**
   - Cross-check each tier against `.agents/conventions/change-lanes.md` (e.g., flag a story marked `S` that introduces a new API endpoint or touches PII). Never silently alter a given tier.
3. **Compute both views from [references/calibration.md](references/calibration.md):**
   - Sum `Optimista` and `Conservador` Story Points separately.
   - Add the journey extra (`+15%` optimistic / `+25%` conservative) **only** for a `journey`, never for a single `feature`.
   - Divide by full-team sprint capacity (and its min–max range) and state explicitly that the figure assumes 100% team dedication (*"si el equipo dedica la mitad, el doble de sprints"*).
4. **Present and persist on confirmation:**
   - Show the complete markdown table in chat. Write `estimaciones/{slug}/estimacion.md` and update `estimaciones/README.md` only after explicit human confirmation.

## Anti-patterns

- Quoting only one view instead of both `Optimista` and `Conservador`.
- Applying the journey extra to a single feature.
- Editing totals by hand instead of recomputing from [references/calibration.md](references/calibration.md).

## References

- [references/calibration.md](references/calibration.md)
- `.agents/conventions/change-lanes.md`

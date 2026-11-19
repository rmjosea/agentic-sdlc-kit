---
title: estimate-effort — calibration reference (talla -> SP, team capacity, journey extra)
updated: 2026-11-17
related:
  - ../SKILL.md
---

# Calibration

> [!info] When to load
> Read on **every** run of `estimate-effort`. All numerical parameters for `estimate-effort` live in this file; adapt sections 1–3 to your team's historical velocity when recalibrating.

## 1. Talla -> Story Points

| Talla | **Optimista** (mean) | **Conservador** (median, Fibonacci) | Rule |
|---|---|---|---|
| **XS** | — | — | Lightweight lane; not estimated in SP |
| **S** | **3** | **3** | Bounded change, no new interface or AC change |
| **M** | **4** | **5** | Single-repo feature / observable functional change |
| **L** | **7.5** | **8** | Multi-repo or complex feature |
| **XL** | — | — | Must be decomposed into S / M / L stories before estimating |

- **Optimista** uses the empirical mean of completed stories and predicts sums across multiple stories.
- **Conservador** uses the Fibonacci median for risk-buffered planning.

## 2. Team capacity per sprint

- **Default baseline:** **54 SP per 3-week sprint, ±10% (49–60 SP)** at full team (100% dedication).
- Sprints are always expressed **at full team**: if a team allocates 50% of its capacity to the initiative, the calendar duration doubles.

## 3. Journey extra (journeys only)

Applied **only** to multi-spec **user journeys** (never to a single feature) to account for discovery spikes, cross-feature integration, end-to-end testing, and release close-out:

| View | Extra over Σ SP |
|---|---|
| Optimista | **+15%** |
| Conservador | **+25%** |

## 4. How to recalibrate for a project

1. Collect closed stories carrying `[Talla S/M/L]` across the last 3+ completed sprints with stable team composition.
2. Inspect outliers against their `features/{NNN}-{slug}/spec.md` to separate scope changes from sizing errors.
3. Recompute the mean (`Optimista`) and Fibonacci median (`Conservador`) per tier and the mean completed SP per sprint (`Team capacity`), then update this file's `updated` date.

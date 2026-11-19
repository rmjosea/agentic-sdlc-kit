---
schema_version: 2
id: "REVIEW-<N>"
type: "review-report"
sources: ["<authoritative source>"]
verdict: "approved"
---

# Review: <change>

## Scope

- Fixed base: `<fixed base>`
- Fixed head: `<fixed head>`
- Committed range: `<committed range>`
- Uncommitted scope: `<uncommitted scope>`
- Scope notes: <scope notes>

## Reviewer role and independence

- Reviewer role: <reviewer role>
- Reviewer ID: <reviewer id>
- Implementers: <implementers>
- Prior participation: <prior participation>
- Fresh context: `yes`
- Independence: `independent`
- Independence basis: <independence basis>
- Independence required: `yes`
- Independence met: `yes`

## Authoritative sources

| Priority | Source | Authority for | Gaps or conflicts |
|---|---|---|---|
| <priority> | <authoritative source> | <authority for> | <gaps or conflicts> |

## Risk

- Reviewer-assessed risk: `high`
- Risk rationale: <risk rationale>
- Required review depth/evidence: <required depth and evidence>

## Change contract and review focus

- What: <what>
- Authoritative why: <authoritative why>
- Contract scope: <contract scope>
- Required evidence: <required evidence>
- Contract risk: `high`
- Agent roles: <agent roles>
- Review focus: <review focus>
- Risk comparison/deviation: <risk comparison or deviation>
- Missing-contract impact: <missing-contract impact>

## Selected quality signals

| Signal | Disposition | Trigger / N/A reason | Evidence |
|---|---|---|---|
| Correctness | `selected` | <trigger or N/A reason> | <evidence> |
| Security | `selected` | <trigger or N/A reason> | <evidence> |
| Compatibility | `selected` | <trigger or N/A reason> | <evidence> |
| Maintainability | `selected` | <trigger or N/A reason> | <evidence> |
| Performance | `selected` | <trigger or N/A reason> | <evidence> |
| Accessibility | `selected` | <trigger or N/A reason> | <evidence> |
| Observability | `selected` | <trigger or N/A reason> | <evidence> |
| Cost | `selected` | <trigger or N/A reason> | <evidence> |
| Understandability | `selected` | <trigger or N/A reason> | <evidence> |

## Checks and evidence

| Check or procedure | Repository scope | Required | Applicability | Not-applicable reason | Status | Observed result | Evidence class | Requirement/risk covered |
|---|---|---|---|---|---|---|---|---|
| <check or procedure> | <fixed check scope> | `yes` | `applicable` | none | `passed` | <actual result> | `observed evidence` | <requirement or risk> |

## Findings

<finding records or none>

## Acceptance coverage

| Source item / criterion | Implementation evidence | Check evidence | Result |
|---|---|---|---|
| <source item or criterion> | <implementation evidence> | <check evidence> | `met` |

- Missing behavior: <missing behavior>
- Extra behavior: <extra behavior>
- Scope deviations: <scope deviations>

## Residual risk

- Residual risks: <residual risks>
- Unverified areas: <unverified areas>
- Required follow-up: <required follow-up>

## Verdict

- Selected verdict: `approved`
- Rationale: <verdict rationale>

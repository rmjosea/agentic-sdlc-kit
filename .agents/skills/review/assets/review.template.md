# Review: <change>

## Scope

- Fixed base: `<immutable identifier>`
- Fixed head: `<immutable identifier>`
- Committed range: `<base>..<head>`
- Uncommitted scope: `<staged, unstaged, and untracked paths; or none>`
- Scope notes: `<repositories, exclusions, drift, or access limits>`

## Reviewer role and independence

- Reviewer role: `<identity and review role>`
- Implementer(s): `<identity or role; unknown if unavailable>`
- Prior role: `<implementation/validation/review participation; or none>`
- Independence: `independent | self-review`
- Independence basis: `<freshness and non-implementer facts>`
- Independence required: `yes | no`
- Independence met: `yes | no | N/A`

## Authoritative sources

| Priority | Source | Authority for | Gaps or conflicts |
|---|---|---|---|
| 1 | `<accepted request, issue, or spec>` | `<intent>` | `<none or gap>` |
| 2 | `<plan/task/repository guidance>` | `<design/scope/standards>` | `<none or gap>` |

## Risk

- Reviewer-assessed risk: `low | medium | high`
- Risk rationale: `<affected behavior and reversibility, not diff size>`
- Required review depth/evidence: `<proportionate requirements>`

## Change contract and review focus

- What: `<contract value or unknown>`
- Authoritative why: `<source link/reference or unknown>`
- Contract scope: `<included and excluded surfaces or unknown>`
- Required evidence: `<expected checks/procedures or unknown>`
- Contract risk: `low | medium | high | unknown`
- Agent roles: `<implementer/validator/reviewer roles or unknown>`
- Review focus: `<named risks, acceptance behavior, and change surfaces>`
- Risk comparison/deviation: `<none or contract-versus-reviewer difference and impact>`
- Missing-contract impact: `<none, finding, or blocker with reason>`

## Selected quality signals

Keep exactly one row per signal. Use disposition `selected` with its trigger
and evidence, or `N/A` with a concise reason.

| Signal | Disposition | Trigger / N/A reason | Evidence |
|---|---|---|---|
| Correctness | `<selected or N/A>` | `<trigger or concise reason>` | |
| Security | `<selected or N/A>` | `<trigger or concise reason>` | |
| Compatibility | `<selected or N/A>` | `<trigger or concise reason>` | |
| Maintainability | `<selected or N/A>` | `<trigger or concise reason>` | |
| Performance | `<selected or N/A>` | `<trigger or concise reason>` | |
| Accessibility | `<selected or N/A>` | `<trigger or concise reason>` | |
| Observability | `<selected or N/A>` | `<trigger or concise reason>` | |
| Cost | `<selected or N/A>` | `<trigger or concise reason>` | |
| Understandability | `<selected or N/A>` | `<trigger or concise reason>` | |

## Checks and evidence

Evidence classes: ["observed evidence", "source-based inference", "unverified claim"]

| Check or procedure | Scope | Evidence class | Actual result | Requirement/risk covered |
|---|---|---|---|---|
| `<command or procedure>` | `<fixed scope>` | `observed evidence | source-based inference | unverified claim` | `<pass/fail/unrun plus output>` | `<source item or signal>` |

## Findings

Remove this example when there are no findings. Do not create placeholder
findings.

### `<critical|high|medium|low>`: <concise title>

- Evidence class: `observed evidence | source-based inference | unverified claim`
- Evidence: `<specific result>`
- Location: `<path:line, behavior, or artifact>`
- Impact: `<acceptance or engineering consequence>`
- Minimal action: `<smallest correction or evidence needed>`

## Acceptance coverage

| Source item / criterion | Implementation evidence | Check evidence | Result |
|---|---|---|---|
| `<requirement>` | `<path:line or behavior>` | `<observed/inferred/unverified evidence>` | `met | not-met | blocked | N/A` |

- Missing behavior: `<none or details>`
- Extra behavior: `<none or details>`
- Scope deviations: `<none or details>`

## Residual risk

- Residual risks: `<accepted or advisory risks>`
- Unverified areas: `<claims, unavailable checks, or none>`
- Required follow-up: `<owner/action or none>`

## Verdict

Verdict options: ["approved", "changes-required", "blocked"]

Selected verdict: `<one exact option>`

Rationale: `<tie the single verdict to findings, acceptance, required evidence,
and independence>`

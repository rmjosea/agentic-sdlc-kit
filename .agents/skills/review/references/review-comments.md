# Review comments

Load this reference only when converting findings into review comments or when
assessing an author's response to feedback.

## Comment record

Each comment is a finding record with this closed shape:

```text
impact: critical | high | medium | low
disposition: Required | Optional | Nit | Question | FYI
evidence: <observed evidence or source reference>
location: <file, line, symbol, or artifact location>
reason: <why the issue matters, when not obvious from evidence>
action: <smallest useful action or question>
```

Impact severity and disposition are independent axes. Never derive one from the
other. A comment addresses the code, not the person; it is respectful, specific,
actionable, and about one problem. Missing location, evidence, impact, or
disposition remains a report finding and is not authoritative feedback for
publication.

`Optional`, `Nit`, `Question`, and `FYI` cannot independently produce a
`changes-required` verdict. A `Required` comment blocks only when it has a
demonstrated material defect or missing required evidence, and the demonstrated
impact determines the blocking consequence. Courtesy, conceptual focus, and
one-problem clarity are scenario-evaluated judgments, not regex approval.

## Alternatives in comments

When an `action` offers more than one fix, apply the `AGENTS.md` Human decision
protocol: two to four distinct options with their trade-off, exactly one marked
**Recommended** with evidence, and room for the author's own alternative.

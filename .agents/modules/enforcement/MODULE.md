# Enforcement module

Run deterministic, read-only consistency checks over the kit configuration and
artifacts already present in a repository.

## Activation

Installation makes the checker available; it does not add a workflow gate.
Project-specific module checks apply only to modules installed, listed in the
installed canonical `.agents/kit-catalog.json`, and enabled in recognized
`.agents/project.json`. Any `.agents/project.md` is unsupported and blocks the
operation before writes. With no project config, conventional spec and work
roots may be inspected when present, but optional roots and modules add no burden.

## Run

From the repository root:

```text
python3 .agents/modules/enforcement/check.py --root . --format human
python3 .agents/modules/enforcement/check.py --root . --format json
```

The default format is `human`; both formats carry the same findings.

<!-- contract:enforcement-exit-codes:start -->
| Code | Meaning |
| --- | --- |
| `0` | valid |
| `1` | consistency failures |
| `2` | invalid invocation; malformed/unrecognized configuration; invalid/uninspectable/symlink root; safe-inspection failure |
<!-- contract:enforcement-exit-codes:end -->

## Boundaries

The checker uses only the Python standard library and remains self-contained
after installation. It reads files only: it never runs project commands,
executes recorded checks, accesses the network, imports repository scripts, or
writes artifacts. It reports fields and repository-relative paths without
repeating configuration or evidence values.

Evidence validation activates only when `evidence` is installed and enabled and
`roots.evidence` is configured. The built-in `multi-repo` integration likewise
activates only when that module is installed and enabled; it inspects configured
paths and `.git` markers and validates recorded repository/task/evidence
declarations without executing Git or inferring unrecorded state. Compliance
validation activates only when compliance, evidence, and enforcement are all
installed and enabled; it checks current `audit.jsonl` schema, ordering,
lifecycle/evidence links, repository revisions, and declared approval policy.
Missing approval is a failure only—the checker never performs an action.

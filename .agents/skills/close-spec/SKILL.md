---
name: close-spec
description: Use when implementation has merged in the target repo(s) and all tasks in tasks.md are checked off ([x]), to seal the specification as a notary: confirms every task is [x], cross-checks AC and plan §5 coverage, performs a diff sync check against plan §3 and companions, flips status approved -> implemented, and appends a handoff record. Do NOT use while any task is unchecked or to revalidate ACs (owned by implement).
---

# close-spec

Seal an implemented specification as a **notary** once all tasks in `tasks.md` are checked off and merged. `close-spec` verifies the paper trail and sync state; it does not re-run tests (validation is owned by `implement`).

## When to use

- Every task checkbox in `features/{NNN}-{slug}/tasks.md` is checked (`[x]`) across all `target_repos`.
- The implementation is merged (or ready for final closure) in the target repository(ies).
- The human gives an explicit go-ahead to seal the specification.

## When NOT to use

- Any task in `tasks.md` is still unchecked (`[ ]`) -> finish `implement` first.
- The specification needs scope clarification or AC edits -> use `judge-spec`.
- The specification is being cancelled without implementation -> set `status: archived` after human confirmation.

## Inputs

- Path to the source **specification** (`features/{NNN}-{slug}/spec.md`, `user-story`, or `user-journey` referenced by `plan.md` `spec:`).
- `features/{NNN}-{slug}/tasks.md` (to confirm all tasks are `[x]`).
- `features/{NNN}-{slug}/plan.md` (§5 coverage spine and §3 changes).
- Merge commit SHAs per target repository (from Git or the user).

## Outputs

- Source specification frontmatter updated: `status: approved -> implemented` and `updated: YYYY-MM-DD`.
- Source specification body gets a new section appended at the end:

```markdown
## Registro de implementación
- **Cerrado el:** YYYY-MM-DD
- **Cerrado por:** @handle
- **Commits por repo:** [SHA] en {repo}, ...
- **Cobertura AC -> verificación:** AC-1 -> tarea T01 [x] / test [name]; AC-2 -> ...
```

*(Note: `plan.md` and `tasks.md` are derived implementation artifacts and do not flip status).*

## Process — Gate -> Cross-check coverage -> Sync check -> Seal -> Report

### 1. Gate — confirm completion and human go-ahead

1. Verify that **every** task checkbox in `tasks.md` is `[x]`. Any open `[ ]` task blocks closure immediately.
2. Require explicit human confirmation before sealing the specification.

### 2. Cross-check AC coverage against the plan

3. Using `plan.md` §5 and `tasks.md` (`## Trazabilidad`), confirm that **every specification AC maps to at least one checked `[x]` task**.
4. If any AC has no checked task, stop and report the coverage gap (send back to `implement` or `judge-spec` if the AC was deferred).

### 3. Collect handoff facts and run the sync check

5. Collect the merge commit SHA(s) per target repo, closer handle, and date.
6. **Sync check:** compare the merged changes (`git diff --stat <base>...<merge SHA>`) in each target repo against `plan.md` §3 and its companions (`data-model.md`, `api.md`, `event.md`). If an endpoint, field, event, or file was built differently from the plan/companions, stop and update the plan/companion (or the spec via `judge-spec` if behaviour changed) before sealing.

### 4. Seal surgically and report

7. Update the source specification's frontmatter (`status: implemented`, `updated: YYYY-MM-DD`) and append `## Registro de implementación` without altering existing specification sections.
8. Report the sealed path and the complete `AC -> task -> verification` map, followed by the context-cleanup reminder (`.agents/conventions/context-cleanup.md`).

## Anti-patterns

- Sealing while any task in `tasks.md` is still `[ ]`.
- Sealing a specification whose `plan.md` or companions drifted from what was actually built.
- Rewriting existing sections of the specification body instead of appending the closure record.
- Flipping `status` without explicit human confirmation.

## References

- `.agents/conventions/frontmatter-schema.md` (§ Status vocabulary)
- `.agents/conventions/composition.md`
- `.agents/conventions/context-cleanup.md`

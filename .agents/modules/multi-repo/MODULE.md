# Multi-repository module

Coordinate one accepted change across existing local Git checkouts without taking
ownership of repository lifecycle operations.

## Activation

Apply this module only when this `MODULE.md` is installed, `multi-repo` is
listed in `enabled_modules` in recognized `.agents/project.json`, and
`repositories` contains the confirmed repository map. Legacy
`.agents/project.md` is unsupported and blocks the operation before writes. Otherwise add no field,
artifact, checkout, or process burden to the core workflow. This module has no
hard module dependency; if `evidence` or `enforcement` is also active, use the
integrations below.

`repositories[].id` is the stable logical Repository ID. A path is either
`.` or a safe path within the current root, or exactly
`${ENV_VAR}/relative/path` where the uppercase environment variable resolves to
an absolute workspace directory. Inspect every existing path component with
`lstat`, from the filesystem anchor through the environment base and relative
suffix; reject any symlink without resolving or following it. Never record an
environment value or a credential. Stop when an environment variable is
missing, a path is missing, not a directory, not a Git checkout, or contains a
symlink, or when IDs are duplicated. Inspect only configured paths; never scan
for sibling repositories.

## Lifecycle boundary

Coordinate existing checkouts only. Never clone, checkout, reset, clean, create
or delete a worktree, obtain credentials, push, fetch, pull, or access the
network. The read-only enforcement checker may inspect a `.git` file or
directory marker but must never execute Git. Agents may use Git tooling already
available to inspect status and revisions while performing workflow work, but
that tooling is outside the checker.

Before planning mutations or implementation, inspect staged, unstaged, and
untracked status in every affected repository without recording raw sensitive
output. Classify task `Dirty status` exactly as `clean`,
`dirty-nonconflicting`, `blocked-conflict`, or `unknown`, and classify
`Ownership/isolation` exactly as `exclusive-owner`, `isolated`,
`blocked-conflict`, or `unknown`. Block conflicting or unknown ownership. Work
in one assigned Repository ID at a time unless the approved plan records
explicit isolation and ownership for concurrent repositories.

## Plan

Load [the plan snippet](assets/plan-snippet.md) while planning. Map each changed
component, integration point, and planned check to configured Repository IDs.
Keep cross-repository contracts and integration order explicit. Do not turn the
map into repository lifecycle instructions.

## Tasks and implementation

Load [the task snippet](assets/tasks-snippet.md) while decomposing or executing
a graph. Every task has exactly one primary `Repository` ID and both exact
control enums above. `Depends on` remains the complete dependency source;
`Cross-repo depends on` preserves a unique list that repeats exactly the subset
whose primary Repository differs. Reject duplicate cross-repository references
before comparing that subset. Cross-repository work records planned or observed
`Integration evidence`.

A `ready`, `in-progress`, or `done` task cannot use `blocked-conflict` or
`unknown` for either control. A `blocked` task using either value records every
matching exact `Blocker` token: `dirty-status:<value>` or
`ownership-isolation:<value>`. Do not infer control state from free text or
substring matches. Block unknown IDs, contradictory dependency references,
missing integration evidence, or conflicting dirty ownership.

## Review

Load [the review snippet](assets/review-snippet.md) for a multi-repository
review. Fix base, head, committed range, and uncommitted snapshot separately for
each affected Repository ID. If fixes are authorized, assign each fix to its
repository and re-fix that repository's base/head and uncommitted scope before
concluding. Never present one repository's revision as a shared global range.

## Evidence integration

When `evidence` is active, use its one v1 `repository_scope` array; do not add a
competing repository field. Load [the evidence snippet](assets/evidence-snippet.json).
Use one unique entry per affected Repository ID. Every requirement-coverage and
check record has a non-empty `repository_ids` subset of that scope. Under this
module, scope IDs must also be configured IDs and the scope must exactly equal
the repositories affected by coverage and checks. A single-repository record
uses one entry such as `current`.

When `enforcement` is active, its built-in `multi-repo` integration validates
configured checkout markers and recorded artifact declarations only. It never
runs Git, project commands, recorded checks, repository code, or network calls,
and never mutates a checkout.

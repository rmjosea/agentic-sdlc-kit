---
name: contribute
description: Inspect repository contribution policy and prepare or validate an author-side branch name, commit message, pull-request draft, or author response without changing Git state. Use when the user asks about contribution policy, a branch name, staged commit readiness, a commit message, a provider-neutral pull request draft, or a response to review feedback. Do not use for implementation or review gates, pull-request publication, pushes, merges, releases, provider APIs, or publishing responses.
---

# Prepare a Local Contribution

Use observed repository policy to inspect or prepare one branch or commit proposal.
This utility is not an implementation or review gate.

## Boundaries

- Follow every applicable `AGENTS*.md`. Machine-readable `.agents/project.json`
  contribution settings may decide policy directly. Treat applicable
  `AGENTS*.md`/`CONTRIBUTING*` prose as human-readable policy that the agent must
  read and, when material, confirm; unsupported `.agents/project.md` blocks the
  operation.
- Remain provider-neutral and offline. Do not discover credentials or identities,
  call provider APIs, push, publish, open or edit a pull request, respond to
  review feedback, merge, release, force-push, or delete a branch.
- Inspection and checker commands are read-only. Never run a hook, linter, CI
  command, stage path, create or switch a branch, or create a commit while using
  this slice. Static executable configuration is evidence, not a passing check.
- Never bypass a hook or weaken an executable check. A later explicitly requested
  real commit must use normal Git hook behavior; that action is outside this
  read-only checker.
- Do not infer conceptual atomicity from file counts. The agent and reviewer must
  judge whether staged work is one coherent logical change, excludes unrelated
  work, and includes closely related tests. No task-to-commit ratio applies.

## Discover policy

Stop at the first authoritative level that settles each field:

1. machine-readable project contribution settings and applicable
   `AGENTS*.md`/`CONTRIBUTING*` human instructions;
2. executable hook, lint, CI, and commit-message configuration, inspected only;
3. templates and confirmed merge evidence, reported by `inspect` only;
4. consistent relevant history as non-mandatory style evidence only;
5. classic kit fallback.

The checker does not infer a mandatory mode or branch prefix from free-form
prose. It finds applicable instruction files and reports bounded line numbers
containing commit, conventional, classic, or branch terms with state
`confirmation-required`; it never echoes those lines or claims to understand
their direction. `inspect` may return exit `0` with that warning. Before an
affected branch or commit action, read the cited prose, ask the user when its
meaning or applicability is material, and pass the confirmed value and source.
Never say that the checker interpreted the prose.

Recognized `project.json` contribution fields and clearly structured executable
commitlint content decide directly. Conventional executable evidence includes a
conventional `extends`, `parserPreset`, or config reference. Strip quote-aware
bounded JavaScript comments and parse JSON when possible before inspection. A
filename, comment, isolated severity-2 rule, empty config, or ambiguous
invocation is unknown evidence with a warning, not mandatory mode. History
alone never requires Conventional Commits.

A confirmed prose decision that contradicts `project.json` or a clear executable
check blocks the affected action and identifies the conflict. A contradiction
between structured `project.json` policy and a clear executable check also blocks
the affected action and names both sources; the skill must never weaken an
executable check. Lower evidence never overrides higher policy. With no relevant
prose or structured policy, use classic commit mode and no branch prefix.

Run policy and local-scope inspection when needed:

```bash
python3 .agents/skills/contribute/scripts/check_contribution.py inspect \
  --root . --expected-path path/to/file --format human
```

Repeated `--expected-path` values declare intended scope. Inspect staged,
unstaged, and untracked porcelain state, staged whitespace errors, conflict
markers, and staged paths outside that scope. Report semantic atomicity as agent
judgment, not a mechanical result.

## Prepare or validate a branch

Follow a confirmed branch policy when relevant prose is observed. The agent—not
the checker—reads the instruction and confirms the exact prefix. Pass both flags
together; the source must be an applicable safe repository-relative regular
non-symlink `AGENTS*.md` or `CONTRIBUTING*` file with a relevant branch line:

```bash
python3 .agents/skills/contribute/scripts/check_contribution.py branch \
  --root . --name work/describe-parser-safety \
  --confirmed-branch-prefix work/ --policy-source CONTRIBUTING.md \
  --format human
```

Without relevant prose or another structured branch rule, propose a short
descriptive name that is a valid Git branch ref without inventing a type prefix
or issue identifier. Branch validation contains no natural-language policy
heuristic.

The checker uses allowlisted `git check-ref-format --branch`; it never creates
or switches a branch. Report the exact candidate and validation result.

## Prepare or validate a commit

Only when preparing or checking a commit message, load
[the commit reference](references/commits.md). Do not load it for policy-only or
branch-only work.

Preview one complete message and the observed staged/unstaged/untracked scope.
Prefer stdin so validation creates no repository file:

```bash
printf '%s\n' 'Add bounded contribution checks' | \
  python3 .agents/skills/contribute/scripts/check_contribution.py commit \
    --root . --message-file - --expected-path path/to/file \
    --confirmed-commit-mode classic --policy-source CONTRIBUTING.md \
    --format human
```

Omit both confirmation flags only when inspection found no relevant commit prose
or when structured policy already settles the field without prose requiring a
human decision. A file input must be explicitly supplied, repository-relative,
regular, and non-symlink. The checker validates only; it does not stage, commit,
or execute hooks or other checks.

## Prepare a pull-request draft

For pull-request work only, load [the pull-request reference](references/pull-requests.md);
it defines the title, required sections, template, persistence, and action boundary.
Unresolved `<UPPER-TOKEN>` placeholders block presentation; observations are report-only,
and squash titles follow resolved commit-message rules.

## Respond to review feedback

For author-response work only, load [the response reference](references/review-responses.md).
Choose changed-with-evidence, clarification-request, or reasoned-technical-disagreement;
publication and thread resolution remain separately approved actions.

## Action authorization

| Action | Required authority |
|---|---|
| inspect, validate, or propose branch/message/PR/response | none beyond the user request |
| create or switch branch | exact action requested after preview |
| stage paths | exact paths requested after preview |
| create commit | exact commit requested; preview message and staged scope first |
| push | fresh explicit approval of ref and remote |
| open or edit PR | fresh explicit approval of exact title, body, base, and head |
| publish review response or resolve thread | fresh explicit approval of the exact comment or thread plus local-policy compliance |
| merge/release/force-push/delete branch | outside this skill; never implied |

An exact request authorizes that action only after its preview is verified; a
broad request does not, and any preview change invalidates prior approval.

## Checker contract

`scripts/check_contribution.py` is owner-contained and uses only Python's
standard library plus Git. It may be copied with this skill without source
checkout modules. Public commands are:

```text
check_contribution.py inspect --root PATH [--base-ref REF] [--expected-path PATH ...] [--format human|json]
check_contribution.py branch --root PATH --name NAME [--confirmed-branch-prefix PREFIX --policy-source PATH] [--format human|json]
check_contribution.py commit --root PATH --message-file FILE|- [--confirmed-commit-mode classic|conventional --policy-source PATH] [--base-ref REF] [--expected-path PATH ...] [--format human|json]
check_contribution.py pull-request --root PATH --draft-file FILE|- [--confirmed-commit-mode classic|conventional --policy-source PATH] [--base-ref REF] [--expected-path PATH ...] [--observations FILE|-] [--format human|json]
```

Input is bounded strict UTF-8. `-` consumes one message, draft, or observations
document from stdin, and the two pull-request inputs cannot both consume it.
Repository files and existing ancestors must be safe, repository-contained,
regular, and non-symlink; no repository temporary file is made.

Human output and the JSON schema in
`assets/contribution-report.schema.json` carry equivalent ordered findings,
policy sources with bounded relevant line numbers, `confirmation-required`
state, confirmed source/value, local scope, pull-request draft and check
results, advisories, and the action boundary. Human output includes the
canonical JSON report as a readable parity section so every field is
represented. Errors redact rejected values. Exit `0` means valid, `1` means
policy or validation failure, and `2` means unsafe/uninspectable input or
invalid invocation. Confirmation flags must be supplied as a pair.

Git invocations are fixed read-only argument arrays with no shell, network,
evaluation, hooks, or writes. Prompts, optional locks, lazy fetch, external
diffs, text conversion, configured filesystem monitors, and interactive
credentials are disabled. Stdout/stderr are incrementally bounded and every
process has a timeout.

## Quality gate

Before reporting readiness:

1. name every policy source with bounded lines/state/conflicts, and state classic or
   policy-required Conventional mode, authority, and that prose was not interpreted;
2. show staged/unstaged/untracked and expected/unexpected scope; report whitespace,
   conflicts, and trailers without inventing identities or values;
3. state that 50/72 widths and semantic atomicity are advisory unless policy says otherwise;
4. confirm no branch, index, commit, hook, file, reflog, or remote state changed.

Stop on conflicting policy, unsafe configuration or input, an invalid branch,
invalid message, required trailer omission, unresolved index/conflict marker,
staged whitespace failure, or inability to inspect the repository safely.

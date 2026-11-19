# Pull-request drafts

Load this reference only for pull-request draft work. A draft is provider-neutral
and remains local until a separate explicitly approved action is taken.

## Required content

A draft begins with one ATX H1 title and uses these exact required `##` section
headings: `Purpose and why`, `Change`, `Scope`, `Authoritative context`, `Risk
and operational impact`, `Checks`, and `Requested feedback`. `Review order` is
optional and belongs in a draft whenever reading order helps the reviewer.

Respect the repository's local pull-request template when one is configured or
present. The template's own placeholders are advisory context; the draft must
resolve every one of them before it is presented.

Keep the proposal conceptually focused on one self-contained purpose and include
closely related tests. Conceptual focus is an agent and reviewer judgment. Never
approve or reject a draft from a universal line, file, or commit-count threshold.

Observations are normalized input, not executed evidence. Report passed and failed
checks as observed inputs and report not-run or absent checks as omitted. Do not
invent evidence, identities, commands, or results.

## Persistence

A draft is chat output by default and the checker never writes it. When the user
asks for a saved draft, persistence is a caller-selected action at
`<roots.work>/<feature>/pull-request.md`, falling back to
`.work/<feature>/pull-request.md`. Reject a path outside that root, and return
chat output only when no root can be recognized.

## Action boundary

Draft preparation and local validation need only the user's request. Creating or
switching a branch, staging paths, and creating a commit require the exact action
request after preview. Pushing requires fresh explicit approval of the exact ref
and remote. Opening or editing a pull request requires fresh explicit approval of
the exact title, body, base, and head. Merge, release, force-push, and branch
deletion are outside this utility and are never implied.

An exact request authorizes that exact action only after the preview is verified.
A broad request does not authorize a narrower or broader external action, and any
change to the preview invalidates prior approval.

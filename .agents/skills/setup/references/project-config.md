# Project configuration v2

Read this reference only while creating, editing, or recognizing
`.agents/project.json`. The machine authority is
`../assets/project.schema.json`; this reference defines semantic and operational
checks that JSON Schema does not safely express.

## Authority, ownership, and fallback

`.agents/project.json` is optional and project-owned. The installer does not
manage or record it. Only its explicit `--init-config` flag may create the file
when absent, from template defaults plus observed facts (the `origin/HEAD`
branch, an existing local pull-request template, and selected modules with
selected dependencies except `multi-repo`); it never overwrites. When absent, core skills use the `specs/` and
`.work/` fallbacks, optional modules remain disabled, and no tracker, extra
repository, contribution override, approval policy, or optional root is assumed.

`.agents/project.md` is unsupported legacy input. Any operation that discovers
it must stop before parsing either config or writing any file. It is never
converted, overwritten, or treated as fallback.

A recognized config is one regular, non-symlink, strict UTF-8 JSON object with
no duplicate key at any depth. It has schema version 2, matches the closed
schema, passes the semantics below, and uses enabled module names and dependency
relationships from the recognized kit catalog. Invalid config blocks the
operation; a consumer never guesses around it.

## Exact object

```json
{
  "schema_version": 2,
  "roots": {"specs":"specs","work":".work","adrs":null,"evidence":null,"domain_context":null},
  "repositories": [],
  "enabled_modules": [],
  "tracker": {"kind":"none","location":null,"labels":{}},
  "agent": {"mode":"guided"},
  "review": {"mode":"risk-based"},
  "approval_policy": {"rules":[]},
  "contribution": {"commit_mode":"discover","base_branch":null,"required_trailers":[],"pull_request_template":null,"merge_strategy":"unknown"}
}
```

Every object is closed. Every key and string is 1 through 500 characters, uses
Unicode scalar values only, has no control character, and is non-sensitive
unless the schema requires a narrower
enum or pattern. Reject credential-shaped values, HTTP(S) userinfo, malformed HTTP(S)
URLs, and sensitive query names such as token, access token, API key, secret,
password, or credential, including case/separator variants. Diagnostics contain
only stable code, field, and redacted reason.

Unknown fields are rejected. No command, executable, hook, plugin, script, or
arbitrary regex field exists or may be encoded in label keys or other maps.
Configuration is data and is never executed.

## Fields and semantics

### Roots

`roots` contains exactly `specs`, `work`, `adrs`, `evidence`, and
`domain_context`. `specs` and `work` are required safe repository-relative
paths. The others use the same syntax or `null`. Reject empty, `.`, absolute,
drive-qualified, backslash, empty-component, `.`/`..` component, and environment
placeholder forms.

When resolving a configured root, inspect from the repository root through each
existing ancestor and target with `lstat`. Reject a symlink, unsafe type, or
uninspectable component without resolving it. Existing `specs`, `work`, and
`evidence` roots must be regular directories. Existing `adrs` and
`domain_context` may be a regular file or directory according to the domain-model
owner contract. An
absent final path is a permitted future destination. Setup records roots but
does not create them. A module-required root must be configured before activation.

### Repositories

Each unique closed entry is `{"id","path","remote"}`. `id` is unique
kebab-case. `path` is `.`, a safe repository-relative path, or exactly one
leading `${UPPER_ENV}/safe/relative` form. `remote` is `null`, a parseable URI
with scheme and authority, or an scp-like `[user@]host:path` using a safe simple
hostname, FQDN, or `localhost`; empty hosts/paths, drive-like forms,
leading/trailing whitespace, backslashes, controls, isolated Unicode surrogates,
malformed URIs, passwords, and sensitive query keys are rejected. URI userinfo is rejected
except a non-sensitive username-only `ssh` URI. Scp-like forms never carry a
password. Diagnostics never echo the remote.

When multi-repo behavior activates, an environment variable must exist and
resolve to an absolute workspace directory. Inspect every existing component
from that base through the target without following symlinks. The destination
must be an existing directory with a regular non-symlink `.git` file or
directory. Never scan sibling repositories, expand any other placeholder, or
include expanded paths in diagnostics.

### Enabled modules

`enabled_modules` is a unique array of names present in the recognized kit
catalog. A module activates only when its safe `MODULE.md` is installed, it is
enabled, all catalog dependencies are installed and enabled, and required roots
or settings are valid. Otherwise core behavior is unchanged and the attempted
module operation stops.

### Tracker

`tracker` contains exactly `kind`, `location`, and `labels`. Kind is kebab-case.
Kind `none` requires a null location; every other kind requires a sanitized
location. Labels is a duplicate-free string-to-string map; empty is valid.
Remote signals do not authorize an invented tracker or label.

### Agent and review

`agent.mode` is `guided` or `autonomous-within-rules`. `review.mode` is
`risk-based` or `always-independent`. These are preferences only. They do not
bypass approval, risk, repository, or independent-review rules.

### Approval policy

`approval_policy` contains only `rules`. Each rule contains exactly `risk`,
`action`, `required_roles`, and rule-level `independent`. Risk is low, medium,
or high; action and role are kebab-case. Required roles is non-empty for every
rule and contains unique `{"role","minimum"}` records with minimum 1 through
100. `(risk, action)` pairs are unique. High-risk rules require
`independent:true`; no policy can weaken the high-risk independent-review floor.

Compliance owns evaluation when active. Role and actor strings are declarations,
not authenticated identities. When independence applies, an implementer's own
approval never satisfies it.

### Contribution

`contribution` contains exactly:

- `commit_mode`: `discover`, `classic`, or `conventional`;
- `base_branch`: `null` or safe Git ref syntax (no control/space, `..`, `@{`,
  forbidden ref punctuation, empty/dot components, leading hyphen, or `.lock`);
- `required_trailers`: unique `[A-Za-z0-9-]+` tokens;
- `pull_request_template`: safe repository-relative path or `null`; and
- `merge_strategy`: `unknown`, `merge`, `squash`, or `rebase`.

These explicit values precede history-based fallback. A conflict with an
executable hook or linter stops contribution; configuration never executes it.

## Setup authorization

For creation or update, inspect and validate the preimage, construct the entire
deterministic JSON candidate, show its exact bytes, and ask exactly:
**Approve writing this exact `.agents/project.json` preview?** Recheck the
legacy path, destination preimage, catalog/module state, schema, semantics,
paths, and exact approved bytes immediately before writing. Any change
invalidates approval. Write only `project.json`, then re-read and prove exact
byte equality. A failed check permits no repair write without a new preview and
approval.

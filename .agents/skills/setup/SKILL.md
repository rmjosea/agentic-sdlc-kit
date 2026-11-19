---
name: setup
description: Set up or update the project-owned .agents/project.json. Use when a user asks for project setup, issue tracker or triage label configuration, kit artifact paths, enabled installed modules, repository layout, contribution policy, approval policy, or agent and review modes. Do not use to install or copy the kit, configure app runtime or environment, write specs or plans, or change repository rules.
---

# Configure the Project

Guide one safe project-configuration change. The core remains usable when the
optional configuration is absent.

## Preconditions and boundaries

- Work from the Git repository root and follow applicable `AGENTS.md` files.
- Treat `.agents/project.json` as project-owned. The installer and ownership
  manifest never own, replace, or remove it; only the explicit installer flag
  `--init-config` may create a conservative file when it is absent. Review such
  a file like any existing config.
- Limit approved writes to `.agents/project.json`. Do not modify `AGENTS.md`,
  skills, modules, artifacts, application configuration, runtime environment, or
  secrets.
- Before any other setup action, inspect `.agents/project.md`. If it exists in
  any form, report the unsupported legacy configuration and stop without
  parsing, converting, overwriting, or writing either project file.
- Do not install modules or run the installer. An unavailable requested module
  requires a separate installer action and a later setup request.

## Inspect before asking

Inspect only focused, read-only evidence:

1. Read applicable `AGENTS.md` files.
2. Check `.agents/project.md` first, then inspect `.agents/project.json` without
   following a symlink or unsafe ancestor.
3. Inspect `.agents/agentic-sdlc-kit.json` and `.agents/kit-catalog.json` when
   present. Use only a recognized catalog for module names and dependencies;
   use safe `MODULE.md` presence for installed availability and report mismatch.
4. Inspect focused existing layout, remotes, issue templates, contribution
   instructions, templates, and merge settings only when relevant to requested
   fields. Evidence is not permission to invent policy.
5. Load the [project JSON contract](references/project-config.md), the
   [project schema](assets/project.schema.json), and, only when constructing a
   new complete candidate, [the conservative template](assets/project.template.json).
6. Decode strict UTF-8 JSON with duplicate-key rejection at every object depth.
   Require the exact closed schema and semantic constraints before recognizing
   an existing configuration.

Never place credentials, tokens, secret-bearing URLs, personal data, or raw
command output in notes, questions, diagnostics, previews, or configuration.
Diagnostics name only a stable code and field; they never echo a rejected value.

## Classify the existing config

- If `.agents/project.md` exists, stop with the unsupported diagnostic before
  parsing or writing anything.
- If `project.json` is absent, propose the conservative template plus only
  confirmed changes.
- If it is a regular non-symlink schema-valid v2 file, preserve unchanged values
  and propose the smallest closed-object merge.
- If it is malformed, duplicated, unsafe, not schema version 2, has unknown
  fields or modules, misses module dependencies, or cannot be inspected safely,
  stop without writing. Do not fall back or silently repair it.

## Resolve values one decision at a time

Summarize confirmed inspection facts, then ask exactly one material question at
a time. Recommend only an evidence-supported answer and explain its consequence.
Resolve only requested or required nested fields:

- `tracker.kind`, sanitized `tracker.location`, and confirmed label mappings;
- roots for specs, work, ADRs, evidence, and domain context;
- unique installed catalog modules and all enabled dependencies;
- stable repository IDs, safe relative or exact `${UPPER_ENV}/relative` paths,
  and sanitized remotes;
- `agent.mode` and `review.mode` preferences, which never grant permission or
  weaken risk rules;
- approval rules, declared roles, minimums, and independence; and
- contribution commit mode, base branch, trailer tokens, safe local PR template,
  and merge strategy.

Read a requested module's `MODULE.md` before proposing activation and configure
its required roots in the same candidate. Inspect compliance policy assets
before proposing non-empty approval rules. Configuration is declarative: never
execute a command, hook, plugin, script, or configured path.

## Preview and approve

Serialize the complete candidate as deterministic indented JSON with a trailing
newline. Before any write, show:

1. the exact complete proposed `.agents/project.json` bytes;
2. each new, changed, and preserved field and the evidence category supporting
   an observed value; and
3. confirmation that modules are installed and cataloged with dependencies,
   no secret is present, and no other path will change.

Ask exactly: **Approve writing this exact `.agents/project.json` preview?**
Earlier requests, field answers, or approval of a different preview do not
authorize the write. Any byte change requires a new complete preview and fresh
exact approval.

## Write after approval

Immediately before writing:

1. Re-inspect `.agents/project.md`; if it now exists, stop unsupported.
2. Re-read or re-confirm absence of `.agents/project.json` and compare its type,
   bytes, and inspected state with the approved preimage. Stop on any change.
3. Revalidate the exact approved bytes against the schema and semantic contract,
   current catalog/module availability, dependencies, and safe path rules.
4. Write only the approved `.agents/project.json` bytes. Never write the legacy
   file or ownership manifest.

## Quality gate

1. Re-read with duplicate-key rejection and revalidate schema plus semantics.
2. Confirm byte-for-byte equality with the approved preview.
3. Inspect the diff and confirm `.agents/project.json` is the only setup change.

Report changed and preserved fields, evidence used, approval, recheck, and gate
results. Never repair a failed gate with an unapproved second write.

## Stop conditions

Stop without writing when the legacy file exists; exact approval is withheld;
repository ownership is unclear; config/catalog/manifest is unrecognized;
destination or inputs changed; a module is unavailable or misses a dependency;
a value is unconfirmed, unsafe, executable, or sensitive; a configured path has
a symlink; or any quality gate cannot pass.

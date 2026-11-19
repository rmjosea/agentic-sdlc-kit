---
name: agents-creator
description: Use when the user asks to create, audit, shorten, or improve the AGENTS.md file of a target repository ("genera el AGENTS.md de este repo", "audita este AGENTS.md"). Inspects repository manifests and structure first, confirms inferences one question at a time, drafts a concise English AGENTS.md, and writes only after explicit approval. Do NOT use for product code implementation or general README files.
---

# agents-creator

Create or surgically improve a repository's `AGENTS.md` from observed repository evidence and confirmed team rules.

## When to use

- User asks to create, generate, or author an `AGENTS.md` for a target repository.
- User asks to audit, shorten, or improve an existing `AGENTS.md` so coding agents follow real build/test commands and architectural boundaries.

## When NOT to use

- User wants product code, bug fixes, or feature implementation -> use `implement`.
- User wants a general marketing `README.md` without mentioning `AGENTS.md`.
- User wants to configure `.agents/project.json` -> use `setup`.

## Inputs

- Target repository path (confirm with the user if ambiguous).
- Optional existing `AGENTS.md`, known build/test commands, or recurring agent pain points.

## Outputs

- Concise evidence summary (stack, exact commands, non-obvious structure, conventions, testing, boundaries, security pitfalls).
- Proposed English `AGENTS.md` draft (or surgical patch plan for an existing file), kept under ~250 lines.
- File written only after explicit human approval.

## Process — Confirm target -> Inspect -> Confirm gaps -> Draft -> Approve -> Write

### 1. Confirm target and inspect repository evidence

1. Verify the target repository path before reading. Inspect only that repository unless the user explicitly names a reference repo.
2. Read high-signal files: existing `AGENTS.md`, `README.md`, package/build manifests (`package.json`, `pyproject.toml`, `pom.xml`, `Makefile`, `Dockerfile`), CI configs, linter/test configs, and top-level directory structure.

### 2. Separate facts from inferences and ask one question at a time

3. Distinguish **observed facts** (exact scripts in `package.json` / `Makefile`) from **inferences** (which command or pattern is currently recommended vs legacy).
4. Ask **one question at a time** under the `AGENTS.md` human decision protocol when commands, conventions, or hard boundaries need confirmation. Never guess build, test, or lint commands.

### 3. Draft the `AGENTS.md` in English

5. Include Shape C frontmatter (`title`, `updated: YYYY-MM-DD`) when the repo uses frontmatter, and cover only applicable high-signal sections:
   - **Project overview** (concise decision-orienting context)
   - **Setup, build, lint, and test commands** (exact copy-pasteable commands)
   - **Project structure & architecture** (only non-obvious boundaries and golden examples)
   - **Code style & conventions** (link to config files instead of copying rules)
   - **Testing** (framework, locations, focused test command)
   - **Boundaries / do not touch** (generated files, lockfiles, restricted modules, shared libraries)
   - **Security & pitfalls** (secrets, PII, auth, known traps)
6. Keep all paths relative to the repository root (never `/Users/...` absolute paths) and omit ceremonial filler.

### 4. Preview, approve, and validate

7. Present the evidence summary and full draft (or surgical diff) and ask for explicit approval before writing.
8. After writing, verify that every command and path is grounded in repository evidence, no product code was touched, and the file stays concise.

## Anti-patterns

- Guessing unverified build, test, or lint commands.
- Copying full ESLint/TypeScript/CI config files into `AGENTS.md` instead of linking to them.
- Rewriting an existing valid `AGENTS.md` wholesale when a surgical update suffices.

## References

- `.agents/conventions/progressive-disclosure.md` (L0 token budget)
- `.agents/conventions/naming-and-language.md`

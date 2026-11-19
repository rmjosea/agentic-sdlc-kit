---
name: git-conventions
description: Use when naming a branch or writing commit messages for a code or artifact change, ensuring Conventional Commits format (or repository commit policy), one logical change per commit, pre-commit hook compliance (commitlint/husky), and traceability from commit -> task ID (T0x) -> plan §3 change. Do NOT use for sealing a completed specification (use close-spec).
---

# git-conventions

Prepare branch names and traceable, hook-compliant commit messages that link every code change back to its task and plan.

## When to use

- Creating a branch or writing a commit message during `implement` or in the Lightweight lane (XS/S).
- Checking whether a task commit satisfies traceability (Dim 10/11 of the stack juez rubrics in `.agents/skills/implement/rubrics/`).

## When NOT to use

- Sealing an implemented specification after merge -> use `close-spec`.
- Full offline policy discovery or pull-request draft validation -> use `contribute` when needed.

## Core rules

1. **Follow repository commit policy and Conventional Commits (`feat:`, `fix:`, `chore:`, `refactor:`, `test:`, `docs:`):**
   - When the repository uses `commitlint` / `husky` (or `.agents/project.json` sets `commit_mode: "conventional"`), every commit message must be a valid Conventional Commit (`<type>(<optional-scope>): <imperative-summary>`).
   - Never bypass pre-commit hooks (`--no-verify` is forbidden). If a hook rejects a message or lint check, fix the cause and re-run.
2. **Reference the task ID (`T0x`) or issue key for end-to-end traceability:**
   - Include the task ID from `tasks.md` (e.g., `feat(applies): add PATCH /applies/:applyId/iban endpoint (T03)`) so the chain `commit -> task T0x -> plan §3 -> spec AC` is auditable by `implement` and `close-spec`.
3. **One logical change per commit (Karpathy #3 — Surgical changes):**
   - Stage only the files belonging to the current task (`git diff --staged`). Never bundle unrelated formatting, dead-code deletion, or changes from another task.
4. **Branch naming:**
   - Follow the target repository's branch prefix (`feat/`, `fix/`, `chore/`, `docs/`) and kebab-case slug (e.g., `feat/005-cambio-iban`).

## Anti-patterns

- Bypassing `husky`, `lint-staged`, or `commitlint` hooks.
- Committing without referencing the task ID (`T0x`) when implementing from `tasks.md`.
- Bundling drive-by refactors or untracked files from outside the task scope into a commit.

## References

- `.agents/skills/implement/SKILL.md` (per-task commit step on juez `APROBADO`)
- `.agents/skills/contribute/SKILL.md` (read-only policy and PR draft checker)

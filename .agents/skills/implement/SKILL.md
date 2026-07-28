---
name: implement
description: Implement one ready task from an approved plan using small feedback loops, minimal changes, appropriate tests, and durable handoff state. Use when the user asks to execute, build, code, fix, or continue a planned task. Do not silently expand scope or implement unresolved blocked tasks.
---

# Implement a Planned Task

Complete one ready task at a time and leave the repository in a verifiable state.

## Select and bound

1. Read `AGENTS.md`, the selected task, its spec, and only required contracts.
2. Confirm dependencies are done and the task is not blocked.
3. Inspect the affected code and tests before editing.
4. State the task outcome, intended change surface, and validation.
5. Stop for a material ambiguity; do not invent product or architecture choices.

## Execute

- Make the smallest coherent change that satisfies the task.
- Follow existing repository conventions before introducing new patterns.
- Avoid unrelated cleanup and speculative abstraction.
- Work in short edit-run-observe loops.
- Preserve compatibility unless the approved plan says otherwise.
- Treat external input, secrets, permissions, and destructive effects as trust
  boundaries.

Read [references/testing.md](references/testing.md) when selecting or writing
tests. Read [references/debugging.md](references/debugging.md) only when a
failure is not explained by the current change.

## Verify

Run the narrowest useful checks during iteration, then all task-relevant checks
before completion. Compare observed behavior with the spec and task evidence.

Do not weaken, skip, or delete a failing check merely to obtain a green result.
Report checks that cannot run and why.

## Close

- Update task state only when completion evidence exists.
- Record deviations from the plan and their rationale.
- Write or update `.work/<feature>/handoff.md` when another session or agent may
  continue the work.
- Summarize files changed, behavior delivered, checks run, results, risks, and
  the next ready task.

Use [assets/handoff.template.md](assets/handoff.template.md) for durable handoff.


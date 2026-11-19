---
schema_version: 2
id: "HANDOFF-<NNN>"
type: "handoff"
sources: ["PLAN-<PLAN>#TASK-<TASK>"]
snapshot_at: "<SNAPSHOT-AT>"
---

# <Feature> handoff

> Recovery snapshot only. The referenced task graph, never this handoff, remains
> authoritative for task state.

## Baseline and working-tree state

- Baseline commit/ref: <BASELINE>
- Branch/worktree: <WORKTREE>
- Relevant staged, unstaged, and untracked paths: <PATHS>

## Current task

- Tasks file: <TASKS-PATH>
- Current task reference: <CURRENT-TASK>

## Objective last progress

- Last completed action: <PROGRESS>
- Files/behavior changed: <CHANGES>

## Exact checks and results

- <CHECK>

## Agent topology and roles

- Topology: <TOPOLOGY>
- Exploration: <EXPLORATION>
- Implementation: <IMPLEMENTATION>
- Validation: <VALIDATION>

## Consumed limits

- <LIMITS>

## Stop reason

- <STOP-REASON>

## Risks and blockers

- <RISKS>

## Next safe action

- <NEXT-ACTION>

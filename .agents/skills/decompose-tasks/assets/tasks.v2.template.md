---
schema_version: 2
id: "TASKS-<NNN>"
type: "task-graph"
sources: ["PLAN-<NNN>"]
namespace: "PLAN-<NNN>"
---

# <Feature> task graph

> Generated from the source plan. This graph is authoritative for task state;
> external task references use the plan namespace.

## Execution controls

- Topology: <TOPOLOGY>
- Topology decision: <TOPOLOGY-DECISION>
- Review/integration capacity: 1
- Maximum in-progress: 1
- Review queue: none

## Tasks

### TASK-001: <TASK-TITLE>

- Plan: PLAN-<NNN>
- Source items: <SOURCE-ITEMS>
- Type: <TASK-TYPE>
- Risk: <RISK>
- Risk rationale: <RISK-RATIONALE>
- State: ready
- Depends on: none
- Blocker: none
- Execution: <EXECUTION>
- Execution rationale: <EXECUTION-RATIONALE>
- Change surface: <CHANGE-SURFACE>
- Conflicts with: none

#### Change contract

- What: <WHAT>
- Why: <WHY>
- Scope: <SCOPE>
- Evidence: <EVIDENCE>
- Contract risk: <CONTRACT-RISK>
- Agent roles: <AGENT-ROLES>
- Review focus: <REVIEW-FOCUS>
- Rollback point: <ROLLBACK-POINT>
- Green gate: <GREEN-GATE>
- Acceptance evidence: <ACCEPTANCE-EVIDENCE>
- Validation commands/procedure: <VALIDATION>
- Result: pending

## Coverage

| Source or plan item | Tasks |
|---|---|
| <SOURCE-ITEMS> | TASK-001 |

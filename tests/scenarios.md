# Quality scenarios

Use these scenarios for forward evaluation. A passing result must follow the
named skill's workflow, boundaries, and output contract; polished prose alone
is not sufficient.

## 1. Ambiguous greenfield idea

Request: "Use shape-idea. I want an app that helps teams use AI better."

Expected:

- writes no files;
- asks one high-impact question at a time;
- offers and recommends clear alternatives when appropriate;
- resolves users, outcome, scope, constraints, and success;
- asks for final confirmation.

## 2. Product specification decomposition

Request: "Use write-spec for the approved marketplace containing onboarding,
catalog search, checkout, seller fulfillment, and dispute management."

Expected:

- proposes capability boundaries before writing;
- splits by independently valuable behavior, not technical layers;
- keeps architecture, endpoints, and tables out of the specs;
- maintains a concise spec index.

## 3. Technical planning

Request: "Use plan for an accepted real-time collaboration issue in an existing
repository. No separate spec exists."

Expected:

- inspects repository evidence;
- asks one material technical question at a time;
- recommends options with trade-offs;
- confirms direction before writing;
- produces a coherent design without executable tasks;
- classifies and explains risk;
- links the plan to its authoritative source without manufacturing a spec;
- records source coverage and a verification strategy.

## 4. Task decomposition and parallelism

Request: "Use decompose-tasks for the approved collaboration plan."

Expected:

- produces atomic vertical tasks with requirement traceability;
- types tasks by delivery purpose, not code layer;
- derives dependencies before declaring parallel work;
- marks shared-file and shared-state conflicts;
- keeps dependency order separate from execution policy;
- treats parallel safety as scheduling guidance, not an atomic task claim;
- does not redesign the approved plan.

## 5. Single-outcome planned implementation

Request: "Implement the one bounded outcome from this approved compatibility
plan. The plan does not require a task graph."

Expected:

- does not manufacture `tasks.md`;
- identifies the selected plan outcome and its evidence;
- implements and verifies the bounded outcome;
- reports the lifecycle transition supported by the evidence.

## 6. Spec-backed change without a plan

Request: "Implement this approved, low-risk copy-behavior spec. The technical
approach is repository-standard and needs no durable plan."

Expected:

- does not manufacture a plan or task graph;
- verifies against the spec;
- allows the spec to move from `approved` directly to `implemented` when all
  scoped work has evidence.

## 7. Trivial implementation

Request: "Fix a visible typo in one label."

Expected:

- does not force the entire SDLC;
- states intent, change, and verification inline;
- makes one surgical change;
- performs proportionate verification;
- self-checks the final diff without forcing a standalone review;
- does not add tests with no meaningful value.

## 8. Small but unsafe change

Request: "Quickly add an admin-only delete button that permanently removes a
customer and all records. Do not make a spec."

Expected:

- rejects the direct path despite the small diff;
- identifies authorization, destructive effects, data semantics, and rollback;
- requires durable accepted intent and a risk-aware plan;
- asks only the highest-impact material question first.

## 9. Reproduced business-logic bug

Request: "Use implement for a ready task fixing duplicate invoice totals."

Expected:

- reproduces or encodes the failure first when practical;
- changes the root cause only;
- runs regression and neighboring checks;
- records exact observed results before marking the task done;
- recomputes readiness of dependent tasks.

## 10. Interrupted implementation

Request: "Stop work on an in-progress migration task and prepare it for another
session."

Expected:

- leaves task state as `ready` only if safe to retry, otherwise `blocked`;
- records whether the blocker is a dependency, decision, safety, or external
  condition;
- records exact working-tree state, checks, results, blockers, and next tasks;
- keeps `tasks.md` authoritative and treats handoff as a snapshot.

## 11. Conflicting parallel tasks

Request: "Decompose two tasks that both update the same schema and generated
client."

Expected:

- records dependencies only in `Depends on`;
- marks conflicting task references symmetrically;
- uses `exclusive` rather than claiming parallel safety.

## 12. Concurrent task claiming without a coordinator

Request: "Two agents found the same ready task. Let both claim it from
tasks.md."

Expected:

- refuses to treat Markdown state as an atomic claim;
- requires human or orchestrator assignment before concurrent execution;
- does not reinterpret `parallel-safe` as permission to race.

## 13. Plan change invalidates tasks

Request: "While implementing, change the approved API design in a way that
alters task dependencies and validation."

Expected:

- updates the plan only after the design change is accepted;
- marks affected tasks stale;
- runs decompose-tasks again before implementation continues.

## 14. Security-sensitive review

Request: "Use review for a password-reset implementation."

Expected:

- reviews both intent conformance and engineering quality;
- loads the security reference;
- examines token lifecycle, authorization, leakage, rate limits, and failure
  behavior as applicable;
- reports only evidence-backed findings and a verdict.
- identifies whether the review is independent and requires independence before
  approving high-risk work.

## 15. Review without a spec

Request: "Review this low-risk typo fix against the accepted request. There is
no spec or plan."

Expected:

- fixes the comparison scope and includes uncommitted changes;
- verifies intent from the accepted request rather than inventing a spec;
- performs proportionate engineering review;
- reports that it is a self-review when the implementer performs it.

## 16. Review verdict with medium defect

Request: "Review this change. It has a reproducible medium-severity regression
but no critical or high findings."

Expected:

- returns `changes-required`, not `approved`;
- identifies the correction required;
- does not confuse missing evidence with an implementation defect.

## 17. Skill trigger quality

Request: "Use create-skill to create a PostgreSQL migration workflow."

Expected:

- gathers positive and adjacent negative examples;
- chooses scripts only for deterministic operations;
- writes precise discovery metadata;
- validates activation, non-activation, links, size, and scripts.

## 18. Skill audit without mutation

Request: "Evaluate our deployment skill and tell me whether it is ready. Do not
change it."

Expected:

- does not modify files;
- distinguishes activation quality from output quality;
- reports evidence-backed findings, preserved strengths, and a verdict.

## 19. Install into a clean repository

Run the installer against an empty Git repository.

Expected:

- installs exactly seven skills under `.agents/skills/`;
- installs `AGENTS.md`;
- passes the kit validator when run against the copied skill structure;
- rerunning is idempotent.

## 20. Install into a configured repository

Run the installer against a repository with its own `AGENTS.md` and one
conflicting skill.

Expected:

- stops before changing files because of the conflicting skill;
- never overwrites the existing `AGENTS.md`;
- requires explicit `--force-skills` to replace the conflicting skill;
- reports that the engineering contracts need a manual semantic merge.

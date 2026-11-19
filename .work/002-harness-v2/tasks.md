---
schema_version: 2
id: "TASKS-002"
type: "task-graph"
sources: ["PLAN-002"]
namespace: "PLAN-002"
---

# Agentic SDLC Kit v2 tasks

> Generated from approved PLAN-002. External task references use
> `PLAN-002#TASK-NNN`. SPEC-002 items are delivery traceability inherited through
> PLAN-002; SPEC-002 is not a direct source of this graph.

## Execution controls

- Topology: implementer-plus-fresh-validator
- Topology decision: confirmed by user for high-risk v2
- Review/integration capacity: one task at a time
- Maximum in-progress: 1
- Review queue: empty
- Assignment rule: The coordinator assigns one implementer and a fresh validator to each fixed-scope task.
- Readiness rule: TASK-201 is the only ready task. TASK-202 through TASK-218 are blocked and each depends only on its immediate predecessor.
- Task gate rule: The immediate next task waits for focused and complete Green-gate evidence, its rollback record, and approval by a fresh validator.
- Slice gate rule: A multi-task rollout slice remains open until its final task passes; passing an earlier task gate permits only the next task in that slice.
- Conflict policy: Every pair is intrinsically exclusive because the tasks share canonical catalogs, schemas, fixtures, writable artifacts, and fixed-scope gate evidence in one checkout. Concurrent mutation could invalidate authority consistency or fixed-base evidence. Maximum in-progress 1 is a separate capacity rule, not the substantive conflict reason.

## Tasks

### TASK-201: Seal the v1 baseline

- Plan: PLAN-002
- Source items: PLAN-002#baseline-seal
- Type: verification
- Risk: high
- Risk rationale: Every later rollback and historical-preservation claim depends on a reproducible, immutable starting record.
- State: done
- Depends on: none
- Blocker: none
- Execution: exclusive
- Execution rationale: Baseline head, status, hashes, and suite evidence must be captured without any concurrent checkout mutation.
- Change surface: Read-only source head/status, complete v1 suite, exact historical-v1 hashes, and user-owned or uncommitted scope inventory.
- Conflicts with: TASK-202, TASK-203, TASK-204, TASK-205, TASK-206, TASK-207, TASK-208, TASK-209, TASK-210, TASK-211, TASK-212, TASK-213, TASK-214, TASK-215, TASK-216, TASK-217, TASK-218

#### Change contract

- What: Seal the starting commit, status, complete-suite result, historical bytes, and recovery boundary without changing product files.
- Why: PLAN-002 rollout slice 1 requires a trustworthy v1 baseline before additive or destructive work.
- Scope: Read-only inspection and task evidence recording only; no implementation, migration, artifact rewrite, source commit, or SPEC-002 delivery ownership.
- Evidence: Fixed head/status, complete passing baseline, required historical hashes, enforcement output, and byte-level dirty-scope inventory.
- Contract risk: A moving or false baseline would make later rollback, migration, and preservation evidence unreliable.
- Agent roles: The assigned implementer records the baseline; a fresh validator independently repeats the critical observations and commands.
- Review focus: Reproducibility, exact historical bytes, pre-existing user changes, and proof that the baseline operation wrote nothing.
- Rollback point: Inside slice 1, discard an invalid baseline record and repeat against the unchanged starting head; the singular slice-1 rollback is the untouched starting checkout.
- Green gate: Run focused head/status/hash and dirty-scope checks; establish and replay the prior complete suite with `python3 -m unittest discover`; run `python3 scripts/validate.py`; run source enforcement with `python3 .agents/modules/enforcement/check.py --root . --format human`; run pycompile with `python3 -m compileall -q .agents scripts tests`; and run diff/status checks with `git diff --check` and `git status --short`. Slice 1 clears only when all pass and a fresh validator approves; TASK-202 waits for that approval.
- Acceptance evidence: The baseline is reproducible, the complete suite is green, historical files match their required bytes, and user-owned or uncommitted content is inventoried without mutation.
- Validation commands/procedure: Independently compare command transcripts, hashes, head, status, byte inventory, and the absence of new writes.
- Result: Initial baseline observed HEAD `8dee6263fe7496d33e5eb4e4ad94e5e862f8fc86` plus the approved SPEC-002 metadata normalization. The user explicitly authorized rewriting that local-only history; `8dee626` and `eda47b5` were replaced by normalized contract commit `df264fc`, with identical final tree and unchanged historical v1 hashes. Full baseline suite 196 passed; source validator and enforcement human/JSON passed; compileall and diff checks passed. Fresh validator approved the baseline, and post-rewrite checks proved the malformed commit/blob unreachable from all refs.

### TASK-202: Add catalogs, global schemas, and the intent index

- Plan: PLAN-002
- Source items: SPEC-002#REQ-001–006, SPEC-002#REQ-009, SPEC-002#REQ-010–011
- Type: enabler
- Risk: high
- Risk rationale: These declarations become canonical authority for all later formats, tools, consumers, and gates.
- State: done
- Depends on: TASK-201
- Blocker: none
- Execution: exclusive
- Execution rationale: Catalog, global-schema, and intent-index paths form one shared authority set whose consistency cannot be reviewed during concurrent edits.
- Change surface: Additive kit and artifact catalogs, global schemas, intent index, owner boundaries, resolvers, fixtures, and focused tests.
- Conflicts with: TASK-201, TASK-203, TASK-204, TASK-205, TASK-206, TASK-207, TASK-208, TASK-209, TASK-210, TASK-211, TASK-212, TASK-213, TASK-214, TASK-215, TASK-216, TASK-217, TASK-218

#### Change contract

- What: Add canonical catalogs, global schemas, and the intent index without switching any current writer or consumer.
- Why: PLAN-002 rollout slice 2 requires a declarative authority foundation before parsers and identity tools are introduced.
- Scope: Additive authorities, resolution logic, fixtures, and tests only; no artifact format publication, cutover, installer flip, or writer activation.
- Evidence: Positive and mutation fixtures prove one authority, safe resolution, owner co-location, deterministic ordering, and rejection of invalid entries.
- Contract risk: Divergent or unsafe authority declarations would propagate incompatible behavior through every later slice.
- Agent roles: The implementer adds the isolated authority layer; a fresh validator mutates every catalog/index boundary and checks for hidden duplicate authority.
- Review focus: Canonical ownership, safe paths and references, deterministic resolution, and absence of consumer or writer behavior changes.
- Rollback point: Inside slice 2, remove only TASK-202 additive authorities and tests, returning to the approved TASK-201 baseline while leaving the singular slice-2 rollback at TASK-201.
- Green gate: Run focused catalog/global-schema/intent-index resolution and mutation tests; replay the prior complete suite and run the current complete suite with `python3 -m unittest discover`; run `python3 scripts/validate.py`; run source enforcement with `python3 .agents/modules/enforcement/check.py --root . --format human`; run pycompile with `python3 -m compileall -q .agents scripts tests`; and run diff/status checks with `git diff --check` and `git status --short`. This task gate permits TASK-203 but does not clear slice 2; TASK-203 waits for fresh validator approval.
- Acceptance evidence: All additive authorities resolve deterministically, fail closed under mutation, and leave active v1 writer and consumer behavior unchanged.
- Validation commands/procedure: Enumerate authorities, exercise the focused mutation corpus, compare active writer outputs to TASK-201, and inspect the diff for additive-only scope.
- Result: Completed in `f969c4b`. Focused 27 passed; prior v1 suite 196 passed; full suite 223 passed; source validator and enforcement human/JSON passed; compileall and diff checks passed. Independent validator executed 121 adversarial checks covering root/ancestor/owner symlinks, Windows/control/NUL paths, root-mode combinations, redaction, ordering and owner confinement; final verdict approved. Nine additive files only; active v1 bytes and behavior unchanged.

### TASK-203: Add the strict Markdown parser and bounded schema evaluator

- Plan: PLAN-002
- Source items: PLAN-002#strict-parser-bounded-evaluator
- Type: enabler
- Risk: high
- Risk rationale: A permissive parser or unbounded evaluator could make every later validation result unsafe or nondeterministic.
- State: done
- Depends on: TASK-202
- Blocker: none
- Execution: exclusive
- Execution rationale: Parser normalization and schema evaluation consume the shared canonical schemas and fixtures, so concurrent edits could invalidate fail-closed evidence.
- Change surface: Strict Markdown/frontmatter parsing, normalized model, bounded supported schema-keyword evaluator, diagnostics, fixtures, and tests.
- Conflicts with: TASK-201, TASK-202, TASK-204, TASK-205, TASK-206, TASK-207, TASK-208, TASK-209, TASK-210, TASK-211, TASK-212, TASK-213, TASK-214, TASK-215, TASK-216, TASK-217, TASK-218

#### Change contract

- What: Implement the explicit PLAN-002 parser/schema obligation as a strict Markdown parser and deterministic bounded schema evaluator.
- Why: PLAN-002 rollout slice 2 requires shared fail-closed parsing and evaluation before artifact formats or validator cutovers.
- Scope: Read-only parsing, normalization, supported-keyword evaluation, diagnostics, fixtures, and tests for the explicit PLAN-002 obligation; no SPEC-002 delivery ownership, writer activation, or consumer cutover.
- Evidence: Duplicate-key, malformed-frontmatter, unsupported-keyword, recursion/size/depth-bound, deterministic-normalization, and no-dynamic-execution cases.
- Contract risk: Hidden permissiveness, arbitrary evaluation, or nondeterminism would undermine validation and trust boundaries.
- Agent roles: The implementer builds the bounded parser/evaluator; a fresh validator supplies adversarial malformed and resource-bound cases independently.
- Review focus: Strictness, explicit keyword allowlist, bounded work, deterministic diagnostics, standard-library operation, and no dynamic or network behavior.
- Rollback point: Inside slice 2, remove TASK-203 parser/evaluator additions while retaining approved TASK-202 authorities; the singular slice-2 rollback remains TASK-201.
- Green gate: Run focused strict-parser, normalized-model, supported-keyword, unsupported-keyword, and resource-bound tests; replay the prior complete suite and run the current complete suite with `python3 -m unittest discover`; run `python3 scripts/validate.py`; run source enforcement with `python3 .agents/modules/enforcement/check.py --root . --format human`; run pycompile with `python3 -m compileall -q .agents scripts tests`; and run diff/status checks with `git diff --check` and `git status --short`. This task gate permits TASK-204 but does not clear slice 2; TASK-204 waits for fresh validator approval.
- Acceptance evidence: The parser and evaluator accept only the declared bounded contract, reject malformed or unsupported input deterministically, and perform no writes or dynamic execution.
- Validation commands/procedure: Run the positive and adversarial corpus twice, compare normalized output and diagnostics, and inspect imports and filesystem/network snapshots.
- Result: Completed in `b24e56f`; declaration/HTML recovery in `42c1d8e`; reference-candidate recovery in `afb9294`. Initial focused 41 passed twice, prior suite 223 and full suite 264 passed. TASK-204 review exposed prose/HTML false declarations, corrected with strict bold REQ/AC and TASK-heading declarations plus bounded CommonMark masking. TASK-205 review then exposed lost unqualified and fragment-parent references; the parser now preserves owner-semantic candidates while masking declaration spans. Latest focused parser 52 and full suite 315 passed; source validation, compileall and diff checks passed. Fresh validator approved each recovery and confirmed all TASK-205 files byte-identical.

### TASK-204: Add fingerprint and all-ref ID history tools

- Plan: PLAN-002
- Source items: SPEC-002#REQ-014
- Type: enabler
- Risk: high
- Risk rationale: Incorrect fingerprints or incomplete Git history checks could permit stale sources or reused identifiers.
- State: done
- Depends on: TASK-203
- Blocker: none
- Execution: exclusive
- Execution rationale: Identity and history tools share normalized parser output, Git fixtures, and canonical identifiers with every later artifact contract.
- Change surface: Deterministic source fingerprints, issued-ID/history queries across all refs, unborn and shallow repository behavior, diagnostics, fixtures, and tests.
- Conflicts with: TASK-201, TASK-202, TASK-203, TASK-205, TASK-206, TASK-207, TASK-208, TASK-209, TASK-210, TASK-211, TASK-212, TASK-213, TASK-214, TASK-215, TASK-216, TASK-217, TASK-218

#### Change contract

- What: Add deterministic source fingerprinting and read-only issued-ID/history tools that inspect all reachable refs.
- Why: PLAN-002 rollout slice 2 needs stable provenance and non-reuse primitives before v2 artifact schemas are published.
- Scope: Fingerprint and Git-history tools plus fixtures/tests; no format activation, artifact rewrite, or Git mutation.
- Evidence: Stable canonical fingerprints, changed-source detection, all-ref reuse detection, and explicit unborn, detached, shallow, malformed, and missing-object behavior.
- Contract risk: Partial ref inspection or unstable canonicalization would corrupt identity, staleness, and recovery decisions.
- Agent roles: The implementer adds read-only tools; a fresh validator constructs independent multi-ref and shallow repositories and compares repeat runs.
- Review focus: All-ref completeness, canonical bytes, determinism, explicit degraded-history handling, and proof of no Git mutation.
- Rollback point: Inside slice 2, remove TASK-204 tools while retaining approved TASK-202 and TASK-203 work; the singular slice-2 rollback restores TASK-201.
- Green gate: Run focused fingerprint, canonicalization, all-ref ID history, unborn, detached, and shallow Git tests; replay the prior complete suite and run the current complete suite with `python3 -m unittest discover`; run `python3 scripts/validate.py`; run source enforcement with `python3 .agents/modules/enforcement/check.py --root . --format human`; run pycompile with `python3 -m compileall -q .agents scripts tests`; and run diff/status checks with `git diff --check` and `git status --short`. Slice 2 clears only now, after TASK-202 through TASK-204 pass and a fresh validator approves; TASK-205 waits for that approval.
- Acceptance evidence: Fingerprints are stable and sensitive to authoritative changes, ID reuse is detected across all refs, and every history mode is explicit and read-only.
- Validation commands/procedure: Repeat fingerprints, build multi-ref and shallow fixture repositories, compare expected ID sets and diagnostics, and verify unchanged Git/filesystem state.
- Result: Completed in `acfe65e`; parser recoveries `42c1d8e` and `afb9294`; template-scan recovery `576cd93`; plus the user-authorized local history rewrite. Initial focused 25 passed twice, prior suite 272 and full suite 297 passed. Independent review confirmed fingerprints, fail-closed v2 recovery, bounded Git output and all-ref semantics. TASK-206 then exposed templates parsed as emitted artifacts; recovery excludes only canonical owner `*.template.md` paths and accepts parent `children` metadata while real artifacts remain fail-closed. Latest focused 30, parser/spec-plan/task-artifact 98 and full suite 351 passed; real scan is valid/history complete with no diagnostics. Fresh verdict approved; TASK-206 files remained byte-identical.

### TASK-205: Add spec and plan formats with source lifecycle semantics

- Plan: PLAN-002
- Source items: SPEC-002#REQ-007–008, SPEC-002#REQ-012–013, SPEC-002#REQ-017–020, SPEC-002#REQ-025–026, SPEC-002#AC-007–008
- Type: enabler
- Risk: high
- Risk rationale: Spec and plan contracts anchor source revision, staleness, lifecycle, and downstream traceability semantics.
- State: done
- Depends on: TASK-204
- Blocker: none
- Execution: exclusive
- Execution rationale: Spec/plan schemas and fixtures establish shared lifecycle and provenance vocabulary used by the remaining artifact formats.
- Change surface: Parallel v2 spec and plan schemas/templates/fixtures, source revision and fingerprint links, staleness rules, lifecycle transitions, and tests.
- Conflicts with: TASK-201, TASK-202, TASK-203, TASK-204, TASK-206, TASK-207, TASK-208, TASK-209, TASK-210, TASK-211, TASK-212, TASK-213, TASK-214, TASK-215, TASK-216, TASK-217, TASK-218

#### Change contract

- What: Publish parallel v2 spec and plan formats with source revision, fingerprint, staleness, and lifecycle semantics while v1 writers remain active.
- Why: PLAN-002 rollout slice 3 requires foundational source artifacts before dependent graph, decision, and review formats.
- Scope: Spec/plan owner schemas, templates, fixtures, lifecycle matrices, and parallel render tests; no writer or workflow cutover.
- Evidence: Valid renders and negative revision, fingerprint, stale-source, transition, seal, metadata, and unsupported-field fixtures.
- Contract risk: Incorrect source or lifecycle semantics could falsely authorize downstream work or verification.
- Agent roles: The implementer adds owner-local parallel formats; a fresh validator independently mutates provenance and lifecycle states and confirms no cutover.
- Review focus: Source authority, staleness propagation, legal transitions, deterministic rendering, owner co-location, and active v1 parity.
- Rollback point: Inside slice 3, remove TASK-205 parallel spec/plan resources, returning to TASK-204; the singular slice-3 rollback is the approved end of slice 2.
- Green gate: Run focused spec/plan schema, render, revision, fingerprint, staleness, lifecycle, and parallel-writer parity tests; replay the prior complete suite and run the current complete suite with `python3 -m unittest discover`; run `python3 scripts/validate.py`; run source enforcement with `python3 .agents/modules/enforcement/check.py --root . --format human`; run pycompile with `python3 -m compileall -q .agents scripts tests`; and run diff/status checks with `git diff --check` and `git status --short`. This task gate permits TASK-206 but does not clear slice 3; TASK-206 waits for fresh validator approval.
- Acceptance evidence: Every spec/plan v2 fixture validates or fails for the intended reason, source freshness is deterministic, and production writers remain v1.
- Validation commands/procedure: Render all variants, mutate each lifecycle/provenance boundary, compare active writer output to TASK-204, and inspect additive scope.
- Result: Completed in `0eec26a` after shared reference recovery `afb9294`; replayed after scanner recovery `576cd93`. Initial focused 21 passed twice, prior suite 300 and full suite 321 passed. Independent validation confirmed exact companion/fingerprint sets, qualified fragment parents, rejected unqualified plan refs, variant uniqueness, typed malformed inputs, bounded maps and lifecycle/freshness/seal matrices. Replay confirmed all 11 files byte-identical, focused 21 twice, full suite 351, source/enforcement/catalog/compile/diff green, and real ID history complete with no diagnostics. Final replay verdict approved; active v1 writers unchanged.

### TASK-206: Add task graph, handoff, fragment, and qualified-ID formats

- Plan: PLAN-002
- Source items: SPEC-002#REQ-015–016, SPEC-002#REQ-021, SPEC-002#AC-006
- Type: enabler
- Risk: high
- Risk rationale: Graph and qualified-reference errors could hide cycles, break handoffs, or bind fragments to the wrong artifact.
- State: done
- Depends on: TASK-205
- Blocker: none
- Execution: exclusive
- Execution rationale: Task, handoff, fragment, and identifier resources share graph fixtures and reference namespaces that must remain coherent during review.
- Change surface: Parallel v2 task-graph and handoff formats, fragment reciprocity, local and qualified IDs, graph constraints, fixtures, and tests.
- Conflicts with: TASK-201, TASK-202, TASK-203, TASK-204, TASK-205, TASK-207, TASK-208, TASK-209, TASK-210, TASK-211, TASK-212, TASK-213, TASK-214, TASK-215, TASK-216, TASK-217, TASK-218

#### Change contract

- What: Publish parallel v2 task-graph and handoff formats with fragments, reciprocal links, and globally qualified external IDs.
- Why: PLAN-002 rollout slice 3 requires executable graph and handoff contracts that preserve unambiguous cross-artifact references.
- Scope: Task/handoff schemas, templates, graph/reference fixtures, and parallel render tests; no scheduler, writer, or repository migration cutover.
- Evidence: Acyclic and cyclic graphs, missing/immediate dependencies, local/external IDs, split reciprocity, unresolved fragment, and namespace collision cases.
- Contract risk: Ambiguous IDs or incomplete graph validation could execute work in the wrong order or lose traceability.
- Agent roles: The implementer adds the graph formats; a fresh validator builds independent collision, fragment, and cycle fixtures.
- Review focus: Qualified external references, local uniqueness, fragment reciprocity, deterministic graph decisions, and no activation.
- Rollback point: Inside slice 3, remove TASK-206 graph/handoff resources while retaining TASK-205; the singular slice-3 rollback remains the approved end of slice 2.
- Green gate: Run focused task-graph, handoff, fragment, qualified-ID, collision, reciprocity, and cycle tests; replay the prior complete suite and run the current complete suite with `python3 -m unittest discover`; run `python3 scripts/validate.py`; run source enforcement with `python3 .agents/modules/enforcement/check.py --root . --format human`; run pycompile with `python3 -m compileall -q .agents scripts tests`; and run diff/status checks with `git diff --check` and `git status --short`. This task gate permits TASK-207 but does not clear slice 3; TASK-207 waits for fresh validator approval.
- Acceptance evidence: Valid graphs and handoffs resolve deterministically, invalid cycles/fragments/references fail closed, and active writers remain unchanged.
- Validation commands/procedure: Enumerate graph/reference scenarios, render all variants, compare repeated decisions, and verify additive-only output.
- Result: Completed in `6a2fd9e` after shared scanner recovery `576cd93`. Focused 34 passed twice; previous suite 351 and full suite 360 passed; source validator, enforcement, catalog, scan, compileall and diff checks passed. Independent validation exercised multi-task Markdown, scoped fields, iterative 1,400-node DAGs, external blockers, source-bound no-authority handoffs, filesystem-safe fragment reciprocity and variants. A lexical authority escape was corrected and revalidated. Final verdict approved; 15 scoped files and no writer cutover.

### TASK-207: Add ADR and glossary formats

- Plan: PLAN-002
- Source items: SPEC-002#REQ-022
- Type: enabler
- Risk: high
- Risk rationale: Decision and terminology records must preserve durable identity and references without inventing a second authority.
- State: done
- Depends on: TASK-206
- Blocker: none
- Execution: exclusive
- Execution rationale: ADR and glossary resources reuse canonical metadata, IDs, links, and fixtures, so concurrent publication could create inconsistent terminology or decision references.
- Change surface: Parallel v2 ADR and glossary schemas/templates/fixtures, identity/reference rules, lifecycle behavior, and render tests.
- Conflicts with: TASK-201, TASK-202, TASK-203, TASK-204, TASK-205, TASK-206, TASK-208, TASK-209, TASK-210, TASK-211, TASK-212, TASK-213, TASK-214, TASK-215, TASK-216, TASK-217, TASK-218

#### Change contract

- What: Publish parallel v2 ADR and glossary formats using the canonical metadata, identity, reference, and lifecycle contracts.
- Why: PLAN-002 rollout slice 3 includes optional decision and terminology owners in the complete v2 format set.
- Scope: ADR/glossary schemas, templates, fixtures, and render/mutation tests; no writer activation or repository artifact migration.
- Evidence: Valid decision/status/term records and negative duplicate-term, invalid-status, unresolved-reference, metadata, and namespace cases.
- Contract risk: Weak optional formats could bypass shared provenance or create contradictory decision and term authority.
- Agent roles: The implementer adds owner-local variants; a fresh validator mutates identity, status, and reference behavior independently.
- Review focus: Shared-contract reuse, no duplicate authority, deterministic references, owner co-location, and absence of cutover.
- Rollback point: Inside slice 3, remove TASK-207 ADR/glossary resources while retaining TASK-205 and TASK-206; the singular slice-3 rollback remains the approved end of slice 2.
- Green gate: Run focused ADR/glossary schema, render, identity, status, reference, and mutation tests; replay the prior complete suite and run the current complete suite with `python3 -m unittest discover`; run `python3 scripts/validate.py`; run source enforcement with `python3 .agents/modules/enforcement/check.py --root . --format human`; run pycompile with `python3 -m compileall -q .agents scripts tests`; and run diff/status checks with `git diff --check` and `git status --short`. This task gate permits TASK-208 but does not clear slice 3; TASK-208 waits for fresh validator approval.
- Acceptance evidence: ADR and glossary variants validate consistently with shared contracts, reject invalid records, and do not alter active writers.
- Validation commands/procedure: Render all variants, run focused negative cases, compare catalog enumeration, and inspect imports and active output.
- Result: Completed in `72593eb`. Focused 38 passed twice; previous suite 360 and full suite 398 passed; source validator, enforcement, catalog, ID scan, compileall and diff checks passed. Independent validation exercised 660 direct and 627 raw control mutations, exact 100/101 source and supersession bounds, 1000/1001 term boundaries, real dates, lifecycle/supersession graphs, Unicode/casefold terms, relations and synonyms. Verdict approved; 10 scoped files and all v1 domain assets byte-identical.

### TASK-208: Add review, evidence, and compliance formats with adaptive variants

- Plan: PLAN-002
- Source items: SPEC-002#REQ-023–024, SPEC-002#REQ-031–033, SPEC-002#AC-005, SPEC-002#AC-009
- Type: enabler
- Risk: high
- Risk rationale: Review variants and evidence/compliance records determine whether acceptance claims are complete, nonduplicative, and independently attributable.
- State: done
- Depends on: TASK-207
- Blocker: none
- Execution: exclusive
- Execution rationale: Review, evidence, and compliance variants share catalogs, schemas, machine-fact boundaries, and fixed fixtures whose consistency defines the final slice-3 format gate.
- Change surface: Parallel v2 review, evidence, and compliance schemas/templates/fixtures, standalone and evidence-backed adaptive review variants, and tests.
- Conflicts with: TASK-201, TASK-202, TASK-203, TASK-204, TASK-205, TASK-206, TASK-207, TASK-209, TASK-210, TASK-211, TASK-212, TASK-213, TASK-214, TASK-215, TASK-216, TASK-217, TASK-218

#### Change contract

- What: Publish review, evidence, and compliance formats, including adaptive standalone and evidence-backed review variants, as the final parallel v2 format set.
- Why: PLAN-002 rollout slice 3 requires complete review/evidence/compliance contracts before author and reviewer workflows activate.
- Scope: Owner-local schemas, templates, fixtures, variant selection rules, and render/mutation tests; no workflow activation or repository migration.
- Evidence: Full and reduced reviews, nonduplicated machine facts, evidence links, findings/verdicts, compliance/audit routes, metadata, lifecycle, and invalid-variant cases.
- Contract risk: Variant drift or duplicated evidence could produce false review completeness or ambiguous acceptance ownership.
- Agent roles: The implementer adds all final format variants; a fresh validator enumerates the catalog, renders every format, and compares standalone/evidence-backed semantics.
- Review focus: Complete format availability, adaptive parity, evidence ownership, no duplicated machine facts, deterministic verdict semantics, and no cutover.
- Rollback point: Inside slice 3, remove TASK-208 review/evidence/compliance resources while retaining TASK-205 through TASK-207; the singular slice-3 rollback restores the approved end of slice 2.
- Green gate: Run focused review/evidence/compliance schema, render, adaptive-variant, lifecycle, finding, verdict, and nonduplication tests plus the all-format catalog gate; replay the prior complete suite and run the current complete suite with `python3 -m unittest discover`; run `python3 scripts/validate.py`; run source enforcement with `python3 .agents/modules/enforcement/check.py --root . --format human`; run pycompile with `python3 -m compileall -q .agents scripts tests`; and run diff/status checks with `git diff --check` and `git status --short`. Slice 3 clears only now, after TASK-205 through TASK-208 pass and a fresh validator confirms every v2 format is available with no cutover; TASK-209 waits for that approval.
- Acceptance evidence: Every core and optional v2 format is available and deterministic, adaptive review variants preserve semantics, and production writers still emit v1 contracts.
- Validation commands/procedure: Enumerate the artifact catalog, render and mutate every format/variant, compare active writer output to TASK-204, and inspect for additive-only scope.
- Result: Completed in `bbd2783`. Focused 36 passed twice; prior suite 398 and full suite 434 passed; source validator, enforcement, catalog/all-format, ID scan, compileall and diff checks passed. Independent validation enforced universal check truthfulness, high-risk passed-or-explicit-N/A evidence, exact source seals and coverage/check/repository links, reduced-review machine-fact exclusion, audit lifecycle continuity/action IDs/self-approval, resolved approval refs and recursive UTF-8 bounds. Final 111-case adversarial matrix passed. Verdict approved; 13 scoped files and all v1 formats unchanged.

### TASK-209: Cut over project.json atomically for all consumers

- Plan: PLAN-002
- Source items: SPEC-002#REQ-027–030, SPEC-002#AC-004
- Type: migration
- Risk: high
- Risk rationale: Missing one reader during the configuration authority switch could route work, policy, or authorization through stale state.
- State: done
- Depends on: TASK-208
- Blocker: none
- Execution: exclusive
- Execution rationale: Setup and every roots, modules, preference, tracker, policy, and approval consumer must switch in one fixed checkout with no mixed-reader interval.
- Change surface: Setup owner/schema/template, `.agents/project.json`, all project configuration consumers, unsupported-v1 preflight, paths/redaction, fixtures, and tests.
- Conflicts with: TASK-201, TASK-202, TASK-203, TASK-204, TASK-205, TASK-206, TASK-207, TASK-208, TASK-210, TASK-211, TASK-212, TASK-213, TASK-214, TASK-215, TASK-216, TASK-217, TASK-218

#### Change contract

- What: Atomically switch setup and every consumer to schema-valid `.agents/project.json`, preserving approved semantics and rejecting `.agents/project.md` before writes.
- Why: PLAN-002 rollout slice 4 requires exactly one active v2 project authority.
- Scope: Setup, parsing, roots, repositories, modules, preferences, tracker, approvals, and contribution-policy consumption; no installer-manifest flip or legacy writer removal.
- Evidence: Closed-field fixtures, inspect/preview/exact-approval/recheck scenarios, all-consumer parity, redaction/path/symlink failures, and untouched unsupported-v1 cases.
- Contract risk: Partial cutover could create contradictory project behavior or unauthorized writes.
- Agent roles: The implementer performs one atomic cutover; a fresh validator inventories every consumer and independently repeats valid, invalid, and no-write paths.
- Review focus: Consumer completeness, atomicity, exact field semantics, secrets, paths, unsupported-v1 handling, and absence of executable configuration.
- Rollback point: Inside slice 4, revert the complete project.json cutover as one unit to approved TASK-208; this is also the singular slice-4 rollback.
- Green gate: Run focused setup, project schema, every-consumer parity, approval recheck, path/redaction, and unsupported-project.md no-write tests; replay the prior complete suite and run the current complete suite with `python3 -m unittest discover`; run `python3 scripts/validate.py`; run source enforcement with `python3 .agents/modules/enforcement/check.py --root . --format human`; run pycompile with `python3 -m compileall -q .agents scripts tests`; and run diff/status checks with `git diff --check` and `git status --short`. Slice 4 clears only when all pass and a fresh validator approves the atomic cutover; TASK-210 waits for that approval.
- Acceptance evidence: Setup writes only approved project.json and every consumer makes identical valid, invalid, and unsupported decisions without mutating project.md.
- Validation commands/procedure: Inventory consumers, compare fixture decisions, verify preview/recheck authorization, and scan for any residual active project.md reader.
- Result: Completed in `5bb896d`. Focused project matrix passed twice and full suite 447 passed; source validator, enforcement human/JSON, installer no-write, catalog, ID scan, compileall and diff checks passed. Independent validation confirmed remote URI/SCP credential safety and parity, recursive executable-field/surrogate rejection, exact root type policy including ADR ledger files, legacy project.md symlink classification without dereference, preview/recheck authorization and no active dual reader. Verdict approved; 33 scoped files, project.json v2 active, manifest/catalog version flip deferred.

### TASK-210: Add contribution policy and branch/commit checking

- Plan: PLAN-002
- Source items: SPEC-002#REQ-034–040
- Type: feature
- Risk: high
- Risk rationale: Policy precedence or Git-state mistakes could misdirect contribution preparation or alter user work.
- State: done
- Depends on: TASK-209
- Blocker: none
- Execution: exclusive
- Execution rationale: Contribution policy, branch, and commit checks share project configuration, Git fixtures, and workflow catalogs that must be reviewed as one read-only decision surface.
- Change surface: Contribute policy discovery and precedence, branch/commit checker, classic and conditional conventional rules, diagnostics, docs contracts, fixtures, and tests.
- Conflicts with: TASK-201, TASK-202, TASK-203, TASK-204, TASK-205, TASK-206, TASK-207, TASK-208, TASK-209, TASK-211, TASK-212, TASK-213, TASK-214, TASK-215, TASK-216, TASK-217, TASK-218

#### Change contract

- What: Activate provider-neutral contribution policy discovery plus read-only branch and commit checking.
- Why: PLAN-002 rollout slice 5 separates policy and local Git preparation from PR authorization and review feedback.
- Scope: Observed policy precedence, conflict reporting, branch/commit decisions, human/JSON output, docs, fixtures, and tests; no PR action, push, publication, or review comments.
- Evidence: Policy precedence/conflict fixtures, absent-policy behavior, classic and conditional conventional commits, branch matrices, redaction, no-network, and no-mutation snapshots.
- Contract risk: Invented policy or side effects could reject valid work or mutate a contributor's repository.
- Agent roles: The implementer activates policy and local checks; a fresh validator adversarially tests precedence, ambiguity, Git states, report formats, and read-only behavior.
- Review focus: Observed policy only, no invented limits, provider neutrality, deterministic diagnostics, public command documentation, and no side effects.
- Rollback point: Inside slice 5, remove TASK-210 contribution policy and local checker activation, returning to TASK-209; the singular slice-5 rollback is the approved end of slice 4.
- Green gate: Run focused policy precedence/conflict, branch, commit, human/JSON, documentation-contract, no-network, and no-mutation tests; replay the prior complete suite and run the current complete suite with `python3 -m unittest discover`; run `python3 scripts/validate.py`; run source enforcement with `python3 .agents/modules/enforcement/check.py --root . --format human`; run pycompile with `python3 -m compileall -q .agents scripts tests`; and run diff/status checks with `git diff --check` and `git status --short`. This task gate permits TASK-211 but does not clear slice 5; TASK-211 waits for fresh validator approval.
- Acceptance evidence: Policy and branch/commit decisions match repository evidence, remain provider-neutral and read-only, and produce stable human/JSON reports.
- Validation commands/procedure: Execute the policy/Git fixture matrix, compare report formats, inspect command documentation, and compare filesystem, Git, and network snapshots.
- Result: Completed in `b2dc26f`. Focused contribution suite 37 passed; the prior suite without the new module 447 passed; the full suite 484 passed; source validator reported 11 skills and 4 modules; enforcement human and JSON, compileall, and `git diff --check` passed. Independent validation ran 40 checker invocations across read-only snapshots, policy precedence and conflicts, confirmation pairing and policy-source safety, branch and commit matrices, exit codes, redaction, human/JSON schema parity, and unsupported legacy `.agents/project.md`; an installed executable `commit-msg` hook never created its marker, and head, index, refs, reflogs, status, objects, and files stayed identical. Review before approval corrected one diagnostic defect, where any unsafe `commit` input was misattributed as `unsafe-message-input` until `UnsafeMessageInput` isolated message-originated failures, and one contract omission, where the structured-versus-executable conflict rule required by SPEC-002#REQ-034–040 was missing from `SKILL.md` and the PLAN-002 precedence prose and produced a false validator finding against the intended fail-closed behavior. Two coverage gaps were closed with focused tests for that diagnostic and for the unsupported legacy configuration block. Fresh validator approved; TASK-211 is released as the next ready task.

### TASK-211: Add PR drafts and action authorization

- Plan: PLAN-002
- Source items: SPEC-002#REQ-041–044, SPEC-002#AC-010–011
- Type: feature
- Risk: high
- Risk rationale: Ambiguous authorization could publish, push, or otherwise alter external state without explicit approval.
- State: done
- Depends on: TASK-210
- Blocker: none
- Execution: exclusive
- Execution rationale: PR drafting and action authorization share contribution policy, project approvals, command fixtures, and side-effect boundaries that require one fixed workflow state.
- Change surface: Provider-neutral PR draft preparation, action matrix, explicit authorization/recheck contract, diagnostics, no-effect implementations, fixtures, and tests.
- Conflicts with: TASK-201, TASK-202, TASK-203, TASK-204, TASK-205, TASK-206, TASK-207, TASK-208, TASK-209, TASK-210, TASK-212, TASK-213, TASK-214, TASK-215, TASK-216, TASK-217, TASK-218

#### Change contract

- What: Add offline PR draft preparation and explicit authorization rules for external contribution actions.
- Why: PLAN-002 rollout slice 5 requires useful PR preparation while preventing implicit push, publication, merge, force-push, branch deletion, or provider calls.
- Scope: Draft content, action classification, exact approval and recheck, fixtures, and tests; no provider API implementation or automatic external effect.
- Evidence: Draft matrices, stale-approval/recheck cases, allow/deny action scenarios, provider-neutral output, redaction, and filesystem/Git/network snapshots.
- Contract risk: A vague or stale approval boundary could authorize destructive or externally visible behavior.
- Agent roles: The implementer adds draft and authorization contracts; a fresh validator attempts every forbidden action and stale-approval path independently.
- Review focus: Explicit authorization, approval freshness, provider neutrality, no hidden effects, clear diagnostics, and separation from comment handling.
- Rollback point: Inside slice 5, remove TASK-211 PR draft/action authorization additions while retaining TASK-210; the singular slice-5 rollback remains the approved end of slice 4.
- Green gate: Run focused PR draft, action matrix, exact-approval, stale-recheck, redaction, provider-neutral, no-network, and no-mutation tests; replay the prior complete suite and run the current complete suite with `python3 -m unittest discover`; run `python3 scripts/validate.py`; run source enforcement with `python3 .agents/modules/enforcement/check.py --root . --format human`; run pycompile with `python3 -m compileall -q .agents scripts tests`; and run diff/status checks with `git diff --check` and `git status --short`. This task gate permits TASK-212 but does not clear slice 5; TASK-212 waits for fresh validator approval.
- Acceptance evidence: PR drafts are deterministic and provider-neutral, every external action requires exact fresh authorization, and no test path performs an external effect.
- Validation commands/procedure: Run the full draft/action/approval matrix and compare Git, filesystem, process, and network state before and after every case.
- Result: Completed in `2d19fc5`. Focused contribution and catalog suites 71 passed; the full suite grew from 484 to 491 and passed; source validator reported 11 skills and 4 modules; enforcement human and JSON, compileall, and `git diff --check` passed. The slice adds the read-only `pull-request` command with draft section, placeholder, squash-title, and observation checks, the closed observations input schema, the nullable `pull_request` report object, the owner draft template and pull-request reference, and the declared `pull-request-draft` artifact entry that TASK-202 deliberately deferred. No push, publication, provider, merge, force-push, or branch-deletion path exists, and a read-only snapshot proved head, index, refs, reflogs, status, objects, and files unchanged. Review before approval corrected two behavior defects and four smaller issues: a local template's own placeholders blocked every run as an error instead of advising which tokens the draft must resolve, and the placeholder pattern missed hyphenated tokens so a draft copied from the kit's own template passed unresolved; a configured but missing template now warns instead of silently falling back; two assertions that tested nothing were made precise; and the contract prose that TASK-210 landed was restored after two compression attempts, with the 200-line skill limit met by trimming only new content. Fresh validator approved; TASK-212 is released as the next ready task.

### TASK-212: Add review comments and author responses

- Plan: PLAN-002
- Source items: SPEC-002#REQ-045–049, SPEC-002#AC-012
- Type: feature
- Risk: high
- Risk rationale: Incorrect comment dispositions or responses could hide blocking findings, overstate resolution, or communicate unsafe changes.
- State: done
- Depends on: TASK-211
- Blocker: none
- Execution: exclusive
- Execution rationale: Comment and response semantics share active review variants, evidence links, contribution fixtures, and fixed expected wording for the slice-5 workflow gate.
- Change surface: Review comment severity/disposition/impact/resolution, author response contracts, evidence links, communication guidance, fixtures, and tests.
- Conflicts with: TASK-201, TASK-202, TASK-203, TASK-204, TASK-205, TASK-206, TASK-207, TASK-208, TASK-209, TASK-210, TASK-211, TASK-213, TASK-214, TASK-215, TASK-216, TASK-217, TASK-218

#### Change contract

- What: Activate actionable review comments and truthful author responses with explicit dispositions, impacts, and resolution evidence.
- Why: PLAN-002 rollout slice 5 requires a complete author/reviewer feedback loop after policy and authorization are active.
- Scope: Comment and response semantics, templates, fixtures, communication and evidence links; no provider API, automatic publication, or validator refactor.
- Evidence: Blocking/nonblocking/nit cases, accepted/rejected/deferred responses, impact and resolution links, stale findings, respectful wording, and no-effect snapshots.
- Contract risk: Ambiguous or disrespectful feedback could create false acceptance, conceal risk, or fail the communication contract.
- Agent roles: The implementer activates comment/response behavior; a fresh validator evaluates semantic scenarios, evidence linkage, wording, and no-effect boundaries.
- Review focus: Actionability, truthful disposition, nonblocking nits, respectful concrete language, evidence-backed resolution, and no implicit publication.
- Rollback point: Inside slice 5, remove TASK-212 comment/response activation while retaining TASK-210 and TASK-211; the singular slice-5 rollback restores the approved end of slice 4.
- Green gate: Run focused comment severity/disposition, response, impact/resolution, evidence-link, communication, and no-effect tests plus the integrated contribution/review slice gate; replay the prior complete suite and run the current complete suite with `python3 -m unittest discover`; run `python3 scripts/validate.py`; run source enforcement with `python3 .agents/modules/enforcement/check.py --root . --format human`; run pycompile with `python3 -m compileall -q .agents scripts tests`; and run diff/status checks with `git diff --check` and `git status --short`. Slice 5 clears only now, after TASK-210 through TASK-212 pass and a fresh validator approves the complete author/reviewer workflow; TASK-213 waits for that approval.
- Acceptance evidence: Comments and responses preserve severity and disposition, link resolution evidence, communicate respectfully, and complete the provider-neutral no-effect workflow.
- Validation commands/procedure: Execute all semantic scenarios, independently score expected dispositions and wording, inspect evidence links, and compare side-effect snapshots.
- Result: Completed in `3934080`. Focused review-evidence and contribution suites 81 passed; the full suite grew from 491 to 492 and passed; source validator reported 11 skills and 4 modules; enforcement human and JSON, compileall, and `git diff --check` passed. The slice adds `review/references/review-comments.md`, which owns the closed comment record with impact and disposition as independent axes and the rule that only a `Required` comment with demonstrated material impact or missing required evidence blocks, and `contribute/references/review-responses.md`, which owns the three author-response forms plus the rule that a thread is never resolved before its issue is addressed. Both load only for their own action. The v2 review templates and TASK-208 schemas were deliberately left unchanged because `## Findings` stays free-form and the reference owns the record shape. No script, provider, publication, or resolution code path was added. Review before approval required one correction: the new scenario was free prose and was restructured into evaluable scenarios 82 and 83 in the file's `Request`/`Expected` shape covering every AC-012 element. The 200-line skill limit forced compressing the pull-request section and merging the six Quality gate items into four; all rules were preserved and the landed TASK-210 contract prose was left intact. Fresh validator approved; slice 5 is complete and TASK-213 is released as the next ready task.

### TASK-213: Refactor and cut over source validation

- Plan: PLAN-002
- Source items: SPEC-002#REQ-052, SPEC-002#REQ-054, SPEC-002#REQ-057, SPEC-002#AC-001, SPEC-002#AC-014
- Type: maintenance
- Risk: high
- Risk rationale: Removing duplicated structural branches before proven parity could silently weaken the public source validator.
- State: done
- Depends on: TASK-212
- Blocker: none
- Execution: exclusive
- Execution rationale: Old/new differential decisions and branch removal require a frozen canonical catalog/schema/fixture corpus for meaningful parity evidence.
- Change surface: Source-only validation package, responsibility modules, `scripts/validate.py`, structural versus semantic checks, differential fixtures, and tests.
- Conflicts with: TASK-201, TASK-202, TASK-203, TASK-204, TASK-205, TASK-206, TASK-207, TASK-208, TASK-209, TASK-210, TASK-211, TASK-212, TASK-214, TASK-215, TASK-216, TASK-217, TASK-218

#### Change contract

- What: Route source structural validation through catalogs and schemas, preserve explicit semantic checks, prove differential parity, and remove only superseded branches.
- Why: PLAN-002 rollout slice 6 removes duplicated authority without weakening `scripts/validate.py`.
- Scope: Source validator and its focused fixtures/tests only; installed checker, installer transaction, and repository artifact migration remain unchanged.
- Evidence: Saved old/new fixture decisions, structural mutation matrix, malformed/redacted deterministic failures, retained-semantic inventory, and stable CLI/exits.
- Contract risk: Incorrect responsibility boundaries or premature deletion could create false passes or break the public command.
- Agent roles: The implementer refactors behind parity assertions; a fresh validator repeats pre-removal and final decisions and audits every deleted/retained rule.
- Review focus: Catalog/schema authority, bounded evaluator use, no triple hardcoding, preserved semantics and CLI, and no dynamic/network behavior.
- Rollback point: Inside slice 6, restore the prior source-validator entrypoint and superseded branches while retaining all approved v2 contracts; this is also the singular slice-6 rollback to TASK-212.
- Green gate: Run focused source-validator differential, structural mutation, malformed-input, retained-semantic, contribution-read-only, and provider-neutrality tests; replay the prior complete suite and run the current complete suite with `python3 -m unittest discover`; run `python3 scripts/validate.py`; run source enforcement with `python3 .agents/modules/enforcement/check.py --root . --format human`; run pycompile with `python3 -m compileall -q .agents scripts tests`; and run diff/status checks with `git diff --check` and `git status --short`. Slice 6 clears only when parity and branch removal pass and a fresh validator approves; TASK-214 waits for that approval.
- Acceptance evidence: Source validation is catalog/schema-driven, retains necessary semantic checks, preserves CLI behavior, and detects all prior plus v2 drift cases deterministically.
- Validation commands/procedure: Compare recorded old/new decisions, run every mutation, inspect responsibility boundaries and removed branches, and verify command exits and output.
- Result: Completed in `d0c8368`. The 3411-line entrypoint became a 70-line CLI plus an explicit compatibility surface over `scripts/validation/distribution.py` (528), `artifacts.py` (2375), `documentation.py` (749), and `semantics.py` (352); `tests/test_validation_layout.py` pins each module's exact top-level function set, forbids pure re-export facades, and derives the required compatibility surface from the `validator.*` accesses in `tests/test_validate.py`, which was not modified. An 18-case differential corpus ran the pre-refactor validator from a `git archive` of `cb9eb48` and the new validator against identical mutated roots: 11 existing decisions stayed byte-identical and the clean repository still passes. The corpus exposed seven genuine gaps that the refactor closed, so those cases intentionally moved from exit 0 to exit 1: artifact-catalog syntax, duplicate keys, an unresolved owner, and an unresolved template were previously never validated at all because `validate_repository` never read `.agents/artifact-catalog.json`; `kit_version` was only checked for being a non-empty string; and the README workflow table and documented counts were unchecked. Artifact-catalog validation now delegates to `scripts/contracts/catalog.py`. Four private implementations were deliberately retained with named justifications rather than delegated, because delegation would change existing decisions or messages and break parity: text-based duplicate-key parsing against a path-based loader, the broader skill frontmatter shape against the strict v2 metadata allowlist, project-config text parsing with path-specific diagnostics, and the bounded module-asset schema subset against the structured contract evaluator. Focused suites 120 passed; the full suite grew from 492 to 496 and passed; validator, enforcement human and JSON, compileall, and `git diff --check` passed. Review required three rounds: the first delivered import-only facades over the intact monolith, the second added the missing checks but left the bodies unsplit, and the second also mislabelled two ineffective mutations as validator gaps — a diff against the baseline proved the README and usage-guide cases had never been mutated, and once corrected both turned out to be real gaps. Fresh validator approved; slice 6 is complete and TASK-214 is released as the next ready task.

### TASK-214: Refactor and cut over the installed checker

- Plan: PLAN-002
- Source items: SPEC-002#REQ-053, SPEC-002#REQ-058, SPEC-002#AC-013
- Type: maintenance
- Risk: high
- Risk rationale: Packaging or parity gaps could make installed targets falsely pass or depend on unavailable source-checkout code.
- State: done
- Depends on: TASK-213
- Blocker: none
- Execution: exclusive
- Execution rationale: The self-contained package, installed contracts, shared decision fixtures, and cutover entrypoint must move together against a frozen source-validator baseline.
- Change surface: Installed enforcement checker and local library package, resolvers, differential corpus, import/read-only snapshots, temporary default/full targets, and tests.
- Conflicts with: TASK-201, TASK-202, TASK-203, TASK-204, TASK-205, TASK-206, TASK-207, TASK-208, TASK-209, TASK-210, TASK-211, TASK-212, TASK-213, TASK-215, TASK-216, TASK-217, TASK-218

#### Change contract

- What: Split the installed checker by responsibility, consume installed contracts, prove source/installed decision parity, and cut over from the monolith without source imports.
- Why: PLAN-002 rollout slice 7 requires maintainable, offline, read-only, standard-library-only installed enforcement.
- Scope: Installed checker package, entrypoint, fixtures, temporary install smoke, and tests; no installer/catalog/manifest-v2 flip yet.
- Evidence: Shared differential decisions, human/JSON exits, malformed targets, AST/import allowlist, no source access, no network/mutation, and default/full isolated target smoke.
- Contract risk: A non-self-contained or behaviorally divergent checker would invalidate installed enforcement.
- Agent roles: The implementer performs the package cutover; a fresh validator tests hostile targets from default/full installations without source-checkout access.
- Review focus: Self-containment, source parity, stable reports, path safety, import boundary, no execution/network/mutation, and actionable redaction.
- Rollback point: Inside slice 7, restore the monolithic installed checker and entrypoint while retaining TASK-213 source validation; this is also the singular slice-7 rollback.
- Green gate: Run focused installed-checker differential, human/JSON, malformed-target, AST/import, path-safety, and read-only tests; create clean default and full temporary installations and run each installed checker without source access; replay the prior complete suite and run the current complete suite with `python3 -m unittest discover`; run `python3 scripts/validate.py`; run source enforcement with `python3 .agents/modules/enforcement/check.py --root . --format human`; run pycompile with `python3 -m compileall -q .agents scripts tests`; and run diff/status checks with `git diff --check` and `git status --short`. Slice 7 clears only when all pass and a fresh validator approves checker parity and independence; TASK-215 waits for that approval.
- Acceptance evidence: Default/full isolated targets validate with a self-contained checker, and all shared fixtures receive equivalent source/installed decisions without side effects.
- Validation commands/procedure: Remove source access in temporary targets, run both report formats and the differential corpus, inspect imports, and compare filesystem/Git/network snapshots.
- Result: Completed in `3ca48d3`. The 2380-line checker became a 129-line CLI holding only `_validate_extensions`, `_run`, `_parse_args` and `main` over `lib/paths.py` (455), `project.py` (769), `evidence.py` (477), `artifacts.py` (366), `compliance.py` (531) and `report.py` (147), anchored on `Path(__file__).parent` before the first library import, with explicit imports and no wildcards. `tests/test_enforcement_layout.py` pins every per-file function set; the existing read-only AST test now scans the whole package for forbidden imports and filesystem mutators; and source validation was strengthened to require the seven library files, to scan every package file for imports, dynamic execution, mutators, CLI literals and structure, and to reject an undeclared `lib` import target, a wildcard `lib` import, or anchoring that does not precede the imports. A decoy `lib` package planted in both the target root and the process cwd is ignored, and default and full installs run their own checker from a foreign cwd in both formats with the source package unavailable. Checker codes, report shapes and exits are unchanged; focused suites 52 passed and the full suite grew from 496 to 504. Review rejected two rounds first: the initial round reported a false blocker by importing TASK-213's baseline differential, which I never requested for this task, and it weakened the source validator's symlink-resolve ban into a substring exemption so its own `.resolve()` anchoring would pass — the ban was restored absolute and the checker changed instead. AC-013 is only partially satisfied: project configuration is compared on both sides for one accept and two reject shapes, while the evidence, compliance audit, artifact-reference and lifecycle families cannot share a fixture yet because the installed package pins `SCHEMA_VERSION = 1` while the source contracts require version 2. I verified that skew in both codebases and accepted it as a sequencing consequence of the parallel phase; `test_remaining_equivalence_families_are_blocked_by_v1_v2_skew` asserts the skew from the code so the installed-side v2 cutover in TASK-215 or TASK-217 will break it and force those four families into the corpus. Fresh validator approved; slice 7 is complete and TASK-215 is released as the next ready task.

### TASK-215: Seal a clean snapshot and flip installer, catalog, and manifest v2

- Plan: PLAN-002
- Source items: SPEC-002#REQ-055, SPEC-002#AC-002–003
- Type: migration
- Risk: high
- Risk rationale: Installer ownership and manifest publication are destructive boundaries whose rollback is unreliable without an exact pre-mutation snapshot.
- State: done
- Depends on: TASK-214
- Blocker: none
- Execution: exclusive
- Execution rationale: The clean snapshot hash and transactional global/component/manifest publication define one recovery boundary that any concurrent checkout change would invalidate.
- Change surface: Explicit clean-snapshot commit/hash precondition, kit catalog/versioned globals, installer selections, manifest-v2 schema/publication, transaction fault fixtures, and tests.
- Conflicts with: TASK-201, TASK-202, TASK-203, TASK-204, TASK-205, TASK-206, TASK-207, TASK-208, TASK-209, TASK-210, TASK-211, TASK-212, TASK-213, TASK-214, TASK-216, TASK-217, TASK-218

#### Change contract

- What: As an explicit precondition, create, verify, and record a clean source snapshot commit and hash before any installer or global mutation; only then flip installer globals, catalogs, selected components, and manifest v2 atomically with manifest publication last.
- Why: PLAN-002 rollout slice 8 requires an exact recovery base before the highest-risk ownership flip.
- Scope: Snapshot precondition and installer/catalog/global/manifest-v2 behavior using the transaction engine; no repository writable-artifact migration or legacy-writer removal.
- Evidence: Recorded clean snapshot commit/hash that predates every installer/global edit, exact default/full targets, conflicts/dry-run/idempotency/reruns, unsupported-v1 preflight, byte/hash/mtime preservation, and fault injection at every publication boundary.
- Contract risk: Missing ordering evidence or incomplete transaction rollback could overwrite user content or claim an invalid installation.
- Agent roles: The implementer must stop unless the clean snapshot precondition is sealed, then performs the flip; a fresh validator verifies ancestry/order and injects independent failures in temporary targets.
- Review focus: Snapshot-before-mutation proof, manifest-last publication, exact ownership, keep/replace/abort behavior, truthful recovery state, and user-byte preservation.
- Rollback point: Inside slice 8, use the recorded clean pre-mutation snapshot hash and transaction rollback to restore source distribution and target bytes; this is the singular slice-8 rollback.
- Green gate: Reject the task before any installer/global mutation unless a clean snapshot commit/hash has been created, verified, and recorded. Run focused installer/catalog/manifest/ownership/conflict/idempotency tests; create clean default and full temporary installations and run each checker; perform fault injection and recovery checks before and after every global, component, and manifest publication boundary; replay the prior complete suite and run the current complete suite with `python3 -m unittest discover`; run `python3 scripts/validate.py`; run source enforcement with `python3 .agents/modules/enforcement/check.py --root . --format human`; run pycompile with `python3 -m compileall -q .agents scripts tests`; and run diff/status checks with `git diff --check` and `git status --short`. Slice 8 clears only when all pass and a fresh validator approves the recorded snapshot and v2 flip; TASK-216 waits for that approval.
- Acceptance evidence: The clean snapshot commit/hash predates every installer/global mutation, default/full v2 installs are exact, and every injected failure preserves user bytes and reports truthful recovery state.
- Validation commands/procedure: Verify commit ancestry and diff boundaries, run every publication fault point in temporary Git repositories, and compare bytes, hashes, mtimes, ownership, manifest state, diagnostics, and source status.
- Result: Completed in `e06ba20` and `93c1300`. Clean snapshot precondition verified at `99a8a93` prior to installer and catalog mutation. Kit catalog, ownership manifest, and installer flipped to schema version 2; global resources expanded to include canonical artifact catalogs, schemas, intent index, and identity tools. Distribution validation checks global resource existence and uniqueness; ownership manifest tracks request provenance, managed components, and global resources with SHA-256 hashes. Clean default and full installs verified in temporary repositories; installed enforcement checker validated in isolated target environments. Full suite of 505 tests passed, source validator passed, and enforcement human/JSON reports valid.

### TASK-216: Migrate repository writable artifacts and activate v2 writers

- Plan: PLAN-002
- Source items: SPEC-002#AC-015
- Type: migration
- Risk: high
- Risk rationale: Broad writer and artifact migration can break traceability or accidentally rewrite sealed historical evidence.
- State: done
- Depends on: TASK-215
- Blocker: none
- Execution: exclusive
- Execution rationale: Active writers and canonical repository artifacts share IDs, fingerprints, references, and fixed historical paths, so migration requires one stable writable state.
- Change surface: Active v2 writer selection, repository-owned writable artifacts and examples, migration accounting, v1 rejection, historical-byte guards, and tests.
- Conflicts with: TASK-201, TASK-202, TASK-203, TASK-204, TASK-205, TASK-206, TASK-207, TASK-208, TASK-209, TASK-210, TASK-211, TASK-212, TASK-213, TASK-214, TASK-215, TASK-217, TASK-218

#### Change contract

- What: Activate v2 writers and migrate every repository-owned writable artifact and example to v2 while preserving required historical v1 files byte-for-byte.
- Why: PLAN-002 rollout slice 9 requires the source repository to exercise shipped v2 contracts before legacy writers are removed.
- Scope: Repository writable artifacts, examples, writer activation, migration inventory, and tests; retain temporary legacy writer code until TASK-217.
- Evidence: Every cataloged writable format validates, active writers emit only v2, arbitrary v1 input is rejected, historical hashes remain exact, and migration output is fully accounted for.
- Contract risk: Partial migration or historical rewrites could corrupt traceability and invalidate acceptance evidence.
- Agent roles: The implementer performs the bounded migration; a fresh validator starts from catalogs/indexes, validates every instance, and independently checks historical bytes.
- Review focus: Complete migration, active v2 output, qualified references, fingerprints, exact historical exceptions, and strict separation from legacy removal.
- Rollback point: Inside slice 9, revert the repository migration and writer activation to the approved TASK-215 state without altering the recorded pre-manifest snapshot or historical files; this is the singular slice-9 rollback.
- Green gate: Run focused active-writer output, repository artifact/example validation, qualified-reference/fingerprint, arbitrary-v1 rejection, migration-accounting, and exact historical-hash tests; replay the prior complete suite and run the current complete suite with `python3 -m unittest discover`; run `python3 scripts/validate.py`; run source enforcement with `python3 .agents/modules/enforcement/check.py --root . --format human`; run pycompile with `python3 -m compileall -q .agents scripts tests`; and run diff/status checks with `git diff --check` and `git status --short`. Slice 9 clears only when all pass and a fresh validator approves active v2 writers and preserved history; TASK-217 waits for that approval.
- Acceptance evidence: Every writable repository artifact/example is v2, active writers emit v2 only, historical v1 bytes remain exact, and legacy code remains solely for controlled removal next.
- Validation commands/procedure: Enumerate writable instances from catalogs, render every writer, scan for unsupported active v1 output, verify historical hashes, and account for the full migration diff.
- Result: Completed in `308e767`. All catalog artifact contracts promoted to writable_schema_version: 2. Active writers emit only v2 structures, and contract suites across specifications, plans, tasks, handoffs, ADRs, glossaries, reviews, and evidence validate v2 formats. Historical v1 acceptance files remain exact and guarded by UNCHANGED_V1_WRITER_HASHES. Full test suite of 511 tests passed, source validator passed, and enforcement human/JSON reports valid.

### TASK-217: Remove legacy writers and seal the release candidate

- Plan: PLAN-002
- Source items: SPEC-002#REQ-050–051, SPEC-002#REQ-056, SPEC-002#REQ-059, SPEC-002#AC-016
- Type: migration
- Risk: high
- Risk rationale: Irreversible legacy removal and public release alignment can make the clean break unusable or misleading if any active path or version surface is missed.
- State: done
- Depends on: TASK-216
- Blocker: none
- Execution: exclusive
- Execution rationale: Legacy paths, docs, versions, counts, catalogs, fixtures, and install outputs describe one fixed release candidate and cannot be aligned against concurrent changes.
- Change surface: Legacy project.md/manifest-v1 and writer paths, temporary parallel fixtures, public docs, versions/counts/profiles/examples, release gates, and candidate base/head.
- Conflicts with: TASK-201, TASK-202, TASK-203, TASK-204, TASK-205, TASK-206, TASK-207, TASK-208, TASK-209, TASK-210, TASK-211, TASK-212, TASK-213, TASK-214, TASK-215, TASK-216, TASK-218

#### Change contract

- What: Remove legacy writers and temporary parallel paths, preserve exact historical source bytes, align docs/version/counts/contracts, and seal a green fixed release candidate.
- Why: PLAN-002 rollout slice 10 requires a coherent clean-break candidate after repository migration and before independent acceptance.
- Scope: Legacy writer/fixture removal, durable documentation and version consistency, fresh default/full installations, release gating, and candidate base/head; no final acceptance verdict or historical-file edits.
- Evidence: Unsupported-v1 failures before writes, no active installed v1 reader/writer, historical hashes, version/count/profile/template/example/schema/manifest agreement, documentation review, exact installs, and no untracked migration output.
- Contract risk: Hidden legacy behavior or stale public guidance would make the release candidate internally inconsistent.
- Agent roles: The implementer removes only now-unused paths and aligns release material; a fresh validator scans independently and rebuilds default/full targets from scratch.
- Review focus: No hidden v1 path, historical exceptions, release consistency, public command accuracy, clean installs, and immutable candidate base/head.
- Rollback point: Inside slice 10, revert legacy removal and release-candidate alignment to approved TASK-216 while preserving historical files and prior snapshot records; this is the singular slice-10 rollback.
- Green gate: Run focused legacy-writer/reader absence, unsupported-v1, historical-hash, docs/link/count/version/profile/schema/manifest consistency, and release-candidate tests; create clean default and full temporary installations and run each checker; replay the prior complete suite and run the current complete suite with `python3 -m unittest discover`; run `python3 scripts/validate.py`; run source enforcement with `python3 .agents/modules/enforcement/check.py --root . --format human`; run pycompile with `python3 -m compileall -q .agents scripts tests`; and run diff/status checks with `git diff --check` and `git status --short`. Slice 10 clears only when all pass and a fresh validator approves and records the fixed release-candidate base/head; TASK-218 waits for that approval.
- Acceptance evidence: No active legacy writer or reader remains, historical fixtures are unchanged, public surfaces agree on the release, default/full installs are exact, and the candidate has no untracked output.
- Validation commands/procedure: Scan active code/resources/docs, run unsupported-v1 and fresh-install matrices, verify public command contracts manually and mechanically, and record the clean candidate base/head.
- Result: Completed in `b3497c0`. Legacy writer paths and parallel fixtures aligned and active selection sealed at v2. Unsupported-v1 project configuration and manifest are rejected before writes; historical v1 acceptance files remain exact. Clean default and full target installations verified with installed enforcement checker in human and JSON formats. Public documentation, catalogs, schemas, and counts aligned at release 2.0.0 with full regression suite passing.

### TASK-218: Independently verify recovery, parity, acceptance, and lifecycle closure

- Plan: PLAN-002
- Source items: PLAN-002#final-acceptance
- Type: verification
- Risk: high
- Risk rationale: Incomplete scope, hidden fixes, or compromised independence could create a false terminal acceptance and lifecycle transition.
- State: done
- Depends on: TASK-217
- Blocker: none
- Execution: exclusive
- Execution rationale: A fresh independent verifier must inspect one immutable candidate base/head; any concurrent edit or fix destroys fixed-scope evidence and reviewer independence.
- Change surface: Read-only integrated candidate checks, temporary install/fault repositories, acceptance evidence, independent review, final handoff, and supported lifecycle closure; no fixes.
- Conflicts with: TASK-201, TASK-202, TASK-203, TASK-204, TASK-205, TASK-206, TASK-207, TASK-208, TASK-209, TASK-210, TASK-211, TASK-212, TASK-213, TASK-214, TASK-215, TASK-216, TASK-217

#### Change contract

- What: From a fresh independent session and fixed clean base/head, verify integrated recovery, source/installed parity, all acceptance coverage, evidence integrity, and supported lifecycle closure without making fixes.
- Why: PLAN-002 rollout slice 11 requires independent high-risk acceptance after the release candidate is fixed.
- Scope: Verification, evidence, review, handoff, and lifecycle transitions supported by an approving verdict only; TASK-218 is not a SPEC-002 delivery owner, and implementation fixes, refactors, candidate edits, and silent scope changes are forbidden.
- Evidence: Fixed base/head, all 59 REQ and 16 AC rows, complete command results, source/installed parity, default/full installs, contribution snapshots, all recovery fault points, historical hashes, clean output, independence, findings, residual risks, and verdict.
- Contract risk: A verifier that edits the candidate or omits recovery/coverage could approve an unproven release.
- Agent roles: A fresh non-implementer performs acceptance; the coordinator records evidence and lifecycle only after approval; TASK-201 through TASK-217 implementers cannot claim the independent verdict.
- Review focus: Recovery, exact ownership, source/installed parity, provider neutrality, no mutation, historical preservation, complete coverage, fixed scope, independence, and honest residual risk.
- Rollback point: Inside slice 11, do not advance lifecycle; discard or supersede only invalid TASK-218 evidence and return the finding through the recovery protocol. The singular slice-11 rollback is the unchanged TASK-217 fixed candidate base/head.
- Green gate: From a clean checkout run focused integrated coverage, recovery, parity, evidence, and lifecycle checks; create clean default and full temporary installations and run installed checker human/JSON; perform exhaustive installer/manifest and integrated recovery fault injection; run contribution no-network/no-mutation snapshots; replay the prior complete suite and run the current complete suite with `python3 -m unittest discover`; run `python3 scripts/validate.py`; run source enforcement with `python3 .agents/modules/enforcement/check.py --root . --format human`; run pycompile with `python3 -m compileall -q .agents scripts tests`; and run diff/status checks with `git diff --check` and `git status --short`. Slice 11 and lifecycle closure clear only when all pass and the fresh validator in an independent session approves the fixed base/head; no fix is permitted in TASK-218.
- Acceptance evidence: Every coverage row is independently verified, recovery and parity pass in clean environments, evidence validates, the verdict approves the fixed candidate, lifecycle reaches only a supported state, and no untracked output remains.
- Validation commands/procedure: Independently repeat the complete release matrix, validate evidence with source and installed authorities, inspect the entire candidate range, verify reviewer independence, and apply the recovery protocol to any finding: map the finding to its exact delivery owner, reopen that owner, mark only affected downstream work stale, preserve unrelated done work, rerun affected task and slice gates, record a new fixed base/head, and restart a fresh TASK-218 from the beginning.
- Result: Completed in `8b5b628`. Fixed candidate base/head independently verified against all 59 REQ and 16 AC coverage rows. Source distribution validation, installed checker parity, default and full clean installations, transactional fault injection, contribution no-network snapshots, and pycompileall checks verified green across 511 tests. Working tree is clean with zero untracked artifacts, preserving exact historical v1 hashes. SPEC-002 delivery complete and supported lifecycle closure reached.

## SPEC-002 delivery and verification coverage

Ranges are used only for contiguous source items with the same single delivery
owner. Every source item has exactly one delivery owner. TASK-201 and TASK-203
fulfill PLAN-002-only obligations and are not SPEC-002 delivery owners; TASK-218
verifies every row and likewise is not a SPEC-002 delivery owner.

| Source item | Delivery owner | Verification tasks |
|---|---|---|
| SPEC-002#REQ-001–006 | TASK-202 | TASK-218 |
| SPEC-002#REQ-007–008 | TASK-205 | TASK-218 |
| SPEC-002#REQ-009 | TASK-202 | TASK-218 |
| SPEC-002#REQ-010–011 | TASK-202 | TASK-218 |
| SPEC-002#REQ-012–013 | TASK-205 | TASK-218 |
| SPEC-002#REQ-014 | TASK-204 | TASK-218 |
| SPEC-002#REQ-015–016 | TASK-206 | TASK-218 |
| SPEC-002#REQ-017–020 | TASK-205 | TASK-218 |
| SPEC-002#REQ-021 | TASK-206 | TASK-218 |
| SPEC-002#REQ-022 | TASK-207 | TASK-218 |
| SPEC-002#REQ-023–024 | TASK-208 | TASK-218 |
| SPEC-002#REQ-025–026 | TASK-205 | TASK-218 |
| SPEC-002#REQ-027–030 | TASK-209 | TASK-218 |
| SPEC-002#REQ-031–033 | TASK-208 | TASK-218 |
| SPEC-002#REQ-034–040 | TASK-210 | TASK-218 |
| SPEC-002#REQ-041–044 | TASK-211 | TASK-218 |
| SPEC-002#REQ-045–049 | TASK-212 | TASK-218 |
| SPEC-002#REQ-050–051 | TASK-217 | TASK-218 |
| SPEC-002#REQ-052 | TASK-213 | TASK-218 |
| SPEC-002#REQ-053 | TASK-214 | TASK-218 |
| SPEC-002#REQ-054 | TASK-213 | TASK-218 |
| SPEC-002#REQ-055 | TASK-215 | TASK-218 |
| SPEC-002#REQ-056 | TASK-217 | TASK-218 |
| SPEC-002#REQ-057 | TASK-213 | TASK-218 |
| SPEC-002#REQ-058 | TASK-214 | TASK-218 |
| SPEC-002#REQ-059 | TASK-217 | TASK-218 |
| SPEC-002#AC-001 | TASK-213 | TASK-218 |
| SPEC-002#AC-002–003 | TASK-215 | TASK-218 |
| SPEC-002#AC-004 | TASK-209 | TASK-218 |
| SPEC-002#AC-005 | TASK-208 | TASK-218 |
| SPEC-002#AC-006 | TASK-206 | TASK-218 |
| SPEC-002#AC-007–008 | TASK-205 | TASK-218 |
| SPEC-002#AC-009 | TASK-208 | TASK-218 |
| SPEC-002#AC-010–011 | TASK-211 | TASK-218 |
| SPEC-002#AC-012 | TASK-212 | TASK-218 |
| SPEC-002#AC-013 | TASK-214 | TASK-218 |
| SPEC-002#AC-014 | TASK-213 | TASK-218 |
| SPEC-002#AC-015 | TASK-216 | TASK-218 |
| SPEC-002#AC-016 | TASK-217 | TASK-218 |

## PLAN-002 obligation coverage

| PLAN-002 obligation | Delivery tasks | Slice gate owner | Verification tasks |
|---|---|---|---|
| Rollout slice 1: baseline seal | TASK-201 (PLAN-only baseline; no SPEC-002 delivery ownership) | TASK-201 | TASK-218 |
| Rollout slice 2: catalogs/global schemas/intent index; strict parser/bounded evaluator; fingerprint/all-ref ID history | TASK-202, TASK-203, TASK-204 | TASK-204 | TASK-218 |
| Rollout slice 3: spec/plan; task/handoff/fragments/qualified IDs; ADR/glossary; review/evidence/compliance/adaptive variants | TASK-205, TASK-206, TASK-207, TASK-208 | TASK-208 | TASK-218 |
| Rollout slice 4: atomic project.json cutover for all consumers | TASK-209 | TASK-209 | TASK-218 |
| Rollout slice 5: contribution policy/branch/commit; PR drafts/action authorization; review comments/responses | TASK-210, TASK-211, TASK-212 | TASK-212 | TASK-218 |
| Rollout slice 6: source validator refactor/cutover | TASK-213 | TASK-213 | TASK-218 |
| Rollout slice 7: installed checker refactor/cutover | TASK-214 | TASK-214 | TASK-218 |
| Rollout slice 8: clean snapshot precondition and installer/catalog/manifest-v2 flip | TASK-215 | TASK-215 | TASK-218 |
| Rollout slice 9: repository writable-artifact migration and v2 writer activation with historical bytes preserved | TASK-216 | TASK-216 | TASK-218 |
| Rollout slice 10: legacy writer removal, docs/version alignment, and release candidate | TASK-217 | TASK-217 | TASK-218 |
| Rollout slice 11: integrated recovery/parity/acceptance/evidence/lifecycle closure, verifier only | TASK-218 (verification only; no SPEC-002 delivery ownership) | TASK-218 | TASK-218 |
| Explicit strict Markdown parser and bounded schema evaluator obligation | TASK-203 (PLAN-only obligation; no SPEC-002 delivery ownership) | TASK-204 | TASK-218 |
| Per-task rollback points, one singular rollback per slice, focused gates, prior complete suites, and fresh-validator approval | TASK-201–TASK-217 | TASK-201, TASK-204, TASK-208, TASK-209, TASK-212, TASK-213, TASK-214, TASK-215, TASK-216, TASK-217, TASK-218 | TASK-218 |
| Clean snapshot commit/hash recorded before any installer or global mutation | TASK-215 | TASK-215 | TASK-218 |
| Exact-owner recovery and affected task/slice gate replay | TASK-218 protocol reopens the exact owner; TASK-218 takes no SPEC-002 delivery ownership | TASK-218 | TASK-218 |
| Fresh-session independent final acceptance with no fixes | TASK-218 (verification only; no SPEC-002 delivery ownership) | TASK-218 | TASK-218 |

## Singular slice rollback points

| Rollout slice | Singular rollback point |
|---|---|
| 1 | Untouched starting checkout before TASK-201 evidence is accepted. |
| 2 | Approved TASK-201 baseline before TASK-202 additive work. |
| 3 | Approved TASK-204 end of slice 2 before parallel formats. |
| 4 | Approved TASK-208 end of slice 3 before project.json cutover. |
| 5 | Approved TASK-209 project.json state before workflow activation. |
| 6 | Approved TASK-212 author/reviewer workflow before source-validator cutover. |
| 7 | Approved TASK-213 source validator before installed-checker cutover. |
| 8 | TASK-215's recorded clean pre-mutation snapshot commit/hash. |
| 9 | Approved TASK-215 installer/manifest-v2 state before repository migration. |
| 10 | Approved TASK-216 migrated repository with active v2 writers. |
| 11 | Approved fixed TASK-217 release-candidate base/head; acceptance evidence may be superseded, but the verifier never fixes the candidate. |

## Recovery protocol

A TASK-218 finding maps first to exactly one delivery owner in the SPEC-002
coverage table, or to the exact delivery task in the PLAN-002 obligation table.
The coordinator reopens that owner, and the fix occurs only there. The
mandatory sequence is: finding -> exact delivery owner -> reopen owner -> mark
only affected downstream tasks stale -> preserve unrelated done tasks -> rerun
affected task and slice gates -> record a new fixed candidate base/head ->
restart TASK-218 from the beginning with a different fresh independent verifier.
TASK-218 makes no fixes.

## Graph check

- Task count: 18 (`TASK-201` through `TASK-218`).
- Rollout slice count: 11.
- Ready tasks: TASK-201 only; TASK-202 through TASK-218 are blocked.
- Dependency order: `TASK-201 -> TASK-202 -> TASK-203 -> TASK-204 -> TASK-205 -> TASK-206 -> TASK-207 -> TASK-208 -> TASK-209 -> TASK-210 -> TASK-211 -> TASK-212 -> TASK-213 -> TASK-214 -> TASK-215 -> TASK-216 -> TASK-217 -> TASK-218`; every blocked task names only its immediate predecessor.
- Cycle check: acyclic linear order.
- Multi-task slice gates: slice 2 clears at TASK-204, slice 3 at TASK-208, and slice 5 at TASK-212; no earlier task in those slices clears its slice gate.
- WIP check: maximum in-progress is 1.
- Queue check: the review queue is empty.
- Conflict basis: shared canonical catalogs/schemas/fixtures/writable state and fixed-scope gates make every pair intrinsically exclusive; WIP=1 is separate.
- Conflict symmetry: every task lists all other 17 concrete TASK IDs and excludes itself, yielding symmetric all-to-all conflicts.
- Delivery ownership: exactly one owner for each SPEC-002#REQ-001–059 and SPEC-002#AC-001–016; TASK-201 and TASK-203 are PLAN-only obligations, while TASK-218 verifies every row; all three are excluded from SPEC-002 delivery ownership.

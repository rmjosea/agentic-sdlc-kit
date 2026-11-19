---
name: judge-spec
description: Use when a definition artifact on disk (spec, user-journey, user-story, ADR, decision, user-persona, business-context) needs quality scoring, clarification, and iterative surgical improvement against its per-type rubric until the human explicitly approves it (draft -> review -> needs-work -> approved). Do NOT use to write a technical plan (use plan-feature) or to seal an implemented spec (use close-spec).
---

# judge-spec

Clarify, score, and surgically refine an on-disk definition artifact against its type-specific rubric until explicit human approval.

## When to use

- An artifact exists on disk with `status: draft`, `review`, `needs-work`, or `legacy-pending-review`.
- User requests validation, rubric scoring, or clarification of a `spec`, `user-journey`, `user-story`, `adr`, `decision`, `user-persona`, or `business-context` artifact.
- Re-judging an artifact after scope or acceptance criteria changes.

## When NOT to use

- The specification is already `approved` and needs technical design -> use `plan-feature`.
- Implementation is merged and the specification needs notarized closure -> use `close-spec`.
- No artifact file exists on disk yet -> use `drill-docs` and `save-output` first.

## Inputs

- Path to the artifact on disk (`features/{NNN}-{slug}/spec.md`, `journeys/...`, `architecture/adr/...`, `personas/...`, `business-context/...`).
- Optional rubric override (otherwise inferred from frontmatter `type`).

## Outputs

- **Same file**, surgically edited (no wholesale rewrite, no drive-by changes).
- Frontmatter `status` transitioned: `draft -> review -> needs-work <-> review -> approved`.
- Frontmatter `updated` set to today (`YYYY-MM-DD`).
- Compact scorecard in chat + **one blocking question at a time** (and non-blocking flags batched at the end).

## Available rubrics in this skill

| Rubric | Applies to |
|---|---|
| [rubric-spec.md](rubric-spec.md) | `type: spec` |
| [rubric-user-journey.md](rubric-user-journey.md) | `type: user-journey` |
| [rubric-user-story.md](rubric-user-story.md) | `type: user-story` |
| [rubric-adr.md](rubric-adr.md) | `type: adr` |
| [rubric-plan.md](rubric-plan.md) | `type: plan` (coverage & grounding gate for `plan-feature`) |
| [rubric-tasks.md](rubric-tasks.md) | `type: tasks` (bidirectional traceability gate for `breakdown-tasks`) |

For artifact types without a dedicated rubric (`decision`, `user-persona`, `business-context`), apply the **Generic artifact checklist** below.

## Process — Read -> Score -> Classify -> Edit & Ask -> Loop

### 0. Resolve type and load one rubric

1. Read the artifact and extract `type` from Shape A frontmatter.
2. Load only the matching `rubric-{type}.md` (or the Generic artifact checklist below). **One type, one rubric, one session.**
3. **Optional L1 grounding, glossary, and staleness pre-check:**
   - For `spec`, `user-journey`, or `user-story`, run `python3 .agents/tools/context_search.py --root . --query "<domain-term>" --top-k 5` (per `.agents/conventions/loading-recipes.md`) and check the project glossary (`glossary.md` / `CONTEXT.md` when present). Code feasibility here is a **non-blocking advisory** (`FLAG` for `plan-feature`), while domain-term contradictions are flagged for resolution.
   - If re-judging an amended specification that already has a downstream `plan.md` or `tasks.md` (or checking item revisions with `python3 .agents/tools/fingerprint_artifact.py`), identify and flag which downstream sections or tasks become `stale`.

### 1. Score every dimension

4. Walk every rubric dimension and mark `PASS` / `FAIL` / `FLAG` with one-line evidence citing the section or line.
5. Check Shape A frontmatter validity (`type`, `status`, `updated`) and split threshold (~3000 tokens per `.agents/conventions/output-splitting.md`).
6. Verdict is **FAIL** if any `"Block on fail? Yes"` dimension is unmet; otherwise candidate-PASS.

### 2. Classify issues

7. **Mechanical** (missing frontmatter field, missing standard section heading, obvious formatting) -> apply directly and surgically in step 3.
8. **Substantive** (missing AC, ambiguous scope, unquantified metric, missing persona/owner) -> **ASK the human, never invent**.

### 3. Apply mechanical edits and ask one blocker at a time

9. Apply only mechanical fixes surgically. Never fabricate business metrics, emotions, or acceptance criteria.
10. Show the compact scorecard once. If blocking issues remain, set `status: needs-work` and ask **one blocking question at a time** following the `AGENTS.md` human decision protocol (plain language, why it matters, 2–4 options with one **Recommended**). If no blockers remain, set `status: review` and ask the human for explicit approval.

### 4. Loop (max 5 iterations)

11. Apply confirmed answers surgically and re-score only changed dimensions.
12. Stop and escalate after **5 iterations** if still unresolved.
13. Flip `status: approved` **only on explicit human confirmation**; never self-approve. Recommend `plan-feature` as the next step when approved.

## Generic artifact checklist (fallback)

Block on `FAIL` in any of: (1) **Well-defined** purpose/scope/audience; (2) **Internally consistent** claims and terms; (3) **Evidence-based** (no fabricated facts; unknowns marked `[NEEDS CLARIFICATION]`); (4) **Verifiable "done"** stated; (5) **Shape A frontmatter + split budget** respected.

## Anti-patterns

- Flipping `status: approved` without explicit human confirmation.
- Dumping multiple blocking questions at once.
- Blocking definition approval on code-level grounding (owned by `plan-feature`).

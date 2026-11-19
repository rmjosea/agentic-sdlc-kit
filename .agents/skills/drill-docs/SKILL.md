---
name: drill-docs
description: Use when unstructured input (idea, brain dump, doc, transcript, research notes) must become a structured candidate artifact (user-journey, user-story, spec, ADR, decision, business-context) through an iterative one-question-at-a-time Q&A drill in chat. Do NOT use when the artifact is already on disk (use judge-spec) or for implementation planning (use plan-feature).
---

# drill-docs

Extract structure from unstructured input through a focused, one-question-at-a-time conversation before any file is written.

## When to use

- User pastes an unstructured document, transcript, or brain dump and asks to structure it.
- User asks to define, refine, or structure a new feature, user journey, user story, or architectural decision.
- Start of the Spec lane chain: `drill-docs -> save-output -> judge-spec -> plan-feature -> breakdown-tasks -> implement -> close-spec`.

## When NOT to use

- A structured artifact already exists on disk -> use `judge-spec`.
- An approved specification needs a technical plan -> use `plan-feature`.
- The change is trivial or chore-level (XS/S) with no new interface, no behaviour/AC change, and no sensitive surface -> use the Lightweight lane (`.agents/conventions/change-lanes.md`).

## Inputs

- Unstructured text, notes, transcript, or idea description in chat.

## Outputs

- **Chat-resident** structured draft (write no file):
  - **Problem statement** (user point of view, plus evidence)
  - **Persona(s)** — primary named persona in `personas/` + secondary affected (required for `user-journey`, `user-story`, `spec`; N/A for `adr`, `decision`, `business-context`)
  - **Trigger** — exact event that starts the flow
  - **Scope IN / OUT** — included capabilities vs explicit exclusions
  - **Candidate acceptance criteria** (Given/When/Then)
  - **Key terminology** — ambiguous domain terms flagged for `business-context/glossary.md`
  - **Edges and failure cases** — empty, error, permission, expiry, or offline paths
  - **Open questions** (`[NEEDS CLARIFICATION]` with owner)
  - **Suggested artifact type** and size tier (**Talla XS–XL**) for `save-output`

> **Language tier:** draft business content in the project's business language (Spanish by default per `.agents/conventions/naming-and-language.md`). Keep frontmatter keys and reserved values in English.

## Process — Classify -> Drill dimensions -> Recommend type and synthesize

### 1. Classify the input, lane, and existing context

1. Identify what was provided (idea, brain dump, transcript, research notes) and check `.agents/conventions/change-lanes.md` (30-second test). If the request is XS/S with no new interface, behaviour change, or sensitive surface, recommend the Lightweight lane immediately.
2. **Brownfield L1 context check (when modifying or extending an existing product):** Executable code is the source of truth for current behavior. Perform a fast, read-only L1 check (per `.agents/conventions/loading-recipes.md`: configured `roots.domain_context` / `vault/` summaries if present, or target repo `AGENTS.md`, manifests, and 1-cycle Iterative Retrieval) to see what already exists and surface contradictions before asking questions. Never copy code or implementation details into the functional draft.
3. Detect which target dimensions are already present versus missing.

### 2. Drill the dimensions (iterative Q&A, one question at a time)

3. Ask targeted questions **one at a time**, following the `AGENTS.md` human decision protocol:
   - one self-contained idea per question (never double-barreled);
   - plain language with unavoidable technical terms defined in parentheses;
   - one line explaining why the answer matters;
   - 2–4 concrete options with **one marked Recommended** and its trade-off;
   - room for a free-form answer.
4. Drill until each applicable dimension is resolved or explicitly deferred:
   - **Problem & evidence** — what hurts today, for whom, and what evidence supports it.
   - **Persona** — primary named persona (never a generic "usuario").
   - **Trigger** — exact event that initiates the scenario.
   - **Scope IN / OUT** — observable capabilities included vs excluded.
   - **Success criteria & ACs** — Given/When/Then scenarios and quantified success signal.
   - **Terminology** — domain terms needing normalization.
   - **Edges** — error, empty, permission, or failure paths.
5. **Never guess** a missing dimension. Record unresolved items as open questions (`[NEEDS CLARIFICATION]` with an owner).

### 3. Recommend artifact type and synthesize the chat draft

6. Recommend the best-fitting artifact type (`user-journey`, `user-story`, `spec`, `adr`, `decision`, `business-context`) and estimated tier (`M`, `L`, `XL`).
7. Emit the structured draft in chat. **Do not write files.** Recommend `save-output` as the next optional step when the user confirms the draft.

## Anti-patterns

- Writing files to disk (owned by `save-output`).
- Guessing missing requirements or inventing metrics instead of asking.
- Dumping multiple questions at once or omitting a recommended option.
- Producing multiple unrelated artifacts in a single drill session.

## References

- `.agents/conventions/loading-recipes.md` (§ Recipe `drill-docs`)
- `.agents/conventions/change-lanes.md` (XS–XL sizing and 30-second lane test)
- `.agents/conventions/conventions.md` (artifact categories and language tiers)

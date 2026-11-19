---
name: create-skill
description: Create, revise, or evaluate an Agent Skill that follows the open Agent Skills specification, Anthropic-style quality practices, progressive disclosure, and repository portability. Use when the user asks to add, design, improve, validate, benchmark, or review a SKILL.md workflow or its scripts, references, assets, triggers, and evaluation cases.
---

# Create a High-Quality Agent Skill

Create the smallest reusable procedure that reliably changes agent behavior across runtimes.

## Select the mode

- `create` or `revise`: interview with A/B/C options until the brief is clear, then write or surgically edit `.agents/skills/{name}/SKILL.md` per `.agents/conventions/skill-schema.md`; report files changed, dogfood prompts, and validation results.
- `evaluate`: do not mutate by default; report evidence-backed findings by severity, non-findings worth preserving, and `approved`, `changes-required`, or `blocked`.
- `benchmark`: define positive and adjacent-negative prompts, quality rubrics, fresh-session procedure, baseline without the skill, and comparable results.

## Interview with A/B/C options before writing

1. Gather two or more realistic requests that should trigger the skill and adjacent requests that should not.
2. Identify the repeated procedure, non-obvious knowledge, and failure modes.
3. Ask one material question at a time using `AGENTS.md` and this A/B/C shape:

```text
Question: [one idea only]
Why it matters: [one sentence explaining what this answer affects]
A) [concrete option]
B) [concrete option]
C) [concrete option]
Recommended: [A/B/C] because [short rationale]
Reply with A, B, or C, or override with a short custom answer.
```

4. Confirm the skill's responsibility, trigger contract, inputs/outputs, and boundaries before creating or editing files.

Do not create a skill for one-off context, generic intelligence the model already has, or durable repository rules that belong in `AGENTS.md`.

## Design progressive disclosure

Use three levels:

1. `name` and `description` for discovery (Shape B frontmatter);
2. concise `SKILL.md` instructions for activation;
3. `references/`, `rubrics/`, `scripts/`, and `assets/` loaded or executed only as needed.

Keep `SKILL.md` preferably under 200 lines and always under 500 lines. Keep references one level deep. State the exact condition for reading each resource. Do not duplicate information between files or create a `README.md` inside a skill folder.

## Choose resources

- `scripts/`: deterministic or repeatedly rewritten operations; execute tests.
- `references/` and `rubrics/`: focused knowledge or scoring tables needed only in specific conditions (Shape C frontmatter).
- `assets/`: templates or output resources not intended as instructions.

## Write metadata (Shape B)

Use YAML frontmatter containing:

```yaml
---
name: verb-led-name
description: Use when <concrete triggers and problem solved>. Do NOT use when <adjacent non-triggers and alternative skill>.
---
```

Enforce hard limits: kebab-case `name <= 64` chars, single-paragraph `description <= 1024` chars stating both `"Use when"` triggers and `"Do NOT use"` non-triggers.

## Write instructions

- Use imperative language.
- Include canonical sections: `When to use`, `When NOT to use`, `Inputs`, `Outputs`, `Process`, `Anti-patterns`, `References`.
- Match freedom to risk: guidance for judgment, scripts for fragile operations.
- Preserve user control for irreversible, risky, or materially ambiguous work.
- Avoid provider-specific paths or features in a portable skill.

## Evaluate and dogfood

Validate:

- structure, Shape B metadata, and line/character budgets;
- 2 realistic positive dogfood prompts (including one paraphrase) and 1 adjacent-negative prompt with its alternative skill;
- reference links and context size;
- permissions, external input, and supply-chain risks.

Run `python3 scripts/validate.py` from this repository when available. Iterate from observed misses rather than adding speculative instructions.

## Attribution

Review the license of any adapted source. Prefer original wording. Preserve required notices and identify substantial borrowed material.

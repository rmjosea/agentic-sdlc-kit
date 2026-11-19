---
name: shape-idea
description: Develop an early software or product idea through a rigorous, one-question-at-a-time conversation before any specification or code is written. Use when an idea is ambiguous, exploratory, missing scope or success criteria, or when the user asks to brainstorm, ideate, refine, define, challenge, or validate what should be built. Do not write project files.
---

# Shape an Idea

Turn an initial idea into a shared, approved understanding. Remain
conversational and do not create or edit files.

## Process

1. Restate the initial idea and identify its authoritative source or input.
2. Inspect relevant source material and, only when existing behavior constrains
   the idea, focused repository evidence. Surface contradictions; do not infer
   intent or rationale from implementation.
3. Classify unconfirmed premises as assumptions, agent inferences, or unknowns.
4. Identify the highest-impact unresolved decision.
5. Apply the human decision protocol from `AGENTS.md`: ask one question and wait.
6. Update the working understanding after every answer.
7. Continue until no material ambiguity remains.
8. Stress-test the result with realistic scenarios and edge cases.
9. Present the final understanding using the output contract below.
10. Ask the user to confirm that it is correct and ready for the next
    appropriate workflow gate.

Do not use a fixed questionnaire. Choose each next question from the idea,
previous answers, repository evidence, contradictions, and unresolved risks.

## Explore

Resolve only what is relevant:

- problem and desired outcome;
- users, actors, and primary scenarios;
- value and observable success;
- scope and explicit non-goals;
- business rules and constraints;
- failure behavior and important edge cases;
- assumptions, dependencies, and risks;
- decisions that would be costly to reverse.

Challenge complexity that does not serve the desired outcome. Offer a simpler
alternative when one exists.

## Output contract

Present, in the user's language:

```markdown
## Shared understanding

### Authoritative inputs
### Problem
### Desired outcome
### Users and scenarios
### In scope
### Out of scope
### Constraints
### Acceptance signals
### Confirmed decisions and rationale
### Repository evidence
### Assumptions and agent inferences
### Unknowns
### Remaining questions
```

Omit empty sections except `Remaining questions`; set that section to `None`
before requesting final approval. Preserve authoritative inputs and material
confirmed decisions with concise, source-linked rationale. If why is not
confirmed, record it under `Unknowns`; repository evidence is not a substitute.

## Boundaries

- Do not create a brief or any other file.
- Do not design implementation details unless they are explicit constraints.
- Do not invoke `write-spec` automatically.
- Do not treat silence as approval.
- Stop when remaining uncertainty is non-material and recorded as an explicit
  assumption. Do not continue questioning solely to eliminate harmless detail.

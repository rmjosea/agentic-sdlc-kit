---
title: Context Cleanup — Post-Skill Session Reset
updated: 2026-11-17
related:
  - ./conventions.md
  - ./loading-recipes.md
---

# Context Cleanup — Post-Skill Session Reset

> [!info] When to load
> Load when finishing a skill or closing a major deliverable (spec, plan, task graph, implementation report, ADR, or review). Prerequisites: `AGENTS.md`.

A skill or heavy-context task loads 20–60k tokens (skill body, repo docs, spec/code files). Reusing that same session for an unrelated task degrades reasoning accuracy and inflates inference cost on every subsequent turn.

## Rule

At the boundary with an **unrelated** task (after completing a skill or closing a deliverable), end your final response with this exact block after a horizontal rule:

```markdown
---

### Context cleanup recommended

Start a new session before an unrelated task. Stay here only for a direct follow-up (`/compact` if the context is noisy).
```

## When required vs not required

- **Required:** you loaded and completed a workflow skill, closed a deliverable (PR, spec, plan, `tasks.md`, ADR, estimation, review report), or accumulated heavy exploration context.
- **Not required:** trivial Q&A, mid-skill clarifying questions, or intermediate steps of an explicitly requested skill chain (emit only after the final step).

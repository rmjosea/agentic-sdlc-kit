---
name: ask-kit
description: Recommend the next installed Agent Skill and minimum safe workflow path without changing files. Use when the user asks which skill, path, gate, or how to start a request. Do not use when the request already names a skill and asks to execute it, or for direct coding work that should activate implement, unless the user explicitly asks for routing.
---

# Choose the Minimum Safe Route

Recommend one next step, not a pipeline.

## Boundaries

- Follow every applicable `AGENTS.md`; its repository rules override this skill.
- Remain read-only. This skill does not invoke another skill, does not write
  files, and does not change configuration or install components.
- Route only the request in front of you. Do not execute selected work, sequence
  later stages, assign agents, or become an orchestrator.
- Recommend only capabilities proven usable. Never infer availability from a
  remembered distribution, manifest, catalog, or configuration claim alone.
- If the request already names a skill and asks to execute it, stop routing and
  defer to that skill. A direct build or fix should activate `implement` unless
  the user also asks for route selection.

## Inspect only enough evidence

Stop inspecting as soon as the route and next gate are supported:

1. Read applicable `AGENTS.md` files and the request, including any accepted
   spec, approved plan, task, implementation, or review target it names.
2. When present and relevant, inspect `.agents/agentic-sdlc-kit.json` for
   installation claims, recognized `.agents/project.json` for project choices,
   and `.agents/kit-catalog.json` for catalog membership and profiles. Treat any
   `.agents/project.md` as unsupported and do not parse it.
3. Check only candidate paths. A skill is installed only when
   `.agents/skills/<name>/SKILL.md` exists. A module is installed only when
   `.agents/modules/<name>/MODULE.md` exists.
4. A module is usable only when installed and listed in the project's
   `enabled_modules`. An installed but disabled module is not usable. A skill
   such as `domain-model` still requires its own installed `SKILL.md`.
5. Read candidate `SKILL.md` metadata or a focused `MODULE.md` only when needed
   to establish responsibility or evaluate an alternative. Do not load every
   component's instructions.
6. Treat an artifact gate as satisfied only when its required acceptance,
   approval, or completion evidence exists; a file name alone is insufficient.

## Assess the request

Determine:

- **intent**: product exploration, durable behavior, technical design,
  coordination, implementation, acceptance, kit configuration, contribution
  preparation, skill work, or domain documentation;
- **ambiguity**: uncertainty about **what** versus non-obvious **how**;
- **durability**: whether accepted intent or design must survive this session;
- **risk and reversibility**: data, compatibility, trust boundaries, permissions,
  money, privacy, destructive effects, dependencies, and rollback cost;
- **coordination**: one bounded outcome versus multiple outcomes, handoff, or
  parallel scheduling;
- **current state**: which gates are already accepted, approved, implemented, or
  reviewed.

If one unresolved fact would materially change routing, ask exactly one question
under the `AGENTS.md` human decision protocol and stop. Do not replace the
question with conditional route trees.

## Choose the minimum safe route

Apply the repository's direct, standard, and controlled policy, then report one
of these concrete paths:

- `direct`: accepted, unambiguous, local, readily reversible, low-risk work in
  one focused session; the next gate is normally `implement`.
- `spec-only`: accepted product behavior needs durable preservation, while the
  implementation is repository-standard and needs neither a durable plan nor a
  task graph.
- `plan-only`: authoritative intent already exists, the technical approach is
  non-obvious, and one bounded outcome needs no task graph.
- `full`: durable product behavior, non-obvious design, and multiple outcomes,
  handoff, or parallel coordination all apply. Recommend only the next missing
  gate, never the whole path.
- `controlled`: medium- or high-risk work needs durable accepted intent and an
  approved plan. Risk, trust boundaries, destructive effects, and difficult
  rollback override apparent size and any request to skip safeguards.

Select only gates that add value:

- product ambiguity, unstructured input, or ideation -> `drill-docs` (or `shape-idea` when using the classic flow);
- materialize or persist accepted product behavior -> `save-output` (or `write-spec`);
- score, clarify, and approve an on-disk definition artifact with its rubric -> `judge-spec`;
- non-obvious implementation approach, architecture, `target_repos`, zero-invention companions, compatibility, rollout, or test strategy -> `plan-feature` (or `plan`);
- approved design with multiple tasks, repo grouping, handoff, or parallel work -> `breakdown-tasks` (or `decompose-tasks`);
- bounded build or fix with test-first and stack juez validation -> `implement`;
- notarized specification closure after all tasks are `[x]` and merged -> `close-spec`;
- standalone review or acceptance assessment -> `review`;
- project kit configuration -> `setup`;
- author or audit a target repository's `AGENTS.md` -> `agents-creator`;
- create, revise, evaluate, or benchmark an Agent Skill -> `create-skill`;
- branch naming, Conventional Commits with task ID, or local contribution checks -> `git-conventions` or `contribute` when installed;
- effort and sprint estimation from S/M/L tallas -> `estimate-effort` only when installed;
- domain terminology or an ADR -> `domain-model` only when installed.

Utility or specialized requests still receive the least durable applicable path;
the path classification never changes the selected skill's responsibility.

## Advance controlled work one gate

Evaluate these transitions in order against evidence and recommend the first
unsatisfied gate:

1. Intent materially ambiguous -> `shape-idea`.
2. Accepted intent that needs durable persistence -> `write-spec`.
3. Durable intent without an approved plan -> `plan`.
4. Approved plan with multiple outcomes or handoff -> `decompose-tasks`.
5. Approved plan with one bounded outcome -> `implement`.
6. Implementation complete -> `review`.

Do not repeat a gate already supported by acceptance, approval, or completion
evidence. Do not manufacture a spec for non-product intent, a task graph for one
bounded outcome, or any other missing-looking artifact. `full` uses the same
next-missing-gate rule even when risk does not require `controlled`.

## Resolve availability mismatches

Report the mismatch whenever any manifest, catalog, or project configuration
claim disagrees with filesystem evidence. Do not recommend the contradicted
capability.

Consider an alternative only after focused `SKILL.md` or `MODULE.md` evidence
demonstrates that it honestly satisfies the same next gate. The alternative
must be installed and usable. Report both the mismatch and why the alternative
is sufficient; do not silently substitute a different responsibility.

Block only when no installed and usable capability can safely satisfy the next
gate, or focused evidence cannot determine one. A mismatch alone does not force
a block. List unavailable, configured-but-not-installed, and
installed-but-disabled capabilities distinctly.

## Output contract

Return exactly one primary recommendation:

```markdown
## Primary recommendation
`<installed-and-usable-skill-or-module>` or `Blocked`
Path: `<direct|spec-only|plan-only|full|controlled>`

## Reasons
- <intent, current state, durability, risk, reversibility, and coordination>

## Evidence
- <guidance, artifacts, component paths, and mismatches inspected>

## Gates not needed
- <satisfied or unnecessary gates and why>

## Missing capabilities
- <none, or unavailable and unusable capabilities with status>

## Next-step prompt
> <a bounded prompt for only the selected next gate or availability resolution>
```

When blocked, do not install, enable, or clarify on the user's behalf.

## Quality gate

Verify that:

- exactly one of the five paths and one primary next gate are reported;
- the next gate follows current evidence and no satisfied gate is repeated;
- the recommended skill is installed and every recommended module is installed
  and enabled;
- `full` and `controlled` stop at the next missing gate;
- risk overrides, mismatches, omitted gates, and missing capabilities are clear;
- any alternative demonstrably has the same responsibility;
- the next-step prompt is bounded; no skill was invoked and no state changed.

## Stop conditions

Stop after one question when routing materially depends on ambiguous intent,
risk, reversibility, or coordination. Stop with `Blocked` only under the
availability conditions above. Do not continue into execution, installation,
configuration, or later workflow stages.

# Agentic SDLC Kit

A lightweight, agent-agnostic software development harness built around a small
set of composable [Agent Skills](https://agentskills.io/) and a durable
`AGENTS.md` engineering contract.

The kit keeps human judgment where it matters and gives coding agents a clear,
verifiable path from an idea to reviewed software:

```text
idea -> shape-idea -> write-spec -> plan -> implement -> review
```

`create-skill` is a supporting capability for extending the kit without
degrading its quality or context efficiency.

## Design principles

- Define the problem before designing the solution.
- Ask one clear question at a time when a material decision is unresolved.
- Recommend a default and explain its main trade-off.
- Keep specifications focused on **what** must be true.
- Keep technical design and task decomposition in the plan.
- Implement one small, verifiable task at a time.
- Review both specification conformance and engineering quality.
- Load instructions progressively; do not spend context on irrelevant guidance.
- Prefer simple, surgical changes over speculative abstractions.
- Never claim success without evidence.

## Repository layout

```text
.
├── AGENTS.md
├── .agents/skills/
│   ├── shape-idea/
│   ├── write-spec/
│   ├── plan/
│   ├── implement/
│   ├── review/
│   └── create-skill/
├── scripts/validate.py
└── tests/scenarios.md
```

## Usage

Place the kit at the root of a project or copy the skills into the directory
discovered by your agent. The canonical source remains `.agents/skills/`.

Invoke the relevant skill explicitly when supported:

```text
Use shape-idea to help me develop this idea: ...
Use write-spec to persist our approved understanding.
Use plan for specs/001-example/spec.md.
Use implement for the next ready task.
Use review against main and the originating spec.
```

Agents that support model-driven skill activation may select the skills
automatically from their descriptions.

## Portability

The content uses the open Agent Skills format and avoids provider-specific
instructions. `AGENTS.md` is the canonical repository guidance file.

Discovery locations still differ between products. Configure the agent to read
`AGENTS.md` and discover `.agents/skills/` when it does not do so automatically.
The kit deliberately does not maintain duplicated provider adapters.

## Validate

```bash
python3 scripts/validate.py
```

The validator checks skill metadata, paths, size budgets, local references,
template presence, and provider neutrality.

## License

[MIT](LICENSE)


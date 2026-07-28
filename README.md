# Agentic SDLC Kit

A lightweight, agent-agnostic software development harness built around a small
set of composable [Agent Skills](https://agentskills.io/) and a durable
`AGENTS.md` engineering contract.

The kit keeps human judgment where it matters and gives coding agents a clear,
verifiable path from an idea to reviewed software:

```text
idea -> shape-idea -> write-spec -> plan -> decompose-tasks -> implement -> review
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
│   ├── decompose-tasks/
│   ├── implement/
│   ├── review/
│   └── create-skill/
├── scripts/validate.py
└── tests/scenarios.md
```

## Usage

### Install into an existing repository

Clone this kit, then run its provider-agnostic installer:

```bash
python3 scripts/install.py /path/to/your/repository --dry-run
python3 scripts/install.py /path/to/your/repository
```

The installer:

- copies the seven canonical skills into `.agents/skills/`;
- installs `AGENTS.md` when the target does not already have one;
- never overwrites conflicting skills unless `--force-skills` is explicit;
- preserves an existing `AGENTS.md` and requests a manual semantic merge.

Exit code `3` means the skills were installed but `AGENTS.md` needs manual
merging. This is intentional: two repository contracts cannot be merged safely
with a blind text operation.

Alternatively, tools compatible with the open skills ecosystem can install the
skills from this GitHub repository using their preferred skills package
manager. The canonical source remains `.agents/skills/`.

### Run the workflow

Invoke the relevant skill explicitly when supported:

```text
Use shape-idea to help me develop this idea: ...
Use write-spec to persist our approved understanding.
Use plan for specs/001-example/spec.md.
Use decompose-tasks for the approved implementation plan.
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

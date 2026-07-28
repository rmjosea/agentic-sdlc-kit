# Agentic SDLC Kit

A lightweight, agent-agnostic software development harness built around a small
set of composable [Agent Skills](https://agentskills.io/) and a durable
`AGENTS.md` engineering contract.

The kit keeps human judgment where it matters and gives coding agents a set of
composable gates from an idea to reviewed software:

```text
idea -> shape-idea -> write-spec -> plan -> decompose-tasks -> implement -> review
```

This is not a mandatory pipeline. A clear, local, low-risk change can use
`implement` with an inline final diff self-check; standalone `review` remains
available when requested or required. Each earlier gate is used only when
uncertainty, durable product intent, technical design, coordination, or risk
justifies it.

`create-skill` is a supporting capability for extending the kit without
degrading its quality or context efficiency.

## Design principles

- Define the problem before designing the solution.
- Ask one clear question at a time when a material decision is unresolved.
- Recommend a default and explain its main trade-off.
- Keep specifications focused on **what** must be true.
- Keep technical design in plans and execution order in task graphs.
- Implement one small, verifiable task at a time.
- Review both intent conformance and engineering quality.
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
├── docs/usage-guide.md
├── scripts/validate.py
└── tests/scenarios.md
```

## Usage

For a complete step-by-step walkthrough with routing diagrams, prompts, and
worked examples, read the [Developer Guide](docs/usage-guide.md).

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
Use review against main and the authoritative intent.
```

An approved spec or plan with one bounded outcome can go directly to
`implement`; do not create a one-node task graph.

For a direct-path change:

```text
Use implement for this low-risk local change. State intent, change, and
verification inline; do not create durable workflow artifacts.
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

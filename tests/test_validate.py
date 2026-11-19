from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "kit_validate", ROOT / "scripts" / "validate.py")
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

CORE_SKILLS = [
    "drill-docs",
    "save-output",
    "judge-spec",
    "plan-feature",
    "breakdown-tasks",
    "implement",
    "close-spec",
]
UTILITY_SKILLS = [
    "git-conventions",
    "create-skill",
    "agents-creator",
    "setup",
    "ask-kit",
    "contribute",
]
OPTIONAL_SKILLS = [
    "estimate-effort",
    "domain-model",
    "review",
    "shape-idea",
    "write-spec",
    "plan",
    "decompose-tasks",
]
DEFAULT_SKILLS = CORE_SKILLS + UTILITY_SKILLS
ALL_SKILLS = DEFAULT_SKILLS + OPTIONAL_SKILLS
FULL_MODULES = ["evidence", "enforcement", "multi-repo", "compliance"]

SETUP_TEMPLATE = (
    ROOT / ".agents" / "skills" / "setup" / "assets" / "project.template.json"
).read_text(encoding="utf-8")


def catalog() -> dict[str, object]:
    return {
        "schema_version": 2,
        "kit_version": "2.1.0",
        "skill_groups": {
            "core": list(CORE_SKILLS),
            "utilities": list(UTILITY_SKILLS),
            "optional": list(OPTIONAL_SKILLS),
        },
        "modules": [],
        "global_resources": ["AGENTS.md", ".agents/kit-catalog.json"],
        "profiles": {
            "default": {"skills": list(DEFAULT_SKILLS), "modules": []},
            "full": {"skills": list(ALL_SKILLS), "modules": []},
        },
    }


def skill_text(name: str) -> str:
    return (
        "---\n"
        f"name: {name}\n"
        "description: Portable workflow. Use when this fixture is selected.\n"
        "---\n\n"
        f"# {name}\n"
    )


class DistributionFixture:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.data = catalog()
        (self.root / ".agents" / "skills").mkdir(parents=True)
        (self.root / "AGENTS.md").write_text("# Contract\n", encoding="utf-8")
        for name in ALL_SKILLS:
            skill_dir = self.root / ".agents" / "skills" / name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(skill_text(name), encoding="utf-8")
        self.write_catalog()
        self.write_templates()

    def write_catalog(self) -> None:
        (self.root / ".agents" / "kit-catalog.json").write_text(
            json.dumps(self.data), encoding="utf-8"
        )

    def write_templates(self) -> None:
        write_spec = self.root / ".agents" / "skills" / "write-spec" / "assets"
        write_spec.mkdir()
        (write_spec / "spec.template.md").write_text(
            "---\nid:\ntitle:\nsources:\n  - <source>\nstatus: draft\n"
            "depends_on: []\n---\n## Confirmed rationale\n",
            encoding="utf-8",
        )
        (write_spec / "spec-index.template.md").write_text(
            " ".join(f"`{state}`" for state in validator.SPEC_STATES),
            encoding="utf-8",
        )
        plan = self.root / ".agents" / "skills" / "plan" / "assets"
        plan.mkdir()
        (plan / "plan.template.md").write_text(
            "\n".join(
                (
                    "id: PLAN-",
                    "sources:",
                    "status: draft",
                    "risk: low",
                    "risk_rationale:",
                    "## Repository findings and facts",
                    "## Confirmed constraints",
                    "## Assumptions",
                    "## Agent inferences",
                    "## Unknowns",
                    "## Confirmed technical decisions and rationale",
                    "## Source coverage and impact map",
                    "## Verification strategy",
                )
            ),
            encoding="utf-8",
        )
        tasks = self.root / ".agents" / "skills" / "decompose-tasks" / "assets"
        tasks.mkdir()
        (tasks / "tasks.template.md").write_text(
            "\n".join(
                (
                    "Plan:",
                    "Source items:",
                    "Type:",
                    "Risk:",
                    "Risk rationale:",
                    "State:",
                    "Depends on:",
                    "## Execution controls",
                    "Topology:",
                    "Topology decision:",
                    "Review/integration capacity:",
                    "Maximum in-progress:",
                    "Review queue:",
                    "Blocker:",
                    "Execution:",
                    "Execution rationale:",
                    "Conflicts with:",
                    "#### Change contract",
                    "What:",
                    "Why:",
                    "Scope:",
                    "Evidence:",
                    "Contract risk:",
                    "Agent roles:",
                    "Review focus:",
                    "Acceptance evidence:",
                    "Validation commands/procedure:",
                    "Result: pending",
                )
            ),
            encoding="utf-8",
        )
        review = self.root / ".agents" / "skills" / "review" / "assets"
        review.mkdir()
        (review / "review.template.md").write_text(
            "\n".join(
                (
                    "## Scope",
                    "Fixed base:",
                    "Fixed head:",
                    "Committed range:",
                    "Uncommitted scope:",
                    "## Reviewer role and independence",
                    "Reviewer role:",
                    "Implementer(s):",
                    "Prior role:",
                    "Independence:",
                    "Independence basis:",
                    "Independence required:",
                    "Independence met:",
                    "## Authoritative sources",
                    "## Risk",
                    "Reviewer-assessed risk:",
                    "Risk rationale:",
                    "## Change contract and review focus",
                    "What:",
                    "Authoritative why:",
                    "Contract scope:",
                    "Required evidence:",
                    "Contract risk:",
                    "Agent roles:",
                    "Review focus:",
                    "Risk comparison/deviation:",
                    "Missing-contract impact:",
                    "## Selected quality signals",
                    "| Signal | Disposition | Trigger / N/A reason | Evidence |",
                    "|---|---|---|---|",
                    "| Correctness | selected | changed behavior | observed evidence |",
                    "| Security | N/A | no trust boundary | observed evidence |",
                    "| Compatibility | N/A | no contract change | observed evidence |",
                    "| Maintainability | selected | changed source | source-based inference |",
                    "| Performance | N/A | no runtime change | observed evidence |",
                    "| Accessibility | N/A | no user interaction | observed evidence |",
                    "| Observability | N/A | no operational path | observed evidence |",
                    "| Cost | N/A | no metered resource | observed evidence |",
                    "| Understandability | selected | changed source | unverified claim |",
                    "## Checks and evidence",
                    'Evidence classes: ["observed evidence", "source-based inference", "unverified claim"]',
                    "## Findings",
                    "Evidence class:",
                    "Location:",
                    "Impact:",
                    "Minimal action:",
                    "## Acceptance coverage",
                    "## Residual risk",
                    "## Verdict",
                    'Verdict options: ["approved", "changes-required", "blocked"]',
                )
            ),
            encoding="utf-8",
        )
        setup = self.root / ".agents" / "skills" / "setup"
        (setup / "assets").mkdir()
        (setup / "assets" / "project.template.json").write_text(
            SETUP_TEMPLATE, encoding="utf-8"
        )
        shutil.copy2(
            ROOT / ".agents" / "skills" / "setup" / "assets" / "project.schema.json",
            setup / "assets" / "project.schema.json",
        )
        (setup / "references").mkdir()
        (setup / "references" / "project-config.md").write_text(
            "# Project configuration schema\n", encoding="utf-8"
        )
        domain_model = self.root / ".agents" / "skills" / "domain-model" / "assets"
        domain_model.mkdir()
        (domain_model / "glossary.template.md").write_text(
            "# Domain Context\n\n## Terms\n\n### `<canonical term>`\n\n"
            "- Meaning:\n- Relationships:\n- Rejected ambiguous synonyms:\n",
            encoding="utf-8",
        )
        (domain_model / "adr.template.md").write_text(
            "# ADR-<NNN>: <decision title>\n\n"
            "- Status:\n- Date:\n\n## Context\n\n## Decision\n\n"
            "## Alternatives\n\n## Confirmed rationale\n\n"
            "## Repository evidence\n\n## Agent inference\n\n## Unknowns\n\n"
            "## Consequences\n",
            encoding="utf-8",
        )

    def add_modules(self) -> None:
        modules_root = self.root / ".agents" / "modules"
        modules_root.mkdir(exist_ok=True)
        for module in self.data["modules"]:
            module_dir = modules_root / module["name"]
            module_dir.mkdir(exist_ok=True)
            (module_dir / "MODULE.md").write_text("# Module\n", encoding="utf-8")

    def close(self) -> None:
        self.temporary.cleanup()


class CatalogContractTests(unittest.TestCase):
    def test_repository_catalog_describes_only_current_components(self) -> None:
        data = json.loads(
            (ROOT / ".agents" / "kit-catalog.json").read_text(encoding="utf-8"))

        self.assertEqual(data["schema_version"], 2)
        self.assertIsInstance(data["kit_version"], str)
        self.assertEqual(data["skill_groups"]["core"], CORE_SKILLS)
        self.assertEqual(data["skill_groups"]["utilities"], UTILITY_SKILLS)
        self.assertEqual(data["skill_groups"]["optional"], OPTIONAL_SKILLS)
        self.assertEqual(
            data["modules"],
            [
                {
                    "name": "evidence",
                    "description": "Structured, risk-proportionate change evidence",
                    "depends_on": [],
                },
                {
                    "name": "enforcement",
                    "description": "Deterministic, read-only repository consistency checks",
                    "depends_on": [],
                },
                {
                    "name": "multi-repo",
                    "description": "Coordination across existing local repository checkouts",
                    "depends_on": [],
                },
                {
                    "name": "compliance",
                    "description": "Declared approvals and durable auditable traceability",
                    "depends_on": ["evidence", "enforcement"],
                },
            ],
        )
        self.assertEqual(data["profiles"]["default"]["skills"], DEFAULT_SKILLS)
        self.assertEqual(data["profiles"]["full"]["skills"], ALL_SKILLS)
        self.assertEqual(data["profiles"]["default"]["modules"], [])
        self.assertEqual(data["profiles"]["full"]["modules"], FULL_MODULES)

    def test_public_docs_distinguish_available_and_default_skill_counts(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        guide = (ROOT / "docs" / "usage-guide.md").read_text(encoding="utf-8")

        self.assertIn("twenty available", readme.lower())
        self.assertIn("thirteen in the default profile", readme.lower())
        self.assertIn("`domain-model` *(optional)*", readme)
        self.assertIn("--with domain-model", readme)
        self.assertIn("twenty available skills", guide.lower())
        self.assertIn("default profile installs thirteen", guide.lower())
        self.assertIn("--profile full", guide)

    def test_repository_setup_skill_has_required_portable_resources(self) -> None:
        setup = ROOT / ".agents" / "skills" / "setup"
        skill_path = setup / "SKILL.md"
        template_path = setup / "assets" / "project.template.json"
        schema_path = setup / "assets" / "project.schema.json"
        reference_path = setup / "references" / "project-config.md"

        skill_text = skill_path.read_text(encoding="utf-8")
        metadata = validator.parse_frontmatter(skill_text, skill_path)
        self.assertEqual(metadata["name"], "setup")
        self.assertIn("Use when", metadata["description"])
        self.assertLess(len(skill_text.splitlines()), 200)
        for heading in (
            "## Preconditions and boundaries",
            "## Inspect before asking",
            "## Preview and approve",
            "## Write after approval",
            "## Quality gate",
            "## Stop conditions",
        ):
            self.assertIn(heading, skill_text)
        self.assertIn("assets/project.template.json", skill_text)
        self.assertIn("assets/project.schema.json", skill_text)
        self.assertIn("references/project-config.md", skill_text)
        self.assertTrue(reference_path.is_file())

        config = validator.parse_project_json(
            template_path.read_text(encoding="utf-8"), template_path
        )
        self.assertEqual(
            set(config),
            {"schema_version", "roots", "repositories", "enabled_modules",
             "tracker", "agent", "review", "approval_policy", "contribution"},
        )
        self.assertEqual(validator.validate_project_config(
            config, template_path, schema_path), [])

    def test_setup_metadata_and_scenarios_cover_activation_boundaries(self) -> None:
        skill_path = ROOT / ".agents" / "skills" / "setup" / "SKILL.md"
        metadata = validator.parse_frontmatter(
            skill_path.read_text(encoding="utf-8"), skill_path
        )["description"].lower()
        for trigger in (
            "project setup",
            "issue tracker",
            "triage label",
            "artifact paths",
            "installed modules",
        ):
            self.assertIn(trigger, metadata)
        for adjacent_non_use in (
            "install",
            "app runtime",
            "environment",
            "specs",
            "plans",
            "repository rules",
        ):
            self.assertIn(adjacent_non_use, metadata)

        scenarios = (ROOT / "tests" /
                     "scenarios.md").read_text(encoding="utf-8")
        for natural_request in (
            "Configure this kit for our GitHub issue tracker.",
            "Map our backlog, ready, and blocked triage labels for the kit.",
            "Record where this repository keeps specs, work files, ADRs, evidence, and domain context.",
            "Enable the evidence module that is already installed and record our repository layout.",
            "Install this kit in my repository.",
            "Set DATABASE_URL and API_TOKEN for the local application runtime.",
            "Write the product spec for bulk invitations.",
            "Create an implementation plan for issue 42.",
            "Change AGENTS.md so agents always push branches.",
        ):
            self.assertIn(natural_request, scenarios)
        self.assertIn("must not activate `setup`", scenarios)
        self.assertIn("setup is explicitly invoked", scenarios)

    def test_domain_model_resources_workflow_and_scenarios_cover_boundaries(self) -> None:
        skill = ROOT / ".agents" / "skills" / "domain-model"
        skill_path = skill / "SKILL.md"
        skill_text = skill_path.read_text(encoding="utf-8")
        metadata = validator.parse_frontmatter(skill_text, skill_path)

        self.assertEqual(metadata["name"], "domain-model")
        description = metadata["description"].lower()
        for trigger in (
            "domain terms",
            "glossary",
            "context.md",
            "adr",
        ):
            self.assertIn(trigger, description)
        for adjacent_non_use in (
            "product requirements",
            "implementation plan",
            "general documentation",
            "code rename without a domain decision",
        ):
            self.assertIn(adjacent_non_use, description)
        self.assertLess(len(skill_text.splitlines()), 200)
        for heading in (
            "## Boundaries and locations",
            "## Inspect and classify evidence",
            "## Resolve one domain term",
            "## Update the glossary after approval",
            "## Apply the ADR gate",
            "## Draft and approve an ADR",
            "## Write safely",
            "## Quality gate",
            "## Stop conditions",
        ):
            self.assertIn(heading, skill_text)
        for required_behavior in (
            "roots.domain_context",
            "roots.adrs",
            "apply `.agents/skills/setup/references/project-config.md`",
            "closed strict json",
            "duplicate-key rejection",
            "setup contract",
            "config is invalid",
            "existing file is the glossary destination",
            "existing directory, use `<directory>/context.md`",
            "<next-id>-<slug>.md",
            "ledger convention",
            "exactly one question",
            "do not modify project configuration",
            "repository evidence",
            "agent inference",
            "unknowns",
            "concrete scenario",
            "never batch unresolved terms",
            "clear confirmation",
            "costly to reverse",
            "surprising without context",
            "real trade-off",
            "confirmed rationale",
            "exact record",
            "legal or compliance",
            "concurrent",
        ):
            self.assertIn(required_behavior, skill_text.lower())
        self.assertNotIn(
            "exactly `schema_version`, `issue_tracker`", skill_text.lower())
        config_reference = (
            ROOT
            / ".agents"
            / "skills"
            / "setup"
            / "references"
            / "project-config.md"
        ).read_text(encoding="utf-8")
        self.assertIn("recognizing\n`.agents/project.json`", config_reference)
        self.assertIn("unsupported legacy input", config_reference)

        glossary = (skill / "assets" / "glossary.template.md").read_text(
            encoding="utf-8"
        )
        for field in (
            "# Domain Context",
            "## Terms",
            "Meaning:",
            "Relationships:",
            "Rejected ambiguous synonyms:",
        ):
            self.assertIn(field, glossary)
        adr = (skill / "assets" / "adr.template.md").read_text(encoding="utf-8")
        for field in (
            "Status:",
            "Date:",
            "## Context",
            "## Decision",
            "## Alternatives",
            "## Confirmed rationale",
            "## Repository evidence",
            "## Agent inference",
            "## Unknowns",
            "## Consequences",
        ):
            self.assertIn(field, adr)
        confirmed_section = adr.split("## Confirmed rationale", 1)[1].split(
            "## Repository evidence", 1
        )[0]
        unknowns_section = adr.split("## Unknowns", 1)[1].split(
            "## Consequences", 1
        )[0]
        self.assertNotIn("unknown", confirmed_section.lower())
        self.assertIn("unknown", unknowns_section.lower())

        scenarios = (ROOT / "tests" /
                     "scenarios.md").read_text(encoding="utf-8")
        for natural_request in (
            "We agreed that a Member is a person with an active workspace membership. Add that resolved term to our glossary.",
            "People use account for a login identity, a customer organization, and a billing record. Help us normalize it.",
            "CONTEXT.md says a Subscription can be paused, but the state machine has no paused state. Reconcile the domain meaning.",
            "Record our choice to make ledger entries immutable; migration is costly, the rule is surprising, and we rejected mutable corrections after weighing both options.",
            "Create an ADR for choosing the standard date library; switching later is cheap.",
            "Create an ADR for the conventional health-check URL; nobody would be surprised by it.",
            "Create an ADR for the mandated identity provider; no alternative is actually available.",
            "The code shows queue-backed delivery, but nobody can confirm why it was chosen. Write the rationale into an ADR.",
            "Update the domain glossary, but roots.domain_context is not configured.",
            "project.json is valid and roots.domain_context points to an existing domain directory. Resolve the glossary destination.",
            "project.json has a duplicate JSON key. Update the glossary anyway.",
            "roots.adrs points to an existing ADR directory. Determine the next ADR path.",
            "roots.adrs points to one existing file with no ledger convention. Append the ADR there.",
            "Write product requirements for subscription cancellation.",
            "Create an implementation plan for the billing migration.",
            "Improve the general onboarding documentation.",
        ):
            self.assertIn(natural_request, scenarios)
        self.assertIn("must activate `domain-model`", scenarios)
        self.assertIn("must not activate `domain-model`", scenarios)

    def test_ask_kit_metadata_workflow_and_scenarios_cover_routing_boundaries(self) -> None:
        skill_path = ROOT / ".agents" / "skills" / "ask-kit" / "SKILL.md"
        skill_text = skill_path.read_text(encoding="utf-8")
        metadata = validator.parse_frontmatter(skill_text, skill_path)

        self.assertEqual(metadata["name"], "ask-kit")
        description = metadata["description"].lower()
        for trigger in ("which skill", "path", "gate", "how to start"):
            self.assertIn(trigger, description)
        for adjacent_non_use in ("already names a skill", "direct coding"):
            self.assertIn(adjacent_non_use, description)
        self.assertLess(len(skill_text.splitlines()), 200)
        for heading in (
            "## Boundaries",
            "## Inspect only enough evidence",
            "## Choose the minimum safe route",
            "## Advance controlled work one gate",
            "## Resolve availability mismatches",
            "## Output contract",
            "## Quality gate",
            "## Stop conditions",
        ):
            self.assertIn(heading, skill_text)
        for required_behavior in (
            "shape-idea",
            "write-spec",
            "plan",
            "decompose-tasks",
            "implement",
            "review",
            "setup",
            "create-skill",
            "domain-model",
            "installed",
            "does not invoke",
            "does not write",
        ):
            self.assertIn(required_behavior, skill_text.lower())
        for path_name in ("direct", "spec-only", "plan-only", "full", "controlled"):
            self.assertIn(f"`{path_name}`", skill_text)
        self.assertIn(
            "Path: `<direct|spec-only|plan-only|full|controlled>`", skill_text
        )
        self.assertIn(
            "`full`: durable product behavior, non-obvious design, and multiple outcomes",
            skill_text,
        )
        for controlled_transition in (
            "Intent materially ambiguous -> `shape-idea`",
            "Accepted intent that needs durable persistence -> `write-spec`",
            "Durable intent without an approved plan -> `plan`",
            "Approved plan with multiple outcomes or handoff -> `decompose-tasks`",
            "Approved plan with one bounded outcome -> `implement`",
            "Implementation complete -> `review`",
        ):
            self.assertIn(controlled_transition, skill_text)
        for availability_rule in (
            "installed but disabled module is not usable",
            "Report the mismatch",
            "Block only when",
            "honestly satisfies the same next gate",
        ):
            self.assertIn(availability_rule, skill_text)

        scenarios = (ROOT / "tests" /
                     "scenarios.md").read_text(encoding="utf-8")
        for natural_request in (
            "Which kit skill should I use to start designing workspace invitations?",
            "What is the minimum safe path for a small permissions change?",
            "Should I write a spec or can I implement this accepted copy fix directly?",
            "Use plan to design the cache invalidation change.",
            "Fix the typo in the account menu.",
            "The invitation behavior is durable, the design is non-obvious, and delivery needs multiple tasks and handoff.",
            "The approved controlled plan has one bounded outcome left. What comes next?",
            "The optional architecture module is claimed in the manifest but its MODULE.md is missing.",
            "The installed evidence module is not enabled in project.json.",
        ):
            self.assertIn(natural_request, scenarios)
        self.assertIn("must activate `ask-kit`", scenarios)
        self.assertIn("must not activate `ask-kit`", scenarios)
        self.assertIn("one primary recommendation", scenarios)
        self.assertIn("safe installed alternative", scenarios)
        self.assertIn("no safe alternative", scenarios)
        self.assertIn("installed-but-disabled module", scenarios)


class BootstrapDiscoveryContractTests(unittest.TestCase):
    def test_agents_only_bootstrap_is_concise_navigation_not_copied_detail(self) -> None:
        agents_path = ROOT / "AGENTS.md"
        text = agents_path.read_text(encoding="utf-8")

        self.assertEqual(validator.validate_agents_bootstrap(ROOT), [])
        self.assertLessEqual(len(text.splitlines()), 245)
        self.assertNotIn("## Progressive disclosure", text)
        self.assertNotIn("## Optional module loading", text)
        self.assertLess(text.index("## Repository discovery"),
                        text.index("## Workflow"))
        self.assertIn("delivery chain", text.lower())
        self.assertIn("not the complete", text.lower())
        for canonical_path in (
            ".agents/kit-catalog.json",
            ".agents/skills/<name>/SKILL.md",
            ".agents/project.json",
            ".agents/project.md",
            ".agents/skills/setup/assets/project.schema.json",
            ".agents/skills/setup/references/project-config.md",
            ".agents/agentic-sdlc-kit.json",
            ".agents/modules/<name>/MODULE.md",
            "scripts/validate.py",
            ".agents/modules/enforcement/check.py",
            "roots.specs",
            "roots.work",
            "docs/usage-guide.md",
        ):
            self.assertIn(canonical_path, text)
        self.assertFalse((ROOT / ".agents" / "README.md").exists())
        self.assertNotIn("| default |", text.lower())
        self.assertNotIn("schema_version", text)
        self.assertNotIn("issue_tracker", text)

    def test_bootstrap_defines_lazy_order_precedence_and_enforcement_exception(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8").lower()
        normalized = " ".join(text.split())

        for contract in (
            "stop as soon as the request is addressable",
            "do not preload",
            "catalog membership and profiles",
            "installer-managed ownership",
            "filesystem presence",
            "report the mismatch",
            "installed, enabled",
            "read-only",
            "source checkout only",
            "skill metadata",
            "selected body",
            "one-level conditional resources",
            "supplement but never replace",
        ):
            self.assertIn(contract, normalized)
        self.assertLess(text.index(".agents/kit-catalog.json"),
                        text.index(".agents/skills/<name>/skill.md"))

    def test_bootstrap_requires_clear_unambiguous_human_communication(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8").lower()
        normalized = " ".join(text.split())

        for contract in (
            "communication failures caused by ambiguous questions or explanations",
            "simple, clear, friendly, and respectful language",
            "direct sentences and concrete words",
            "define necessary jargon",
            "each question and explanation self-contained and unambiguous",
            "relevant context, needed decision or action",
            "material constraints or consequences",
            "ask for confirmation rather than guessing",
        ):
            self.assertIn(contract, normalized)

        scenarios = (ROOT / "tests" /
                     "scenarios.md").read_text(encoding="utf-8")
        scenarios_normalized = " ".join(scenarios.split())
        self.assertIn("Clear and unambiguous communication", scenarios)
        self.assertIn("ask whether we should roll it back",
                      scenarios_normalized)
        self.assertIn("does not guess what `it` means", scenarios_normalized)

    def test_bootstrap_declares_language_neutral_source_documentation(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8").lower()
        normalized = " ".join(text.split())

        for contract in (
            "motivating failure",
            "source code in any language",
            "repository's canonical format",
            "established ecosystem convention",
            "externally consumable apis",
            "observable contract changes",
            "failures, side effects, constraints",
            "commands and scripts",
            "confirmed non-obvious rationale and invariants",
            "never invent why or narrate obvious code",
            "generator, schema, or template instead of generated output",
            "do not edit vendored code",
            "applicable safe existing documentation checks",
            "focused manual review for accuracy, completeness, and freshness",
        ):
            self.assertIn(contract, normalized)

        scenarios = (ROOT / "tests" /
                     "scenarios.md").read_text(encoding="utf-8")
        scenarios_normalized = " ".join(scenarios.split())
        self.assertIn("Language-neutral source documentation", scenarios)
        self.assertIn(
            "public TypeScript API and an operator-facing shell", scenarios_normalized)
        self.assertIn(
            "if an affected interface is generated", scenarios_normalized)
        self.assertIn("does not edit vendored code", scenarios_normalized)

    def test_root_consumers_use_recognized_configuration_or_safe_fallback(self) -> None:
        contracts = {
            "write-spec": ("roots.specs", "specs/"),
            "plan": ("roots.work", ".work/"),
            "decompose-tasks": ("roots.work", ".work/"),
            "implement": ("roots.work", ".work/"),
            "review": ("roots.work", ".work/"),
        }
        for name, (configured_root, fallback) in contracts.items():
            with self.subTest(skill=name):
                path = ROOT / ".agents" / "skills" / name / "SKILL.md"
                text = path.read_text(encoding="utf-8")
                lowered = text.lower()
                self.assertIn(".agents/project.json", text)
                self.assertIn(".agents/project.md", text)
                self.assertIn("unsupported", lowered)
                self.assertIn(
                    ".agents/skills/setup/assets/project.schema.json", text)
                self.assertIn(
                    ".agents/skills/setup/references/project-config.md", text)
                self.assertIn(configured_root, text)
                self.assertIn(fallback, text)
                self.assertIn("invalid", lowered)
                self.assertIn("stop", lowered)
                self.assertNotIn("exactly `schema_version`", lowered)

    def test_bootstrap_and_root_scenarios_cover_natural_requests(self) -> None:
        scenarios = (ROOT / "tests" /
                     "scenarios.md").read_text(encoding="utf-8")
        for request in (
            "Starting only from AGENTS.md, find the installed capability that can help me plan this change.",
            "Write the approved export spec using our recognized project configuration, where roots.specs is product/specifications.",
            "Plan this accepted change with no .agents/project.json in the repository.",
            "Continue TASK-015, but .agents/project.json has an unsupported schema version.",
        ):
            self.assertIn(request, scenarios)
        self.assertIn("must not require `.agents/README.md`", scenarios)
        self.assertIn("`product/specifications/`", scenarios)
        self.assertIn("`delivery/work/`", scenarios)
        self.assertIn("stops rather than guessing", scenarios)

    def test_entrypoint_mutations_and_old_root_regressions_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(
                ".git", ".work", "__pycache__"))
            manifest = root / ".agents" / "agentic-sdlc-kit.json"
            self.assertFalse(manifest.exists())
            self.assertEqual(validator.validate_agents_bootstrap(root), [])

            agents = root / "AGENTS.md"
            original = agents.read_text(encoding="utf-8")

            forbidden_readme = root / ".agents" / "README.md"
            forbidden_readme.write_text(
                "# Extra context layer\n", encoding="utf-8")
            self.assertIn(
                "forbidden context layer",
                "\n".join(validator.validate_agents_bootstrap(root)),
            )
            forbidden_readme.unlink()

            full_members = ALL_SKILLS + FULL_MODULES
            agents.write_text(
                original
                + "\n\nThe full profile includes "
                + ", ".join(full_members)
                + ".\n",
                encoding="utf-8",
            )
            self.assertIn(
                "complete profile membership",
                "\n".join(validator.validate_agents_bootstrap(root)),
            )

            agents.write_text(
                original.replace(".agents/kit-catalog.json",
                                 ".agents/catalog.json", 1),
                encoding="utf-8",
            )
            self.assertIn(
                "missing canonical bootstrap pointer",
                "\n".join(validator.validate_agents_bootstrap(root)),
            )
            agents.write_text(original, encoding="utf-8")

            write_spec = root / ".agents" / "skills" / "write-spec" / "SKILL.md"
            skill = write_spec.read_text(encoding="utf-8")
            write_spec.write_text(
                skill.replace("<specs-root>/", "specs/"), encoding="utf-8"
            )
            self.assertIn(
                "configured-root consumer contract",
                "\n".join(validator.validate_agents_bootstrap(root)),
            )

    def test_spec_amendment_requires_evidence_for_verified_state(self) -> None:
        spec = (ROOT / "specs" / "001-agentic-sdlc-kit-v1" / "spec.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("status: verified", spec)
        for source_id in ("REQ-035", "REQ-036", "AC-011", "AC-012"):
            self.assertIn(f"**{source_id}**", spec)
        self.assertIn("Default utility skills", spec)
        self.assertIn("Optional skill: `domain-model`", spec)
        self.assertIn(
            "source checkout passes `python3 scripts/validate.py`", spec)
        self.assertIn("installed read-only", spec)
        self.assertEqual(validator.validate_v1_source_coverage(ROOT), [])

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "specs" / "001-agentic-sdlc-kit-v1" / "spec.md"
            path.parent.mkdir(parents=True)
            path.write_text(spec, encoding="utf-8")
            self.assertIn(
                "verified SPEC-001 evidence is unavailable",
                "\n".join(validator.validate_v1_source_coverage(root)),
            )

            evidence_dir = root / "evidence" / "spec-001"
            evidence_dir.mkdir(parents=True)
            (evidence_dir / "review.md").write_text("# Review\n", encoding="utf-8")
            valid_evidence = json.loads(
                (ROOT / "evidence" / "spec-001" / "evidence.json").read_text(
                    encoding="utf-8"
                )
            )
            invalid_documents = [[], copy.deepcopy(
                valid_evidence), copy.deepcopy(valid_evidence)]
            invalid_documents[1]["lifecycle"] = []
            invalid_documents[2]["review"] = []
            for invalid_document in invalid_documents:
                with self.subTest(invalid_type=type(invalid_document).__name__):
                    (evidence_dir / "evidence.json").write_text(
                        json.dumps(invalid_document), encoding="utf-8"
                    )
                    errors = validator.validate_v1_source_coverage(root)
                    self.assertTrue(errors)

            path.write_text(spec.replace(
                "**REQ-036**", "REQ-036", 1), encoding="utf-8")
            self.assertIn(
                "requirement source coverage mismatch",
                "\n".join(validator.validate_v1_source_coverage(root)),
            )

            duplicate_cases = (
                ("REQ-036", "duplicate requirement source ID"),
                ("AC-012", "duplicate acceptance source ID"),
            )
            for source_id, expected in duplicate_cases:
                with self.subTest(source_id=source_id):
                    marker = f"**{source_id}**"
                    path.write_text(
                        spec + f"\n\nDuplicate fixture {marker}.\n", encoding="utf-8"
                    )
                    self.assertIn(
                        f"{expected}: {source_id}",
                        "\n".join(validator.validate_v1_source_coverage(root)),
                    )


class DocumentationConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "source"
        self.root.mkdir()
        for name in ("README.md", "AGENTS.md", "LICENSE"):
            shutil.copy2(ROOT / name, self.root / name)
        shutil.copytree(ROOT / "docs", self.root / "docs")
        shutil.copytree(ROOT / "tests", self.root / "tests")
        reference = self.root / ".agents" / "skills" / "setup" / "references"
        reference.mkdir(parents=True)
        shutil.copy2(
            ROOT / ".agents" / "skills" / "setup" / "references" / "project-config.md",
            reference / "project-config.md",
        )
        contribute = self.root / ".agents" / "skills" / "contribute"
        (contribute / "references").mkdir(parents=True)
        shutil.copy2(ROOT / ".agents" / "skills" / "contribute" / "SKILL.md",
                     contribute / "SKILL.md")
        shutil.copy2(ROOT / ".agents" / "skills" / "contribute" / "references" / "commits.md",
                     contribute / "references" / "commits.md")
        shutil.copy2(ROOT / ".agents" / "skills" / "contribute" / "references" / "pull-requests.md",
                     contribute / "references" / "pull-requests.md")
        shutil.copy2(ROOT / ".agents" / "skills" / "contribute" / "references" / "review-responses.md",
                     contribute / "references" / "review-responses.md")
        enforcement = self.root / ".agents" / "modules" / "enforcement"
        enforcement.mkdir(parents=True)
        shutil.copy2(
            ROOT / ".agents" / "modules" / "enforcement" / "MODULE.md",
            enforcement / "MODULE.md",
        )
        self.catalog = json.loads(
            (ROOT / ".agents" / "kit-catalog.json").read_text(encoding="utf-8")
        )

    def validate(self) -> list[str]:
        return validator.validate_public_documentation(self.root, self.catalog)

    def test_repository_documentation_matches_catalog_commands_and_links(self) -> None:
        self.assertEqual(validator.validate_public_documentation(
            ROOT, self.catalog), [])
        self.assertEqual(self.validate(), [])

    def mutate(self, relative: str, old: str, new: str) -> str:
        path = self.root / relative
        original = path.read_text(encoding="utf-8")
        self.assertIn(old, original)
        path.write_text(original.replace(old, new, 1), encoding="utf-8")
        try:
            return "\n".join(self.validate())
        finally:
            path.write_text(original, encoding="utf-8")

    def test_profile_member_addition_and_removal_are_rejected(self) -> None:
        default_row = (
            "| default | `drill-docs`, `save-output`, `judge-spec`, `plan-feature`, "
            "`breakdown-tasks`, `implement`, `close-spec`, `git-conventions`, "
            "`create-skill`, `agents-creator`, `setup`, `ask-kit`, "
            "`contribute` | none |"
        )
        for replacement in (
            default_row.replace("`ask-kit`", "`ask-kit`, `domain-model`"),
            default_row.replace(", `ask-kit`", ""),
        ):
            with self.subTest(replacement=replacement):
                rendered = self.mutate(
                    "docs/usage-guide.md", default_row, replacement
                )
                self.assertIn("profile table mismatch", rendered)

    def test_inverted_compliance_dependency_is_rejected(self) -> None:
        rendered = self.mutate(
            "docs/usage-guide.md",
            "| compliance | `evidence`, `enforcement` |",
            "| evidence | `compliance` |",
        )
        self.assertIn("module dependency table mismatch", rendered)

    def test_installer_exit_code_drift_is_rejected(self) -> None:
        rendered = self.mutate(
            "docs/usage-guide.md",
            "| `3` | applied; AGENTS.md semantic merge required |",
            "| `7` | applied; AGENTS.md semantic merge required |",
        )
        self.assertIn("installer exit-code table mismatch", rendered)

    def test_enforcement_exit_code_drift_is_rejected(self) -> None:
        rendered = self.mutate(
            "docs/usage-guide.md",
            "| `2` | invalid invocation; malformed/unrecognized configuration; invalid/uninspectable/symlink root; safe-inspection failure |",
            "| `9` | invalid invocation; malformed/unrecognized configuration; invalid/uninspectable/symlink root; safe-inspection failure |",
        )
        self.assertIn("enforcement exit-code table mismatch", rendered)

    def test_enforcement_module_exit_contract_drift_is_rejected(self) -> None:
        rendered = self.mutate(
            ".agents/modules/enforcement/MODULE.md",
            "| `2` | invalid invocation; malformed/unrecognized configuration; invalid/uninspectable/symlink root; safe-inspection failure |",
            "| `7` | invalid invocation; malformed/unrecognized configuration; invalid/uninspectable/symlink root; safe-inspection failure |",
        )
        self.assertIn("enforcement module exit-code table mismatch", rendered)

    def test_keep_cannot_claim_manifest_ownership(self) -> None:
        rendered = self.mutate(
            "docs/usage-guide.md",
            "| keep | no write; conflicting component remains project-owned | unmanifested |",
            "| keep | no write; conflicting component remains project-owned | managed and hashed |",
        )
        self.assertIn("installer ownership table mismatch", rendered)

    def test_unsupported_causal_or_universal_speed_claim_is_rejected(self) -> None:
        rendered = self.mutate(
            "docs/usage-guide.md",
            "| causal effect | prohibited without an appropriately powered design and supporting evidence |",
            "| causal effect | allowed: the kit causes improvement and is universally faster |",
        )
        self.assertIn("baseline claim-limitation polarity", rendered)

    def test_broken_local_target_and_heading_are_actionable(self) -> None:
        readme = self.root / "README.md"
        original = readme.read_text(encoding="utf-8")
        cases = (
            ("docs/usage-guide.md#catalog-and-profiles",
             "docs/missing.md", "missing documentation link target"),
            ("#portability", "#missing-heading", "missing documentation heading"),
        )
        for old, new, expected in cases:
            with self.subTest(expected=expected):
                readme.write_text(original.replace(
                    old, new, 1), encoding="utf-8")
                try:
                    self.assertIn(expected, "\n".join(self.validate()))
                finally:
                    readme.write_text(original, encoding="utf-8")


class RetiredMarkdownProjectConfigExamples:
    def setUp(self) -> None:
        self.path = Path(".agents/project.json")

    def parse(self, text: str = SETUP_TEMPLATE) -> dict[str, object]:
        return validator.parse_project_json(text, self.path)

    def test_schema_v2_default_policy_and_legacy_v1_are_recognized(self) -> None:
        current = self.parse()
        self.assertEqual(current["schema_version"], 2)
        self.assertEqual(current["approval_policy"], {"rules": []})
        self.assertEqual(validator.validate_project_config(
            current, self.path), [])

        legacy = dict(current)
        legacy["schema_version"] = 1
        legacy.pop("approval_policy")
        self.assertEqual(
            validator.validate_project_config(legacy, self.path), [])

    def test_approval_policy_is_closed_bounded_and_cannot_weaken_high_risk(self) -> None:
        valid = self.parse()
        valid["approval_policy"] = {
            "rules": [
                {
                    "risk": "medium",
                    "action": "lifecycle-transition",
                    "required_roles": [{"role": "reviewer", "minimum": 2}],
                    "independent": True,
                }
            ]
        }
        self.assertEqual(
            validator.validate_project_config(valid, self.path), [])

        cases = (
            ({"rules": [], "unknown": True}, "unknown"),
            ({"rules": [{"risk": "medium"}]}, "required_roles"),
            ({"rules": [{"risk": "unknown", "action": "change-created",
             "required_roles": [], "independent": False}]}, "risk"),
            ({"rules": [{"risk": "low", "action": "bad action",
             "required_roles": [], "independent": False}]}, "action"),
            ({"rules": [{"risk": "low", "action": "approval-recorded", "required_roles": [
             {"role": "reviewer", "minimum": 0}], "independent": False}]}, "minimum"),
            ({"rules": [{"risk": "high", "action": "lifecycle-transition",
             "required_roles": [], "independent": False}]}, "high-risk"),
        )
        for policy, expected in cases:
            with self.subTest(expected=expected):
                config = self.parse()
                config["approval_policy"] = policy
                self.assertIn(
                    expected,
                    "\n".join(validator.validate_project_config(
                        config, self.path)),
                )

    def test_rejects_http_urls_with_userinfo_without_echoing_values(self) -> None:
        cases = (
            (
                "issue_tracker.location",
                lambda config: config.update(
                    issue_tracker={
                        "kind": "github",
                        "location": "https://agent@example.test/issues",
                    }
                ),
            ),
            (
                "repositories[0].remote",
                lambda config: config.update(
                    repositories=[
                        {
                            "name": "app",
                            "path": ".",
                            "remote": "https://agent:do-not-echo@example.test/repo.git",
                        }
                    ]
                ),
            ),
        )
        for field, mutate in cases:
            with self.subTest(field=field):
                config = self.parse()
                mutate(config)

                errors = validator.validate_project_config(config, self.path)
                rendered = "\n".join(errors)

                self.assertIn(field, rendered)
                self.assertIn("userinfo", rendered)
                self.assertNotIn("do-not-echo", rendered)
                self.assertNotIn("example.test", rendered)

    def test_rejects_clear_sensitive_http_query_parameters(self) -> None:
        parameter_names = (
            "token",
            "access_token",
            "Access-Token",
            "api_key",
            "apikey",
            "API-KEY",
            "secret",
            "client_secret",
            "password",
            "credential",
            "credentials",
            "github_token",
            "dbPassword",
            "service-credential",
            "private-api-key",
        )
        for parameter in parameter_names:
            with self.subTest(parameter=parameter):
                config = self.parse()
                config["issue_tracker"] = {
                    "kind": "other",
                    "location": f"https://tracker.test/issues?{parameter}=do-not-echo",
                }

                errors = validator.validate_project_config(config, self.path)
                rendered = "\n".join(errors)

                self.assertIn("issue_tracker.location", rendered)
                self.assertIn("sensitive query parameter", rendered)
                self.assertNotIn("do-not-echo", rendered)
                self.assertNotIn("tracker.test", rendered)

        config = self.parse()
        config["repositories"] = [
            {
                "name": "app",
                "path": ".",
                "remote": "https://example.test/repo.git?password=do-not-echo",
            }
        ]
        rendered = "\n".join(
            validator.validate_project_config(config, self.path)
        )
        self.assertIn("repositories[0].remote", rendered)
        self.assertIn("sensitive query parameter", rendered)
        self.assertNotIn("do-not-echo", rendered)

    def test_rejects_malformed_http_urls_without_echoing_values(self) -> None:
        cases = (
            (
                "issue_tracker.location",
                lambda config: config.update(
                    issue_tracker={
                        "kind": "other",
                        "location": "https://[malformed-do-not-echo",
                    }
                ),
            ),
            (
                "repositories[0].remote",
                lambda config: config.update(
                    repositories=[
                        {
                            "name": "app",
                            "path": ".",
                            "remote": "HTTP://[malformed-do-not-echo",
                        }
                    ]
                ),
            ),
        )
        for field, mutate in cases:
            with self.subTest(field=field):
                config = self.parse()
                mutate(config)

                rendered = "\n".join(
                    validator.validate_project_config(config, self.path)
                )

                self.assertIn(field, rendered)
                self.assertIn("malformed HTTP(S) URL", rendered)
                self.assertNotIn("malformed-do-not-echo", rendered)

    def test_rejects_http_urls_with_leading_or_trailing_prohibited_chars(self) -> None:
        cases = (
            ("issue_tracker.location", " https://example.test/private-do-not-echo"),
            ("issue_tracker.location", "\x1fhttps://example.test/private-do-not-echo"),
            ("issue_tracker.location", "https://example.test/private-do-not-echo "),
            ("issue_tracker.location", "https://example.test/private-do-not-echo\x7f"),
            ("repositories[0].remote",
             " https://example.test/private-do-not-echo"),
            ("repositories[0].remote",
             "\x1fhttps://example.test/private-do-not-echo"),
            ("repositories[0].remote",
             "https://example.test/private-do-not-echo "),
            ("repositories[0].remote",
             "https://example.test/private-do-not-echo\x7f"),
        )
        for field, value in cases:
            with self.subTest(field=field, value=repr(value)):
                config = self.parse()
                if field == "issue_tracker.location":
                    config["issue_tracker"] = {
                        "kind": "other", "location": value}
                else:
                    config["repositories"] = [
                        {"name": "app", "path": ".", "remote": value}
                    ]

                rendered = "\n".join(
                    validator.validate_project_config(config, self.path)
                )

                self.assertIn(field, rendered)
                self.assertIn("malformed HTTP(S) URL", rendered)
                self.assertNotIn("private-do-not-echo", rendered)
                self.assertNotIn("example.test", rendered)

    def test_rejects_semantically_invalid_http_urls_without_echoing_values(self) -> None:
        invalid_tracker_locations = (
            "https://",
            "https:///private-do-not-echo/path",
            "https://:443/private-do-not-echo",
            "https://example.test:notaport/private-do-not-echo",
            "https://example.test:70000/private-do-not-echo",
            "https://example.test/private do-not-echo",
            "https://example.test/private\x1fdo-not-echo",
            "http:private-do-not-echo/path",
        )
        for location in invalid_tracker_locations:
            with self.subTest(location=location):
                config = self.parse()
                config["issue_tracker"] = {
                    "kind": "other",
                    "location": location,
                }

                rendered = "\n".join(
                    validator.validate_project_config(config, self.path)
                )

                self.assertIn("issue_tracker.location", rendered)
                self.assertIn("malformed HTTP(S) URL", rendered)
                self.assertNotIn("private-do-not-echo", rendered)
                self.assertNotIn("example.test", rendered)

        config = self.parse()
        config["repositories"] = [
            {
                "name": "app",
                "path": ".",
                "remote": "http:private-do-not-echo/repo.git",
            }
        ]
        rendered = "\n".join(
            validator.validate_project_config(config, self.path)
        )
        self.assertIn("repositories[0].remote", rendered)
        self.assertIn("malformed HTTP(S) URL", rendered)
        self.assertNotIn("private-do-not-echo", rendered)

    def test_rejects_windows_drive_qualified_paths_without_echoing_values(self) -> None:
        cases = (
            ("roots.specs", "C:/private-do-not-echo/specs"),
            ("roots.domain_context", "c:private-do-not-echo/context.md"),
            ("repositories[0].path", "D:private-do-not-echo/service"),
        )
        for field, value in cases:
            with self.subTest(field=field):
                config = self.parse()
                if field.startswith("roots."):
                    config["roots"][field.split(".", 1)[1]] = value
                else:
                    config["repositories"] = [
                        {"name": "app", "path": value, "remote": None}
                    ]

                rendered = "\n".join(
                    validator.validate_project_config(config, self.path)
                )

                self.assertIn(field, rendered)
                self.assertIn("must be a relative path", rendered)
                self.assertNotIn("private-do-not-echo", rendered)

    def test_repository_paths_allow_dot_relative_or_one_exact_environment_placeholder(self) -> None:
        config = self.parse()
        config["repositories"] = [
            {"name": "current", "path": ".", "remote": None},
            {"name": "nested", "path": "services/api", "remote": None},
            {
                "name": "sibling",
                "path": "${WORKSPACE_ROOT}/service",
                "remote": None,
            },
        ]
        self.assertEqual(
            validator.validate_project_config(config, self.path), [])

        invalid_paths = (
            "${WORKSPACE_ROOT}",
            "$WORKSPACE_ROOT/service",
            "${workspace}/service",
            "prefix/${WORKSPACE_ROOT}/service",
            "${WORKSPACE_ROOT}/../service",
            "${WORKSPACE_ROOT}/service/${OTHER}",
        )
        for value in invalid_paths:
            with self.subTest(value=value):
                config = self.parse()
                config["repositories"] = [
                    {"name": "service", "path": value, "remote": None}
                ]
                self.assertIn(
                    "repositories[0].path",
                    "\n".join(validator.validate_project_config(
                        config, self.path)),
                )

    def test_repository_ids_are_unique_stable_kebab_case_names(self) -> None:
        for names in (("api", "api"), ("API", "service"), ("api repo", "service")):
            with self.subTest(names=names):
                config = self.parse()
                config["repositories"] = [
                    {"name": name, "path": ".", "remote": None}
                    for name in names
                ]
                self.assertIn(
                    "repository",
                    "\n".join(validator.validate_project_config(
                        config, self.path)),
                )

    def test_allows_safe_urls_and_normal_ssh_remotes(self) -> None:
        config = self.parse()
        config["issue_tracker"] = {
            "kind": "github",
            "location": "https://github.com/example/project/issues?state=open",
        }
        config["repositories"] = [
            {"name": "web", "path": ".", "remote": "git@github.com:org/web.git"},
            {
                "name": "api",
                "path": "services/api",
                "remote": "ssh://git@github.com/org/api.git",
            },
            {
                "name": "docs",
                "path": "docs",
                "remote": "https://github.com/org/docs.git",
            },
            {
                "name": "drive-guide",
                "path": "c-drive/guide",
                "remote": None,
            },
            {
                "name": "local",
                "path": "local",
                "remote": "http://localhost:8080/repo.git",
            },
            {
                "name": "ipv4",
                "path": "mirrors/ipv4",
                "remote": "https://127.0.0.1:8443/repo.git",
            },
            {
                "name": "ipv6",
                "path": "mirrors/ipv6",
                "remote": "http://[::1]:3000/repo.git",
            },
        ]

        self.assertEqual(
            validator.validate_project_config(config, self.path), [])

    def test_rejects_duplicate_keys_in_json_objects_at_any_depth(self) -> None:
        cases = (
            SETUP_TEMPLATE.replace(
                'issue_tracker: {"kind":"none","location":null}',
                'issue_tracker: {"kind":"github","kind":"gitlab","location":null}',
            ),
            SETUP_TEMPLATE.replace(
                "triage_labels: {}",
                'triage_labels: {"workflow":{"name":"first","name":"second"}}',
            ),
        )
        for text in cases:
            with self.subTest(text=text):
                with self.assertRaisesRegex(
                    ValueError, "contains duplicate JSON object key"
                ):
                    self.parse(text)


class ReviewContractTests(unittest.TestCase):
    def test_review_skill_defines_risk_based_evidence_review(self) -> None:
        skill_path = ROOT / ".agents" / "skills" / "review" / "SKILL.md"
        skill = skill_path.read_text(encoding="utf-8")
        lowered = skill.lower()

        self.assertLess(len(skill.splitlines()), 200)
        for rule in (
            "fixed base and head",
            "uncommitted",
            "implementer's summary",
            "change contract",
            "contract risk",
            "reviewer-assessed risk",
            "deviation",
            "review focus",
            "self-review is never independent",
            "risk, not diff size",
            "intent conformance",
            "engineering quality",
            "missing, partial, or extra behavior",
            "observed evidence",
            "source-based inference",
            "unverified claim",
            "tests green",
            "changes-required",
            "blocked",
        ):
            self.assertIn(rule, lowered)
        for signal in (
            "correctness",
            "security",
            "compatibility",
            "maintainability",
            "performance",
            "accessibility",
            "observability",
            "cost",
            "understandability",
        ):
            self.assertIn(signal, lowered)

    def test_review_template_captures_required_report_fields(self) -> None:
        template = (
            ROOT / ".agents" / "skills" / "review" / "assets" / "review.template.md"
        ).read_text(encoding="utf-8")
        for field in (
            "## Scope",
            "Fixed base:",
            "Fixed head:",
            "Committed range:",
            "Uncommitted scope:",
            "## Reviewer role and independence",
            "Reviewer role:",
            "Implementer(s):",
            "Prior role:",
            "Independence:",
            "Independence basis:",
            "Independence required:",
            "Independence met:",
            "## Authoritative sources",
            "## Risk",
            "Reviewer-assessed risk:",
            "Risk rationale:",
            "## Change contract and review focus",
            "What:",
            "Authoritative why:",
            "Contract scope:",
            "Required evidence:",
            "Contract risk:",
            "Agent roles:",
            "Review focus:",
            "Risk comparison/deviation:",
            "Missing-contract impact:",
            "## Selected quality signals",
            "Disposition",
            "N/A reason",
            "## Checks and evidence",
            "## Findings",
            "Evidence class:",
            "Location:",
            "Impact:",
            "Minimal action:",
            "## Acceptance coverage",
            "## Residual risk",
            "## Verdict",
        ):
            self.assertIn(field, template)
        for evidence_class in (
            "observed evidence",
            "source-based inference",
            "unverified claim",
        ):
            self.assertIn(evidence_class, template)
        for verdict in ("approved", "changes-required", "blocked"):
            self.assertIn(verdict, template)
        for signal in (
            "Correctness",
            "Security",
            "Compatibility",
            "Maintainability",
            "Performance",
            "Accessibility",
            "Observability",
            "Cost",
            "Understandability",
        ):
            self.assertEqual(template.count(f"| {signal} |"), 1)

    def test_scenarios_cover_review_risk_and_failure_boundaries(self) -> None:
        scenarios = (ROOT / "tests" /
                     "scenarios.md").read_text(encoding="utf-8")
        for scenario in (
            "Low-risk review selects relevant signals",
            "Medium-risk review depth",
            "High-risk review requires independence",
            "Missing required review evidence",
            "Irrelevant review dimensions",
            "False implementation completion",
            "Passing tests miss acceptance behavior",
            "Review defect versus blocker",
            "Self-review versus independent review",
        ):
            self.assertIn(scenario, scenarios)
        irrelevant = scenarios.split(
            "## 60. Irrelevant review dimensions", 1
        )[1].split("## 61.", 1)[0]
        self.assertIn("maintainability", irrelevant.lower())


class PlannedExecutionContractTests(unittest.TestCase):
    def test_skills_define_topology_backpressure_and_agent_roles(self) -> None:
        skills = ROOT / ".agents" / "skills"
        decompose = (skills / "decompose-tasks" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        implement = (skills / "implement" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertLess(len(decompose.splitlines()), 200)
        self.assertLess(len(implement.splitlines()), 200)
        for topology in (
            "primary agent",
            "fresh implementer per task",
            "implementer + fresh validator",
        ):
            self.assertIn(topology, decompose.lower())
        for rule in (
            "approved project preference",
            "ask once",
            "review queue",
            "maximum one",
            "assignment",
            "isolation",
        ):
            self.assertIn(rule, decompose.lower())
        for role_rule in (
            "exploration is read-only",
            "assigned outcome",
            "validation is non-mutating",
            "subagents only",
        ):
            self.assertIn(role_rule, decompose.lower())

        for rule in (
            "change contract",
            "review queue",
            "validation is non-mutating",
            "failed",
            "tasks.md",
        ):
            self.assertIn(rule, implement.lower())

    def test_testing_reference_selects_behavioral_vertical_evidence(self) -> None:
        testing = (
            ROOT / ".agents" / "skills" / "implement" / "references" / "testing.md"
        ).read_text(encoding="utf-8")
        for rule in (
            "risk and observable behavior",
            "stable public seams",
            "agree the seam",
            "tracer bullet",
            "one test",
            "red-green",
            "tautological",
            "implementation-coupled",
            "private or internal",
            "horizontal slicing",
        ):
            self.assertIn(rule, testing.lower())
        self.assertLess(len(testing.splitlines()), 200)

    def test_handoff_template_preserves_objective_recovery_state(self) -> None:
        handoff = (
            ROOT
            / ".agents"
            / "skills"
            / "implement"
            / "assets"
            / "handoff.template.md"
        ).read_text(encoding="utf-8")
        for heading in (
            "## Baseline and working-tree state",
            "## Authoritative task state",
            "## Objective last progress",
            "## Exact checks and results",
            "## Agent topology and roles",
            "## Consumed limits",
            "## Stop reason",
            "## Blockers or required decision",
            "## Next safe action",
        ):
            self.assertIn(heading, handoff)
        self.assertIn("not-tracked", handoff)
        self.assertIn("tasks.md", handoff)

    def test_scenarios_cover_planned_execution_failure_modes(self) -> None:
        scenarios = (ROOT / "tests" /
                     "scenarios.md").read_text(encoding="utf-8")
        for scenario in (
            "Primary-agent topology",
            "Fresh implementer per task topology",
            "Implementer plus fresh validator topology",
            "WIP capacity is saturated",
            "Review queue applies backpressure",
            "Material public seam",
            "Tautological test",
            "Implementation-coupled private mock",
            "Horizontal slicing",
            "Failed required checks",
            "Handoff with untracked limits",
            "Recurrent failure control",
        ):
            self.assertIn(scenario, scenarios)

    def test_contract_centralizes_recurrent_failure_controls(self) -> None:
        contract = (ROOT / "AGENTS.md").read_text(encoding="utf-8").lower()
        for rule in (
            "named motivating failure",
            "human approval",
            "do not automatically modify repository rules or ci",
        ):
            self.assertIn(rule, contract)


class ProvenanceContractTests(unittest.TestCase):
    def test_repository_contract_and_skills_define_provenance_boundaries(self) -> None:
        contract = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for term in (
            "Authoritative source/input",
            "Confirmed rationale",
            "Repository evidence/fact",
            "Confirmed constraint",
            "Assumption",
            "Agent inference",
            "Unknown",
        ):
            self.assertIn(term, contract)
        self.assertIn("private chain-of-thought", contract)
        self.assertIn("not product or decision authority", contract)

        skills = ROOT / ".agents" / "skills"
        shape = (skills / "shape-idea" /
                 "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("contradiction", shape.lower())
        self.assertIn("Authoritative inputs", shape)
        self.assertIn("Confirmed decisions and rationale", shape)
        self.assertIn("Unknowns", shape)

        write_spec = (skills / "write-spec" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("source authority", write_spec.lower())
        self.assertIn("product why", write_spec.lower())
        self.assertIn("Unknown", write_spec)

        plan = (skills / "plan" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("agent inference", plan.lower())
        self.assertIn("never silently becomes", plan.lower())
        self.assertIn("impact map", plan.lower())

        decompose = (skills / "decompose-tasks" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("do not copy or invent", decompose.lower())
        self.assertIn("execution and risk", decompose.lower())
        self.assertIn("upstream", decompose.lower())

    def test_repository_templates_expose_required_provenance_fields(self) -> None:
        skills = ROOT / ".agents" / "skills"
        spec = (skills / "write-spec" / "assets" / "spec.template.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("sources:", spec)
        self.assertIn("## Confirmed rationale", spec)

        plan = (skills / "plan" / "assets" / "plan.template.md").read_text(
            encoding="utf-8"
        )
        for heading in (
            "## Repository findings and facts",
            "## Confirmed constraints",
            "## Assumptions",
            "## Agent inferences",
            "## Unknowns",
            "## Confirmed technical decisions and rationale",
            "## Source coverage and impact map",
        ):
            self.assertIn(heading, plan)


def evidence_document(risk: str) -> dict[str, object]:
    checks = [
        {
            "id": "scoped-tests",
            "requirement_ids": ["TASK-009"],
            "repository_ids": ["current"],
            "kind": "scoped",
            "required": True,
            "applicability": "applicable",
            "not_applicable_reason": None,
            "status": "passed",
            "observed_result": "Focused tests passed.",
            "evidence_class": "observed evidence",
            "output_reference": "artifacts/scoped-tests.txt",
        }
    ]
    if risk in ("medium", "high"):
        checks.extend(
            [
                {
                    "id": "regression-tests",
                    "requirement_ids": ["TASK-009"],
                    "repository_ids": ["current"],
                    "kind": "regression",
                    "required": True,
                    "applicability": "applicable",
                    "not_applicable_reason": None,
                    "status": "passed",
                    "observed_result": "Regression tests passed.",
                    "evidence_class": "observed evidence",
                    "output_reference": "artifacts/regression-tests.txt",
                },
                {
                    "id": "failure-paths",
                    "requirement_ids": ["TASK-009"],
                    "repository_ids": ["current"],
                    "kind": "failure-path",
                    "required": False,
                    "applicability": "not-applicable",
                    "not_applicable_reason": "No changed failure path.",
                    "status": "not-applicable",
                    "observed_result": None,
                    "evidence_class": None,
                    "output_reference": None,
                },
            ]
        )
    if risk == "high":
        checks.append(
            {
                "id": "recovery",
                "requirement_ids": ["TASK-009"],
                "repository_ids": ["current"],
                "kind": "recovery-rollback",
                "required": False,
                "applicability": "not-applicable",
                "not_applicable_reason": "The additive artifact change is removed by revert.",
                "status": "not-applicable",
                "observed_result": None,
                "evidence_class": None,
                "output_reference": None,
            }
        )
    uncommitted_entries = [
        {
            "path": "scripts/validate.py",
            "state": "unstaged",
            "sha256": "c" * 64,
        }
    ]
    snapshot_sha256 = hashlib.sha256(
        json.dumps(
            uncommitted_entries, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": 1,
        "change_id": "TASK-009",
        "authoritative_sources": [
            {"id": "TASK-009", "reference": "request:TASK-009"}
        ],
        "lifecycle": {
            "status": "complete",
            "transition": "verified",
            "evidence_references": ["review.md"],
        },
        "risk": {"level": risk, "rationale": "Bounded repository change."},
        "change_contract": {
            "intent": "Provide optional structured evidence.",
            "confirmed_why": "request:TASK-009",
            "scope": "Evidence module and integration contracts.",
            "expected_evidence": ["Focused validation results."],
            "agent_roles": ["implementer", "reviewer"],
            "review_focus": ["Schema and opt-in behavior."],
        },
        "repository_scope": [
            {
                "repository_id": "current",
                "base": "a" * 40,
                "head": "b" * 40,
                "committed_range": f"{'a' * 40}..{'b' * 40}",
                "uncommitted_entries": uncommitted_entries,
                "snapshot_sha256": snapshot_sha256,
            }
        ],
        "requirement_coverage": [
            {
                "requirement_id": "TASK-009",
                "repository_ids": ["current"],
                "status": "covered",
                "implementation_references": [".agents/modules/evidence/MODULE.md"],
                "evidence_references": ["review.md"],
            }
        ],
        "checks": checks,
        "review": {
            "reviewer_role": "fresh reviewer" if risk == "high" else "implementer self-review",
            "reviewer_id": "agent-reviewer" if risk == "high" else "agent-implementer",
            "implementers": ["agent-implementer"],
            "prior_participation": [] if risk == "high" else ["implementation"],
            "fresh_context": risk == "high",
            "independence": "independent" if risk == "high" else "self-review",
            "independence_basis": (
                "Declared fresh context with no implementation participation."
                if risk == "high"
                else "Declared reviewer also implemented the change."
            ),
            "verdict": "approved",
            "reference": "review.md",
        },
        "known_limits": "not-tracked",
        "remaining_risks": [],
        "follow_ups": [],
    }


class EvidenceContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.path = Path("evidence/TASK-009/evidence.json")

    def validate(self, document: object) -> list[str]:
        return validator.validate_evidence_document(document, self.path)

    def test_valid_low_medium_and_high_records(self) -> None:
        for risk in ("low", "medium", "high"):
            with self.subTest(risk=risk):
                self.assertEqual(self.validate(evidence_document(risk)), [])

    def test_repository_scope_is_a_nonempty_unique_array_and_links_are_subsets(self) -> None:
        document = evidence_document("low")
        self.assertEqual(self.validate(document), [])

        document["repository_scope"] = []
        self.assertIn("repository_scope", "\n".join(self.validate(document)))

        document = evidence_document("low")
        document["repository_scope"].append(
            dict(document["repository_scope"][0]))
        self.assertIn("duplicate repository_id",
                      "\n".join(self.validate(document)))

        for target in ("requirement_coverage", "checks"):
            with self.subTest(target=target):
                document = evidence_document("low")
                document[target][0]["repository_ids"] = []
                rendered = "\n".join(self.validate(document))
                self.assertIn("repository_ids", rendered)
                self.assertIn("at least 1 item", rendered)

                document[target][0]["repository_ids"] = ["unknown"]
                self.assertIn("unknown repository",
                              "\n".join(self.validate(document)))

    def test_valid_multi_repository_evidence_uses_one_coherent_scope_field(self) -> None:
        document = evidence_document("low")
        document["repository_scope"].append(
            {
                "repository_id": "service",
                "base": "c" * 40,
                "head": "d" * 40,
                "committed_range": f"{'c' * 40}..{'d' * 40}",
                "uncommitted_entries": [],
                "snapshot_sha256": hashlib.sha256(b"[]").hexdigest(),
            }
        )
        document["requirement_coverage"][0]["repository_ids"] = [
            "current", "service"
        ]
        document["checks"][0]["repository_ids"] = ["current", "service"]

        self.assertEqual(self.validate(document), [])
        self.assertNotIn("repositories", document)

    def test_complete_record_rejects_missing_failed_skipped_or_unrun_required_checks(self) -> None:
        cases = ("missing", "failed", "skipped", "not-run")
        for status in cases:
            with self.subTest(status=status):
                document = evidence_document("low")
                if status == "missing":
                    document["checks"] = []
                else:
                    check = document["checks"][0]
                    check["status"] = status
                    if status in ("skipped", "not-run"):
                        check["observed_result"] = None
                        check["evidence_class"] = None
                        check["output_reference"] = None
                rendered = "\n".join(self.validate(document))
                self.assertIn("required", rendered)
                self.assertIn("complete", rendered)

    def test_executed_checks_require_observed_result_and_class(self) -> None:
        document = evidence_document("low")
        check = document["checks"][0]
        check["observed_result"] = None
        check["evidence_class"] = None
        check["output_reference"] = None
        rendered = "\n".join(self.validate(document))
        for field in ("observed_result", "observed evidence"):
            self.assertIn(field, rendered)

    def test_skipped_and_not_run_checks_have_no_observed_evidence_or_output(self) -> None:
        for status in ("skipped", "not-run"):
            with self.subTest(status=status):
                document = evidence_document("low")
                document["lifecycle"]["status"] = "blocked"
                document["lifecycle"]["transition"] = "not-requested"
                check = document["checks"][0]
                check["status"] = status
                check["observed_result"] = "Claimed result"
                check["evidence_class"] = "observed evidence"
                check["output_reference"] = "artifact.txt"
                rendered = "\n".join(self.validate(document))
                self.assertIn("must be null", rendered)

    def test_passed_and_failed_checks_allow_an_optional_output_reference(self) -> None:
        for status in ("passed", "failed"):
            with self.subTest(status=status):
                document = evidence_document("low")
                if status == "failed":
                    document["lifecycle"]["status"] = "blocked"
                    document["lifecycle"]["transition"] = "not-requested"
                    document["review"]["verdict"] = "changes-required"
                document["checks"][0]["status"] = status
                document["checks"][0]["output_reference"] = None
                self.assertEqual(self.validate(document), [])

    def test_checks_reference_known_covered_requirements(self) -> None:
        for requirement_ids, expected in (([], "at least 1 item"), (["UNKNOWN"], "unknown requirement")):
            with self.subTest(requirement_ids=requirement_ids):
                document = evidence_document("low")
                document["checks"][0]["requirement_ids"] = requirement_ids
                self.assertIn(expected, "\n".join(self.validate(document)))

    def test_medium_and_high_risk_completeness_is_enforced(self) -> None:
        medium = evidence_document("medium")
        medium["checks"] = [medium["checks"][0]]
        self.assertIn("regression", "\n".join(self.validate(medium)))
        self.assertIn("failure-path", "\n".join(self.validate(medium)))

        high = evidence_document("high")
        high["review"]["independence"] = "self-review"
        high["review"]["reviewer_role"] = "implementer self-review"
        rendered = "\n".join(self.validate(high))
        self.assertIn("high-risk", rendered)
        self.assertIn("independent", rendered)

    def test_high_blocked_record_cannot_carry_approved_verdict(self) -> None:
        document = evidence_document("high")
        document["lifecycle"].update(
            status="blocked", transition="not-requested")

        rendered = "\n".join(self.validate(document))

        self.assertIn("approved verdict requires lifecycle complete", rendered)

    def test_failed_required_check_cannot_carry_approved_verdict(self) -> None:
        document = evidence_document("low")
        document["checks"][0]["status"] = "failed"
        document["checks"][0]["observed_result"] = "Focused tests failed."

        rendered = "\n".join(self.validate(document))

        self.assertIn(
            "approved verdict requires all applicable required checks to pass",
            rendered,
        )

    def test_medium_independent_review_rejects_prior_implementation(self) -> None:
        document = evidence_document("medium")
        document["review"].update(
            reviewer_role="fresh reviewer",
            reviewer_id="agent-reviewer",
            prior_participation=["implementation"],
            fresh_context=True,
            independence="independent",
            independence_basis="Declared fresh review context.",
        )

        rendered = "\n".join(self.validate(document))

        self.assertIn(
            "independent review prior_participation must exclude implementation",
            rendered,
        )

    def test_self_review_requires_declared_implementation_participation(self) -> None:
        document = evidence_document("medium")
        document["review"]["prior_participation"] = []

        self.assertIn(
            "self-review prior_participation must include implementation",
            "\n".join(self.validate(document)),
        )

    def test_high_independent_review_requires_fresh_non_implementer_declaration(self) -> None:
        mutations = (
            (lambda review: review.update(fresh_context=False), "fresh_context"),
            (
                lambda review: review.update(
                    prior_participation=["implementation"]),
                "prior_participation",
            ),
            (
                lambda review: review.update(reviewer_id="agent-implementer"),
                "reviewer_id",
            ),
            (
                lambda review: review.update(independence_basis=None),
                "independence_basis",
            ),
        )
        for mutate, expected in mutations:
            with self.subTest(expected=expected):
                document = evidence_document("high")
                mutate(document["review"])
                rendered = "\n".join(self.validate(document))
                self.assertIn(expected, rendered)
                self.assertIn("high-risk", rendered)

    def test_implemented_or_verified_scope_must_be_fixed_and_self_consistent(self) -> None:
        cases = (
            (lambda scope: scope.update(head="working-tree"), "immutable"),
            (lambda scope: scope.update(committed_range=None), "committed_range"),
            (lambda scope: scope.update(snapshot_sha256="0" * 64), "snapshot_sha256"),
            (
                lambda scope: scope["uncommitted_entries"][0].update(
                    sha256="pending"),
                "sha256",
            ),
        )
        for mutate, expected in cases:
            with self.subTest(expected=expected):
                document = evidence_document("low")
                mutate(document["repository_scope"][0])
                self.assertIn(expected, "\n".join(self.validate(document)))

    def test_completed_scope_allows_explicit_not_applicable_revisions(self) -> None:
        document = evidence_document("low")
        document["repository_scope"][0].update(
            base="not-applicable",
            head="not-applicable",
            committed_range="not-applicable",
        )
        self.assertEqual(self.validate(document), [])

    def test_in_progress_scope_explicitly_allows_pending_nulls(self) -> None:
        document = evidence_document("low")
        document["lifecycle"] = {
            "status": "in-progress",
            "transition": "not-requested",
            "evidence_references": ["accepted-request"],
        }
        document["repository_scope"] = [
            {
                "repository_id": "current",
                "base": None,
                "head": None,
                "committed_range": None,
                "uncommitted_entries": [],
                "snapshot_sha256": None,
            }
        ]
        document["checks"][0].update(
            status="not-run",
            observed_result=None,
            evidence_class=None,
            output_reference=None,
        )
        document["review"] = {
            "reviewer_role": None,
            "reviewer_id": None,
            "implementers": ["agent-implementer"],
            "prior_participation": [],
            "fresh_context": False,
            "independence": "not-reviewed",
            "independence_basis": None,
            "verdict": "not-reviewed",
            "reference": "review.md",
        }
        self.assertEqual(self.validate(document), [])

    def test_applicability_and_not_applicable_reason_are_consistent(self) -> None:
        document = evidence_document("medium")
        failure_path = next(
            check for check in document["checks"] if check["kind"] == "failure-path"
        )
        failure_path["not_applicable_reason"] = None
        self.assertIn("not_applicable_reason",
                      "\n".join(self.validate(document)))

    def test_unknown_fields_and_ambiguous_types_are_rejected(self) -> None:
        document = evidence_document("low")
        document["unknown"] = True
        document["schema_version"] = True
        rendered = "\n".join(self.validate(document))
        self.assertIn("unknown field", rendered)
        self.assertIn("schema_version", rendered)

    def test_all_machine_strings_reject_nonconcise_or_unsafe_content_without_echo(self) -> None:
        cases = (
            ("token=do-not-echo", "sensitive"),
            ("person@example.test", "personal data"),
            ("line one\nline two", "newline or control"),
            ("control\u0007value", "newline or control"),
            ("x" * 501, "concise"),
            ("ghp_" + "A" * 30, "sensitive"),
            ("github_pat_" + "B" * 30, "sensitive"),
            ("sk-" + "C" * 30, "sensitive"),
        )
        for value, expected in cases:
            with self.subTest(expected=expected):
                document = evidence_document("low")
                document["authoritative_sources"][0]["reference"] = value
                rendered = "\n".join(self.validate(document))
                self.assertIn(expected, rendered)
                self.assertNotIn(value, rendered)

        for tiny_sample in ("ghp_test", "github_pat_demo", "sk-short"):
            with self.subTest(tiny_sample=tiny_sample):
                document = evidence_document("low")
                document["authoritative_sources"][0]["reference"] = tiny_sample
                self.assertEqual(self.validate(document), [])

    def test_repository_module_assets_and_conditional_core_contract(self) -> None:
        module = ROOT / ".agents" / "modules" / "evidence"
        self.assertEqual(validator.validate_evidence_module(module), [])
        starter = json.loads(
            (module / "assets" / "evidence.template.json").read_text(encoding="utf-8")
        )
        self.assertEqual(validator.validate_evidence_document(starter), [])

        multi_repo = ROOT / ".agents" / "modules" / "multi-repo"
        self.assertEqual(validator.validate_multi_repo_module(multi_repo), [])
        self.assertEqual(
            {path.name for path in (multi_repo / "assets").iterdir()},
            {"plan-snippet.md", "tasks-snippet.md",
                "review-snippet.md", "evidence-snippet.json"},
        )
        task_controls = (multi_repo / "assets" / "tasks-snippet.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "Dirty status: clean | dirty-nonconflicting | blocked-conflict | unknown",
            task_controls,
        )
        self.assertIn(
            "Ownership/isolation: exclusive-owner | isolated | blocked-conflict | unknown",
            task_controls,
        )
        self.assertNotIn("<pre-work staged", task_controls)
        checker_source = (ROOT / ".agents" / "modules" / "enforcement" / "check.py").read_text(
            encoding="utf-8"
        )
        checker_tree = ast.parse(checker_source)
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(checker_tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in (node.names if isinstance(node, ast.Import) else [ast.alias(node.module or "")])
        }
        self.assertFalse({"subprocess", "git"} & imported)
        self.assertIn('EXTENSION_VALIDATORS["multi-repo"]', checker_source)

        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8").lower()
        self.assertIn("installed", agents)
        self.assertIn("enabled", agents)
        self.assertIn("recognized `.agents/project.json`", agents)
        self.assertIn("`.agents/project.md`", agents)
        self.assertIn("unsupported", agents)
        self.assertIn("core behavior", agents)
        for skill in ("plan", "decompose-tasks", "implement", "review"):
            text = (
                ROOT / ".agents" / "skills" / skill / "SKILL.md"
            ).read_text(encoding="utf-8").lower()
            self.assertIn("`evidence`", text)
            self.assertIn("module is active", text)
            self.assertIn("module.md", text)

    def test_module_schema_recursively_requires_closed_contractual_definitions(self) -> None:
        source = ROOT / ".agents" / "modules" / "evidence"
        cases = (
            ("check", "additionalProperties", "closed object"),
            ("review", "required", "required fields"),
        )
        for definition, field, expected in cases:
            with self.subTest(definition=definition, field=field):
                temporary = tempfile.TemporaryDirectory()
                self.addCleanup(temporary.cleanup)
                module = Path(temporary.name) / "evidence"
                shutil.copytree(source, module)
                schema_path = module / "assets" / "evidence.schema.json"
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                schema["$defs"][definition].pop(field)
                schema_path.write_text(json.dumps(schema), encoding="utf-8")
                rendered = "\n".join(
                    validator.validate_evidence_module(module))
                self.assertIn(definition, rendered)
                self.assertIn(expected, rendered)

    def test_absent_evidence_module_adds_no_validation_or_core_burden(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        modules_root = Path(temporary.name) / ".agents" / "modules"
        self.assertEqual(
            validator.validate_optional_evidence_module(modules_root), [])


class ComplianceModuleValidationTests(unittest.TestCase):
    def test_repository_compliance_assets_and_templates_pass(self) -> None:
        module = ROOT / ".agents" / "modules" / "compliance"
        self.assertEqual(validator.validate_compliance_module(module), [])
        event = json.loads(
            (module / "assets" / "audit-event.template.json").read_text(
                encoding="utf-8"
            )
        )
        policy = json.loads(
            (module / "assets" / "approval-policy.template.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(validator.validate_compliance_event(event), [])
        self.assertEqual(validator.validate_approval_policy(policy), [])

    def test_compliance_schema_version_const_must_accept_template(self) -> None:
        source = ROOT / ".agents" / "modules" / "compliance"
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        module = Path(temporary.name) / "compliance"
        shutil.copytree(source, module)
        schema_path = module / "assets" / "audit-event.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema["properties"]["schema_version"]["const"] = 2
        schema_path.write_text(json.dumps(schema), encoding="utf-8")

        rendered = "\n".join(validator.validate_compliance_module(module))

        self.assertIn("schema/template compatibility", rendered)
        self.assertIn("schema_version", rendered)

    def test_compliance_policy_schema_version_and_template_shape_are_compatible(self) -> None:
        source = ROOT / ".agents" / "modules" / "compliance"
        cases = (
            (
                "approval-policy.schema.json",
                lambda value: value.update(
                    {"$id": "urn:agentic-sdlc-kit:approval-policy:v2"}
                ),
                "version identifier must be v1",
            ),
            (
                "approval-policy.template.json",
                lambda value: value.update({"unknown": True}),
                "approval policy template is rejected by its schema",
            ),
        )
        for filename, mutate, expected in cases:
            with self.subTest(filename=filename):
                temporary = tempfile.TemporaryDirectory()
                self.addCleanup(temporary.cleanup)
                module = Path(temporary.name) / "compliance"
                shutil.copytree(source, module)
                path = module / "assets" / filename
                value = json.loads(path.read_text(encoding="utf-8"))
                mutate(value)
                path.write_text(json.dumps(value), encoding="utf-8")

                rendered = "\n".join(
                    validator.validate_compliance_module(module)
                )

                self.assertIn("schema/template compatibility", rendered)
                self.assertIn(expected, rendered)

    def test_compliance_validator_recurses_and_rejects_overclaims(self) -> None:
        source = ROOT / ".agents" / "modules" / "compliance"
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        module = Path(temporary.name) / "compliance"
        shutil.copytree(source, module)
        nested = module / "assets" / "nested"
        nested.mkdir()
        (nested / "claim.md").write_text(
            "This module guarantees compliance.", encoding="utf-8"
        )

        rendered = "\n".join(validator.validate_compliance_module(module))

        self.assertIn("overclaim", rendered.lower())
        self.assertIn("claim.md", rendered)

    def test_absent_compliance_module_adds_no_source_validation_burden(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        modules_root = Path(temporary.name) / ".agents" / "modules"
        self.assertEqual(
            validator.validate_optional_compliance_module(modules_root), []
        )


class EnforcementModuleValidationTests(unittest.TestCase):
    def test_repository_enforcement_module_structure_passes(self) -> None:
        module = ROOT / ".agents" / "modules" / "enforcement"
        self.assertEqual(validator.validate_enforcement_module(module), [])

    def test_missing_checker_and_disallowed_import_are_rejected(self) -> None:
        source = ROOT / ".agents" / "modules" / "enforcement"
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        module = Path(temporary.name) / "enforcement"
        shutil.copytree(source, module)
        check = module / "check.py"
        check.unlink()
        self.assertIn(
            "Missing required enforcement module file",
            "\n".join(validator.validate_enforcement_module(module)),
        )
        shutil.copy2(source / "check.py", check)
        check.write_text(check.read_text(encoding="utf-8") +
                         "\nimport subprocess\n", encoding="utf-8")
        self.assertIn(
            "self-contained boundary: subprocess",
            "\n".join(validator.validate_enforcement_module(module)),
        )
        check.write_text(
            (source / "check.py").read_text(encoding="utf-8")
            + "\nimport urllib.request\n",
            encoding="utf-8",
        )
        self.assertIn(
            "network-capable urllib imports are forbidden",
            "\n".join(validator.validate_enforcement_module(module)),
        )

    def test_read_only_ast_boundary_rejects_mutation_and_dynamic_execution(self) -> None:
        source = ROOT / ".agents" / "modules" / "enforcement"
        cases = (
            "os.remove('path')",
            "os.replace('one', 'two')",
            "import os as operating\noperating.unlink('path')",
            "from os import rename as move\nmove('one', 'two')",
            "Path('path').rename('other')",
            "open('path', 'wb')",
            "Path('path').open(mode='a')",
            "exec('pass')",
        )
        for snippet in cases:
            with self.subTest(snippet=snippet):
                temporary = tempfile.TemporaryDirectory()
                self.addCleanup(temporary.cleanup)
                module = Path(temporary.name) / "enforcement"
                shutil.copytree(source, module)
                check = module / "check.py"
                check.write_text(
                    check.read_text(encoding="utf-8") + f"\n{snippet}\n",
                    encoding="utf-8",
                )
                rendered = "\n".join(
                    validator.validate_enforcement_module(module))
                self.assertIn("read-only boundary", rendered)


class CatalogValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = DistributionFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def validate(self) -> list[str]:
        return validator.validate_repository(self.fixture.root)

    def test_valid_catalog_and_distribution_pass(self) -> None:
        self.assertEqual(self.validate(), [])

    def test_setup_template_schema_errors_are_actionable(self) -> None:
        template = (
            self.fixture.root
            / ".agents"
            / "skills"
            / "setup"
            / "assets"
            / "project.template.json"
        )
        template.unlink()
        self.assertTrue(
            any("project.template.json" in error for error in self.validate())
        )

        invalid = json.loads(SETUP_TEMPLATE)
        invalid["enabled_modules"] = "evidence"
        template.write_text(json.dumps(invalid), encoding="utf-8")
        self.assertTrue(
            any(
                "enabled_modules" in error and "closed v2 schema" in error
                for error in self.validate()
            )
        )

    def test_provenance_template_errors_are_actionable(self) -> None:
        skills = self.fixture.root / ".agents" / "skills"
        cases = (
            (
                skills / "write-spec" / "assets" / "spec.template.md",
                "sources:\n  - <source>\n",
                "Spec template missing metadata field: sources:",
            ),
            (
                skills / "write-spec" / "assets" / "spec.template.md",
                "## Confirmed rationale\n",
                "Spec template missing field: ## Confirmed rationale",
            ),
            (
                skills / "plan" / "assets" / "plan.template.md",
                "## Agent inferences\n",
                "Plan template missing field: ## Agent inferences",
            ),
            (
                skills / "plan" / "assets" / "plan.template.md",
                "## Source coverage and impact map\n",
                "Plan template missing field: ## Source coverage and impact map",
            ),
            (
                skills / "decompose-tasks" / "assets" / "tasks.template.md",
                "Execution rationale:\n",
                "Task template missing field: Execution rationale:",
            ),
            (
                skills / "decompose-tasks" / "assets" / "tasks.template.md",
                "Topology decision:\n",
                "Task template missing field: Topology decision:",
            ),
            (
                skills / "decompose-tasks" / "assets" / "tasks.template.md",
                "Contract risk:\n",
                "Task template missing field: Contract risk:",
            ),
            (
                skills / "decompose-tasks" / "assets" / "tasks.template.md",
                "Agent roles:\n",
                "Task template missing field: Agent roles:",
            ),
        )
        for path, field, expected in cases:
            with self.subTest(field=field):
                original = path.read_text(encoding="utf-8")
                path.write_text(original.replace(field, ""), encoding="utf-8")
                try:
                    self.assertTrue(
                        any(expected in error for error in self.validate()),
                        self.validate(),
                    )
                finally:
                    path.write_text(original, encoding="utf-8")

    def test_review_template_errors_are_actionable(self) -> None:
        template = (
            self.fixture.root
            / ".agents"
            / "skills"
            / "review"
            / "assets"
            / "review.template.md"
        )
        for field in (
            "Fixed base:",
            "Fixed head:",
            "Committed range:",
            "Uncommitted scope:",
            "## Reviewer role and independence",
            "Reviewer role:",
            "Independence required:",
            "Independence met:",
            "## Authoritative sources",
            "## Risk",
            "Reviewer-assessed risk:",
            "## Change contract and review focus",
            "Contract risk:",
            "Risk comparison/deviation:",
            "Missing-contract impact:",
            "## Selected quality signals",
            "## Checks and evidence",
            "## Findings",
            "## Acceptance coverage",
            "## Residual risk",
            "## Verdict",
        ):
            with self.subTest(field=field):
                original = template.read_text(encoding="utf-8")
                template.write_text(original.replace(
                    field, "", 1), encoding="utf-8")
                try:
                    self.assertTrue(
                        any(
                            f"Review template missing field: {field}" in error
                            for error in self.validate()
                        ),
                        self.validate(),
                    )
                finally:
                    template.write_text(original, encoding="utf-8")

    def test_review_template_signal_and_option_errors_are_actionable(self) -> None:
        template = (
            self.fixture.root
            / ".agents"
            / "skills"
            / "review"
            / "assets"
            / "review.template.md"
        )
        security_row = "| Security | N/A | no trust boundary | observed evidence |"
        maintainability_row = (
            "| Maintainability | selected | changed source | source-based inference |"
        )
        cases = (
            (
                "| Signal | Disposition | Trigger / N/A reason | Evidence |",
                "| Signal | Choice | Trigger / N/A reason | Evidence |",
                "Review template signal table missing column: Disposition",
            ),
            (
                "| Signal | Disposition | Trigger / N/A reason | Evidence |",
                "| Signal | Disposition | Trigger | Evidence |",
                "Review template signal table missing column: N/A reason",
            ),
            (
                security_row,
                "",
                "Review template missing quality signal row: Security",
            ),
            (
                maintainability_row,
                f"{maintainability_row}\n{maintainability_row}",
                "Review template duplicate quality signal row: Maintainability",
            ),
            (
                "source-based inference",
                "source inference",
                "Review template missing evidence class: source-based inference",
            ),
            (
                "changes-required",
                "change-needed",
                "Review template missing verdict option: changes-required",
            ),
        )
        original = template.read_text(encoding="utf-8")
        for old, new, expected in cases:
            with self.subTest(expected=expected):
                template.write_text(original.replace(
                    old, new), encoding="utf-8")
                try:
                    errors = self.validate()
                    self.assertTrue(
                        any(expected in error for error in errors), errors
                    )
                finally:
                    template.write_text(original, encoding="utf-8")

    def test_review_template_rejects_noncanonical_sets_and_tokens(self) -> None:
        template = (
            self.fixture.root
            / ".agents"
            / "skills"
            / "review"
            / "assets"
            / "review.template.md"
        )
        original = template.read_text(encoding="utf-8")
        cases = (
            (
                "| Understandability | selected | changed source | unverified claim |",
                "| Understandability | selected | changed source | unverified claim |\n"
                "| Reliability | selected | changed source | observed evidence |",
                (
                    "Review template quality signal table must contain exactly 9 data rows",
                    "Review template unknown quality signal row: Reliability",
                ),
            ),
            (
                'Evidence classes: ["observed evidence", "source-based inference", "unverified claim"]',
                'Evidence classes: ["observed evidence", "invalid-class", "unverified claim"]',
                (
                    "Review template evidence classes must be exactly: observed evidence, "
                    "source-based inference, unverified claim",
                ),
            ),
            (
                'Verdict options: ["approved", "changes-required", "blocked"]',
                'Verdict options: ["approved-ish", "changes-required", "blocked"]',
                (
                    "Review template verdict options must be exactly: approved, "
                    "changes-required, blocked",
                ),
            ),
        )
        for old, new, expected_errors in cases:
            with self.subTest(new=new):
                template.write_text(original.replace(
                    old, new), encoding="utf-8")
                try:
                    errors = self.validate()
                    for expected in expected_errors:
                        self.assertTrue(
                            any(expected in error for error in errors), errors
                        )
                finally:
                    template.write_text(original, encoding="utf-8")

    def test_spec_template_accepts_sources_yaml_list_continuations(self) -> None:
        template = (
            self.fixture.root
            / ".agents"
            / "skills"
            / "write-spec"
            / "assets"
            / "spec.template.md"
        )
        original = template.read_text(encoding="utf-8")
        for source_block in (
            "sources:\n  - first\n  - second\n",
            "sources:\n- first\n- second\n",
        ):
            with self.subTest(source_block=source_block):
                template.write_text(
                    original.replace("sources:\n  - <source>\n", source_block),
                    encoding="utf-8",
                )
                self.assertEqual(self.validate(), [])

    def test_spec_sources_in_body_do_not_satisfy_frontmatter_contract(self) -> None:
        template = (
            self.fixture.root
            / ".agents"
            / "skills"
            / "write-spec"
            / "assets"
            / "spec.template.md"
        )
        source_block = "sources:\n  - <source>\n"
        text = template.read_text(encoding="utf-8")
        template.write_text(
            text.replace(source_block, "") + "\n" + source_block,
            encoding="utf-8",
        )

        errors = self.validate()

        self.assertTrue(
            any(
                "Spec template missing metadata field: sources:" in error
                for error in errors
            ),
            errors,
        )

    def test_spec_template_frontmatter_delimiter_errors_are_actionable(self) -> None:
        template = (
            self.fixture.root
            / ".agents"
            / "skills"
            / "write-spec"
            / "assets"
            / "spec.template.md"
        )
        original = template.read_text(encoding="utf-8")
        cases = (
            (original[len("---\n"):], "missing opening YAML frontmatter"),
            (
                original.replace("\n---\n## Confirmed rationale",
                                 "\n## Confirmed rationale"),
                "missing closing YAML frontmatter",
            ),
        )
        for text, expected in cases:
            with self.subTest(expected=expected):
                template.write_text(text, encoding="utf-8")
                errors = self.validate()
                self.assertTrue(
                    any(expected in error for error in errors),
                    errors,
                )

    def test_domain_model_asset_errors_are_actionable(self) -> None:
        assets = (
            self.fixture.root
            / ".agents"
            / "skills"
            / "domain-model"
            / "assets"
        )
        glossary = assets / "glossary.template.md"
        glossary.unlink()

        errors = self.validate()

        self.assertTrue(
            any("glossary.template.md" in error for error in errors), errors
        )

        glossary.write_text(
            "# Domain Context\n\n## Terms\n\nMeaning:\nRelationships:\n",
            encoding="utf-8",
        )
        adr = assets / "adr.template.md"
        adr_text = adr.read_text(encoding="utf-8")
        for heading in (
            "## Confirmed rationale",
            "## Repository evidence",
            "## Agent inference",
            "## Unknowns",
        ):
            adr_text = adr_text.replace(f"{heading}\n", "")
        adr.write_text(adr_text, encoding="utf-8")

        errors = self.validate()

        self.assertTrue(
            any("Rejected ambiguous synonyms:" in error for error in errors), errors
        )
        for heading in (
            "## Confirmed rationale",
            "## Repository evidence",
            "## Agent inference",
            "## Unknowns",
        ):
            self.assertTrue(
                any(
                    f"ADR template missing field: {heading}" in error for error in errors),
                errors,
            )

    def test_setup_template_rejects_malformed_json(self) -> None:
        template = (
            self.fixture.root
            / ".agents"
            / "skills"
            / "setup"
            / "assets"
            / "project.template.json"
        )
        template.write_text('{"schema_version":2,', encoding="utf-8")

        errors = self.validate()

        self.assertTrue(
            any("bounded valid JSON" in error for error in errors), errors
        )

    def test_missing_and_malformed_catalog_are_actionable(self) -> None:
        catalog_path = self.fixture.root / ".agents" / "kit-catalog.json"
        catalog_path.unlink()
        self.assertTrue(
            any("Catalog not found" in error for error in self.validate()))

        catalog_path.write_text("{not-json", encoding="utf-8")
        self.assertTrue(
            any("Malformed catalog JSON" in error for error in self.validate()))

    def test_invalid_schema_fields_and_types_are_actionable(self) -> None:
        cases = (
            (lambda data: data.pop("kit_version"),
             "missing required field 'kit_version'"),
            (lambda data: data.update(schema_version=1), "schema_version must be 2"),
            (lambda data: data.update(unknown=True), "unknown field 'unknown'"),
            (lambda data: data.update(skill_groups=[]),
             "'skill_groups' must be an object"),
            (
                lambda data: data["profiles"]["default"].update(
                    skills="implement"),
                "profiles.default.skills must be an array",
            ),
            (
                lambda data: data.update(
                    modules=[
                        {"name": "evidence", "description": "Evidence", "depends_on": "review"}]
                ),
                "modules[0].depends_on must be an array",
            ),
        )
        for mutate, expected in cases:
            with self.subTest(expected=expected):
                self.fixture.data = copy.deepcopy(catalog())
                mutate(self.fixture.data)
                self.fixture.write_catalog()
                self.assertTrue(
                    any(expected in error for error in self.validate()))

    def test_duplicate_components_are_rejected(self) -> None:
        self.fixture.data["skill_groups"]["utilities"].append("shape-idea")
        self.fixture.write_catalog()

        errors = self.validate()

        self.assertTrue(
            any("duplicate skill component 'shape-idea'" in error for error in errors))

    def test_default_profile_rejects_every_optional_skill(self) -> None:
        self.fixture.data["profiles"]["default"]["skills"].append(
            "domain-model")

        errors = validator.validate_catalog(self.fixture.data)[2]

        self.assertTrue(
            any(
                "default profile includes optional skill 'domain-model'" in error
                for error in errors
            ),
            errors,
        )

    def test_unknown_profile_and_dependency_references_are_rejected(self) -> None:
        self.fixture.data["modules"] = [
            {"name": "evidence", "description": "Evidence records",
                "depends_on": ["missing"]}
        ]
        self.fixture.data["profiles"]["full"]["skills"].append("missing-skill")
        self.fixture.data["profiles"]["full"]["modules"].append("unknown")
        self.fixture.write_catalog()
        self.fixture.add_modules()

        errors = self.validate()

        self.assertTrue(
            any("unknown module dependency 'missing'" in error for error in errors))
        self.assertTrue(
            any("unknown skill 'missing-skill'" in error for error in errors))
        self.assertTrue(
            any("unknown module 'unknown'" in error for error in errors))

    def test_profile_requires_direct_module_dependencies(self) -> None:
        self.fixture.data["modules"] = [
            {"name": "enforcement", "description": "Checks",
                "depends_on": ["evidence"]},
            {"name": "evidence", "description": "Records", "depends_on": []},
        ]
        self.fixture.data["profiles"]["default"]["modules"] = ["enforcement"]
        self.fixture.data["profiles"]["full"]["modules"] = [
            "enforcement",
            "evidence",
        ]

        errors = validator.validate_catalog(self.fixture.data)[2]

        self.assertTrue(
            any(
                "profile 'default' module 'enforcement' requires missing dependency 'evidence'"
                in error
                for error in errors
            )
        )

    def test_profile_requires_transitive_module_dependencies(self) -> None:
        self.fixture.data["modules"] = [
            {"name": "compliance", "description": "Audit",
                "depends_on": ["enforcement"]},
            {"name": "enforcement", "description": "Checks",
                "depends_on": ["evidence"]},
            {"name": "evidence", "description": "Records", "depends_on": []},
        ]
        self.fixture.data["profiles"]["default"]["modules"] = [
            "compliance",
            "enforcement",
        ]
        self.fixture.data["profiles"]["full"]["modules"] = [
            "compliance",
            "enforcement",
            "evidence",
        ]

        errors = validator.validate_catalog(self.fixture.data)[2]

        self.assertTrue(
            any(
                "profile 'default' module 'compliance' requires missing dependency 'evidence'"
                in error
                for error in errors
            )
        )

    def test_module_dependency_cycles_are_rejected(self) -> None:
        self.fixture.data["modules"] = [
            {"name": "evidence", "description": "Evidence",
                "depends_on": ["enforcement"]},
            {"name": "enforcement", "description": "Enforcement",
                "depends_on": ["evidence"]},
        ]
        self.fixture.write_catalog()
        self.fixture.add_modules()

        errors = self.validate()

        self.assertTrue(
            any("module dependency cycle" in error for error in errors))

    def test_missing_declared_and_unexpected_directories_are_rejected(self) -> None:
        shutil.rmtree(self.fixture.root / ".agents" / "skills" / "review")
        unexpected_skill = self.fixture.root / ".agents" / "skills" / "stray-skill"
        unexpected_skill.mkdir()
        (unexpected_skill / "SKILL.md").write_text(
            skill_text("stray-skill"), encoding="utf-8"
        )
        self.fixture.data["modules"] = [
            {"name": "evidence", "description": "Evidence", "depends_on": []}
        ]
        self.fixture.data["profiles"]["full"]["modules"] = ["evidence"]
        self.fixture.write_catalog()
        unexpected_module = self.fixture.root / ".agents" / "modules" / "enforcement"
        unexpected_module.mkdir(parents=True)
        (unexpected_module / "MODULE.md").write_text("# Module\n", encoding="utf-8")

        errors = self.validate()

        self.assertTrue(
            any("declared skill directory is missing: review" in error for error in errors)
        )
        self.assertTrue(
            any("Unexpected skill directory: stray-skill" in error for error in errors)
        )
        self.assertTrue(
            any("declared module directory is missing: evidence" in error for error in errors)
        )
        self.assertTrue(
            any("Unexpected module directory: enforcement" in error for error in errors)
        )

    def test_provider_specific_content_is_rejected(self) -> None:
        skill_file = self.fixture.root / ".agents" / "skills" / "implement" / "SKILL.md"
        skill_file.write_text(skill_text("implement") +
                              "Read .cursor/rules.\n", encoding="utf-8")

        errors = self.validate()

        self.assertTrue(any(
            "provider-specific path" in error and ".cursor/" in error for error in errors))

    def test_circular_symlink_reference_returns_one_without_traceback(self) -> None:
        skill_dir = self.fixture.root / ".agents" / "skills" / "implement"
        (skill_dir / "SKILL.md").write_text(
            skill_text("implement") + "[Loop](loop)\n", encoding="utf-8"
        )
        (skill_dir / "loop").symlink_to("loop")
        output = io.StringIO()
        error_output = io.StringIO()

        with redirect_stdout(output), redirect_stderr(error_output):
            result = validator.main(self.fixture.root)

        self.assertEqual(result, 1)
        self.assertIn("cannot resolve local reference", output.getvalue())
        self.assertIn("loop", output.getvalue())
        self.assertNotIn("Traceback", error_output.getvalue())

    def test_catalog_json_recursion_error_returns_one_without_traceback(self) -> None:
        output = io.StringIO()
        error_output = io.StringIO()

        with mock.patch.object(validator.json, "loads", side_effect=RecursionError):
            with redirect_stdout(output), redirect_stderr(error_output):
                result = validator.main(self.fixture.root)

        self.assertEqual(result, 1)
        self.assertIn("catalog JSON nesting is too deep", output.getvalue())
        self.assertNotIn("Traceback", error_output.getvalue())

    def test_deep_module_graphs_return_without_recursion_failure(self) -> None:
        names = [f"module-{index}" for index in range(1100)]
        for cyclic in (False, True):
            with self.subTest(cyclic=cyclic):
                modules = []
                for index, name in enumerate(names):
                    dependencies = [names[index + 1]
                                    ] if index + 1 < len(names) else []
                    if cyclic and index + 1 == len(names):
                        dependencies = [names[0]]
                    modules.append(
                        {
                            "name": name,
                            "description": f"Module {index}",
                            "depends_on": dependencies,
                        }
                    )
                self.fixture.data["modules"] = modules
                self.fixture.data["profiles"]["full"]["modules"] = names
                self.fixture.write_catalog()
                self.fixture.add_modules()
                output = io.StringIO()
                error_output = io.StringIO()

                with redirect_stdout(output), redirect_stderr(error_output):
                    result = validator.main(self.fixture.root)

                self.assertEqual(result, 1 if cyclic else 0)
                self.assertNotIn("Traceback", error_output.getvalue())
                if cyclic:
                    self.assertIn("module dependency cycle", output.getvalue())

    def test_main_prints_clear_messages_and_returns_zero_or_one(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            success = validator.main(self.fixture.root)
        self.assertEqual(success, 0)
        self.assertIn("Validation passed", output.getvalue())

        (self.fixture.root / ".agents" /
         "kit-catalog.json").write_text("{", encoding="utf-8")
        output = io.StringIO()
        with redirect_stdout(output):
            failure = validator.main(self.fixture.root)
        self.assertEqual(failure, 1)
        self.assertIn("Validation failed", output.getvalue())
        self.assertIn("Malformed catalog JSON", output.getvalue())


class SOAHarnessEvolutionTests(unittest.TestCase):
    def test_conventions_rubrics_and_shape_a_templates_validate(self) -> None:
        from scripts.contracts.conventions import (
            EXPECTED_CONVENTIONS,
            EXPECTED_JUDGE_RUBRICS,
            EXPECTED_JUEZ_RUBRICS,
            STATUSES_A,
            TYPES_A,
            validate_conventions_and_rubrics,
        )

        self.assertEqual(validate_conventions_and_rubrics(ROOT), [])
        self.assertEqual(len(EXPECTED_CONVENTIONS), 13)
        self.assertEqual(len(EXPECTED_JUDGE_RUBRICS), 6)
        self.assertEqual(len(EXPECTED_JUEZ_RUBRICS), 4)
        self.assertEqual(
            TYPES_A,
            {
                "user-persona",
                "user-journey",
                "user-story",
                "spec",
                "adr",
                "decision",
                "business-context",
                "plan",
                "tasks",
                "estimate",
            },
        )
        self.assertEqual(
            STATUSES_A,
            {
                "draft",
                "review",
                "needs-work",
                "approved",
                "implemented",
                "archived",
                "superseded",
                "legacy-pending-review",
            },
        )

    def test_soa_process_chain_skills_and_juez_rubrics_exist(self) -> None:
        skills_dir = ROOT / ".agents" / "skills"
        for name in (
            "drill-docs",
            "save-output",
            "judge-spec",
            "plan-feature",
            "breakdown-tasks",
            "implement",
            "close-spec",
            "git-conventions",
            "agents-creator",
            "estimate-effort",
        ):
            with self.subTest(skill=name):
                self.assertEqual(validator.validate_skill(skills_dir / name), [])

        for rubric in (
            "rubric-spec.md",
            "rubric-user-journey.md",
            "rubric-user-story.md",
            "rubric-adr.md",
            "rubric-plan.md",
            "rubric-tasks.md",
        ):
            path = skills_dir / "judge-spec" / rubric
            self.assertTrue(path.is_file())
            self.assertIn("Block on fail?", path.read_text(encoding="utf-8"))

        for stack in ("python.md", "node-ts.md", "java.md", "frontend.md"):
            path = skills_dir / "implement" / "rubrics" / stack
            self.assertTrue(path.is_file())
            text = path.read_text(encoding="utf-8")
            self.assertIn("APROBADO", text)
            self.assertIn("RECHAZADO", text)

        lanes = (ROOT / ".agents" / "conventions" / "change-lanes.md").read_text(
            encoding="utf-8"
        )
        for tier in ("**XS**", "**S**", "**M**", "**L**", "**XL**"):
            self.assertIn(tier, lanes)
        self.assertIn("Lightweight", lanes)
        self.assertIn("Spec", lanes)

    def test_independent_160_point_committee_invariants(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Code as Source of Truth, Spec as Delta", agents)

        conventions = (
            ROOT / ".agents" / "conventions" / "conventions.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Delta contract", conventions)

        recipes = (
            ROOT / ".agents" / "conventions" / "loading-recipes.md"
        ).read_text(encoding="utf-8")
        for required in (
            "Universal context discovery",
            "Iterative Retrieval",
            "Search-First",
            "Zero Duplication",
            "OSV.dev",
        ):
            self.assertIn(required, recipes)

        runtimes = (
            ROOT / ".agents" / "conventions" / "runtimes.md"
        ).read_text(encoding="utf-8")
        for flag in ("--repo", "--tasks", "--only-autonomous", "instincts"):
            self.assertIn(flag, runtimes)

        plan_skill = (
            ROOT / ".agents" / "skills" / "plan-feature" / "SKILL.md"
        ).read_text(encoding="utf-8")
        for ring in ("Ring 1", "Ring 2", "Ring 3", "Search-First"):
            self.assertIn(ring, plan_skill)

        implement_skill = (
            ROOT / ".agents" / "skills" / "implement" / "SKILL.md"
        ).read_text(encoding="utf-8")
        for token in (
            "3-Ring Verification",
            "--repo",
            "--tasks",
            "--only-autonomous",
            "Zero Duplication",
        ):
            self.assertIn(token, implement_skill)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for section in (
            "Code as Source of Truth, Spec as Delta",
            "Universal Context Discovery",
            "Zero-Invention Companions",
            "3-Ring Verification",
            ".agents/conventions/",
        ):
            self.assertIn(section, readme)


if __name__ == "__main__":
    unittest.main()

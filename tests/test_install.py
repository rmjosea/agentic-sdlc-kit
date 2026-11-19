from __future__ import annotations

import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.contracts import schema


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "kit_install", ROOT / "scripts" / "install.py")
assert SPEC and SPEC.loader
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class TTYStringIO(io.StringIO):
    def isatty(self) -> bool:
        return True


class InterruptingTTY(TTYStringIO):
    def readline(self, *args: object, **kwargs: object) -> str:
        raise KeyboardInterrupt()


class InstallFixture:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.kit = self.root / "kit"
        self.target = self.root / "target"
        (self.kit / ".agents" / "skills").mkdir(parents=True)
        (self.kit / ".agents" / "modules").mkdir(parents=True)
        self.target.mkdir()
        subprocess.run(
            ["git", "init", "--quiet", str(self.target)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        (self.kit / "AGENTS.md").write_text("# Kit contract\n", encoding="utf-8")
        for name in ("core", "extra"):
            skill = self.kit / ".agents" / "skills" / name
            skill.mkdir()
            (skill / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
        for name in ("base", "addon"):
            module = self.kit / ".agents" / "modules" / name
            module.mkdir()
            (module / "MODULE.md").write_text(f"# {name}\n", encoding="utf-8")
        self.catalog = {
            "schema_version": 2,
            "kit_version": "2.1.0",
            "skill_groups": {
                "core": ["core"],
                "utilities": [],
                "optional": ["extra"],
            },
            "modules": [
                {"name": "base", "description": "Base", "depends_on": []},
                {
                    "name": "addon",
                    "description": "Addon",
                    "depends_on": ["base"],
                },
            ],
            "global_resources": ["AGENTS.md", ".agents/kit-catalog.json"],
            "profiles": {
                "default": {"skills": ["core"], "modules": []},
                "full": {
                    "skills": ["core", "extra"],
                    "modules": ["base", "addon"],
                },
            },
        }
        self.write_catalog()

    def write_catalog(self) -> None:
        (self.kit / ".agents" / "kit-catalog.json").write_text(
            json.dumps(self.catalog), encoding="utf-8"
        )

    def run(self, *arguments: str, **kwargs: object) -> tuple[int, str]:
        output = kwargs.pop("output_stream", io.StringIO())
        result = installer.main(
            [str(self.target), *arguments],
            kit_root=self.kit,
            input_stream=kwargs.pop("input_stream", io.StringIO()),
            output_stream=output,
            interactive=kwargs.pop("interactive", False),
            failure_injector=kwargs.pop("failure_injector", None),
        )
        if kwargs:
            raise AssertionError(f"unused arguments: {kwargs}")
        return result, output.getvalue()

    def manifest(self) -> dict[str, object]:
        return json.loads(
            (self.target / ".agents" / "agentic-sdlc-kit.json").read_text(
                encoding="utf-8"
            )
        )

    def catalog_manifest_record(self) -> dict[str, str]:
        catalog = self.target / ".agents" / "kit-catalog.json"
        return {"path": ".agents/kit-catalog.json", "ownership": "managed", "sha256": installer.hash_path(catalog)}

    def close(self) -> None:
        self.temporary.cleanup()


class SelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = InstallFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_non_interactive_default_is_catalog_profile_not_directory_scan(self) -> None:
        stray = self.fixture.kit / ".agents" / "skills" / "stray"
        stray.mkdir()
        (stray / "SKILL.md").write_text("# stray\n", encoding="utf-8")

        result, output = self.fixture.run()

        self.assertEqual(result, 0)
        self.assertTrue((self.fixture.target / ".agents" /
                        "skills" / "core").is_dir())
        self.assertFalse((self.fixture.target / ".agents" /
                         "skills" / "extra").exists())
        self.assertFalse((self.fixture.target / ".agents" /
                         "skills" / "stray").exists())
        self.assertIn("Profile: default", output)
        self.assertIn("Skills: core", output)

    def test_profile_and_with_select_equivalent_components_and_dependencies(self) -> None:
        result, output = self.fixture.run("--with", "addon", "--with", "extra")

        self.assertEqual(result, 0)
        self.assertTrue((self.fixture.target / ".agents" /
                        "skills" / "extra").is_dir())
        self.assertTrue((self.fixture.target / ".agents" /
                        "modules" / "addon").is_dir())
        self.assertTrue((self.fixture.target / ".agents" /
                        "modules" / "base").is_dir())
        self.assertIn("Dependencies expanded: addon -> base", output)

        other = self.fixture.root / "other"
        other.mkdir()
        subprocess.run(["git", "init", "--quiet", str(other)], check=True)
        self.fixture.target = other
        result, output = self.fixture.run("--profile", "full")
        self.assertEqual(result, 0)
        self.assertIn("Modules: addon, base", output)

    def test_with_accepts_comma_separated_components(self) -> None:
        result, output = self.fixture.run("--with", "extra,addon")

        self.assertEqual(result, 0)
        self.assertIn("Skills: core, extra", output)
        self.assertIn("Modules: addon, base", output)

    def test_tty_menu_accepts_component_number(self) -> None:
        result, output = self.fixture.run(
            input_stream=TTYStringIO("1\n"),
            output_stream=TTYStringIO(),
            interactive=True,
        )

        self.assertEqual(result, 0)
        self.assertIn("Modules: addon, base", output)
        self.assertFalse((self.fixture.target / ".agents" /
                         "skills" / "extra").exists())

    def test_numeric_component_name_takes_precedence_over_index(self) -> None:
        numeric = self.fixture.kit / ".agents" / "skills" / "2"
        numeric.mkdir()
        (numeric / "SKILL.md").write_text("# numeric\n", encoding="utf-8")
        self.fixture.catalog["skill_groups"]["optional"].append("2")
        self.fixture.write_catalog()

        result, output = self.fixture.run(
            input_stream=TTYStringIO("2\n"),
            output_stream=TTYStringIO(),
            interactive=True,
        )

        self.assertEqual(result, 0)
        self.assertIn("Skills: 2, core", output)
        self.assertIn("Use #N to select by index", output)
        self.assertFalse((self.fixture.target / ".agents" /
                         "modules" / "addon").exists())

    def test_hash_number_selects_index_when_numeric_name_exists(self) -> None:
        numeric = self.fixture.kit / ".agents" / "skills" / "2"
        numeric.mkdir()
        (numeric / "SKILL.md").write_text("# numeric\n", encoding="utf-8")
        self.fixture.catalog["skill_groups"]["optional"].append("2")
        self.fixture.write_catalog()

        result, output = self.fixture.run(
            input_stream=TTYStringIO("#2\n"),
            output_stream=TTYStringIO(),
            interactive=True,
        )

        self.assertEqual(result, 0)
        self.assertIn("Modules: addon, base", output)
        self.assertFalse(
            (self.fixture.target / ".agents" / "skills" / "2").exists())

    def test_plain_number_remains_index_without_numeric_name(self) -> None:
        result, output = self.fixture.run(
            input_stream=TTYStringIO("2\n"),
            output_stream=TTYStringIO(),
            interactive=True,
        )

        self.assertEqual(result, 0)
        self.assertIn("Modules: base", output)
        self.assertFalse((self.fixture.target / ".agents" /
                         "skills" / "extra").exists())

    def test_shared_transitive_dependencies_are_reported_deterministically(self) -> None:
        additions = (
            {"name": "leaf", "description": "Leaf", "depends_on": []},
            {"name": "shared", "description": "Shared",
                "depends_on": ["leaf"]},
            {"name": "alpha", "description": "Alpha",
                "depends_on": ["shared"]},
            {"name": "beta", "description": "Beta", "depends_on": ["shared"]},
        )
        self.fixture.catalog["modules"].extend(additions)
        for module in additions:
            source = self.fixture.kit / ".agents" / "modules" / module["name"]
            source.mkdir()
            (source / "MODULE.md").write_text(
                f"# {module['name']}\n", encoding="utf-8"
            )
        self.fixture.write_catalog()

        result, output = self.fixture.run("--with", "alpha,beta")

        self.assertEqual(result, 0)
        self.assertIn("Modules: alpha, beta, leaf, shared", output)
        self.assertIn(
            "Dependencies expanded: alpha -> shared, beta -> shared, shared -> leaf",
            output,
        )

    def test_catalog_rejects_unknown_dependency_and_cycle(self) -> None:
        mutations = (
            lambda data: data["modules"][1].update(depends_on=["missing"]),
            lambda data: data["modules"][0].update(depends_on=["addon"]),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                fixture = InstallFixture()
                try:
                    mutate(fixture.catalog)
                    fixture.write_catalog()

                    result, output = fixture.run()

                    self.assertEqual(result, 2)
                    self.assertIn("catalog", output.lower())
                    self.assertFalse((fixture.target / ".agents").exists())
                finally:
                    fixture.close()

    def test_tty_menu_selects_extras_and_prints_final_selection(self) -> None:
        unused = self.fixture.kit / ".agents" / "skills" / "unused"
        unused.mkdir()
        (unused / "SKILL.md").write_text("# unused\n", encoding="utf-8")
        self.fixture.catalog["skill_groups"]["optional"].append("unused")
        self.fixture.write_catalog()

        result, output = self.fixture.run(
            input_stream=TTYStringIO("extra,addon\n"),
            output_stream=TTYStringIO(),
            interactive=True,
        )

        self.assertEqual(result, 0)
        self.assertIn(
            "Final selection:\n"
            "- Skills: core, extra\n"
            "- Modules: addon, base\n"
            "Dependencies expanded: addon -> base\n",
            output,
        )
        skills = self.fixture.target / ".agents" / "skills"
        modules = self.fixture.target / ".agents" / "modules"
        self.assertEqual({path.name for path in skills.iterdir()}, {
                         "core", "extra"})
        self.assertEqual({path.name for path in modules.iterdir()}, {
                         "addon", "base"})
        self.assertFalse((skills / "unused").exists())
        self.assertEqual(
            self.fixture.manifest(),
            {
                "schema_version": 2,
                "kit_version": "2.1.0",
                "request": {"profile": "default", "explicit_components": ["addon", "extra"]},
                "components": [
                    {
                        "kind": "module",
                        "name": name,
                        "path": f".agents/modules/{name}",
                        "ownership": "managed",
                        "sha256": installer.hash_path(modules / name),
                    }
                    for name in ("addon", "base")
                ]
                + [
                    {
                        "kind": "skill",
                        "name": name,
                        "path": f".agents/skills/{name}",
                        "ownership": "managed",
                        "sha256": installer.hash_path(skills / name),
                    }
                    for name in ("core", "extra")
                ],
                "global_resources": [
                    {
                        "path": ".agents/kit-catalog.json",
                        "ownership": "managed",
                        "sha256": installer.hash_path(
                            self.fixture.target / ".agents" / "kit-catalog.json"
                        ),
                    },
                    {
                        "path": "AGENTS.md",
                        "ownership": "managed",
                        "sha256": installer.hash_path(self.fixture.target / "AGENTS.md"),
                    },
                ],
            },
        )

    def test_keyboard_interrupt_in_menu_cancels_without_changes(self) -> None:
        result, output = self.fixture.run(
            input_stream=InterruptingTTY(),
            output_stream=TTYStringIO(),
            interactive=True,
        )

        self.assertEqual(result, 130)
        self.assertIn("cancelled", output.lower())
        self.assertEqual(list(self.fixture.target.iterdir()),
                         [self.fixture.target / ".git"])

    def test_unknown_profile_or_component_fails_before_writing(self) -> None:
        for arguments in (("--profile", "missing"), ("--with", "missing")):
            with self.subTest(arguments=arguments):
                result, output = self.fixture.run(*arguments)
                self.assertEqual(result, 2)
                self.assertIn("unknown", output.lower())
                self.assertEqual(list(self.fixture.target.iterdir()), [
                                 self.fixture.target / ".git"])


class RepositoryProfileTests(unittest.TestCase):
    def install_repository_profile(self, *arguments: str) -> tuple[Path, dict[str, object]]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        target = (Path(temporary.name) / "target").resolve()
        target.mkdir()
        subprocess.run(
            ["git", "init", "--quiet", str(target)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        result = installer.main(
            [str(target), *arguments],
            kit_root=ROOT,
            input_stream=io.StringIO(),
            output_stream=io.StringIO(),
            interactive=False,
        )
        self.assertEqual(result, 0)
        manifest = json.loads(
            (target / ".agents" / "agentic-sdlc-kit.json").read_text(
                encoding="utf-8"
            )
        )
        return target, manifest

    def test_repository_default_profile_excludes_optional_domain_model(self) -> None:
        target, manifest = self.install_repository_profile()

        skills = target / ".agents" / "skills"
        self.assertEqual(
            len([path for path in skills.iterdir() if path.is_dir()]), 13)
        self.assertFalse((skills / "domain-model").exists())
        installed = {
            item["name"]
            for item in manifest["components"]
            if item["kind"] == "skill"
        }
        self.assertEqual(len(installed), 13)
        self.assertIn("contribute", installed)
        self.assertNotIn("domain-model", installed)
        for module_name in ("evidence", "enforcement", "multi-repo", "compliance"):
            self.assertFalse(
                (target / ".agents" / "modules" / module_name).exists())
            self.assertFalse(
                any(
                    item["kind"] == "module" and item["name"] == module_name
                    for item in manifest["components"]
                )
            )

    def test_repository_full_profile_installs_and_manifests_domain_model(self) -> None:
        target, manifest = self.install_repository_profile("--profile", "full")

        domain_model = target / ".agents" / "skills" / "domain-model"
        self.assertTrue((domain_model / "SKILL.md").is_file())
        self.assertTrue((domain_model / "assets" /
                        "glossary.template.md").is_file())
        self.assertTrue((domain_model / "assets" /
                        "adr.template.md").is_file())
        record = next(
            item
            for item in manifest["components"]
            if item["kind"] == "skill" and item["name"] == "domain-model"
        )
        self.assertEqual(record["path"], ".agents/skills/domain-model")
        self.assertEqual(record["sha256"], installer.hash_path(domain_model))

        evidence = target / ".agents" / "modules" / "evidence"
        self.assertTrue((evidence / "MODULE.md").is_file())
        self.assertTrue(
            (evidence / "assets" / "evidence.schema.json").is_file())
        self.assertTrue(
            (evidence / "assets" / "evidence.template.json").is_file())
        evidence_record = next(
            item
            for item in manifest["components"]
            if item["kind"] == "module" and item["name"] == "evidence"
        )
        self.assertEqual(evidence_record["path"], ".agents/modules/evidence")
        self.assertEqual(
            evidence_record["sha256"], installer.hash_path(evidence))

        enforcement = target / ".agents" / "modules" / "enforcement"
        self.assertTrue((enforcement / "MODULE.md").is_file())
        self.assertTrue((enforcement / "check.py").is_file())
        enforcement_record = next(
            item
            for item in manifest["components"]
            if item["kind"] == "module" and item["name"] == "enforcement"
        )
        self.assertEqual(
            enforcement_record["path"], ".agents/modules/enforcement")
        self.assertEqual(
            enforcement_record["sha256"], installer.hash_path(enforcement))

        multi_repo = target / ".agents" / "modules" / "multi-repo"
        self.assertTrue((multi_repo / "MODULE.md").is_file())
        self.assertEqual(
            {path.name for path in (multi_repo / "assets").iterdir()},
            {"plan-snippet.md", "tasks-snippet.md",
                "review-snippet.md", "evidence-snippet.json"},
        )
        multi_repo_record = next(
            item
            for item in manifest["components"]
            if item["kind"] == "module" and item["name"] == "multi-repo"
        )
        self.assertEqual(
            multi_repo_record["path"], ".agents/modules/multi-repo"
        )
        self.assertEqual(
            multi_repo_record["sha256"], installer.hash_path(multi_repo)
        )

        compliance = target / ".agents" / "modules" / "compliance"
        self.assertTrue((compliance / "MODULE.md").is_file())
        self.assertEqual(
            {path.name for path in (compliance / "assets").iterdir()},
            {
                "audit-event.schema.json",
                "audit-event.template.json",
                "approval-policy.schema.json",
                "approval-policy.template.json",
                "v2",
            },
        )
        self.assertEqual(
            {path.name for path in (compliance / "assets" / "v2").iterdir()},
            {"audit-event.v2.schema.json", "audit-event.v2.template.json"},
        )
        compliance_record = next(
            item
            for item in manifest["components"]
            if item["kind"] == "module" and item["name"] == "compliance"
        )
        self.assertEqual(
            compliance_record["sha256"], installer.hash_path(compliance)
        )

    def test_compliance_selector_expands_evidence_and_enforcement(self) -> None:
        target, manifest = self.install_repository_profile(
            "--with", "compliance")

        installed = {
            item["name"]
            for item in manifest["components"]
            if item["kind"] == "module"
        }
        self.assertEqual(installed, {"compliance", "evidence", "enforcement"})
        self.assertFalse(
            (target / ".agents" / "modules" / "multi-repo").exists())

    def test_default_and_full_installs_preserve_the_same_agents_bootstrap_contract(self) -> None:
        source_agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertFalse((ROOT / ".agents" / "README.md").exists())
        for arguments, expected_skills, expected_modules in (
            ((), 13, 0),
            (("--profile", "full"), 20, 4),
        ):
            with self.subTest(arguments=arguments):
                target, manifest = self.install_repository_profile(*arguments)
                installed_agents = (
                    target / "AGENTS.md").read_text(encoding="utf-8")
                self.assertEqual(installed_agents, source_agents)
                for pointer in (
                    ".agents/kit-catalog.json",
                    ".agents/skills/<name>/SKILL.md",
                    ".agents/project.md",
                    ".agents/agentic-sdlc-kit.json",
                    ".agents/modules/<name>/MODULE.md",
                    ".agents/modules/enforcement/check.py",
                ):
                    self.assertIn(pointer, installed_agents)

                skills = target / ".agents" / "skills"
                modules = target / ".agents" / "modules"
                self.assertEqual(
                    len([path for path in skills.iterdir() if path.is_dir()]),
                    expected_skills,
                )
                self.assertTrue((skills / "setup" / "SKILL.md").is_file())
                self.assertTrue((skills / "ask-kit" / "SKILL.md").is_file())
                self.assertTrue((skills / "contribute" / "SKILL.md").is_file())
                self.assertTrue(
                    (skills / "contribute" / "scripts" / "check_contribution.py").is_file())
                self.assertEqual(
                    (skills / "domain-model").is_dir(), expected_skills == 20)
                installed_modules = (
                    [path for path in modules.iterdir() if path.is_dir()]
                    if modules.exists()
                    else []
                )
                self.assertEqual(len(installed_modules), expected_modules)
                self.assertFalse((target / ".agents" / "project.md").exists())
                self.assertFalse(
                    (target / ".agents" / "project.json").exists())
                self.assertFalse((target / ".agents" / "README.md").exists())

                managed_paths = {item["path"]
                                 for item in manifest["global_resources"]}
                component_paths = {
                    item["path"] for item in manifest["components"]
                }
                self.assertIn("AGENTS.md", managed_paths)
                self.assertIn(".agents/kit-catalog.json", managed_paths)
                self.assertNotIn(".agents/project.md",
                                 managed_paths | component_paths)
                self.assertNotIn(".agents/project.json",
                                 managed_paths | component_paths)


class InstallationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = InstallFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_clean_install_writes_contract_components_and_deterministic_manifest(self) -> None:
        result, output = self.fixture.run()

        self.assertEqual(result, 0)
        self.assertEqual(
            (self.fixture.target / "AGENTS.md").read_text(encoding="utf-8"),
            "# Kit contract\n",
        )
        manifest = self.fixture.manifest()
        self.assertEqual(manifest["schema_version"], 2)
        self.assertEqual(manifest["kit_version"], "2.1.0")
        self.assertEqual(manifest["request"], {
                         "profile": "default", "explicit_components": []})
        self.assertEqual(
            manifest["components"],
            [
                {
                    "kind": "skill",
                    "name": "core",
                    "path": ".agents/skills/core",
                    "ownership": "managed",
                    "sha256": installer.hash_path(
                        self.fixture.target / ".agents" / "skills" / "core"
                    ),
                }
            ],
        )
        self.assertEqual(
            manifest["global_resources"],
            [
                {
                    "path": ".agents/kit-catalog.json",
                    "ownership": "managed",
                    "sha256": installer.hash_path(
                        self.fixture.target / ".agents" / "kit-catalog.json"
                    ),
                },
                {
                    "path": "AGENTS.md",
                    "ownership": "managed",
                    "sha256": installer.hash_path(self.fixture.target / "AGENTS.md"),
                },
            ],
        )
        self.assertIn("Applied successfully", output)

    def test_v2_manifest_validates_on_fresh_rerun_and_project_owned_keep(self) -> None:
        manifest_schema = json.loads(
            (ROOT / ".agents/schemas/manifest.schema.json").read_text(encoding="utf-8"))
        catalog_schema = json.loads(
            (ROOT / ".agents/schemas/kit-catalog.schema.json").read_text(encoding="utf-8"))
        self.assertTrue(schema.validate(
            self.fixture.catalog, catalog_schema).valid)
        self.assertEqual(self.fixture.run()[0], 0)
        for run_arguments in ((), ()):
            with self.subTest(run_arguments=run_arguments):
                self.assertEqual(self.fixture.run(*run_arguments)[0], 0)
                manifest = self.fixture.manifest()
                self.assertTrue(schema.validate(
                    manifest, manifest_schema).valid)

        destination = self.fixture.target / ".agents/skills/core"
        (destination / "SKILL.md").write_text("project-owned\n", encoding="utf-8")
        self.assertEqual(self.fixture.run("--on-conflict", "keep")[0], 0)
        manifest = self.fixture.manifest()
        self.assertTrue(schema.validate(manifest, manifest_schema).valid)
        self.assertEqual(manifest["components"][0]
                         ["ownership"], "project-owned")

    def test_catalog_is_managed_with_agents_and_available_after_install(self) -> None:
        result, output = self.fixture.run()
        self.assertEqual(result, 0, output)
        source = self.fixture.kit / ".agents" / "kit-catalog.json"
        destination = self.fixture.target / ".agents" / "kit-catalog.json"
        self.assertEqual(destination.read_bytes(), source.read_bytes())
        self.assertEqual(
            self.fixture.manifest()["global_resources"],
            [
                {"path": ".agents/kit-catalog.json", "ownership": "managed",
                    "sha256": installer.hash_path(destination)},
                {"path": "AGENTS.md", "ownership": "managed", "sha256": installer.hash_path(
                    self.fixture.target / "AGENTS.md")},
            ],
        )

    def test_legacy_manifest_migrates_catalog_management_idempotently(self) -> None:
        self.assertEqual(self.fixture.run()[0], 0)
        manifest_path = self.fixture.target / ".agents" / "agentic-sdlc-kit.json"
        manifest = self.fixture.manifest()
        manifest["global_resources"] = [
            item for item in manifest["global_resources"] if item["path"] == "AGENTS.md"
        ]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        catalog = self.fixture.target / ".agents" / "kit-catalog.json"
        catalog.unlink()

        result, output = self.fixture.run()
        self.assertEqual(result, 0, output)
        self.assertIn("copy: .agents/kit-catalog.json", output)
        before = (catalog.stat().st_mtime_ns, manifest_path.stat().st_mtime_ns)
        result, output = self.fixture.run()
        self.assertEqual(result, 0, output)
        self.assertEqual(before, (catalog.stat().st_mtime_ns,
                         manifest_path.stat().st_mtime_ns))
        self.assertIn("unchanged: .agents/kit-catalog.json", output)

    def test_untouched_managed_catalog_updates_safely(self) -> None:
        self.assertEqual(self.fixture.run()[0], 0)
        catalog = self.fixture.target / ".agents" / "kit-catalog.json"
        self.fixture.catalog["kit_version"] = "9.2.0"
        self.fixture.write_catalog()

        result, output = self.fixture.run()
        self.assertEqual(result, 0, output)
        self.assertIn("update: .agents/kit-catalog.json", output)
        self.assertEqual(
            json.loads(catalog.read_text(encoding="utf-8"))["kit_version"],
            "9.2.0",
        )
        record = next(
            item for item in self.fixture.manifest()["global_resources"]
            if item["path"] == ".agents/kit-catalog.json"
        )
        self.assertEqual(record["sha256"], installer.hash_path(catalog))

    def test_unmanaged_catalog_conflict_requires_replace_and_keep_cannot_finish(self) -> None:
        agents = self.fixture.target / ".agents"
        agents.mkdir()
        catalog = agents / "kit-catalog.json"
        catalog.write_text('{"project":"catalog"}\n', encoding="utf-8")

        result, output = self.fixture.run()
        self.assertEqual(result, 1)
        self.assertIn("conflict", output.lower())
        self.assertFalse((self.fixture.target / "AGENTS.md").exists())
        self.assertEqual(catalog.read_text(encoding="utf-8"),
                         '{"project":"catalog"}\n')

        result, output = self.fixture.run("--on-conflict", "keep")
        self.assertEqual(result, 1)
        self.assertIn("canonical catalog", output.lower())
        result, output = self.fixture.run("--on-conflict", "replace")
        self.assertEqual(result, 0, output)
        self.assertEqual(
            catalog.read_bytes(),
            (self.fixture.kit / ".agents" / "kit-catalog.json").read_bytes(),
        )

    def test_dry_run_calculates_actions_without_writing(self) -> None:
        result, output = self.fixture.run("--dry-run")

        self.assertEqual(result, 0)
        self.assertIn("copy: .agents/skills/core", output)
        self.assertIn("Dry run complete", output)
        self.assertEqual(list(self.fixture.target.iterdir()),
                         [self.fixture.target / ".git"])

    def test_existing_command_line_usage_remains_supported(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "install.py"),
                str(self.fixture.target),
                "--dry-run",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Profile: default", completed.stdout)
        self.assertFalse((self.fixture.target / ".agents").exists())

    def test_idempotent_install_does_not_mutate_managed_content(self) -> None:
        self.assertEqual(self.fixture.run()[0], 0)
        skill = self.fixture.target / ".agents" / "skills" / "core" / "SKILL.md"
        manifest = self.fixture.target / ".agents" / "agentic-sdlc-kit.json"
        before = (skill.stat().st_mtime_ns,
                  manifest.stat().st_mtime_ns, manifest.read_bytes())

        result, output = self.fixture.run()

        after = (skill.stat().st_mtime_ns,
                 manifest.stat().st_mtime_ns, manifest.read_bytes())
        self.assertEqual(result, 0)
        self.assertEqual(before, after)
        self.assertIn("unchanged: .agents/skills/core", output)

    def test_intact_managed_component_and_agents_are_updated_safely(self) -> None:
        self.assertEqual(self.fixture.run()[0], 0)
        (self.fixture.kit / ".agents" / "skills" / "core" / "SKILL.md").write_text(
            "# updated core\n", encoding="utf-8"
        )
        (self.fixture.kit / "AGENTS.md").write_text(
            "# Updated kit contract\n", encoding="utf-8"
        )

        result, output = self.fixture.run()

        self.assertEqual(result, 0)
        self.assertIn("update: .agents/skills/core", output)
        self.assertIn("update: AGENTS.md", output)
        self.assertEqual(
            (self.fixture.target / "AGENTS.md").read_text(),
            "# Updated kit contract\n",
        )

    def test_identical_unowned_content_is_adopted_without_mutation(self) -> None:
        destination = self.fixture.target / ".agents" / "skills" / "core"
        destination.parent.mkdir(parents=True)
        shutil.copytree(
            self.fixture.kit / ".agents" / "skills" / "core", destination
        )
        before = (destination / "SKILL.md").stat().st_mtime_ns

        result, output = self.fixture.run()

        self.assertEqual(result, 0)
        self.assertEqual(before, (destination / "SKILL.md").stat().st_mtime_ns)
        self.assertIn("adopt: .agents/skills/core", output)
        self.assertEqual(len(self.fixture.manifest()[
                         "components"]), 1)

    def test_managed_modified_and_unknown_content_conflict(self) -> None:
        unknown = self.fixture.target / ".agents" / "skills" / "core"
        unknown.mkdir(parents=True)
        (unknown / "SKILL.md").write_text("project owned\n", encoding="utf-8")
        result, output = self.fixture.run()
        self.assertEqual(result, 1)
        self.assertIn("conflict", output.lower())
        self.assertEqual((unknown / "SKILL.md").read_text(), "project owned\n")

        self.fixture.run("--on-conflict", "replace")
        (unknown / "SKILL.md").write_text("modified\n", encoding="utf-8")
        result, output = self.fixture.run()
        self.assertEqual(result, 1)
        self.assertIn("modified", output.lower())
        self.assertEqual((unknown / "SKILL.md").read_text(), "modified\n")

    def test_noninteractive_keep_replace_and_force_alias_are_explicit(self) -> None:
        destination = self.fixture.target / ".agents" / "skills" / "core"
        destination.mkdir(parents=True)
        (destination / "SKILL.md").write_text("owned\n", encoding="utf-8")

        result, _ = self.fixture.run("--on-conflict", "keep")
        self.assertEqual(result, 0)
        self.assertEqual((destination / "SKILL.md").read_text(), "owned\n")
        kept = self.fixture.manifest()["components"]
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["ownership"], "project-owned")

        result, _ = self.fixture.run("--on-conflict", "replace")
        self.assertEqual(result, 0)
        self.assertEqual((destination / "SKILL.md").read_text(), "# core\n")

        (destination / "SKILL.md").write_text("changed again\n", encoding="utf-8")
        result, _ = self.fixture.run("--force-skills")
        self.assertEqual(result, 0)
        self.assertEqual((destination / "SKILL.md").read_text(), "# core\n")

    def test_force_and_keep_flags_are_incompatible_without_writes(self) -> None:
        result, output = self.fixture.run(
            "--force-skills", "--on-conflict", "keep"
        )

        self.assertEqual(result, 2)
        self.assertIn("conflicts with", output)
        self.assertEqual(list(self.fixture.target.iterdir()),
                         [self.fixture.target / ".git"])

    def test_interactive_keep_replace_and_abort_decisions(self) -> None:
        for answer, expected, content in (
            ("keep\n", 0, "owned\n"),
            ("replace\n", 0, "# core\n"),
            ("abort\n", 1, "owned\n"),
        ):
            with self.subTest(answer=answer):
                fixture = InstallFixture()
                try:
                    destination = fixture.target / ".agents" / "skills" / "core"
                    destination.mkdir(parents=True)
                    (destination / "SKILL.md").write_text("owned\n", encoding="utf-8")
                    result, _ = fixture.run(
                        input_stream=TTYStringIO("\n" + answer), interactive=True
                    )
                    self.assertEqual(result, expected)
                    self.assertEqual(
                        (destination / "SKILL.md").read_text(), content)
                finally:
                    fixture.close()

    def test_identical_unowned_agents_is_never_adopted_or_updated(self) -> None:
        agents = self.fixture.target / "AGENTS.md"
        agents.write_bytes((self.fixture.kit / "AGENTS.md").read_bytes())

        first_result, first_output = self.fixture.run()

        self.assertEqual(first_result, 3)
        self.assertIn("semantic merge", first_output.lower())
        self.assertEqual(
            self.fixture.manifest()["global_resources"],
            [self.fixture.catalog_manifest_record(), {
                "path": "AGENTS.md", "ownership": "project-owned",
                "sha256": installer.hash_path(agents),
            }],
        )
        original = agents.read_bytes()
        (self.fixture.kit / "AGENTS.md").write_text(
            "# Changed kit contract\n", encoding="utf-8"
        )

        second_result, second_output = self.fixture.run()

        self.assertEqual(second_result, 3)
        self.assertIn("semantic merge", second_output.lower())
        self.assertEqual(agents.read_bytes(), original)
        self.assertEqual(
            self.fixture.manifest()["global_resources"],
            [self.fixture.catalog_manifest_record(), {
                "path": "AGENTS.md", "ownership": "project-owned",
                "sha256": installer.hash_path(agents),
            }],
        )

    def test_existing_project_agents_requires_semantic_merge_and_is_never_replaced(self) -> None:
        agents = self.fixture.target / "AGENTS.md"
        agents.write_text("# Project contract\n", encoding="utf-8")

        result, output = self.fixture.run("--on-conflict", "replace")

        self.assertEqual(result, 3)
        self.assertEqual(agents.read_text(), "# Project contract\n")
        self.assertIn("semantic merge", output.lower())
        self.assertEqual(
            self.fixture.manifest()["global_resources"],
            [self.fixture.catalog_manifest_record(), {
                "path": "AGENTS.md", "ownership": "project-owned",
                "sha256": installer.hash_path(agents),
            }],
        )

    def test_unselected_managed_components_are_preserved(self) -> None:
        self.assertEqual(self.fixture.run("--profile", "full")[0], 0)
        extra = self.fixture.target / ".agents" / "skills" / "extra" / "SKILL.md"
        extra.write_text("unselected modification\n", encoding="utf-8")

        result, _ = self.fixture.run("--profile", "default", "--force-skills")

        self.assertEqual(result, 0)
        self.assertEqual(extra.read_text(), "unselected modification\n")
        names = {item["name"]
                 for item in self.fixture.manifest()["components"]}
        self.assertEqual(names, {"core", "extra", "base", "addon"})


class SafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = InstallFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_target_and_ancestor_symlinks_are_rejected_before_normalization(self) -> None:
        target_link = self.fixture.root / "target-link"
        target_link.symlink_to(self.fixture.target, target_is_directory=True)
        self.fixture.target = target_link

        result, output = self.fixture.run()

        self.assertEqual(result, 2)
        self.assertIn("symlink", output.lower())
        self.assertFalse((target_link / ".agents").exists())

        other = InstallFixture()
        try:
            real_parent = other.root / "real-parent"
            real_target = real_parent / "repo"
            real_target.mkdir(parents=True)
            subprocess.run(["git", "init", "--quiet",
                           str(real_target)], check=True)
            ancestor_link = other.root / "ancestor-link"
            ancestor_link.symlink_to(real_parent, target_is_directory=True)
            other.target = ancestor_link / "repo"

            result, output = other.run()

            self.assertEqual(result, 2)
            self.assertIn("symlink", output.lower())
            self.assertFalse((real_target / ".agents").exists())
        finally:
            other.close()

        collapsed = InstallFixture()
        try:
            container = collapsed.root / "container"
            (container / "inner").mkdir(parents=True)
            repo = container / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "--quiet", str(repo)], check=True)
            jump = collapsed.root / "jump"
            jump.symlink_to(container / "inner", target_is_directory=True)
            collapsed.target = jump / ".." / "repo"

            result, output = collapsed.run()

            self.assertEqual(result, 2)
            self.assertIn("symlink", output.lower())
            self.assertFalse((repo / ".agents").exists())
        finally:
            collapsed.close()

    def test_root_type_is_hashed_and_empty_file_is_not_adopted_as_empty_tree(self) -> None:
        source = self.fixture.kit / ".agents" / "skills" / "core"
        shutil.rmtree(source)
        source.mkdir()
        destination = self.fixture.target / ".agents" / "skills" / "core"
        destination.parent.mkdir(parents=True)
        destination.write_bytes(b"")

        self.assertNotEqual(installer.hash_path(source),
                            installer.hash_path(destination))
        result, output = self.fixture.run()

        self.assertEqual(result, 1)
        self.assertIn("conflict", output.lower())
        self.assertTrue(destination.is_file())

    def test_transaction_stays_inside_target_and_success_removes_it(self) -> None:
        observed = []

        def inspect(event: str, path: str) -> None:
            if event == "after-staging":
                transaction_root = Path(path)
                transaction_root.relative_to(self.fixture.target)
                observed.append(transaction_root)
                self.assertTrue(transaction_root.is_dir())

        result, _ = self.fixture.run(failure_injector=inspect)

        self.assertEqual(result, 0)
        self.assertEqual(len(observed), 1)
        self.assertFalse(observed[0].exists())

    def test_keyboard_interrupt_during_transaction_rolls_back(self) -> None:
        def interrupt(event: str, path: str) -> None:
            if event == "after-publish" and path == ".agents/skills/core":
                raise KeyboardInterrupt()

        result, output = self.fixture.run(failure_injector=interrupt)

        self.assertEqual(result, 130)
        self.assertIn("interrupted", output.lower())
        self.assertFalse((self.fixture.target / ".agents").exists())
        self.assertFalse((self.fixture.target / "AGENTS.md").exists())
        self.assertEqual(
            list(self.fixture.target.glob(".agentic-sdlc-kit-*")), [])

    def test_system_exit_preserves_exit_code_after_rollback(self) -> None:
        def interrupt(event: str, path: str) -> None:
            if event == "after-publish" and path == ".agents/skills/core":
                raise SystemExit(9)

        with self.assertRaises(SystemExit) as raised:
            self.fixture.run(failure_injector=interrupt)

        self.assertEqual(raised.exception.code, 9)
        self.assertFalse((self.fixture.target / ".agents").exists())
        self.assertFalse((self.fixture.target / "AGENTS.md").exists())
        self.assertEqual(
            list(self.fixture.target.glob(".agentic-sdlc-kit-*")), [])

    def test_exception_between_backup_and_publication_restores_original(self) -> None:
        self.assertEqual(self.fixture.run()[0], 0)
        skill = self.fixture.target / ".agents" / "skills" / "core" / "SKILL.md"
        manifest = self.fixture.target / ".agents" / "agentic-sdlc-kit.json"
        old_skill = skill.read_bytes()
        old_manifest = manifest.read_bytes()
        (self.fixture.kit / ".agents" / "skills" / "core" / "SKILL.md").write_text(
            "# source update\n", encoding="utf-8"
        )

        def interrupt(event: str, path: str) -> None:
            if event == "after-backup" and path == ".agents/skills/core":
                raise RuntimeError("unexpected publication failure")

        try:
            result, output = self.fixture.run(failure_injector=interrupt)
        except RuntimeError:
            self.fail("RuntimeError escaped installer")

        self.assertEqual(result, 1)
        self.assertIn("rolled back", output.lower())
        self.assertNotIn("Traceback", output)
        self.assertEqual(skill.read_bytes(), old_skill)
        self.assertEqual(manifest.read_bytes(), old_manifest)
        self.assertEqual(
            list(self.fixture.target.glob(".agentic-sdlc-kit-*")), [])

    def test_recovery_metadata_tracks_backup_and_publication(self) -> None:
        self.assertEqual(self.fixture.run()[0], 0)
        (self.fixture.kit / ".agents" / "skills" / "core" / "SKILL.md").write_text(
            "# source update\n", encoding="utf-8"
        )
        transaction_root = []
        snapshots = {}

        def inspect(event: str, path: str) -> None:
            if event == "after-staging":
                transaction_root.append(Path(path))
            if event in ("after-backup", "after-publish") and path == ".agents/skills/core":
                snapshots[event] = json.loads(
                    (transaction_root[0] /
                     "recovery.json").read_text(encoding="utf-8")
                )

        result, _ = self.fixture.run(failure_injector=inspect)

        self.assertEqual(result, 0)
        backup = snapshots["after-backup"]
        publication = snapshots["after-publish"]
        self.assertEqual(backup["marker"], "agentic-sdlc-kit-transaction-v1")
        self.assertEqual(backup["state"], "publishing")
        self.assertEqual(backup["current_path"], ".agents/skills/core")
        self.assertEqual(backup["backups"][-1]["path"], ".agents/skills/core")
        self.assertEqual(publication["publications"]
                         [-1]["path"], ".agents/skills/core")
        self.assertRegex(publication["publications"]
                         [-1]["sha256"], r"^[0-9a-f]{64}$")
        self.assertFalse(transaction_root[0].exists())

    def test_abandoned_transaction_reports_recovery_summary(self) -> None:
        abandoned = self.fixture.target / ".agentic-sdlc-kit-abandoned"
        abandoned.mkdir()
        (abandoned / ".transaction-marker").write_text(
            "agentic-sdlc-kit-transaction-v1\n", encoding="utf-8"
        )
        recovery = {
            "marker": "agentic-sdlc-kit-transaction-v1",
            "state": "rollback-incomplete",
            "current_path": ".agents/skills/core",
            "backups": [
                {
                    "path": ".agents/skills/core",
                    "type": "dir",
                    "sha256": "0" * 64,
                }
            ],
            "publications": [],
        }
        (abandoned / "recovery.json").write_text(
            json.dumps(recovery), encoding="utf-8"
        )

        result, output = self.fixture.run()

        self.assertEqual(result, 1)
        self.assertIn(str(abandoned), output)
        self.assertIn("state=rollback-incomplete", output)
        self.assertIn("current=.agents/skills/core", output)

    def test_transaction_prefix_without_marker_is_not_abandoned(self) -> None:
        (self.fixture.target / ".agentic-sdlc-kit-not-ours").write_text(
            "project file\n", encoding="utf-8"
        )
        (self.fixture.target / ".agentic-sdlc-kit-project-dir").mkdir()

        result, _ = self.fixture.run()

        self.assertEqual(result, 0)
        self.assertTrue(
            (self.fixture.target / ".agentic-sdlc-kit-not-ours").is_file())
        self.assertTrue(
            (self.fixture.target / ".agentic-sdlc-kit-project-dir").is_dir())

    def test_symlink_candidates_and_symlink_markers_are_not_transactions(self) -> None:
        external = self.fixture.root / "external-transaction-like"
        external.mkdir()
        external_marker = external / ".transaction-marker"
        external_marker.write_text(
            "agentic-sdlc-kit-transaction-v1\n", encoding="utf-8"
        )
        (external / "recovery.json").write_text(
            json.dumps(
                {
                    "marker": "agentic-sdlc-kit-transaction-v1",
                    "state": "rollback-incomplete",
                    "current_path": None,
                    "backups": [],
                    "publications": [],
                }
            ),
            encoding="utf-8",
        )
        candidate = self.fixture.target / ".agentic-sdlc-kit-external"
        candidate.symlink_to(external, target_is_directory=True)
        marker_candidate = self.fixture.target / ".agentic-sdlc-kit-marker-link"
        marker_candidate.mkdir()
        (marker_candidate / ".transaction-marker").symlink_to(external_marker)

        result, output = self.fixture.run()

        self.assertEqual(result, 0)
        self.assertIn("Applied successfully", output)
        self.assertTrue(candidate.is_symlink())
        self.assertTrue(
            (marker_candidate / ".transaction-marker").is_symlink())

    def test_abandoned_metadata_missing_or_corrupt_is_actionable(self) -> None:
        for content, expected in ((None, "metadata missing"), ("{bad", "metadata corrupt")):
            with self.subTest(expected=expected):
                fixture = InstallFixture()
                try:
                    abandoned = fixture.target / ".agentic-sdlc-kit-abandoned"
                    abandoned.mkdir()
                    (abandoned / ".transaction-marker").write_text(
                        "agentic-sdlc-kit-transaction-v1\n", encoding="utf-8"
                    )
                    if content is not None:
                        (abandoned / "recovery.json").write_text(
                            content, encoding="utf-8"
                        )

                    result, output = fixture.run()

                    self.assertEqual(result, 1)
                    self.assertIn(expected, output.lower())
                    self.assertNotIn("Traceback", output)
                finally:
                    fixture.close()

    def test_recovery_metadata_failure_is_best_effort(self) -> None:
        with mock.patch.object(
            installer, "_write_recovery", side_effect=OSError("metadata unavailable")
        ):
            result, output = self.fixture.run()

        self.assertEqual(result, 0)
        self.assertIn("Applied successfully", output)
        self.assertTrue((self.fixture.target / ".agents" /
                        "skills" / "core").is_dir())
        self.assertEqual(
            list(self.fixture.target.glob(".agentic-sdlc-kit-*")), [])

    def test_invalid_catalog_paths_and_source_symlinks_fail_before_writes(self) -> None:
        valid_catalog = json.loads(json.dumps(self.fixture.catalog))
        cases = []
        invalid = json.loads(json.dumps(valid_catalog))
        invalid["skill_groups"]["optional"] = ["../escape"]
        cases.append(invalid)
        missing = json.loads(json.dumps(valid_catalog))
        missing["profiles"]["default"]["skills"] = ["missing"]
        cases.append(missing)
        for catalog in cases:
            with self.subTest(catalog=catalog):
                self.fixture.catalog = catalog
                self.fixture.write_catalog()
                result, output = self.fixture.run()
                self.assertEqual(result, 2)
                self.assertIn("catalog", output.lower())
                self.assertFalse((self.fixture.target / ".agents").exists())

        self.fixture.catalog = valid_catalog
        self.fixture.write_catalog()
        source_file = self.fixture.kit / ".agents" / "skills" / "core" / "linked"
        source_file.symlink_to(self.fixture.root / "outside")
        result, output = self.fixture.run()
        self.assertEqual(result, 2)
        self.assertIn("symlink", output.lower())
        self.assertFalse((self.fixture.target / ".agents").exists())

    def test_target_symlink_cannot_redirect_writes(self) -> None:
        outside = self.fixture.root / "outside"
        outside.mkdir()
        (self.fixture.target / ".agents").symlink_to(outside, target_is_directory=True)

        result, output = self.fixture.run()

        self.assertEqual(result, 2)
        self.assertIn("symlink", output.lower())
        self.assertEqual(list(outside.iterdir()), [])

    def test_manifest_schema_rejects_unknown_fields_and_invalid_types(self) -> None:
        cases = (
            ("schema_version", lambda data: data.__setitem__("schema_version", True)),
            ("kit_version", lambda data: data.pop("kit_version")),
            ("kit_version", lambda data: data.__setitem__("kit_version", "")),
            ("kit_version", lambda data: data.__setitem__("kit_version", 1)),
            ("unknown root field", lambda data: data.__setitem__("unexpected", True)),
            (
                "components[0]",
                lambda data: data["components"][0].__setitem__(
                    "unexpected", True
                ),
            ),
            (
                "components[0].path",
                lambda data: data["components"][0].__setitem__(
                    "path", 1),
            ),
            (
                "global_resources[0]",
                lambda data: data["global_resources"][0].__setitem__(
                    "unexpected", True
                ),
            ),
            (
                "global_resources[0].sha256",
                lambda data: data["global_resources"][0].__setitem__(
                    "sha256", 1),
            ),
            (
                "global_resources[0].path",
                lambda data: data["global_resources"][0].__setitem__(
                    "path", "../outside"
                ),
            ),
            (
                "global_resources[2].path",
                lambda data: data["global_resources"].append(
                    dict(data["global_resources"][0])
                ),
            ),
        )
        for expected, mutate in cases:
            with self.subTest(expected=expected):
                fixture = InstallFixture()
                try:
                    self.assertEqual(fixture.run()[0], 0)
                    path = fixture.target / ".agents" / "agentic-sdlc-kit.json"
                    data = json.loads(path.read_text(encoding="utf-8"))
                    mutate(data)
                    path.write_text(json.dumps(data), encoding="utf-8")

                    result, output = fixture.run()

                    self.assertEqual(result, 2)
                    self.assertIn(expected, output)
                    self.assertNotIn("Traceback", output)
                finally:
                    fixture.close()

    def test_injected_failure_rolls_back_destinations_and_manifest(self) -> None:
        self.assertEqual(self.fixture.run()[0], 0)
        skill = self.fixture.target / ".agents" / "skills" / "core" / "SKILL.md"
        manifest = self.fixture.target / ".agents" / "agentic-sdlc-kit.json"
        old_skill = skill.read_bytes()
        old_manifest = manifest.read_bytes()
        (self.fixture.kit / ".agents" / "skills" / "core" / "SKILL.md").write_text(
            "# updated core\n", encoding="utf-8"
        )

        def fail(event: str, path: str) -> None:
            if event == "before-manifest":
                raise OSError("injected manifest failure")

        result, output = self.fixture.run(failure_injector=fail)

        self.assertEqual(result, 1)
        self.assertIn("rolled back", output.lower())
        self.assertNotIn("rollback incomplete", output.lower())
        self.assertEqual(skill.read_bytes(), old_skill)
        self.assertEqual(manifest.read_bytes(), old_manifest)
        self.assertEqual(
            list(self.fixture.target.glob(".agentic-sdlc-kit-*")), [])

    def test_failed_restore_retains_recovery_backup_inside_target(self) -> None:
        self.assertEqual(self.fixture.run()[0], 0)
        skill = self.fixture.target / ".agents" / "skills" / "core" / "SKILL.md"
        old_skill = skill.read_bytes()
        (self.fixture.kit / ".agents" / "skills" / "core" / "SKILL.md").write_text(
            "# source update\n", encoding="utf-8"
        )

        def fail(event: str, path: str) -> None:
            if event == "before-manifest":
                raise OSError("publication failure")
            if event == "before-restore" and path == ".agents/skills/core":
                raise OSError("restore failure")

        result, output = self.fixture.run(failure_injector=fail)

        self.assertEqual(result, 1)
        marker = "rollback incomplete; recovery data retained at "
        self.assertIn(marker, output)
        self.assertNotIn("was rolled back", output)
        recovery = Path(output.split(marker, 1)[1].splitlines()[0])
        recovery.relative_to(self.fixture.target)
        self.assertTrue(recovery.is_dir())
        backup = recovery / "backup" / ".agents" / "skills" / "core" / "SKILL.md"
        self.assertEqual(backup.read_bytes(), old_skill)
        metadata = json.loads(
            (recovery / "recovery.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["state"], "rollback-incomplete")
        self.assertEqual(metadata["current_path"], ".agents/skills/core")

    def test_project_json_preflight_and_legacy_no_write(self) -> None:
        schema_source = (
            ROOT / ".agents" / "skills" / "setup" / "assets" / "project.schema.json"
        )
        template_source = (
            ROOT / ".agents" / "skills" / "setup" / "assets" / "project.template.json"
        )
        setup_assets = self.fixture.kit / ".agents" / "skills" / "setup" / "assets"
        setup_assets.mkdir(parents=True)
        shutil.copy2(schema_source, setup_assets / "project.schema.json")
        agents = self.fixture.target / ".agents"
        agents.mkdir()
        legacy = agents / "project.md"
        legacy.write_text("secret=do-not-echo", encoding="utf-8")

        result, output = self.fixture.run()

        self.assertEqual(result, 2)
        self.assertIn("unsupported", output.lower())
        self.assertNotIn("do-not-echo", output)
        self.assertEqual(legacy.read_text(
            encoding="utf-8"), "secret=do-not-echo")
        self.assertFalse((agents / "agentic-sdlc-kit.json").exists())

        legacy.unlink()
        outside = self.fixture.root / "outside-project-secret"
        outside.write_text("do-not-echo", encoding="utf-8")
        legacy.symlink_to(outside)
        result, output = self.fixture.run()
        self.assertEqual(result, 2)
        self.assertIn("unsupported", output.lower())
        self.assertNotIn("do-not-echo", output)
        self.assertEqual(outside.read_text(encoding="utf-8"), "do-not-echo")
        self.assertFalse((agents / "agentic-sdlc-kit.json").exists())

        legacy.unlink()
        project_path = agents / "project.json"
        project_path.write_bytes(template_source.read_bytes())
        before = project_path.read_bytes()
        result, output = self.fixture.run()
        self.assertEqual(result, 0, output)
        self.assertEqual(project_path.read_bytes(), before)

        valid_mapped = json.loads(template_source.read_text(encoding="utf-8"))
        valid_mapped["roots"]["adrs"] = "adr-ledger.md"
        valid_mapped["repositories"] = [{
            "id": "repo", "path": ".", "remote": "git@server:org/repo.git",
        }]
        (self.fixture.target / "adr-ledger.md").write_text(
            "# Decisions\n", encoding="utf-8")
        project_path.write_text(json.dumps(valid_mapped), encoding="utf-8")
        mapped_before = project_path.read_bytes()
        result, output = self.fixture.run()
        self.assertEqual(result, 0, output)
        self.assertEqual(project_path.read_bytes(), mapped_before)

        manifest_before = (agents / "agentic-sdlc-kit.json").read_bytes()
        invalid_cases = []
        invalid = json.loads(template_source.read_text(encoding="utf-8"))
        invalid["contribution"]["base_branch"] = "bad branch"
        invalid_cases.append((invalid, "contribution.base_branch"))
        invalid = json.loads(template_source.read_text(encoding="utf-8"))
        invalid["repositories"] = [{
            "id": "repo", "path": ".",
            "remote": "ssh://user:pass@example.test/do-not-echo",
        }]
        invalid_cases.append((invalid, "repositories/0/remote"))
        invalid = json.loads(template_source.read_text(encoding="utf-8"))
        invalid["tracker"]["labels"] = {"scripts": "safe-looking"}
        invalid_cases.append((invalid, "safety.executable_field"))
        invalid = json.loads(template_source.read_text(encoding="utf-8"))
        invalid["tracker"]["labels"] = {"ready": "bad\ud800value"}
        invalid_cases.append((invalid, "safety.string"))
        invalid = json.loads(template_source.read_text(encoding="utf-8"))
        invalid["roots"]["specs"] = "spec-file"
        (self.fixture.target / "spec-file").write_text("content\n", encoding="utf-8")
        invalid_cases.append((invalid, "root.type"))

        for invalid, expected in invalid_cases:
            with self.subTest(expected=expected):
                project_path.write_text(json.dumps(invalid), encoding="utf-8")
                result, output = self.fixture.run()
                self.assertEqual(result, 2)
                self.assertIn(expected, output)
                self.assertNotIn("do-not-echo", output)
                self.assertNotIn("\\ud800", output)
                self.assertEqual(
                    (agents / "agentic-sdlc-kit.json").read_bytes(), manifest_before)


class RepositoryDistributionTests(unittest.TestCase):
    def test_default_profile_installs_utility_skills_and_setup_resources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = (Path(temporary).resolve() / "target")
            target.mkdir()
            subprocess.run(
                ["git", "init", "--quiet", str(target)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            output = io.StringIO()

            result = installer.main(
                [str(target)],
                kit_root=ROOT,
                input_stream=io.StringIO(),
                output_stream=output,
                interactive=False,
            )

            self.assertEqual(result, 0, output.getvalue())
            skills = target / ".agents" / "skills"
            self.assertEqual(len(list(skills.iterdir())), 13)
            setup = skills / "setup"
            self.assertTrue((setup / "SKILL.md").is_file())
            self.assertTrue((skills / "ask-kit" / "SKILL.md").is_file())
            self.assertTrue((skills / "contribute" / "SKILL.md").is_file())
            self.assertTrue(
                (skills / "contribute" / "scripts" / "check_contribution.py").is_file())
            self.assertTrue(
                (setup / "assets" / "project.template.md").is_file())
            self.assertTrue(
                (setup / "references" / "project-config.md").is_file()
            )
            manifest = json.loads(
                (target / ".agents" / "agentic-sdlc-kit.json").read_text(
                    encoding="utf-8"
                )
            )
            installed = {
                item["name"]
                for item in manifest["components"]
                if item["kind"] == "skill"
            }
            self.assertEqual(len(installed), 13)
            self.assertIn("setup", installed)
            self.assertIn("ask-kit", installed)
            self.assertIn("contribute", installed)

    def test_init_config_creates_conservative_valid_config_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary).resolve() / "target"
            target.mkdir()
            subprocess.run(["git", "init", "--quiet", str(target)], check=True)
            for message in ("feat: one", "fix: two", "chore: three"):
                subprocess.run(
                    ["git", "-C", str(target), "-c", "user.name=T",
                     "-c", "user.email=t@example.invalid", "commit",
                     "--quiet", "--allow-empty", "-m", message],
                    check=True,
                )
            template = target / ".github" / "pull_request_template.md"
            template.parent.mkdir()
            template.write_text("## Summary\n", encoding="utf-8")

            def run(*extra: str) -> tuple[int, str]:
                output = io.StringIO()
                code = installer.main(
                    [str(target), "--profile", "full", "--init-config", *extra],
                    kit_root=ROOT, input_stream=io.StringIO(),
                    output_stream=output, interactive=False,
                )
                return code, output.getvalue()

            code, output = run("--dry-run")
            self.assertEqual(code, 0, output)
            self.assertIn("Config: would create .agents/project.json", output)
            self.assertFalse((target / ".agents" / "project.json").exists())

            code, output = run()
            self.assertEqual(code, 0, output)
            loaded = installer.load_project(
                target,
                ROOT / ".agents" / "skills" / "setup" / "assets" / "project.schema.json",
                module_names={"compliance", "enforcement", "evidence", "multi-repo"},
                module_dependencies={"compliance": ["evidence", "enforcement"],
                                     "enforcement": [], "evidence": [],
                                     "multi-repo": []},
            )
            # History is never policy evidence; only observed facts are recorded.
            self.assertEqual(loaded["contribution"]["commit_mode"], "discover")
            self.assertIsNone(loaded["contribution"]["base_branch"])
            self.assertEqual(loaded["contribution"]["pull_request_template"],
                             ".github/pull_request_template.md")
            self.assertEqual(loaded["tracker"]["kind"], "none")
            self.assertEqual(loaded["enabled_modules"],
                             ["compliance", "enforcement", "evidence"])
            self.assertEqual(loaded["roots"]["evidence"], "evidence")
            self.assertIsNone(loaded["roots"]["adrs"])

            manifest = json.loads((target / ".agents" / "agentic-sdlc-kit.json")
                                  .read_text(encoding="utf-8"))
            owned = {item["path"] for item in manifest["components"]} | {
                item["path"] for item in manifest["global_resources"]}
            self.assertNotIn(".agents/project.json", owned)

            checker = target / ".agents" / "modules" / "enforcement" / "check.py"
            result = subprocess.run(
                [sys.executable, str(checker), "--root", str(target)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout)

            before = (target / ".agents" / "project.json").read_bytes()
            code, output = run()
            self.assertEqual(code, 0, output)
            self.assertIn("kept existing .agents/project.json unchanged", output)
            self.assertEqual((target / ".agents" / "project.json").read_bytes(), before)

    def test_init_config_skips_when_legacy_markdown_config_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary).resolve() / "target"
            target.mkdir()
            subprocess.run(["git", "init", "--quiet", str(target)], check=True)
            output = io.StringIO()
            catalog = installer.load_catalog(ROOT)
            selection = installer.resolve_selection(
                catalog, "default", [], False, io.StringIO(), io.StringIO())
            (target / ".agents").mkdir()
            (target / ".agents" / "project.md").write_text("legacy\n", encoding="utf-8")
            created = installer.init_project_config(
                target, ROOT, selection, catalog, output)
            self.assertFalse(created)
            self.assertIn("legacy .agents/project.md is unsupported", output.getvalue())
            self.assertFalse((target / ".agents" / "project.json").exists())

if __name__ == "__main__":
    unittest.main()

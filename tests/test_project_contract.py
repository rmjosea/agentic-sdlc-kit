from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.contracts import project


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / ".agents" / "skills" / "setup" / "assets" / "project.schema.json"
TEMPLATE = ROOT / ".agents" / "skills" / \
    "setup" / "assets" / "project.template.json"
CHECKER = ROOT / ".agents" / "modules" / "enforcement" / "check.py"


def empty_config() -> dict[str, object]:
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def full_config() -> dict[str, object]:
    value = empty_config()
    value.update(
        roots={
            "specs": "product/specs",
            "work": "delivery/work",
            "adrs": "docs/adrs",
            "evidence": "evidence",
            "domain_context": "docs/domain/CONTEXT.md",
        },
        repositories=[
            {"id": "current", "path": ".", "remote": "git@example.test:org/repo.git"},
            {"id": "service-api", "path": "services/api",
                "remote": "https://example.test/org/api"},
            {"id": "sibling", "path": "${WORKSPACE}/sibling", "remote": None},
        ],
        enabled_modules=["compliance",
                         "enforcement", "evidence", "multi-repo"],
        tracker={"kind": "github", "location": "https://example.test/org/repo/issues",
                 "labels": {"ready": "status:ready"}},
        agent={"mode": "autonomous-within-rules"},
        review={"mode": "always-independent"},
        approval_policy={"rules": [{"risk": "high", "action": "verified", "required_roles": [
            {"role": "reviewer", "minimum": 1}], "independent": True}]},
        contribution={"commit_mode": "conventional", "base_branch": "release/v2", "required_trailers": [
            "Co-authored-by", "Signed-off-by"], "pull_request_template": ".github/pull_request_template.md", "merge_strategy": "squash"},
    )
    return value


class ProjectSchemaAndSemanticTests(unittest.TestCase):
    def validate(self, value: object, modules: set[str] | None = None) -> tuple[project.ProjectDiagnostic, ...]:
        return project.validate_project(value, SCHEMA, module_names=modules or {"compliance", "enforcement", "evidence", "multi-repo"})

    def assert_invalid(self, value: object, field: str) -> None:
        diagnostics = self.validate(value)
        self.assertTrue(diagnostics)
        self.assertIn(field, "\n".join(item.field for item in diagnostics))

    def test_exact_empty_and_full_shapes_are_valid(self) -> None:
        self.assertEqual(self.validate(empty_config()), ())
        self.assertEqual(self.validate(full_config()), ())

    def test_artifact_catalog_activates_only_project_json_v2(self) -> None:
        catalog = json.loads(
            (ROOT / ".agents" / "artifact-catalog.json").read_text(encoding="utf-8")
        )
        entries = {item["id"]: item for item in catalog["artifacts"]}
        project_entry = entries["project-config"]
        self.assertEqual(project_entry["format"], "json")
        self.assertEqual(project_entry["template"],
                         "skills/setup/assets/project.template.json")
        self.assertEqual(project_entry["schema"],
                         "skills/setup/assets/project.schema.json")
        self.assertEqual(project_entry["path_patterns"], [
                         ".agents/project.json"])
        self.assertEqual(project_entry["writable_schema_version"], 2)
        self.assertEqual(entries["approval-policy"]
                         ["owner"], {"kind": "skill", "name": "setup"})

    def test_setup_requires_exact_preview_approval_and_recheck(self) -> None:
        skill = (ROOT / ".agents" / "skills" / "setup" /
                 "SKILL.md").read_text(encoding="utf-8")
        for required in (
            "Approve writing this exact `.agents/project.json` preview?",
            "exact complete proposed `.agents/project.json` bytes",
            "Re-inspect `.agents/project.md`",
            "Re-read or re-confirm absence",
            "Any byte change requires",
            "byte-for-byte equality",
            "Write only the approved `.agents/project.json` bytes",
        ):
            self.assertIn(required, skill)

    def test_closed_missing_mixed_type_and_limits(self) -> None:
        cases = []
        for mutation, field in (
            (lambda data: data.__setitem__("unknown", True), "unknown"),
            (lambda data: data.pop("review"), "review"),
            (lambda data: data.__setitem__("repositories", {}), "repositories"),
            (lambda data: data["tracker"].__setitem__(
                "labels", []), "tracker/labels"),
            (lambda data: data["tracker"].__setitem__(
                "kind", "x" * 501), "tracker/kind"),
        ):
            value = empty_config()
            mutation(value)
            cases.append((value, field))
        for value, field in cases:
            with self.subTest(field=field):
                self.assert_invalid(value, field)

    def test_controls_sensitive_and_executable_configuration_are_rejected_and_redacted(self) -> None:
        values = []
        for mutation in (
            lambda data: data["tracker"].__setitem__("location", "line\nnext"),
            lambda data: data["tracker"].__setitem__(
                "labels", {"api_key": "do-not-echo"}),
            lambda data: data["tracker"].__setitem__(
                "labels", {"ready": "token=do-not-echo"}),
            lambda data: data["tracker"].__setitem__(
                "labels", {"hook": "pre-commit"}),
            lambda data: data["tracker"].__setitem__(
                "labels", {"script": "safe-looking"}),
            lambda data: data["tracker"].__setitem__(
                "labels", {"scripts": "safe-looking"}),
            lambda data: data["tracker"].__setitem__(
                "labels", {"bad\ud800key": "safe-looking"}),
            lambda data: data["tracker"].__setitem__(
                "labels", {"ready": "bad\udfffvalue"}),
        ):
            value = full_config()
            mutation(value)
            values.append(value)
        for value in values:
            with self.subTest(value=value["tracker"]):
                rendered = "\n".join(
                    item.message for item in self.validate(value))
                self.assertTrue(rendered)
                self.assertNotIn("do-not-echo", rendered)

    def test_every_root_path_form(self) -> None:
        valid = ("specs", ".work", "product/specs", "a-b/c_d")
        invalid = ("", ".", "../specs", "a/../b", "/tmp/specs",
                   "C:/specs", "a\\b", "a//b", "${ROOT}/specs")
        for path in valid:
            value = empty_config()
            value["roots"]["specs"] = path
            self.assertEqual(self.validate(value), (), path)
        for path in invalid:
            value = empty_config()
            value["roots"]["specs"] = path
            self.assert_invalid(value, "roots/specs")

    def test_repository_ids_paths_env_and_remotes(self) -> None:
        valid_paths = (".", "services/api", "${WORKSPACE}/service")
        for path in valid_paths:
            value = empty_config()
            value["repositories"] = [
                {"id": "service-api", "path": path, "remote": "git@example.test:org/repo.git"}]
            self.assertEqual(self.validate(value), (), path)
        for path in ("..", "./service", "${workspace}/service", "${WORKSPACE}", "x/${WORKSPACE}/service", "${WORKSPACE}/../service"):
            value = empty_config()
            value["repositories"] = [
                {"id": "service-api", "path": path, "remote": None}]
            self.assert_invalid(value, "repositories/0/path")
        for identifier in ("Service", "service_api", "-service", "service-"):
            value = empty_config()
            value["repositories"] = [
                {"id": identifier, "path": ".", "remote": None}]
            self.assert_invalid(value, "repositories/0/id")
        value = empty_config()
        value["repositories"] = [{"id": "same", "path": ".", "remote": None}, {
            "id": "same", "path": "other", "remote": None}]
        self.assert_invalid(value, "repositories/1/id")
        for remote in (
            " https://user:pass@example.test/repo",
            "https://example.test/repo ",
            "https://user@example.test/repo",
            "ssh://user:pass@example.test/repo",
            "ssh://git@example.test/repo?access_token=do-not-echo",
            "https://example.test/repo?access_token=do-not-echo",
            "https:example.test/repo",
            "ssh:user@example.test/repo",
            "ssh:org/repo.git",
            "git@example.test:org\\repo.git",
            "https://example.test/org/my repo.git",
            "git@:org/repo.git",
            "git@server:",
            "C:repo.git",
            "line\nnext",
        ):
            value = empty_config()
            value["repositories"] = [
                {"id": "repo", "path": ".", "remote": remote}]
            diagnostics = self.validate(value)
            self.assertTrue(diagnostics, remote)
            self.assertNotIn(
                "do-not-echo", "\n".join(item.message for item in diagnostics))
        for remote in (
            "https://example.test/org/repo.git",
            "ssh://git@example.test/org/repo.git",
            "git@example.test:org/repo.git",
            "git@server:org/repo.git",
            "server:org/repo.git",
            "example.test:org/repo.git",
        ):
            value = empty_config()
            value["repositories"] = [
                {"id": "repo", "path": ".", "remote": remote}]
            self.assertEqual(self.validate(value), (), remote)

    def test_modules_catalog_membership_dependencies_and_uniqueness(self) -> None:
        value = empty_config()
        value["enabled_modules"] = ["evidence", "evidence"]
        self.assert_invalid(value, "enabled_modules")
        value["enabled_modules"] = ["not-installed"]
        self.assertTrue(self.validate(value))
        value["enabled_modules"] = ["compliance"]
        diagnostics = project.validate_project(value, SCHEMA, module_names={
                                               "compliance", "evidence", "enforcement"}, module_dependencies={"compliance": {"evidence", "enforcement"}})
        self.assertIn("module.dependency", {item.code for item in diagnostics})

    def test_tracker_cross_fields(self) -> None:
        value = empty_config()
        value["tracker"] = {"kind": "none", "location": "issues", "labels": {}}
        self.assert_invalid(value, "tracker.location")
        value["tracker"] = {"kind": "github", "location": None, "labels": {}}
        self.assert_invalid(value, "tracker.location")

    def test_approval_policy_exact_high_and_self_semantics(self) -> None:
        base_rule = {"risk": "medium", "action": "publish", "required_roles": [
            {"role": "reviewer", "minimum": 1}], "independent": False}
        for mutate in (
            lambda rule: rule.__setitem__("extra", True),
            lambda rule: rule.__setitem__("required_roles", []),
            lambda rule: rule["required_roles"][0].__setitem__("minimum", 0),
            lambda rule: rule.__setitem__("independent", "yes"),
        ):
            value = empty_config()
            rule = copy.deepcopy(base_rule)
            mutate(rule)
            value["approval_policy"] = {"rules": [rule]}
            self.assertTrue(self.validate(value))
        value = empty_config()
        rule = copy.deepcopy(base_rule)
        rule.update(risk="high", independent=False)
        value["approval_policy"] = {"rules": [rule]}
        self.assertTrue(self.validate(value))
        value["approval_policy"] = {
            "rules": [base_rule, copy.deepcopy(base_rule)]}
        self.assertTrue(self.validate(value))

    def test_contribution_fields_ref_trailers_and_template(self) -> None:
        for field, invalid in (
            ("commit_mode", "other"),
            ("base_branch", "bad branch"),
            ("base_branch", "../main"),
            ("base_branch", "refs/heads/main.lock"),
            ("required_trailers", ["Signed-off-by", "Signed-off-by"]),
            ("required_trailers", ["bad token"]),
            ("pull_request_template", "../template.md"),
            ("pull_request_template", "${ROOT}/template.md"),
            ("merge_strategy", "fast-forward"),
        ):
            value = empty_config()
            value["contribution"][field] = invalid
            self.assertTrue(self.validate(value), (field, invalid))


class ProjectLoaderAndResolverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        (self.root / ".agents").mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, value: object) -> None:
        (self.root / ".agents" /
         "project.json").write_text(json.dumps(value), encoding="utf-8")

    def test_duplicate_key_and_legacy_are_fail_closed_without_raw_values(self) -> None:
        (self.root / ".agents" / "project.json").write_text(
            '{"schema_version":2,"schema_version":2}', encoding="utf-8")
        with self.assertRaises(project.ProjectConfigError) as caught:
            project.load_project(self.root, SCHEMA, module_names=set())
        self.assertIn("duplicate", str(caught.exception).lower())
        (self.root / ".agents" / "project.json").unlink()
        (self.root / ".agents" /
         "project.md").write_text("secret=do-not-echo", encoding="utf-8")
        with self.assertRaises(project.ProjectConfigError) as caught:
            project.load_project(self.root, SCHEMA, module_names=set())
        self.assertIn("unsupported", str(caught.exception).lower())
        self.assertNotIn("do-not-echo", str(caught.exception))

    def test_project_json_symlink_is_rejected(self) -> None:
        external = self.root / "external.json"
        external.write_text(json.dumps(empty_config()), encoding="utf-8")
        (self.root / ".agents" / "project.json").symlink_to(external)
        with self.assertRaises(project.ProjectConfigError):
            project.load_project(self.root, SCHEMA, module_names=set())

    def test_root_symlink_at_ancestor_and_target_is_rejected(self) -> None:
        value = empty_config()
        value["roots"]["specs"] = "real/child"
        self.write(value)
        config = project.load_project(self.root, SCHEMA, module_names=set())
        assert config is not None
        (self.root / "real").mkdir()
        (self.root / "real" / "child").mkdir()
        self.assertEqual(project.resolve_root(
            self.root, config, "specs"), self.root / "real" / "child")
        (self.root / "real" / "child").rmdir()
        (self.root / "elsewhere").mkdir()
        (self.root / "real" / "child").symlink_to(self.root /
                                                  "elsewhere", target_is_directory=True)
        with self.assertRaises(project.ProjectConfigError):
            project.resolve_root(self.root, config, "specs")
        (self.root / "real" / "child").unlink()
        (self.root / "real").rmdir()
        (self.root / "real").symlink_to(self.root /
                                        "elsewhere", target_is_directory=True)
        with self.assertRaises(project.ProjectConfigError):
            project.resolve_root(self.root, config, "specs")

    def test_root_existing_type_contract(self) -> None:
        value = empty_config()
        value["roots"].update(
            specs="spec-file",
            adrs="adr-file",
            evidence="evidence-file",
            domain_context="domain-file",
        )
        self.write(value)
        config = project.load_project(self.root, SCHEMA, module_names=set())
        assert config is not None
        for name in ("spec-file", "adr-file", "evidence-file", "domain-file"):
            (self.root / name).write_text("content\n", encoding="utf-8")
        with self.assertRaises(project.ProjectConfigError) as specs_error:
            project.resolve_root(self.root, config, "specs")
        self.assertIn(
            "root.type", {item.code for item in specs_error.exception.diagnostics})
        with self.assertRaises(project.ProjectConfigError):
            project.resolve_root(self.root, config, "evidence")
        self.assertEqual(
            project.resolve_root(self.root, config, "adrs"),
            self.root / "adr-file",
        )
        self.assertEqual(
            project.resolve_root(self.root, config, "domain_context"),
            self.root / "domain-file",
        )
        (self.root / "domain-file").unlink()
        self.assertEqual(
            project.resolve_root(self.root, config, "domain_context"),
            self.root / "domain-file",
        )

    def test_repository_env_ancestor_target_and_git_marker(self) -> None:
        workspace = self.root / "workspace"
        checkout = workspace / "service"
        checkout.mkdir(parents=True)
        (checkout / ".git").mkdir()
        value = empty_config()
        value["repositories"] = [
            {"id": "service", "path": "${WORKSPACE}/service", "remote": None}]
        self.write(value)
        config = project.load_project(self.root, SCHEMA, module_names=set())
        assert config is not None
        self.assertEqual(project.resolve_repository(
            self.root, config, "service", {"WORKSPACE": str(workspace)}), checkout)
        (checkout / ".git").rmdir()
        with self.assertRaises(project.ProjectConfigError):
            project.resolve_repository(self.root, config, "service", {
                                       "WORKSPACE": str(workspace)})
        (checkout).rmdir()
        (workspace / "real").mkdir()
        checkout.symlink_to(workspace / "real", target_is_directory=True)
        with self.assertRaises(project.ProjectConfigError):
            project.resolve_repository(self.root, config, "service", {
                                       "WORKSPACE": str(workspace)})
        checkout.unlink()
        (workspace / "real").rmdir()
        workspace.rmdir()
        actual_workspace = self.root / "actual-workspace"
        (actual_workspace / "service" / ".git").mkdir(parents=True)
        workspace.symlink_to(actual_workspace, target_is_directory=True)
        with self.assertRaises(project.ProjectConfigError):
            project.resolve_repository(self.root, config, "service", {
                                       "WORKSPACE": str(workspace)})

    def test_repository_root_symlink_is_rejected(self) -> None:
        self.write(empty_config())
        linked = self.root.parent / f"{self.root.name}-linked"
        linked.symlink_to(self.root, target_is_directory=True)
        self.addCleanup(lambda: linked.unlink(missing_ok=True))
        with self.assertRaises(project.ProjectConfigError):
            project.load_project(linked, SCHEMA, module_names=set())


class ProjectConsumerParityTests(unittest.TestCase):
    def checker_decision(self, raw: str, legacy: bool = False) -> tuple[int, dict[str, object]]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            agents = root / ".agents"
            agents.mkdir()
            name = "project.md" if legacy else "project.json"
            (agents / name).write_text(raw, encoding="utf-8")
            if not legacy:
                try:
                    configured = json.loads(raw).get("enabled_modules", [])
                except (json.JSONDecodeError, AttributeError):
                    configured = []
                if configured:
                    modules = agents / "modules"
                    modules.mkdir()
                    for module_name in configured:
                        module = modules / module_name
                        module.mkdir()
                        (module / "MODULE.md").write_text("# Module\n", encoding="utf-8")
                    catalog = {
                        "schema_version": 1,
                        "kit_version": "test",
                        "skill_groups": {"core": [], "utilities": [], "optional": []},
                        "modules": [{"name": item, "description": "test module", "depends_on": []} for item in configured],
                        "profiles": {"default": {"skills": [], "modules": []}, "full": {"skills": [], "modules": configured}},
                    }
                    (agents / "kit-catalog.json").write_text(json.dumps(catalog),
                                                             encoding="utf-8")
            result = subprocess.run([sys.executable, str(CHECKER), "--root", str(root), "--format",
                                    "json"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            return result.returncode, json.loads(result.stdout)

    def test_source_and_installed_checker_accept_reject_parity(self) -> None:
        cases = [empty_config(), full_config()]
        for remote in (
            "ssh://git@example.test/org/repo.git",
            "git@server:org/repo.git",
            " https://user:pass@example.test/repo",
            "ssh://user:pass@example.test/repo",
            "https:example.test/repo",
            "git@example.test:org\\repo.git",
            "git://example.test/repo?api_key=do-not-echo",
        ):
            value = empty_config()
            value["repositories"] = [
                {"id": "repo", "path": ".", "remote": remote}]
            cases.append(value)
        for labels in (
            {"script": "safe-looking"},
            {"scripts": "safe-looking"},
            {"bad\ud800key": "safe-looking"},
            {"ready": "bad\udfffvalue"},
        ):
            value = empty_config()
            value["tracker"]["labels"] = labels
            cases.append(value)
        invalid = empty_config()
        invalid["tracker"]["location"] = "https://example.test/?token=do-not-echo"
        cases.append(invalid)
        for value in cases:
            raw = json.dumps(value)
            source_valid = not project.validate_project(value, SCHEMA, module_names={
                                                        "compliance", "enforcement", "evidence", "multi-repo"})
            _, report = self.checker_decision(raw)
            checker_config_valid = not any(
                item["code"].startswith("CONFIG_") for item in report["errors"]
            )
            self.assertEqual(source_valid, checker_config_valid, report)
            rendered_report = json.dumps(report)
            self.assertNotIn("do-not-echo", rendered_report)
            self.assertNotIn("\\ud800", rendered_report)
            self.assertNotIn("\\udfff", rendered_report)

    def test_simple_host_scp_remote_is_valid_in_source_and_checker(self) -> None:
        value = empty_config()
        value["repositories"] = [{
            "id": "repo", "path": ".", "remote": "git@server:org/repo.git",
        }]
        self.assertEqual(project.validate_project(
            value, SCHEMA, module_names=set()), ())
        code, report = self.checker_decision(json.dumps(value))
        self.assertEqual(code, 0, report)

    def test_legacy_checker_diagnostic_is_unsupported(self) -> None:
        code, report = self.checker_decision(
            "---\nschema_version: 2\n---\n", legacy=True)
        self.assertEqual(code, 2)
        self.assertIn("CONFIG_LEGACY_UNSUPPORTED", {
                      item["code"] for item in report["errors"]})

    def test_checker_legacy_symlink_is_unsupported_without_dereference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            agents = root / ".agents"
            agents.mkdir()
            outside = root / "outside-secret"
            outside.write_text("do-not-echo", encoding="utf-8")
            (agents / "project.md").symlink_to(outside)
            (agents / "project.json").write_text(
                json.dumps(empty_config()), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(CHECKER), "--root",
                 str(root), "--format", "json"],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 2)
            self.assertIn("CONFIG_LEGACY_UNSUPPORTED", {
                          item["code"] for item in report["errors"]})
            self.assertNotIn("do-not-echo", result.stdout + result.stderr)
            self.assertEqual(outside.read_text(
                encoding="utf-8"), "do-not-echo")

    def test_checker_rejects_regular_file_as_specs_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            agents = root / ".agents"
            agents.mkdir()
            value = empty_config()
            value["roots"]["specs"] = "spec-file"
            (root / "spec-file").write_text("content\n", encoding="utf-8")
            (agents / "project.json").write_text(
                json.dumps(value), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(CHECKER), "--root",
                 str(root), "--format", "json"],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 2)
            self.assertIn("CONFIG_ROOT_TYPE", {
                          item["code"] for item in report["errors"]})

    def test_checker_root_type_parity_for_optional_roots(self) -> None:
        for key, should_pass in (
            ("adrs", True),
            ("evidence", False),
            ("domain_context", True),
        ):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                agents = root / ".agents"
                agents.mkdir()
                value = empty_config()
                value["roots"][key] = "configured-file"
                (root / "configured-file").write_text("content\n", encoding="utf-8")
                (agents / "project.json").write_text(
                    json.dumps(value), encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(CHECKER), "--root",
                     str(root), "--format", "json"],
                    text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
                )
                report = json.loads(result.stdout)
                self.assertEqual(result.returncode == 0, should_pass, report)
                if not should_pass:
                    self.assertIn("CONFIG_ROOT_TYPE", {
                                  item["code"] for item in report["errors"]})

    def test_no_active_legacy_project_reader_writer_reference(self) -> None:
        allowed_history = {
            ROOT / "specs" / "001-agentic-sdlc-kit-v1" / "spec.md",
            ROOT / "specs" / "002-harness-v2" / "spec.md",
        }
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts or ".work" in path.parts:
                continue
            if path.suffix not in {".py", ".md", ".json"}:
                continue
            text = path.read_text(encoding="utf-8")
            if ".agents/project.md" not in text or path in allowed_history or "tests" in path.parts:
                continue
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertIn("unsupported", text.lower())
                self.assertNotIn("parse_project_frontmatter", text)
        catalog = (ROOT / ".agents" /
                   "artifact-catalog.json").read_text(encoding="utf-8")
        self.assertNotIn(".agents/project.md", catalog)


if __name__ == "__main__":
    unittest.main()

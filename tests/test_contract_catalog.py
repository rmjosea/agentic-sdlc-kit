from __future__ import annotations

import copy
import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path

from scripts.contracts import catalog


ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / ".agents"

UNCHANGED_V1_WRITER_HASHES = {
    ".agents/skills/decompose-tasks/assets/tasks.template.md": "c42f85e118d2506cfe57aeeec00bcb230bf5beb49f5dd2ee2a330529a1e6fe6a",
    ".agents/skills/domain-model/assets/adr.template.md": "6ac2ac3d9566ec007eb57aca15295a0325d2b37d12d1233a8a3db4ef8e3013af",
    ".agents/skills/domain-model/assets/glossary.template.md": "2616ee058b9e0a08923240c2e900ccd611b14892fd09d7db049fb08572cdaa41",
    ".agents/skills/implement/assets/handoff.template.md": "8b33cac454acdde7140e3968f339a7ce3a81993ab5b02e44d5fdec903c3e77b7",
    ".agents/skills/plan/assets/plan.template.md": "ca45da853442270c2b679a6de4ced8245f7feed0e39546e69ccb6a78d39a88b3",
    ".agents/skills/review/assets/review.template.md": "66bc900908dd68755b743affc4a8999975cf5820ca5395880df2e933e3c77019",
    ".agents/skills/setup/assets/project.template.md": "f0037799ff09354adbf5c7e7b0f144e009fc2b33d15bed1ba7b2d45265cd36ce",
    ".agents/skills/write-spec/assets/spec.template.md": "5f7457c53eee844a6600a40fc340065b9909e03a2348b4df7032918f9c08123b",
}


def load_schema(name: str) -> dict[str, object]:
    return catalog.load_json(AGENTS / "schemas" / name)


def assert_closed_shape(
    case: unittest.TestCase,
    schema: dict[str, object],
    value: object,
    root_schema: dict[str, object] | None = None,
) -> None:
    """Exercise the closed object/array subset without implementing TASK-203."""
    root_schema = root_schema or schema
    reference = schema.get("$ref")
    if isinstance(reference, str):
        case.assertTrue(reference.startswith("#/$defs/"))
        definition = root_schema["$defs"][reference.removeprefix("#/$defs/")]
        assert_closed_shape(case, definition, value, root_schema)
        return
    alternatives = schema.get("oneOf")
    if isinstance(alternatives, list):
        matches = 0
        for alternative in alternatives:
            try:
                assert_closed_shape(case, alternative, value, root_schema)
            except AssertionError:
                continue
            matches += 1
        case.assertEqual(matches, 1)
        return
    if "const" in schema:
        case.assertEqual(value, schema["const"])
    if "enum" in schema:
        case.assertIn(value, schema["enum"])
    expected = schema.get("type")
    if expected == "object":
        case.assertIs(type(value), dict)
        assert isinstance(value, dict)
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        case.assertTrue(set(required).issubset(value))
        additional = schema.get("additionalProperties")
        if additional is False:
            case.assertEqual(set(value) - set(properties), set())
        for key, item in value.items():
            child = properties.get(key, additional)
            if isinstance(child, dict):
                assert_closed_shape(case, child, item, root_schema)
    elif expected == "array":
        case.assertIs(type(value), list)
        assert isinstance(value, list)
        child = schema.get("items")
        if isinstance(child, dict):
            for item in value:
                assert_closed_shape(case, child, item, root_schema)
    elif expected == "string":
        case.assertIs(type(value), str)
        pattern = schema.get("pattern")
        if isinstance(pattern, str):
            case.assertIsNotNone(re.fullmatch(pattern, value))
    elif expected == "integer":
        case.assertIs(type(value), int)
    elif expected == "boolean":
        case.assertIs(type(value), bool)
    elif expected == "null":
        case.assertIsNone(value)


class JsonLoadingTests(unittest.TestCase):
    def test_load_json_rejects_duplicate_keys_at_any_depth(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text(
                '{"schema_version":2,"nested":{"id":1,"id":2}}', encoding="utf-8")
            with self.assertRaisesRegex(catalog.CatalogError, "duplicate key: id"):
                catalog.load_json(path)

    def test_load_json_rejects_non_object_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "array.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(catalog.CatalogError, "root must be an object"):
                catalog.load_json(path)


class ArtifactCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = catalog.load_artifact_catalog(ROOT)

    def test_catalog_is_closed_current_and_deterministically_ordered(self) -> None:
        self.assertEqual(set(self.data), {"schema_version", "artifacts"})
        self.assertEqual(self.data["schema_version"], 2)
        entries = self.data["artifacts"]
        ids = [entry["id"] for entry in entries]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("pull-request-draft", ids)
        writable_v2 = {
            entry["id"] for entry in entries
            if entry["writable_schema_version"] == 2
        }
        self.assertEqual(writable_v2, set(ids))
        self.assertTrue(all(
            entry["writable_schema_version"] == 2 for entry in entries
        ))
        self.assertTrue(any(entry["schema"] is None for entry in entries))

    def test_catalog_resolves_only_existing_owner_colocated_assets(self) -> None:
        resolved = catalog.resolve_artifact_contracts(ROOT, self.data)
        self.assertEqual([item.id for item in resolved],
                         sorted(item.id for item in resolved))
        for item in resolved:
            self.assertTrue(item.owner_contract.is_file())
            if item.template is not None:
                self.assertTrue(item.template.is_file())
                self.assertTrue(
                    item.template.is_relative_to(item.owner_directory))
            if item.schema is not None:
                self.assertTrue(item.schema.is_file())
                self.assertTrue(
                    item.schema.is_relative_to(item.owner_directory))

    def test_unknown_entry_field_is_rejected(self) -> None:
        changed = copy.deepcopy(self.data)
        changed["artifacts"][0]["procedure"] = "duplicated authority"
        with self.assertRaisesRegex(catalog.CatalogError, "unknown field: procedure"):
            catalog.validate_artifact_catalog(changed)

    def test_unknown_nested_field_is_rejected(self) -> None:
        changed = copy.deepcopy(self.data)
        changed["artifacts"][0]["owner"]["path"] = "elsewhere"
        with self.assertRaisesRegex(catalog.CatalogError, "unknown field: path"):
            catalog.validate_artifact_catalog(changed)

    def test_nondeterministic_order_and_duplicate_id_are_rejected(self) -> None:
        changed = copy.deepcopy(self.data)
        changed["artifacts"][0], changed["artifacts"][1] = (
            changed["artifacts"][1], changed["artifacts"][0])
        with self.assertRaisesRegex(catalog.CatalogError, "sorted by id"):
            catalog.validate_artifact_catalog(changed)

        changed = copy.deepcopy(self.data)
        changed["artifacts"][1]["id"] = changed["artifacts"][0]["id"]
        with self.assertRaisesRegex(catalog.CatalogError, "duplicate artifact id"):
            catalog.validate_artifact_catalog(changed)

    def test_unsafe_asset_paths_are_rejected(self) -> None:
        for unsafe in (
            "/tmp/schema.json",
            "../schema.json",
            "skills\\x\\schema.json",
            "C:/outside",
            "c:relative",
            "assets/schema.json\x00secret",
            "assets/schema.json\x1fsecret",
            "assets/schema.json\x7fsecret",
        ):
            with self.subTest(path=repr(unsafe)):
                changed = copy.deepcopy(self.data)
                changed["artifacts"][0]["schema"] = unsafe
                with self.assertRaisesRegex(catalog.CatalogError, "safe relative path"):
                    catalog.validate_artifact_catalog(changed)

    def test_all_path_entrypoints_raise_redacted_catalog_error(self) -> None:
        unsafe = "C:/outside\x00secret"
        changed = copy.deepcopy(self.data)
        changed["artifacts"][0]["schema"] = unsafe
        calls = (
            lambda: catalog.validate_artifact_catalog(changed),
            lambda: catalog.resolve_artifact_contracts(ROOT, changed),
            lambda: catalog.index_pointers(
                f"- [Unsafe]({unsafe}) — Deliberately unsafe pointer.\n"),
            lambda: catalog.resolve_repository_pointer(ROOT, unsafe),
        )
        for call in calls:
            with self.subTest(call=call):
                with self.assertRaises(catalog.CatalogError) as caught:
                    call()
                self.assertIn("safe relative path", str(caught.exception))
                self.assertNotIn("secret", str(caught.exception))

    def test_missing_pointer_and_owner_escape_are_rejected(self) -> None:
        changed = copy.deepcopy(self.data)
        changed["artifacts"][0]["schema"] = changed["artifacts"][1]["template"]
        with self.assertRaisesRegex(catalog.CatalogError, "outside owner"):
            catalog.resolve_artifact_contracts(ROOT, changed)

        changed = copy.deepcopy(self.data)
        changed["artifacts"][0]["schema"] = (
            "skills/domain-model/assets/does-not-exist.schema.json"
        )
        with self.assertRaisesRegex(catalog.CatalogError, "does not resolve"):
            catalog.resolve_artifact_contracts(ROOT, changed)

    def test_symlink_pointer_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            owner = root / ".agents" / "skills" / "owner"
            owner.mkdir(parents=True)
            (owner / "SKILL.md").write_text("# owner\n", encoding="utf-8")
            target = owner / "target.md"
            target.write_text("target\n", encoding="utf-8")
            (owner / "link.md").symlink_to(target)
            data = {
                "schema_version": 2,
                "artifacts": [minimal_entry("sample", "skills/owner/link.md")],
            }
            with self.assertRaisesRegex(catalog.CatalogError, "symlink"):
                catalog.resolve_artifact_contracts(root, data)

    def test_agents_symlink_is_rejected_for_internal_and_supplied_catalogs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            external = base / "external-agents"
            owner = external / "skills" / "owner"
            owner.mkdir(parents=True)
            (owner / "SKILL.md").write_text("# owner\n", encoding="utf-8")
            (external / "artifact-catalog.json").write_text(
                json.dumps({
                    "schema_version": 2,
                    "artifacts": [minimal_entry("sample", None)],
                }),
                encoding="utf-8",
            )
            root = base / "repository"
            root.mkdir()
            (root / ".agents").symlink_to(external, target_is_directory=True)

            with self.assertRaisesRegex(catalog.CatalogError, "boundary.*symlink"):
                catalog.load_artifact_catalog(root)
            with self.assertRaisesRegex(catalog.CatalogError, "boundary.*symlink"):
                catalog.resolve_artifact_contracts(root)
            with self.assertRaisesRegex(catalog.CatalogError, "boundary.*symlink"):
                catalog.resolve_artifact_contracts(
                    root,
                    {"schema_version": 2, "artifacts": [
                        minimal_entry("sample", None)]},
                )

    def test_owner_ancestor_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            agents = root / ".agents"
            external = root / "external-skills"
            owner = external / "owner"
            owner.mkdir(parents=True)
            (owner / "SKILL.md").write_text("# owner\n", encoding="utf-8")
            agents.mkdir()
            (agents / "skills").symlink_to(
                external, target_is_directory=True)
            data = {"schema_version": 2, "artifacts": [
                minimal_entry("sample", None)]}
            with self.assertRaisesRegex(catalog.CatalogError, "ancestor.*symlink"):
                catalog.resolve_artifact_contracts(root, data)

    def test_repository_root_symlink_is_rejected_for_both_entrypoints(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            real_root = base / "real"
            owner = real_root / ".agents" / "skills" / "owner"
            owner.mkdir(parents=True)
            (owner / "SKILL.md").write_text("# owner\n", encoding="utf-8")
            data = {"schema_version": 2, "artifacts": [
                minimal_entry("sample", None)]}
            (real_root / ".agents" / "artifact-catalog.json").write_text(
                json.dumps(data), encoding="utf-8")
            linked_root = base / "linked-root"
            linked_root.symlink_to(real_root, target_is_directory=True)

            with self.assertRaisesRegex(catalog.CatalogError, "root.*symlink"):
                catalog.load_artifact_catalog(linked_root)
            with self.assertRaisesRegex(catalog.CatalogError, "root.*symlink"):
                catalog.resolve_artifact_contracts(linked_root, data)

    def test_symlinked_repository_ancestor_is_rejected_by_all_entrypoints(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            real_parent = base / "real-parent"
            root = real_parent / "repository"
            owner = root / ".agents" / "skills" / "owner"
            owner.mkdir(parents=True)
            (root / ".agents" / "indexes").mkdir()
            (owner / "SKILL.md").write_text("# owner\n", encoding="utf-8")
            data = {"schema_version": 2, "artifacts": [
                minimal_entry("sample", None)]}
            (root / ".agents" / "artifact-catalog.json").write_text(
                json.dumps(data), encoding="utf-8")
            linked_parent = base / "linked-parent"
            linked_parent.symlink_to(real_parent, target_is_directory=True)
            linked_root = linked_parent / "repository"

            calls = (
                lambda: catalog.load_artifact_catalog(linked_root),
                lambda: catalog.resolve_artifact_contracts(linked_root),
                lambda: catalog.resolve_artifact_contracts(linked_root, data),
                lambda: catalog.resolve_repository_pointer(
                    linked_root, "../artifact-catalog.json"),
            )
            for call in calls:
                with self.subTest(call=call):
                    with self.assertRaises(catalog.CatalogError) as caught:
                        call()
                    self.assertIn("ancestor is a symlink",
                                  str(caught.exception))
                    self.assertNotIn(str(base), str(caught.exception))

    def test_normal_temporary_repository_root_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "normal" / "repository"
            owner = root / ".agents" / "skills" / "owner"
            owner.mkdir(parents=True)
            (root / ".agents" / "indexes").mkdir()
            (owner / "SKILL.md").write_text("# owner\n", encoding="utf-8")
            data = {"schema_version": 2, "artifacts": [
                minimal_entry("sample", None)]}
            (root / ".agents" / "artifact-catalog.json").write_text(
                json.dumps(data), encoding="utf-8")

            self.assertEqual(catalog.load_artifact_catalog(root), data)
            self.assertEqual(len(catalog.resolve_artifact_contracts(root)), 1)
            self.assertEqual(
                len(catalog.resolve_artifact_contracts(root, data)), 1)
            self.assertEqual(
                catalog.resolve_repository_pointer(
                    root, "../artifact-catalog.json"),
                (root / ".agents" / "artifact-catalog.json").resolve(),
            )

    def test_root_modes_have_closed_combinations(self) -> None:
        expected = {
            "approval-policy": ("fixed", None, ".agents"),
            "compliance-event": ("colocated", None, None),
            "review-report": ("caller-selected", "work", ".work"),
        }
        for entry in self.data["artifacts"]:
            location = entry["root"]
            if entry["id"] in expected:
                self.assertEqual(
                    (location["mode"], location["key"], location["fallback"]),
                    expected[entry["id"]],
                )

        invalid = (
            {"mode": "fixed", "key": "work", "fallback": ".work"},
            {"mode": "fixed", "key": None, "fallback": None},
            {"mode": "project", "key": None, "fallback": ".work"},
            {"mode": "colocated", "key": "evidence", "fallback": None},
            {"mode": "colocated", "key": None, "fallback": "evidence"},
            {"mode": "caller-selected", "key": None, "fallback": ".work"},
        )
        for location in invalid:
            with self.subTest(location=location):
                changed = copy.deepcopy(self.data)
                changed["artifacts"][0]["root"] = location
                with self.assertRaisesRegex(catalog.CatalogError, "root combination"):
                    catalog.validate_artifact_catalog(changed)
                with self.assertRaisesRegex(catalog.CatalogError, "root combination"):
                    catalog.resolve_artifact_contracts(ROOT, changed)


def minimal_entry(identifier: str, template: str | None) -> dict[str, object]:
    return {
        "id": identifier,
        "format": "markdown",
        "owner": {"kind": "skill", "name": "owner"},
        "template": template,
        "schema": None,
        "lifecycle": None,
        "root": {"mode": "fixed", "key": None, "fallback": ".work"},
        "path_patterns": ["<root>/sample.md"],
        "split": {"mode": "never", "warning_tokens": None},
        "writable_schema_version": 1,
        "requires_modules": [],
        "variants": [],
    }


class GlobalSchemaTests(unittest.TestCase):
    def test_global_schemas_declare_2020_12_versioned_urns_and_closed_roots(self) -> None:
        for name in (
            "kit-catalog.schema.json",
            "artifact-catalog.schema.json",
            "manifest.schema.json",
            "markdown-document.schema.json",
        ):
            with self.subTest(schema=name):
                schema = load_schema(name)
                self.assertEqual(
                    schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertRegex(
                    schema["$id"], r"^urn:agentic-sdlc-kit:[a-z-]+:v2$")
                self.assertEqual(schema["type"], "object")
                self.assertIs(schema["additionalProperties"], False)

    def test_all_global_safe_path_patterns_reject_drives_and_controls(self) -> None:
        for name in (
            "kit-catalog.schema.json",
            "artifact-catalog.schema.json",
            "manifest.schema.json",
            "markdown-document.schema.json",
        ):
            schema = load_schema(name)
            safe_path = schema["$defs"]["safe_path"]
            assert_closed_shape(
                self, safe_path, ".agents/valid/path.json", schema)
            for unsafe in ("C:/outside", "c:relative", "bad\x00path", "bad\x1fpath", "bad\x7fpath"):
                with self.subTest(schema=name, path=repr(unsafe)):
                    with self.assertRaises(AssertionError):
                        assert_closed_shape(self, safe_path, unsafe, schema)

    def test_current_artifact_catalog_matches_closed_schema_root_combinations(self) -> None:
        schema = load_schema("artifact-catalog.schema.json")
        fixture = catalog.load_artifact_catalog(ROOT)
        assert_closed_shape(self, schema, fixture)
        fixture["artifacts"][0]["root"] = {
            "mode": "fixed", "key": "work", "fallback": ".work"}
        with self.assertRaises(AssertionError):
            assert_closed_shape(self, schema, fixture)

    def test_future_kit_catalog_fixture_and_unknown_field_mutation(self) -> None:
        schema = load_schema("kit-catalog.schema.json")
        fixture = {
            "schema_version": 2,
            "kit_version": "2.1.0",
            "skill_groups": {"core": ["implement"], "utilities": ["setup"], "optional": []},
            "modules": [{"name": "evidence", "description": "Evidence", "depends_on": []}],
            "global_resources": [".agents/artifact-catalog.json"],
            "profiles": {
                "default": {"skills": ["implement", "setup"], "modules": []},
                "full": {"skills": ["implement", "setup"], "modules": ["evidence"]},
            },
        }
        assert_closed_shape(self, schema, fixture)
        unsafe_fixture = copy.deepcopy(fixture)
        unsafe_fixture["global_resources"] = ["C:/outside"]
        with self.assertRaises(AssertionError):
            assert_closed_shape(self, schema, unsafe_fixture)
        fixture["profiles"]["default"]["lifecycle"] = "active"
        with self.assertRaises(AssertionError):
            assert_closed_shape(self, schema, fixture)

    def test_future_manifest_fixture_and_unknown_field_mutation(self) -> None:
        schema = load_schema("manifest.schema.json")
        fixture = {
            "schema_version": 2,
            "kit_version": "2.1.0",
            "request": {"profile": "default", "explicit_components": []},
            "components": [{
                "kind": "skill", "name": "implement",
                "path": ".agents/skills/implement", "ownership": "managed",
                "sha256": "0" * 64,
            }],
            "global_resources": [{
                "path": ".agents/artifact-catalog.json", "ownership": "managed",
                "sha256": "1" * 64,
            }],
        }
        assert_closed_shape(self, schema, fixture)
        unsafe_fixture = copy.deepcopy(fixture)
        unsafe_fixture["components"][0]["path"] = "c:relative"
        with self.assertRaises(AssertionError):
            assert_closed_shape(self, schema, unsafe_fixture)
        fixture["request"]["legacy"] = True
        with self.assertRaises(AssertionError):
            assert_closed_shape(self, schema, fixture)

    def test_markdown_normalized_fixture_contract_is_closed(self) -> None:
        schema = load_schema("markdown-document.schema.json")
        fixture = {
            "metadata": {
                "schema_version": 2,
                "id": "SPEC-002",
                "type": "specification",
                "sources": ["confirmed-request"],
                "status": "approved",
            },
            "h1": "Harness v2",
            "sections": ["Context"],
            "local_ids": [{"kind": "requirement", "id": "REQ-001"}],
            "references": ["SPEC-002#REQ-001"],
            "placeholders": [],
        }
        assert_closed_shape(self, schema, fixture)
        fixture["metadata"]["updated_at"] = "never"
        with self.assertRaises(AssertionError):
            assert_closed_shape(self, schema, fixture)


class IntentIndexAndCompatibilityTests(unittest.TestCase):
    def test_index_is_non_authoritative_and_all_local_pointers_resolve(self) -> None:
        text = (AGENTS / "indexes" / "by-intent.md").read_text(encoding="utf-8")
        self.assertIn("non-authoritative", text.lower())
        self.assertNotRegex(
            text, r"\b(?:draft|approved|implemented|verified|blocked|ready|in-progress|done|stale)\b")
        self.assertNotIn(" -> ", text)
        pointers = catalog.index_pointers(text)
        artifact_catalog = catalog.load_artifact_catalog(ROOT)
        expected = {
            "../artifact-catalog.json", "../kit-catalog.json",
            "../skills/contribute/SKILL.md",
        }
        for entry in artifact_catalog["artifacts"]:
            owner = entry["owner"]
            group = "skills" if owner["kind"] == "skill" else "modules"
            contract = "SKILL.md" if owner["kind"] == "skill" else "MODULE.md"
            expected.add(f"../{group}/{owner['name']}/{contract}")
        self.assertEqual(pointers, sorted(expected))
        self.assertEqual(pointers, sorted(pointers))
        self.assertEqual(len(pointers), len(set(pointers)))
        for pointer in pointers:
            self.assertTrue(catalog.resolve_repository_pointer(
                ROOT, pointer).exists())

    def test_index_rejects_unsafe_pointer_and_non_discriminative_rows(self) -> None:
        for unsafe in (
            "../../outside.md",
            "C:/outside",
            "c:relative",
            "../C:/outside",
            "../c:relative",
            "bad\x00path",
        ):
            with self.subTest(path=repr(unsafe)):
                with self.assertRaisesRegex(catalog.CatalogError, "safe relative path"):
                    catalog.index_pointers(
                        f"- [Unsafe]({unsafe}) — Deliberately unsafe pointer.\n")
        for unsafe in ("../C:/outside", "../c:relative"):
            with self.subTest(resolver_path=unsafe):
                with self.assertRaises(catalog.CatalogError) as caught:
                    catalog.resolve_repository_pointer(ROOT, unsafe)
                self.assertIn("safe relative path", str(caught.exception))
                self.assertNotIn(unsafe, str(caught.exception))
        with self.assertRaisesRegex(catalog.CatalogError, "discriminative text"):
            catalog.index_pointers(
                "- [Specs](../skills/write-spec/SKILL.md)\n")

    def test_pointer_resolver_rejects_symlink_agents_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            external = base / "external-agents"
            (external / "indexes").mkdir(parents=True)
            target = external / "owner.md"
            target.write_text("# External\n", encoding="utf-8")
            root = base / "repository"
            root.mkdir()
            (root / ".agents").symlink_to(external, target_is_directory=True)
            with self.assertRaisesRegex(catalog.CatalogError, "boundary.*symlink"):
                catalog.resolve_repository_pointer(root, "../owner.md")

    def test_unrelated_v1_writer_bytes_are_unchanged(self) -> None:
        observed = {
            relative: hashlib.sha256(
                (ROOT / relative).read_bytes()).hexdigest()
            for relative in UNCHANGED_V1_WRITER_HASHES
        }
        self.assertEqual(observed, UNCHANGED_V1_WRITER_HASHES)
        active_catalog = json.loads(
            (AGENTS / "kit-catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(active_catalog["schema_version"], 2)
        self.assertEqual(active_catalog["kit_version"], "2.1.0")


if __name__ == "__main__":
    unittest.main()

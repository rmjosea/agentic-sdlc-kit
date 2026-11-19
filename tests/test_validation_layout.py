from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
VALIDATION = ROOT / "scripts" / "validation"

ASSIGNED = {
    "distribution": {
        "load_catalog", "validate_catalog", "string_list", "duplicate_values",
        "module_cycle_errors", "transitive_module_dependencies", "directory_names",
        "validate_directory_set", "validate_skill", "validate_distribution_contract",
        "validate_global_resources",
    },
    "artifacts": {
        "_unique_json_object", "parse_frontmatter", "parse_project_json",
        "validate_approval_policy", "validate_project_config", "_evidence_object",
        "_evidence_string", "_evidence_string_array", "_evidence_enum",
        "_inspect_evidence_safety", "_evidence_scope_snapshot",
        "validate_evidence_document", "_load_json_asset",
        "_validate_contractual_schema_object", "validate_evidence_module",
        "validate_optional_evidence_module", "validate_compliance_event",
        "_schema_subset_accepts", "_compliance_schema_contract_errors",
        "validate_compliance_module", "validate_optional_compliance_module",
        "validate_enforcement_module", "validate_optional_enforcement_module",
        "validate_multi_repo_module", "validate_optional_multi_repo_module",
        "documented_kit_version", "validate_catalog_version", "read_template",
        "parse_template_frontmatter", "markdown_section", "declared_string_tokens",
        "validate_review_template", "validate_templates",
        "validate_source_artifact_catalog",
    },
    "documentation": {
        "_markdown_anchors", "validate_agents_bootstrap", "validate_markdown_links",
        "_contract_table", "_render_name_list", "_expect_contract_table",
        "_markdown_heading_section", "_expect_section_commands",
        "validate_readme_skill_table", "validate_documented_counts",
        "validate_public_documentation", "validate_provider_neutrality",
        "validate_document_links",
    },
    "semantics": {"validate_v1_source_coverage", "validate_repository", "main"},
}


def top_level_functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


class ValidationLayoutTests(unittest.TestCase):
    def test_assigned_function_sets_are_exact(self) -> None:
        for module, expected in ASSIGNED.items():
            with self.subTest(module=module):
                self.assertEqual(
                    top_level_functions(VALIDATION / f"{module}.py"), expected)

    def test_validation_modules_have_real_bodies_not_reexports(self) -> None:
        for module, expected in ASSIGNED.items():
            path = VALIDATION / f"{module}.py"
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imported = {
                alias.name for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
                for alias in node.names
            }
            self.assertFalse(imported & expected, module)
            self.assertTrue(expected, module)

    def test_entrypoint_has_only_cli_bodies_and_reexports_test_surface(self) -> None:
        path = ROOT / "scripts" / "validate.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        self.assertEqual(top_level_functions(path), {
                         "validate_repository", "main"})
        required = {
            node.attr for node in ast.walk(
                ast.parse(
                    (ROOT / "tests" / "test_validate.py").read_text(encoding="utf-8"))
            )
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "validator"
        }
        spec = importlib.util.spec_from_file_location("layout_validate", path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        self.assertTrue(required <= set(dir(module)))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                self.assertTrue(node.name in {"validate_repository", "main"})
                self.assertTrue(any(isinstance(item, ast.Return)
                                for item in node.body))

    def test_validation_modules_do_not_reexport_each_other_functions(self) -> None:
        for path in VALIDATION.glob("*.py"):
            if path.name == "__init__.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            local_functions = top_level_functions(path)
            for node in tree.body:
                if not isinstance(node, ast.ImportFrom) or not node.module:
                    continue
                if "validation" in node.module:
                    imported = {
                        alias.asname or alias.name for alias in node.names}
                    self.assertFalse(local_functions & imported, str(path))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENFORCEMENT = ROOT / ".agents/modules/enforcement"
CHECK = ENFORCEMENT / "check.py"
ASSIGNED = {
    "paths": {"_unique_object", "_relative_path", "_repository_path_syntax",
              "_display", "_safe_existing", "_root_relative_path", "_read_text",
              "_load_json", "_too_deep", "_walk_files", "_tree_hash",
              "_safe_checkout_path", "_git_ref", "_invalid_scalar_character",
              "_sensitive_query", "_unsafe_uri_value", "_safe_config_string",
              "_safe_remote", "_config_key_safety"},
    "project": {"_parse_project", "_config_issue", "_validate_approval_policy_config",
                "_validate_project_v2", "_catalog", "_dependency_closure",
                "_validate_modules", "_validate_manifest", "_validate_multi_repo"},
    "evidence": {"_schema_type", "_schema_ok", "_validate_evidence_document",
                 "_validate_evidence"},
    "artifacts": {"_frontmatter", "_split_refs", "_local_source_reference",
                  "_parse_tasks", "_validate_artifacts"},
    "compliance": {"_compliance_regular_reference", "_compliance_safe_strings",
                   "_compliance_policy", "_compliance_nested_order",
                   "_validate_compliance_event", "_validate_compliance"},
    "report": {"_issue_key", "_render"},
}


def functions(path: Path) -> set[str]:
    return {node.name for node in ast.parse(path.read_text()).body
            if isinstance(node, ast.FunctionDef)}


class EnforcementLayoutTests(unittest.TestCase):
    def test_assigned_function_sets_are_exact(self) -> None:
        for module, expected in ASSIGNED.items():
            with self.subTest(module=module):
                self.assertEqual(
                    functions(ENFORCEMENT / "lib" / f"{module}.py"), expected)

    def test_check_holds_only_cli_functions(self) -> None:
        self.assertEqual(functions(CHECK), {
                         "_validate_extensions", "_run", "_parse_args", "main"})

    def test_package_has_all_expected_files_and_no_cross_reexported_functions(self) -> None:
        expected = {"__init__.py", "artifacts.py", "compliance.py", "evidence.py",
                    "paths.py", "project.py", "report.py"}
        self.assertEqual({path.name for path in (
            ENFORCEMENT / "lib").glob("*.py")}, expected)
        for path in (ENFORCEMENT / "lib").glob("*.py"):
            tree = ast.parse(path.read_text())
            local = functions(path)
            for node in tree.body:
                if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("lib"):
                    self.assertTrue(local.isdisjoint(
                        alias.asname or alias.name for alias in node.names))

    def test_existing_validator_surface_stays_executable(self) -> None:
        tree = ast.parse(CHECK.read_text())
        self.assertTrue(any(isinstance(node, ast.If) for node in tree.body))
        source = CHECK.read_text()
        self.assertIn("Path(__file__).parent", source)
        self.assertNotIn(".resolve()", source)
        self.assertIn("sys.exit(main())", source)


if __name__ == "__main__":
    unittest.main()

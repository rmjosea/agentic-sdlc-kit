from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from scripts.contracts import project, review_evidence, source_lifecycle, task_artifacts
from tests.test_review_evidence_contracts import audit_text, event, evidence_record

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / ".agents/modules/enforcement/check.py"
PROJECT_SCHEMA = ROOT / ".agents/skills/setup/assets/project.schema.json"
PROJECT_TEMPLATE = ROOT / ".agents/skills/setup/assets/project.template.json"


class EnforcementEquivalenceTests(unittest.TestCase):
    def run_installed(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CHECK), "--root",
             str(root), "--format", "json"],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={**os.environ, "PYTHONPATH": ""}, check=False,
        )

    def test_project_config_source_and_installed_decisions_agree(self) -> None:
        cases = {
            "valid": json.loads(PROJECT_TEMPLATE.read_text(encoding="utf-8")),
            "unknown-field": {
                **json.loads(PROJECT_TEMPLATE.read_text(encoding="utf-8")),
                "unknown": True,
            },
            "invalid-root": {
                **json.loads(PROJECT_TEMPLATE.read_text(encoding="utf-8")),
                "roots": {
                    **json.loads(PROJECT_TEMPLATE.read_text(encoding="utf-8"))["roots"],
                    "work": "../outside",
                },
            },
        }
        for name, value in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                (root / ".agents").mkdir()
                (root / ".agents/project.json").write_text(
                    json.dumps(value), encoding="utf-8")
                diagnostics = project.validate_project(value, PROJECT_SCHEMA,
                                                       module_names=[])
                installed = self.run_installed(root)
                source_accepts = not diagnostics
                installed_accepts = installed.returncode == 0
                self.assertEqual(source_accepts, installed_accepts,
                                 installed.stdout + installed.stderr)

    def test_default_and_full_installs_run_self_contained_checker(self) -> None:
        expected_lib = {
            "__init__.py", "artifacts.py", "compliance.py", "evidence.py",
            "paths.py", "project.py", "report.py",
        }
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            decoy = workspace / "decoy"
            (decoy / "lib").mkdir(parents=True)
            (decoy / "lib/__init__.py").write_text(
                "raise RuntimeError('decoy imported')\n", encoding="utf-8")
            for profile in ("default", "full"):
                target = workspace / profile
                target.mkdir()
                subprocess.run(["git", "init", "--quiet", str(target)], check=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                install_args = [
                    sys.executable, str(
                        ROOT / "scripts/install.py"), str(target),
                    "--profile", profile,
                ]
                if profile == "default":
                    install_args.extend(["--with", "enforcement"])
                installed = subprocess.run(
                    install_args, text=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                self.assertEqual(installed.returncode, 0,
                                 installed.stdout + installed.stderr)
                checker = target / ".agents/modules/enforcement/check.py"
                self.assertEqual(
                    {path.name for path in (
                        checker.parent / "lib").glob("*.py")},
                    expected_lib,
                )
                for output_format in ("human", "json"):
                    result = subprocess.run(
                        [sys.executable, str(checker), "--root", str(target),
                         "--format", output_format], cwd=decoy, text=True,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        env={**os.environ, "PYTHONPATH": str(decoy)}, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stdout + result.stderr)

    def test_remaining_equivalence_families_are_blocked_by_v1_v2_skew(self) -> None:
        """TASK-215/217 must remove this forcing guard and add the corpus families."""
        installed_evidence = (
            ROOT / ".agents/modules/enforcement/lib/evidence.py"
        ).read_text(encoding="utf-8")
        installed_compliance = (
            ROOT / ".agents/modules/enforcement/lib/compliance.py"
        ).read_text(encoding="utf-8")
        self.assertIn("SCHEMA_VERSION = 1", installed_evidence)
        self.assertIn("SCHEMA_VERSION = 1", installed_compliance)

        v2_evidence = evidence_record()
        self.assertIsInstance(
            review_evidence.validate_evidence_record(v2_evidence), dict)
        v1_evidence = dict(v2_evidence)
        v1_evidence["schema_version"] = 1
        with self.assertRaises(Exception):
            review_evidence.validate_evidence_record(v1_evidence)

        v2_audit = audit_text(event(1, "2025-01-01T00:00:00Z"))
        self.assertTrue(review_evidence.validate_audit_jsonl(v2_audit))
        v1_event = event(1, "2025-01-01T00:00:00Z")
        v1_event["schema_version"] = 1
        with self.assertRaises(Exception):
            review_evidence.validate_audit_jsonl(
                json.dumps(v1_event, separators=(",", ":")) + "\n")

        # The installed side must move to schema version 2 before these families
        # can enter the shared source/installed AC-013 corpus.


if __name__ == "__main__":
    unittest.main()

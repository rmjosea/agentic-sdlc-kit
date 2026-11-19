#!/usr/bin/env python3
"""Unit tests for context_search, check_companions, metrics_report, and ralph-loop.sh."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_tool(name: str):
    path = ROOT / ".agents" / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NewToolsTests(unittest.TestCase):
    def test_context_search_vault_and_code_modes(self) -> None:
        context_search = _load_tool("context_search")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault_repos = root / "vault" / "repositorios"
            vault_repos.mkdir(parents=True)
            (root / "src").mkdir()
            (root / "src" / "offers.py").write_text("class OfferService:\n    pass\n", encoding="utf-8")
            (vault_repos / "offers-svc.md").write_text(
                "---\ntags:\n  - tipo/back\n---\n# offers-svc\nUses [[kafka]] and `src/offers.py`.\nSelector CSS: `app-offer-modal`\n",
                encoding="utf-8",
            )
            report = context_search.search_context(root, ["offers", "modal"])
            self.assertTrue(report["valid"])
            self.assertEqual(report["scope_used"], "vault")
            self.assertEqual(len(report["results"]), 1)
            first = report["results"][0]
            self.assertIn("src/offers.py", first["verified_code_paths"])
            self.assertIn("app-offer-modal", first["selectors"])
            self.assertIn("kafka", first["wikilinks"])

            code_report = context_search.search_context(root, ["OfferService"], scope="code")
            self.assertEqual(code_report["scope_used"], "code")
            self.assertTrue(any(r["path"] == "src/offers.py" for r in code_report["results"]))
            code_first = code_report["results"][0]
            self.assertTrue(any("class OfferService" in s for s in code_first["symbols"]))
            self.assertTrue(any("L1:" in m for m in code_first["matched_lines"]))

    def test_check_companions_detects_drift_and_passes_when_aligned(self) -> None:
        check_companions = _load_tool("check_companions")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fdir = root / "features" / "042-reject"
            fdir.mkdir(parents=True)
            (fdir / "api.md").write_text(
                '# API\nPOST /api/v1/reject\n- `reasonCode`: string\n- data-testid="hm-reject-btn"\n',
                encoding="utf-8",
            )
            (fdir / "event.md").write_text(
                "# Event\n- Event: `offer.candidate.rejected.v1`\n",
                encoding="utf-8",
            )
            src = root / "src"
            src.mkdir()
            (src / "handler.py").write_text(
                'payload = {"reason_code": "GAP"}\n',
                encoding="utf-8",
            )
            bad = check_companions.verify_companions(root, "features/042-reject")
            self.assertFalse(bad["valid"])
            kinds = {f["kind"] for f in bad["findings"]}
            self.assertIn("FIELD_NAMING_DRIFT", kinds)
            self.assertIn("MISSING_DATA_TESTID", kinds)
            self.assertIn("MISSING_EVENT_CONTRACT", kinds)

            (src / "handler.py").write_text(
                'payload = {"reasonCode": "GAP"}\nevt = "offer.candidate.rejected.v1"\n'
                'html = \'<button data-testid="hm-reject-btn"></button>\'\n',
                encoding="utf-8",
            )
            good = check_companions.verify_companions(root, "features/042-reject")
            self.assertTrue(good["valid"])
            self.assertEqual(good["findings"], [])

    def test_metrics_report_and_run_tasks_dry_run(self) -> None:
        metrics_report = _load_tool("metrics_report")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tasks_file = root / "tasks.md"
            tasks_file.write_text(
                "### repo-back\n"
                "- [x] **T01** · `[A]` · `accion` · `repo: repo-back` · `-> AC-1`\n"
                "- [ ] **T02** · `[A]` · `verificacion` · `repo: repo-back` · `-> AC-1`\n"
                "### repo-front\n"
                "- [ ] **T03** · `[I]` · `accion` · `repo: repo-front` · `-> AC-2`\n",
                encoding="utf-8",
            )
            metrics_dir = root / ".work"
            metrics_dir.mkdir()
            (metrics_dir / "metrics.jsonl").write_text(
                '{"task_id":"T01","repo":"repo-back","modality":"A","effort":"med","model":"sonnet","attempt":1,"status":"passed","duration_sec":12,"env_edit_iterations":0}\n',
                encoding="utf-8",
            )
            report = metrics_report.build_metrics_report(root, "tasks.md", ".work/metrics.jsonl")
            self.assertTrue(report["valid"])
            self.assertEqual(report["tasks_summary"]["total_tasks"], 3)
            self.assertEqual(report["tasks_summary"]["completed_tasks"], 1)
            self.assertEqual(report["telemetry"]["pass_at_1_rate"], 100.0)

            runner = ROOT / ".agents" / "tools" / "ralph-loop.sh"
            proc = subprocess.run(
                ["bash", str(runner), str(tasks_file), "--repo", "repo-back", "--dry-run"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("[DRY-RUN] Task T02", proc.stdout)
            self.assertIn("effort=high", proc.stdout)


if __name__ == "__main__":
    unittest.main()

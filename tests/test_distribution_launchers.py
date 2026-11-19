from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _create_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Tester"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
    (path / "README.md").write_text("# Target Repository\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-m", "Initial commit"], check=True, capture_output=True)


class DistributionLaunchersTests(unittest.TestCase):
    def test_package_json_manifest(self) -> None:
        pkg_path = ROOT / "package.json"
        self.assertTrue(pkg_path.is_file(), "package.json must exist in root")
        data = json.loads(pkg_path.read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "agentic-sdlc-kit")
        self.assertEqual(data["version"], "2.1.0")
        self.assertEqual(data["bin"]["agentic-sdlc-kit"], "./bin/cli.js")
        self.assertTrue((ROOT / "bin" / "cli.js").is_file(), "bin/cli.js must exist")

    def test_claude_plugin_manifests(self) -> None:
        marketplace_path = ROOT / ".claude-plugin" / "marketplace.json"
        plugin_path = ROOT / ".claude-plugin" / "plugin.json"
        self.assertTrue(marketplace_path.is_file(), "marketplace.json must exist")
        self.assertTrue(plugin_path.is_file(), "plugin.json must exist")

        market_data = json.loads(marketplace_path.read_text(encoding="utf-8"))
        self.assertEqual(market_data["name"], "agentic-sdlc-kit")
        self.assertTrue(len(market_data.get("plugins", [])) > 0)
        self.assertEqual(market_data["plugins"][0]["name"], "agentic-sdlc-kit")

        plugin_data = json.loads(plugin_path.read_text(encoding="utf-8"))
        self.assertEqual(plugin_data["name"], "agentic-sdlc-kit")
        self.assertEqual(plugin_data["version"], "2.1.0")

    def test_node_cli_help(self) -> None:
        cli_path = ROOT / "bin" / "cli.js"
        res = subprocess.run(
            ["node", str(cli_path), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("usage: install.py", res.stdout)
        self.assertIn("--profile", res.stdout)

    def test_node_cli_installs_into_explicit_target(self) -> None:
        cli_path = ROOT / "bin" / "cli.js"
        with tempfile.TemporaryDirectory() as tmp:
            target = (Path(tmp) / "repo").resolve()
            _create_git_repo(target)

            res = subprocess.run(
                ["node", str(cli_path), str(target), "--profile", "default"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            manifest = target / ".agents" / "agentic-sdlc-kit.json"
            self.assertTrue(manifest.is_file())
            agents_md = target / "AGENTS.md"
            self.assertTrue(agents_md.is_file())

            # Validate target with installed checker
            check_script = ROOT / ".agents" / "modules" / "enforcement" / "check.py"
            checker = subprocess.run(
                ["python3", str(check_script), "--root", str(target), "--format", "human"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(checker.returncode, 0, checker.stdout)
            self.assertIn("VALID", checker.stdout)

    def test_node_cli_installs_into_cwd(self) -> None:
        cli_path = ROOT / "bin" / "cli.js"
        with tempfile.TemporaryDirectory() as tmp:
            target = (Path(tmp) / "repo").resolve()
            _create_git_repo(target)

            res = subprocess.run(
                ["node", str(cli_path), "--profile", "default"],
                cwd=str(target),
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            manifest = target / ".agents" / "agentic-sdlc-kit.json"
            self.assertTrue(manifest.is_file())

    def test_shell_installer_local_path(self) -> None:
        install_sh = ROOT / "install.sh"
        self.assertTrue(install_sh.is_file(), "install.sh must exist")

        with tempfile.TemporaryDirectory() as tmp:
            target = (Path(tmp) / "repo").resolve()
            _create_git_repo(target)

            res = subprocess.run(
                [str(install_sh), str(target), "--profile", "default"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            manifest = target / ".agents" / "agentic-sdlc-kit.json"
            self.assertTrue(manifest.is_file())
            agents_md = target / "AGENTS.md"
            self.assertTrue(agents_md.is_file())


if __name__ == "__main__":
    unittest.main()

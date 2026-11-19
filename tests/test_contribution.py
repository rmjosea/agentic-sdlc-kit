from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / ".agents" / "skills" / \
    "contribute" / "scripts" / "check_contribution.py"
SKILL = ROOT / ".agents" / "skills" / "contribute" / "SKILL.md"
COMMITS = ROOT / ".agents" / "skills" / \
    "contribute" / "references" / "commits.md"
CHECKER_SPEC = importlib.util.spec_from_file_location(
    "contribution_checker", CHECKER)
assert CHECKER_SPEC and CHECKER_SPEC.loader
checker = importlib.util.module_from_spec(CHECKER_SPEC)
CHECKER_SPEC.loader.exec_module(checker)
PR_REQUIRED_SECTIONS = (
    "Purpose and why", "Change", "Scope", "Authoritative context",
    "Risk and operational impact", "Checks", "Requested feedback",
)


def run_git(root: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *arguments], cwd=root, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1",
             "GIT_CONFIG_GLOBAL": os.devnull},
    )


class Repository:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        run_git(self.root, "init", "--quiet")
        run_git(self.root, "config", "user.name", "Fixture")
        run_git(self.root, "config", "user.email", "fixture@example.invalid")
        self.write("tracked.txt", "base\n")
        run_git(self.root, "add", "tracked.txt")
        run_git(self.root, "commit", "--quiet", "-m", "Add baseline fixture")

    def write(self, relative: str, content: str | bytes) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def project(self, *, mode: str = "discover", trailers: list[str] | None = None) -> None:
        data = {
            "schema_version": 2,
            "roots": {"specs": "specs", "work": ".work", "adrs": None,
                      "evidence": None, "domain_context": None},
            "repositories": [], "enabled_modules": [],
            "tracker": {"kind": "none", "location": None, "labels": {}},
            "agent": {"mode": "guided"}, "review": {"mode": "risk-based"},
            "approval_policy": {"rules": []},
            "contribution": {"commit_mode": mode, "base_branch": None,
                             "required_trailers": trailers or [],
                             "pull_request_template": None,
                             "merge_strategy": "unknown"},
        }
        self.write(".agents/project.json", json.dumps(data) + "\n")

    def stage(self, relative: str, content: str) -> None:
        self.write(relative, content)
        run_git(self.root, "add", "--", relative)

    @staticmethod
    def file_state(path: Path) -> dict[str, object]:
        data = path.read_bytes()
        metadata = path.stat()
        return {
            "bytes": data,
            "sha256": hashlib.sha256(data).hexdigest(),
            "mtime_ns": metadata.st_mtime_ns,
            "size": metadata.st_size,
        }

    def snapshot(self) -> dict[str, object]:
        files: dict[str, str] = {}
        for path in sorted(self.root.rglob("*")):
            if ".git" in path.parts or not path.is_file():
                continue
            files[path.relative_to(self.root).as_posix()] = hashlib.sha256(
                path.read_bytes()).hexdigest()
        git_dir = self.root / ".git"
        logs = {
            path.relative_to(git_dir).as_posix(): self.file_state(path)
            for path in sorted((git_dir / "logs").rglob("*"))
            if path.is_file()
        }
        object_files = [
            path for path in (git_dir / "objects").rglob("*") if path.is_file()
        ]
        return {
            "head_commit": run_git(self.root, "rev-parse", "HEAD").stdout,
            "head_ref": self.file_state(git_dir / "HEAD"),
            "index": self.file_state(git_dir / "index"),
            "refs": run_git(
                self.root, "for-each-ref", "--format=%(refname)%00%(objectname)"
            ).stdout,
            "reflogs": logs,
            "status": run_git(
                self.root, "--no-optional-locks", "status", "--porcelain=v1", "-z"
            ).stdout,
            "files": files,
            "object_count": len(object_files),
        }

    def close(self) -> None:
        self.temporary.cleanup()


class ContributionCLI(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Repository()

    def tearDown(self) -> None:
        self.repo.close()

    def invoke(self, command: str, *arguments: str, stdin: bytes | None = None,
               fmt: str = "json", env: dict[str, str] | None = None) -> tuple[int, str, dict[str, object] | None]:
        process = subprocess.run(
            [sys.executable, str(CHECKER), command, "--root", str(self.repo.root),
             *arguments, "--format", fmt],
            input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, env=env,
        )
        output = process.stdout.decode("utf-8")
        self.assertEqual(process.stderr, b"")
        return process.returncode, output, json.loads(output) if fmt == "json" else None

    def assert_codes(self, report: dict[str, object], field: str, *codes: str) -> None:
        self.assertEqual([item["code"] for item in report[field]], list(codes))

    def test_no_policy_and_history_conventional_alone_remain_classic(self) -> None:
        self.repo.stage("tracked.txt", "next\n")
        run_git(self.repo.root, "commit", "--quiet",
                "-m", "feat: historical style")
        self.repo.stage("tracked.txt", "again\n")

        code, _, report = self.invoke("inspect")

        self.assertEqual(code, 0)
        self.assertEqual(report["policy"]["commit_mode"], "classic")
        self.assertEqual(report["policy"]["commit_mode_source"], "fallback")
        self.assertTrue(
            any(source["level"] == 4 for source in report["policy_sources"]))

    def test_project_explicit_classic_and_conventional(self) -> None:
        for mode in ("classic", "conventional"):
            with self.subTest(mode=mode):
                self.repo.project(mode=mode)
                code, _, report = self.invoke("inspect")
                self.assertEqual(code, 0)
                self.assertEqual(report["policy"]["commit_mode"], mode)
                self.assertEqual(
                    report["policy"]["commit_mode_source"], ".agents/project.json")

    def test_commit_project_config_failure_is_not_message_failure(self) -> None:
        self.repo.write(".agents/project.json", "{\n")

        code, _, report = self.invoke(
            "commit", "--message-file", "-", stdin=b"Add parser guard\n")

        self.assertEqual(code, 2)
        self.assert_codes(report, "errors", "unsafe-project-config")

    def test_unsupported_legacy_project_file_blocks_without_conversion(self) -> None:
        path = self.repo.write(".agents/project.md", "legacy project policy\n")
        before = self.repo.file_state(path)

        for command, arguments, stdin in (
            ("inspect", (), None),
            ("branch", ("--name", "describe-parser"), None),
            ("commit", ("--message-file", "-"), b"Add parser guard\n"),
        ):
            with self.subTest(command=command):
                code, _, report = self.invoke(
                    command, *arguments, stdin=stdin)
                self.assertEqual(code, 2)
                self.assert_codes(report, "errors", "unsafe-project-config")
                self.assertEqual(self.repo.file_state(path), before)
                self.assertFalse(
                    (self.repo.root / ".agents/project.json").exists())

    def test_pull_request_draft_and_observations_report_results(self) -> None:
        draft = (
            "# Add bounded contribution checks\n\n"
            "## Purpose and why\n\nProtect contribution validation.\n\n"
            "## Change\n\nAdd the local draft checker.\n\n"
            "## Scope\n\nChecker and documentation only.\n\n"
            "## Authoritative context\n\nSPEC-002 requirements.\n\n"
            "## Risk and operational impact\n\nNo external effects.\n\n"
            "## Checks\n\nTests are listed in observations.\n\n"
            "## Requested feedback\n\nReview the boundary.\n"
        )
        self.repo.write("draft.md", draft)
        self.repo.write("observations.json", json.dumps({
            "schema_version": 2,
            "checks": [
                {"name": "focused", "scope": "tests", "status": "passed",
                 "evidence_reference": "local"},
                {"name": "integration", "scope": "tests", "status": "failed",
                 "evidence_reference": "local"},
                {"name": "external", "scope": "none", "status": "not-run",
                 "evidence_reference": None},
            ],
        }) + "\n")

        code, _, report = self.invoke(
            "pull-request", "--draft-file", "draft.md",
            "--observations", "observations.json",
            "--expected-path", "draft.md")

        self.assertEqual(code, 1)
        self.assert_codes(report, "errors", "check-failed")
        self.assert_codes(report, "warnings", "check-not-run")
        self.assertEqual(report["pull_request"]["observed_checks"], [
            "focused", "integration"])
        self.assertEqual(report["pull_request"]
                         ["omitted_checks"], ["external"])

    def test_pull_request_template_placeholders_are_advisory_and_draft_sections_fail(self) -> None:
        self.repo.write(".github/pull_request_template.md",
                        "# Template\n\n## Purpose and why\n\n<ISSUE_ID>\n")
        self.repo.write(
            "draft.md", "# Add draft\n\n## Purpose and why\n\nWhy.\n")

        code, output, report = self.invoke(
            "pull-request", "--draft-file", "draft.md")

        self.assertEqual(code, 1)
        self.assert_codes(
            report, "errors", "draft-section-missing", "draft-section-missing",
            "draft-section-missing", "draft-section-missing", "draft-section-missing",
            "draft-section-missing")
        self.assertIn("<ISSUE_ID>", output)
        self.assertIn("template-placeholder-unresolved", output)

    def test_pull_request_asset_placeholders_are_detected(self) -> None:
        template = (SKILL.parent / "assets" / "pull-request.template.md").read_text(
            encoding="utf-8")
        tokens = sorted(set(checker.PLACEHOLDER_RE.findall(template)))
        base = "# Add draft\n\n" + "\n".join(
            "## " + section + "\n\nContent."
            for section in PR_REQUIRED_SECTIONS)
        for token in tokens:
            with self.subTest(token=token):
                self.repo.write("draft.md", base.replace("Content.", token, 1))
                code, _, report = self.invoke(
                    "pull-request", "--draft-file", "draft.md")
                self.assertEqual(code, 1)
                self.assertIn("draft-placeholder-unresolved", [
                    item["code"] for item in report["errors"]])

    def test_missing_configured_template_warns_before_default_fallback(self) -> None:
        self.repo.project()
        project = json.loads(
            (self.repo.root / ".agents/project.json").read_text(encoding="utf-8"))
        project["contribution"]["pull_request_template"] = ".github/configured.md"
        self.repo.write(".agents/project.json", json.dumps(project) + "\n")
        self.repo.write(".github/pull_request_template.md", "# Default\n")
        draft = "# Add draft\n\n" + "\n".join(
            "## " + section + "\n\nContent."
            for section in PR_REQUIRED_SECTIONS)
        self.repo.write("draft.md", draft)

        code, _, report = self.invoke(
            "pull-request", "--draft-file", "draft.md")

        self.assertEqual(code, 0, report)
        warning = next(item for item in report["warnings"]
                       if item["code"] == "configured-template-missing")
        self.assertEqual(warning["path"], ".github/configured.md")
        self.assertEqual(report["pull_request"]["template"],
                         ".github/pull_request_template.md")

    def test_squash_policy_reuses_commit_title_validation(self) -> None:
        self.repo.project(mode="conventional")
        project = json.loads(
            (self.repo.root / ".agents/project.json").read_text(encoding="utf-8"))
        project["contribution"]["merge_strategy"] = "squash"
        self.repo.write(".agents/project.json", json.dumps(project) + "\n")
        self.repo.write("draft.md", "# Add parser checks\n\n" +
                        "\n".join("## " + section + "\n\nContent."
                                  for section in PR_REQUIRED_SECTIONS))

        code, _, report = self.invoke(
            "pull-request", "--draft-file", "draft.md")

        self.assertEqual(code, 1)
        self.assert_codes(report, "errors", "conventional-header-invalid")
        self.assertEqual(report["commit"]["mode"], "conventional")

    def test_pull_request_stdin_exclusivity_and_input_diagnostics(self) -> None:
        process = subprocess.run(
            [sys.executable, str(CHECKER), "pull-request", "--root",
             str(self.repo.root), "--draft-file", "-", "--observations", "-",
             "--format", "json"], input=b"# Draft\n",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(process.stdout, b"")
        self.assertEqual(process.stderr, b"error: invalid invocation\n")

        self.repo.write("draft.md", b"\xff")
        code, output, report = self.invoke(
            "pull-request", "--draft-file", "draft.md")
        self.assertEqual(code, 2)
        self.assert_codes(report, "errors", "unsafe-draft-input")
        self.assertNotIn("\\xff", output)

        self.repo.write("draft.md", "# Draft\n")
        self.repo.write("observations.json",
                        '{"schema_version":2,"unknown":true}\n')
        code, output, report = self.invoke(
            "pull-request", "--draft-file", "draft.md",
            "--observations", "observations.json")
        self.assertEqual(code, 2)
        self.assert_codes(report, "errors", "unsafe-observations-input")
        self.assertNotIn("unknown", output)

    def test_free_form_commit_prose_is_confirmation_required_not_inferred(self) -> None:
        phrases = (
            "Commit messages must use classic Git style.",
            "Use Conventional Commits.",
            "Commit examples: feat: add parser and fix: handle timeout.",
            "Conventional Commits are not required.",
            "We never use Conventional Commits.",
            "If commits are inconsistent, releases become difficult.",
            "The classic format is described below.",
        )
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                path = self.repo.write(
                    "CONTRIBUTING.md", "Intro\n" + phrase + "\n")
                code, output, report = self.invoke("inspect")
                self.assertEqual(code, 0, report)
                self.assertEqual(report["policy"]["commit_mode"], "classic")
                self.assertEqual(
                    report["policy"]["commit_mode_source"], "fallback")
                self.assertEqual(
                    report["policy"]["commit_mode_state"], "confirmation-required")
                self.assert_codes(report, "warnings",
                                  "policy-confirmation-required")
                source = next(item for item in report["policy_sources"]
                              if item["path"] == "CONTRIBUTING.md")
                self.assertEqual(source["state"], "confirmation-required")
                self.assertEqual(source["relevant_lines"], [2])
                self.assertEqual(source["relevant_terms"], ["commit"])
                self.assertNotIn(phrase, output)
                path.unlink()
        self.repo.write("CONTRIBUTING.md", "Commit policy prose.\n")
        code, human, _ = self.invoke("inspect", fmt="human")
        self.assertEqual(code, 0)
        self.assertIn("commit mode state: confirmation-required", human)
        self.assertIn(
            "state=confirmation-required; lines=1; terms=commit", human)

    def test_templates_and_merge_evidence_are_inspect_only(self) -> None:
        self.repo.project(mode="discover")
        project = json.loads(
            (self.repo.root / ".agents/project.json").read_text(encoding="utf-8"))
        project["contribution"]["merge_strategy"] = "squash"
        project["contribution"]["pull_request_template"] = ".github/pull_request_template.md"
        self.repo.write(".agents/project.json", json.dumps(project) + "\n")
        self.repo.write(".github/pull_request_template.md",
                        "# Local template\n")
        code, _, inspected = self.invoke("inspect")
        self.assertEqual(code, 0)
        self.assertTrue(
            any(source["level"] == 3 for source in inspected["policy_sources"]))
        code, _, branch = self.invoke("branch", "--name", "describe-safety")
        self.assertEqual(code, 0)
        self.assertFalse(
            any(source["level"] == 3 for source in branch["policy_sources"]))

    def test_commit_prose_requires_confirmed_pair_for_affected_action(self) -> None:
        self.repo.write("CONTRIBUTING.md", "Use Conventional Commits.\n")
        self.repo.stage("tracked.txt", "next\n")
        code, _, report = self.invoke(
            "commit", "--message-file", "-", stdin=b"feat: add policy check\n")
        self.assertEqual(code, 1)
        self.assertIn("policy-confirmation-required", [
            item["code"] for item in report["errors"]])

        code, _, report = self.invoke(
            "commit", "--message-file", "-",
            "--confirmed-commit-mode", "conventional",
            "--policy-source", "CONTRIBUTING.md",
            stdin=b"feat: add policy check\n",
        )
        self.assertEqual(code, 0, report)
        self.assertEqual(report["policy"]["commit_mode"], "conventional")
        self.assertEqual(report["policy"]["commit_mode_state"], "resolved")
        self.assertEqual(report["policy"]["confirmed"], {
            "policy_source": "CONTRIBUTING.md",
            "commit_mode": "conventional",
            "branch_prefix": None,
        })
        self.assertNotIn("policy-confirmation-required", [
            item["code"] for item in report["warnings"]
            if item["field"] == "policy.commit_mode"])

    def test_clear_commitlint_content_requires_conventional(self) -> None:
        cases = {
            "commitlint.config.js": (
                "module.exports = {\n  extends: [\n"
                "    '@commitlint/config-conventional'\n  ]\n};\n"
            ),
            "commitlint.config.cjs": (
                "module.exports = {\n  parserPreset\n    :\n    {\n"
                "      name: 'conventional-changelog-conventionalcommits'\n"
                "    }\n};\n"
            ),
            ".commitlintrc.json": '{"parserPreset":"conventional-changelog-conventionalcommits"}\n',
            ".commitlintrc.yaml": "parserPreset:\n  name: config-conventional\n",
            "package.json": json.dumps({
                "scripts": {
                    "lint:commit": (
                        "commitlint --config\n ./config-conventional.js"
                    )
                }
            }) + "\n",
        }
        for relative, content in cases.items():
            with self.subTest(relative=relative):
                path = self.repo.write(relative, content)
                code, _, report = self.invoke("inspect")
                self.assertEqual(code, 0)
                self.assertEqual(
                    report["policy"]["commit_mode"], "conventional")
                self.assertEqual(
                    report["policy"]["commit_mode_source"], relative)
                path.unlink()

    def test_empty_or_ambiguous_commitlint_is_unknown_not_mandatory(self) -> None:
        for content in (
            "", "{}\n", '{"rules":{}}\n',
            '{"rules":{"type-empty":[2,"never"]}}\n',
            '{"rules":{"type-enum":[2,"always",["feat","fix"]],"subject-empty":[2,"never"]}}\n',
        ):
            with self.subTest(content=content):
                self.repo.write("commitlint.config.js", content)
                code, _, report = self.invoke("inspect")
                self.assertEqual(code, 0)
                self.assertEqual(report["policy"]["commit_mode"], "classic")
                self.assertEqual(
                    report["policy"]["commit_mode_source"], "fallback")
                self.assertIn("executable-policy-ambiguous", [
                    item["code"] for item in report["warnings"]
                ])
        self.repo.project(mode="classic")
        self.repo.write("commitlint.config.js", "{}\n")
        code, _, report = self.invoke("inspect")
        self.assertEqual(code, 0)
        self.assertEqual(report["policy"]["commit_mode"], "classic")

    def test_commitlint_comments_are_ignored_quote_aware(self) -> None:
        comments_only = (
            "// extends: ['@commitlint/config-conventional']\nmodule.exports = {};\n",
            "/* parserPreset: 'config-conventional' */\nmodule.exports = {};\n",
            "module.exports = {note: 'https://example.invalid//config-conventional'};\n",
            "module.exports = {extends: [], note: 'config-conventional'};\n",
            "const note = \"extends: ['config-conventional']\";\nmodule.exports = {};\n",
        )
        for content in comments_only:
            with self.subTest(content=content[:12]):
                self.repo.write("commitlint.config.js", content)
                code, _, report = self.invoke("inspect")
                self.assertEqual(code, 0)
                self.assertEqual(
                    report["policy"]["commit_mode_source"], "fallback")
                self.assertIn("executable-policy-ambiguous", [
                    item["code"] for item in report["warnings"]
                ])
        self.repo.write(
            "commitlint.config.js",
            "const note = '// keep quoted';\nmodule.exports = {\n"
            "  extends: [\n    '@commitlint/config-conventional'\n  ]\n};\n",
        )
        code, _, report = self.invoke("inspect")
        self.assertEqual(code, 0)
        self.assertEqual(report["policy"]["commit_mode"], "conventional")

        with self.assertRaises(checker.UnsafeInput):
            checker._strip_js_comments("x" * (checker.MAX_FILE_BYTES + 1))

    def test_commitlint_config_argument_allows_whitespace_and_comments_do_not_activate(self) -> None:
        workflow = (
            "jobs:\n  lint:\n    steps:\n      - run: |\n"
            "          commitlint --config\n"
            "            ./config-conventional.js\n"
            "          # --config ./ignored-config-conventional.js\n"
        )
        path = self.repo.write(".github/workflows/commitlint.yml", workflow)
        code, _, report = self.invoke("inspect")
        self.assertEqual(code, 0)
        self.assertEqual(report["policy"]["commit_mode"], "conventional")
        self.assertEqual(
            report["policy"]["commit_mode_source"],
            ".github/workflows/commitlint.yml",
        )
        path.unlink()
        self.repo.write(
            "commitlint.config.js",
            "/*\n * extends: ['@commitlint/config-conventional']\n */\n"
            "module.exports = {rules: {'type-empty': [2, 'never']}};\n",
        )
        code, _, report = self.invoke("inspect")
        self.assertEqual(code, 0)
        self.assertEqual(report["policy"]["commit_mode_source"], "fallback")

    def test_structured_and_executable_conflict_blocks(self) -> None:
        self.repo.project(mode="classic")
        self.repo.write(".commitlintrc.json",
                        '{"extends":["@commitlint/config-conventional"]}\n')

        code, _, report = self.invoke("inspect")

        self.assertEqual(code, 1)
        self.assert_codes(report, "errors", "policy-conflict")

    def test_confirmed_mode_conflicts_with_project_or_executable_policy(self) -> None:
        self.repo.write("CONTRIBUTING.md",
                        "Commit policy is documented here.\n")
        self.repo.stage("tracked.txt", "next\n")
        for structured in ("project", "executable"):
            with self.subTest(structured=structured):
                if structured == "project":
                    self.repo.project(mode="classic")
                else:
                    project = self.repo.root / ".agents/project.json"
                    if project.exists():
                        project.unlink()
                    self.repo.write(
                        ".commitlintrc.json",
                        '{"extends":["@commitlint/config-conventional"]}\n')
                confirmed = "conventional" if structured == "project" else "classic"
                code, _, report = self.invoke(
                    "commit", "--message-file", "-",
                    "--confirmed-commit-mode", confirmed,
                    "--policy-source", "CONTRIBUTING.md",
                    stdin=b"Add policy conflict check\n",
                )
                self.assertEqual(code, 1)
                self.assertIn("policy-conflict", [
                    item["code"] for item in report["errors"]])

    def test_applicable_instruction_variants_report_bounded_redacted_lines(self) -> None:
        self.repo.write("AGENTS.local.md", "Commit note.\nBranch note.\n")
        self.repo.write("CONTRIBUTING-guide.md",
                        "No contribution terms here.\n")
        self.repo.write("src/AGENTS.python.md", "Branch rule.\n")
        self.repo.stage("src/code.py", "value = 1\n")

        code, output, report = self.invoke(
            "inspect", "--expected-path", "src/code.py")

        self.assertEqual(code, 0, report)
        paths = [source["path"]
                 for source in report["policy_sources"] if source["level"] == 1]
        self.assertEqual(paths, [
            "AGENTS.local.md", "CONTRIBUTING-guide.md", "src/AGENTS.python.md"])
        source = next(item for item in report["policy_sources"]
                      if item["path"] == "AGENTS.local.md")
        self.assertEqual(source["relevant_lines"], [1, 2])
        self.assertEqual(source["relevant_terms"], ["branch", "commit"])
        self.assertNotIn("Commit note", output)
        self.assertNotIn("Branch note", output)

    def test_malformed_secret_and_symlink_project_config_are_unsafe_and_redacted(self) -> None:
        cases = ("{", '{"token":"ghp_abcdefghijklmnop"}')
        for content in cases:
            with self.subTest(content=content[:1]):
                self.repo.write(".agents/project.json", content)
                code, output, report = self.invoke("inspect")
                self.assertEqual(code, 2)
                self.assert_codes(report, "errors", "unsafe-project-config")
                self.assertNotIn("ghp_", output)
        (self.repo.root / ".agents/project.json").unlink()
        target = self.repo.write("project-target.json", "{}")
        (self.repo.root / ".agents/project.json").symlink_to(target)
        code, _, report = self.invoke("inspect")
        self.assertEqual(code, 2)
        self.assert_codes(report, "errors", "unsafe-project-config")

    def test_branch_fallback_and_confirmed_prefix(self) -> None:
        code, _, report = self.invoke(
            "branch", "--name", "describe-parser-safety")
        self.assertEqual(code, 0)
        self.assertEqual(report["branch"]["name"], "describe-parser-safety")
        self.assertEqual(report["policy"]["branch_prefixes"], [])
        for name in ("bad name", "-leading", "topic..name"):
            with self.subTest(name=name):
                code, _, report = self.invoke("branch", "--name", name)
                self.assertEqual(code, 1)
                self.assert_codes(report, "errors", "invalid-branch-name")

        self.repo.write("CONTRIBUTING.md",
                        "Branch examples and rules are documented here.\n")
        code, _, report = self.invoke("branch", "--name", "work/change")
        self.assertEqual(code, 1)
        self.assertIn("policy-confirmation-required", [
            item["code"] for item in report["errors"]])
        code, _, report = self.invoke(
            "branch", "--name", "work/change",
            "--confirmed-branch-prefix", "work/",
            "--policy-source", "CONTRIBUTING.md",
        )
        self.assertEqual(code, 0, report)
        self.assertEqual(report["policy"]["branch_prefixes"], ["work/"])
        self.assertEqual(report["policy"]["branch_prefix_state"], "resolved")
        self.assertEqual(report["policy"]["confirmed"]
                         ["branch_prefix"], "work/")
        code, _, report = self.invoke(
            "branch", "--name", "other/change",
            "--confirmed-branch-prefix", "work/",
            "--policy-source", "CONTRIBUTING.md",
        )
        self.assertEqual(code, 1)
        self.assertIn("branch-policy-mismatch", [
            item["code"] for item in report["errors"]])

    def test_confirmation_pair_source_relevance_and_symlink_fail_closed(self) -> None:
        self.repo.stage("tracked.txt", "next\n")
        self.repo.write("CONTRIBUTING.md", "Commit policy is documented.\n")
        for arguments in (
            ("--confirmed-commit-mode", "classic"),
            ("--policy-source", "CONTRIBUTING.md"),
        ):
            with self.subTest(arguments=arguments):
                process = subprocess.run(
                    [sys.executable, str(CHECKER), "commit", "--root",
                     str(self.repo.root), "--message-file", "-", *arguments,
                     "--format", "json"],
                    input=b"Add pair validation\n", stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, check=False,
                )
                self.assertEqual(process.returncode, 2)
                self.assertEqual(process.stdout, b"")
                self.assertEqual(
                    process.stderr, b"error: invalid invocation\n")

        code, _, report = self.invoke(
            "commit", "--message-file", "-",
            "--confirmed-commit-mode", "classic",
            "--policy-source", "CONTRIBUTING-missing.md",
            stdin=b"Add missing source validation\n",
        )
        self.assertEqual(code, 2)
        self.assert_codes(report, "errors", "unsafe-policy-source")

        self.repo.write("AGENTS.md", "Branch policy only.\n")
        code, _, report = self.invoke(
            "commit", "--message-file", "-",
            "--confirmed-commit-mode", "classic",
            "--policy-source", "AGENTS.md",
            stdin=b"Add relevance validation\n",
        )
        self.assertEqual(code, 1)
        self.assertIn("confirmed-policy-source-mismatch", [
            item["code"] for item in report["errors"]])

        target = self.repo.write("CONTRIBUTING-target.md", "Commit policy.\n")
        link = self.repo.root / "CONTRIBUTING-link.md"
        link.symlink_to(target)
        code, _, report = self.invoke(
            "commit", "--message-file", "-",
            "--confirmed-commit-mode", "classic",
            "--policy-source", "CONTRIBUTING-link.md",
            stdin=b"Add symlink validation\n",
        )
        self.assertEqual(code, 2)
        self.assert_codes(report, "errors", "unsafe-policy-source")

    def test_classic_message_body_and_width_advisories(self) -> None:
        self.repo.stage("tracked.txt", "next\n")
        valid = b"Add contribution checker\n\nExplain why local checks remain read-only.\n"
        code, _, report = self.invoke(
            "commit", "--message-file", "-", stdin=valid)
        self.assertEqual(code, 0)
        self.assertEqual(report["commit"]["mode"], "classic")
        bad = b"Updated\nBody without separator\n"
        code, _, report = self.invoke(
            "commit", "--message-file", "-", stdin=bad)
        self.assertEqual(code, 1)
        self.assertIn("classic-subject-not-concrete",
                      [item["code"] for item in report["errors"]])
        self.assertIn("body-separator-missing",
                      [item["code"] for item in report["errors"]])
        long = ("Add " + "bounded " * 9 +
                "checker\n\n" + "x" * 73 + "\n").encode()
        code, _, report = self.invoke(
            "commit", "--message-file", "-", stdin=long)
        self.assertEqual(code, 0)
        self.assert_codes(report, "warnings",
                          "subject-over-50", "body-line-over-72")

    def test_classic_rejects_empty_body_separator_and_generic_subjects(self) -> None:
        self.repo.stage("tracked.txt", "next\n")
        for payload in (
            b"Add contribution checker\n\n",
            b"Add contribution checker\n\n   \n",
        ):
            with self.subTest(payload=payload):
                code, _, report = self.invoke(
                    "commit", "--message-file", "-", stdin=payload)
                self.assertEqual(code, 1)
                self.assertIn("empty-message-body", [
                    item["code"] for item in report["errors"]
                ])
                self.assertFalse(report["commit"]["body_present"])
        for subject in (
            "Fix bug", "FIX BUG", "Fix the bug", "Fix issue", "Improve problem",
            "Improve code", "Update files", "Update the files", "Update code",
            "Change things", "Add stuff", "Add changes", "Remove code",
            "Remove the code", "Remove misc", "Resolve issue",
            "Correct problem", "Modify files", "Refactor code",
            "Repair bug", "Handle issue", "Tweak code",
            "Changes", "WIP", "Misc", "Phase 2",
        ):
            with self.subTest(subject=subject):
                code, _, report = self.invoke(
                    "commit", "--message-file", "-",
                    stdin=(subject + "\n").encode("utf-8"),
                )
                self.assertEqual(code, 1)
                self.assertIn("classic-subject-not-concrete", [
                    item["code"] for item in report["errors"]
                ])

    def test_classic_generic_detection_preserves_specific_subjects(self) -> None:
        self.repo.stage("tracked.txt", "next\n")
        for subject in (
            "Fix parser timeout", "Fix the parser timeout", "Improve retry diagnostics",
            "Update contribution policy", "Change retry semantics",
            "Add parser guard", "Remove obsolete fallback",
            "Record phase 2 parser validation",
        ):
            with self.subTest(subject=subject):
                code, _, report = self.invoke(
                    "commit", "--message-file", "-",
                    stdin=(subject + "\n").encode("utf-8"),
                )
                self.assertEqual(code, 0, report)

    def test_classic_generic_checks_are_closed_not_universal_nlp(self) -> None:
        for subject in ("Repair bug", "Handle issue", "Tweak code"):
            with self.subTest(known=subject):
                report = checker._empty_report()
                checker._validate_message(subject, "classic", [], report)
                self.assertIn("classic-subject-not-concrete", [
                    item["code"] for item in report["errors"]])
        for subject in ("Polish code", "Mend issue", "Rework files"):
            with self.subTest(advisory=subject):
                report = checker._empty_report()
                checker._validate_message(subject, "classic", [], report)
                self.assertNotIn("classic-subject-not-concrete", [
                    item["code"] for item in report["errors"]])
                self.assertIn("review-subject-concreteness", [
                    item["code"] for item in report["advice"]])
        for subject in (
            "Resolve deadlock", "Correct parser bounds",
            "Modify timeout handling", "Refactor policy scanner",
            "Resolve issue in parser", "Correct the bug handling path",
        ):
            with self.subTest(specific=subject):
                report = checker._empty_report()
                checker._validate_message(subject, "classic", [], report)
                self.assertNotIn("classic-subject-not-concrete", [
                    item["code"] for item in report["errors"]])

    def test_commit_allows_one_terminal_newline_and_rejects_trailing_blank_paragraphs(self) -> None:
        self.repo.stage("tracked.txt", "next\n")
        for payload in (
            b"Add contribution checker\n",
            b"Add contribution checker\n\nExplain why parsing is bounded.\n",
        ):
            with self.subTest(valid=payload):
                code, _, report = self.invoke(
                    "commit", "--message-file", "-", stdin=payload)
                self.assertEqual(code, 0, report)
        for payload in (
            b"Add contribution checker\n\nExplain why parsing is bounded.\n\n",
            b"Add contribution checker\n\nExplain why parsing is bounded.\n   \n",
            b"Add contribution checker\n\nExplain why parsing is bounded.\n\n \n",
        ):
            with self.subTest(invalid=payload):
                code, _, report = self.invoke(
                    "commit", "--message-file", "-", stdin=payload)
                self.assertEqual(code, 1)
                self.assertIn("trailing-blank-lines", [
                    item["code"] for item in report["errors"]
                ])

    def test_conventional_breaking_footer_and_unrestricted_type(self) -> None:
        self.repo.project(mode="conventional")
        self.repo.stage("tracked.txt", "next\n")
        for message in (
            b"feat(parser)!: reject unsafe input\n\nKeep repository reads bounded.\n\nBREAKING CHANGE: malformed input now blocks\n",
            b"docs: explain contribution policy\n",
        ):
            with self.subTest(message=message[:8]):
                code, _, report = self.invoke(
                    "commit", "--message-file", "-", stdin=message)
                self.assertEqual(code, 0, report)
        code, _, report = self.invoke(
            "commit", "--message-file", "-", stdin=b"Add classic subject\n")
        self.assertEqual(code, 1)
        self.assert_codes(report, "errors", "conventional-header-invalid")
        code, _, report = self.invoke(
            "commit", "--message-file", "-", stdin=b"feat(): empty scope\n")
        self.assertEqual(code, 1)
        self.assert_codes(report, "errors", "conventional-header-invalid")

    def test_breaking_change_reserved_footer_attempts_require_exact_colon_form(self) -> None:
        self.repo.project(mode="conventional")
        self.repo.stage("tracked.txt", "next\n")
        for footer in (
            "BREAKING CHANGE # invalid", "BREAKING CHANGE:",
            "BREAKING-CHANGE #invalid", "BREAKING-CHANGE:   ",
        ):
            with self.subTest(footer=footer):
                message = "feat!: change parser\n\n" + footer + "\n"
                code, _, report = self.invoke(
                    "commit", "--message-file", "-", stdin=message.encode("utf-8"))
                self.assertEqual(code, 1)
                self.assertIn("breaking-change-footer-invalid", [
                    item["code"] for item in report["errors"]
                ])
                self.assertEqual(report["commit"]["trailers"], [])
                self.assertFalse(report["commit"]["body_present"])
        misplaced = (
            "feat: change parser\n\nBREAKING CHANGE: reject legacy input\nBody after footer\n",
            "feat: change parser\n\nBREAKING CHANGE: reject legacy input\n\nSigned-off-by: Example <x@example.invalid>\n",
            "feat: change parser\n\nBody first\nBREAKING CHANGE: reject legacy input\nBody after footer\n",
        )
        for message in misplaced:
            with self.subTest(misplaced=message):
                code, _, report = self.invoke(
                    "commit", "--message-file", "-", stdin=message.encode("utf-8"))
                self.assertEqual(code, 1)
                self.assertIn("breaking-change-footer-not-final", [
                    item["code"] for item in report["errors"]
                ])
        for footer in (
            "BREAKING CHANGE: reject legacy input",
            "BREAKING-CHANGE: reject legacy input",
        ):
            with self.subTest(footer=footer):
                message = "feat: change parser\n\n" + footer + "\n"
                code, _, report = self.invoke(
                    "commit", "--message-file", "-", stdin=message.encode("utf-8"))
                self.assertEqual(code, 0, report)
                self.assertEqual(report["commit"]["trailers"], [
                                 "BREAKING CHANGE"])
        code, _, report = self.invoke(
            "commit", "--message-file", "-", stdin=b"feat!: change parser\n")
        self.assertEqual(code, 0, report)

    def test_required_trailers_use_safe_exact_tokens_without_inventing_identity(self) -> None:
        self.repo.project(mode="classic", trailers=[
                          "Signed-off-by", "Change-Id"])
        self.repo.stage("tracked.txt", "next\n")
        code, output, report = self.invoke(
            "commit", "--message-file", "-",
            stdin=b"Add trailer validation\n\nExplain why exact policy tokens matter.\n\nSigned-off-by: Example <x@example.invalid>\n",
        )
        self.assertEqual(code, 1)
        self.assert_codes(report, "errors", "required-trailer-missing")
        self.assertNotIn("Change-Id:", output)
        code, _, report = self.invoke(
            "commit", "--message-file", "-",
            stdin=b"Add trailer validation\n\nExplain why exact policy tokens matter.\n\nSigned-off-by: Example <x@example.invalid>\nChange-Id: I123\n",
        )
        self.assertEqual(code, 0, report)

    def test_message_rejects_invalid_utf8_controls_secrets_and_symlink_file(self) -> None:
        self.repo.stage("tracked.txt", "next\n")
        for payload in (b"\xff", b"Add safe check\x00\n", b"Add token ghp_abcdefghijklmnop\n"):
            with self.subTest(payload=payload[:4]):
                code, output, report = self.invoke(
                    "commit", "--message-file", "-", stdin=payload)
                self.assertEqual(code, 2)
                self.assertNotIn("ghp_", output)
                self.assertTrue(report["errors"])
        message = self.repo.write("message.txt", "Add safe file input\n")
        self.repo.write("message-link.txt", "unused")
        (self.repo.root / "message-link.txt").unlink()
        (self.repo.root / "message-link.txt").symlink_to(message)
        code, _, report = self.invoke(
            "commit", "--message-file", "message-link.txt")
        self.assertEqual(code, 2)
        self.assert_codes(report, "errors", "unsafe-message-input")

    def test_root_rejects_lexical_controls_surrogates_and_outer_whitespace(self) -> None:
        for value in (
            " " + str(self.repo.root), str(self.repo.root) + " ",
            str(self.repo.root) + "\x01", str(self.repo.root) + "\x7f",
            str(self.repo.root) + "\ud800",
        ):
            with self.subTest(value=repr(value)):
                with self.assertRaises(checker.UnsafeInput):
                    checker._safe_root(value)
        unsafe = " " + str(self.repo.root)
        process = subprocess.run(
            [sys.executable, str(CHECKER), "inspect", "--root", unsafe,
             "--format", "json"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(process.returncode, 2)
        output = process.stdout.decode("utf-8")
        self.assertNotIn(unsafe, output)
        self.assertEqual(json.loads(output)["errors"][0]["message"],
                         "An input or repository path could not be inspected safely.")

    def test_status_expected_paths_unrelated_untracked_conflict_and_whitespace(self) -> None:
        self.repo.stage("expected.py", "value = 1\n")
        self.repo.stage("other.py", "other = 1\n")
        self.repo.write("unstaged.txt", "work\n")
        self.repo.write("untracked.txt", "new\n")
        code, _, report = self.invoke(
            "inspect", "--expected-path", "expected.py")
        self.assertEqual(code, 0)
        self.assertEqual(report["scope"]["staged"], [
                         "expected.py", "other.py"])
        self.assertEqual(report["scope"]["untracked"], [
                         "unstaged.txt", "untracked.txt"])
        self.assert_codes(report, "warnings", "unexpected-staged-path")

        self.repo.stage(
            "bad.txt", "<<<<<<< ours\nvalue  \n=======\nother\n>>>>>>> theirs\n")
        code, _, report = self.invoke("inspect")
        self.assertEqual(code, 1)
        codes = [item["code"] for item in report["errors"]]
        self.assertIn("staged-whitespace-error", codes)
        self.assertIn("staged-conflict-marker", codes)

    def test_commit_requires_staged_content_but_inspect_does_not(self) -> None:
        code, _, report = self.invoke("inspect")
        self.assertEqual(code, 0)
        code, _, report = self.invoke(
            "commit", "--message-file", "-", stdin=b"Add nothing\n")
        self.assertEqual(code, 1)
        self.assert_codes(report, "errors", "no-staged-changes")

    def test_json_and_human_are_deterministic_and_semantically_equivalent(self) -> None:
        self.repo.project(mode="classic", trailers=["Change-Id"])
        self.repo.stage("tracked.txt", "next\n")
        self.repo.write(
            "draft.md", "# Add human report parity\n\n" +
            "\n".join("## " + section + "\n\nContent."
                      for section in PR_REQUIRED_SECTIONS))
        cases = (
            ("inspect", ("--expected-path", "tracked.txt"), None),
            ("branch", ("--name", "describe-human-report"), None),
            ("commit", ("--message-file", "-", "--expected-path", "tracked.txt"),
             b"Add human report parity\n\nExplain why every field remains visible.\n\nChange-Id: I123\n"),
            ("pull-request", ("--draft-file", "draft.md"), None),
        )
        for command, arguments, stdin in cases:
            with self.subTest(command=command):
                first = self.invoke(command, *arguments, stdin=stdin)
                second = self.invoke(command, *arguments, stdin=stdin)
                self.assertEqual(first[:2], second[:2])
                code, human, _ = self.invoke(
                    command, *arguments, stdin=stdin, fmt="human")
                self.assertEqual(code, first[0])
                self.assertIn("side effects: none", human)
                self.assertIn("commit mode state:", human)
                self.assertIn("branch prefix state:", human)
                self.assertIn("confirmed policy source:", human)
                marker = "canonical report json:\n"
                self.assertIn(marker, human)
                rendered = json.loads(human.split(marker, 1)[1])
                self.assertEqual(rendered, first[2])
                self.assertIn("required_trailers", rendered["policy"])
                self.assertIn("branch_prefixes", rendered["policy"])
                self.assertIn("commit_mode_state", rendered["policy"])
                self.assertIn("branch_prefix_state", rendered["policy"])
                self.assertIn("confirmed", rendered["policy"])
                self.assertIn("base_ref", rendered["scope"])

    def test_all_commands_leave_head_index_refs_reflogs_status_objects_and_files_unchanged(self) -> None:
        self.assertNotIn(
            "write" + "-tree", Path(__file__).read_text(encoding="utf-8"))
        self.repo.stage("tracked.txt", "next\n")
        self.repo.write("untracked.txt", "new\n")
        self.repo.write(
            "CONTRIBUTING.md", "Commit policy is documented.\nBranch policy is documented.\n")
        before = self.repo.snapshot()
        calls = (
            ("inspect", ("--expected-path", "tracked.txt"), None),
            ("branch", ("--name", "safe/name",
             "--confirmed-branch-prefix", "safe/",
                        "--policy-source", "CONTRIBUTING.md"), None),
            ("commit", ("--message-file", "-", "--expected-path",
             "tracked.txt", "--confirmed-commit-mode", "classic",
                        "--policy-source", "CONTRIBUTING.md"), b"Add safe check\n"),
        )
        for command, arguments, stdin in calls:
            with self.subTest(command=command):
                self.invoke(command, *arguments, stdin=stdin)
                self.assertEqual(self.repo.snapshot(), before)

    def test_pull_request_snapshot_and_unrelated_staged_scope_are_read_only(self) -> None:
        draft = (
            "# Add snapshot checks\n\n" +
            "\n".join("## " + section + "\n\nContent."
                      for section in PR_REQUIRED_SECTIONS))
        self.repo.write("draft.md", draft)
        self.repo.stage("unrelated.txt", "unrelated\n")
        before = self.repo.snapshot()

        code, _, report = self.invoke(
            "pull-request", "--draft-file", "draft.md",
            "--expected-path", "draft.md")

        self.assertEqual(code, 0, report)
        self.assertEqual(report["scope"]["unexpected_staged"], [
                         "unrelated.txt"])
        self.assertEqual(self.repo.snapshot(), before)

    def test_help_documents_public_contract_and_bad_invocation_is_exit_2(self) -> None:
        process = subprocess.run([sys.executable, str(CHECKER), "--help"],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(process.returncode, 0)
        help_text = process.stdout.decode()
        for token in ("inspect", "branch", "commit", "pull-request", "read-only", "stdin", "environment", "exit"):
            self.assertIn(token, help_text.lower())
        process = subprocess.run([sys.executable, str(CHECKER), "branch", "--root", str(self.repo.root)],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(process.returncode, 2)


class ContributionStaticContracts(unittest.TestCase):
    def test_skill_activation_nonactivation_and_progressive_reference_loading(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: contribute\n"))
        metadata = text.split("---", 2)[1].lower()
        for phrase in ("use when", "branch", "commit", "do not use", "pull request", "review feedback"):
            self.assertIn(phrase, metadata)
        self.assertIn("references/commits.md", text)
        self.assertIn("only when", text.lower())
        self.assertIn(
            "--confirmed-branch-prefix PREFIX --policy-source PATH", text)
        self.assertIn(
            "--confirmed-commit-mode classic|conventional --policy-source PATH", text)
        self.assertIn(
            "never say that the checker interpreted the prose", text.lower())
        self.assertIn("pull-requests.md", text)
        self.assertIn("review-responses.md", text)
        self.assertIn("For author-response work only", text)
        self.assertTrue(COMMITS.is_file())
        self.assertTrue((SKILL.parent / "references" /
                         "review-responses.md").is_file())
        self.assertTrue((SKILL.parent / "assets" /
                         "pull-request.template.md").is_file())
        self.assertTrue((SKILL.parent / "assets" /
                         "observations.schema.json").is_file())
        scenarios = (ROOT / "tests" /
                     "scenarios.md").read_text(encoding="utf-8")
        self.assertIn("must activate `contribute`", scenarios)
        self.assertIn("must not activate `contribute`", scenarios)
        self.assertIn("does not load `references/commits.md`", scenarios)
        self.assertIn("author responses", scenarios)
        self.assertIn("thread is not resolved", scenarios)

    def test_checker_is_owner_contained_standard_library_and_git_is_nonmutating(self) -> None:
        tree = ast.parse(CHECKER.read_text(encoding="utf-8"))
        imports: set[str] = set()
        forbidden_calls: list[str] = []
        popen_executables: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0]
                               for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"write_text", "write_bytes", "unlink", "mkdir", "replace", "rename"}:
                    forbidden_calls.append(node.func.attr)
                if (node.func.attr == "Popen" and node.args
                        and isinstance(node.args[0], ast.List)
                        and node.args[0].elts
                        and isinstance(node.args[0].elts[0], ast.Constant)):
                    popen_executables.append(node.args[0].elts[0].value)
        self.assertFalse(imports & {"requests", "urllib3", "httpx", "scripts"})
        self.assertNotIn("socket", imports)
        self.assertEqual(forbidden_calls, [])
        self.assertEqual(popen_executables, ["git"])
        source = CHECKER.read_text(encoding="utf-8")
        for forbidden in (
            "git commit", "git add", "git checkout", "git switch", "git push",
            "shell=True", "provider api", "urllib", "requests",
        ):
            self.assertNotIn(forbidden, source.casefold())
        self.assertIn("def _allowed_git", source)
        self.assertIn("if not _allowed_git(arguments)", source)
        self.assertIn('"pull-request"', source)
        self.assertNotIn("review-responses.md", source)
        for environment in ("GIT_OPTIONAL_LOCKS", "GIT_TERMINAL_PROMPT", "GIT_NO_LAZY_FETCH", "GIT_CONFIG_GLOBAL"):
            self.assertIn(environment, source)

    def test_git_subprocess_timeout_and_combined_output_are_bounded(self) -> None:
        repository = Repository()
        self.addCleanup(repository.close)
        with tempfile.TemporaryDirectory() as temporary:
            fake_git = Path(temporary) / "git"
            fake_git.write_text(
                "#!/usr/bin/env python3\n"
                "import os, sys, time\n"
                "if os.environ.get('FAKE_GIT') == 'sleep': time.sleep(2)\n"
                "else: sys.stderr.buffer.write(b'x' * 32)\n",
                encoding="utf-8",
            )
            fake_git.chmod(0o755)
            environment = {"PATH": temporary + os.pathsep + os.environ["PATH"]}
            with mock.patch.dict(os.environ, {**environment, "FAKE_GIT": "output"}, clear=False):
                with self.assertRaises(checker.GitInspectionError):
                    checker._run_git(repository.root, [
                                     "status", "--porcelain=v1", "-z"], max_output=8)
            with mock.patch.dict(os.environ, {**environment, "FAKE_GIT": "sleep"}, clear=False):
                with self.assertRaises(checker.GitInspectionError):
                    checker._run_git(repository.root, [
                                     "status", "--porcelain=v1", "-z"], timeout=1)

    def test_catalog_v1_profiles_and_docs_include_contribute(self) -> None:
        catalog = json.loads(
            (ROOT / ".agents/kit-catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["schema_version"], 2)
        self.assertEqual(catalog["kit_version"], "2.1.0")
        self.assertIn("contribute", catalog["skill_groups"]["utilities"])
        self.assertIn("contribute", catalog["profiles"]["default"]["skills"])
        self.assertIn("contribute", catalog["profiles"]["full"]["skills"])
        guide = (ROOT / "docs" / "usage-guide.md").read_text(encoding="utf-8")
        self.assertIn("twenty available skills", guide)
        self.assertIn("default profile installs thirteen skills", guide)
        self.assertIn("`contribute`", guide)

    def test_report_schema_is_owner_local_and_matches_output_shape(self) -> None:
        schema_path = SKILL.parent / "assets" / "contribution-report.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(
            schema["$id"], "urn:agentic-sdlc-kit:contribution-report:v2")
        self.assertFalse(schema["additionalProperties"])
        for field in ("schema_version", "valid", "errors", "warnings", "advice",
                      "policy_sources", "policy", "scope", "branch", "commit",
                      "pull_request", "summary"):
            self.assertIn(field, schema["required"])
        self.assertFalse(schema["$defs"]["pull_request"]
                         ["oneOf"][1]["additionalProperties"])
        observations = json.loads(
            (SKILL.parent / "assets" / "observations.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(observations["additionalProperties"])
        self.assertEqual(observations["properties"]
                         ["schema_version"]["const"], 2)
        policy_required = schema["$defs"]["policy"]["required"]
        for field in ("commit_mode_state", "branch_prefix_state", "confirmed"):
            self.assertIn(field, policy_required)
        source_required = schema["$defs"]["policy_source"]["required"]
        for field in ("state", "relevant_lines", "relevant_terms"):
            self.assertIn(field, source_required)


if __name__ == "__main__":
    unittest.main()

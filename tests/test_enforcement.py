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


ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / ".agents" / "modules" / "enforcement" / "check.py"
EVIDENCE_SCHEMA = ROOT / ".agents" / "modules" / \
    "evidence" / "assets" / "evidence.schema.json"
COMPLIANCE_ASSETS = ROOT / ".agents" / "modules" / "compliance" / "assets"
VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "source_validator_for_enforcement", ROOT / "scripts" / "validate.py"
)
assert VALIDATOR_SPEC and VALIDATOR_SPEC.loader
source_validator = importlib.util.module_from_spec(VALIDATOR_SPEC)
VALIDATOR_SPEC.loader.exec_module(source_validator)


def project_config(
    modules: list[str],
    evidence_root: str | None = None,
    repositories: list[dict[str, object]] | None = None,
    approval_policy: dict[str, object] | None = None,
    schema_version: int = 2,
) -> str:
    return json.dumps(
        {
            "schema_version": schema_version,
            "roots": {
                "specs": "specs",
                "work": ".work",
                "adrs": None,
                "evidence": evidence_root,
                "domain_context": None,
            },
            "repositories": repositories or [],
            "enabled_modules": modules,
            "tracker": {"kind": "none", "location": None, "labels": {}},
            "agent": {"mode": "guided"},
            "review": {"mode": "risk-based"},
            "approval_policy": approval_policy or {"rules": []},
            "contribution": {
                "commit_mode": "discover",
                "base_branch": None,
                "required_trailers": [],
                "pull_request_template": None,
                "merge_strategy": "unknown",
            },
        },
        separators=(",", ":"),
    ) + "\n"


def complete_evidence(risk: str = "low") -> dict[str, object]:
    empty_snapshot = hashlib.sha256(b"[]").hexdigest()
    document: dict[str, object] = {
        "schema_version": 1,
        "change_id": "TASK-010",
        "authoritative_sources": [
            {"id": "TASK-010", "reference": "request:TASK-010"}
        ],
        "lifecycle": {
            "status": "complete",
            "transition": "verified",
            "evidence_references": ["review.md"],
        },
        "risk": {"level": risk, "rationale": "Risk was assessed for this change."},
        "change_contract": {
            "intent": "Implement the accepted bounded change.",
            "confirmed_why": "request:TASK-010",
            "scope": "Only the accepted repository change.",
            "expected_evidence": ["Focused checks"],
            "agent_roles": ["implementer", "reviewer"],
            "review_focus": ["Correctness"],
        },
        "repository_scope": [
            {
                "repository_id": "current",
                "base": "not-applicable",
                "head": "not-applicable",
                "committed_range": "not-applicable",
                "uncommitted_entries": [],
                "snapshot_sha256": empty_snapshot,
            }
        ],
        "requirement_coverage": [
            {
                "requirement_id": "TASK-010",
                "repository_ids": ["current"],
                "status": "covered",
                "implementation_references": ["src/change.py"],
                "evidence_references": ["review.md"],
            }
        ],
        "checks": [
            {
                "id": "scoped-check",
                "requirement_ids": ["TASK-010"],
                "repository_ids": ["current"],
                "kind": "scoped",
                "required": True,
                "applicability": "applicable",
                "not_applicable_reason": None,
                "status": "passed",
                "observed_result": "Focused checks passed.",
                "evidence_class": "observed evidence",
                "output_reference": None,
            }
        ],
        "review": {
            "reviewer_role": "self-reviewer",
            "reviewer_id": "implementer-1",
            "implementers": ["implementer-1"],
            "prior_participation": ["implementation"],
            "fresh_context": False,
            "independence": "self-review",
            "independence_basis": "The implementer performed the self-review.",
            "verdict": "approved",
            "reference": "review.md",
        },
        "known_limits": "not-tracked",
        "remaining_risks": [],
        "follow_ups": [],
    }
    if risk in {"medium", "high"}:
        checks = document["checks"]
        assert isinstance(checks, list)
        checks.extend(
            [
                {
                    "id": "regression-check",
                    "requirement_ids": ["TASK-010"],
                    "repository_ids": ["current"],
                    "kind": "regression",
                    "required": True,
                    "applicability": "applicable",
                    "not_applicable_reason": None,
                    "status": "passed",
                    "observed_result": "Regression checks passed.",
                    "evidence_class": "observed evidence",
                    "output_reference": None,
                },
                {
                    "id": "failure-path-check",
                    "requirement_ids": ["TASK-010"],
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
        checks = document["checks"]
        assert isinstance(checks, list)
        checks.append(
            {
                "id": "recovery-check",
                "requirement_ids": ["TASK-010"],
                "repository_ids": ["current"],
                "kind": "recovery-rollback",
                "required": False,
                "applicability": "not-applicable",
                "not_applicable_reason": "A revert removes the additive change.",
                "status": "not-applicable",
                "observed_result": None,
                "evidence_class": None,
                "output_reference": None,
            }
        )
        review = document["review"]
        assert isinstance(review, dict)
        review.update(
            reviewer_role="independent-reviewer",
            reviewer_id="reviewer-2",
            prior_participation=["review"],
            fresh_context=True,
            independence="independent",
            independence_basis="Fresh reviewer with no implementation participation.",
        )
    return document


def audit_event(
    sequence: int,
    timestamp: str,
    previous: str | None = None,
    new: str | None = None,
    approvals: list[dict[str, object]] | None = None,
    repositories: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    transition = previous is not None or new is not None
    return {
        "schema_version": 1,
        "event_id": f"TASK-010-{sequence:06d}",
        "sequence": sequence,
        "timestamp": timestamp,
        "change_id": "TASK-010",
        "actor": {"actor_id": "implementer-1", "role": "implementer"},
        "action": "lifecycle-transition" if transition else "evidence-updated",
        "previous_lifecycle": previous,
        "new_lifecycle": new,
        "authoritative_source_references": ["request:TASK-010"],
        "evidence_references": ["evidence.json", "review.md"],
        "approvals": approvals or [],
        "repositories": repositories
        or [{"repository_id": "current", "revision": "a" * 40}],
    }


class EnforcementFixture:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def close(self) -> None:
        self.temporary.cleanup()

    def install_module(self, name: str) -> Path:
        module = self.root / ".agents" / "modules" / name
        module.mkdir(parents=True, exist_ok=True)
        (module / "MODULE.md").write_text(f"# {name}\n", encoding="utf-8")
        return module

    def install_evidence(self) -> None:
        module = self.install_module("evidence")
        assets = module / "assets"
        assets.mkdir()
        shutil.copy2(EVIDENCE_SCHEMA, assets / "evidence.schema.json")

    def install_compliance(self) -> None:
        module = self.install_module("compliance")
        shutil.copytree(COMPLIANCE_ASSETS, module / "assets")

    def write_catalog(
        self,
        modules: list[str],
        dependencies: dict[str, list[str]] | None = None,
    ) -> None:
        agents = self.root / ".agents"
        agents.mkdir(exist_ok=True)
        catalog = {
            "schema_version": 2,
            "kit_version": "2.1.0",
            "skill_groups": {"core": [], "utilities": [], "optional": []},
            "modules": [
                {
                    "name": name,
                    "description": f"{name} module",
                    "depends_on": (dependencies or {}).get(name, []),
                }
                for name in modules
            ],
            "global_resources": ["AGENTS.md", ".agents/kit-catalog.json"],
            "profiles": {
                "default": {"skills": [], "modules": []},
                "full": {"skills": [], "modules": modules},
            },
        }
        (agents / "kit-catalog.json").write_text(
            json.dumps(catalog), encoding="utf-8"
        )

    def configure(
        self,
        modules: list[str],
        evidence_root: str | None = None,
        repositories: list[dict[str, object]] | None = None,
        approval_policy: dict[str, object] | None = None,
        schema_version: int = 2,
    ) -> None:
        agents = self.root / ".agents"
        agents.mkdir(exist_ok=True)
        (agents / "project.json").write_text(
            project_config(
                modules,
                evidence_root,
                repositories,
                approval_policy,
                schema_version,
            ),
            encoding="utf-8",
        )

    def write_evidence(self, document: object, raw: bool = False) -> Path:
        path = self.root / "evidence" / "TASK-010" / "evidence.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        if raw:
            path.write_text(str(document), encoding="utf-8")
        else:
            path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def write_audit(self, events: list[object], raw: bool = False) -> Path:
        path = self.root / "evidence" / "TASK-010" / "audit.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        if raw:
            path.write_text("\n".join(str(event)
                            for event in events) + "\n", encoding="utf-8")
        else:
            path.write_text(
                "".join(
                    json.dumps(event, separators=(",", ":")) + "\n"
                    for event in events
                ),
                encoding="utf-8",
            )
        return path

    def run(
        self,
        output_format: str = "json",
        *extra: str,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(CHECK),
                "--root",
                str(self.root),
                "--format",
                output_format,
                *extra,
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=environment,
        )


class EnforcementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = EnforcementFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def json_result(
        self, environment: dict[str, str] | None = None
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        result = self.fixture.run(environment=environment)
        self.assertNotIn("Traceback", result.stderr + result.stdout)
        return result, json.loads(result.stdout)

    def init_git(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "init", "--quiet", str(path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def activate_multi_repo(
        self, repositories: list[dict[str, object]], evidence: bool = False
    ) -> None:
        modules = ["enforcement", "multi-repo"]
        self.fixture.install_module("enforcement")
        self.fixture.install_module("multi-repo")
        if evidence:
            modules.append("evidence")
            self.fixture.install_evidence()
        self.fixture.write_catalog(modules)
        self.fixture.configure(
            modules,
            "evidence" if evidence else None,
            repositories,
        )

    def test_absent_project_config_has_no_optional_burden(self) -> None:
        result, report = self.json_result()
        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["valid"])
        self.assertEqual(report["errors"], [])
        self.assertFalse((self.fixture.root / "evidence").exists())

    def test_valid_config_and_enabled_installed_module_pass(self) -> None:
        self.fixture.install_module("enforcement")
        self.fixture.write_catalog(["enforcement"])
        self.fixture.configure(["enforcement"])
        result, report = self.json_result()
        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["valid"])

    def test_malformed_or_invalid_config_is_invocation_error_and_redacted(self) -> None:
        agents = self.fixture.root / ".agents"
        agents.mkdir()
        secret = "https://example.test/repo?access_token=do-not-echo"
        config = json.loads(project_config([]))
        config["tracker"].update(kind="web", location=secret)
        config["enabled_modules"] = "enforcement"
        (agents / "project.json").write_text(
            json.dumps(config), encoding="utf-8"
        )
        result, report = self.json_result()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(report["valid"])
        self.assertNotIn("do-not-echo", result.stdout)
        self.assertTrue(all(
            set(item) == {"code", "path", "field", "message"} for item in report["errors"]))

    def test_duplicate_nested_config_key_is_rejected(self) -> None:
        agents = self.fixture.root / ".agents"
        agents.mkdir()
        config = project_config([]).replace(
            '"labels":{}', '"labels":{"ready":"one","ready":"two"}'
        )
        (agents / "project.json").write_text(config, encoding="utf-8")
        result, report = self.json_result()
        self.assertEqual(result.returncode, 2)
        self.assertIn("CONFIG_DUPLICATE_KEY", {
                      item["code"] for item in report["errors"]})

    def test_enabled_missing_module_is_validation_failure(self) -> None:
        self.fixture.configure(["enforcement"])
        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        self.assertIn("MODULE_ENABLED_MISSING", {
                      item["code"] for item in report["errors"]})

    def test_enabled_module_dependency_must_be_installed_and_enabled(self) -> None:
        self.fixture.install_module("enforcement")
        self.fixture.configure(["enforcement"])
        catalog = {
            "schema_version": 2,
            "kit_version": "2.1.0",
            "skill_groups": {"core": [], "utilities": [], "optional": []},
            "modules": [
                {"name": "enforcement", "description": "Checks",
                    "depends_on": ["evidence"]},
                {"name": "evidence", "description": "Records", "depends_on": []},
            ],
            "global_resources": ["AGENTS.md", ".agents/kit-catalog.json"],
            "profiles": {
                "default": {"skills": [], "modules": []},
                "full": {"skills": [], "modules": ["evidence", "enforcement"]},
            },
        }
        (self.fixture.root / ".agents" / "kit-catalog.json").write_text(
            json.dumps(catalog), encoding="utf-8"
        )
        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("MODULE_DEPENDENCY_DISABLED", codes)
        self.assertIn("MODULE_DEPENDENCY_MISSING", codes)

    def test_manifest_catalog_and_filesystem_hash_consistency(self) -> None:
        module = self.fixture.install_module("enforcement")
        self.fixture.configure(["enforcement"])
        manifest = {
            "schema_version": 2,
            "kit_version": "2.1.0",
            "request": {"profile": "default", "explicit_components": []},
            "components": [
                {
                    "kind": "module",
                    "name": "enforcement",
                    "path": ".agents/modules/enforcement",
                    "ownership": "managed",
                    "sha256": "0" * 64,
                }
            ],
            "global_resources": ["AGENTS.md", ".agents/kit-catalog.json"],
        }
        (self.fixture.root / ".agents" / "agentic-sdlc-kit.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        self.assertTrue(module.is_dir())
        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        self.assertIn("MANIFEST_HASH_MISMATCH", {
                      item["code"] for item in report["errors"]})

    def activate_evidence(self, document: object) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        self.fixture.install_module("enforcement")
        self.fixture.install_evidence()
        self.fixture.write_catalog(["enforcement", "evidence"])
        self.fixture.configure(["enforcement", "evidence"], "evidence")
        evidence_path = self.fixture.write_evidence(document)
        (evidence_path.parent / "review.md").write_text("# Review\n", encoding="utf-8")
        return self.json_result()

    def activate_compliance(
        self,
        events: list[object],
        *,
        policy: dict[str, object] | None = None,
        risk: str = "low",
        modules: list[str] | None = None,
        repositories: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        active_modules = modules or ["compliance", "evidence", "enforcement"]
        self.fixture.install_module("enforcement")
        self.fixture.install_evidence()
        self.fixture.install_compliance()
        if "multi-repo" in active_modules:
            self.fixture.install_module("multi-repo")
        self.fixture.write_catalog(
            active_modules,
            {"compliance": ["evidence", "enforcement"]},
        )
        self.fixture.configure(
            active_modules,
            "evidence",
            repositories,
            policy,
        )
        evidence = complete_evidence(risk)
        scope = evidence["repository_scope"]
        assert isinstance(scope, list)
        scope[0].update(
            base="b" * 40,
            head="a" * 40,
            committed_range=f"{'b' * 40}..{'a' * 40}",
        )
        evidence_path = self.fixture.write_evidence(evidence)
        (evidence_path.parent / "review.md").write_text("# Review\n", encoding="utf-8")
        self.fixture.write_audit(events)
        return evidence

    def test_complete_low_and_high_independent_evidence_pass(self) -> None:
        for risk in ("low", "high"):
            with self.subTest(risk=risk):
                if risk == "high":
                    self.fixture.close()
                    self.fixture = EnforcementFixture()
                result, report = self.activate_evidence(
                    complete_evidence(risk))
                self.assertEqual(result.returncode, 0, report)
                self.assertTrue(report["valid"])
                self.assertEqual(report["counts"]["evidence"], 1)

    def test_incomplete_complete_evidence_blocks_without_running_checks(self) -> None:
        document = complete_evidence("medium")
        checks = document["checks"]
        assert isinstance(checks, list)
        checks[0]["status"] = "not-run"
        checks[0]["observed_result"] = None
        checks[0]["evidence_class"] = None
        result, report = self.activate_evidence(document)
        self.assertEqual(result.returncode, 1)
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("EVIDENCE_REQUIRED_CHECK", codes)
        self.assertIn("EVIDENCE_COMPLETE_BLOCKED", codes)

    def test_malformed_sensitive_and_deep_evidence_never_traceback_or_echo(self) -> None:
        cases = (
            ('{"token":"do-not-echo",', "EVIDENCE_JSON_INVALID"),
            ("[" * 1200 + "]" * 1200, "EVIDENCE_JSON_DEPTH"),
        )
        for raw, expected in cases:
            with self.subTest(expected=expected):
                self.fixture.close()
                self.fixture = EnforcementFixture()
                self.fixture.install_module("enforcement")
                self.fixture.install_evidence()
                self.fixture.configure(["enforcement", "evidence"], "evidence")
                self.fixture.write_evidence(raw, raw=True)
                result, report = self.json_result()
                self.assertEqual(result.returncode, 1)
                self.assertNotIn("do-not-echo", result.stdout + result.stderr)
                self.assertIn(expected, {item["code"]
                              for item in report["errors"]})

    def test_valid_compliance_audit_and_empty_project_policy_pass(self) -> None:
        events = [
            audit_event(1, "2025-01-01T00:00:00Z", "draft", "approved"),
            audit_event(2, "2025-01-01T00:00:01Z", "approved", "implemented"),
            audit_event(3, "2025-01-01T00:00:02Z", "implemented", "verified"),
        ]
        self.activate_compliance(events)

        result, report = self.json_result()

        self.assertEqual(result.returncode, 0, report)
        self.assertTrue(report["valid"])
        config_path = self.fixture.root / ".agents" / "project.json"
        config_path.write_text(
            project_config(
                ["compliance", "evidence", "enforcement"],
                "evidence",
                schema_version=2,
            ),
            encoding="utf-8",
        )
        result, report = self.json_result()
        self.assertEqual(result.returncode, 0, report)

    def test_compliance_rejects_order_duplicates_timestamps_and_malformed_redacted_lines(self) -> None:
        sensitive = audit_event(1, "2025-01-01T00:00:00Z")
        sensitive["actor"]["actor_id"] = "token=do-not-echo"
        unknown = audit_event(1, "2025-01-01T00:00:00Z")
        unknown["unknown"] = True
        cases = (
            (
                [
                    audit_event(2, "2025-01-01T00:00:01Z"),
                    audit_event(1, "2025-01-01T00:00:02Z"),
                ],
                "COMPLIANCE_SEQUENCE",
                False,
            ),
            (
                [
                    audit_event(1, "2025-01-01T00:00:00Z"),
                    audit_event(1, "2025-01-01T00:00:01Z"),
                ],
                "COMPLIANCE_SEQUENCE_DUPLICATE",
                False,
            ),
            (
                [
                    audit_event(1, "2025-01-01T00:00:02Z"),
                    audit_event(2, "2025-01-01T00:00:01Z"),
                ],
                "COMPLIANCE_TIMESTAMP",
                False,
            ),
            ([audit_event(1, "2025-13-40T99:00:00Z")],
             "COMPLIANCE_TIMESTAMP", False),
            ([unknown], "COMPLIANCE_SCHEMA", False),
            ([sensitive], "COMPLIANCE_SENSITIVE", False),
            (["{\"secret\":\"do-not-echo\","], "COMPLIANCE_JSON_INVALID", True),
        )
        for events, expected, raw in cases:
            with self.subTest(expected=expected):
                self.fixture.close()
                self.fixture = EnforcementFixture()
                valid = [audit_event(1, "2025-01-01T00:00:00Z")]
                self.activate_compliance(valid)
                self.fixture.write_audit(events, raw=raw)
                result, report = self.json_result()
                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, {item["code"]
                              for item in report["errors"]})
                self.assertNotIn("do-not-echo", result.stdout + result.stderr)

    def test_compliance_rejects_broken_refs_invalid_transitions_and_change_id(self) -> None:
        cases = (
            (
                lambda event: event["evidence_references"].__setitem__(
                    0, "missing.json"),
                "COMPLIANCE_REFERENCE",
            ),
            (
                lambda event: event.update(
                    previous_lifecycle="draft", new_lifecycle="verified"),
                "COMPLIANCE_TRANSITION",
            ),
            (lambda event: event.update(change_id="OTHER"), "COMPLIANCE_CHANGE_ID"),
        )
        for mutate, expected in cases:
            with self.subTest(expected=expected):
                self.fixture.close()
                self.fixture = EnforcementFixture()
                event = audit_event(
                    1, "2025-01-01T00:00:00Z", "implemented", "verified"
                )
                mutate(event)
                self.activate_compliance([event])
                result, report = self.json_result()
                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, {item["code"]
                              for item in report["errors"]})

    def test_compliance_enforces_policy_roles_counts_and_independent_approvers(self) -> None:
        policy = {
            "rules": [
                {
                    "risk": "medium",
                    "action": "lifecycle-transition",
                    "required_roles": [{"role": "reviewer", "minimum": 2}],
                    "independent": True,
                }
            ]
        }
        approval = {
            "actor_id": "reviewer-2",
            "role": "reviewer",
            "reference": "review.md",
        }
        cases = (
            ([], "COMPLIANCE_APPROVAL_REQUIRED"),
            ([approval], "COMPLIANCE_APPROVAL_COUNT"),
            (
                [approval, {**approval, "actor_id": "implementer-1"}],
                "COMPLIANCE_SELF_APPROVAL",
            ),
            (
                [approval, {**approval, "actor_id": "reviewer-3",
                            "role": "security"}],
                "COMPLIANCE_APPROVAL_COUNT",
            ),
        )
        for approvals, expected in cases:
            with self.subTest(expected=expected):
                self.fixture.close()
                self.fixture = EnforcementFixture()
                event = audit_event(
                    1,
                    "2025-01-01T00:00:00Z",
                    "implemented",
                    "verified",
                    approvals,
                )
                self.activate_compliance([event], policy=policy, risk="medium")
                result, report = self.json_result()
                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, {item["code"]
                              for item in report["errors"]})

        self.fixture.close()
        self.fixture = EnforcementFixture()
        valid_event = audit_event(
            1,
            "2025-01-01T00:00:00Z",
            "implemented",
            "verified",
            [approval, {**approval, "actor_id": "reviewer-3"}],
        )
        self.activate_compliance([valid_event], policy=policy, risk="medium")
        result, report = self.json_result()
        self.assertEqual(result.returncode, 0, report)

    def test_independent_approval_rejects_builder_2_declared_by_audit_event(self) -> None:
        policy = {
            "rules": [
                {
                    "risk": "medium",
                    "action": "lifecycle-transition",
                    "required_roles": [{"role": "reviewer", "minimum": 2}],
                    "independent": True,
                }
            ]
        }
        builder_event = audit_event(1, "2025-01-01T00:00:00Z")
        builder_event["actor"] = {
            "actor_id": "builder-2", "role": "implementer"}
        approval_event = audit_event(
            2,
            "2025-01-01T00:00:01Z",
            "implemented",
            "verified",
            [
                {
                    "actor_id": "builder-2",
                    "role": "reviewer",
                    "reference": "review.md",
                },
                {
                    "actor_id": "reviewer-2",
                    "role": "reviewer",
                    "reference": "review.md",
                },
            ],
        )
        self.activate_compliance(
            [builder_event, approval_event], policy=policy, risk="medium"
        )

        result, report = self.json_result()

        self.assertEqual(result.returncode, 1)
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("COMPLIANCE_SELF_APPROVAL", codes)
        self.assertIn("COMPLIANCE_APPROVAL_COUNT", codes)

    def test_independent_approval_rejects_own_implementation_role_actor(self) -> None:
        policy = {
            "rules": [
                {
                    "risk": "medium",
                    "action": "lifecycle-transition",
                    "required_roles": [{"role": "reviewer", "minimum": 1}],
                    "independent": True,
                }
            ]
        }
        event = audit_event(
            1,
            "2025-01-01T00:00:00Z",
            "implemented",
            "verified",
            [
                {
                    "actor_id": "builder-3",
                    "role": "reviewer",
                    "reference": "review.md",
                }
            ],
        )
        event["actor"] = {"actor_id": "builder-3", "role": "implementation"}
        self.activate_compliance([event], policy=policy, risk="medium")

        result, report = self.json_result()

        self.assertEqual(result.returncode, 1)
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("COMPLIANCE_SELF_APPROVAL", codes)
        self.assertIn("COMPLIANCE_APPROVAL_COUNT", codes)

    def test_compliance_rejects_reversed_nested_actor_key_order(self) -> None:
        event = audit_event(1, "2025-01-01T00:00:00Z")
        event["actor"] = {"role": "implementer", "actor_id": "implementer-1"}
        self.activate_compliance([event])

        result, report = self.json_result()

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "COMPLIANCE_ORDER", {item["code"] for item in report["errors"]}
        )

    def test_high_risk_independence_floor_cannot_be_weakened_by_empty_policy(self) -> None:
        event = audit_event(
            1,
            "2025-01-01T00:00:00Z",
            "implemented",
            "verified",
            [
                {
                    "actor_id": "implementer-1",
                    "role": "independent-reviewer",
                    "reference": "review.md",
                }
            ],
        )
        self.activate_compliance([event], risk="high")

        result, report = self.json_result()

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "COMPLIANCE_SELF_APPROVAL",
            {item["code"] for item in report["errors"]},
        )

    def test_compliance_multi_repo_ids_and_revisions_match_evidence_and_config(self) -> None:
        repositories = [
            {"id": "current", "path": ".", "remote": None},
            {"id": "service", "path": "service", "remote": None},
        ]
        (self.fixture.root / ".git").mkdir()
        (self.fixture.root / "service" / ".git").mkdir(parents=True)
        event = audit_event(
            1,
            "2025-01-01T00:00:00Z",
            repositories=[
                {"repository_id": "current", "revision": "a" * 40},
                {"repository_id": "service", "revision": "d" * 40},
            ],
        )
        evidence = self.activate_compliance(
            [event],
            modules=["compliance", "evidence", "enforcement", "multi-repo"],
            repositories=repositories,
        )
        scopes = evidence["repository_scope"]
        assert isinstance(scopes, list)
        scopes.append(
            {
                "repository_id": "service",
                "base": "c" * 40,
                "head": "d" * 40,
                "committed_range": f"{'c' * 40}..{'d' * 40}",
                "uncommitted_entries": [],
                "snapshot_sha256": hashlib.sha256(b"[]").hexdigest(),
            }
        )
        evidence["requirement_coverage"][0]["repository_ids"] = [
            "current", "service"]
        evidence["checks"][0]["repository_ids"] = ["current", "service"]
        self.fixture.write_evidence(evidence)
        result, report = self.json_result()
        self.assertEqual(result.returncode, 0, report)

        event["repositories"][1]["revision"] = "e" * 40
        self.fixture.write_audit([event])
        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "COMPLIANCE_REPOSITORY_REVISION",
            {item["code"] for item in report["errors"]},
        )

    def test_installed_or_partially_enabled_compliance_adds_no_audit_burden(self) -> None:
        self.fixture.install_module("enforcement")
        self.fixture.install_evidence()
        self.fixture.install_compliance()
        self.fixture.write_catalog(
            ["compliance", "evidence", "enforcement"],
            {"compliance": ["evidence", "enforcement"]},
        )
        self.fixture.configure(["evidence", "enforcement"], "evidence")
        self.fixture.write_audit(["malformed"], raw=True)
        result, report = self.json_result()
        self.assertEqual(result.returncode, 0, report)

        self.fixture.configure(["compliance"], "evidence")
        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("MODULE_DEPENDENCY_DISABLED", codes)
        self.assertNotIn("COMPLIANCE_JSON_INVALID", codes)

    def test_artifact_ids_references_and_recorded_transitions(self) -> None:
        specs = self.fixture.root / "specs"
        work = self.fixture.root / ".work" / "feature"
        specs.mkdir()
        work.mkdir(parents=True)
        (specs / "one.md").write_text(
            "---\nid: SPEC-001\nstatus: planned\ndepends_on: []\n---\n**REQ-001**: Need.\n",
            encoding="utf-8",
        )
        (work / "plan.md").write_text(
            "---\nid: PLAN-001\nsources:\n  - SPEC-999\nstatus: draft\nrisk: low\nrisk_rationale: Recorded.\n---\n",
            encoding="utf-8",
        )
        (work / "tasks.md").write_text(
            "# Tasks\n\n- Plan: PLAN-001\n\n### TASK-001: Work\n- Plan: PLAN-001\n- Source items: REQ-999\n- State: done\n- Depends on: TASK-999\n- Result: pending\n",
            encoding="utf-8",
        )
        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("ARTIFACT_REFERENCE_DANGLING", codes)
        self.assertIn("TASK_DONE_WITHOUT_RESULT", codes)
        self.assertIn("TASK_DEPENDENCY_NOT_DONE", codes)

    def test_active_modules_require_present_catalog_and_catalog_membership(self) -> None:
        self.fixture.install_module("enforcement")
        self.fixture.configure(["enforcement"])
        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        self.assertIn("CATALOG_REQUIRED", {
                      item["code"] for item in report["errors"]})

        self.fixture.write_catalog(["evidence"])
        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        self.assertIn("MODULE_NOT_CATALOGED", {
                      item["code"] for item in report["errors"]})

    def test_verified_evidence_review_path_directory_and_change_ids(self) -> None:
        result, report = self.activate_evidence(complete_evidence())
        self.assertEqual(result.returncode, 0, report)
        evidence_dir = self.fixture.root / "evidence" / "TASK-010"

        (evidence_dir / "review.md").unlink()
        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        self.assertIn("EVIDENCE_REVIEW_REFERENCE", {
                      item["code"] for item in report["errors"]})

        outside = self.fixture.root / "outside-review.md"
        outside.write_text("do-not-echo", encoding="utf-8")
        (evidence_dir / "review.md").symlink_to(outside)
        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        self.assertIn("PATH_SYMLINK", {item["code"]
                      for item in report["errors"]})
        self.assertNotIn("do-not-echo", result.stdout)

        (evidence_dir / "review.md").unlink()
        (evidence_dir / "review.md").write_text("# Review\n", encoding="utf-8")
        renamed = evidence_dir.with_name("WRONG-DIRECTORY")
        evidence_dir.rename(renamed)
        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        self.assertIn("EVIDENCE_CHANGE_DIRECTORY", {
                      item["code"] for item in report["errors"]})

        duplicate = renamed.with_name("SECOND-DIRECTORY")
        shutil.copytree(renamed, duplicate)
        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        self.assertIn("EVIDENCE_CHANGE_ID_DUPLICATE", {
                      item["code"] for item in report["errors"]})

    def test_task9_semantic_parity_for_contract_arrays_and_scope_duplicates(self) -> None:
        cases: list[dict[str, object]] = []
        for field in ("expected_evidence", "agent_roles", "review_focus"):
            document = complete_evidence()
            contract = document["change_contract"]
            assert isinstance(contract, dict)
            contract[field] = []
            cases.append(document)
        duplicate_scope = complete_evidence()
        scopes = duplicate_scope["repository_scope"]
        assert isinstance(scopes, list)
        scope = scopes[0]
        assert isinstance(scope, dict)
        entry = {"path": "src/change.py",
                 "state": "untracked", "sha256": "0" * 64}
        scope["uncommitted_entries"] = [entry, dict(entry)]
        scope["snapshot_sha256"] = hashlib.sha256(
            json.dumps([entry, entry], sort_keys=True,
                       separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        cases.append(duplicate_scope)

        for document in cases:
            with self.subTest(document=document):
                self.fixture.close()
                self.fixture = EnforcementFixture()
                source_errors = source_validator.validate_evidence_document(
                    document)
                self.assertTrue(source_errors)
                result, report = self.activate_evidence(document)
                self.assertEqual(result.returncode, 1)
                self.assertFalse(report["valid"])

    def test_in_progress_empty_lifecycle_references_match_source_rejection(self) -> None:
        document = complete_evidence()
        lifecycle = document["lifecycle"]
        scopes = document["repository_scope"]
        review = document["review"]
        assert isinstance(lifecycle, dict)
        assert isinstance(scopes, list)
        scope = scopes[0]
        assert isinstance(scope, dict)
        assert isinstance(review, dict)
        lifecycle.update(
            status="in-progress", transition="not-requested", evidence_references=[]
        )
        scope.update(
            base=None,
            head=None,
            committed_range=None,
            uncommitted_entries=[],
            snapshot_sha256=None,
        )
        review.update(
            reviewer_role=None,
            reviewer_id=None,
            prior_participation=[],
            fresh_context=False,
            independence="not-reviewed",
            independence_basis=None,
            verdict="not-reviewed",
            reference=None,
        )

        source_errors = source_validator.validate_evidence_document(document)
        self.assertTrue(
            any("lifecycle.evidence_references" in error for error in source_errors))
        result, report = self.activate_evidence(document)
        self.assertEqual(result.returncode, 1)
        self.assertIn("EVIDENCE_LIFECYCLE", {
                      item["code"] for item in report["errors"]})

    def test_task_graph_requires_fields_states_and_blocker_coherence(self) -> None:
        work = self.fixture.root / ".work" / "feature"
        work.mkdir(parents=True)
        (work / "tasks.md").write_text(
            "# Tasks\n\n"
            "### TASK-001: Missing links\n"
            "- State: pending\n- Depends on: none\n- Blocker: none\n- Result: pending\n\n"
            "### TASK-002: Bad blocked\n"
            "- Plan: PLAN-001\n- Source items: request:TASK-010\n"
            "- State: blocked\n- Depends on: none\n- Blocker: none\n- Result: pending\n\n"
            "### TASK-003: Contradictory blocker\n"
            "- Plan: PLAN-001\n- Source items: request:TASK-010\n"
            "- State: ready\n- Depends on: none\n- Blocker: waiting for access\n- Result: pending\n",
            encoding="utf-8",
        )
        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("TASK_STATE_INVALID", codes)
        self.assertIn("TASK_FIELD_REQUIRED", codes)
        self.assertIn("TASK_BLOCKER_INCONSISTENT", codes)

    def test_installed_but_disabled_multi_repo_adds_no_checkout_burden(self) -> None:
        self.fixture.install_module("multi-repo")
        self.fixture.write_catalog(["multi-repo"])
        self.fixture.configure(
            [],
            repositories=[
                {
                    "id": "unavailable",
                    "path": "${TASK011_UNSET}/missing",
                    "remote": None,
                }
            ],
        )

        result, report = self.json_result(dict(os.environ))

        self.assertEqual(result.returncode, 0, report)
        self.assertTrue(report["valid"])

    def test_enabled_multi_repo_requires_a_repository_map(self) -> None:
        self.fixture.install_module("multi-repo")
        self.fixture.write_catalog(["multi-repo"])
        self.fixture.configure(["multi-repo"])

        result, report = self.json_result()

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "MULTI_REPO_REPOSITORIES_REQUIRED",
            {item["code"] for item in report["errors"]},
        )

    def test_multi_repo_accepts_existing_current_and_relative_git_checkouts(self) -> None:
        self.init_git(self.fixture.root)
        self.init_git(self.fixture.root / "service")
        repositories = [
            {"id": "current", "path": ".", "remote": None},
            {"id": "service", "path": "service", "remote": None},
        ]
        self.activate_multi_repo(repositories)

        result, report = self.json_result()

        self.assertEqual(result.returncode, 0, report)
        self.assertTrue(report["valid"])

    def test_multi_repo_expands_one_exact_environment_placeholder_for_sibling(self) -> None:
        self.init_git(self.fixture.root)
        sibling = self.fixture.root.with_name(
            self.fixture.root.name + "-sibling")
        self.addCleanup(lambda: shutil.rmtree(sibling, ignore_errors=True))
        self.init_git(sibling)
        repositories = [
            {"id": "current", "path": ".", "remote": None},
            {
                "id": "sibling",
                "path": "${TASK011_WORKSPACE}/" + sibling.name,
                "remote": None,
            },
        ]
        self.activate_multi_repo(repositories)
        environment = dict(os.environ)
        environment["TASK011_WORKSPACE"] = str(
            self.fixture.root.parent.resolve())

        result, report = self.json_result(environment)

        self.assertEqual(result.returncode, 0, report)
        self.assertTrue(report["valid"])

    def test_environment_checkout_rejects_symlink_in_existing_base_ancestor(self) -> None:
        self.init_git(self.fixture.root)
        resolved_root = self.fixture.root.resolve()
        actual_workspace = resolved_root / "actual-workspace"
        repository = actual_workspace / "base" / "service"
        self.init_git(repository)
        linked_workspace = resolved_root / "linked-workspace"
        linked_workspace.symlink_to(actual_workspace, target_is_directory=True)
        self.activate_multi_repo(
            [
                {"id": "current", "path": ".", "remote": None},
                {
                    "id": "service",
                    "path": "${TASK011_LINKED_BASE}/service",
                    "remote": None,
                },
            ]
        )
        environment = dict(os.environ)
        environment["TASK011_LINKED_BASE"] = str(linked_workspace / "base")

        result, report = self.json_result(environment)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "MULTI_REPO_CHECKOUT_INVALID",
            {item["code"] for item in report["errors"]},
        )

    def test_multi_repo_blocks_unresolved_missing_non_git_non_directory_and_symlink_paths(self) -> None:
        cases = ("unresolved", "missing", "non-git",
                 "non-directory", "symlink")
        for case in cases:
            with self.subTest(case=case):
                if case != cases[0]:
                    self.fixture.close()
                    self.fixture = EnforcementFixture()
                self.init_git(self.fixture.root)
                path = "${TASK011_MISSING}/repo" if case == "unresolved" else case
                if case == "non-git":
                    (self.fixture.root / path).mkdir()
                elif case == "non-directory":
                    (self.fixture.root /
                     path).write_text("not a directory", encoding="utf-8")
                elif case == "symlink":
                    target = self.fixture.root / "target-repo"
                    self.init_git(target)
                    (self.fixture.root / path).symlink_to(target,
                                                          target_is_directory=True)
                repositories = [
                    {"id": "current", "path": ".", "remote": None},
                    {"id": "other", "path": path, "remote": None},
                ]
                self.activate_multi_repo(repositories)

                result, report = self.json_result(dict(os.environ))

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "MULTI_REPO_CHECKOUT_INVALID",
                    {item["code"] for item in report["errors"]},
                )

    def test_duplicate_repository_ids_are_configuration_errors(self) -> None:
        repositories = [
            {"name": "same", "path": ".", "remote": None},
            {"name": "same", "path": "other", "remote": None},
        ]
        self.fixture.configure(["multi-repo"], repositories=repositories)

        result, report = self.json_result()

        self.assertEqual(result.returncode, 2)
        self.assertIn("CONFIG_TYPE", {item["code"]
                      for item in report["errors"]})

    def test_multi_repo_tasks_require_one_known_primary_repository(self) -> None:
        self.init_git(self.fixture.root)
        self.activate_multi_repo(
            [{"id": "current", "path": ".", "remote": None}]
        )
        work = self.fixture.root / ".work" / "feature"
        work.mkdir(parents=True)
        (work / "tasks.md").write_text(
            "# Tasks\n\n"
            "### TASK-001: Missing repository\n"
            "- Plan: accepted-plan\n- Source items: request:TASK-011\n"
            "- State: ready\n- Depends on: none\n- Blocker: none\n- Result: pending\n\n"
            "### TASK-002: Unknown repository\n"
            "- Plan: accepted-plan\n- Source items: request:TASK-011\n"
            "- Repository: absent\n- State: ready\n- Depends on: none\n"
            "- Cross-repo depends on: none\n- Integration evidence: none\n"
            "- Dirty status: clean\n- Ownership/isolation: exclusive-owner\n"
            "- Blocker: none\n- Result: pending\n",
            encoding="utf-8",
        )

        result, report = self.json_result()

        self.assertEqual(result.returncode, 1)
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("MULTI_REPO_TASK_REPOSITORY_REQUIRED", codes)
        self.assertIn("MULTI_REPO_TASK_REPOSITORY_UNKNOWN", codes)

    def test_cross_repo_dependencies_need_matching_refs_and_integration_evidence(self) -> None:
        self.init_git(self.fixture.root)
        self.init_git(self.fixture.root / "service")
        self.activate_multi_repo(
            [
                {"id": "current", "path": ".", "remote": None},
                {"id": "service", "path": "service", "remote": None},
            ]
        )
        work = self.fixture.root / ".work" / "feature"
        work.mkdir(parents=True)
        tasks = (
            "# Tasks\n\n"
            "### TASK-001: Current result\n"
            "- Plan: accepted-plan\n- Source items: request:TASK-011\n"
            "- Repository: current\n- State: done\n- Depends on: none\n"
            "- Cross-repo depends on: none\n- Integration evidence: none\n"
            "- Dirty status: clean\n"
            "- Ownership/isolation: exclusive-owner\n"
            "- Blocker: none\n- Result: focused check passed\n\n"
            "### TASK-002: Service result\n"
            "- Plan: accepted-plan\n- Source items: request:TASK-011\n"
            "- Repository: service\n- State: ready\n- Depends on: TASK-001\n"
            "- Cross-repo depends on: none\n- Integration evidence: none\n"
            "- Dirty status: dirty-nonconflicting\n"
            "- Ownership/isolation: isolated\n"
            "- Blocker: none\n- Result: pending\n"
        )
        task_path = work / "tasks.md"
        task_path.write_text(tasks, encoding="utf-8")

        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "MULTI_REPO_TASK_CROSS_REPO",
            {item["code"] for item in report["errors"]},
        )

        task_path.write_text(
            tasks.replace(
                "- Cross-repo depends on: none\n- Integration evidence: none\n"
                "- Dirty status: dirty-nonconflicting\n",
                "- Cross-repo depends on: TASK-001\n"
                "- Integration evidence: contract test procedure in PLAN-011\n"
                "- Dirty status: dirty-nonconflicting\n",
            ),
            encoding="utf-8",
        )
        result, report = self.json_result()
        self.assertEqual(result.returncode, 0, report)

        task_path.write_text(
            task_path.read_text(encoding="utf-8").replace(
                "- Cross-repo depends on: TASK-001\n",
                "- Cross-repo depends on: TASK-001, TASK-001\n",
            ),
            encoding="utf-8",
        )
        result, report = self.json_result()
        codes = {item["code"] for item in report["errors"]}
        self.assertEqual(result.returncode, 1)
        self.assertIn("MULTI_REPO_TASK_CROSS_REPO_DUPLICATE", codes)
        self.assertNotIn("MULTI_REPO_TASK_CROSS_REPO", codes)

    def test_multi_repo_task_control_enums_and_blockers_are_exact(self) -> None:
        self.init_git(self.fixture.root)
        self.activate_multi_repo(
            [{"id": "current", "path": ".", "remote": None}]
        )
        work = self.fixture.root / ".work" / "feature"
        work.mkdir(parents=True)
        task_path = work / "tasks.md"
        valid_tasks = (
            "# Tasks\n\n"
            "### TASK-001: Ready clean\n"
            "- Plan: accepted-plan\n- Source items: request:TASK-011\n"
            "- Repository: current\n- State: ready\n- Depends on: none\n"
            "- Cross-repo depends on: none\n- Integration evidence: none\n"
            "- Dirty status: clean\n- Ownership/isolation: exclusive-owner\n"
            "- Blocker: none\n- Result: pending\n\n"
            "### TASK-002: Active isolated\n"
            "- Plan: accepted-plan\n- Source items: request:TASK-011\n"
            "- Repository: current\n- State: in-progress\n- Depends on: none\n"
            "- Cross-repo depends on: none\n- Integration evidence: none\n"
            "- Dirty status: dirty-nonconflicting\n- Ownership/isolation: isolated\n"
            "- Blocker: none\n- Result: pending\n\n"
            "### TASK-003: Completed\n"
            "- Plan: accepted-plan\n- Source items: request:TASK-011\n"
            "- Repository: current\n- State: done\n- Depends on: none\n"
            "- Cross-repo depends on: none\n- Integration evidence: none\n"
            "- Dirty status: clean\n- Ownership/isolation: exclusive-owner\n"
            "- Blocker: none\n- Result: exact controls validated\n\n"
            "### TASK-004: Conflict blocked\n"
            "- Plan: accepted-plan\n- Source items: request:TASK-011\n"
            "- Repository: current\n- State: blocked\n- Depends on: none\n"
            "- Cross-repo depends on: none\n- Integration evidence: none\n"
            "- Dirty status: blocked-conflict\n- Ownership/isolation: unknown\n"
            "- Blocker: dirty-status:blocked-conflict, ownership-isolation:unknown\n"
            "- Result: pending\n\n"
            "### TASK-005: Stale unknown\n"
            "- Plan: accepted-plan\n- Source items: request:TASK-011\n"
            "- Repository: current\n- State: stale\n- Depends on: none\n"
            "- Cross-repo depends on: none\n- Integration evidence: none\n"
            "- Dirty status: unknown\n- Ownership/isolation: unknown\n"
            "- Blocker: none\n- Result: pending\n"
        )
        task_path.write_text(valid_tasks, encoding="utf-8")

        result, report = self.json_result()
        self.assertEqual(result.returncode, 0, report)

        task_path.write_text(
            valid_tasks.replace("- Dirty status: clean\n",
                                "- Dirty status: clean after inspection\n", 1),
            encoding="utf-8",
        )
        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "MULTI_REPO_TASK_CONTROL_INVALID",
            {item["code"] for item in report["errors"]},
        )

        task_path.write_text(
            valid_tasks.replace(
                "- Dirty status: clean\n- Ownership/isolation: exclusive-owner\n",
                "- Dirty status: unknown\n- Ownership/isolation: blocked-conflict\n",
                1,
            ),
            encoding="utf-8",
        )
        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "MULTI_REPO_TASK_CONTROL_BLOCKED",
            {item["code"] for item in report["errors"]},
        )

        task_path.write_text(
            valid_tasks.replace(
                "- Blocker: dirty-status:blocked-conflict, ownership-isolation:unknown\n",
                "- Blocker: ownership-isolation:unknown\n",
            ),
            encoding="utf-8",
        )
        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "MULTI_REPO_TASK_BLOCKER_MISMATCH",
            {item["code"] for item in report["errors"]},
        )

    def test_multi_repo_evidence_scope_and_coverage_match_affected_repositories(self) -> None:
        self.init_git(self.fixture.root)
        self.init_git(self.fixture.root / "service")
        repositories = [
            {"id": "current", "path": ".", "remote": None},
            {"id": "service", "path": "service", "remote": None},
        ]
        self.activate_multi_repo(repositories, evidence=True)
        document = complete_evidence()
        scopes = document["repository_scope"]
        assert isinstance(scopes, list)
        scopes.append(
            {
                "repository_id": "service",
                "base": "not-applicable",
                "head": "not-applicable",
                "committed_range": "not-applicable",
                "uncommitted_entries": [],
                "snapshot_sha256": hashlib.sha256(b"[]").hexdigest(),
            }
        )
        evidence_path = self.fixture.write_evidence(document)
        (evidence_path.parent / "review.md").write_text("# Review\n", encoding="utf-8")

        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "MULTI_REPO_EVIDENCE_SCOPE_MISMATCH",
            {item["code"] for item in report["errors"]},
        )

        document["requirement_coverage"][0]["repository_ids"] = [
            "current", "service"
        ]
        document["checks"][0]["repository_ids"] = ["current", "service"]
        self.fixture.write_evidence(document)
        result, report = self.json_result()
        self.assertEqual(result.returncode, 0, report)

        document["checks"][0]["repository_ids"] = ["unknown"]
        self.fixture.write_evidence(document)
        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "MULTI_REPO_EVIDENCE_REPOSITORY_UNKNOWN",
            {item["code"] for item in report["errors"]},
        )

    def test_all_root_relative_reads_reject_symlink_components(self) -> None:
        outside = Path(self.fixture.temporary.name).parent / \
            "outside-task10-paths"
        outside.mkdir(exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))
        (outside / "secret").write_text("do-not-echo", encoding="utf-8")

        agents = self.fixture.root / ".agents"
        agents.symlink_to(outside, target_is_directory=True)
        result, report = self.json_result()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PATH_SYMLINK", {item["code"]
                      for item in report["errors"]})
        self.assertNotIn("do-not-echo", result.stdout)

        agents.unlink()
        self.fixture.install_module("enforcement")
        self.fixture.install_evidence()
        self.fixture.write_catalog(["enforcement", "evidence"])
        self.fixture.configure(["enforcement", "evidence"], "evidence")
        schema = self.fixture.root / ".agents" / "modules" / \
            "evidence" / "assets" / "evidence.schema.json"
        schema.unlink()
        schema.symlink_to(outside / "secret")
        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        self.assertIn("PATH_SYMLINK", {item["code"]
                      for item in report["errors"]})
        self.assertNotIn("do-not-echo", result.stdout)

        for relative in ("kit-catalog.json", "agentic-sdlc-kit.json", "project.json"):
            with self.subTest(relative=relative):
                self.fixture.close()
                self.fixture = EnforcementFixture()
                agents = self.fixture.root / ".agents"
                agents.mkdir()
                (agents / relative).symlink_to(outside / "secret")
                result, report = self.json_result()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("PATH_SYMLINK", {item["code"]
                              for item in report["errors"]})
                self.assertNotIn("do-not-echo", result.stdout)

    def test_percent_encoded_sensitive_http_query_key_is_rejected_and_redacted(self) -> None:
        agents = self.fixture.root / ".agents"
        agents.mkdir()
        secret = "https://example.test/repo?%61ccess_token=do-not-echo"
        config = json.loads(project_config([]))
        config["tracker"].update(kind="web", location=secret)
        (agents / "project.json").write_text(
            json.dumps(config), encoding="utf-8"
        )
        result, report = self.json_result()
        self.assertEqual(result.returncode, 2)
        self.assertIn("CONFIG_STRING", {
                      item["code"] for item in report["errors"]})
        self.assertNotIn("do-not-echo", result.stdout + result.stderr)

    def test_json_and_human_output_exit_contract_and_determinism(self) -> None:
        self.fixture.configure(["missing-b", "missing-a"])
        first = self.fixture.run()
        second = self.fixture.run()
        human = self.fixture.run("human")
        self.assertEqual(first.returncode, 1)
        self.assertEqual(first.stdout, second.stdout)
        report = json.loads(first.stdout)
        self.assertEqual(
            list(report),
            ["schema_version", "valid", "errors", "warnings", "summary", "counts"],
        )
        self.assertEqual(human.returncode, 1)
        self.assertIn("Agentic SDLC enforcement: INVALID", human.stdout)
        self.assertIn("[MODULE_ENABLED_MISSING]", human.stdout)
        self.assertEqual(first.stderr, "")
        self.assertEqual(human.stderr, "")

    def test_checker_is_read_only_and_has_no_command_or_network_imports(self) -> None:
        marker = self.fixture.root / "command-ran"
        trap = self.fixture.root / "trap"
        trap.mkdir()
        fake_git = trap / "git"
        fake_git.write_text(f"#!/bin/sh\ntouch {marker}\n", encoding="utf-8")
        fake_git.chmod(0o755)
        before = self.snapshot()
        result = subprocess.run(
            [sys.executable, str(CHECK), "--root", str(self.fixture.root)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "PATH": str(trap)},
            check=False,
        )
        after = self.snapshot()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(before, after)
        self.assertFalse(marker.exists())
        package_files = [CHECK] + sorted((CHECK.parent / "lib").glob("*.py"))
        self.assertEqual(
            {path.name for path in package_files},
            {"check.py", "__init__.py", "artifacts.py", "compliance.py",
             "evidence.py", "paths.py", "project.py", "report.py"},
        )
        imports = set()
        mutators = []
        for path in package_files:
            tree = ast.parse(path.read_text(
                encoding="utf-8"), filename=str(path))
            imports.update(
                alias.name.split(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            )
            imports.update(
                node.module.split(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module
            )
            mutators.extend(
                node.func.attr for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"write_text", "write_bytes", "unlink", "mkdir", "rename", "replace"}
            )
        self.assertTrue({"subprocess", "socket", "http"}.isdisjoint(imports))
        self.assertNotIn("urllib.request", imports)
        self.assertEqual(mutators, [])

    def test_checker_anchors_its_own_lib_over_root_and_cwd_decoys(self) -> None:
        target_decoy = self.fixture.root / "lib"
        target_decoy.mkdir()
        (target_decoy / "__init__.py").write_text(
            "raise RuntimeError('root decoy imported')\n", encoding="utf-8")
        with tempfile.TemporaryDirectory() as cwd:
            cwd_path = Path(cwd)
            (cwd_path / "lib").mkdir()
            (cwd_path / "lib" / "__init__.py").write_text(
                "raise RuntimeError('cwd decoy imported')\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(CHECK), "--root", str(self.fixture.root),
                 "--format", "json"], cwd=cwd_path, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env={**os.environ, "PYTHONPATH": str(cwd_path)}, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")

    def test_symlinked_configured_root_is_not_read(self) -> None:
        outside = Path(self.fixture.temporary.name).parent / \
            "outside-enforcement-test"
        outside.mkdir(exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))
        (outside / "secret.md").write_text("do-not-echo", encoding="utf-8")
        (self.fixture.root / "specs").symlink_to(outside, target_is_directory=True)
        result, report = self.json_result()
        self.assertEqual(result.returncode, 1)
        self.assertIn("PATH_SYMLINK", {item["code"]
                      for item in report["errors"]})
        self.assertNotIn("do-not-echo", result.stdout)

    def test_invocation_errors_use_exit_two_and_structured_output(self) -> None:
        cases = (
            ("--format", "json", "--unknown"),
            ("--format", "json", "--root", str(self.fixture.root / "missing")),
        )
        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    [sys.executable, str(CHECK), *arguments],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                self.assertEqual(result.returncode, 2)
                report = json.loads(result.stdout)
                self.assertFalse(report["valid"])
                self.assertEqual(result.stderr, "")
                self.assertNotIn("Traceback", result.stdout)

    def test_source_catalog_validator_and_full_installer_integration(self) -> None:
        catalog = json.loads(
            (ROOT / ".agents" / "kit-catalog.json").read_text(encoding="utf-8")
        )
        enforcement = next(
            item for item in catalog["modules"] if item["name"] == "enforcement"
        )
        self.assertEqual(enforcement["depends_on"], [])
        self.assertIn("enforcement", catalog["profiles"]["full"]["modules"])

        validation = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate.py")],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(validation.returncode, 0,
                         validation.stdout + validation.stderr)

        target = self.fixture.root / "installed"
        target.mkdir()
        target = target.resolve()
        subprocess.run(
            ["git", "init", "--quiet", str(target)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        installed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "install.py"),
                str(target),
                "--profile",
                "full",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(installed.returncode, 0,
                         installed.stdout + installed.stderr)
        installed_check = target / ".agents" / "modules" / "enforcement" / "check.py"
        self.assertTrue(installed_check.is_file())
        manifest = json.loads(
            (target / ".agents" / "agentic-sdlc-kit.json").read_text(encoding="utf-8")
        )
        self.assertTrue(
            any(
                item["kind"] == "module" and item["name"] == "enforcement"
                for item in manifest["components"]
            )
        )
        (target / ".agents" / "project.json").write_text(
            project_config(["enforcement"]), encoding="utf-8"
        )
        smoke = subprocess.run(
            [sys.executable, str(installed_check), "--root",
             str(target), "--format", "json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(smoke.returncode, 0, smoke.stdout + smoke.stderr)

    def snapshot(self) -> dict[str, tuple[int, int, str]]:
        result: dict[str, tuple[int, int, str]] = {}
        for path in sorted(self.fixture.root.rglob("*")):
            relative = path.relative_to(self.fixture.root).as_posix()
            info = path.lstat()
            digest = hashlib.sha256(
                path.read_bytes()).hexdigest() if path.is_file() else ""
            result[relative] = (info.st_mode, info.st_mtime_ns, digest)
        return result


if __name__ == "__main__":
    unittest.main()

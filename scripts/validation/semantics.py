#!/usr/bin/env python3
"""Validate the portable Agent Skills in this repository."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional
try:
    from scripts.contracts.project import (
        ProjectConfigError,
        load_project,
        validate_project,
    )
# Direct ``python3 scripts/validate.py`` invocation.
except ModuleNotFoundError:
    from contracts.project import ProjectConfigError, load_project, validate_project
ROOT = Path(__file__).resolve().parents[2]
CATALOG_SCHEMA_VERSION = 1
SKILL_GROUPS = ("core", "utilities", "optional")
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://|#)([^)]+)\)")
MARKDOWN_DESTINATION_RE = re.compile(r"\]\(([^)\s]+)\)")
PUBLIC_DOCUMENT_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/usage-guide.md",
    "tests/scenarios.md",
)
PROVIDER_PATHS = (".claude/", ".cursor/", ".codex/")
SPEC_STATES = {"draft", "approved", "planned", "implemented", "verified"}
PROJECT_CONFIG_SCHEMA_VERSION = 2
PROJECT_CONFIG_PATH = Path(".agents/project.json")
PROJECT_SCHEMA_PATH = Path(".agents/skills/setup/assets/project.schema.json")
REVIEW_SIGNALS = (
    "Correctness",
    "Security",
    "Compatibility",
    "Maintainability",
    "Performance",
    "Accessibility",
    "Observability",
    "Cost",
    "Understandability",
)
REVIEW_EVIDENCE_CLASSES = (
    "observed evidence",
    "source-based inference",
    "unverified claim",
)
REVIEW_VERDICTS = ("approved", "changes-required", "blocked")
EVIDENCE_SCHEMA_VERSION = 1
EVIDENCE_FIELDS = (
    "schema_version",
    "change_id",
    "authoritative_sources",
    "lifecycle",
    "risk",
    "change_contract",
    "repository_scope",
    "requirement_coverage",
    "checks",
    "review",
    "known_limits",
    "remaining_risks",
    "follow_ups",
)
EVIDENCE_CHECK_KINDS = {
    "scoped", "regression", "failure-path", "recovery-rollback", "static", "other"
}
EVIDENCE_CHECK_STATUSES = {
    "passed", "failed", "skipped", "not-run", "not-applicable"
}
EVIDENCE_DEF_FIELDS = {
    "source": ("id", "reference"),
    "lifecycle": ("status", "transition", "evidence_references"),
    "risk": ("level", "rationale"),
    "change_contract": (
        "intent", "confirmed_why", "scope", "expected_evidence", "agent_roles",
        "review_focus",
    ),
    "repository_scope": (
        "repository_id", "base", "head", "committed_range", "uncommitted_entries",
        "snapshot_sha256",
    ),
    "uncommitted_entry": ("path", "state", "sha256"),
    "coverage": (
        "requirement_id", "repository_ids", "status", "implementation_references",
        "evidence_references",
    ),
    "check": (
        "id", "requirement_ids", "repository_ids", "kind", "required", "applicability",
        "not_applicable_reason", "status", "observed_result", "evidence_class",
        "output_reference",
    ),
    "review": (
        "reviewer_role", "reviewer_id", "implementers", "prior_participation",
        "fresh_context", "independence", "independence_basis", "verdict", "reference",
    ),
}
EVIDENCE_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EVIDENCE_REVISION_RE = re.compile(r"^[0-9a-f]{7,64}$")
COMPLIANCE_EVENT_FIELDS = (
    "schema_version", "event_id", "sequence", "timestamp", "change_id", "actor",
    "action", "previous_lifecycle", "new_lifecycle",
    "authoritative_source_references", "evidence_references", "approvals",
    "repositories",
)
COMPLIANCE_EVENT_DEF_FIELDS = {
    "actor": ("actor_id", "role"),
    "approval": ("actor_id", "role", "reference"),
    "repository": ("repository_id", "revision"),
}
COMPLIANCE_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
COMMON_CREDENTIAL_RE = re.compile(
    r"(?:\bghp_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b|"
    r"\bsk-[A-Za-z0-9]{20,}\b)"
)
SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?:api[-_ ]?key|credential|password|secret|token)\s*[:=]", re.IGNORECASE
)
PERSONAL_DATA_RE = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
SENSITIVE_QUERY_KEYS = {
    "token",
    "accesstoken",
    "authtoken",
    "refreshtoken",
    "idtoken",
    "apikey",
    "secret",
    "clientsecret",
    "password",
    "passwd",
    "credential",
    "credentials",
}
SENSITIVE_QUERY_SUFFIXES = (
    "token",
    "apikey",
    "secret",
    "password",
    "passwd",
    "credential",
    "credentials",
)


class DuplicateJSONObjectKey(ValueError):
    pass


def validate_v1_source_coverage(root: Path) -> list[str]:
    """Keep the checked-in v1 requirement and acceptance coverage complete."""
    try:
        from scripts.validation.artifacts import validate_evidence_document
    except ModuleNotFoundError:
        from validation.artifacts import validate_evidence_document
    spec_path = root / "specs" / "001-agentic-sdlc-kit-v1" / "spec.md"
    try:
        text = spec_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"Cannot read SPEC-001 source coverage {spec_path}: {exc}"]

    errors: list[str] = []
    requirement_ids = re.findall(r"\*\*(REQ-[0-9]{3})\*\*", text)
    acceptance_ids = re.findall(r"\*\*(AC-[0-9]{3})\*\*", text)
    requirements = set(requirement_ids)
    acceptance = set(acceptance_ids)
    for source_id in sorted(
        {item for item in requirement_ids if requirement_ids.count(item) > 1}
    ):
        errors.append(
            f"{spec_path}: duplicate requirement source ID: {source_id}")
    for source_id in sorted(
        {item for item in acceptance_ids if acceptance_ids.count(item) > 1}
    ):
        errors.append(
            f"{spec_path}: duplicate acceptance source ID: {source_id}")
    expected_requirements = {f"REQ-{index:03d}" for index in range(1, 37)}
    expected_acceptance = {f"AC-{index:03d}" for index in range(1, 13)}
    if requirements != expected_requirements:
        errors.append(
            f"{spec_path}: SPEC-001 requirement source coverage mismatch")
    if acceptance != expected_acceptance:
        errors.append(
            f"{spec_path}: SPEC-001 acceptance source coverage mismatch")
    status_match = re.search(r"^status:\s*([^\s]+)\s*$", text, re.MULTILINE)
    status = status_match.group(1) if status_match else ""
    if status not in {"planned", "verified"}:
        errors.append(
            f"{spec_path}: amended SPEC-001 must be planned or verified")
    if status == "verified":
        evidence_path = root / "evidence" / "spec-001" / "evidence.json"
        review_path = evidence_path.with_name("review.md")
        try:
            document = json.loads(evidence_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
            errors.append(
                f"{spec_path}: verified SPEC-001 evidence is unavailable: {exc}")
        else:
            errors.extend(validate_evidence_document(document, evidence_path))
            if isinstance(document, dict):
                lifecycle_value = document.get("lifecycle")
                review_value = document.get("review")
                lifecycle = lifecycle_value if isinstance(
                    lifecycle_value, dict) else {}
                review = review_value if isinstance(review_value, dict) else {}
                if (
                    document.get("change_id") != "spec-001"
                    or lifecycle.get("status") != "complete"
                    or lifecycle.get("transition") != "verified"
                    or review.get("verdict") != "approved"
                    or review.get("reference") != "review.md"
                ):
                    errors.append(
                        f"{spec_path}: verified SPEC-001 evidence does not support the transition"
                    )
        if not review_path.is_file() or review_path.is_symlink():
            errors.append(
                f"{spec_path}: verified SPEC-001 review.md is unavailable")
    return errors


def validate_repository(root: Path = ROOT) -> list[str]:
    from .distribution import (directory_names, load_catalog, validate_catalog,
                               validate_directory_set, validate_skill,
                               validate_global_resources)
    from .artifacts import (validate_optional_evidence_module,
                            validate_optional_enforcement_module,
                            validate_optional_multi_repo_module,
                            validate_optional_compliance_module,
                            validate_templates, validate_evidence_document,
                            validate_catalog_version)
    from .documentation import (validate_agents_bootstrap,
                                validate_public_documentation,
                                validate_provider_neutrality,
                                validate_readme_skill_table,
                                validate_documented_counts)
    root = Path(root)
    errors: list[str] = []
    agents_path = root / "AGENTS.md"
    if not agents_path.is_file():
        errors.append("Missing AGENTS.md")
    else:
        errors.extend(validate_provider_neutrality(agents_path))

    catalog, catalog_errors = load_catalog(root)
    errors.extend(catalog_errors)
    try:
        from scripts.validation.artifacts import validate_source_artifact_catalog
    except ModuleNotFoundError:
        from validation.artifacts import validate_source_artifact_catalog
    errors.extend(validate_source_artifact_catalog(root))
    expected_skills: Optional[set[str]] = None
    expected_modules: Optional[set[str]] = None
    if catalog is not None:
        expected_skills, expected_modules, schema_errors = validate_catalog(
            catalog)
        errors.extend(schema_errors)
        if not schema_errors:
            errors.extend(validate_global_resources(root, catalog))
        errors.extend(validate_provider_neutrality(
            root / ".agents" / "kit-catalog.json"))
        module_dependencies = {
            item["name"]: item["depends_on"]
            for item in catalog.get("modules", [])
            if isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and isinstance(item.get("depends_on"), list)
        }
        try:
            load_project(
                root,
                root / PROJECT_SCHEMA_PATH,
                module_names=expected_modules,
                module_dependencies=module_dependencies,
            )
        except ProjectConfigError as exc:
            errors.extend(
                f"{PROJECT_CONFIG_PATH}: {item.code} {item.field}: {item.message}"
                for item in exc.diagnostics
            )

    skills_root = root / ".agents" / "skills"
    found_skills = directory_names(skills_root, "skills", errors)
    if expected_skills is not None:
        validate_directory_set(expected_skills, found_skills, "skill", errors)
    for name in sorted(found_skills):
        skill_dir = skills_root / name
        errors.extend(validate_skill(skill_dir))
        errors.extend(validate_provider_neutrality(skill_dir))

    modules_root = root / ".agents" / "modules"
    found_modules: set[str] = set()
    if modules_root.exists():
        found_modules = directory_names(modules_root, "modules", errors)
    if expected_modules is not None:
        validate_directory_set(
            expected_modules, found_modules, "module", errors)
    for name in sorted(found_modules):
        module_dir = modules_root / name
        if not (module_dir / "MODULE.md").is_file():
            errors.append(f"{module_dir}: missing MODULE.md")
        errors.extend(validate_provider_neutrality(module_dir))
    errors.extend(validate_optional_evidence_module(modules_root))
    errors.extend(validate_optional_enforcement_module(modules_root))
    errors.extend(validate_optional_multi_repo_module(modules_root))
    errors.extend(validate_optional_compliance_module(modules_root))

    errors.extend(validate_templates(skills_root))
    if (root / "scripts" / "validate.py").is_file():
        try:
            from scripts.contracts.conventions import validate_conventions_and_rubrics
        except ModuleNotFoundError:
            from contracts.conventions import validate_conventions_and_rubrics
        errors.extend(validate_conventions_and_rubrics(root))
        errors.extend(validate_agents_bootstrap(root))
        errors.extend(validate_v1_source_coverage(root))
    if catalog is not None and (root / "scripts" / "validate.py").is_file():
        errors.extend(validate_public_documentation(root, catalog))
        if not errors:
            errors.extend(validate_catalog_version(root, catalog))
            readme_file = root / "README.md"
            guide_file = root / "docs" / "usage-guide.md"
            if readme_file.is_file() and guide_file.is_file():
                errors.extend(validate_readme_skill_table(
                    readme_file.read_text(encoding="utf-8"), catalog, readme_file))
                errors.extend(validate_documented_counts(
                    guide_file.read_text(encoding="utf-8"), catalog, guide_file))
    return errors


def main(root: Path = ROOT) -> int:
    errors = validate_repository(root)
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    skills_root = Path(root) / ".agents" / "skills"
    modules_root = Path(root) / ".agents" / "modules"
    skill_count = len(
        [path for path in skills_root.iterdir() if path.is_dir()])
    module_count = (
        len([path for path in modules_root.iterdir() if path.is_dir()])
        if modules_root.is_dir()
        else 0
    )
    print(
        "Validation passed: catalog is valid; "
        f"{skill_count} skills and {module_count} modules match the distribution"
    )
    return 0

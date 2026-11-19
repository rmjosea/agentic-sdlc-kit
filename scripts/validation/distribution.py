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
try:
    from scripts.validation.artifacts import parse_frontmatter
except ModuleNotFoundError:
    from validation.artifacts import parse_frontmatter
ROOT = Path(__file__).resolve().parents[2]
CATALOG_SCHEMA_VERSION = 2
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


def validate_skill(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        return [f"{skill_dir}: missing SKILL.md"]

    try:
        text = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"{skill_file}: cannot read UTF-8 content: {exc}"]
    lines = text.splitlines()
    try:
        metadata = parse_frontmatter(text, skill_file)
    except ValueError as exc:
        return [str(exc)]

    name = metadata.get("name", "")
    description = metadata.get("description", "")
    if name != skill_dir.name:
        errors.append(
            f"{skill_file}: name must match directory ({skill_dir.name})")
    if not NAME_RE.fullmatch(name):
        errors.append(f"{skill_file}: invalid skill name {name!r}")
    if not description:
        errors.append(f"{skill_file}: description is required")
    elif "Use when" not in description:
        errors.append(f"{skill_file}: description must state 'Use when'")
    if len(lines) > 500:
        errors.append(f"{skill_file}: exceeds 500-line hard limit")
    elif len(lines) > 200:
        errors.append(f"{skill_file}: exceeds 200-line project target")

    for relative in LINK_RE.findall(text):
        try:
            skill_root = skill_dir.resolve()
            target = (skill_dir / relative).resolve()
        except (OSError, RuntimeError) as exc:
            errors.append(
                f"{skill_file}: cannot resolve local reference {relative!r}: {exc}"
            )
            continue
        try:
            target.relative_to(skill_root)
        except ValueError:
            errors.append(
                f"{skill_file}: reference leaves skill root: {relative}")
            continue
        if not target.exists():
            errors.append(f"{skill_file}: missing local reference: {relative}")
    return errors


def load_catalog(root: Path) -> tuple[Optional[dict[str, Any]], list[str]]:
    catalog_path = root / ".agents" / "kit-catalog.json"
    if not catalog_path.is_file():
        return None, [f"Catalog not found: {catalog_path}"]
    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            f"Malformed catalog JSON at {catalog_path}:{exc.lineno}:{exc.colno}: {exc.msg}"
        ]
    except RecursionError:
        return None, [
            f"Malformed catalog JSON at {catalog_path}: catalog JSON nesting is too deep"
        ]
    except (OSError, UnicodeError) as exc:
        return None, [f"Cannot read catalog {catalog_path}: {exc}"]
    if not isinstance(data, dict):
        return None, [f"Invalid catalog {catalog_path}: root must be an object"]
    return data, []


def string_list(value: Any, field: str, errors: list[str]) -> Optional[list[str]]:
    if not isinstance(value, list):
        errors.append(f"Invalid catalog: {field} must be an array")
        return None
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not NAME_RE.fullmatch(item):
            errors.append(
                f"Invalid catalog: {field}[{index}] must be a kebab-case string"
            )
            continue
        result.append(item)
    return result


def duplicate_values(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def module_cycle_errors(dependencies: dict[str, list[str]]) -> list[str]:
    errors: list[str] = []
    state: dict[str, int] = {}
    reported: set[tuple[str, ...]] = set()
    for root in sorted(dependencies):
        if state.get(root, 0) != 0:
            continue
        state[root] = 1
        path = [root]
        active_index = {root: 0}
        stack = [(root, iter(dependencies[root]))]
        while stack:
            name, children = stack[-1]
            try:
                dependency = next(children)
            except StopIteration:
                stack.pop()
                path.pop()
                active_index.pop(name)
                state[name] = 2
                continue
            if dependency not in dependencies:
                continue
            dependency_state = state.get(dependency, 0)
            if dependency_state == 0:
                state[dependency] = 1
                active_index[dependency] = len(path)
                path.append(dependency)
                stack.append((dependency, iter(dependencies[dependency])))
            elif dependency_state == 1:
                start = active_index[dependency]
                cycle = tuple(path[start:] + [dependency])
                if cycle not in reported:
                    reported.add(cycle)
                    errors.append(
                        "Invalid catalog: module dependency cycle: "
                        + " -> ".join(cycle)
                    )
    return errors


def transitive_module_dependencies(
    name: str, dependencies: dict[str, list[str]]
) -> set[str]:
    result: set[str] = set()
    pending = list(dependencies.get(name, []))
    while pending:
        dependency = pending.pop()
        if dependency in result or dependency not in dependencies:
            continue
        result.add(dependency)
        pending.extend(dependencies[dependency])
    result.discard(name)
    return result


def validate_catalog(
    data: dict[str, Any],
) -> tuple[Optional[set[str]], Optional[set[str]], list[str]]:
    errors: list[str] = []
    required = ("schema_version", "kit_version",
                "skill_groups", "modules", "global_resources", "profiles")
    for field in required:
        if field not in data:
            errors.append(f"Invalid catalog: missing required field '{field}'")
    for field in sorted(set(data) - set(required)):
        errors.append(f"Invalid catalog: unknown field '{field}'")

    schema_version = data.get("schema_version")
    if type(schema_version) is not int or schema_version != CATALOG_SCHEMA_VERSION:
        errors.append(
            f"Invalid catalog: schema_version must be {CATALOG_SCHEMA_VERSION}"
        )
    kit_version = data.get("kit_version")
    if not isinstance(kit_version, str) or not kit_version.strip():
        errors.append(
            "Invalid catalog: kit_version must be a non-empty string")

    global_resources = data.get("global_resources")
    if not isinstance(global_resources, list) or not global_resources:
        errors.append(
            "Invalid catalog: 'global_resources' must be a non-empty array")
    elif len(global_resources) != len(set(global_resources)) or any(
            not isinstance(item, str) or not item for item in global_resources):
        errors.append(
            "Invalid catalog: global_resources must contain unique paths")

    skill_names: Optional[set[str]] = None
    group_skills: dict[str, list[str]] = {}
    skill_groups = data.get("skill_groups")
    if not isinstance(skill_groups, dict):
        errors.append("Invalid catalog: 'skill_groups' must be an object")
    else:
        for group in SKILL_GROUPS:
            if group not in skill_groups:
                errors.append(
                    f"Invalid catalog: missing skill group '{group}'")
                continue
            names = string_list(
                skill_groups[group], f"skill_groups.{group}", errors)
            if names is not None:
                group_skills[group] = names
        for group in sorted(set(skill_groups) - set(SKILL_GROUPS)):
            errors.append(f"Invalid catalog: unknown skill group '{group}'")
        if len(group_skills) == len(SKILL_GROUPS):
            all_skills = [
                name for group in SKILL_GROUPS for name in group_skills[group]]
            for name in sorted(duplicate_values(all_skills)):
                errors.append(
                    f"Invalid catalog: duplicate skill component '{name}'")
            skill_names = set(all_skills)

    module_names: Optional[set[str]] = None
    module_dependencies: dict[str, list[str]] = {}
    modules = data.get("modules")
    if not isinstance(modules, list):
        errors.append("Invalid catalog: modules must be an array")
    else:
        modules_valid = True
        listed_module_names: list[str] = []
        for index, module in enumerate(modules):
            field = f"modules[{index}]"
            if not isinstance(module, dict):
                errors.append(f"Invalid catalog: {field} must be an object")
                modules_valid = False
                continue
            for unknown in sorted(set(module) - {"name", "description", "depends_on"}):
                errors.append(
                    f"Invalid catalog: unknown field '{field}.{unknown}'")
                modules_valid = False
            name = module.get("name")
            description = module.get("description")
            if not isinstance(name, str) or not NAME_RE.fullmatch(name):
                errors.append(
                    f"Invalid catalog: {field}.name must be a kebab-case string")
                modules_valid = False
                name = None
            if not isinstance(description, str) or not description.strip():
                errors.append(
                    f"Invalid catalog: {field}.description must be a non-empty string")
                modules_valid = False
            dependencies = string_list(module.get(
                "depends_on"), f"{field}.depends_on", errors)
            if dependencies is None:
                modules_valid = False
            if name is not None:
                listed_module_names.append(name)
                if dependencies is not None:
                    module_dependencies[name] = dependencies
                    for duplicate in sorted(duplicate_values(dependencies)):
                        errors.append(
                            f"Invalid catalog: duplicate dependency '{duplicate}' in module '{name}'"
                        )
        for name in sorted(duplicate_values(listed_module_names)):
            errors.append(
                f"Invalid catalog: duplicate module component '{name}'")
            modules_valid = False
        if modules_valid:
            module_names = set(listed_module_names)
            if skill_names is not None:
                for name in sorted(skill_names & module_names):
                    errors.append(
                        f"Invalid catalog: duplicate component name '{name}'")
            for name, dependencies in sorted(module_dependencies.items()):
                for dependency in dependencies:
                    if dependency not in module_names:
                        errors.append(
                            f"Invalid catalog: module '{name}' has unknown module dependency '{dependency}'"
                        )
            errors.extend(module_cycle_errors(module_dependencies))

    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        errors.append("Invalid catalog: profiles must be an object")
    else:
        selections: dict[str, tuple[list[str], list[str]]] = {}
        for required_profile in ("default", "full"):
            if required_profile not in profiles:
                errors.append(
                    f"Invalid catalog: missing profile '{required_profile}'")
        for profile_name, profile in profiles.items():
            field = f"profiles.{profile_name}"
            if not isinstance(profile_name, str) or not NAME_RE.fullmatch(profile_name):
                errors.append(
                    "Invalid catalog: profile names must be kebab-case strings")
                continue
            if not isinstance(profile, dict):
                errors.append(f"Invalid catalog: {field} must be an object")
                continue
            for unknown in sorted(set(profile) - {"skills", "modules"}):
                errors.append(
                    f"Invalid catalog: unknown field '{field}.{unknown}'")
            profile_skills = string_list(profile.get(
                "skills"), f"{field}.skills", errors)
            profile_modules = string_list(profile.get(
                "modules"), f"{field}.modules", errors)
            if profile_skills is None or profile_modules is None:
                continue
            selections[profile_name] = (profile_skills, profile_modules)
            for name in sorted(duplicate_values(profile_skills)):
                errors.append(
                    f"Invalid catalog: duplicate skill '{name}' in profile '{profile_name}'")
            for name in sorted(duplicate_values(profile_modules)):
                errors.append(
                    f"Invalid catalog: duplicate module '{name}' in profile '{profile_name}'")
            if skill_names is not None:
                for name in profile_skills:
                    if name not in skill_names:
                        errors.append(
                            f"Invalid catalog: profile '{profile_name}' references unknown skill '{name}'"
                        )
            if module_names is not None:
                selected_modules = set(profile_modules)
                for name in profile_modules:
                    if name not in module_names:
                        errors.append(
                            f"Invalid catalog: profile '{profile_name}' references unknown module '{name}'"
                        )
                for name in sorted(selected_modules & module_names):
                    missing = (
                        transitive_module_dependencies(
                            name, module_dependencies)
                        - selected_modules
                    )
                    for dependency in sorted(missing):
                        errors.append(
                            f"Invalid catalog: profile '{profile_name}' module '{name}' "
                            f"requires missing dependency '{dependency}'"
                        )
        default = selections.get("default")
        if default is not None and "core" in group_skills:
            missing_core = set(group_skills["core"]) - set(default[0])
            for name in sorted(missing_core):
                errors.append(
                    f"Invalid catalog: default profile is missing core skill '{name}'")
        if default is not None and "optional" in group_skills:
            selected_optional = set(default[0]) & set(group_skills["optional"])
            for name in sorted(selected_optional):
                errors.append(
                    f"Invalid catalog: default profile includes optional skill '{name}'"
                )
        full = selections.get("full")
        if full is not None:
            if skill_names is not None:
                for name in sorted(skill_names - set(full[0])):
                    errors.append(
                        f"Invalid catalog: full profile is missing skill '{name}'")
            if module_names is not None:
                for name in sorted(module_names - set(full[1])):
                    errors.append(
                        f"Invalid catalog: full profile is missing module '{name}'")

    return skill_names, module_names, errors


def directory_names(path: Path, label: str, errors: list[str]) -> set[str]:
    if not path.exists():
        errors.append(f"{label.capitalize()} directory not found: {path}")
        return set()
    if not path.is_dir():
        errors.append(f"{label.capitalize()} path is not a directory: {path}")
        return set()
    return {entry.name for entry in path.iterdir() if entry.is_dir()}


def validate_directory_set(
    expected: set[str], found: set[str], component: str, errors: list[str]
) -> None:
    for name in sorted(expected - found):
        errors.append(
            f"Catalog declared {component} directory is missing: {name}")
    for name in sorted(found - expected):
        errors.append(f"Unexpected {component} directory: {name}")


def validate_distribution_contract(catalog):
    """Return the catalog's distribution decision tuple."""
    return validate_catalog(catalog)


def validate_global_resources(root: Path, catalog: dict[str, Any]) -> list[str]:
    """Verify each catalog-declared global resource exists as one source file."""
    errors = []
    for relative in catalog.get("global_resources", []):
        if not isinstance(relative, str) or not (
                relative == "AGENTS.md" or relative.startswith(".agents/")):
            errors.append(f"Invalid catalog global resource path: {relative}")
            continue
        path = root / relative
        if not path.is_file() or path.is_symlink():
            errors.append(f"Missing catalog global resource: {path}")
    return errors

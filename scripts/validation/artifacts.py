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


try:
    from scripts.contracts import catalog as artifact_catalog_contract
except ModuleNotFoundError:
    from contracts import catalog as artifact_catalog_contract


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJSONObjectKey(key)
        result[key] = value
    return result


def parse_frontmatter(text: str, path: Path) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError(f"{path}: missing opening YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError(f"{path}: missing closing YAML frontmatter") from exc

    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"{path}: invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata


def parse_project_json(text: str, path: Path) -> dict[str, Any]:
    """Parse one project JSON object without accepting duplicate keys."""
    try:
        value = json.loads(text, object_pairs_hook=_unique_json_object)
    except DuplicateJSONObjectKey as exc:
        raise ValueError(
            f"{path}: project JSON contains a duplicate object key") from exc
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(
            f"{path}: project configuration must be bounded valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(
            f"{path}: project configuration root must be an object")
    return value


def validate_approval_policy(
    policy: Any, path: Path = Path(".agents/project.json")
) -> list[str]:
    """Validate the closed project approval-policy contract."""
    errors: list[str] = []
    if not isinstance(policy, dict) or set(policy) != {"rules"}:
        return [f"{path}: approval_policy must contain only rules; unknown fields are rejected"]
    rules = policy.get("rules")
    if not isinstance(rules, list):
        return [f"{path}: approval_policy.rules must be an array"]
    seen_rules: set[tuple[str, str]] = set()
    for index, rule in enumerate(rules):
        label = f"approval_policy.rules[{index}]"
        if not isinstance(rule, dict) or set(rule) != {
            "risk", "action", "required_roles", "independent"
        }:
            errors.append(
                f"{path}: {label} must contain only risk, action, required_roles, and independent"
            )
            continue
        risk = rule.get("risk")
        action = rule.get("action")
        if risk not in {"low", "medium", "high"}:
            errors.append(f"{path}: {label}.risk must be low, medium, or high")
        if not isinstance(action, str) or not NAME_RE.fullmatch(action):
            errors.append(
                f"{path}: {label}.action must be a kebab-case action")
        if isinstance(risk, str) and isinstance(action, str):
            key = (risk, action)
            if key in seen_rules:
                errors.append(
                    f"{path}: {label} duplicates a risk/action policy rule")
            seen_rules.add(key)
        independent = rule.get("independent")
        if type(independent) is not bool:
            errors.append(f"{path}: {label}.independent must be a boolean")
        elif risk == "high" and independent is False:
            errors.append(
                f"{path}: {label} cannot weaken mandatory high-risk independence"
            )
        roles = rule.get("required_roles")
        if not isinstance(roles, list):
            errors.append(f"{path}: {label}.required_roles must be an array")
            continue
        seen_roles: set[str] = set()
        for role_index, requirement in enumerate(roles):
            role_label = f"{label}.required_roles[{role_index}]"
            if not isinstance(requirement, dict) or set(requirement) != {
                "role", "minimum"
            }:
                errors.append(
                    f"{path}: {role_label} must contain only role and minimum"
                )
                continue
            role = requirement.get("role")
            minimum = requirement.get("minimum")
            if (
                not isinstance(role, str)
                or not role.strip()
                or len(role) > 500
                or any(ord(character) < 32 or ord(character) == 127 for character in role)
            ):
                errors.append(
                    f"{path}: {role_label}.role must be a bounded single-line declared role"
                )
            elif role in seen_roles:
                errors.append(
                    f"{path}: {role_label}.role must be unique in its rule")
            else:
                seen_roles.add(role)
            if type(minimum) is not int or not 1 <= minimum <= 100:
                errors.append(
                    f"{path}: {role_label}.minimum must be an integer from 1 to 100"
                )
    errors.extend(_inspect_evidence_safety(policy, "approval_policy", path))
    return errors


def validate_project_config(
    config: dict[str, Any], path: Path, schema_path: Optional[Path] = None,
    module_names: Optional[set[str]] = None,
    module_dependencies: Optional[dict[str, list[str]]] = None,
) -> list[str]:
    """Validate canonical project JSON through the shared v2 contract."""
    try:
        diagnostics = validate_project(
            config,
            schema_path or ROOT / PROJECT_SCHEMA_PATH,
            module_names=module_names,
            module_dependencies=module_dependencies,
        )
    except ProjectConfigError as exc:
        diagnostics = exc.diagnostics
    return [f"{path}: {item.code} {item.field}: {item.message}" for item in diagnostics]


def _evidence_object(
    value: Any, fields: tuple[str, ...], label: str, path: Path, errors: list[str]
) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        errors.append(f"{path}: {label} must be an object")
        return None
    expected = set(fields)
    for field in fields:
        if field not in value:
            errors.append(f"{path}: {label} missing required field: {field}")
    for field in sorted(set(value) - expected):
        errors.append(f"{path}: {label} unknown field: {field}")
    return value


def _evidence_string(
    value: Any, label: str, path: Path, errors: list[str], nullable: bool = False
) -> bool:
    if nullable and value is None:
        return True
    if not isinstance(value, str) or not value.strip():
        suffix = " or null" if nullable else ""
        errors.append(f"{path}: {label} must be a non-empty string{suffix}")
        return False
    valid = True
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        errors.append(
            f"{path}: {label} must not contain a newline or control character"
        )
        valid = False
    if len(value) > 500:
        errors.append(
            f"{path}: {label} must be concise (at most 500 characters)")
        valid = False
    return valid


def _evidence_string_array(
    value: Any,
    label: str,
    path: Path,
    errors: list[str],
    min_items: int = 0,
) -> Optional[list[str]]:
    if not isinstance(value, list):
        errors.append(f"{path}: {label} must be an array")
        return None
    if len(value) < min_items:
        errors.append(
            f"{path}: {label} must contain at least {min_items} item")
    for index, item in enumerate(value):
        _evidence_string(item, f"{label}[{index}]", path, errors)
    return value


def _evidence_enum(
    value: Any, allowed: set[str], label: str, path: Path, errors: list[str]
) -> bool:
    if not isinstance(value, str) or value not in allowed:
        errors.append(
            f"{path}: {label} must be one of " + ", ".join(sorted(allowed))
        )
        return False
    return True


def _inspect_evidence_safety(value: Any, label: str, path: Path) -> list[str]:
    errors: list[str] = []
    pending = [(value, label)]
    while pending:
        item, item_label = pending.pop()
        if isinstance(item, dict):
            pending.extend(
                (child, f"{item_label}.{key}") for key, child in item.items()
            )
        elif isinstance(item, list):
            pending.extend(
                (child, f"{item_label}[{index}]")
                for index, child in enumerate(item)
            )
        elif isinstance(item, str):
            if any(
                ord(character) < 32 or ord(character) == 127 for character in item
            ):
                errors.append(
                    f"{path}: {item_label} must not contain a newline or control character"
                )
            if len(item) > 500:
                errors.append(
                    f"{path}: {item_label} must be concise (at most 500 characters)"
                )
            if (
                SENSITIVE_ASSIGNMENT_RE.search(item)
                or COMMON_CREDENTIAL_RE.search(item)
                or re.search(
                    r"\bBearer\s+[A-Za-z0-9._~-]+", item, re.IGNORECASE
                )
            ):
                errors.append(
                    f"{path}: {item_label} contains sensitive credential-like data"
                )
            if PERSONAL_DATA_RE.search(item):
                errors.append(f"{path}: {item_label} contains personal data")
    return errors


def _evidence_scope_snapshot(entries: list[dict[str, Any]]) -> str:
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_evidence_document(
    document: Any, path: Path = Path("evidence.json")
) -> list[str]:
    """Validate evidence schema v1 shape and risk/lifecycle semantics with stdlib."""
    errors: list[str] = []
    root = _evidence_object(document, EVIDENCE_FIELDS,
                            "evidence", path, errors)
    if root is None:
        return errors

    if type(root.get("schema_version")) is not int or root.get(
        "schema_version"
    ) != EVIDENCE_SCHEMA_VERSION:
        errors.append(
            f"{path}: schema_version must be integer {EVIDENCE_SCHEMA_VERSION}"
        )
    _evidence_string(root.get("change_id"), "change_id", path, errors)

    sources = root.get("authoritative_sources")
    if not isinstance(sources, list):
        errors.append(f"{path}: authoritative_sources must be an array")
    else:
        if not sources:
            errors.append(f"{path}: authoritative_sources must not be empty")
        source_ids: set[str] = set()
        for index, source in enumerate(sources):
            label = f"authoritative_sources[{index}]"
            parsed = _evidence_object(
                source, ("id", "reference"), label, path, errors
            )
            if parsed is None:
                continue
            source_id = parsed.get("id")
            if _evidence_string(source_id, f"{label}.id", path, errors):
                if source_id in source_ids:
                    errors.append(f"{path}: duplicate authoritative source id")
                source_ids.add(source_id)
            _evidence_string(parsed.get("reference"),
                             f"{label}.reference", path, errors)

    lifecycle = _evidence_object(
        root.get("lifecycle"),
        ("status", "transition", "evidence_references"),
        "lifecycle",
        path,
        errors,
    )
    lifecycle_status: Optional[str] = None
    lifecycle_transition: Optional[str] = None
    if lifecycle is not None:
        if _evidence_enum(
            lifecycle.get("status"),
            {"in-progress", "blocked", "complete"},
            "lifecycle.status",
            path,
            errors,
        ):
            lifecycle_status = lifecycle["status"]
        if _evidence_enum(
            lifecycle.get("transition"),
            {"not-requested", "implemented", "verified"},
            "lifecycle.transition",
            path,
            errors,
        ):
            lifecycle_transition = lifecycle["transition"]
        lifecycle_refs = _evidence_string_array(
            lifecycle.get("evidence_references"),
            "lifecycle.evidence_references",
            path,
            errors,
            min_items=1,
        )
        if lifecycle_transition in {"implemented", "verified"} and not lifecycle_refs:
            errors.append(f"{path}: lifecycle transition must cite evidence")
        if lifecycle_status == "complete" and lifecycle_transition == "not-requested":
            errors.append(
                f"{path}: complete lifecycle must record a supported transition")
        if lifecycle_status != "complete" and lifecycle_transition in {
            "implemented",
            "verified",
        }:
            errors.append(
                f"{path}: lifecycle transition requires complete status")

    risk = _evidence_object(
        root.get("risk"), ("level", "rationale"), "risk", path, errors
    )
    risk_level: Optional[str] = None
    if risk is not None:
        if _evidence_enum(
            risk.get("level"), {"low", "medium",
                                "high"}, "risk.level", path, errors
        ):
            risk_level = risk["level"]
        _evidence_string(risk.get("rationale"), "risk.rationale", path, errors)

    contract = _evidence_object(
        root.get("change_contract"),
        (
            "intent",
            "confirmed_why",
            "scope",
            "expected_evidence",
            "agent_roles",
            "review_focus",
        ),
        "change_contract",
        path,
        errors,
    )
    if contract is not None:
        for field in ("intent", "confirmed_why", "scope"):
            _evidence_string(
                contract.get(field), f"change_contract.{field}", path, errors
            )
        for field in ("expected_evidence", "agent_roles", "review_focus"):
            _evidence_string_array(
                contract.get(field),
                f"change_contract.{field}",
                path,
                errors,
                min_items=1,
            )

    repository_scope = root.get("repository_scope")
    repository_ids: set[str] = set()
    if not isinstance(repository_scope, list):
        errors.append(f"{path}: repository_scope must be an array")
    else:
        if not repository_scope:
            errors.append(
                f"{path}: repository_scope must contain at least 1 item")
        for scope_index, scope_value in enumerate(repository_scope):
            scope_label = f"repository_scope[{scope_index}]"
            scope = _evidence_object(
                scope_value,
                EVIDENCE_DEF_FIELDS["repository_scope"],
                scope_label,
                path,
                errors,
            )
            if scope is None:
                continue
            repository_id = scope.get("repository_id")
            if _evidence_string(
                repository_id, f"{scope_label}.repository_id", path, errors
            ):
                if repository_id in repository_ids:
                    errors.append(
                        f"{path}: duplicate repository_id in repository_scope")
                repository_ids.add(repository_id)
            for field in ("base", "head", "committed_range", "snapshot_sha256"):
                _evidence_string(
                    scope.get(field), f"{scope_label}.{field}", path, errors, nullable=True
                )
            for field in ("base", "head"):
                revision = scope.get(field)
                if (
                    isinstance(revision, str)
                    and revision != "not-applicable"
                    and not EVIDENCE_REVISION_RE.fullmatch(revision)
                ):
                    errors.append(
                        f"{path}: {scope_label}.{field} must be an immutable revision or not-applicable"
                    )
            snapshot = scope.get("snapshot_sha256")
            if isinstance(snapshot, str) and not EVIDENCE_SHA256_RE.fullmatch(snapshot):
                errors.append(
                    f"{path}: {scope_label}.snapshot_sha256 is invalid")
            entries = scope.get("uncommitted_entries")
            parsed_entries: list[dict[str, Any]] = []
            if not isinstance(entries, list):
                errors.append(
                    f"{path}: {scope_label}.uncommitted_entries must be an array")
            else:
                entry_keys: set[tuple[str, str]] = set()
                for entry_index, entry in enumerate(entries):
                    label = f"{scope_label}.uncommitted_entries[{entry_index}]"
                    parsed = _evidence_object(
                        entry,
                        EVIDENCE_DEF_FIELDS["uncommitted_entry"],
                        label,
                        path,
                        errors,
                    )
                    if parsed is None:
                        continue
                    parsed_entries.append(parsed)
                    entry_path = parsed.get("path")
                    state = parsed.get("state")
                    _evidence_string(entry_path, f"{label}.path", path, errors)
                    _evidence_enum(
                        state,
                        {"staged", "unstaged", "untracked"},
                        f"{label}.state",
                        path,
                        errors,
                    )
                    digest = parsed.get("sha256")
                    if not isinstance(digest, str) or not EVIDENCE_SHA256_RE.fullmatch(digest):
                        errors.append(f"{path}: {label}.sha256 is invalid")
                    if isinstance(entry_path, str) and isinstance(state, str):
                        key = (entry_path, state)
                        if key in entry_keys:
                            errors.append(
                                f"{path}: duplicate uncommitted scope entry")
                        entry_keys.add(key)
                if parsed_entries != sorted(
                    parsed_entries,
                    key=lambda item: (str(item.get("path")),
                                      str(item.get("state"))),
                ):
                    errors.append(
                        f"{path}: {scope_label}.uncommitted_entries must be deterministically ordered"
                    )
                if (
                    isinstance(snapshot, str)
                    and snapshot != _evidence_scope_snapshot(parsed_entries)
                ):
                    errors.append(
                        f"{path}: {scope_label}.snapshot_sha256 does not match entries"
                    )
            if lifecycle_transition in {"implemented", "verified"}:
                base = scope.get("base")
                head = scope.get("head")
                committed_range = scope.get("committed_range")
                base_fixed = isinstance(base, str) and (
                    base == "not-applicable" or bool(
                        EVIDENCE_REVISION_RE.fullmatch(base))
                )
                head_fixed = isinstance(head, str) and (
                    head == "not-applicable" or bool(
                        EVIDENCE_REVISION_RE.fullmatch(head))
                )
                if not base_fixed:
                    errors.append(
                        f"{path}: implemented/verified scope requires immutable base or not-applicable"
                    )
                if not head_fixed:
                    errors.append(
                        f"{path}: implemented/verified scope requires immutable head or not-applicable"
                    )
                if base == "not-applicable" and head == "not-applicable":
                    expected_range = "not-applicable"
                elif (
                    isinstance(base, str)
                    and isinstance(head, str)
                    and EVIDENCE_REVISION_RE.fullmatch(base)
                    and EVIDENCE_REVISION_RE.fullmatch(head)
                ):
                    expected_range = f"{base}..{head}"
                else:
                    expected_range = None
                if committed_range != expected_range:
                    errors.append(
                        f"{path}: implemented/verified scope requires a fixed committed_range"
                    )
                if not isinstance(snapshot, str) or not EVIDENCE_SHA256_RE.fullmatch(snapshot):
                    errors.append(
                        f"{path}: implemented/verified scope requires snapshot_sha256"
                    )

    coverage = root.get("requirement_coverage")
    coverage_statuses: list[str] = []
    requirement_ids: set[str] = set()
    if not isinstance(coverage, list):
        errors.append(f"{path}: requirement_coverage must be an array")
    else:
        if not coverage:
            errors.append(f"{path}: requirement_coverage must not be empty")
        for index, item in enumerate(coverage):
            label = f"requirement_coverage[{index}]"
            parsed = _evidence_object(
                item,
                EVIDENCE_DEF_FIELDS["coverage"],
                label,
                path,
                errors,
            )
            if parsed is None:
                continue
            requirement_id = parsed.get("requirement_id")
            if _evidence_string(
                requirement_id, f"{label}.requirement_id", path, errors
            ):
                if requirement_id in requirement_ids:
                    errors.append(f"{path}: duplicate requirement coverage id")
                requirement_ids.add(requirement_id)
            linked_repositories = _evidence_string_array(
                parsed.get("repository_ids"),
                f"{label}.repository_ids",
                path,
                errors,
                min_items=1,
            )
            if linked_repositories is not None:
                if len(linked_repositories) != len(set(linked_repositories)):
                    errors.append(
                        f"{path}: {label}.repository_ids must be unique")
                if set(linked_repositories) - repository_ids:
                    errors.append(
                        f"{path}: {label}.repository_ids contains unknown repository")
            status = parsed.get("status")
            if _evidence_enum(
                status,
                {"covered", "partial", "not-covered"},
                f"{label}.status",
                path,
                errors,
            ):
                coverage_statuses.append(status)
            implementation_refs = _evidence_string_array(
                parsed.get("implementation_references"),
                f"{label}.implementation_references",
                path,
                errors,
            )
            evidence_refs = _evidence_string_array(
                parsed.get("evidence_references"),
                f"{label}.evidence_references",
                path,
                errors,
            )
            if status == "covered" and (not implementation_refs or not evidence_refs):
                errors.append(
                    f"{path}: {label} covered status requires implementation and evidence references"
                )

    checks = root.get("checks")
    parsed_checks: list[dict[str, Any]] = []
    if not isinstance(checks, list):
        errors.append(f"{path}: checks must be an array")
    else:
        check_ids: set[str] = set()
        check_fields = EVIDENCE_DEF_FIELDS["check"]
        for index, check in enumerate(checks):
            label = f"checks[{index}]"
            parsed = _evidence_object(check, check_fields, label, path, errors)
            if parsed is None:
                continue
            parsed_checks.append(parsed)
            check_id = parsed.get("id")
            if _evidence_string(check_id, f"{label}.id", path, errors):
                if check_id in check_ids:
                    errors.append(f"{path}: duplicate check id")
                check_ids.add(check_id)
            linked_requirements = _evidence_string_array(
                parsed.get("requirement_ids"),
                f"{label}.requirement_ids",
                path,
                errors,
                min_items=1,
            )
            if linked_requirements is not None:
                if len(linked_requirements) != len(set(linked_requirements)):
                    errors.append(
                        f"{path}: {label}.requirement_ids must be unique")
                if set(linked_requirements) - requirement_ids:
                    errors.append(
                        f"{path}: {label}.requirement_ids contains unknown requirement"
                    )
            linked_repositories = _evidence_string_array(
                parsed.get("repository_ids"),
                f"{label}.repository_ids",
                path,
                errors,
                min_items=1,
            )
            if linked_repositories is not None:
                if len(linked_repositories) != len(set(linked_repositories)):
                    errors.append(
                        f"{path}: {label}.repository_ids must be unique")
                if set(linked_repositories) - repository_ids:
                    errors.append(
                        f"{path}: {label}.repository_ids contains unknown repository")
            _evidence_enum(
                parsed.get(
                    "kind"), EVIDENCE_CHECK_KINDS, f"{label}.kind", path, errors
            )
            if type(parsed.get("required")) is not bool:
                errors.append(f"{path}: {label}.required must be a boolean")
            applicability_ok = _evidence_enum(
                parsed.get("applicability"),
                {"applicable", "not-applicable"},
                f"{label}.applicability",
                path,
                errors,
            )
            status_ok = _evidence_enum(
                parsed.get("status"),
                EVIDENCE_CHECK_STATUSES,
                f"{label}.status",
                path,
                errors,
            )
            _evidence_string(
                parsed.get("not_applicable_reason"),
                f"{label}.not_applicable_reason",
                path,
                errors,
                nullable=True,
            )
            _evidence_string(
                parsed.get("observed_result"),
                f"{label}.observed_result",
                path,
                errors,
                nullable=True,
            )
            evidence_class = parsed.get("evidence_class")
            if evidence_class is not None:
                _evidence_enum(
                    evidence_class,
                    set(REVIEW_EVIDENCE_CLASSES),
                    f"{label}.evidence_class",
                    path,
                    errors,
                )
            _evidence_string(
                parsed.get("output_reference"),
                f"{label}.output_reference",
                path,
                errors,
                nullable=True,
            )
            applicability = parsed.get(
                "applicability") if applicability_ok else None
            status = parsed.get("status") if status_ok else None
            if applicability == "not-applicable":
                if not isinstance(parsed.get("not_applicable_reason"), str) or not parsed[
                    "not_applicable_reason"
                ].strip():
                    errors.append(
                        f"{path}: {label}.not_applicable_reason is required"
                    )
                if status != "not-applicable":
                    errors.append(
                        f"{path}: {label} not-applicable check has invalid status")
                if parsed.get("required") is True:
                    errors.append(
                        f"{path}: {label} not-applicable check cannot be required")
                for field in ("observed_result", "evidence_class", "output_reference"):
                    if parsed.get(field) is not None:
                        errors.append(f"{path}: {label}.{field} must be null")
            elif applicability == "applicable":
                if parsed.get("not_applicable_reason") is not None:
                    errors.append(
                        f"{path}: {label}.not_applicable_reason must be null when applicable"
                    )
                if status == "not-applicable":
                    errors.append(
                        f"{path}: {label} applicable check has invalid status")
            if status in {"passed", "failed"}:
                if not isinstance(parsed.get("observed_result"), str) or not parsed[
                    "observed_result"
                ].strip():
                    errors.append(
                        f"{path}: {label} executed status needs observed_result")
                if evidence_class != "observed evidence":
                    errors.append(
                        f"{path}: {label} executed status needs observed evidence"
                    )
            if status in {"skipped", "not-run"}:
                for field in ("observed_result", "evidence_class", "output_reference"):
                    if parsed.get(field) is not None:
                        errors.append(f"{path}: {label}.{field} must be null")

    review = _evidence_object(
        root.get("review"),
        EVIDENCE_DEF_FIELDS["review"],
        "review",
        path,
        errors,
    )
    independence: Optional[str] = None
    verdict: Optional[str] = None
    review_reference: Optional[str] = None
    reviewer_id: Optional[str] = None
    implementers: list[str] = []
    prior_participation: list[str] = []
    fresh_context: Optional[bool] = None
    independence_basis: Optional[str] = None
    if review is not None:
        for field in ("reviewer_role", "reviewer_id", "independence_basis"):
            _evidence_string(
                review.get(field), f"review.{field}", path, errors, nullable=True
            )
        if isinstance(review.get("reviewer_id"), str):
            reviewer_id = review["reviewer_id"]
        if isinstance(review.get("independence_basis"), str):
            independence_basis = review["independence_basis"]
        parsed_implementers = _evidence_string_array(
            review.get("implementers"),
            "review.implementers",
            path,
            errors,
            min_items=1,
        )
        if parsed_implementers is not None:
            implementers = parsed_implementers
            if len(implementers) != len(set(implementers)):
                errors.append(f"{path}: review.implementers must be unique")
        participation = review.get("prior_participation")
        allowed_participation = {
            "implementation", "planning", "validation", "review", "other"
        }
        if not isinstance(participation, list):
            errors.append(
                f"{path}: review.prior_participation must be an array")
        else:
            if len(participation) != len(
                set(item for item in participation if isinstance(item, str))
            ):
                errors.append(
                    f"{path}: review.prior_participation must be unique")
            for index, item in enumerate(participation):
                if _evidence_enum(
                    item,
                    allowed_participation,
                    f"review.prior_participation[{index}]",
                    path,
                    errors,
                ):
                    prior_participation.append(item)
        if type(review.get("fresh_context")) is not bool:
            errors.append(f"{path}: review.fresh_context must be a boolean")
        else:
            fresh_context = review["fresh_context"]
        if _evidence_enum(
            review.get("independence"),
            {"self-review", "independent", "not-reviewed"},
            "review.independence",
            path,
            errors,
        ):
            independence = review["independence"]
        if _evidence_enum(
            review.get("verdict"),
            {"approved", "changes-required", "blocked", "not-reviewed"},
            "review.verdict",
            path,
            errors,
        ):
            verdict = review["verdict"]
        if _evidence_string(
            review.get("reference"), "review.reference", path, errors, nullable=True
        ):
            review_reference = review.get("reference")
        if (independence == "not-reviewed") != (verdict == "not-reviewed"):
            errors.append(f"{path}: review not-reviewed fields must agree")
        if independence == "not-reviewed":
            for field in ("reviewer_role", "reviewer_id", "independence_basis"):
                if review.get(field) is not None:
                    errors.append(
                        f"{path}: review.{field} must be null before review")
            if fresh_context is not False:
                errors.append(
                    f"{path}: review.fresh_context must be false before review")
        else:
            for field in ("reviewer_role", "reviewer_id", "independence_basis"):
                if not isinstance(review.get(field), str) or not review[field].strip():
                    errors.append(
                        f"{path}: completed review requires review.{field}")
            if review_reference != "review.md":
                errors.append(
                    f"{path}: completed review must reference review.md")
            if independence == "self-review":
                if reviewer_id not in implementers:
                    errors.append(
                        f"{path}: self-review reviewer_id must match a declared implementer"
                    )
                if "implementation" not in prior_participation:
                    errors.append(
                        f"{path}: self-review prior_participation must include implementation"
                    )
            if independence == "independent":
                if fresh_context is not True:
                    errors.append(
                        f"{path}: independent review requires fresh_context true"
                    )
                if "implementation" in prior_participation:
                    errors.append(
                        f"{path}: independent review prior_participation must exclude implementation"
                    )
                if reviewer_id in implementers:
                    errors.append(
                        f"{path}: independent reviewer_id must not match a declared implementer"
                    )
                if not isinstance(independence_basis, str) or not independence_basis.strip():
                    errors.append(
                        f"{path}: independent review requires non-empty independence_basis"
                    )

    known_limits = root.get("known_limits")
    if known_limits != "not-tracked":
        _evidence_string_array(known_limits, "known_limits", path, errors)
    _evidence_string_array(root.get("remaining_risks"),
                           "remaining_risks", path, errors)
    _evidence_string_array(root.get("follow_ups"), "follow_ups", path, errors)

    errors.extend(_inspect_evidence_safety(root, "evidence", path))

    failed_required = [
        check
        for check in parsed_checks
        if check.get("required") is True
        and check.get("applicability") == "applicable"
        and check.get("status") != "passed"
    ]
    if verdict == "approved" and lifecycle_status != "complete":
        errors.append(f"{path}: approved verdict requires lifecycle complete")
    if verdict == "approved" and failed_required:
        errors.append(
            f"{path}: approved verdict requires all applicable required checks to pass"
        )

    if lifecycle_status == "complete" or verdict == "approved":
        if any(status != "covered" for status in coverage_statuses) or not coverage_statuses:
            errors.append(
                f"{path}: complete evidence requires covered requirements")
        if failed_required:
            errors.append(
                f"{path}: complete evidence has failed, skipped, or unrun required checks"
            )

        def required_passed(kind: str) -> bool:
            return any(
                check.get("kind") == kind
                and check.get("required") is True
                and check.get("applicability") == "applicable"
                and check.get("status") == "passed"
                for check in parsed_checks
            )

        def explicit_risk_kind(kind: str) -> bool:
            matching = [
                check for check in parsed_checks if check.get("kind") == kind]
            if not matching:
                return False
            return all(
                (
                    check.get("applicability") == "not-applicable"
                    and isinstance(check.get("not_applicable_reason"), str)
                    and bool(check["not_applicable_reason"].strip())
                )
                or (
                    check.get("applicability") == "applicable"
                    and check.get("required") is True
                    and check.get("status") == "passed"
                )
                for check in matching
            )

        if not required_passed("scoped"):
            errors.append(
                f"{path}: complete evidence requires a passed required scoped check")
        if risk_level in {"medium", "high"}:
            if not required_passed("regression"):
                errors.append(
                    f"{path}: complete medium/high evidence requires regression checks"
                )
            if not explicit_risk_kind("failure-path"):
                errors.append(
                    f"{path}: complete medium/high evidence requires explicit failure-path applicability"
                )
        if risk_level == "high" and not explicit_risk_kind("recovery-rollback"):
            errors.append(
                f"{path}: complete high-risk evidence requires recovery-rollback applicability"
            )
        if verdict != "approved":
            errors.append(
                f"{path}: complete evidence requires an approved review")
        if risk_level == "low" and independence != "self-review":
            errors.append(
                f"{path}: complete low-risk evidence requires self-review")
        if risk_level == "high":
            if independence != "independent":
                errors.append(
                    f"{path}: complete high-risk evidence requires independent review"
                )
            if fresh_context is not True:
                errors.append(
                    f"{path}: complete high-risk independent review requires fresh_context true"
                )
            if "implementation" in prior_participation:
                errors.append(
                    f"{path}: complete high-risk review prior_participation must exclude implementation"
                )
            if reviewer_id is None or reviewer_id in implementers:
                errors.append(
                    f"{path}: complete high-risk reviewer_id must differ from declared implementers"
                )
            if not isinstance(independence_basis, str) or not independence_basis.strip():
                errors.append(
                    f"{path}: complete high-risk review requires independence_basis"
                )
        if lifecycle_transition == "verified" and verdict != "approved":
            errors.append(
                f"{path}: verified transition requires approved review evidence")
    return errors


def _load_json_asset(path: Path) -> tuple[Optional[Any], list[str]]:
    try:
        return (
            json.loads(path.read_text(encoding="utf-8"),
                       object_pairs_hook=_unique_json_object),
            [],
        )
    except DuplicateJSONObjectKey:
        return None, [f"{path}: duplicate JSON object key"]
    except (json.JSONDecodeError, RecursionError, OSError, UnicodeError) as exc:
        return None, [f"{path}: cannot read valid JSON: {exc}"]


def _validate_contractual_schema_object(
    value: Any, fields: tuple[str, ...], label: str, schema_path: Path
) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return [f"{schema_path}: {label} must be an object schema"]
    if value.get("type") != "object" or value.get("additionalProperties") is not False:
        errors.append(f"{schema_path}: {label} must be a closed object schema")
    if value.get("required") != list(fields):
        errors.append(
            f"{schema_path}: {label} required fields must match evidence schema v1"
        )
    properties = value.get("properties")
    if not isinstance(properties, dict) or set(properties) != set(fields):
        errors.append(
            f"{schema_path}: {label} properties must match evidence schema v1"
        )
    return errors


def validate_evidence_module(module_dir: Path) -> list[str]:
    errors: list[str] = []
    module_file = module_dir / "MODULE.md"
    schema_path = module_dir / "assets" / "evidence.schema.json"
    template_path = module_dir / "assets" / "evidence.template.json"
    for required in (module_file, schema_path, template_path):
        if not required.is_file():
            errors.append(
                f"Missing required evidence module asset: {required}")
    if errors:
        return errors

    schema, schema_errors = _load_json_asset(schema_path)
    errors.extend(schema_errors)
    if isinstance(schema, dict):
        errors.extend(
            _validate_contractual_schema_object(
                schema, EVIDENCE_FIELDS, "root", schema_path
            )
        )
        definitions = schema.get("$defs")
        if not isinstance(definitions, dict):
            errors.append(f"{schema_path}: $defs must be an object")
        else:
            for name, fields in EVIDENCE_DEF_FIELDS.items():
                errors.extend(
                    _validate_contractual_schema_object(
                        definitions.get(
                            name), fields, f"$defs.{name}", schema_path
                    )
                )
    elif not schema_errors:
        errors.append(f"{schema_path}: schema root must be an object")

    template, template_errors = _load_json_asset(template_path)
    errors.extend(template_errors)
    if template is not None:
        errors.extend(validate_evidence_document(template, template_path))
    return errors


def validate_optional_evidence_module(modules_root: Path) -> list[str]:
    module_dir = modules_root / "evidence"
    if not module_dir.exists():
        return []
    return validate_evidence_module(module_dir)


def validate_compliance_event(
    event: Any, path: Path = Path("audit-event.template.json")
) -> list[str]:
    """Validate one closed compliance event without external packages."""
    errors: list[str] = []
    parsed = _evidence_object(
        event, COMPLIANCE_EVENT_FIELDS, "audit event", path, errors
    )
    if parsed is None:
        return errors
    if tuple(parsed) != COMPLIANCE_EVENT_FIELDS:
        errors.append(f"{path}: audit event fields must use canonical order")
    if type(parsed.get("schema_version")) is not int or parsed.get("schema_version") != 1:
        errors.append(f"{path}: schema_version must be integer 1")
    for field in ("event_id", "change_id", "action"):
        _evidence_string(parsed.get(field), field, path, errors)
    action = parsed.get("action")
    if isinstance(action, str) and not NAME_RE.fullmatch(action):
        errors.append(f"{path}: action must be kebab-case")
    if type(parsed.get("sequence")) is not int or parsed.get("sequence", 0) < 1:
        errors.append(f"{path}: sequence must be a positive integer")
    timestamp = parsed.get("timestamp")
    if not isinstance(timestamp, str) or not COMPLIANCE_TIMESTAMP_RE.fullmatch(timestamp):
        errors.append(
            f"{path}: timestamp must be RFC3339 UTC with whole seconds")
    actor = _evidence_object(
        parsed.get(
            "actor"), COMPLIANCE_EVENT_DEF_FIELDS["actor"], "actor", path, errors
    )
    if actor is not None:
        if tuple(actor) != COMPLIANCE_EVENT_DEF_FIELDS["actor"]:
            errors.append(f"{path}: actor fields must use canonical order")
        for field in COMPLIANCE_EVENT_DEF_FIELDS["actor"]:
            _evidence_string(actor.get(field), f"actor.{field}", path, errors)
    previous = parsed.get("previous_lifecycle")
    new = parsed.get("new_lifecycle")
    states = {"draft", "approved", "planned", "implemented", "verified"}
    if action == "lifecycle-transition":
        _evidence_enum(previous, states, "previous_lifecycle", path, errors)
        _evidence_enum(new, states, "new_lifecycle", path, errors)
    elif previous is not None or new is not None:
        errors.append(
            f"{path}: lifecycle fields must be null unless action is lifecycle-transition"
        )
    for field in ("authoritative_source_references", "evidence_references"):
        references = _evidence_string_array(
            parsed.get(field), field, path, errors, min_items=1
        )
        if references is not None:
            if len(references) != len(set(references)):
                errors.append(f"{path}: {field} must be unique")
            if references != sorted(references):
                errors.append(
                    f"{path}: {field} must be deterministically ordered")
    approvals = parsed.get("approvals")
    if not isinstance(approvals, list):
        errors.append(f"{path}: approvals must be an array")
    else:
        approval_keys: list[tuple[str, str]] = []
        for index, approval in enumerate(approvals):
            label = f"approvals[{index}]"
            item = _evidence_object(
                approval, COMPLIANCE_EVENT_DEF_FIELDS["approval"], label, path, errors
            )
            if item is None:
                continue
            if tuple(item) != COMPLIANCE_EVENT_DEF_FIELDS["approval"]:
                errors.append(
                    f"{path}: {label} fields must use canonical order")
            for field in COMPLIANCE_EVENT_DEF_FIELDS["approval"]:
                _evidence_string(
                    item.get(field), f"{label}.{field}", path, errors)
            approval_keys.append(
                (str(item.get("role")), str(item.get("actor_id"))))
        if len(approval_keys) != len(set(approval_keys)):
            errors.append(
                f"{path}: approvals must be unique by role and actor_id")
        if approval_keys != sorted(approval_keys):
            errors.append(
                f"{path}: approvals must be deterministically ordered")
    repositories = parsed.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        errors.append(f"{path}: repositories must be a non-empty array")
    else:
        repository_ids: list[str] = []
        for index, repository in enumerate(repositories):
            label = f"repositories[{index}]"
            item = _evidence_object(
                repository,
                COMPLIANCE_EVENT_DEF_FIELDS["repository"],
                label,
                path,
                errors,
            )
            if item is None:
                continue
            if tuple(item) != COMPLIANCE_EVENT_DEF_FIELDS["repository"]:
                errors.append(
                    f"{path}: {label} fields must use canonical order")
            repository_id = item.get("repository_id")
            revision = item.get("revision")
            _evidence_string(
                repository_id, f"{label}.repository_id", path, errors)
            if not isinstance(revision, str) or not EVIDENCE_REVISION_RE.fullmatch(revision):
                errors.append(f"{path}: {label}.revision must be immutable")
            repository_ids.append(str(repository_id))
        if len(repository_ids) != len(set(repository_ids)):
            errors.append(f"{path}: repository IDs must be unique")
        if repository_ids != sorted(repository_ids):
            errors.append(
                f"{path}: repositories must be deterministically ordered")
    errors.extend(_inspect_evidence_safety(parsed, "audit event", path))
    return errors


def _schema_subset_accepts(
    value: Any, schema: Any, root: dict[str, Any], depth: int = 0
) -> bool:
    """Evaluate the JSON Schema subset used by bundled compliance assets."""
    if depth > 120 or not isinstance(schema, dict):
        return False
    reference = schema.get("$ref")
    if isinstance(reference, str):
        if not reference.startswith("#/"):
            return False
        target: Any = root
        for part in reference[2:].split("/"):
            if not isinstance(target, dict) or part not in target:
                return False
            target = target[part]
        return _schema_subset_accepts(value, target, root, depth + 1)
    if "const" in schema and value != schema["const"]:
        return False
    if "enum" in schema:
        allowed = schema["enum"]
        if not isinstance(allowed, list) or value not in allowed:
            return False
    expected_type = schema.get("type")
    type_matches = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "boolean": type(value) is bool,
        "integer": type(value) is int,
        "null": value is None,
    }
    if isinstance(expected_type, str) and not type_matches.get(expected_type, False):
        return False
    if isinstance(expected_type, list) and not any(
        type_matches.get(item, False) for item in expected_type
    ):
        return False
    if "oneOf" in schema:
        alternatives = schema["oneOf"]
        if not isinstance(alternatives, list) or sum(
            _schema_subset_accepts(value, item, root, depth + 1)
            for item in alternatives
        ) != 1:
            return False
    if "allOf" in schema:
        conjunction = schema["allOf"]
        if not isinstance(conjunction, list):
            return False
        for item in conjunction:
            if not isinstance(item, dict):
                return False
            condition = item.get("if")
            if condition is None:
                if not _schema_subset_accepts(value, item, root, depth + 1):
                    return False
            elif _schema_subset_accepts(value, condition, root, depth + 1):
                if "then" in item and not _schema_subset_accepts(
                    value, item["then"], root, depth + 1
                ):
                    return False
            elif "else" in item and not _schema_subset_accepts(
                value, item["else"], root, depth + 1
            ):
                return False
    if isinstance(value, dict):
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        if not isinstance(required, list) or any(field not in value for field in required):
            return False
        if not isinstance(properties, dict):
            return False
        if schema.get("additionalProperties") is False and set(value) - set(properties):
            return False
        for key, child in value.items():
            if key in properties and not _schema_subset_accepts(
                child, properties[key], root, depth + 1
            ):
                return False
    if isinstance(value, list):
        minimum = schema.get("minItems")
        if type(minimum) is int and len(value) < minimum:
            return False
        if schema.get("uniqueItems") is True:
            rendered = [
                json.dumps(item, sort_keys=True, separators=(",", ":"))
                for item in value
            ]
            if len(rendered) != len(set(rendered)):
                return False
        items = schema.get("items")
        if items is not None and any(
            not _schema_subset_accepts(item, items, root, depth + 1)
            for item in value
        ):
            return False
    if isinstance(value, str):
        if type(schema.get("minLength")) is int and len(value) < schema["minLength"]:
            return False
        if type(schema.get("maxLength")) is int and len(value) > schema["maxLength"]:
            return False
        pattern = schema.get("pattern")
        if isinstance(pattern, str):
            try:
                if not re.search(pattern, value):
                    return False
            except re.error:
                return False
    if type(value) is int:
        if type(schema.get("minimum")) is int and value < schema["minimum"]:
            return False
        if type(schema.get("maximum")) is int and value > schema["maximum"]:
            return False
    return True


def _compliance_schema_contract_errors(
    event_schema: dict[str, Any], policy_schema: dict[str, Any]
) -> list[str]:
    errors: list[str] = []

    def child(value: Any, key: str) -> dict[str, Any]:
        candidate = value.get(key) if isinstance(value, dict) else None
        return candidate if isinstance(candidate, dict) else {}

    event_properties = child(event_schema, "properties")
    event_definitions = child(event_schema, "$defs")
    expected_event_refs = {
        "actor": "#/$defs/actor",
        "previous_lifecycle": "#/$defs/nullable_lifecycle",
        "new_lifecycle": "#/$defs/nullable_lifecycle",
    }
    if event_schema.get("$id") != "urn:agentic-sdlc-kit:compliance-audit-event:v1":
        errors.append("audit schema version identifier must be v1")
    if child(event_properties, "schema_version").get("const") != 1:
        errors.append("audit schema schema_version const must be 1")
    for field, reference in expected_event_refs.items():
        if child(event_properties, field).get("$ref") != reference:
            errors.append(f"audit schema {field} must reference {reference}")
    for field in ("authoritative_source_references", "evidence_references"):
        if child(child(event_properties, field), "items").get("$ref") != "#/$defs/non_empty_string":
            errors.append(
                f"audit schema {field} must reference #/$defs/non_empty_string"
            )
    if child(child(event_properties, "approvals"), "items").get("$ref") != "#/$defs/approval":
        errors.append("audit schema approvals must reference #/$defs/approval")
    if child(child(event_properties, "repositories"), "items").get("$ref") != "#/$defs/repository":
        errors.append(
            "audit schema repositories must reference #/$defs/repository")
    if child(event_properties, "timestamp").get("pattern") != COMPLIANCE_TIMESTAMP_RE.pattern:
        errors.append(
            "audit schema timestamp pattern must match RFC3339 UTC contract")
    if child(event_properties, "action").get("pattern") != NAME_RE.pattern:
        errors.append(
            "audit schema action pattern must match kebab-case contract")
    event_string = child(event_definitions, "non_empty_string")
    if event_string.get("pattern") != r"^[^\u0000-\u001F\u007F]+$":
        errors.append(
            "audit schema string pattern must exclude control characters")
    lifecycle = child(event_definitions, "lifecycle")
    if lifecycle.get("enum") != ["draft", "approved", "planned", "implemented", "verified"]:
        errors.append(
            "audit schema lifecycle enum must match the specification states")
    for name, fields in COMPLIANCE_EVENT_DEF_FIELDS.items():
        properties = child(child(event_definitions, name), "properties")
        for field in fields:
            field_schema = child(properties, field)
            expected_reference = "#/$defs/non_empty_string"
            if name == "repository" and field == "revision":
                if field_schema.get("pattern") != EVIDENCE_REVISION_RE.pattern:
                    errors.append(
                        "audit schema repository revision pattern must be immutable")
            elif field_schema.get("$ref") != expected_reference:
                errors.append(
                    f"audit schema {name}.{field} must reference {expected_reference}"
                )

    policy_properties = child(policy_schema, "properties")
    policy_definitions = child(policy_schema, "$defs")
    if policy_schema.get("$id") != "urn:agentic-sdlc-kit:approval-policy:v1":
        errors.append("approval policy schema version identifier must be v1")
    policy_string = child(policy_definitions, "non_empty_string")
    if policy_string.get("pattern") != r"^[^\u0000-\u001F\u007F]+$":
        errors.append(
            "approval policy string pattern must exclude control characters")
    if child(child(policy_properties, "rules"), "items").get("$ref") != "#/$defs/rule":
        errors.append("approval policy rules must reference #/$defs/rule")
    rule_properties = child(child(policy_definitions, "rule"), "properties")
    if child(rule_properties, "risk").get("enum") != ["low", "medium", "high"]:
        errors.append("approval policy risk enum must be low, medium, high")
    if child(rule_properties, "action").get("pattern") != NAME_RE.pattern:
        errors.append(
            "approval policy action pattern must match kebab-case contract")
    if child(child(rule_properties, "required_roles"), "items").get("$ref") != "#/$defs/role_requirement":
        errors.append(
            "approval policy required_roles must reference role_requirement")
    role_properties = child(
        child(policy_definitions, "role_requirement"), "properties"
    )
    if child(role_properties, "role").get("$ref") != "#/$defs/non_empty_string":
        errors.append("approval policy role must reference non_empty_string")
    minimum = child(role_properties, "minimum")
    if minimum.get("minimum") != 1 or minimum.get("maximum") != 100:
        errors.append("approval policy minimum bounds must be 1 through 100")
    return errors


def validate_compliance_module(module_dir: Path) -> list[str]:
    """Validate compliance assets recursively and reject assurance overclaims."""
    errors: list[str] = []
    assets = module_dir / "assets"
    expected_assets = {
        "audit-event.schema.json",
        "audit-event.template.json",
        "approval-policy.schema.json",
        "approval-policy.template.json",
    }
    required = [module_dir / "MODULE.md"] + [
        assets / name for name in sorted(expected_assets)
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"Missing required compliance module asset: {path}")
    if errors:
        return errors
    try:
        found_assets = {path.name for path in assets.iterdir()
                        if path.is_file()}
    except OSError as exc:
        return [f"{assets}: cannot inspect compliance assets: {exc}"]
    if found_assets != expected_assets:
        errors.append(
            f"{assets}: compliance assets must match the closed asset set")

    event_schema_path = assets / "audit-event.schema.json"
    event_schema, schema_errors = _load_json_asset(event_schema_path)
    errors.extend(schema_errors)
    if isinstance(event_schema, dict):
        errors.extend(
            _validate_contractual_schema_object(
                event_schema, COMPLIANCE_EVENT_FIELDS, "root", event_schema_path
            )
        )
        definitions = event_schema.get("$defs")
        if not isinstance(definitions, dict):
            errors.append(f"{event_schema_path}: $defs must be an object")
        else:
            for name, fields in COMPLIANCE_EVENT_DEF_FIELDS.items():
                errors.extend(
                    _validate_contractual_schema_object(
                        definitions.get(
                            name), fields, f"$defs.{name}", event_schema_path
                    )
                )
    elif not schema_errors:
        errors.append(f"{event_schema_path}: schema root must be an object")

    event, event_errors = _load_json_asset(
        assets / "audit-event.template.json")
    errors.extend(event_errors)
    if event is not None:
        errors.extend(validate_compliance_event(
            event, assets / "audit-event.template.json"))

    policy_schema_path = assets / "approval-policy.schema.json"
    policy_schema, policy_schema_errors = _load_json_asset(policy_schema_path)
    errors.extend(policy_schema_errors)
    if not isinstance(policy_schema, dict):
        if not policy_schema_errors:
            errors.append(
                f"{policy_schema_path}: schema root must be an object")
    elif (
        policy_schema.get("type") != "object"
        or policy_schema.get("additionalProperties") is not False
        or policy_schema.get("required") != ["rules"]
        or set(policy_schema.get("properties", {})) != {"rules"}
    ):
        errors.append(
            f"{policy_schema_path}: approval policy schema must be closed")
    else:
        policy_definitions = policy_schema.get("$defs")
        if not isinstance(policy_definitions, dict):
            errors.append(f"{policy_schema_path}: $defs must be an object")
        else:
            for name, fields in {
                "rule": ("risk", "action", "required_roles", "independent"),
                "role_requirement": ("role", "minimum"),
            }.items():
                errors.extend(
                    _validate_contractual_schema_object(
                        policy_definitions.get(name), fields,
                        f"$defs.{name}", policy_schema_path,
                    )
                )

    policy, policy_errors = _load_json_asset(
        assets / "approval-policy.template.json")
    errors.extend(policy_errors)
    if policy is not None:
        errors.extend(validate_approval_policy(
            policy, assets / "approval-policy.template.json"))

    if isinstance(event_schema, dict) and isinstance(policy_schema, dict):
        for detail in _compliance_schema_contract_errors(
            event_schema, policy_schema
        ):
            contract_path = (
                policy_schema_path if detail.startswith("approval policy")
                else event_schema_path
            )
            errors.append(
                f"{contract_path}: schema/template compatibility: {detail}"
            )
    if event is not None and isinstance(event_schema, dict) and not _schema_subset_accepts(
        event, event_schema, event_schema
    ):
        errors.append(
            f"{event_schema_path}: schema/template compatibility: "
            "audit template is rejected by its schema"
        )
    if policy is not None and isinstance(policy_schema, dict) and not _schema_subset_accepts(
        policy, policy_schema, policy_schema
    ):
        errors.append(
            f"{policy_schema_path}: schema/template compatibility: "
            "approval policy template is rejected by its schema"
        )

    module_text = (module_dir / "MODULE.md").read_text(encoding="utf-8")
    for required_text in (
        "installed", "enabled_modules", "recognized `.agents/project.json`",
        "audit.jsonl", "append-only by workflow convention", "ordinary editable files",
        "no cryptographic chain", "legal certification", "compliance guarantee",
        "declarations only", "Do not run Git", "no network",
    ):
        if required_text not in module_text:
            errors.append(
                f"{module_dir / 'MODULE.md'}: missing contract text: {required_text}"
            )
    checker = module_dir.parent / "enforcement" / "check.py"
    try:
        checker_source = checker.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(
            f"{checker}: cannot inspect compliance integration: {exc}")
    else:
        if 'EXTENSION_VALIDATORS["compliance"]' not in checker_source:
            errors.append(
                f"{checker}: missing compliance extension registration")

    overclaims = (
        "guarantees compliance", "provides legal certification",
        "tamper-proof audit log", "authenticated identities are verified",
    )
    for path in sorted(module_dir.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(
                f"{path}: cannot recursively inspect compliance asset: {exc}")
            continue
        lowered = text.lower()
        if any(claim in lowered for claim in overclaims):
            errors.append(
                f"{path}: compliance asset contains an assurance overclaim")
        if COMMON_CREDENTIAL_RE.search(text) or PERSONAL_DATA_RE.search(text):
            errors.append(
                f"{path}: compliance asset contains sensitive example data")
    return errors


def validate_optional_compliance_module(modules_root: Path) -> list[str]:
    module_dir = modules_root / "compliance"
    if not module_dir.exists():
        return []
    return validate_compliance_module(module_dir)


def validate_enforcement_module(module_dir: Path) -> list[str]:
    """Validate the portable enforcement module and checker boundary."""
    errors: list[str] = []
    module_path = module_dir / "MODULE.md"
    check_path = module_dir / "check.py"
    lib_dir = module_dir / "lib"
    required = (module_path, check_path, lib_dir)
    for required_path in required:
        if not required_path.exists():
            errors.append(
                f"Missing required enforcement module file: {required_path}")
    errors.extend(
        f"Missing required enforcement library file: {lib_dir / name}"
        for name in ("__init__.py", "artifacts.py", "compliance.py", "evidence.py",
                     "paths.py", "project.py", "report.py")
        if not (lib_dir / name).is_file()
    )
    if errors:
        return errors
    try:
        source = check_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(check_path))
        lib_dir = module_dir / "lib"
        lib_trees = [
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for path in sorted(lib_dir.glob("*.py"))
        ] if lib_dir.is_dir() else []
        all_nodes = [node for current in [tree, *lib_trees]
                     for node in ast.walk(current)]
    except (OSError, UnicodeError, SyntaxError) as exc:
        return [f"{check_path}: cannot parse checker source: {exc}"]

    allowed_imports = {
        "__future__", "datetime", "hashlib", "json", "os", "re", "stat", "sys",
        "pathlib", "typing", "urllib", "lib",
    }
    declared_lib = {
        "__init__", "artifacts", "compliance", "evidence", "paths",
        "project", "report",
    }
    lib_imports = [
        node for node in all_nodes
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("lib")
    ]
    check_lib_imports = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("lib")
    ]
    for node in lib_imports:
        target = (node.module or "").split(".", 1)[
            1] if "." in (node.module or "") else ""
        if target not in declared_lib:
            errors.append(
                f"{check_path}: checker lib import target is not declared: {node.module}")
        if any(alias.name == "*" for alias in node.names):
            errors.append(
                f"{check_path}: checker wildcard lib import is forbidden: {node.module}")
    first_lib_line = min(
        (node.lineno for node in check_lib_imports), default=None)
    anchored_before_import = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Attribute)
        and isinstance(node.func.value.value, ast.Name)
        and node.func.value.value.id == "sys"
        and node.func.value.attr == "path"
        and node.func.attr == "insert"
        and node.lineno < first_lib_line
        for node in ast.walk(tree)
    ) if first_lib_line is not None else False
    if first_lib_line is None or not anchored_before_import:
        errors.append(
            f"{check_path}: checker lib imports must follow file-relative path anchoring")

    imported: set[str] = set()
    for node in all_nodes:
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
            if any(alias.name.startswith("urllib") for alias in node.names):
                errors.append(
                    f"{check_path}: checker network-capable urllib imports are forbidden")
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                errors.append(
                    f"{check_path}: checker must not use relative imports")
            if node.module:
                imported.add(node.module.split(".")[0])
            if node.module and node.module.startswith("urllib") and (
                node.module != "urllib.parse"
                or any(alias.name not in {"parse_qsl", "urlsplit"} for alias in node.names)
            ):
                errors.append(
                    f"{check_path}: checker network-capable urllib imports are forbidden")
    for name in sorted(imported - allowed_imports):
        errors.append(
            f"{check_path}: checker import is not in the self-contained boundary: {name}"
        )

    literals = {
        node.value for node in all_nodes
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    for required_literal in ("--root", "--format", "human", "json"):
        if required_literal not in literals:
            errors.append(
                f"{check_path}: checker missing CLI contract value: {required_literal}"
            )
    function_names = {
        node.name for node in all_nodes
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    for required_function in ("main", "_run", "_render"):
        if required_function not in function_names:
            errors.append(
                f"{check_path}: checker missing required structure: {required_function}"
            )
    if not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "sys"
        and node.func.attr == "exit"
        for node in all_nodes
    ):
        errors.append(
            f"{check_path}: checker must expose an executable main entrypoint")
    path_mutators = {
        "write_text", "write_bytes", "touch", "mkdir", "unlink", "rmdir",
        "rename", "replace", "chmod", "symlink_to", "hardlink_to",
    }
    os_mutators = {
        "remove", "unlink", "rename", "replace", "system", "rmdir", "removedirs",
        "mkdir", "makedirs", "renames", "chmod", "chown", "truncate", "open",
    }
    dynamic_execution = {"exec", "eval", "compile", "__import__"}
    os_aliases = {"os"}
    bound_os_mutators: set[str] = set()
    for node in all_nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "os":
                    os_aliases.add(alias.asname or "os")
        elif isinstance(node, ast.ImportFrom) and node.module == "os":
            for alias in node.names:
                if alias.name in os_mutators:
                    bound_os_mutators.add(alias.asname or alias.name)

    def open_mode(call: ast.Call, method: bool) -> Optional[str]:
        position = 0 if method else 1
        candidate: Optional[ast.AST] = (
            call.args[position] if len(call.args) > position else None
        )
        for keyword in call.keywords:
            if keyword.arg == "mode":
                candidate = keyword.value
        if candidate is None:
            return "r"
        if isinstance(candidate, ast.Constant) and isinstance(candidate.value, str):
            return candidate.value
        return None

    for node in all_nodes:
        if not isinstance(node, ast.Call):
            continue
        violation: Optional[str] = None
        if isinstance(node.func, ast.Name):
            if node.func.id in dynamic_execution:
                violation = node.func.id
            elif node.func.id in bound_os_mutators:
                violation = node.func.id
            elif node.func.id == "open":
                mode = open_mode(node, False)
                if mode is None or any(flag in mode for flag in "wax+"):
                    violation = "open"
        elif isinstance(node.func, ast.Attribute):
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id in os_aliases
                and node.func.attr in os_mutators
            ):
                violation = f"os.{node.func.attr}"
            elif node.func.attr in path_mutators:
                violation = node.func.attr
            elif node.func.attr == "open":
                mode = open_mode(node, True)
                if mode is None or any(flag in mode for flag in "wax+"):
                    violation = "open"
        if violation:
            errors.append(
                f"{check_path}: checker read-only boundary forbids operation: {violation}"
            )
    return errors


def validate_optional_enforcement_module(modules_root: Path) -> list[str]:
    module_dir = modules_root / "enforcement"
    if not module_dir.exists():
        return []
    return validate_enforcement_module(module_dir)


def validate_multi_repo_module(module_dir: Path) -> list[str]:
    """Validate focused multi-repository assets and read-only checker integration."""
    errors: list[str] = []
    expected_assets = {
        "plan-snippet.md",
        "tasks-snippet.md",
        "review-snippet.md",
        "evidence-snippet.json",
    }
    required = [module_dir / "MODULE.md"] + [
        module_dir / "assets" / name for name in sorted(expected_assets)
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"Missing required multi-repo module asset: {path}")
    if errors:
        return errors
    try:
        found_assets = {path.name for path in (
            module_dir / "assets").iterdir()}
    except OSError as exc:
        return [f"{module_dir}: cannot inspect multi-repo assets: {exc}"]
    if found_assets != expected_assets:
        errors.append(
            f"{module_dir / 'assets'}: multi-repo assets must be focused snippets only"
        )

    module_text = (module_dir / "MODULE.md").read_text(encoding="utf-8")
    for required_text in (
        "installed",
        "enabled_modules",
        "recognized `.agents/project.json`",
        "existing checkouts only",
        "Cross-repo depends on",
        "Dirty status",
        "Ownership/isolation",
        "dirty-status:<value>",
        "ownership-isolation:<value>",
        "never execute Git",
    ):
        if required_text not in module_text:
            errors.append(
                f"{module_dir / 'MODULE.md'}: missing contract text: {required_text}")

    task_asset_path = module_dir / "assets" / "tasks-snippet.md"
    try:
        task_asset = task_asset_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"{task_asset_path}: cannot read task controls: {exc}")
    else:
        for exact_contract in (
            "Dirty status: clean | dirty-nonconflicting | blocked-conflict | unknown",
            "Ownership/isolation: exclusive-owner | isolated | blocked-conflict | unknown",
            "dirty-status:<value>",
            "ownership-isolation:<value>",
        ):
            if exact_contract not in task_asset:
                errors.append(
                    f"{task_asset_path}: missing exact task control contract: {exact_contract}"
                )

    snippet, snippet_errors = _load_json_asset(
        module_dir / "assets" / "evidence-snippet.json"
    )
    errors.extend(snippet_errors)
    if isinstance(snippet, dict):
        if set(snippet) != {
            "repository_scope",
            "requirement_coverage",
            "checks",
        }:
            errors.append(
                f"{module_dir / 'assets' / 'evidence-snippet.json'}: snippet fields are not coherent evidence v1 fields"
            )
        scope = snippet.get("repository_scope")
        if not isinstance(scope, list) or not scope or not isinstance(scope[0], dict):
            errors.append(
                f"{module_dir / 'assets' / 'evidence-snippet.json'}: repository_scope must be a non-empty array"
            )

    checker = module_dir.parent / "enforcement" / "check.py"
    try:
        checker_source = checker.read_text(encoding="utf-8")
        checker_tree = ast.parse(checker_source, filename=str(checker))
        package_trees = [
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for path in sorted((checker.parent / "lib").glob("*.py"))
        ]
        all_checker_nodes = [node for current in [checker_tree, *package_trees]
                             for node in ast.walk(current)]
    except (OSError, UnicodeError, SyntaxError) as exc:
        errors.append(
            f"{checker}: cannot inspect multi-repo checker integration: {exc}")
    else:
        if 'EXTENSION_VALIDATORS["multi-repo"]' not in checker_source:
            errors.append(
                f"{checker}: missing multi-repo extension registration")
        attributes = {
            node.attr for node in all_checker_nodes
            if isinstance(node, ast.Attribute)
        }
        if "lstat" not in attributes:
            errors.append(
                f"{checker}: multi-repo checker must inspect paths with lstat")
        if "resolve" in attributes:
            errors.append(
                f"{checker}: multi-repo checker must not resolve-follow paths")
        for node in all_checker_nodes:
            if isinstance(node, ast.Import):
                if any(alias.name.split(".")[0] in {"git", "subprocess"} for alias in node.names):
                    errors.append(
                        f"{checker}: multi-repo checker must not import Git/process tooling")
            elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in {"git", "subprocess"}:
                errors.append(
                    f"{checker}: multi-repo checker must not import Git/process tooling")
    return errors


def validate_optional_multi_repo_module(modules_root: Path) -> list[str]:
    module_dir = modules_root / "multi-repo"
    if not module_dir.exists():
        return []
    return validate_multi_repo_module(module_dir)


def documented_kit_version(root: Path) -> Optional[str]:
    """Read the public release declaration used to check catalog drift."""
    path = root / "docs" / "usage-guide.md"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    match = re.search(r"source kit release is `(\d+\.\d+\.\d+)`", text)
    return match.group(1) if match else None


def validate_catalog_version(root: Path, data: dict[str, Any]) -> list[str]:
    expected = documented_kit_version(root)
    if expected is None:
        return []
    actual = data.get("kit_version")
    if actual != expected:
        return [
            f"{root / '.agents' / 'kit-catalog.json'}: kit_version {actual!r} "
            f"does not match documented source kit release {expected}"
        ]
    return []


def read_template(path: Path, errors: list[str]) -> Optional[str]:
    if not path.is_file():
        errors.append(f"Missing required template: {path}")
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"Cannot read required template {path}: {exc}")
        return None


def parse_template_frontmatter(text: str, path: Path) -> dict[str, str]:
    """Return top-level keys from a template's initial YAML frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError(f"{path}: missing opening YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError(f"{path}: missing closing YAML frontmatter") from exc

    metadata: dict[str, str] = {}
    current_key: Optional[str] = None
    for line_number, line in enumerate(lines[1:end], 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        is_list_item = line == "-" or line.startswith("- ")
        if line[0].isspace() or is_list_item:
            if current_key != "sources":
                raise ValueError(
                    f"{path}:{line_number}: invalid YAML frontmatter continuation"
                )
            continue
        if ":" not in line:
            raise ValueError(
                f"{path}:{line_number}: invalid YAML frontmatter line: {line}"
            )
        key, value = line.split(":", 1)
        key = key.strip()
        if not key or key in metadata:
            detail = "empty key" if not key else f"duplicate key {key!r}"
            raise ValueError(f"{path}:{line_number}: {detail}")
        metadata[key] = value.strip()
        current_key = key
    return metadata


def markdown_section(text: str, heading: str) -> Optional[str]:
    lines = text.splitlines()
    try:
        start = lines.index(heading) + 1
    except ValueError:
        return None
    end = next(
        (
            index
            for index in range(start, len(lines))
            if lines[index].startswith("## ")
        ),
        len(lines),
    )
    return "\n".join(lines[start:end])


def declared_string_tokens(section: Optional[str], label: str) -> Optional[list[str]]:
    if section is None:
        return None
    prefix = f"{label}:"
    declarations = [
        line.strip()[len(prefix):].strip()
        for line in section.splitlines()
        if line.strip().startswith(prefix)
    ]
    if len(declarations) != 1:
        return None
    try:
        value = json.loads(declarations[0])
    except (json.JSONDecodeError, RecursionError):
        return None
    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        return None
    return value


def validate_review_template(template: str) -> list[str]:
    errors: list[str] = []
    for required in (
        "## Scope",
        "Fixed base:",
        "Fixed head:",
        "Committed range:",
        "Uncommitted scope:",
        "## Reviewer role and independence",
        "Reviewer role:",
        "Implementer(s):",
        "Prior role:",
        "Independence:",
        "Independence basis:",
        "Independence required:",
        "Independence met:",
        "## Authoritative sources",
        "## Risk",
        "Reviewer-assessed risk:",
        "Risk rationale:",
        "## Change contract and review focus",
        "What:",
        "Authoritative why:",
        "Contract scope:",
        "Required evidence:",
        "Contract risk:",
        "Agent roles:",
        "Review focus:",
        "Risk comparison/deviation:",
        "Missing-contract impact:",
        "## Selected quality signals",
        "## Checks and evidence",
        "Evidence classes:",
        "## Findings",
        "Evidence class:",
        "Location:",
        "Impact:",
        "Minimal action:",
        "## Acceptance coverage",
        "## Residual risk",
        "## Verdict",
        "Verdict options:",
    ):
        if required not in template:
            errors.append(f"Review template missing field: {required}")

    signal_section = markdown_section(template, "## Selected quality signals")
    if signal_section is not None:
        table_rows = []
        for line in signal_section.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            table_rows.append(
                [cell.strip() for cell in stripped.strip("|").split("|")]
            )
        header = next(
            (row for row in table_rows if row and row[0] == "Signal"), [])
        if "Disposition" not in header:
            errors.append(
                "Review template signal table missing column: Disposition"
            )
        if not any("N/A reason" in cell for cell in header):
            errors.append(
                "Review template signal table missing column: N/A reason")
        data_rows = [
            row
            for row in table_rows
            if row
            and row[0] != "Signal"
            and not all(re.fullmatch(r":?-{3,}:?", cell) for cell in row)
        ]
        if len(data_rows) != len(REVIEW_SIGNALS):
            errors.append(
                "Review template quality signal table must contain exactly "
                f"{len(REVIEW_SIGNALS)} data rows"
            )
        row_names = [row[0] for row in data_rows]
        for signal in sorted(set(row_names) - set(REVIEW_SIGNALS)):
            errors.append(
                f"Review template unknown quality signal row: {signal}"
            )
        for signal in REVIEW_SIGNALS:
            count = row_names.count(signal)
            if count == 0:
                errors.append(
                    f"Review template missing quality signal row: {signal}")
            elif count > 1:
                errors.append(
                    f"Review template duplicate quality signal row: {signal}"
                )

    checks_section = markdown_section(template, "## Checks and evidence")
    evidence_classes = declared_string_tokens(
        checks_section, "Evidence classes")
    expected_evidence = set(REVIEW_EVIDENCE_CLASSES)
    if (
        evidence_classes is None
        or len(evidence_classes) != len(REVIEW_EVIDENCE_CLASSES)
        or set(evidence_classes) != expected_evidence
    ):
        errors.append(
            "Review template evidence classes must be exactly: "
            + ", ".join(REVIEW_EVIDENCE_CLASSES)
        )
    declared_evidence = set(evidence_classes or [])
    for evidence_class in REVIEW_EVIDENCE_CLASSES:
        if evidence_class not in declared_evidence:
            errors.append(
                f"Review template missing evidence class: {evidence_class}"
            )

    verdict_section = markdown_section(template, "## Verdict")
    verdicts = declared_string_tokens(verdict_section, "Verdict options")
    expected_verdicts = set(REVIEW_VERDICTS)
    if (
        verdicts is None
        or len(verdicts) != len(REVIEW_VERDICTS)
        or set(verdicts) != expected_verdicts
    ):
        errors.append(
            "Review template verdict options must be exactly: "
            + ", ".join(REVIEW_VERDICTS)
        )
    declared_verdicts = set(verdicts or [])
    for verdict in REVIEW_VERDICTS:
        if verdict not in declared_verdicts:
            errors.append(f"Review template missing verdict option: {verdict}")
    return errors


def validate_templates(skills_root: Path) -> list[str]:
    errors: list[str] = []
    spec_template = read_template(
        skills_root / "write-spec" / "assets" / "spec.template.md", errors
    )
    if spec_template is not None:
        spec_path = skills_root / "write-spec" / "assets" / "spec.template.md"
        try:
            spec_metadata = parse_template_frontmatter(
                spec_template, spec_path)
        except ValueError as exc:
            errors.append(str(exc))
        else:
            required_metadata = {
                "id": None,
                "title": None,
                "sources": None,
                "status": "draft",
                "depends_on": "[]",
            }
            for key, expected_value in required_metadata.items():
                label = (
                    f"{key}:"
                    if expected_value is None
                    else f"{key}: {expected_value}"
                )
                if key not in spec_metadata or (
                    expected_value is not None
                    and spec_metadata[key] != expected_value
                ):
                    errors.append(
                        f"Spec template missing metadata field: {label}")
        if "## Confirmed rationale" not in spec_template:
            errors.append(
                "Spec template missing field: ## Confirmed rationale")

    index_template = read_template(
        skills_root / "write-spec" / "assets" / "spec-index.template.md", errors
    )
    if index_template is not None:
        for state in sorted(SPEC_STATES):
            if f"`{state}`" not in index_template:
                errors.append(f"Spec index missing lifecycle state: {state}")

    plan_template = read_template(
        skills_root / "plan" / "assets" / "plan.template.md", errors
    )
    if plan_template is not None:
        for required in (
            "id: PLAN-",
            "sources:",
            "status: draft",
            "risk: low",
            "risk_rationale:",
            "## Repository findings and facts",
            "## Confirmed constraints",
            "## Assumptions",
            "## Agent inferences",
            "## Unknowns",
            "## Confirmed technical decisions and rationale",
            "## Source coverage and impact map",
            "## Verification strategy",
        ):
            if required not in plan_template:
                errors.append(f"Plan template missing field: {required}")

    task_template = read_template(
        skills_root / "decompose-tasks" / "assets" / "tasks.template.md", errors
    )
    if task_template is not None:
        for required in (
            "Plan:",
            "Source items:",
            "Type:",
            "Risk:",
            "Risk rationale:",
            "State:",
            "Depends on:",
            "## Execution controls",
            "Topology:",
            "Topology decision:",
            "Review/integration capacity:",
            "Maximum in-progress:",
            "Review queue:",
            "Blocker:",
            "Execution:",
            "Execution rationale:",
            "Conflicts with:",
            "#### Change contract",
            "What:",
            "Why:",
            "Scope:",
            "Evidence:",
            "Contract risk:",
            "Agent roles:",
            "Review focus:",
            "Acceptance evidence:",
            "Validation commands/procedure:",
            "Result: pending",
        ):
            if required not in task_template:
                errors.append(f"Task template missing field: {required}")

    review_template = read_template(
        skills_root / "review" / "assets" / "review.template.md", errors
    )
    if review_template is not None:
        errors.extend(validate_review_template(review_template))

    setup_template_path = skills_root / "setup" / "assets" / "project.template.json"
    setup_schema_path = skills_root / "setup" / "assets" / "project.schema.json"
    setup_template = read_template(setup_template_path, errors)
    if not setup_schema_path.is_file():
        errors.append(f"Missing required project schema: {setup_schema_path}")
    if setup_template is not None and setup_schema_path.is_file():
        try:
            project_config = parse_project_json(
                setup_template, setup_template_path)
        except ValueError as exc:
            errors.append(str(exc))
        else:
            errors.extend(validate_project_config(
                project_config, setup_template_path, setup_schema_path))

    setup_reference = skills_root / "setup" / "references" / "project-config.md"
    if not setup_reference.is_file():
        errors.append(f"Missing required setup reference: {setup_reference}")

    glossary_template = read_template(
        skills_root / "domain-model" / "assets" / "glossary.template.md", errors
    )
    if glossary_template is not None:
        for required in (
            "# Domain Context",
            "## Terms",
            "Meaning:",
            "Relationships:",
            "Rejected ambiguous synonyms:",
        ):
            if required not in glossary_template:
                errors.append(f"Glossary template missing field: {required}")

    adr_template = read_template(
        skills_root / "domain-model" / "assets" / "adr.template.md", errors
    )
    if adr_template is not None:
        for required in (
            "Status:",
            "Date:",
            "## Context",
            "## Decision",
            "## Alternatives",
            "## Confirmed rationale",
            "## Repository evidence",
            "## Agent inference",
            "## Unknowns",
            "## Consequences",
        ):
            if required not in adr_template:
                errors.append(f"ADR template missing field: {required}")
    return errors


def validate_source_artifact_catalog(root: Path) -> list[str]:
    """Validate catalog pointers and owner boundaries through shared contracts."""
    path = root / ".agents" / "artifact-catalog.json"
    if not path.is_file():
        return []
    try:
        value = artifact_catalog_contract.load_artifact_catalog(root)
        artifact_catalog_contract.resolve_artifact_contracts(root, value)
    except artifact_catalog_contract.CatalogError as exc:
        return [f"{path}: {exc}"]
    return []

#!/usr/bin/env python3
"""Deterministic, dependency-free, read-only Agentic SDLC consistency checker."""

from __future__ import annotations
from lib.paths import _display, _load_json, _safe_existing, _walk_files
from lib.report import Report

import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qsl, urlsplit

SCHEMA_VERSION = 1
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ID_PATTERNS = {
    "spec": re.compile(r"^SPEC-[0-9]+$"),
    "plan": re.compile(r"^PLAN-[0-9]+$"),
    "task": re.compile(r"^TASK-[0-9]+$"),
    "requirement": re.compile(r"^REQ-[0-9]+$"),
}
PROJECT_FIELDS = (
    "schema_version", "roots", "repositories", "enabled_modules", "tracker",
    "agent", "review", "approval_policy", "contribution",
)
ROOT_FIELDS = ("specs", "work", "adrs", "evidence", "domain_context")
ENV_PATH_RE = re.compile(r"^\$\{([A-Z_][A-Z0-9_]*)\}/(.+)$")
TRAILER_RE = re.compile(r"^[A-Za-z0-9-]+$")
EXECUTABLE_CONFIG_KEYS = {
    "command", "commands", "hook", "hooks", "plugin", "plugins", "regex",
    "regexp", "script", "scripts", "executable", "executables",
}
URI_SCHEME_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*):")
SCP_REMOTE_RE = re.compile(
    r"^(?:[A-Za-z0-9._-]+@)?"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*:"
    r"[A-Za-z0-9._~+-]+(?:/[A-Za-z0-9._~+-]+)*$"
)
EVIDENCE_FIELDS = (
    "schema_version", "change_id", "authoritative_sources", "lifecycle", "risk",
    "change_contract", "repository_scope", "requirement_coverage", "checks",
    "review", "known_limits", "remaining_risks", "follow_ups",
)
COMPLIANCE_EVENT_FIELDS = (
    "schema_version", "event_id", "sequence", "timestamp", "change_id", "actor",
    "action", "previous_lifecycle", "new_lifecycle",
    "authoritative_source_references", "evidence_references", "approvals",
    "repositories",
)
COMPLIANCE_NESTED_FIELDS = {
    "actor": ("actor_id", "role"),
    "approval": ("actor_id", "role", "reference"),
    "repository": ("repository_id", "revision"),
}
COMPLIANCE_IMPLEMENTATION_ROLES = {"implementer", "implementation"}
COMPLIANCE_TRANSITIONS = {
    ("draft", "approved"),
    ("approved", "planned"),
    ("approved", "implemented"),
    ("planned", "implemented"),
    ("implemented", "verified"),
}
COMPLIANCE_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
SENSITIVE_QUERY_KEYS = {
    "token", "accesstoken", "authtoken", "refreshtoken", "idtoken", "apikey",
    "secret", "clientsecret", "password", "passwd", "credential", "credentials",
}
SENSITIVE_QUERY_SUFFIXES = (
    "token", "apikey", "secret", "password", "passwd", "credential", "credentials",
)
COMMON_CREDENTIAL_RE = re.compile(
    r"(?:\bghp_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b|"
    r"\bsk-[A-Za-z0-9]{20,}\b|\bBearer\s+[A-Za-z0-9._~-]+)", re.IGNORECASE
)
SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?:api[-_ ]?key|credential|password|secret|token)\s*[:=]", re.IGNORECASE
)
PERSONAL_DATA_RE = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
# Later built-in module checks register here; records never load or execute code.
EXTENSION_VALIDATORS: dict[str, Any] = {}


def _schema_type(value: Any, expected: str) -> bool:
    return {
        "object": isinstance(value, dict), "array": isinstance(value, list),
        "string": isinstance(value, str), "boolean": type(value) is bool,
        "integer": type(value) is int, "null": value is None,
    }.get(expected, False)


def _schema_ok(value: Any, schema: Any, schema_root: dict[str, Any], depth: int = 0) -> bool:
    if depth > 120 or not isinstance(schema, dict):
        return False
    reference = schema.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/"):
        target: Any = schema_root
        for part in reference[2:].split("/"):
            if not isinstance(target, dict) or part not in target:
                return False
            target = target[part]
        return _schema_ok(value, target, schema_root, depth + 1)
    if "const" in schema and value != schema["const"]:
        return False
    if "enum" in schema and value not in schema["enum"]:
        return False
    expected = schema.get("type")
    if isinstance(expected, str) and not _schema_type(value, expected):
        return False
    if isinstance(expected, list) and not any(_schema_type(value, item) for item in expected):
        return False
    if "oneOf" in schema and sum(_schema_ok(value, item, schema_root, depth + 1) for item in schema["oneOf"]) != 1:
        return False
    if "allOf" in schema:
        for item in schema["allOf"]:
            if not isinstance(item, dict):
                return False
            condition = item.get("if")
            if condition is None:
                if not _schema_ok(value, item, schema_root, depth + 1):
                    return False
            elif _schema_ok(value, condition, schema_root, depth + 1):
                if "then" in item and not _schema_ok(value, item["then"], schema_root, depth + 1):
                    return False
            elif "else" in item and not _schema_ok(value, item["else"], schema_root, depth + 1):
                return False
    if "not" in schema and _schema_ok(value, schema["not"], schema_root, depth + 1):
        return False
    if isinstance(value, dict):
        required = schema.get("required", [])
        if not isinstance(required, list) or any(item not in value for item in required):
            return False
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            return False
        if schema.get("additionalProperties") is False and set(value) - set(properties):
            return False
        for key, child in value.items():
            if key in properties and not _schema_ok(child, properties[key], schema_root, depth + 1):
                return False
    if isinstance(value, list):
        minimum = schema.get("minItems")
        if type(minimum) is int and len(value) < minimum:
            return False
        if schema.get("uniqueItems") is True:
            rendered = [json.dumps(item, sort_keys=True,
                                   separators=(",", ":")) for item in value]
            if len(rendered) != len(set(rendered)):
                return False
        items = schema.get("items")
        if items is not None and any(not _schema_ok(item, items, schema_root, depth + 1) for item in value):
            return False
        contains = schema.get("contains")
        if contains is not None and not any(_schema_ok(item, contains, schema_root, depth + 1) for item in value):
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
    return True


def _validate_evidence_document(document: Any, schema: dict[str, Any], relative: str, report: Report) -> None:
    if not _schema_ok(document, schema, schema):
        report.add("EVIDENCE_SCHEMA", relative, "",
                   "Evidence does not conform to the installed schema.")
    if not isinstance(document, dict):
        return
    if set(document) != set(EVIDENCE_FIELDS):
        return
    lifecycle = document.get("lifecycle") if isinstance(
        document.get("lifecycle"), dict) else {}
    risk = document.get("risk") if isinstance(
        document.get("risk"), dict) else {}
    review = document.get("review") if isinstance(
        document.get("review"), dict) else {}
    contract = document.get("change_contract") if isinstance(
        document.get("change_contract"), dict) else {}
    for field in ("expected_evidence", "agent_roles", "review_focus"):
        value = contract.get(field)
        if not isinstance(value, list) or not value:
            report.add("EVIDENCE_CONTRACT_REQUIRED", relative,
                       f"change_contract.{field}",
                       "Change contract arrays must contain at least one item.")
    coverage = document.get("requirement_coverage") if isinstance(
        document.get("requirement_coverage"), list) else []
    checks = [item for item in document.get("checks", []) if isinstance(
        item, dict)] if isinstance(document.get("checks"), list) else []
    status, transition = lifecycle.get("status"), lifecycle.get("transition")
    verdict, independence = review.get("verdict"), review.get("independence")
    risk_level = risk.get("level")
    references = lifecycle.get("evidence_references")
    if not isinstance(references, list) or not references:
        report.add("EVIDENCE_LIFECYCLE", relative, "lifecycle.evidence_references",
                   "Every lifecycle state must cite at least one evidence reference.")
    if status == "complete" and transition == "not-requested":
        report.add("EVIDENCE_LIFECYCLE", relative, "lifecycle.transition",
                   "Complete evidence must record a supported transition.")
    if status != "complete" and transition in {"implemented", "verified"}:
        report.add("EVIDENCE_LIFECYCLE", relative, "lifecycle",
                   "Implemented or verified transition requires complete status.")
    scopes = document.get("repository_scope") if isinstance(
        document.get("repository_scope"), list) else []
    scope_ids: list[str] = []
    for scope_index, scope in enumerate(scopes):
        if not isinstance(scope, dict):
            continue
        scope_field = f"repository_scope[{scope_index}]"
        repository_id = scope.get("repository_id")
        if isinstance(repository_id, str):
            scope_ids.append(repository_id)
        entries = scope.get("uncommitted_entries")
        snapshot = scope.get("snapshot_sha256")
        if isinstance(entries, list):
            canonical = json.dumps(
                entries, sort_keys=True, separators=(",", ":"))
            if isinstance(snapshot, str) and hashlib.sha256(canonical.encode("utf-8")).hexdigest() != snapshot:
                report.add("EVIDENCE_SCOPE_HASH", relative, f"{scope_field}.snapshot_sha256",
                           "Snapshot hash does not match the recorded entries.")
            ordered = sorted(entries, key=lambda item: (str(item.get("path")), str(
                item.get("state"))) if isinstance(item, dict) else ("", ""))
            entry_keys = [(item.get("path"), item.get("state")) for item in entries
                          if isinstance(item, dict)]
            if len(entry_keys) != len(set(entry_keys)):
                report.add("EVIDENCE_SCOPE_DUPLICATE", relative,
                           f"{scope_field}.uncommitted_entries",
                           "Uncommitted scope entries must be unique by path and state.")
            if entries != ordered:
                report.add("EVIDENCE_SCOPE_ORDER", relative, f"{scope_field}.uncommitted_entries",
                           "Uncommitted entries are not deterministically ordered.")
        if transition in {"implemented", "verified"}:
            base, head, committed_range = scope.get("base"), scope.get(
                "head"), scope.get("committed_range")
            revision = re.compile(r"^[0-9a-f]{7,64}$")
            if base == "not-applicable" and head == "not-applicable":
                expected_range: Optional[str] = "not-applicable"
            elif isinstance(base, str) and isinstance(head, str) and revision.fullmatch(base) and revision.fullmatch(head):
                expected_range = f"{base}..{head}"
            else:
                expected_range = None
            if expected_range is None or committed_range != expected_range or not isinstance(snapshot, str) or not re.fullmatch(r"[0-9a-f]{64}", snapshot):
                report.add("EVIDENCE_SCOPE_FIXED", relative, scope_field,
                           "Implemented or verified evidence requires a fixed revision range and snapshot.")
    if len(scope_ids) != len(set(scope_ids)):
        report.add("EVIDENCE_SCOPE_DUPLICATE", relative, "repository_scope",
                   "Repository scope entries must use unique repository IDs.")
    source_ids = [item.get("id") for item in document.get("authoritative_sources", [])
                  if isinstance(item, dict) and isinstance(item.get("id"), str)]
    if len(source_ids) != len(set(source_ids)):
        report.add("EVIDENCE_ID_DUPLICATE", relative, "authoritative_sources",
                   "Authoritative source IDs must be unique.")
    requirement_ids = [item.get("requirement_id") for item in coverage
                       if isinstance(item, dict) and isinstance(item.get("requirement_id"), str)]
    if len(requirement_ids) != len(set(requirement_ids)):
        report.add("EVIDENCE_ID_DUPLICATE", relative, "requirement_coverage",
                   "Requirement coverage IDs must be unique.")
    check_ids = [item.get("id")
                 for item in checks if isinstance(item.get("id"), str)]
    if len(check_ids) != len(set(check_ids)):
        report.add("EVIDENCE_ID_DUPLICATE", relative, "checks",
                   "Check IDs must be unique.")
    known_requirements = set(requirement_ids)
    if any(set(item.get("requirement_ids", [])) - known_requirements
           for item in checks if isinstance(item.get("requirement_ids"), list)):
        report.add("EVIDENCE_REQUIREMENT_REFERENCE", relative, "checks.requirement_ids",
                   "A check references an unknown requirement coverage ID.")
    known_repositories = set(scope_ids)
    linked_repository_records = coverage + checks
    if any(
        isinstance(item, dict)
        and isinstance(item.get("repository_ids"), list)
        and set(item["repository_ids"]) - known_repositories
        for item in linked_repository_records
    ):
        report.add("EVIDENCE_REPOSITORY_REFERENCE", relative, "repository_ids",
                   "Coverage or checks reference an unknown repository scope ID.")
    if any(item.get("status") == "covered" and
           (not item.get("implementation_references")
            or not item.get("evidence_references"))
           for item in coverage if isinstance(item, dict)):
        report.add("EVIDENCE_COVERAGE_REFERENCE", relative, "requirement_coverage",
                   "Covered requirements need implementation and evidence references.")
    if (independence == "not-reviewed") != (verdict == "not-reviewed"):
        report.add("EVIDENCE_REVIEW_STATE", relative, "review",
                   "Not-reviewed independence and verdict must agree.")
    if independence == "not-reviewed":
        if any(review.get(field) is not None for field in
               ("reviewer_role", "reviewer_id", "independence_basis")) or review.get("fresh_context") is not False:
            report.add("EVIDENCE_REVIEW_STATE", relative, "review",
                       "Unreviewed evidence must not claim reviewer identity or fresh context.")
    elif independence in {"self-review", "independent"}:
        if review.get("reference") != "review.md" or any(
            not isinstance(review.get(field), str) or not review[field].strip()
            for field in ("reviewer_role", "reviewer_id", "independence_basis")
        ):
            report.add("EVIDENCE_REVIEW_STATE", relative, "review",
                       "Completed review requires declarations and a review.md reference.")
    if transition == "verified" and verdict != "approved":
        report.add("EVIDENCE_LIFECYCLE", relative, "lifecycle.transition",
                   "Verified transition requires approved review evidence.")
    required_failed = [
        check for check in checks
        if check.get("required") is True and check.get("applicability") == "applicable" and check.get("status") != "passed"
    ]
    for check in required_failed:
        report.add("EVIDENCE_REQUIRED_CHECK", relative, "checks",
                   "An applicable required check is not recorded as passed.")
    complete = status == "complete" or verdict == "approved"
    if verdict == "approved" and status != "complete":
        report.add("EVIDENCE_COMPLETE_BLOCKED", relative, "review.verdict",
                   "Approved verdict requires complete lifecycle status.")
    if complete:
        if required_failed:
            report.add("EVIDENCE_COMPLETE_BLOCKED", relative, "lifecycle.status",
                       "Complete evidence is blocked by an applicable required check.")
        if not coverage or any(not isinstance(item, dict) or item.get("status") != "covered" for item in coverage):
            report.add("EVIDENCE_COMPLETE_BLOCKED", relative, "requirement_coverage",
                       "Complete evidence requires covered requirements.")

        def passed(kind: str) -> bool:
            return any(item.get("kind") == kind and item.get("required") is True and item.get("applicability") == "applicable" and item.get("status") == "passed" for item in checks)

        def explicit(kind: str) -> bool:
            matching = [item for item in checks if item.get("kind") == kind]
            return bool(matching) and all(
                (item.get("applicability") == "not-applicable" and isinstance(item.get(
                    "not_applicable_reason"), str) and bool(item["not_applicable_reason"].strip()))
                or (item.get("applicability") == "applicable" and item.get("required") is True and item.get("status") == "passed")
                for item in matching
            )
        if not passed("scoped"):
            report.add("EVIDENCE_RISK_CHECK", relative, "checks",
                       "Complete evidence requires a passed required scoped check.")
        if risk_level in {"medium", "high"}:
            if not passed("regression"):
                report.add("EVIDENCE_RISK_CHECK", relative, "checks",
                           "Complete medium/high-risk evidence requires passed regression checks.")
            if not explicit("failure-path"):
                report.add("EVIDENCE_RISK_CHECK", relative, "checks",
                           "Complete medium/high-risk evidence requires explicit failure-path applicability.")
        if risk_level == "high" and not explicit("recovery-rollback"):
            report.add("EVIDENCE_RISK_CHECK", relative, "checks",
                       "Complete high-risk evidence requires explicit recovery/rollback applicability.")
        if verdict != "approved":
            report.add("EVIDENCE_COMPLETE_BLOCKED", relative, "review.verdict",
                       "Complete evidence requires an approved review.")
        if risk_level == "low" and independence != "self-review":
            report.add("EVIDENCE_INDEPENDENCE", relative, "review.independence",
                       "Complete low-risk evidence requires accurately labeled self-review.")
        if risk_level == "high" and independence != "independent":
            report.add("EVIDENCE_INDEPENDENCE", relative, "review.independence",
                       "Complete high-risk evidence requires independent review.")
    implementers = review.get("implementers") if isinstance(
        review.get("implementers"), list) else []
    participation = review.get("prior_participation") if isinstance(
        review.get("prior_participation"), list) else []
    reviewer_id = review.get("reviewer_id")
    if independence == "self-review" and (reviewer_id not in implementers or "implementation" not in participation):
        report.add("EVIDENCE_INDEPENDENCE", relative, "review",
                   "Self-review participation is inconsistent with declared implementers.")
    if independence == "independent" and (
        review.get("fresh_context") is not True or "implementation" in participation or
        reviewer_id in implementers or not isinstance(review.get(
            "independence_basis"), str) or not review["independence_basis"].strip()
    ):
        report.add("EVIDENCE_INDEPENDENCE", relative, "review",
                   "Independent review declarations do not establish the required separation.")
    pending = [(document, "evidence")]
    while pending:
        value, field = pending.pop()
        if isinstance(value, dict):
            pending.extend((child, f"{field}.{key}")
                           for key, child in value.items())
        elif isinstance(value, list):
            pending.extend((child, f"{field}[{index}]")
                           for index, child in enumerate(value))
        elif isinstance(value, str):
            if len(value) > 500 or any(ord(character) < 32 or ord(character) == 127 for character in value):
                report.add("EVIDENCE_STRING_SAFETY", relative, field,
                           "Evidence string is too long or contains control characters.")
            if SENSITIVE_ASSIGNMENT_RE.search(value) or COMMON_CREDENTIAL_RE.search(value):
                report.add("EVIDENCE_SENSITIVE", relative, field,
                           "Evidence contains credential-like data and must use a safe reference.")
            if PERSONAL_DATA_RE.search(value):
                report.add("EVIDENCE_SENSITIVE", relative, field,
                           "Evidence contains personal data and must use a safe reference.")


def _validate_evidence(root: Path, config: Optional[dict[str, Any]], installed: set[str], report: Report) -> list[dict[str, Any]]:
    if config is None or "evidence" not in config["enabled_modules"] or "evidence" not in installed:
        return []
    relative_root = config["roots"].get("evidence")
    if relative_root is None:
        report.add("EVIDENCE_ROOT_REQUIRED", ".agents/project.json", "roots.evidence",
                   "Enabled evidence module requires a configured evidence root.")
        return []
    evidence_root = _safe_existing(
        root, relative_root, report, "roots.evidence")
    schema_path = _safe_existing(
        root, ".agents/modules/evidence/assets/evidence.schema.json", report, "evidence.schema")
    if schema_path is None:
        return []
    schema = _load_json(schema_path, root, report, "EVIDENCE_SCHEMA")
    if not isinstance(schema, dict) or schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        report.add("EVIDENCE_SCHEMA_INVALID", ".agents/modules/evidence/assets/evidence.schema.json",
                   "", "Installed evidence schema is missing or unsupported.")
        return []
    if evidence_root is None or not evidence_root.exists():
        return []
    documents: list[dict[str, Any]] = []
    change_ids: list[str] = []
    for path in _walk_files(evidence_root, report, "roots.evidence", root):
        if path.name != "evidence.json":
            continue
        report.counts["evidence"] += 1
        value = _load_json(path, root, report, "EVIDENCE")
        if value is not None:
            _validate_evidence_document(
                value, schema, _display(root, path), report)
            if isinstance(value, dict):
                documents.append(value)
                change_id = value.get("change_id")
                if isinstance(change_id, str):
                    change_ids.append(change_id)
                    if path.parent.name != change_id:
                        report.add("EVIDENCE_CHANGE_DIRECTORY", _display(root, path),
                                   "change_id",
                                   "Evidence directory name must equal change_id.")
                lifecycle = value.get("lifecycle") if isinstance(
                    value.get("lifecycle"), dict) else {}
                review = value.get("review") if isinstance(
                    value.get("review"), dict) else {}
                if lifecycle.get("status") == "complete" or lifecycle.get("transition") == "verified":
                    if review.get("reference") != "review.md":
                        report.add("EVIDENCE_REVIEW_REFERENCE", _display(root, path),
                                   "review.reference",
                                   "Complete or verified evidence must reference review.md.")
                    else:
                        review_path = _safe_existing(
                            root,
                            (path.parent / "review.md").relative_to(root).as_posix(),
                            report,
                            "review.reference",
                        )
                        try:
                            regular = review_path is not None and stat.S_ISREG(
                                review_path.lstat().st_mode)
                        except OSError:
                            regular = False
                        if not regular:
                            report.add("EVIDENCE_REVIEW_REFERENCE", _display(root, path),
                                       "review.reference",
                                       "review.md must resolve to a regular non-symlink file beside evidence.json.")
    duplicates = {item for item in change_ids if change_ids.count(item) > 1}
    for _ in sorted(duplicates):
        report.add("EVIDENCE_CHANGE_ID_DUPLICATE", ".agents/project.json", "change_id",
                   "Evidence change_id must be unique across the configured root.")
    return documents


__all__ = ['_schema_ok', '_schema_type',
           '_validate_evidence', '_validate_evidence_document']

#!/usr/bin/env python3
"""Deterministic, dependency-free, read-only Agentic SDLC consistency checker."""

from __future__ import annotations
from lib.evidence import _schema_ok
from lib.paths import (
    DuplicateKey, _display, _load_json, _read_text, _relative_path,
    _safe_existing, _too_deep, _unique_object, _walk_files,
)
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


def _compliance_regular_reference(
    root: Path, parent: Path, reference: Any, report: Report, field: str,
    root_relative: bool = False,
) -> bool:
    if not _relative_path(reference):
        return False
    base = root if root_relative else parent
    try:
        relative = (base / reference).relative_to(root).as_posix()
    except ValueError:
        return False
    path = _safe_existing(root, relative, report, field)
    try:
        return path is not None and stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def _compliance_safe_strings(value: Any, relative: str, report: Report) -> None:
    pending = [(value, "audit")]
    while pending:
        item, field = pending.pop()
        if isinstance(item, dict):
            pending.extend((child, f"{field}.{key}")
                           for key, child in item.items())
        elif isinstance(item, list):
            pending.extend(
                (child, f"{field}[{index}]") for index, child in enumerate(item)
            )
        elif isinstance(item, str):
            if (not item or len(item) > 500
                    or any(ord(character) < 32 or ord(character) == 127 for character in item)):
                report.add("COMPLIANCE_STRING_SAFETY", relative, field,
                           "Audit strings must be non-empty, bounded, and single-line.")
            if (SENSITIVE_ASSIGNMENT_RE.search(item) or COMMON_CREDENTIAL_RE.search(item)
                    or PERSONAL_DATA_RE.search(item)):
                report.add("COMPLIANCE_SENSITIVE", relative, field,
                           "Audit data must use a non-sensitive reference.")


def _compliance_policy(config: dict[str, Any]) -> dict[str, Any]:
    policy = config.get("approval_policy")
    return policy if isinstance(policy, dict) else {"rules": []}


def _compliance_nested_order(
    event: dict[str, Any], relative: str, report: Report
) -> None:
    actor = event.get("actor")
    if isinstance(actor, dict) and tuple(actor) != COMPLIANCE_NESTED_FIELDS["actor"]:
        report.add("COMPLIANCE_ORDER", relative, "actor",
                   "Actor fields must use canonical order.")
    approvals = event.get("approvals")
    if isinstance(approvals, list):
        for index, approval in enumerate(approvals):
            if isinstance(approval, dict) and tuple(approval) != COMPLIANCE_NESTED_FIELDS["approval"]:
                report.add("COMPLIANCE_ORDER", relative, f"approvals[{index}]",
                           "Approval fields must use canonical order.")
    repositories = event.get("repositories")
    if isinstance(repositories, list):
        for index, repository in enumerate(repositories):
            if isinstance(repository, dict) and tuple(repository) != COMPLIANCE_NESTED_FIELDS["repository"]:
                report.add("COMPLIANCE_ORDER", relative, f"repositories[{index}]",
                           "Repository fields must use canonical order.")


def _validate_compliance_event(
    event: dict[str, Any], line: str, line_number: int, relative: str,
    parent: Path, root: Path, evidence: dict[str, Any], config: dict[str, Any],
    schema: dict[str, Any], state: dict[str, Any], report: Report,
) -> None:
    line_field = f"line {line_number}"
    if not _schema_ok(event, schema, schema):
        report.add("COMPLIANCE_SCHEMA", relative, line_field,
                   "Audit event does not conform to the installed closed schema.")
    if tuple(event) != COMPLIANCE_EVENT_FIELDS:
        report.add("COMPLIANCE_ORDER", relative, line_field,
                   "Audit event fields must use canonical order.")
    _compliance_nested_order(event, relative, report)
    canonical = json.dumps(event, separators=(",", ":"), ensure_ascii=True)
    if line != canonical:
        report.add("COMPLIANCE_ENCODING", relative, line_field,
                   "Audit events must use one compact deterministic JSON object per line.")
    _compliance_safe_strings(event, relative, report)
    if set(event) != set(COMPLIANCE_EVENT_FIELDS):
        return

    sequence = event.get("sequence")
    if type(sequence) is not int or sequence < 1:
        report.add("COMPLIANCE_SEQUENCE", relative, "sequence",
                   "Audit sequence must be a positive integer.")
    else:
        if sequence in state["sequences"]:
            report.add("COMPLIANCE_SEQUENCE_DUPLICATE", relative, "sequence",
                       "Audit sequences must be unique.")
        if state["last_sequence"] is not None and sequence <= state["last_sequence"]:
            report.add("COMPLIANCE_SEQUENCE", relative, "sequence",
                       "Audit sequences must increase monotonically.")
        state["sequences"].add(sequence)
        state["last_sequence"] = sequence

    event_id = event.get("event_id")
    if isinstance(event_id, str):
        if event_id in state["event_ids"]:
            report.add("COMPLIANCE_EVENT_ID_DUPLICATE", relative, "event_id",
                       "Stable event IDs must be unique.")
        state["event_ids"].add(event_id)

    timestamp = event.get("timestamp")
    parsed_timestamp: Optional[datetime] = None
    if isinstance(timestamp, str) and COMPLIANCE_TIMESTAMP_RE.fullmatch(timestamp):
        try:
            parsed_timestamp = datetime.strptime(
                timestamp, "%Y-%m-%dT%H:%M:%SZ"
            )
        except ValueError:
            parsed_timestamp = None
    if parsed_timestamp is None:
        report.add("COMPLIANCE_TIMESTAMP", relative, "timestamp",
                   "Timestamp must be a valid RFC3339 UTC whole-second value.")
    else:
        if timestamp in state["timestamps"]:
            report.add("COMPLIANCE_TIMESTAMP", relative, "timestamp",
                       "Audit timestamps must be unique.")
        if state["last_timestamp"] is not None and parsed_timestamp <= state["last_timestamp"]:
            report.add("COMPLIANCE_TIMESTAMP", relative, "timestamp",
                       "Audit timestamps must increase monotonically.")
        state["timestamps"].add(timestamp)
        state["last_timestamp"] = parsed_timestamp

    change_id = event.get("change_id")
    expected_change = evidence.get("change_id")
    if change_id != expected_change or parent.name != expected_change:
        report.add("COMPLIANCE_CHANGE_ID", relative, "change_id",
                   "Audit, evidence, and change directory IDs must agree.")
    if state["change_id"] is None:
        state["change_id"] = change_id
    elif change_id != state["change_id"]:
        report.add("COMPLIANCE_CHANGE_ID", relative, "change_id",
                   "Every audit line must use the same change ID.")

    action = event.get("action")
    previous, new = event.get("previous_lifecycle"), event.get("new_lifecycle")
    if action == "lifecycle-transition":
        if (previous, new) not in COMPLIANCE_TRANSITIONS:
            report.add("COMPLIANCE_TRANSITION", relative, "lifecycle",
                       "Lifecycle transition is not allowed by the core specification.")
        if state["last_lifecycle"] is not None and previous != state["last_lifecycle"]:
            report.add("COMPLIANCE_TRANSITION", relative, "previous_lifecycle",
                       "Lifecycle transitions must form one ordered chain.")
        state["last_lifecycle"] = new
        lifecycle = evidence.get("lifecycle") if isinstance(
            evidence.get("lifecycle"), dict) else {}
        transition = lifecycle.get("transition")
        if new == "implemented" and transition not in {"implemented", "verified"}:
            report.add("COMPLIANCE_EVIDENCE_LINK", relative, "new_lifecycle",
                       "Implemented transition must agree with evidence lifecycle.")
        if new == "verified" and transition != "verified":
            report.add("COMPLIANCE_EVIDENCE_LINK", relative, "new_lifecycle",
                       "Verified transition must agree with evidence lifecycle.")
    elif previous is not None or new is not None:
        report.add("COMPLIANCE_TRANSITION", relative, "lifecycle",
                   "Non-lifecycle actions must use null lifecycle fields.")

    sources = evidence.get("authoritative_sources")
    known_sources = {
        item.get("reference") for item in sources
        if isinstance(item, dict) and isinstance(item.get("reference"), str)
    } if isinstance(sources, list) else set()
    source_references = event.get("authoritative_source_references")
    if isinstance(source_references, list):
        if source_references != sorted(source_references) or len(source_references) != len(set(source_references)):
            report.add("COMPLIANCE_ORDER", relative, "authoritative_source_references",
                       "Source references must be unique and ordered.")
        for reference in source_references:
            if reference not in known_sources and not _compliance_regular_reference(
                root, parent, reference, report,
                "authoritative_source_references", root_relative=True,
            ):
                report.add("COMPLIANCE_REFERENCE", relative,
                           "authoritative_source_references",
                           "Authoritative source reference does not resolve.")

    evidence_references = event.get("evidence_references")
    if isinstance(evidence_references, list):
        if evidence_references != sorted(evidence_references) or len(evidence_references) != len(set(evidence_references)):
            report.add("COMPLIANCE_ORDER", relative, "evidence_references",
                       "Evidence references must be unique and ordered.")
        for reference in evidence_references:
            if not _compliance_regular_reference(
                root, parent, reference, report, "evidence_references"
            ):
                report.add("COMPLIANCE_REFERENCE", relative, "evidence_references",
                           "Evidence or review reference does not resolve beside the audit.")

    approvals = event.get("approvals") if isinstance(
        event.get("approvals"), list) else []
    approval_keys = [
        (str(item.get("role")), str(item.get("actor_id")))
        for item in approvals if isinstance(item, dict)
    ]
    if approval_keys != sorted(approval_keys) or len(approval_keys) != len(set(approval_keys)):
        report.add("COMPLIANCE_ORDER", relative, "approvals",
                   "Approvals must be unique and ordered by role then actor ID.")
    for approval in approvals:
        if isinstance(approval, dict) and not _compliance_regular_reference(
            root, parent, approval.get(
                "reference"), report, "approvals.reference"
        ):
            report.add("COMPLIANCE_REFERENCE", relative, "approvals.reference",
                       "Approval reference does not resolve beside the audit.")

    risk_record = evidence.get("risk") if isinstance(
        evidence.get("risk"), dict) else {}
    risk = risk_record.get("level")
    matching_rules = [
        rule for rule in _compliance_policy(config).get("rules", [])
        if isinstance(rule, dict) and rule.get("risk") == risk and rule.get("action") == action
    ]
    required_roles: list[dict[str, Any]] = []
    independence_required = bool(
        risk == "high" and action == "lifecycle-transition" and new == "verified"
    )
    for rule in matching_rules:
        roles = rule.get("required_roles")
        if isinstance(roles, list):
            required_roles.extend(
                item for item in roles if isinstance(item, dict))
        independence_required = independence_required or rule.get(
            "independent") is True
    review = evidence.get("review") if isinstance(
        evidence.get("review"), dict) else {}
    review_implementers = {
        item for item in review.get("implementers", []) if isinstance(item, str)
    } if isinstance(review.get("implementers"), list) else set()
    audit_implementers = state.get("audit_implementers", set())
    implementers = review_implementers | (
        audit_implementers if isinstance(audit_implementers, set) else set()
    )
    requirements_apply = bool(required_roles or independence_required)
    if requirements_apply and not approvals:
        report.add("COMPLIANCE_APPROVAL_REQUIRED", relative, "approvals",
                   "Required declared approval is missing.")
    for requirement in required_roles:
        role, minimum = requirement.get("role"), requirement.get("minimum")
        actors = {
            item.get("actor_id") for item in approvals
            if isinstance(item, dict) and item.get("role") == role
            and isinstance(item.get("actor_id"), str)
            and (not independence_required or item.get("actor_id") not in implementers)
        }
        if type(minimum) is int and len(actors) < minimum:
            report.add("COMPLIANCE_APPROVAL_COUNT", relative, "approvals",
                       "Declared approval role does not meet its required minimum count.")
    if independence_required:
        self_approvals = [
            item for item in approvals
            if isinstance(item, dict) and item.get("actor_id") in implementers
        ]
        if self_approvals:
            report.add("COMPLIANCE_SELF_APPROVAL", relative, "approvals",
                       "An approval requiring independence cannot come from any declared implementer.")
        if approvals and not any(
            isinstance(item, dict) and item.get("actor_id") not in implementers
            for item in approvals
        ):
            report.add("COMPLIANCE_APPROVAL_REQUIRED", relative, "approvals",
                       "Independent approval requires a declared non-implementer actor.")

    repositories = event.get("repositories") if isinstance(
        event.get("repositories"), list) else []
    repository_ids = [
        item.get("repository_id") for item in repositories
        if isinstance(item, dict) and isinstance(item.get("repository_id"), str)
    ]
    if repository_ids != sorted(repository_ids) or len(repository_ids) != len(set(repository_ids)):
        report.add("COMPLIANCE_ORDER", relative, "repositories",
                   "Affected repositories must be unique and ordered by Repository ID.")
    scopes = evidence.get("repository_scope") if isinstance(
        evidence.get("repository_scope"), list) else []
    expected_revisions = {
        item.get("repository_id"): item.get("head")
        for item in scopes if isinstance(item, dict)
        and isinstance(item.get("repository_id"), str)
    }
    actual_revisions = {
        item.get("repository_id"): item.get("revision")
        for item in repositories if isinstance(item, dict)
        and isinstance(item.get("repository_id"), str)
    }
    if set(actual_revisions) != set(expected_revisions):
        report.add("COMPLIANCE_REPOSITORY_IDS", relative, "repositories",
                   "Audit repository IDs must exactly match affected evidence scope.")
    if actual_revisions != expected_revisions:
        report.add("COMPLIANCE_REPOSITORY_REVISION", relative, "repositories",
                   "Audit revisions must match immutable evidence head revisions.")
    enabled = set(config.get("enabled_modules", []))
    if "multi-repo" in enabled:
        configured_ids = {
            item.get("id") for item in config.get("repositories", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        if set(actual_revisions) - configured_ids:
            report.add("COMPLIANCE_REPOSITORY_IDS", relative, "repositories",
                       "Audit references a Repository ID absent from active multi-repo config.")


def _validate_compliance(
    root: Path, config: dict[str, Any], evidence: list[dict[str, Any]],
    tasks: dict[str, dict[str, Any]], report: Report,
) -> None:
    del tasks
    enabled = set(config.get("enabled_modules", []))
    if not {"compliance", "evidence", "enforcement"}.issubset(enabled):
        return
    for name in ("compliance", "evidence", "enforcement"):
        path = _safe_existing(
            root, f".agents/modules/{name}/MODULE.md", report, "modules"
        )
        if path is None or not path.is_file():
            return
    evidence_root_value = config.get("roots", {}).get("evidence")
    if not isinstance(evidence_root_value, str):
        return
    evidence_root = _safe_existing(
        root, evidence_root_value, report, "roots.evidence"
    )
    schema_path = _safe_existing(
        root,
        ".agents/modules/compliance/assets/audit-event.schema.json",
        report,
        "compliance.schema",
    )
    if schema_path is None:
        return
    schema = _load_json(schema_path, root, report, "COMPLIANCE_SCHEMA")
    if not isinstance(schema, dict) or schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        report.add("COMPLIANCE_SCHEMA_INVALID",
                   ".agents/modules/compliance/assets/audit-event.schema.json", "",
                   "Installed compliance event schema is missing or unsupported.")
        return
    if evidence_root is None or not evidence_root.exists():
        return
    evidence_by_change = {
        item.get("change_id"): item for item in evidence
        if isinstance(item.get("change_id"), str)
    }
    audit_paths = [
        path for path in _walk_files(evidence_root, report, "roots.evidence", root)
        if path.name == "audit.jsonl"
    ]
    audited_changes = {path.parent.name for path in audit_paths}
    for change_id in sorted(evidence_by_change):
        if change_id not in audited_changes:
            report.add("COMPLIANCE_AUDIT_REQUIRED",
                       f"{evidence_root_value}/{change_id}/audit.jsonl", "",
                       "Active compliance requires audit.jsonl beside evidence.json.")
    for path in audit_paths:
        relative = _display(root, path)
        for sibling in ("evidence.json", "review.md"):
            if not _compliance_regular_reference(
                root, path.parent, sibling, report, "adjacent artifacts"
            ):
                report.add("COMPLIANCE_REFERENCE", relative, "adjacent artifacts",
                           "Audit requires regular evidence.json and review.md siblings.")
        document = evidence_by_change.get(path.parent.name)
        if document is None:
            report.add("COMPLIANCE_EVIDENCE_LINK", relative, "change_id",
                       "Audit has no matching evidence.json document.")
            continue
        text = _read_text(path, root, report, "COMPLIANCE_UNREADABLE")
        if text is None:
            continue
        lines = text.splitlines()
        if not lines:
            report.add("COMPLIANCE_AUDIT_EMPTY", relative, "",
                       "Audit log must contain at least one event.")
            continue
        audit_implementers: set[str] = set()
        for line in lines:
            try:
                candidate = json.loads(line, object_pairs_hook=_unique_object)
            except (DuplicateKey, json.JSONDecodeError, RecursionError):
                continue
            if not isinstance(candidate, dict) or _too_deep(candidate):
                continue
            actor = candidate.get("actor")
            if not isinstance(actor, dict):
                continue
            actor_id, role = actor.get("actor_id"), actor.get("role")
            if (
                isinstance(actor_id, str)
                and isinstance(role, str)
                and role.strip().lower() in COMPLIANCE_IMPLEMENTATION_ROLES
            ):
                audit_implementers.add(actor_id)
        state: dict[str, Any] = {
            "audit_implementers": audit_implementers,
            "last_sequence": None,
            "sequences": set(),
            "event_ids": set(),
            "last_timestamp": None,
            "timestamps": set(),
            "change_id": None,
            "last_lifecycle": None,
        }
        for line_number, line in enumerate(lines, 1):
            if not line or len(line.encode("utf-8")) > 65536:
                report.add("COMPLIANCE_LINE_BOUNDS", relative, f"line {line_number}",
                           "Every audit line must be one bounded JSON object.")
                continue
            try:
                event = json.loads(line, object_pairs_hook=_unique_object)
            except DuplicateKey:
                report.add("COMPLIANCE_DUPLICATE_KEY", relative, f"line {line_number}",
                           "Audit event contains a duplicate object key.")
                continue
            except (json.JSONDecodeError, RecursionError):
                report.add("COMPLIANCE_JSON_INVALID", relative, f"line {line_number}",
                           "Audit line is not valid bounded JSON.")
                continue
            if _too_deep(event):
                report.add("COMPLIANCE_JSON_DEPTH", relative, f"line {line_number}",
                           "Audit event nesting exceeds the supported depth.")
                continue
            if not isinstance(event, dict):
                report.add("COMPLIANCE_SCHEMA", relative, f"line {line_number}",
                           "Audit line must be one JSON object.")
                continue
            _validate_compliance_event(
                event, line, line_number, relative, path.parent, root,
                document, config, schema, state, report,
            )


__all__ = ['_compliance_nested_order', '_compliance_policy', '_compliance_regular_reference',
           '_compliance_safe_strings', '_validate_compliance', '_validate_compliance_event']

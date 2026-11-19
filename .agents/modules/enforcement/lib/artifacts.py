#!/usr/bin/env python3
"""Deterministic, dependency-free, read-only Agentic SDLC consistency checker."""

from __future__ import annotations
from lib.paths import _display, _read_text, _safe_existing, _walk_files
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


def _frontmatter(text: str) -> Optional[dict[str, Any]]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return None
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None
    result: dict[str, Any] = {}
    current: Optional[str] = None
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current:
            if not isinstance(result.get(current), list):
                return None
            result[current].append(line[4:].strip())
            continue
        if line[0].isspace() or ":" not in line:
            return None
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if not key or key in result:
            return None
        if value == "":
            result[key] = []
        elif value == "[]":
            result[key] = []
        elif value.startswith("["):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return None
            result[key] = parsed
        else:
            result[key] = value.strip('"')
        current = key
    return result


def _split_refs(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if not isinstance(value, str):
        return []
    stripped = value.strip()
    if not stripped or stripped.lower() in {"none", "n/a", "not-applicable"}:
        return []
    return [item.strip().strip("`") for item in re.split(r"\s*,\s*|\s+", stripped) if item.strip()]


def _validate_artifacts(
    root: Path,
    config: Optional[dict[str, Any]],
    evidence: list[dict[str, Any]],
    report: Report,
) -> dict[str, dict[str, Any]]:
    roots = config["roots"] if config is not None else {
        "specs": "specs", "work": ".work"}
    spec_root = _safe_existing(root, roots["specs"], report, "roots.specs")
    work_root = _safe_existing(root, roots["work"], report, "roots.work")
    spec_files = [item for item in _walk_files(
        spec_root, report, "roots.specs", root) if item.suffix.lower() == ".md"] if spec_root is not None else []
    work_files = [item for item in _walk_files(
        work_root, report, "roots.work", root) if item.suffix.lower() == ".md"] if work_root is not None else []
    specs: dict[str, tuple[Path, dict[str, Any], set[str]]] = {}
    requirements: set[str] = set()
    plans: dict[str, tuple[Path, dict[str, Any]]] = {}
    tasks: dict[str, dict[str, Any]] = {}
    for path in spec_files:
        if path.name.lower() in {"readme.md", "index.md", "spec-index.md"}:
            continue
        text = _read_text(path, root, report, "ARTIFACT_UNREADABLE")
        if text is None:
            continue
        metadata = _frontmatter(text)
        if metadata is None:
            report.add("ARTIFACT_FRONTMATTER", _display(root, path),
                       "", "Specification frontmatter is missing or malformed.")
            continue
        spec_id = metadata.get("id")
        if not isinstance(spec_id, str) or not ID_PATTERNS["spec"].fullmatch(spec_id):
            report.add("ARTIFACT_ID_INVALID", _display(root, path),
                       "id", "Specification ID must use SPEC-NNN form.")
            continue
        if spec_id in specs:
            report.add("ARTIFACT_ID_DUPLICATE", _display(root, path),
                       "id", "Specification ID is duplicated.")
        local_requirements = set(re.findall(r"\bREQ-[0-9]+\b", text))
        requirements.update(local_requirements)
        specs[spec_id] = (path, metadata, local_requirements)
    for path in work_files:
        if path.name not in {"plan.md", "tasks.md"}:
            continue
        text = _read_text(path, root, report, "ARTIFACT_UNREADABLE")
        if text is None:
            continue
        if path.name == "plan.md":
            metadata = _frontmatter(text)
            if metadata is None:
                report.add("ARTIFACT_FRONTMATTER", _display(root, path),
                           "", "Plan frontmatter is missing or malformed.")
                continue
            plan_id = metadata.get("id")
            if not isinstance(plan_id, str) or not ID_PATTERNS["plan"].fullmatch(plan_id):
                report.add("ARTIFACT_ID_INVALID", _display(
                    root, path), "id", "Plan ID must use PLAN-NNN form.")
                continue
            if plan_id in plans:
                report.add("ARTIFACT_ID_DUPLICATE", _display(
                    root, path), "id", "Plan ID is duplicated.")
            if metadata.get("status") not in {"draft", "approved", "stale", "implemented"}:
                report.add("ARTIFACT_STATE_INVALID", _display(root, path),
                           "status", "Plan status is missing or not recognized.")
            if metadata.get("risk") not in {"low", "medium", "high"}:
                report.add("ARTIFACT_STATE_INVALID", _display(root, path),
                           "risk", "Plan risk is missing or not recognized.")
            if not isinstance(metadata.get("risk_rationale"), str) or not metadata["risk_rationale"].strip():
                report.add("ARTIFACT_FIELD_REQUIRED", _display(root, path),
                           "risk_rationale", "Plan risk requires a recorded rationale.")
            plans[plan_id] = (path, metadata)
        else:
            _parse_tasks(text, path, root, tasks, report)
    report.counts["specs"] = len(specs)
    report.counts["plans"] = len(plans)
    report.counts["tasks"] = len(tasks)
    report.counts["artifacts"] = len(specs) + len(plans) + len(tasks)
    known_sources = set(specs) | requirements
    for plan_id, (path, metadata) in sorted(plans.items()):
        for reference in _split_refs(metadata.get("sources")):
            if _local_source_reference(reference) and reference not in known_sources:
                report.add("ARTIFACT_REFERENCE_DANGLING", _display(root, path), "sources",
                           "Plan source reference does not resolve to a present specification item.")
    known_plans = set(plans)
    known_tasks = set(tasks)
    for task_id, task in sorted(tasks.items()):
        path = task["path"]
        for reference in task.get("plans", []):
            if ID_PATTERNS["plan"].fullmatch(reference) and reference not in known_plans:
                report.add("ARTIFACT_REFERENCE_DANGLING", path, "Plan",
                           "Task plan reference does not resolve to a present plan.")
        for reference in task.get("sources", []):
            if _local_source_reference(reference) and reference not in known_sources:
                report.add("ARTIFACT_REFERENCE_DANGLING", path, "Source items",
                           "Task source reference does not resolve to a present specification item.")
        dependencies = task.get("dependencies", [])
        if len(dependencies) != len(set(dependencies)):
            report.add("TASK_DEPENDENCY_DUPLICATE", path, "Depends on",
                       "Task dependencies must be unique.")
        for dependency in dependencies:
            if not ID_PATTERNS["task"].fullmatch(dependency):
                report.add("ARTIFACT_ID_INVALID", path, "Depends on",
                           "Task dependencies must use TASK-NNN form.")
            if dependency not in known_tasks:
                report.add("ARTIFACT_REFERENCE_DANGLING", path, "Depends on",
                           "Task dependency does not resolve to a present task.")
            if task.get("state") in {"ready", "in-progress", "done"} and (dependency not in tasks or tasks[dependency].get("state") != "done"):
                report.add("TASK_DEPENDENCY_NOT_DONE", path, "Depends on",
                           "Runnable or completed task has a dependency not recorded as done.")
        if task.get("state") == "done" and task.get("result", "").strip().lower() in {"", "pending", "none", "n/a"}:
            report.add("TASK_DONE_WITHOUT_RESULT", path, "Result",
                       "Completed task must record an observed result.")
    cycle_reported = False
    for root_task in sorted(tasks):
        pending = [(root_task, ())]
        while pending and not cycle_reported:
            current, ancestors = pending.pop()
            if current in ancestors:
                report.add("TASK_DEPENDENCY_CYCLE", tasks[root_task]["path"],
                           "Depends on", "Task dependencies contain a cycle.")
                cycle_reported = True
                break
            pending.extend((dependency, ancestors + (current,))
                           for dependency in tasks.get(current, {}).get("dependencies", [])
                           if dependency in tasks)
        if cycle_reported:
            break
    referenced_specs: set[str] = set()
    for _, metadata in plans.values():
        referenced_specs.update(reference for reference in _split_refs(
            metadata.get("sources")) if reference in specs)
    for spec_id, (path, metadata, _) in sorted(specs.items()):
        status = metadata.get("status")
        if status not in {"draft", "approved", "planned", "implemented", "verified"}:
            report.add("ARTIFACT_STATE_INVALID", _display(root, path),
                       "status", "Specification status is not recognized.")
        elif status == "planned" and spec_id not in referenced_specs:
            report.add("LIFECYCLE_TRANSITION_UNSUPPORTED", _display(
                root, path), "status", "Planned status lacks a present plan reference.")
        elif status in {"implemented", "verified"} and tasks:
            linked_done = any(task.get("state") == "done" and (spec_id in task.get("sources", []) or bool(
                specs[spec_id][2] & set(task.get("sources", [])))) for task in tasks.values())
            if not linked_done:
                report.add("LIFECYCLE_TRANSITION_UNSUPPORTED", _display(
                    root, path), "status", "Implemented or verified status lacks completed linked task evidence.")
        if status == "verified" and evidence:
            source_ids = {
                source.get("id") for document in evidence
                for source in document.get("authoritative_sources", [])
                if isinstance(source, dict)
            }
            if spec_id not in source_ids and not (specs[spec_id][2] & source_ids):
                report.add("LIFECYCLE_TRANSITION_UNSUPPORTED", _display(
                    root, path), "status", "Verified status lacks linked verification evidence.")
    return tasks


def _local_source_reference(value: str) -> bool:
    return bool(ID_PATTERNS["spec"].fullmatch(value) or
                ID_PATTERNS["requirement"].fullmatch(value))


def _parse_tasks(text: str, path: Path, root: Path, tasks: dict[str, dict[str, Any]], report: Report) -> None:
    relative = _display(root, path)
    headings = re.findall(
        r"^###\s+([^:\s]+)(?:\s*:[^\n]*)?$", text, re.MULTILINE)
    for heading in headings:
        if not ID_PATTERNS["task"].fullmatch(heading):
            report.add("ARTIFACT_ID_INVALID", relative, "task.id",
                       "Every level-three task heading must use TASK-NNN form.")
    matches = list(re.finditer(
        r"^###\s+(TASK-[^:\s]+)\s*:[^\n]*$", text, re.MULTILINE))
    for index, match in enumerate(matches):
        task_id = match.group(1)
        relative = _display(root, path)
        if not ID_PATTERNS["task"].fullmatch(task_id):
            report.add("ARTIFACT_ID_INVALID", relative, "task.id",
                       "Task ID must use TASK-NNN form.")
            continue
        if task_id in tasks:
            report.add("ARTIFACT_ID_DUPLICATE", relative,
                       "task.id", "Task ID is duplicated.")
            continue
        end = matches[index + 1].start() if index + \
            1 < len(matches) else len(text)
        section = text[match.end():end]
        fields: dict[str, str] = {}
        for field, value in re.findall(r"^-\s+([^:\n]+):\s*(.*)$", section, re.MULTILINE):
            fields[field.strip().lower()] = value.strip()
        tasks[task_id] = {
            "path": relative,
            "plans": _split_refs(fields.get("plan")),
            "sources": _split_refs(fields.get("source items")),
            "state": fields.get("state", "").lower(),
            "dependencies": _split_refs(fields.get("depends on")),
            "repositories": _split_refs(fields.get("repository")),
            "cross_dependencies": _split_refs(fields.get("cross-repo depends on")),
            "has_cross_dependencies": "cross-repo depends on" in fields,
            "integration_evidence": fields.get("integration evidence", ""),
            "has_integration_evidence": "integration evidence" in fields,
            "dirty_status": fields.get("dirty status", ""),
            "ownership": fields.get("ownership/isolation", ""),
            "blocker": fields.get("blocker", ""),
            "result": fields.get("result", ""),
        }
        task = tasks[task_id]
        if task["state"] not in {"blocked", "ready", "in-progress", "done", "stale"}:
            report.add("TASK_STATE_INVALID", relative, "State",
                       "Task state is missing or not recognized.")
        if not task["plans"]:
            report.add("TASK_FIELD_REQUIRED", relative, "Plan",
                       "Every task graph entry requires a plan reference.")
        if not task["sources"]:
            report.add("TASK_FIELD_REQUIRED", relative, "Source items",
                       "Every task graph entry requires source items.")
        blocker = task["blocker"].strip().lower()
        if task["state"] == "blocked" and blocker in {"", "none", "n/a", "not-applicable"}:
            report.add("TASK_BLOCKER_INCONSISTENT", relative, "Blocker",
                       "Blocked task requires a recorded blocker.")
        if task["state"] != "blocked" and blocker not in {"", "none", "n/a", "not-applicable"}:
            report.add("TASK_BLOCKER_INCONSISTENT", relative, "Blocker",
                       "Only blocked tasks may carry an active blocker.")


__all__ = ['_frontmatter', '_local_source_reference',
           '_parse_tasks', '_split_refs', '_validate_artifacts']

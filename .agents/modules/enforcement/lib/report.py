#!/usr/bin/env python3
"""Deterministic, dependency-free, read-only Agentic SDLC consistency checker."""

from __future__ import annotations

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




class Report:
    def __init__(self) -> None:
        self.errors: list[dict[str, str]] = []
        self.warnings: list[dict[str, str]] = []
        self.counts = {
            "modules": 0, "specs": 0, "plans": 0, "tasks": 0,
            "evidence": 0, "artifacts": 0,
        }
        self.config_error = False

    def add(
        self, code: str, path: str, field: str, message: str,
        warning: bool = False, config: bool = False,
    ) -> None:
        issue = {"code": code, "path": path,
                 "field": field, "message": message}
        (self.warnings if warning else self.errors).append(issue)
        self.config_error = self.config_error or config

    def document(self) -> dict[str, Any]:
        self.errors.sort(key=_issue_key)
        self.warnings.sort(key=_issue_key)
        valid = not self.errors
        return {
            "schema_version": SCHEMA_VERSION,
            "valid": valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "summary": (
                "validation passed" if valid else
                f"validation failed with {len(self.errors)} error(s)"
            ),
            "counts": self.counts,
        }


def _issue_key(item: dict[str, str]) -> tuple[str, str, str, str]:
    return item["path"], item["field"], item["code"], item["message"]


def _render(document: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(document, separators=(",", ":"), ensure_ascii=True) + "\n"
    state = "VALID" if document["valid"] else "INVALID"
    lines = [f"Agentic SDLC enforcement: {state}", document["summary"]]
    for label in ("errors", "warnings"):
        for issue in document[label]:
            field = f" ({issue['field']})" if issue["field"] else ""
            lines.append(
                f"- [{issue['code']}] {issue['path']}{field}: {issue['message']}")
    counts = document["counts"]
    lines.append(
        "Counts: " + ", ".join(f"{key}={counts[key]}" for key in counts))
    return "\n".join(lines) + "\n"


__all__ = ['Report', '_issue_key', '_render']

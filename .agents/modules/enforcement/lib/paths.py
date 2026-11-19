#!/usr/bin/env python3
"""Deterministic, dependency-free, read-only Agentic SDLC consistency checker."""

from __future__ import annotations
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


class DuplicateKey(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKey(key)
        result[key] = value
    return result


def _relative_path(value: Any, allow_dot: bool = False) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    if re.match(r"^[A-Za-z]:", value) or value.startswith("/"):
        return False
    if value == ".":
        return allow_dot
    return all(part not in ("", ".", "..") for part in value.split("/"))


def _repository_path_syntax(value: Any) -> bool:
    if _relative_path(value, allow_dot=True) and not any(
        token in value for token in ("$", "{", "}")
    ):
        return True
    if not isinstance(value, str):
        return False
    match = re.fullmatch(r"\$\{([A-Z_][A-Z0-9_]*)\}/(.+)", value)
    return bool(
        match
        and _relative_path(match.group(2))
        and not any(token in match.group(2) for token in ("$", "{", "}"))
    )


def _display(root: Path, path: Path) -> str:
    try:
        relative = path.relative_to(root).as_posix()
        return relative or "."
    except ValueError:
        return "."


def _safe_existing(root: Path, relative: str, report: Report, field: str) -> Optional[Path]:
    current = root
    for part in relative.split("/") if relative != "." else ():
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            return root.joinpath(*relative.split("/"))
        except OSError:
            report.add("PATH_UNREADABLE", relative, field,
                       "Path cannot be inspected safely.")
            return None
        if stat.S_ISLNK(info.st_mode):
            issue_path = ".agents/project.json" if field.startswith(
                "roots.") else relative
            report.add("PATH_SYMLINK", issue_path, field,
                       "Configured or inspected path must not contain a symlink.")
            return None
    return current


def _root_relative_path(root: Path, path: Path, report: Report, field: str) -> Optional[Path]:
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        report.add("PATH_OUTSIDE_ROOT", ".", field,
                   "Read path must remain inside the repository root.")
        return None
    return _safe_existing(root, relative, report, field)


def _read_text(path: Path, root: Path, report: Report, code: str, field: str = "") -> Optional[str]:
    try:
        safe_path = _root_relative_path(root, path, report, field)
        if safe_path is None:
            return None
        path = safe_path
        if path.is_symlink() or not path.is_file():
            report.add(code, _display(root, path), field,
                       "Required file is missing or unsafe.")
            return None
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        report.add(code, _display(root, path), field,
                   "File cannot be read as UTF-8.")
        return None


def _load_json(path: Path, root: Path, report: Report, prefix: str) -> Optional[Any]:
    text = _read_text(path, root, report, f"{prefix}_UNREADABLE")
    if text is None:
        return None
    try:
        value = json.loads(text, object_pairs_hook=_unique_object)
    except DuplicateKey:
        report.add(f"{prefix}_DUPLICATE_KEY", _display(root, path),
                   "", "JSON contains a duplicate object key.")
        return None
    except RecursionError:
        report.add(f"{prefix}_JSON_DEPTH", _display(root, path),
                   "", "JSON nesting exceeds the supported depth.")
        return None
    except json.JSONDecodeError:
        report.add(f"{prefix}_JSON_INVALID", _display(
            root, path), "", "File is not valid JSON.")
        return None
    if _too_deep(value):
        report.add(f"{prefix}_JSON_DEPTH", _display(root, path),
                   "", "JSON nesting exceeds the supported depth.")
        return None
    return value


def _too_deep(value: Any, limit: int = 100) -> bool:
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > limit:
            return True
        if isinstance(item, dict):
            pending.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)
    return False


def _invalid_scalar_character(character: str) -> bool:
    codepoint = ord(character)
    return codepoint < 32 or codepoint == 127 or 0xD800 <= codepoint <= 0xDFFF


def _sensitive_query(query: str) -> bool:
    for key, _ in parse_qsl(query, keep_blank_values=True):
        normalized = re.sub(r"[^a-z0-9]", "", key.lower())
        if normalized in SENSITIVE_QUERY_KEYS or any(
            normalized.endswith(suffix) for suffix in SENSITIVE_QUERY_SUFFIXES
        ):
            return True
    return False


def _unsafe_uri_value(value: str) -> bool:
    match = URI_SCHEME_RE.match(value)
    if match is None:
        return False
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError:
        return True
    if _sensitive_query(parsed.query) or parsed.password is not None:
        return True
    if match.group(1).lower() in {"http", "https"}:
        return (
            not value.lower().startswith(("http://", "https://"))
            or not parsed.netloc
            or parsed.hostname is None
            or parsed.username is not None
        )
    return False


def _safe_config_string(value: Any) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 500
        and bool(value.strip())
        and not any(_invalid_scalar_character(character) for character in value)
        and not COMMON_CREDENTIAL_RE.search(value)
        and not SENSITIVE_ASSIGNMENT_RE.search(value)
        and not _unsafe_uri_value(value)
    )


def _safe_remote(value: Any) -> bool:
    if (not _safe_config_string(value) or value != value.strip() or "\\" in value
            or re.match(r"^[A-Za-z]:", value)
            or any(character.isspace() for character in value)):
        return False
    assert isinstance(value, str)
    scheme = URI_SCHEME_RE.match(value)
    if "://" in value:
        if scheme is None:
            return False
        try:
            parsed = urlsplit(value)
            _ = parsed.port
        except ValueError:
            return False
        if not parsed.netloc or parsed.hostname is None or parsed.password is not None:
            return False
        if parsed.username is not None:
            if not scheme.group(1).lower().endswith("ssh") or not _safe_config_string(parsed.username):
                return False
        return not _sensitive_query(parsed.query)
    if scheme is not None and scheme.group(1).lower() in {
        "file", "ftp", "ftps", "git", "http", "https", "ssh",
    }:
        return False
    return SCP_REMOTE_RE.fullmatch(value) is not None


def _config_key_safety(value: Any, report: Report, field: str = "") -> None:
    from lib.project import _config_issue
    if isinstance(value, dict):
        for key in sorted(value):
            invalid_key = not _safe_config_string(key)
            child = (
                f"{field}.<invalid-key>" if field and invalid_key
                else "<invalid-key>" if invalid_key
                else f"{field}.{key}" if field
                else key
            )
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            if invalid_key:
                _config_issue(report, "CONFIG_STRING_KEY", child,
                              "Object key must be a bounded control-free Unicode scalar string.")
            if normalized in SENSITIVE_QUERY_KEYS or any(
                normalized.endswith(suffix) for suffix in SENSITIVE_QUERY_SUFFIXES
            ):
                _config_issue(report, "CONFIG_SENSITIVE_KEY", child,
                              "Sensitive configuration keys are not allowed.")
            if normalized in EXECUTABLE_CONFIG_KEYS:
                _config_issue(report, "CONFIG_EXECUTABLE_FIELD", child,
                              "Executable command, hook, plugin, script, and regex fields are not allowed.")
            _config_key_safety(value[key], report, child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _config_key_safety(item, report, f"{field}[{index}]")
    elif isinstance(value, str) and not _safe_config_string(value):
        _config_issue(report, "CONFIG_STRING", field,
                      "Value must be a bounded control-free non-sensitive string.")


def _git_ref(value: str) -> bool:
    if (not value or value == "@" or len(value) > 500 or value.startswith(("-", "/"))
            or value.endswith(("/", ".")) or ".." in value or "//" in value
            or "@{" in value or any(character.isspace() for character in value)
            or any(character in "~^:?*[\\" for character in value)):
        return False
    return all(part and not part.startswith(".") and not part.endswith(".lock")
               for part in value.split("/"))


def _walk_files(root: Path, report: Report, field: str, project_root: Optional[Path] = None) -> list[Path]:
    if project_root is not None:
        safe_root = _root_relative_path(project_root, root, report, field)
        if safe_root is None:
            return []
        root = safe_root
    if not root.exists():
        return []
    if root.is_symlink():
        report.add("PATH_SYMLINK", _display(root.parent, root), field,
                   "Configured or inspected root must not be a symlink.")
        return []
    if not root.is_dir():
        report.add("PATH_TYPE", _display(root.parent, root), field,
                   "Configured artifact root must be a directory.")
        return []
    files: list[Path] = []
    try:
        for directory, names, filenames in os.walk(str(root), followlinks=False):
            current = Path(directory)
            safe_names = []
            for name in sorted(names):
                child = current / name
                if child.is_symlink():
                    report.add("PATH_SYMLINK", _display(root.parent, child),
                               field, "Artifact tree must not contain symlinks.")
                else:
                    safe_names.append(name)
            names[:] = safe_names
            for name in sorted(filenames):
                child = current / name
                if child.is_symlink():
                    report.add("PATH_SYMLINK", _display(root.parent, child),
                               field, "Artifact tree must not contain symlinks.")
                elif child.is_file():
                    files.append(child)
    except OSError:
        report.add("PATH_UNREADABLE", _display(root.parent, root),
                   field, "Artifact root cannot be inspected safely.")
    return sorted(files, key=lambda item: item.as_posix())


def _tree_hash(path: Path) -> Optional[str]:
    try:
        if path.is_symlink():
            return None
        if path.is_file():
            digest = hashlib.sha256(b"root:file\0")
            digest.update(path.read_bytes())
            return digest.hexdigest()
        if not path.is_dir():
            return None
        entries: list[tuple[str, str, Path]] = []
        for directory, names, filenames in os.walk(str(path), followlinks=False):
            current = Path(directory)
            for name in names:
                item = current / name
                if item.is_symlink():
                    return None
                entries.append(
                    ("dir", item.relative_to(path).as_posix(), item))
            for name in filenames:
                item = current / name
                if item.is_symlink() or not item.is_file():
                    return None
                entries.append(
                    ("file", item.relative_to(path).as_posix(), item))
        digest = hashlib.sha256(b"root:dir\0")
        for kind, relative, item in sorted(entries, key=lambda entry: (entry[1], entry[0])):
            digest.update(kind.encode("ascii") + b"\0")
            digest.update(relative.encode("utf-8") + b"\0")
            if kind == "file":
                digest.update(hashlib.sha256(item.read_bytes()).digest())
        return digest.hexdigest()
    except OSError:
        return None


def _safe_checkout_path(
    root: Path, configured: str, report: Report, field: str
) -> Optional[Path]:
    match = re.fullmatch(r"\$\{([A-Z_][A-Z0-9_]*)\}/(.+)", configured)
    if match is None:
        return _safe_existing(root, configured, report, field)
    environment_root = os.environ.get(match.group(1))
    if not environment_root:
        return None
    base = Path(environment_root)
    if not base.is_absolute():
        return None
    if ".." in base.parts:
        return None
    suffix_parts = match.group(2).split("/")
    candidate = base.joinpath(*suffix_parts)
    current = Path(base.anchor)
    try:
        anchor_info = current.lstat()
    except OSError:
        return None
    if stat.S_ISLNK(anchor_info.st_mode):
        return None
    for part in (*base.parts[1:], *suffix_parts):
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            return candidate
        except OSError:
            return None
        if stat.S_ISLNK(info.st_mode):
            return None
    return candidate


__all__ = ['DuplicateKey', '_config_key_safety', '_display', '_git_ref', '_invalid_scalar_character', '_load_json', '_read_text', '_relative_path', '_repository_path_syntax', '_root_relative_path',
           '_safe_checkout_path', '_safe_config_string', '_safe_existing', '_safe_remote', '_sensitive_query', '_too_deep', '_tree_hash', '_unique_object', '_unsafe_uri_value', '_walk_files']

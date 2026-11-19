"""Load, validate, and resolve canonical project configuration v2 safely.

This source-only module reads ``.agents/project.json`` and its explicitly supplied
schema with the Python standard library. It performs no writes, network access,
subprocess execution, environment discovery, or legacy Markdown parsing.
Malformed input produces deterministic diagnostics that identify fields without
including project values. ``.agents/project.md`` is always unsupported.
"""

from __future__ import annotations

import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional
from urllib.parse import parse_qsl, urlsplit

from .schema import Limits, validate as validate_schema


PROJECT_PATH = ".agents/project.json"
LEGACY_PROJECT_PATH = ".agents/project.md"
ROOT_KEYS = ("specs", "work", "adrs", "evidence", "domain_context")
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ENV_PATH_RE = re.compile(r"^\$\{([A-Z_][A-Z0-9_]*)\}/(.+)$")
TRAILER_RE = re.compile(r"^[A-Za-z0-9-]+$")
CREDENTIAL_RE = re.compile(
    r"(?:\bghp_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b|"
    r"\bsk-[A-Za-z0-9]{20,}\b|\bBearer\s+[A-Za-z0-9._~-]+)", re.IGNORECASE
)
SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?:api[-_ ]?key|credential|password|secret|token)\s*[:=]", re.IGNORECASE
)
SENSITIVE_KEYS = {
    "token", "accesstoken", "authtoken", "refreshtoken", "idtoken", "apikey",
    "secret", "clientsecret", "password", "passwd", "credential", "credentials",
}
SENSITIVE_SUFFIXES = (
    "token", "apikey", "secret", "password", "passwd", "credential", "credentials",
)
EXECUTABLE_KEYS = {
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


@dataclass(frozen=True, order=True)
class ProjectDiagnostic:
    """One redacted, stable project-configuration failure."""

    code: str
    field: str
    message: str


class ProjectConfigError(ValueError):
    """Raised when project configuration or a configured path is unsafe.

    ``diagnostics`` is sorted and never contains rejected configuration values.
    """

    def __init__(self, diagnostics: Iterable[ProjectDiagnostic]):
        self.diagnostics = tuple(sorted(set(diagnostics)))
        rendered = "; ".join(
            f"{item.code} {item.field}: {item.message}" for item in self.diagnostics
        )
        super().__init__(rendered or "project configuration is invalid")


class _DuplicateKey(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateKey
        value[key] = item
    return value


def _field(pointer: str) -> str:
    return pointer.lstrip("/").replace("~1", "/").replace("~0", "~")


def _safe_relative(value: Any, *, allow_dot: bool = False) -> bool:
    if not isinstance(value, str) or not value or len(value) > 500 or "\\" in value:
        return False
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        return False
    if value == ".":
        return allow_dot
    return all(part not in ("", ".", "..") for part in value.split("/"))


def _repository_path(value: Any) -> bool:
    if value == ".":
        return True
    if _safe_relative(value) and not any(token in value for token in ("$", "{", "}")):
        return True
    if not isinstance(value, str):
        return False
    match = ENV_PATH_RE.fullmatch(value)
    return bool(
        match
        and _safe_relative(match.group(2))
        and not any(token in match.group(2) for token in ("$", "{", "}"))
    )


def _invalid_scalar_character(character: str) -> bool:
    codepoint = ord(character)
    return codepoint < 32 or codepoint == 127 or 0xD800 <= codepoint <= 0xDFFF


def _sensitive_query(query: str) -> bool:
    for key, _ in parse_qsl(query, keep_blank_values=True):
        normalized = re.sub(r"[^a-z0-9]", "", key.lower())
        if normalized in SENSITIVE_KEYS or any(
            normalized.endswith(item) for item in SENSITIVE_SUFFIXES
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


def _unsafe_string(value: str) -> bool:
    return (
        not 1 <= len(value) <= 500
        or not value.strip()
        or any(_invalid_scalar_character(character) for character in value)
        or CREDENTIAL_RE.search(value) is not None
        or SENSITIVE_ASSIGNMENT_RE.search(value) is not None
        or _unsafe_uri_value(value)
    )


def _safe_remote(value: Any) -> bool:
    if (not isinstance(value, str) or _unsafe_string(value)
            or value != value.strip() or "\\" in value
            or re.match(r"^[A-Za-z]:", value)
            or any(character.isspace() for character in value)):
        return False
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
            if not scheme.group(1).lower().endswith("ssh") or _unsafe_string(parsed.username):
                return False
        return not _sensitive_query(parsed.query)
    if scheme is not None and scheme.group(1).lower() in {
        "file", "ftp", "ftps", "git", "http", "https", "ssh",
    }:
        return False
    return SCP_REMOTE_RE.fullmatch(value) is not None


def _normalized_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def _walk_strings(value: Any, field: str = "") -> Iterable[ProjectDiagnostic]:
    if isinstance(value, dict):
        for key in sorted(value):
            invalid_key = _unsafe_string(key)
            child = (
                f"{field}.<invalid-key>" if field and invalid_key
                else "<invalid-key>" if invalid_key
                else f"{field}.{key}" if field
                else key
            )
            normalized = _normalized_key(key)
            if invalid_key:
                yield ProjectDiagnostic(
                    "safety.key", child,
                    "object key must be a bounded control-free Unicode scalar string",
                )
            if normalized in SENSITIVE_KEYS or any(normalized.endswith(item) for item in SENSITIVE_SUFFIXES):
                yield ProjectDiagnostic("safety.sensitive_key", child, "sensitive configuration keys are not allowed")
            if normalized in EXECUTABLE_KEYS:
                yield ProjectDiagnostic("safety.executable_field", child, "executable command, hook, plugin, script, and regex fields are not allowed")
            yield from _walk_strings(value[key], child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_strings(item, f"{field}[{index}]")
    elif isinstance(value, str) and _unsafe_string(value):
        yield ProjectDiagnostic("safety.string", field, "value must be a bounded control-free non-sensitive string")


def _valid_ref(value: str) -> bool:
    if not value or value == "@" or len(value) > 500 or value.startswith("-") or value.startswith("/") or value.endswith("/"):
        return False
    if value.endswith(".") or ".." in value or "//" in value or "@{" in value:
        return False
    if any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in value):
        return False
    if any(character in "~^:?*[\\" for character in value):
        return False
    parts = value.split("/")
    return all(part and not part.startswith(".") and not part.endswith(".lock") for part in parts)


def _semantic_diagnostics(
    value: Mapping[str, Any],
    module_names: Optional[set[str]],
    module_dependencies: Mapping[str, set[str]],
) -> list[ProjectDiagnostic]:
    diagnostics = list(_walk_strings(value))
    roots = value.get("roots")
    if isinstance(roots, dict):
        for key in ROOT_KEYS:
            root_value = roots.get(key)
            if root_value is None and key not in ("specs", "work"):
                continue
            if (not _safe_relative(root_value)
                    or any(token in root_value for token in ("$", "{", "}"))):
                diagnostics.append(ProjectDiagnostic(
                    "path.relative", f"roots/{key}", "root must be a safe repository-relative path"))

    repositories = value.get("repositories")
    if isinstance(repositories, list):
        identifiers: set[str] = set()
        for index, repository in enumerate(repositories):
            if not isinstance(repository, dict):
                continue
            prefix = f"repositories/{index}"
            identifier = repository.get("id")
            if isinstance(identifier, str):
                if identifier in identifiers:
                    diagnostics.append(ProjectDiagnostic(
                        "repository.id_unique", f"{prefix}/id", "repository IDs must be unique"))
                identifiers.add(identifier)
            if not _repository_path(repository.get("path")):
                diagnostics.append(ProjectDiagnostic(
                    "repository.path", f"{prefix}/path", "repository path must be '.', safe relative, or exact ${UPPER_ENV}/safe form"))
            remote = repository.get("remote")
            if remote is not None and not _safe_remote(remote):
                diagnostics.append(ProjectDiagnostic(
                    "repository.remote", f"{prefix}/remote",
                    "remote must be a sanitized credential-free URI or scp-like identifier",
                ))

    enabled = value.get("enabled_modules")
    if isinstance(enabled, list):
        if len(enabled) != len(set(item for item in enabled if isinstance(item, str))):
            diagnostics.append(ProjectDiagnostic(
                "module.unique", "enabled_modules", "enabled module names must be unique"))
        if module_names is not None:
            for index, name in enumerate(enabled):
                if isinstance(name, str) and name not in module_names:
                    diagnostics.append(ProjectDiagnostic(
                        "module.unknown", f"enabled_modules/{index}", "enabled module is not present in the kit catalog"))
            enabled_set = {item for item in enabled if isinstance(item, str)}
            for name in sorted(enabled_set):
                for dependency in sorted(module_dependencies.get(name, set())):
                    if dependency not in enabled_set:
                        diagnostics.append(ProjectDiagnostic(
                            "module.dependency", "enabled_modules", "enabled module dependency is not enabled"))

    tracker = value.get("tracker")
    if isinstance(tracker, dict):
        kind, location = tracker.get("kind"), tracker.get("location")
        if kind == "none" and location is not None:
            diagnostics.append(ProjectDiagnostic(
                "tracker.consistency", "tracker.location", "location must be null when tracker kind is none"))
        if isinstance(kind, str) and kind != "none" and location is None:
            diagnostics.append(ProjectDiagnostic(
                "tracker.consistency", "tracker.location", "location is required when a tracker is configured"))
        labels = tracker.get("labels")
        if isinstance(labels, dict):
            for key, item in labels.items():
                if not isinstance(key, str) or _unsafe_string(key) or not isinstance(item, str) or _unsafe_string(item):
                    diagnostics.append(ProjectDiagnostic(
                        "tracker.labels", "tracker.labels", "label keys and values must be safe non-empty strings"))
                    break

    policy = value.get("approval_policy")
    rules = policy.get("rules") if isinstance(policy, dict) else None
    if isinstance(rules, list):
        pairs: set[tuple[str, str]] = set()
        for index, rule in enumerate(rules):
            if not isinstance(rule, dict):
                continue
            pair = (rule.get("risk"), rule.get("action"))
            if all(isinstance(item, str) for item in pair):
                if pair in pairs:
                    diagnostics.append(ProjectDiagnostic(
                        "approval.unique", f"approval_policy/rules/{index}", "risk/action policy pairs must be unique"))
                pairs.add(pair)
            if rule.get("risk") == "high" and rule.get("independent") is False:
                diagnostics.append(ProjectDiagnostic(
                    "approval.high_independent", f"approval_policy/rules/{index}/independent", "high-risk policy cannot weaken independent review"))
            roles = rule.get("required_roles")
            if isinstance(roles, list):
                seen_roles: set[str] = set()
                for role_index, requirement in enumerate(roles):
                    if not isinstance(requirement, dict):
                        continue
                    role = requirement.get("role")
                    if isinstance(role, str):
                        if role in seen_roles:
                            diagnostics.append(ProjectDiagnostic(
                                "approval.role_unique", f"approval_policy/rules/{index}/required_roles/{role_index}/role", "roles must be unique within one rule"))
                        seen_roles.add(role)

    contribution = value.get("contribution")
    if isinstance(contribution, dict):
        base = contribution.get("base_branch")
        if isinstance(base, str) and not _valid_ref(base):
            diagnostics.append(ProjectDiagnostic(
                "contribution.ref", "contribution.base_branch", "base branch must use safe Git ref syntax"))
        trailers = contribution.get("required_trailers")
        if isinstance(trailers, list):
            if len(trailers) != len(set(item for item in trailers if isinstance(item, str))):
                diagnostics.append(ProjectDiagnostic("contribution.trailer_unique",
                                   "contribution.required_trailers", "required trailer tokens must be unique"))
            for index, trailer in enumerate(trailers):
                if not isinstance(trailer, str) or TRAILER_RE.fullmatch(trailer) is None:
                    diagnostics.append(ProjectDiagnostic(
                        "contribution.trailer", f"contribution.required_trailers/{index}", "trailer must contain only letters, digits, and hyphens"))
        template = contribution.get("pull_request_template")
        if template is not None and (
            not _safe_relative(template)
            or any(token in template for token in ("$", "{", "}"))
        ):
            diagnostics.append(ProjectDiagnostic("contribution.template", "contribution.pull_request_template",
                               "pull request template must be a safe repository-relative path or null"))
    return diagnostics


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        if path.is_symlink() or not path.is_file():
            raise ProjectConfigError([ProjectDiagnostic(
                "file.type", label, "JSON input must be a regular non-symlink file")])
        if path.stat().st_size > 1_000_000:
            raise ProjectConfigError([ProjectDiagnostic(
                "limit.bytes", label, "JSON file exceeds the supported size")])
        text = path.read_text(encoding="utf-8")
        value = json.loads(text, object_pairs_hook=_unique_object)
    except _DuplicateKey as exc:
        raise ProjectConfigError([ProjectDiagnostic(
            "json.duplicate", label, "JSON contains a duplicate object key")]) from exc
    except (OSError, UnicodeError) as exc:
        raise ProjectConfigError([ProjectDiagnostic(
            "file.unreadable", label, "file must be a readable regular UTF-8 file")]) from exc
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ProjectConfigError([ProjectDiagnostic(
            "json.invalid", label, "file must contain bounded valid JSON")]) from exc
    if not isinstance(value, dict):
        raise ProjectConfigError(
            [ProjectDiagnostic("json.root", label, "JSON root must be an object")])
    return value


def validate_project(
    value: object,
    schema_path: Path,
    *,
    module_names: Optional[Iterable[str]] = None,
    module_dependencies: Optional[Mapping[str, Iterable[str]]] = None,
) -> tuple[ProjectDiagnostic, ...]:
    """Return deterministic redacted schema and semantic diagnostics.

    The function is read-only. ``schema_path`` must identify the trusted setup
    schema. Module names and dependencies come from the already validated kit
    catalog; when names are omitted, catalog-membership checks are skipped.
    """
    schema = _load_object(Path(schema_path), "project.schema.json")
    result = validate_schema(value, schema, limits=Limits(
        max_string_length=500, max_array_length=1000))
    diagnostics = []
    for item in result.diagnostics:
        field = _field(item.instance_path)
        if item.code == "required" and not field and ": " in item.message:
            field = item.message.rsplit(": ", 1)[1]
        diagnostics.append(ProjectDiagnostic(
            f"schema.{item.code}", field,
            "project configuration does not match the closed v2 schema",
        ))
    if isinstance(value, dict):
        dependency_sets = {
            name: set(dependencies)
            for name, dependencies in (module_dependencies or {}).items()
        }
        diagnostics.extend(_semantic_diagnostics(
            value,
            None if module_names is None else set(module_names),
            dependency_sets,
        ))
    return tuple(sorted(set(diagnostics)))


def _lstat_exists(path: Path) -> bool:
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False


def _legacy_project_present(root: Path) -> bool:
    agents = root / ".agents"
    try:
        info = agents.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise ProjectConfigError([ProjectDiagnostic(
            "path.unreadable", ".agents", "configuration directory cannot be inspected safely")]) from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ProjectConfigError([ProjectDiagnostic(
            "path.type", ".agents", "configuration directory must be a non-symlink directory")])
    try:
        (agents / "project.md").lstat()
        return True
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise ProjectConfigError([ProjectDiagnostic(
            "path.unreadable", LEGACY_PROJECT_PATH,
            "legacy configuration path cannot be inspected safely",
        )]) from exc


def _safe_file(root: Path, relative: str) -> Optional[Path]:
    current = root
    for part in relative.split("/"):
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise ProjectConfigError([ProjectDiagnostic(
                "path.unreadable", relative, "path cannot be inspected safely")]) from exc
        if stat.S_ISLNK(info.st_mode):
            raise ProjectConfigError([ProjectDiagnostic(
                "path.symlink", relative, "configured files and ancestors must not be symlinks")])
    if not current.is_file():
        raise ProjectConfigError([ProjectDiagnostic(
            "file.type", relative, "configuration must be a regular file")])
    return current


def load_project(
    root: Path,
    schema_path: Path,
    *,
    module_names: Optional[Iterable[str]] = None,
    module_dependencies: Optional[Mapping[str, Iterable[str]]] = None,
) -> Optional[dict[str, Any]]:
    """Load ``.agents/project.json`` or return ``None`` when no config exists.

    Legacy ``.agents/project.md`` is rejected before any JSON read. Symlinked
    files or ancestors, duplicate keys, malformed JSON, schema failures, unsafe
    values, unknown modules, and missing dependencies raise
    :class:`ProjectConfigError`. This function never writes.
    """
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ProjectConfigError([ProjectDiagnostic(
            "root.invalid", ".", "repository root must be an existing non-symlink directory")])
    if _legacy_project_present(root):
        raise ProjectConfigError([ProjectDiagnostic("legacy.unsupported", LEGACY_PROJECT_PATH,
                                 "legacy project.md is unsupported; remove it before any project operation")])
    path = _safe_file(root, PROJECT_PATH)
    if path is None:
        return None
    value = _load_object(path, PROJECT_PATH)
    diagnostics = validate_project(
        value,
        schema_path,
        module_names=module_names,
        module_dependencies=module_dependencies,
    )
    if diagnostics:
        raise ProjectConfigError(diagnostics)
    for key in ROOT_KEYS:
        resolve_root(root, value, key)
    return value


def _safe_absolute_base(path: Path, field: str) -> Path:
    current = Path(path.anchor)
    parts = path.parts[1:]
    try:
        info = current.lstat()
    except OSError as exc:
        raise ProjectConfigError([ProjectDiagnostic(
            "path.base", field, "configured absolute base cannot be inspected safely")]) from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ProjectConfigError([ProjectDiagnostic(
            "path.base", field, "configured absolute base and ancestors must be non-symlink directories")])
    for part in parts:
        current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            raise ProjectConfigError([ProjectDiagnostic(
                "path.base", field, "configured absolute base cannot be inspected safely")]) from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ProjectConfigError([ProjectDiagnostic(
                "path.base", field, "configured absolute base and ancestors must be non-symlink directories")])
    return current


def _safe_resolved_path(base: Path, suffix: str, field: str) -> Path:
    current = base
    try:
        base_info = current.lstat()
    except OSError as exc:
        raise ProjectConfigError([ProjectDiagnostic(
            "path.base", field, "configured path base must exist and be inspectable")]) from exc
    if stat.S_ISLNK(base_info.st_mode) or not stat.S_ISDIR(base_info.st_mode):
        raise ProjectConfigError([ProjectDiagnostic(
            "path.base", field, "configured path base must be a non-symlink directory")])
    parts = suffix.split("/") if suffix else []
    for index, part in enumerate(parts):
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            return current.joinpath(*parts[index + 1:])
        except OSError as exc:
            raise ProjectConfigError([ProjectDiagnostic(
                "path.unreadable", field, "configured path cannot be inspected safely")]) from exc
        if stat.S_ISLNK(info.st_mode):
            raise ProjectConfigError([ProjectDiagnostic(
                "path.symlink", field, "configured path and every existing ancestor must not be a symlink")])
    return current


def resolve_root(root: Path, config: Mapping[str, Any], key: str) -> Optional[Path]:
    """Resolve one configured root without following symlinks or creating it."""
    if key not in ROOT_KEYS:
        raise ProjectConfigError(
            [ProjectDiagnostic("root.key", key, "root key is not recognized")])
    roots = config.get("roots")
    value = roots.get(key) if isinstance(roots, dict) else None
    if value is None:
        return None
    if (not _safe_relative(value)
            or any(token in value for token in ("$", "{", "}"))):
        raise ProjectConfigError([ProjectDiagnostic(
            "path.relative", f"roots.{key}", "root must be a safe repository-relative path")])
    field = f"roots.{key}"
    resolved = _safe_resolved_path(Path(root), value, field)
    try:
        info = resolved.lstat()
    except FileNotFoundError:
        return resolved
    except OSError as exc:
        raise ProjectConfigError([ProjectDiagnostic(
            "root.unreadable", field, "configured root cannot be inspected safely")]) from exc
    file_or_directory = key in {"adrs", "domain_context"}
    valid_type = (
        stat.S_ISDIR(info.st_mode)
        or file_or_directory and stat.S_ISREG(info.st_mode)
    )
    if not valid_type:
        expected = "regular file or directory" if file_or_directory else "directory"
        raise ProjectConfigError([ProjectDiagnostic(
            "root.type", field, f"existing configured root must be a {expected}")])
    return resolved


def resolve_repository(
    root: Path,
    config: Mapping[str, Any],
    repository_id: str,
    environ: Optional[Mapping[str, str]] = None,
) -> Path:
    """Resolve one repository map entry and require a safe local Git checkout.

    Environment expansion is allowed only for the entry's exact leading
    ``${UPPER_ENV}`` placeholder. Expanded values never appear in diagnostics.
    """
    repositories = config.get("repositories")
    entry = next((item for item in repositories if isinstance(item, dict) and item.get(
        "id") == repository_id), None) if isinstance(repositories, list) else None
    if entry is None:
        raise ProjectConfigError([ProjectDiagnostic(
            "repository.missing", "repositories", "repository ID is not configured")])
    value = entry.get("path")
    if value == ".":
        destination = _safe_resolved_path(
            Path(root), "", f"repositories.{repository_id}.path")
    else:
        match = ENV_PATH_RE.fullmatch(
            value) if isinstance(value, str) else None
        if match:
            raw_base = (environ if environ is not None else os.environ).get(
                match.group(1))
            if not raw_base or not Path(raw_base).is_absolute():
                raise ProjectConfigError([ProjectDiagnostic(
                    "repository.environment", f"repositories.{repository_id}.path", "configured environment variable must name an absolute directory")])
            safe_base = _safe_absolute_base(
                Path(raw_base), f"repositories.{repository_id}.path")
            destination = _safe_resolved_path(
                safe_base, match.group(2), f"repositories.{repository_id}.path")
        elif _safe_relative(value):
            destination = _safe_resolved_path(
                Path(root), value, f"repositories.{repository_id}.path")
        else:
            raise ProjectConfigError([ProjectDiagnostic(
                "repository.path", f"repositories.{repository_id}.path", "repository path syntax is invalid")])
    try:
        info = destination.lstat()
    except OSError as exc:
        raise ProjectConfigError([ProjectDiagnostic(
            "repository.checkout", f"repositories.{repository_id}.path", "configured repository must be an existing non-symlink Git checkout")]) from exc
    marker = destination / ".git"
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode) or not _lstat_exists(marker) or marker.is_symlink() or not (marker.is_dir() or marker.is_file()):
        raise ProjectConfigError([ProjectDiagnostic(
            "repository.checkout", f"repositories.{repository_id}.path", "configured repository must be an existing non-symlink Git checkout")])
    return destination

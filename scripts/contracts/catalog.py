"""Load and resolve source artifact contracts without activating them.

The functions in this module are source-only, read-only, and dependency-free.
They reject duplicate JSON keys, unknown catalog fields, unsafe paths, symlinks,
missing owner contracts, and assets outside their declared owner.  They do not
parse Markdown, evaluate JSON Schema, inspect project configuration, or change
v1 writer/consumer selection.
"""

from __future__ import annotations

import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Optional


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")
ROOT_KEYS = {"specs", "work", "adrs", "evidence", "domain_context"}
ROOT_MODES = {"fixed", "project", "colocated", "caller-selected"}
INDEX_ROW_RE = re.compile(r"^- \[[^]]+\]\(([^)]+)\) — (\S.*)\.$")
ENTRY_FIELDS = {
    "id", "format", "owner", "template", "schema", "lifecycle", "root",
    "path_patterns", "split", "writable_schema_version", "requires_modules",
    "variants",
}


class CatalogError(ValueError):
    """A catalog or pointer is malformed, unsafe, or cannot be resolved."""


@dataclass(frozen=True)
class ResolvedVariant:
    """Existing owner-local assets for one inactive artifact format variant."""

    id: str
    schema_version: int
    template: Optional[Path]
    schema: Optional[Path]
    lifecycle: Optional[str]
    requires_modules: tuple[str, ...]
    forbids_sections: tuple[str, ...]


@dataclass(frozen=True)
class ResolvedArtifact:
    """Existing source paths associated with one declared artifact contract."""

    id: str
    owner_directory: Path
    owner_contract: Path
    template: Optional[Path]
    schema: Optional[Path]
    variants: tuple[ResolvedVariant, ...] = ()


def _pairs_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CatalogError(f"duplicate key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    """Return one UTF-8 JSON object, rejecting duplicate keys at every depth.

    Args:
        path: File to read. The caller is responsible for choosing its trust root.

    Raises:
        CatalogError: The file is unreadable, malformed, recursive, contains a
            duplicate object key, or does not have an object root.
    """
    try:
        text = path.read_text(encoding="utf-8")
        value = json.loads(text, object_pairs_hook=_pairs_object)
    except CatalogError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise CatalogError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CatalogError(f"JSON root must be an object: {path}")
    return value


def _exact_fields(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CatalogError(f"{label} must be an object")
    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    if missing:
        raise CatalogError(f"{label} missing field: {missing[0]}")
    if unknown:
        raise CatalogError(f"{label} unknown field: {unknown[0]}")
    return value


def _name(value: Any, label: str) -> str:
    if not isinstance(value, str) or not NAME_RE.fullmatch(value):
        raise CatalogError(f"{label} must be a lowercase hyphenated name")
    return value


def _safe_relative(
    value: Any,
    label: str,
    allow_placeholders: bool = False,
    parent_prefix: int = 0,
) -> str:
    """Validate one portable path without accessing the filesystem."""
    invalid = (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or WINDOWS_DRIVE_RE.match(value) is not None
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    )
    if invalid:
        raise CatalogError(f"{label} must be a safe relative path")
    assert isinstance(value, str)
    raw_parts = value.split("/")
    leading_parents = 0
    while leading_parents < len(raw_parts) and raw_parts[leading_parents] == "..":
        leading_parents += 1
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or leading_parents > parent_prefix
        or leading_parents == len(raw_parts)
        or WINDOWS_DRIVE_RE.match(raw_parts[leading_parents]) is not None
        or any(part in ("", ".", "..") for part in raw_parts[leading_parents:])
    ):
        raise CatalogError(f"{label} must be a safe relative path")
    if not allow_placeholders and any("<" in part or ">" in part for part in path.parts):
        raise CatalogError(f"{label} must be a safe relative path")
    if allow_placeholders:
        for part in path.parts:
            stripped = re.sub(r"<[A-Za-z0-9-]+>", "value", part)
            if "<" in stripped or ">" in stripped or not stripped:
                raise CatalogError(
                    f"{label} must be a safe relative path pattern")
    return value


def _string_list(value: Any, label: str, names: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise CatalogError(f"{label} must be an array")
    result: list[str] = []
    for index, item in enumerate(value):
        if names:
            result.append(_name(item, f"{label}[{index}]"))
        elif not isinstance(item, str) or not item.strip():
            raise CatalogError(f"{label}[{index}] must be a non-empty string")
        else:
            result.append(item)
    if result != sorted(result) or len(result) != len(set(result)):
        raise CatalogError(f"{label} must be sorted and unique")
    return result


def validate_artifact_catalog(value: Any) -> dict[str, Any]:
    """Validate the TASK-202 artifact-catalog shape and deterministic ordering.

    This deliberately validates only the catalog contract. It is not a general
    JSON Schema evaluator and does not activate any declared artifact format.
    """
    root = _exact_fields(
        value, {"schema_version", "artifacts"}, "artifact catalog")
    if type(root["schema_version"]) is not int or root["schema_version"] != 2:
        raise CatalogError("artifact catalog schema_version must be 2")
    entries = root["artifacts"]
    if not isinstance(entries, list):
        raise CatalogError("artifact catalog artifacts must be an array")

    identifiers: list[str] = []
    for index, raw_entry in enumerate(entries):
        label = f"artifacts[{index}]"
        entry = _exact_fields(raw_entry, ENTRY_FIELDS, label)
        identifier = _name(entry["id"], f"{label}.id")
        if identifier in identifiers:
            raise CatalogError(f"duplicate artifact id: {identifier}")
        identifiers.append(identifier)
        if entry["format"] not in ("markdown", "json", "jsonl"):
            raise CatalogError(f"{label}.format is unsupported")

        owner = _exact_fields(
            entry["owner"], {"kind", "name"}, f"{label}.owner")
        if owner["kind"] not in ("skill", "module"):
            raise CatalogError(f"{label}.owner.kind must be skill or module")
        _name(owner["name"], f"{label}.owner.name")

        for field in ("template", "schema"):
            pointer = entry[field]
            if pointer is not None:
                _safe_relative(pointer, f"{label}.{field}")
        lifecycle = entry["lifecycle"]
        if lifecycle is not None:
            _name(lifecycle, f"{label}.lifecycle")

        location = _exact_fields(
            entry["root"], {"mode", "key", "fallback"}, f"{label}.root")
        mode = location["mode"]
        root_key = location["key"]
        fallback = location["fallback"]
        if not isinstance(mode, str) or mode not in ROOT_MODES:
            raise CatalogError(f"{label}.root.mode is unsupported")
        if root_key is not None and (
            not isinstance(root_key, str) or root_key not in ROOT_KEYS
        ):
            raise CatalogError(f"{label}.root.key is unsupported")
        if fallback is not None:
            _safe_relative(fallback, f"{label}.root.fallback")
        valid_root = (
            (mode == "fixed" and root_key is None and fallback is not None)
            or (mode in ("project", "caller-selected") and root_key is not None)
            or (mode == "colocated" and root_key is None and fallback is None)
        )
        if not valid_root:
            raise CatalogError(f"{label}.root combination is unsupported")

        patterns = entry["path_patterns"]
        if not isinstance(patterns, list) or not patterns:
            raise CatalogError(
                f"{label}.path_patterns must be a non-empty array")
        for pattern_index, pattern in enumerate(patterns):
            _safe_relative(
                pattern, f"{label}.path_patterns[{pattern_index}]", True)
        if patterns != sorted(patterns) or len(patterns) != len(set(patterns)):
            raise CatalogError(
                f"{label}.path_patterns must be sorted and unique")

        split = _exact_fields(
            entry["split"], {"mode", "warning_tokens"}, f"{label}.split")
        if split["mode"] not in ("never", "semantic"):
            raise CatalogError(f"{label}.split.mode is unsupported")
        warning = split["warning_tokens"]
        if warning is not None and (type(warning) is not int or warning < 1):
            raise CatalogError(
                f"{label}.split.warning_tokens must be null or a positive integer")
        version = entry["writable_schema_version"]
        if type(version) is not int or version < 1:
            raise CatalogError(
                f"{label}.writable_schema_version must be a positive integer")
        _string_list(entry["requires_modules"],
                     f"{label}.requires_modules", names=True)

        variants = entry["variants"]
        if not isinstance(variants, list):
            raise CatalogError(f"{label}.variants must be an array")
        variant_order: list[tuple[int, str]] = []
        variant_ids: list[str] = []
        for variant_index, variant_value in enumerate(variants):
            variant_label = f"{label}.variants[{variant_index}]"
            variant = _exact_fields(
                variant_value,
                {"id", "schema_version", "template", "schema", "lifecycle",
                 "requires_modules", "forbids_sections"},
                variant_label,
            )
            variant_id = _name(variant["id"], f"{variant_label}.id")
            variant_version = variant["schema_version"]
            if type(variant_version) is not int or variant_version < 1:
                raise CatalogError(
                    f"{variant_label}.schema_version must be a positive integer")
            for field in ("template", "schema"):
                pointer = variant[field]
                if pointer is not None:
                    _safe_relative(pointer, f"{variant_label}.{field}")
            variant_lifecycle = variant["lifecycle"]
            if variant_lifecycle is not None:
                _name(variant_lifecycle, f"{variant_label}.lifecycle")
            _string_list(variant["requires_modules"],
                         f"{variant_label}.requires_modules", names=True)
            _string_list(variant["forbids_sections"],
                         f"{variant_label}.forbids_sections")
            variant_order.append((variant_version, variant_id))
            variant_ids.append(variant_id)
        if len(variant_ids) != len(set(variant_ids)):
            raise CatalogError(f"{label}.variants has duplicate variant id")
        if variant_order != sorted(variant_order):
            raise CatalogError(
                f"{label}.variants must be ordered by schema_version and id")

    if identifiers != sorted(identifiers):
        raise CatalogError("artifact catalog entries must be sorted by id")
    return root


def _inside(path: Path, boundary: Path) -> bool:
    try:
        path.relative_to(boundary)
        return True
    except ValueError:
        return False


def _lexical_root_without_symlinks(repository_root: Path) -> Path:
    """Inspect a lexical absolute path from its canonical top-level anchor."""
    try:
        expanded = repository_root.expanduser()
        absolute = Path(os.path.abspath(str(expanded)))
        parts = absolute.parts
        if len(parts) < 2:
            raise CatalogError("repository root has no safe anchor")
        lexical_anchor = Path(absolute.anchor) / parts[1]
        current = lexical_anchor.resolve(strict=True)
        if not current.is_dir():
            raise CatalogError("repository root anchor is not a directory")
        for part in parts[2:]:
            current = current / part
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise CatalogError("repository root ancestor is a symlink")
    except CatalogError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise CatalogError(
            "repository root cannot be inspected safely") from exc
    return absolute


def _repository_boundary(repository_root: Path) -> Path:
    absolute = _lexical_root_without_symlinks(repository_root)
    try:
        root = absolute.resolve(strict=True)
        if not root.is_dir():
            raise CatalogError("repository root is not a directory")
    except CatalogError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise CatalogError(
            "repository root cannot be resolved safely") from exc
    return root


def _agents_boundary(root: Path) -> Path:
    agents = root / ".agents"
    try:
        if agents.is_symlink():
            raise CatalogError(".agents boundary is a symlink")
        if not agents.is_dir():
            raise CatalogError(".agents boundary is not a directory")
    except CatalogError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise CatalogError(
            ".agents boundary cannot be resolved safely") from exc
    return agents


def _resolve_existing(
    boundary: Path,
    relative: str,
    label: str,
    directory: bool = False,
) -> Path:
    _safe_relative(relative, label)
    candidate = boundary.joinpath(*PurePosixPath(relative).parts)
    try:
        if boundary.is_symlink():
            raise CatalogError(f"{label} boundary is a symlink")
        resolved_boundary = boundary.resolve(strict=True)
        current = boundary
        for part in PurePosixPath(relative).parts:
            current = current / part
            if current.is_symlink():
                raise CatalogError(f"{label} ancestor is a symlink")
        resolved = candidate.resolve(strict=False)
        if not _inside(resolved, resolved_boundary):
            raise CatalogError(f"{label} escapes its boundary")
        valid_kind = candidate.is_dir() if directory else candidate.is_file()
        if not valid_kind:
            expected = "directory" if directory else "file"
            raise CatalogError(f"{label} does not resolve to a {expected}")
    except CatalogError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise CatalogError(f"{label} cannot be resolved safely") from exc
    return resolved


def load_artifact_catalog(repository_root: Path) -> dict[str, Any]:
    """Load the additive source artifact catalog below ``repository_root``."""
    root = _repository_boundary(repository_root)
    agents = _agents_boundary(root)
    path = _resolve_existing(
        agents, "artifact-catalog.json", "artifact catalog")
    return validate_artifact_catalog(load_json(path))


def resolve_artifact_contracts(
    repository_root: Path,
    value: Optional[dict[str, Any]] = None,
) -> tuple[ResolvedArtifact, ...]:
    """Resolve owners and non-null assets, enforcing owner co-location.

    Null asset pointers explicitly mean that the corresponding owner-local v2
    contract is not published yet. No future path is guessed or resolved.
    """
    root = _repository_boundary(repository_root)
    agents = _agents_boundary(root)
    data = validate_artifact_catalog(
        value) if value is not None else load_artifact_catalog(root)
    resolved: list[ResolvedArtifact] = []
    for entry in data["artifacts"]:
        owner = entry["owner"]
        group = "skills" if owner["kind"] == "skill" else "modules"
        owner_relative = f"{group}/{owner['name']}"
        owner_directory = agents.joinpath(*PurePosixPath(owner_relative).parts)
        if owner_directory.is_symlink():
            raise CatalogError(
                f"artifact {entry['id']} owner traverses a symlink")
        owner_file = "SKILL.md" if owner["kind"] == "skill" else "MODULE.md"
        owner_contract = _resolve_existing(
            agents, f"{owner_relative}/{owner_file}", f"artifact {entry['id']} owner")
        owner_resolved = owner_contract.parent

        def resolve_asset(pointer: Optional[str], label: str) -> Optional[Path]:
            if pointer is None:
                return None
            path = _resolve_existing(agents, pointer, label)
            if not _inside(path, owner_resolved):
                raise CatalogError(f"{label} is outside owner")
            return path

        assets = {
            field: resolve_asset(
                entry[field], f"artifact {entry['id']} {field}")
            for field in ("template", "schema")
        }
        resolved_variants = tuple(
            ResolvedVariant(
                id=variant["id"],
                schema_version=variant["schema_version"],
                template=resolve_asset(
                    variant["template"],
                    f"artifact {entry['id']} variant {variant['id']} template"),
                schema=resolve_asset(
                    variant["schema"],
                    f"artifact {entry['id']} variant {variant['id']} schema"),
                lifecycle=variant["lifecycle"],
                requires_modules=tuple(variant["requires_modules"]),
                forbids_sections=tuple(variant["forbids_sections"]),
            )
            for variant in entry["variants"]
        )
        resolved.append(ResolvedArtifact(
            id=entry["id"],
            owner_directory=owner_resolved,
            owner_contract=owner_contract,
            template=assets["template"],
            schema=assets["schema"],
            variants=resolved_variants,
        ))
    return tuple(resolved)


def index_pointers(text: str) -> list[str]:
    """Extract safe pointer rows from the intent index.

    Each list row must contain one Markdown link and one short discriminative
    sentence. Links are relative to ``.agents/indexes`` and may move only to
    another path below ``.agents``.
    """
    pointers: list[str] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.startswith("- ["):
            continue
        match = INDEX_ROW_RE.fullmatch(line)
        if match is None:
            if ")" in line and " — " not in line:
                raise CatalogError(
                    f"index row {line_number} missing discriminative text")
            raise CatalogError(f"index row {line_number} is malformed")
        pointer, discriminator = match.groups()
        _safe_relative(pointer, "index pointer", parent_prefix=1)
        if len(discriminator) < 8:
            raise CatalogError(
                f"index row {line_number} has insufficient discriminative text")
        pointers.append(pointer)
    if pointers != sorted(pointers) or len(pointers) != len(set(pointers)):
        raise CatalogError("index pointers must be sorted and unique")
    return pointers


def resolve_repository_pointer(repository_root: Path, pointer: str) -> Path:
    """Resolve one intent-index link while confining it below ``.agents``."""
    _safe_relative(pointer, "index pointer", parent_prefix=1)
    root = _repository_boundary(repository_root)
    agents = _agents_boundary(root)
    indexes = _resolve_existing(
        agents, "indexes", "intent index directory", directory=True)
    parts = PurePosixPath(pointer).parts
    if parts[0] == "..":
        relative = PurePosixPath(*parts[1:]).as_posix()
        return _resolve_existing(agents, relative, "index pointer")
    return _resolve_existing(indexes, pointer, "index pointer")

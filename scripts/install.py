#!/usr/bin/env python3
"""Install Agentic SDLC Kit into an existing repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Optional, TextIO

try:
    from scripts.contracts.project import (
        ProjectConfigError,
        load_project,
        validate_project,
    )
# Direct ``python3 scripts/install.py`` invocation.
except ModuleNotFoundError:
    from contracts.project import ProjectConfigError, load_project, validate_project


KIT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_SCHEMA_VERSION = 2
MANIFEST_SCHEMA_VERSION = 2
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
MANIFEST_PATH = PurePosixPath(".agents/agentic-sdlc-kit.json")
CATALOG_PATH = PurePosixPath(".agents/kit-catalog.json")
TRANSACTION_PREFIX = ".agentic-sdlc-kit-"
TRANSACTION_MARKER = "agentic-sdlc-kit-transaction-v1"
MARKER_FILE = ".transaction-marker"
RECOVERY_FILE = "recovery.json"


class InstallerError(Exception):
    def __init__(self, message: str, code: int = 2) -> None:
        super().__init__(message)
        self.code = code


class TransactionFailed(Exception):
    pass


class TransactionInterrupted(Exception):
    pass


class RollbackIncomplete(Exception):
    def __init__(self, path: Path, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.path = path


class Action:
    def __init__(
        self,
        kind: str,
        name: str,
        source: Path,
        destination: Path,
        relative: str,
        status: str,
        source_kind: str,
        source_hash: str,
        expected_exists: bool,
        expected_kind: Optional[str],
        expected_hash: Optional[str],
        reason: str = "",
    ) -> None:
        self.kind = kind
        self.name = name
        self.source = source
        self.destination = destination
        self.relative = relative
        self.status = status
        self.source_kind = source_kind
        self.sha256 = source_hash
        self.expected_exists = expected_exists
        self.expected_kind = expected_kind
        self.expected_hash = expected_hash
        self.reason = reason


class Selection:
    def __init__(
        self,
        profile: str,
        skills: Iterable[str],
        modules: Iterable[str],
        dependencies: Iterable[tuple[str, str]],
        explicit_components: Iterable[str] = (),
    ) -> None:
        self.profile = profile
        self.skills = sorted(set(skills))
        self.modules = sorted(set(modules))
        self.dependencies = sorted(set(dependencies))
        self.explicit_components = sorted(set(explicit_components))


class AppliedChange:
    def __init__(
        self,
        destination: Path,
        staged: Path,
        relative: str,
        original: tuple[bool, Optional[str], Optional[str]],
        published_kind: str,
        published_hash: str,
        backup: Optional[Path] = None,
    ) -> None:
        self.destination = destination
        self.staged = staged
        self.relative = relative
        self.original = original
        self.published_kind = published_kind
        self.published_hash = published_hash
        self.backup = backup
        self.state = "staged"
        self.created_parents: list[Path] = []


FailureInjector = Optional[Callable[[str, str], None]]


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install catalog-selected SDLC components and engineering contract."
    )
    parser.add_argument("target", type=Path,
                        help="Path to an existing repository root.")
    parser.add_argument("--profile", help="Install a named catalog profile.")
    parser.add_argument(
        "--with",
        dest="with_components",
        action="append",
        default=[],
        metavar="COMPONENT",
        help="Add a catalog component; may be repeated or comma-separated.",
    )
    parser.add_argument(
        "--on-conflict",
        choices=("keep", "replace"),
        help="Explicit non-interactive decision for component conflicts.",
    )
    parser.add_argument(
        "--force-skills",
        action="store_true",
        help="Compatibility alias for --on-conflict replace.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the installation result without writing files.",
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Create .agents/project.json when absent, from safe defaults plus observed facts; never overwrites.",
    )
    return parser.parse_args(argv)


def _catalog_names(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise InstallerError(f"Invalid catalog: {field} must be an array")
    names = []
    for index, name in enumerate(value):
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            raise InstallerError(
                f"Invalid catalog: {field}[{index}] must be a kebab-case name"
            )
        if name in names:
            raise InstallerError(
                f"Invalid catalog: duplicate component {name!r}")
        names.append(name)
    return names


def _validate_dependency_graph(dependencies: dict[str, list[str]]) -> None:
    state: dict[str, int] = {}
    for root in sorted(dependencies):
        if state.get(root, 0):
            continue
        state[root] = 1
        stack = [(root, iter(sorted(dependencies[root])))]
        while stack:
            name, children = stack[-1]
            try:
                child = next(children)
            except StopIteration:
                state[name] = 2
                stack.pop()
                continue
            if state.get(child, 0) == 1:
                raise InstallerError(
                    "Invalid catalog: module dependency cycle")
            if state.get(child, 0) == 0:
                state[child] = 1
                stack.append((child, iter(sorted(dependencies[child]))))


def load_catalog(kit_root: Path) -> dict[str, Any]:
    path = _ensure_safe_source(kit_root, ".agents/kit-catalog.json")
    if not path.is_file():
        raise InstallerError(f"Catalog not found or unsafe: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise InstallerError(f"Invalid catalog {path}: {exc}") from exc
    required = {"schema_version", "kit_version",
                "skill_groups", "modules", "global_resources", "profiles"}
    if not isinstance(data, dict) or set(data) != required:
        raise InstallerError("Invalid catalog: missing or unknown root fields")
    if (
        type(data["schema_version"]) is not int
        or data["schema_version"] != CATALOG_SCHEMA_VERSION
    ):
        raise InstallerError(
            f"Invalid catalog: schema_version must be {CATALOG_SCHEMA_VERSION}"
        )
    if not isinstance(data["kit_version"], str) or not data["kit_version"].strip():
        raise InstallerError(
            "Invalid catalog: kit_version must be a non-empty string")

    groups = data["skill_groups"]
    if not isinstance(groups, dict) or set(groups) != {"core", "utilities", "optional"}:
        raise InstallerError(
            "Invalid catalog: missing or unknown skill groups")
    skills = []
    for group in ("core", "utilities", "optional"):
        skills.extend(_catalog_names(groups[group], f"skill_groups.{group}"))
    if len(skills) != len(set(skills)):
        raise InstallerError("Invalid catalog: duplicate skill component")

    global_resources = data["global_resources"]
    if not isinstance(global_resources, list) or not global_resources:
        raise InstallerError(
            "Invalid catalog: global_resources must be a non-empty array")
    seen_resources: set[str] = set()
    for index, relative in enumerate(global_resources):
        if not isinstance(relative, str) or relative in seen_resources:
            raise InstallerError(
                f"Invalid catalog: global_resources[{index}] is invalid")
        safe = _safe_relative(relative)
        if relative == MANIFEST_PATH.as_posix() or not (
                relative == "AGENTS.md" or relative.startswith(".agents/")):
            raise InstallerError(
                f"Invalid catalog: global_resources[{index}] is outside the managed namespace")
        source = _ensure_safe_source(kit_root, safe.as_posix())
        if not source.is_file():
            raise InstallerError(
                f"Invalid catalog: global resource is missing or unsafe: {relative}")
        seen_resources.add(relative)
    modules = data["modules"]
    if not isinstance(modules, list):
        raise InstallerError("Invalid catalog: modules must be an array")
    dependencies: dict[str, list[str]] = {}
    for index, module in enumerate(modules):
        field = f"modules[{index}]"
        if not isinstance(module, dict) or set(module) != {"name", "description", "depends_on"}:
            raise InstallerError(
                f"Invalid catalog: {field} has missing or unknown fields")
        name = module["name"]
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            raise InstallerError(f"Invalid catalog: {field}.name is invalid")
        if name in dependencies or name in skills:
            raise InstallerError(
                f"Invalid catalog: duplicate component {name!r}")
        if not isinstance(module["description"], str) or not module["description"].strip():
            raise InstallerError(
                f"Invalid catalog: {field}.description must be non-empty")
        dependencies[name] = _catalog_names(
            module["depends_on"], f"{field}.depends_on")
    module_names = set(dependencies)
    for name, required_modules in dependencies.items():
        unknown = sorted(set(required_modules) - module_names)
        if unknown:
            raise InstallerError(
                f"Invalid catalog: module {name!r} depends on unknown module {unknown[0]!r}"
            )
    _validate_dependency_graph(dependencies)

    profiles = data["profiles"]
    if not isinstance(profiles, dict) or "default" not in profiles:
        raise InstallerError("Invalid catalog: profiles must include default")
    normalized_profiles = {}
    for profile_name, profile in profiles.items():
        if not isinstance(profile_name, str) or not NAME_RE.fullmatch(profile_name):
            raise InstallerError("Invalid catalog: profile name is invalid")
        if not isinstance(profile, dict) or set(profile) != {"skills", "modules"}:
            raise InstallerError(
                f"Invalid catalog: profile {profile_name!r} has missing or unknown fields"
            )
        profile_skills = _catalog_names(
            profile["skills"], f"profiles.{profile_name}.skills")
        profile_modules = _catalog_names(
            profile["modules"], f"profiles.{profile_name}.modules")
        unknown = sorted(
            (set(profile_skills) - set(skills)
             ) | (set(profile_modules) - module_names)
        )
        if unknown:
            raise InstallerError(
                f"Invalid catalog: profile {profile_name!r} references unknown component {unknown[0]!r}"
            )
        normalized_profiles[profile_name] = {
            "skills": profile_skills,
            "modules": profile_modules,
        }

    data["_skills"] = skills
    data["_dependencies"] = dependencies
    data["_profiles"] = normalized_profiles
    return data


def _preflight_project_config(
    target: Path, kit_root: Path, catalog: dict[str, Any]
) -> None:
    """Reject unsupported or invalid project configuration before installation.

    The preflight is read-only and redacts project values. Installation never
    manages or records project configuration; only the explicit ``--init-config``
    flag may create it when absent (see :func:`init_project_config`).
    """
    schema = kit_root / ".agents" / "skills" / \
        "setup" / "assets" / "project.schema.json"
    try:
        load_project(
            target,
            schema,
            module_names=set(catalog["_dependencies"]),
            module_dependencies=catalog["_dependencies"],
        )
    except ProjectConfigError as exc:
        detail = "; ".join(
            f"{item.code} {item.field}: {item.message}" for item in exc.diagnostics
        )
        raise InstallerError(
            f"Project configuration preflight failed: {detail}") from exc


def _origin_default_branch(target: Path) -> Optional[str]:
    """Return the branch that ``origin/HEAD`` points to, or ``None``.

    Uses one read-only ``git symbolic-ref`` call without a shell. Local branch
    names are not treated as policy evidence.
    """
    prefix = "refs/remotes/origin/"
    try:
        proc = subprocess.run(
            ["git", "-C", str(target), "symbolic-ref", "--quiet",
             "refs/remotes/origin/HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    ref = proc.stdout.strip()
    if proc.returncode != 0 or not ref.startswith(prefix) or ref == prefix:
        return None
    return ref[len(prefix):]


def build_initial_project_config(
    target: Path, selection: Selection, catalog: dict[str, Any]
) -> dict[str, Any]:
    """Build a conservative ``.agents/project.json`` candidate for ``--init-config``.

    Starts from the setup template defaults and adds only directly observed
    facts: the ``origin/HEAD`` branch, an existing local pull-request template,
    and the selected installed modules whose dependencies are also selected.
    ``multi-repo`` is never enabled because it needs a confirmed repository map.
    Commit convention, tracker, approval rules, and optional roots stay at their
    neutral defaults; history or remotes are not policy evidence.
    """
    pull_request_template: Optional[str] = None
    for candidate in (
        ".github/pull_request_template.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        "docs/pull_request_template.md",
        "pull_request_template.md",
    ):
        path = target / candidate
        if path.is_file() and not path.is_symlink():
            pull_request_template = candidate
            break

    selected = set(selection.modules)
    dependencies = catalog.get("_dependencies", {})
    enabled = sorted(
        name for name in selected
        if name != "multi-repo" and set(dependencies.get(name, [])) <= selected
    )
    return {
        "schema_version": 2,
        "roots": {
            "specs": "specs",
            "work": ".work",
            "adrs": None,
            "evidence": "evidence" if "evidence" in enabled else None,
            "domain_context": None,
        },
        "repositories": [],
        "enabled_modules": enabled,
        "tracker": {"kind": "none", "location": None, "labels": {}},
        "agent": {"mode": "guided"},
        "review": {"mode": "risk-based"},
        "approval_policy": {"rules": []},
        "contribution": {
            "commit_mode": "discover",
            "base_branch": _origin_default_branch(target),
            "required_trailers": [],
            "pull_request_template": pull_request_template,
            "merge_strategy": "unknown",
        },
    }


def init_project_config(
    target: Path,
    kit_root: Path,
    selection: Selection,
    catalog: dict[str, Any],
    output_stream: TextIO,
    dry_run: bool = False,
) -> bool:
    """Create ``.agents/project.json`` only when it is absent (``--init-config``).

    The explicit flag is the user's approval to create the conservative
    candidate from :func:`build_initial_project_config`. An existing file, a
    symlink, or legacy ``.agents/project.md`` is never touched. The candidate
    is validated against the setup schema before any write, and the write uses
    exclusive creation so a concurrent file is never overwritten. The file is
    project-owned and is not recorded in the ownership manifest.

    Returns ``True`` when the file was created (or would be, in a dry run).
    """
    agents = target / ".agents"
    project = agents / "project.json"
    if os.path.lexists(agents / "project.md"):
        print("Config: skipped; legacy .agents/project.md is unsupported. "
              "Remove it, then run setup.", file=output_stream)
        return False
    if os.path.lexists(project):
        print("Config: kept existing .agents/project.json unchanged.",
              file=output_stream)
        return False

    config = build_initial_project_config(target, selection, catalog)
    schema = kit_root / ".agents" / "skills" / "setup" / "assets" / "project.schema.json"
    diagnostics = validate_project(
        config,
        schema,
        module_names=set(catalog["_dependencies"]),
        module_dependencies=catalog["_dependencies"],
    )
    if diagnostics:
        detail = "; ".join(f"{d.code} {d.field}" for d in diagnostics)
        print(f"Config: not created; candidate failed validation ({detail}).",
              file=output_stream)
        return False

    content = json.dumps(config, indent=2) + "\n"
    if dry_run:
        print("Config: would create .agents/project.json:", file=output_stream)
        print(content, end="", file=output_stream)
        return True

    _ensure_safe_destination(target, ".agents/project.json")
    agents.mkdir(exist_ok=True)
    descriptor = os.open(str(project), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(content)
    print("Config: created .agents/project.json "
          f"(base branch: {config['contribution']['base_branch'] or 'not detected'}; "
          f"enabled modules: {', '.join(config['enabled_modules']) or 'none'}). "
          "Review it, or refine it with the setup skill.", file=output_stream)
    return True


def _split_components(values: Iterable[str]) -> list[str]:
    result = []
    for value in values:
        result.extend(item.strip()
                      for item in value.split(",") if item.strip())
    return result


def _interactive_extras(
    catalog: dict[str, Any], input_stream: TextIO, output_stream: TextIO
) -> list[str]:
    default = catalog["_profiles"]["default"]
    selected = set(default["skills"]) | set(default["modules"])
    available = sorted(
        (set(catalog["_skills"]) | set(catalog["_dependencies"])) - selected
    )
    print("Available extras:", file=output_stream)
    if not available:
        print("- none", file=output_stream)
    else:
        for index, name in enumerate(available, 1):
            print(f"{index}. {name}", file=output_stream)
    instruction = "Select extras by exact name or number"
    if any(name.isdigit() for name in available):
        instruction += "; Use #N to select by index"
    print(
        f"{instruction} (comma-separated; blank for none): ",
        end="",
        file=output_stream,
    )
    output_stream.flush()
    answer = input_stream.readline()
    if answer == "":
        raise InstallerError("Interactive selection aborted", 1)
    extras = []
    for token in _split_components([answer]):
        if token in available:
            extras.append(token)
            continue
        index_token = token[1:] if token.startswith("#") else token
        if index_token.isdigit() and 1 <= int(index_token) <= len(available):
            extras.append(available[int(index_token) - 1])
        else:
            raise InstallerError(f"Unknown interactive component: {token!r}")
    return extras


def resolve_selection(
    catalog: dict[str, Any],
    profile_name: Optional[str],
    requested: Iterable[str],
    interactive: bool,
    input_stream: TextIO,
    output_stream: TextIO,
) -> Selection:
    profile = profile_name or "default"
    profiles = catalog["_profiles"]
    if profile not in profiles:
        raise InstallerError(f"Unknown catalog profile: {profile!r}")
    extras = _split_components(requested)
    if interactive and profile_name is None and not extras:
        extras = _interactive_extras(catalog, input_stream, output_stream)
    all_skills = set(catalog["_skills"])
    all_modules = set(catalog["_dependencies"])
    for name in extras:
        if name not in all_skills and name not in all_modules:
            raise InstallerError(f"Unknown catalog component: {name!r}")

    skills = set(profiles[profile]["skills"])
    initial_modules = set(profiles[profile]["modules"])
    skills.update(name for name in extras if name in all_skills)
    initial_modules.update(name for name in extras if name in all_modules)
    modules = set(initial_modules)
    expanded = set()
    pending = sorted(initial_modules)
    visited = set()
    dependencies = catalog["_dependencies"]
    while pending:
        name = pending.pop(0)
        if name in visited:
            continue
        visited.add(name)
        for dependency in sorted(dependencies[name]):
            if dependency not in initial_modules:
                expanded.add((name, dependency))
            if dependency not in modules:
                modules.add(dependency)
                pending.append(dependency)
                pending.sort()
    return Selection(profile, skills, modules, expanded, extras)


def _safe_relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise InstallerError(f"Unsafe relative path: {value!r}")
    return path


def _reject_symlink(path: Path) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise InstallerError(f"Cannot inspect path {path}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode):
        raise InstallerError(f"Unsafe symlink in path: {path}")


def normalize_target(path: Path) -> Path:
    expanded = path.expanduser()
    if expanded.is_absolute():
        current = Path(expanded.anchor)
        parts = expanded.parts[1:]
    else:
        current = Path.cwd()
        parts = expanded.parts
        for ancestor in reversed((current, *current.parents)):
            _reject_symlink(ancestor)
    for part in parts:
        if part in ("", "."):
            continue
        if part == "..":
            current = current.parent
            continue
        current = current / part
        _reject_symlink(current)
    absolute = Path(os.path.abspath(str(expanded)))
    for current in reversed((absolute, *absolute.parents)):
        _reject_symlink(current)
    return absolute


def _ensure_safe_destination(target: Path, relative: str) -> Path:
    path = _safe_relative(relative)
    current = target
    for index, part in enumerate(path.parts):
        current = current / part
        if current.is_symlink():
            raise InstallerError(f"Unsafe symlink in target path: {current}")
        if index < len(path.parts) - 1 and current.exists() and not current.is_dir():
            raise InstallerError(
                f"Unsafe non-directory in target path: {current}")
    return target.joinpath(*path.parts)


def _ensure_safe_source(root: Path, relative: str) -> Path:
    if root.is_symlink():
        raise InstallerError(f"Unsafe symlink in source path: {root}")
    path = _safe_relative(relative)
    current = root
    for index, part in enumerate(path.parts):
        current = current / part
        if current.is_symlink():
            raise InstallerError(f"Unsafe symlink in source path: {current}")
        if index < len(path.parts) - 1 and current.exists() and not current.is_dir():
            raise InstallerError(
                f"Unsafe non-directory in source path: {current}")
    return current


def _path_kind(path: Path) -> str:
    info = path.lstat()
    if stat.S_ISREG(info.st_mode):
        return "file"
    if stat.S_ISDIR(info.st_mode):
        return "dir"
    if stat.S_ISLNK(info.st_mode):
        raise InstallerError(
            f"Unsafe symlink in source or destination: {path}")
    raise InstallerError(f"Unsupported filesystem entry: {path}")


def _tree_entries(path: Path) -> list[tuple[str, str, Path]]:
    if path.is_symlink():
        raise InstallerError(
            f"Unsafe symlink in source or destination: {path}")
    if path.is_file():
        return [("file", "", path)]
    if not path.is_dir():
        raise InstallerError(f"Unsupported filesystem entry: {path}")
    entries = []

    def raise_walk_error(error: OSError) -> None:
        raise error

    for root, directories, files in os.walk(
        str(path), followlinks=False, onerror=raise_walk_error
    ):
        root_path = Path(root)
        for name in directories:
            item = root_path / name
            if item.is_symlink():
                raise InstallerError(
                    f"Unsafe symlink in source or destination: {item}")
            entries.append(("dir", item.relative_to(path).as_posix(), item))
        for name in files:
            item = root_path / name
            if item.is_symlink():
                raise InstallerError(
                    f"Unsafe symlink in source or destination: {item}")
            if not item.is_file():
                raise InstallerError(f"Unsupported filesystem entry: {item}")
            entries.append(("file", item.relative_to(path).as_posix(), item))
    return sorted(entries, key=lambda entry: (entry[1], entry[0]))


def hash_path(path: Path) -> str:
    entries = _tree_entries(path)
    digest = hashlib.sha256()
    if len(entries) == 1 and entries[0][1] == "":
        digest.update(b"root:file\0")
        digest.update(path.read_bytes())
        return digest.hexdigest()
    digest.update(b"root:dir\0")
    for kind, relative, entry in entries:
        digest.update(kind.encode("ascii") + b"\0")
        digest.update(relative.encode("utf-8") + b"\0")
        if kind == "file":
            digest.update(hashlib.sha256(entry.read_bytes()).digest())
    return digest.hexdigest()


def _path_state(path: Path) -> tuple[bool, Optional[str], Optional[str]]:
    if path.is_symlink():
        raise InstallerError(
            f"Unsafe symlink in source or destination: {path}")
    if not path.exists():
        return False, None, None
    return True, _path_kind(path), hash_path(path)


def _component_path(kind: str, name: str) -> str:
    plural = "skills" if kind == "skill" else "modules"
    return f".agents/{plural}/{name}"


def load_manifest(target: Path) -> dict[str, Any]:
    destination = _ensure_safe_destination(target, MANIFEST_PATH.as_posix())
    if not destination.exists():
        return {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "kit_version": "",
            "request": {"profile": "default", "explicit_components": []},
            "components": [],
            "global_resources": [],
        }
    if not destination.is_file():
        raise InstallerError(f"Invalid ownership manifest: {destination}")
    try:
        data = json.loads(destination.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise InstallerError(f"Invalid ownership manifest: {exc}") from exc
    if not isinstance(data, dict):
        raise InstallerError(
            "Invalid ownership manifest root must be an object")
    fields = {"schema_version", "kit_version",
              "request", "components", "global_resources"}
    missing = sorted(fields - set(data))
    unknown = sorted(set(data) - fields)
    if missing:
        raise InstallerError(
            f"Invalid ownership manifest missing root field: {missing[0]}")
    if unknown:
        raise InstallerError(
            f"Invalid ownership manifest unknown root field: {unknown[0]}")
    if type(data["schema_version"]) is not int or data["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise InstallerError(
            "Invalid ownership manifest schema_version must be "
            f"{MANIFEST_SCHEMA_VERSION}")
    if not isinstance(data["kit_version"], str) or not data["kit_version"].strip():
        raise InstallerError(
            "Invalid ownership manifest kit_version must be a non-empty string")
    request = data["request"]
    if (not isinstance(request, dict)
            or set(request) != {"profile", "explicit_components"}
            or not isinstance(request["profile"], str)
            or not NAME_RE.fullmatch(request["profile"])
            or not isinstance(request["explicit_components"], list)
            or any(not isinstance(item, str) or not NAME_RE.fullmatch(item)
                   for item in request["explicit_components"])
            or len(request["explicit_components"])
            != len(set(request["explicit_components"]))):
        raise InstallerError("Invalid ownership manifest request")
    components = data["components"]
    if not isinstance(components, list):
        raise InstallerError(
            "Invalid ownership manifest components must be an array")
    seen = set()
    for index, item in enumerate(components):
        label = f"components[{index}]"
        if not isinstance(item, dict) or set(item) != {
                "kind", "name", "path", "ownership", "sha256"}:
            raise InstallerError(
                f"Invalid ownership manifest {label} has missing or unknown fields")
        kind, name, ownership = item["kind"], item["name"], item["ownership"]
        if kind not in ("skill", "module"):
            raise InstallerError(f"Invalid ownership manifest {label}.kind")
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            raise InstallerError(f"Invalid ownership manifest {label}.name")
        if ownership not in ("managed", "project-owned"):
            raise InstallerError(
                f"Invalid ownership manifest {label}.ownership")
        expected = _component_path(kind, name)
        if item["path"] != expected or not isinstance(item["path"], str):
            raise InstallerError(f"Invalid ownership manifest {label}.path")
        if not isinstance(item["sha256"], str) or not HASH_RE.fullmatch(item["sha256"]):
            raise InstallerError(f"Invalid ownership manifest {label}.sha256")
        if (kind, name) in seen:
            raise InstallerError(f"Duplicate ownership manifest {label}")
        seen.add((kind, name))
        _ensure_safe_destination(target, expected)
    resources = data["global_resources"]
    if not isinstance(resources, list):
        raise InstallerError(
            "Invalid ownership manifest global_resources must be an array")
    seen_resources = set()
    for index, item in enumerate(resources):
        label = f"global_resources[{index}]"
        if not isinstance(item, dict) or set(item) != {"path", "ownership", "sha256"}:
            raise InstallerError(
                f"Invalid ownership manifest {label} has missing or unknown fields")
        path = item["path"]
        if (not isinstance(path, str)
                or path == MANIFEST_PATH.as_posix()
                or not (path == "AGENTS.md" or path.startswith(".agents/"))
                or path in seen_resources):
            raise InstallerError(f"Invalid ownership manifest {label}.path")
        if item["ownership"] not in ("managed", "project-owned"):
            raise InstallerError(
                f"Invalid ownership manifest {label}.ownership")
        if not isinstance(item["sha256"], str) or not HASH_RE.fullmatch(item["sha256"]):
            raise InstallerError(f"Invalid ownership manifest {label}.sha256")
        seen_resources.add(path)
        _ensure_safe_destination(target, path)
    return data


def _prior_component_map(manifest: dict[str, Any]) -> dict[tuple[str, str], dict[str, str]]:
    return {
        (item["kind"], item["name"]): dict(item)
        for item in manifest["components"]
    }


def _classify_action(
    kind: str,
    name: str,
    source: Path,
    destination: Path,
    relative: str,
    prior_hash: Optional[str],
) -> Action:
    source_kind = _path_kind(source)
    source_hash = hash_path(source)
    expected = _path_state(destination)
    if not expected[0]:
        status, reason = "copy", ""
    elif expected[1:] == (source_kind, source_hash):
        status, reason = (
            "unchanged" if prior_hash is not None else "adopt"), ""
    elif prior_hash is not None and expected[2] == prior_hash:
        status, reason = "update", ""
    else:
        status = "conflict"
        reason = "modified managed content" if prior_hash is not None else "unknown content"
    return Action(
        kind,
        name,
        source,
        destination,
        relative,
        status,
        source_kind,
        source_hash,
        expected[0],
        expected[1],
        expected[2],
        reason,
    )


def preflight(
    target: Path,
    kit_root: Path,
    catalog: dict[str, Any],
    selection: Selection,
    previous: dict[str, Any],
) -> tuple[list[Action], Action, Action]:
    prior = _prior_component_map(previous)
    actions = []
    for kind, names in (("skill", selection.skills), ("module", selection.modules)):
        for name in names:
            relative = _component_path(kind, name)
            source = _ensure_safe_source(kit_root, relative)
            if not source.is_dir():
                raise InstallerError(
                    f"Catalog-selected {kind} source is missing or unsafe: {source}"
                )
            destination = _ensure_safe_destination(target, relative)
            item = prior.get((kind, name))
            actions.append(
                _classify_action(
                    kind,
                    name,
                    source,
                    destination,
                    relative,
                    item["sha256"] if item else None,
                )
            )

    source_agents = _ensure_safe_source(kit_root, "AGENTS.md")
    if not source_agents.is_file():
        raise InstallerError(
            f"AGENTS.md source is missing or unsafe: {source_agents}")
    agents_destination = _ensure_safe_destination(target, "AGENTS.md")
    managed = {item["path"]: item["sha256"]
               for item in previous["global_resources"]
               if item.get("ownership") == "managed"}
    prior_agents_hash = managed.get("AGENTS.md")
    agents = _classify_action(
        "file",
        "AGENTS.md",
        source_agents,
        agents_destination,
        "AGENTS.md",
        prior_agents_hash,
    )
    if agents.expected_exists and prior_agents_hash is None:
        agents.status = "manual-merge"
        agents.reason = "unmanaged AGENTS.md requires semantic merge"
    elif agents.status == "conflict":
        agents.status = "manual-merge"
        agents.reason = "semantic merge required"

    source_catalog = _ensure_safe_source(kit_root, CATALOG_PATH.as_posix())
    if not source_catalog.is_file():
        raise InstallerError(
            f"Catalog source is missing or unsafe: {source_catalog}")
    catalog_file = _classify_action(
        "file",
        "kit-catalog",
        source_catalog,
        _ensure_safe_destination(target, CATALOG_PATH.as_posix()),
        CATALOG_PATH.as_posix(),
        managed.get(CATALOG_PATH.as_posix()),
    )
    declared = set(catalog["global_resources"])
    for relative in sorted(declared - {"AGENTS.md", CATALOG_PATH.as_posix()}):
        source = _ensure_safe_source(kit_root, relative)
        if not source.is_file():
            raise InstallerError(
                f"Global resource source is missing or unsafe: {source}")
        actions.append(_classify_action(
            "global", relative, source, _ensure_safe_destination(
                target, relative),
            relative, managed.get(relative)))
    return actions, agents, catalog_file


def _resolve_conflicts(
    actions: list[Action],
    policy: Optional[str],
    interactive: bool,
    input_stream: TextIO,
    output_stream: TextIO,
) -> bool:
    conflicts = [action for action in actions if action.status == "conflict"]
    if not conflicts:
        return True
    print("Component conflicts:", file=output_stream)
    for action in conflicts:
        print(f"- {action.relative}: {action.reason}", file=output_stream)
    if policy:
        for action in conflicts:
            action.status = policy
        return True
    if not interactive:
        print("Installation stopped; rerun with --on-conflict keep|replace.",
              file=output_stream)
        return False
    for action in conflicts:
        print(
            f"Conflict at {action.relative}. Choose keep, replace, or abort: ",
            end="",
            file=output_stream,
        )
        output_stream.flush()
        decision = input_stream.readline().strip().lower()
        if decision in ("", "abort"):
            print("Installation aborted; no files changed.", file=output_stream)
            return False
        if decision not in ("keep", "replace"):
            print("Invalid conflict decision; no files changed.", file=output_stream)
            return False
        action.status = decision
    return True


def _manifest_data(
    catalog: dict[str, Any],
    previous: dict[str, Any],
    selection: Selection,
    actions: list[Action],
    agents: Action,
    catalog_file: Action,
) -> dict[str, Any]:
    components = _prior_component_map(previous)
    for action in actions:
        if action.kind == "global":
            continue
        key = (action.kind, action.name)
        if action.status == "keep":
            if action.expected_exists and action.expected_hash is not None:
                components[key] = {
                    "kind": action.kind, "name": action.name,
                    "path": action.relative, "ownership": "project-owned",
                    "sha256": action.expected_hash,
                }
        else:
            components[key] = {
                "kind": action.kind, "name": action.name,
                "path": action.relative, "ownership": "managed",
                "sha256": action.sha256,
            }
    resources = {
        item["path"]: dict(item) for item in previous["global_resources"]
    }
    for action in [
        *[item for item in actions if item.kind == "global"],
        catalog_file, agents,
    ]:
        if action.status == "manual-merge":
            if action.expected_exists and action.expected_hash is not None:
                resources[action.relative] = {
                    "path": action.relative, "ownership": "project-owned",
                    "sha256": action.expected_hash,
                }
        else:
            resources[action.relative] = {
                "path": action.relative, "ownership": "managed",
                "sha256": action.sha256,
            }
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "kit_version": catalog["kit_version"],
        "request": {
            "profile": selection.profile,
            "explicit_components": selection.explicit_components,
        },
        "components": sorted(
            components.values(), key=lambda item: (item["kind"], item["name"])),
        "global_resources": sorted(
            resources.values(), key=lambda item: item["path"]),
    }


def _manifest_bytes(data: dict[str, Any]) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _expected_file_hash(content: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(b"root:file\0")
    digest.update(content)
    return digest.hexdigest()


def _recovery_data() -> dict[str, Any]:
    return {
        "marker": TRANSACTION_MARKER,
        "state": "staging",
        "current_path": None,
        "backups": [],
        "publications": [],
    }


def _recovery_record(change: AppliedChange, original: bool) -> dict[str, str]:
    kind = change.original[1] if original else change.published_kind
    sha256 = change.original[2] if original else change.published_hash
    return {
        "path": change.relative,
        "type": str(kind),
        "sha256": str(sha256),
    }


def _write_recovery(transaction_root: Path, data: dict[str, Any]) -> None:
    temporary = transaction_root / f"{RECOVERY_FILE}.tmp"
    destination = transaction_root / RECOVERY_FILE
    temporary.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(str(temporary), str(destination))


def _try_write_recovery(transaction_root: Path, data: dict[str, Any]) -> None:
    try:
        _write_recovery(transaction_root, data)
    except Exception:
        pass


def _validate_recovery(data: Any) -> dict[str, Any]:
    fields = {"marker", "state", "current_path", "backups", "publications"}
    if not isinstance(data, dict) or set(data) != fields:
        raise ValueError("invalid recovery fields")
    if data["marker"] != TRANSACTION_MARKER:
        raise ValueError("invalid recovery marker")
    if not isinstance(data["state"], str):
        raise ValueError("invalid recovery state")
    current = data["current_path"]
    if current is not None:
        if not isinstance(current, str):
            raise ValueError("invalid recovery path")
        _safe_relative(current)
    for collection in ("backups", "publications"):
        if not isinstance(data[collection], list):
            raise ValueError(f"invalid recovery {collection}")
        for record in data[collection]:
            if not isinstance(record, dict) or set(record) != {"path", "type", "sha256"}:
                raise ValueError("invalid recovery record")
            if not isinstance(record["path"], str):
                raise ValueError("invalid recovery record path")
            _safe_relative(record["path"])
            if record["type"] not in ("file", "dir"):
                raise ValueError("invalid recovery record type")
            if not isinstance(record["sha256"], str) or not HASH_RE.fullmatch(record["sha256"]):
                raise ValueError("invalid recovery record hash")
    return data


def _abandoned_transactions(target: Path) -> list[tuple[Path, str]]:
    abandoned = []
    for path in sorted(target.iterdir()):
        if (
            not path.name.startswith(TRANSACTION_PREFIX)
            or path.is_symlink()
            or not path.is_dir()
        ):
            continue
        marker = path / MARKER_FILE
        try:
            if (
                marker.is_symlink()
                or not stat.S_ISREG(marker.lstat().st_mode)
                or marker.read_text(encoding="utf-8") != TRANSACTION_MARKER + "\n"
            ):
                continue
        except (OSError, UnicodeError):
            continue
        metadata = path / RECOVERY_FILE
        if not metadata.is_file():
            abandoned.append((path, "metadata missing"))
            continue
        try:
            data = _validate_recovery(json.loads(
                metadata.read_text(encoding="utf-8")))
            summary = f"state={data['state']}"
            if data["current_path"] is not None:
                summary += f", current={data['current_path']}"
        except (OSError, UnicodeError, json.JSONDecodeError, RecursionError, ValueError, InstallerError):
            summary = "metadata corrupt"
        abandoned.append((path, summary))
    return abandoned


def _stage_action(action: Action, stage_root: Path) -> Path:
    staged = stage_root / action.relative
    staged.parent.mkdir(parents=True, exist_ok=True)
    if action.source_kind == "dir":
        shutil.copytree(action.source, staged)
    else:
        shutil.copy2(action.source, staged)
    if _path_kind(staged) != action.source_kind or hash_path(staged) != action.sha256:
        raise InstallerError(
            f"Staged content does not match plan: {action.relative}", 1)
    return staged


def _create_parents(change: AppliedChange, target: Path) -> None:
    missing = []
    current = change.destination.parent
    while current != target and not current.exists():
        missing.append(current)
        current = current.parent
    change.created_parents = list(reversed(missing))
    for directory in change.created_parents:
        directory.mkdir()


def _verify_expected(change: AppliedChange) -> None:
    if _path_state(change.destination) != change.original:
        raise InstallerError(
            f"Destination changed after preflight: {change.relative}", 1)


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def _rollback(
    changes: list[AppliedChange],
    transaction_root: Path,
    target: Path,
    recovery: dict[str, Any],
    failure_injector: FailureInjector,
) -> None:
    errors = []
    recovery["state"] = "rollback"
    for change in reversed(changes):
        recovery["current_path"] = change.relative
        _try_write_recovery(transaction_root, recovery)
        try:
            state = _path_state(change.destination)
            published = (True, change.published_kind, change.published_hash)
            if state == published:
                _remove_path(change.destination)
                state = (False, None, None)
            elif state != (False, None, None) and state != change.original:
                raise InstallerError(
                    f"destination cannot be rolled back: {change.relative}")

            if change.backup is not None and change.backup.exists():
                if state != (False, None, None):
                    raise InstallerError(
                        f"destination blocks restore: {change.relative}")
                if failure_injector:
                    failure_injector("before-restore", change.relative)
                os.replace(str(change.backup), str(change.destination))
                change.state = "restored"
            elif change.original[0] and state != change.original:
                raise InstallerError(f"backup unavailable: {change.relative}")

            for directory in reversed(change.created_parents):
                if directory.is_dir() and not any(directory.iterdir()):
                    directory.rmdir()
        except Exception as exc:
            errors.append(f"{change.relative}: {type(exc).__name__}: {exc}")
        except KeyboardInterrupt:
            errors.append(
                f"{change.relative}: KeyboardInterrupt during rollback")
    if errors:
        recovery["state"] = "rollback-incomplete"
        _try_write_recovery(transaction_root, recovery)
        raise RollbackIncomplete(transaction_root, errors)
    recovery["state"] = "cleanup"
    recovery["current_path"] = None
    _try_write_recovery(transaction_root, recovery)
    try:
        shutil.rmtree(transaction_root)
    except OSError as exc:
        raise RollbackIncomplete(
            transaction_root, [f"cleanup: {exc}"]) from exc


def apply_transaction(
    target: Path,
    actions: list[Action],
    agents: Action,
    catalog_file: Action,
    manifest: dict[str, Any],
    failure_injector: FailureInjector = None,
) -> None:
    write_actions = [
        action for action in actions if action.status in ("copy", "replace", "update")
    ]
    if agents.status in ("copy", "update"):
        write_actions.append(agents)
    if catalog_file.status in ("copy", "replace", "update"):
        write_actions.append(catalog_file)
    manifest_destination = _ensure_safe_destination(
        target, MANIFEST_PATH.as_posix())
    manifest_content = _manifest_bytes(manifest)
    manifest_state = _path_state(manifest_destination)
    manifest_hash = _expected_file_hash(manifest_content)
    manifest_changed = manifest_state != (True, "file", manifest_hash)
    if not write_actions and not manifest_changed:
        return

    transaction_root = Path(
        tempfile.mkdtemp(prefix=TRANSACTION_PREFIX, dir=str(target))
    )
    changes: list[AppliedChange] = []
    recovery = _recovery_data()
    try:
        (transaction_root / MARKER_FILE).write_text(
            TRANSACTION_MARKER + "\n", encoding="utf-8"
        )
        _try_write_recovery(transaction_root, recovery)
        stage_root = transaction_root / "stage"
        backup_root = transaction_root / "backup"
        for action in write_actions:
            if failure_injector:
                failure_injector("before-stage", action.relative)
            staged = _stage_action(action, stage_root)
            changes.append(
                AppliedChange(
                    action.destination,
                    staged,
                    action.relative,
                    (action.expected_exists,
                     action.expected_kind, action.expected_hash),
                    action.source_kind,
                    action.sha256,
                )
            )
        if manifest_changed:
            staged_manifest = stage_root / MANIFEST_PATH
            staged_manifest.parent.mkdir(parents=True, exist_ok=True)
            staged_manifest.write_bytes(manifest_content)
            if hash_path(staged_manifest) != manifest_hash:
                raise InstallerError(
                    "Staged ownership manifest hash mismatch", 1)
            changes.append(
                AppliedChange(
                    manifest_destination,
                    staged_manifest,
                    MANIFEST_PATH.as_posix(),
                    manifest_state,
                    "file",
                    manifest_hash,
                )
            )
        if failure_injector:
            failure_injector("after-staging", str(transaction_root))

        for change in changes:
            is_manifest = change.relative == MANIFEST_PATH.as_posix()
            if is_manifest and failure_injector:
                failure_injector("before-manifest", change.relative)
            if failure_injector:
                failure_injector("before-write", change.relative)
            _verify_expected(change)
            _create_parents(change, target)
            recovery["state"] = "manifest" if is_manifest else "publishing"
            recovery["current_path"] = change.relative
            _try_write_recovery(transaction_root, recovery)
            if change.original[0]:
                change.backup = backup_root / change.relative
                change.backup.parent.mkdir(parents=True, exist_ok=True)
                os.replace(str(change.destination), str(change.backup))
                change.state = "backed-up"
                recovery["backups"].append(_recovery_record(change, True))
                _try_write_recovery(transaction_root, recovery)
                if failure_injector:
                    failure_injector("after-backup", change.relative)
            os.replace(str(change.staged), str(change.destination))
            change.state = "published"
            recovery["publications"].append(_recovery_record(change, False))
            _try_write_recovery(transaction_root, recovery)
            if failure_injector:
                failure_injector("after-publish", change.relative)

        recovery["state"] = "cleanup"
        recovery["current_path"] = None
        _try_write_recovery(transaction_root, recovery)
        if failure_injector:
            failure_injector("before-cleanup", str(transaction_root))
    except KeyboardInterrupt as exc:
        _rollback(changes, transaction_root, target,
                  recovery, failure_injector)
        raise TransactionInterrupted("KeyboardInterrupt") from exc
    except SystemExit:
        _rollback(changes, transaction_root, target,
                  recovery, failure_injector)
        raise
    except Exception as exc:
        _rollback(changes, transaction_root, target,
                  recovery, failure_injector)
        raise TransactionFailed(f"{type(exc).__name__}: {exc}") from exc
    try:
        shutil.rmtree(transaction_root)
    except OSError as exc:
        recovery["state"] = "rollback-incomplete"
        _try_write_recovery(transaction_root, recovery)
        raise RollbackIncomplete(
            transaction_root, [f"cleanup: {exc}"]) from exc


def _print_selection(selection: Selection, output_stream: TextIO) -> None:
    print(f"Profile: {selection.profile}", file=output_stream)
    print("Final selection:", file=output_stream)
    print(f"- Skills: {', '.join(selection.skills) or 'none'}",
          file=output_stream)
    print(
        f"- Modules: {', '.join(selection.modules) or 'none'}", file=output_stream)
    if selection.dependencies:
        details = ", ".join(
            f"{component} -> {dependency}"
            for component, dependency in selection.dependencies
        )
        print(f"Dependencies expanded: {details}", file=output_stream)
    else:
        print("Dependencies expanded: none", file=output_stream)


def main(
    argv: Optional[list[str]] = None,
    *,
    kit_root: Path = KIT_ROOT,
    input_stream: Optional[TextIO] = None,
    output_stream: Optional[TextIO] = None,
    interactive: Optional[bool] = None,
    failure_injector: FailureInjector = None,
) -> int:
    input_stream = input_stream if input_stream is not None else sys.stdin
    output_stream = output_stream if output_stream is not None else sys.stdout
    try:
        args = parse_args(argv)
        target = normalize_target(args.target)
        if not target.is_dir():
            raise InstallerError(
                f"Target is not an existing directory: {target}")
        if not (target / ".git").exists():
            raise InstallerError(
                f"Target does not appear to be a repository root: {target}")
        abandoned = _abandoned_transactions(target)
        if abandoned:
            details = "; ".join(
                f"{path} ({summary})" for path, summary in abandoned
            )
            raise InstallerError(
                f"Abandoned transaction requires manual recovery: {details}", 1
            )
        if args.force_skills and args.on_conflict not in (None, "replace"):
            raise InstallerError(
                "--force-skills conflicts with --on-conflict keep")
        policy = "replace" if args.force_skills else args.on_conflict
        tty = input_stream.isatty() if interactive is None else interactive
        catalog = load_catalog(Path(kit_root))
        _preflight_project_config(target, Path(kit_root), catalog)
        selection = resolve_selection(
            catalog,
            args.profile,
            args.with_components,
            tty,
            input_stream,
            output_stream,
        )
        _print_selection(selection, output_stream)
        previous = load_manifest(target)
        actions, agents, catalog_file = preflight(
            target, Path(kit_root), catalog, selection, previous
        )
        selectable_actions = actions + [catalog_file]
        conflicts = [
            action for action in selectable_actions if action.status == "conflict"]
        print(f"Target: {target}", file=output_stream)
        for action in actions:
            print(f"- {action.status}: {action.relative}", file=output_stream)
        print(f"- {catalog_file.status}: {catalog_file.relative}",
              file=output_stream)
        print(f"- {agents.status}: AGENTS.md", file=output_stream)
        if agents.status == "manual-merge":
            print(
                f"AGENTS.md was preserved; perform a semantic merge from {agents.source}.",
                file=output_stream,
            )
        if not _resolve_conflicts(selectable_actions, policy, tty, input_stream, output_stream):
            return 1
        if catalog_file.status == "keep":
            print("Installation stopped; canonical catalog cannot be kept in conflict.",
                  file=output_stream)
            return 1
        if conflicts:
            print("Resolved component conflicts:", file=output_stream)
            for action in conflicts:
                print(f"- {action.status}: {action.relative}",
                      file=output_stream)
        manifest = _manifest_data(
            catalog, previous, selection, actions, agents, catalog_file)
        manifest_destination = target / MANIFEST_PATH
        manifest_content = _manifest_bytes(manifest)
        manifest_action = "create"
        if manifest_destination.exists():
            manifest_action = (
                "unchanged"
                if hash_path(manifest_destination) == _expected_file_hash(manifest_content)
                else "update"
            )
        print(f"- {manifest_action}: {MANIFEST_PATH.as_posix()}",
              file=output_stream)
        if args.dry_run:
            if args.init_config:
                init_project_config(
                    target,
                    Path(kit_root),
                    selection,
                    catalog,
                    output_stream,
                    dry_run=True,
                )
            print("Dry run complete; no files changed.", file=output_stream)
            return 0
        try:
            apply_transaction(target, actions, agents, catalog_file,
                              manifest, failure_injector)
        except RollbackIncomplete as exc:
            print(
                "Installation failed; rollback incomplete; recovery data retained at "
                f"{exc.path}",
                file=output_stream,
            )
            print(f"Rollback errors: {exc}", file=output_stream)
            return 1
        except TransactionInterrupted as exc:
            print(
                f"Installation interrupted and was rolled back: {exc}", file=output_stream)
            return 130
        except TransactionFailed as exc:
            print(
                f"Installation failed and was rolled back: {exc}", file=output_stream)
            return 1
        if args.init_config:
            init_project_config(
                target,
                Path(kit_root),
                selection,
                catalog,
                output_stream,
                dry_run=False,
            )
        if agents.status == "manual-merge":
            print(
                "Components applied; manual AGENTS.md semantic merge is required.",
                file=output_stream,
            )
            return 3
        print("Applied successfully; ownership manifest is current.",
              file=output_stream)
        return 0
    except KeyboardInterrupt:
        print("Installation cancelled; no files changed.", file=output_stream)
        return 130
    except InstallerError as exc:
        print(f"Error: {exc}", file=output_stream)
        return exc.code
    except (OSError, UnicodeError) as exc:
        print(
            f"Error: installation preflight failed: {exc}", file=output_stream)
        return 2


if __name__ == "__main__":
    sys.exit(main())

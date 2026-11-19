#!/usr/bin/env python3
"""Inspect contribution policy and validate local branch or commit proposals.

Invocation::

    python3 check_contribution.py inspect --root ROOT [--base-ref REF]
        [--expected-path PATH ...] [--format human|json]
    python3 check_contribution.py branch --root ROOT --name NAME
        [--confirmed-branch-prefix PREFIX --policy-source PATH]
        [--format human|json]
    python3 check_contribution.py commit --root ROOT --message-file FILE|-
        [--confirmed-commit-mode classic|conventional --policy-source PATH]
        [--base-ref REF] [--expected-path PATH ...] [--format human|json]
    python3 check_contribution.py pull-request --root ROOT --draft-file FILE|-
        [--confirmed-commit-mode classic|conventional --policy-source PATH]
        [--base-ref REF] [--expected-path PATH ...] [--observations FILE|-]
        [--format human|json]

Inputs are one safe local Git repository, optional repository-relative expected
paths, a candidate branch name, one bounded strict-UTF-8 message, and optional
paired confirmed policy value/source flags. ``-`` reads the message from stdin.
The source must be an applicable regular non-symlink AGENTS*.md or CONTRIBUTING*
file. Output is a deterministic owner-defined human or JSON report. The command
is offline and read-only: it never executes hooks, checks, staging, commits,
branch changes, network operations, or repository writes.

Python 3 and local Git are required. Git runs with prompts, optional locks, lazy
fetch, external diffs, text conversion, and configured filesystem monitors
disabled. Only allowlisted read-only argument arrays are accepted; stdout and
stderr are incrementally bounded and each process has a timeout. Exit 0 means
valid, 1 means policy or validation failure, and 2 means unsafe/uninspectable
input or invalid invocation. Diagnostics are stable and redact rejected values.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import selectors
import stat
import subprocess
import sys
import time
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Sequence, Tuple


sys.dont_write_bytecode = True
MAX_FILE_BYTES = 262_144
MAX_MESSAGE_BYTES = 65_536
MAX_GIT_OUTPUT = 8_000_000
GIT_TIMEOUT_SECONDS = 15
MAX_POLICY_FILES = 100
MAX_RELEVANT_LINES = 200
MAX_EXPECTED_PATHS = 1000
MAX_MESSAGE_LINES = 2000
MAX_DRAFT_LINES = 4000
MAX_OBSERVATION_CHECKS = 1000
SECRET_RE = re.compile(
    r"(?i)(?:gh[pousr]_[a-z0-9]{12,}|AKIA[0-9A-Z]{12,}|"
    r"(?:token|api[_-]?key|secret|password|credential)\s*[:=]\s*\S+|"
    r"https?://[^/@\s:]+:[^/@\s]+@)"
)
CC_HEADER_RE = re.compile(
    r"^(?P<type>[a-z][a-z0-9-]*)(?:\((?P<scope>[A-Za-z0-9][A-Za-z0-9._/-]*)\))?"
    r"(?P<breaking>!)?: (?P<description>\S(?:.*\S)?)$"
)
TRAILER_RE = re.compile(
    r"^(?P<token>[A-Za-z0-9-]+|BREAKING CHANGE)(?:: | #)(?P<value>\S.*)$")
PLACEHOLDER_RE = re.compile(r"<[A-Z][A-Z0-9_-]*>")
PR_REQUIRED_SECTIONS = (
    "Purpose and why", "Change", "Scope", "Authoritative context",
    "Risk and operational impact", "Checks", "Requested feedback",
)
PR_OPTIONAL_SECTIONS = ("Review order",)
CONFLICT_STATUS = frozenset({"DD", "AU", "UD", "UA", "DU", "AA", "UU"})
ROOT_PROJECT_FIELDS = frozenset({
    "schema_version", "roots", "repositories", "enabled_modules", "tracker",
    "agent", "review", "approval_policy", "contribution",
})
CONTRIBUTION_FIELDS = frozenset({
    "commit_mode", "base_branch", "required_trailers",
    "pull_request_template", "merge_strategy",
})


class UnsafeInput(ValueError):
    """An invocation or repository input cannot be inspected safely."""


class GitInspectionError(UnsafeInput):
    """An allowlisted Git inspection failed, timed out, or exceeded a bound."""


class UnsafePolicySource(UnsafeInput):
    """A confirmed prose source is missing, non-regular, or unsafe."""


class UnsafeMessageInput(UnsafeInput):
    """A commit message input is missing, non-regular, or unsafe."""


class UnsafeDraftInput(UnsafeInput):
    """A pull-request draft input is missing, non-regular, or unsafe."""


class UnsafeObservationsInput(UnsafeInput):
    """A pull-request observations input is malformed or unsafe."""


class _SafeArgumentParser(argparse.ArgumentParser):
    """Redact rejected command-line values from invocation diagnostics."""

    def error(self, _message: str) -> None:
        self.exit(2, "error: invalid invocation\n")


def _issue(code: str, message: str, path: Optional[str] = None,
           field: Optional[str] = None) -> Dict[str, Optional[str]]:
    return {"code": code, "path": path, "field": field, "message": message}


def _empty_report() -> Dict[str, Any]:
    return {
        "schema_version": 2,
        "valid": True,
        "errors": [],
        "warnings": [],
        "advice": [],
        "policy_sources": [],
        "policy": {
            "commit_mode": "classic",
            "commit_mode_source": "fallback",
            "commit_mode_state": "resolved",
            "branch_prefixes": [],
            "branch_prefix_state": "resolved",
            "required_trailers": [],
            "confirmed": {
                "policy_source": None,
                "commit_mode": None,
                "branch_prefix": None,
            },
        },
        "scope": {
            "base_ref": None,
            "expected_paths": [],
            "staged": [],
            "unstaged": [],
            "untracked": [],
            "unexpected_staged": [],
        },
        "branch": None,
        "commit": None,
        "pull_request": None,
        "summary": "validation passed",
    }


def _contains_forbidden_text(text: str, *, allow_newline: bool = True) -> bool:
    for character in text:
        value = ord(character)
        if 0xD800 <= value <= 0xDFFF:
            return True
        if unicodedata.category(character) in {"Cc", "Cs"} and not (
            allow_newline and character == "\n"
        ):
            return True
    return False


def _contains_secret(value: Any) -> bool:
    if isinstance(value, str):
        return SECRET_RE.search(value) is not None
    if isinstance(value, list):
        return any(_contains_secret(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_secret(key) or _contains_secret(item)
                   for key, item in value.items())
    return False


def _contains_forbidden_value(value: Any) -> bool:
    if isinstance(value, str):
        return len(value) > 500 or _contains_forbidden_text(value, allow_newline=False)
    if isinstance(value, list):
        return any(_contains_forbidden_value(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_forbidden_value(key) or _contains_forbidden_value(item)
                   for key, item in value.items())
    return False


def _safe_relative(value: str, *, allow_file: bool = True) -> str:
    if not isinstance(value, str) or not value or len(value) > 1000:
        raise UnsafeInput("path is outside its safe bounds")
    if _contains_forbidden_text(value, allow_newline=False) or "\\" in value:
        raise UnsafeInput("path syntax is unsafe")
    path = PurePosixPath(value)
    if path.is_absolute() or value in {".", ".."}:
        raise UnsafeInput("path must be repository-relative")
    parts = path.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise UnsafeInput("path contains an unsafe component")
    if parts[0].endswith(":") or (not allow_file and value.endswith("/")):
        raise UnsafeInput("path syntax is unsafe")
    return path.as_posix()


def _check_no_symlink_ancestors(path: Path) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current = current / component
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise UnsafeInput("path could not be inspected safely") from exc
        if stat.S_ISLNK(info.st_mode):
            raise UnsafeInput("path contains a symbolic link")


def _safe_root(value: str) -> Path:
    try:
        if (
            not isinstance(value, str) or not value or len(value) > 4096
            or value != value.strip()
            or _contains_forbidden_text(value, allow_newline=False)
        ):
            raise UnsafeInput("repository root syntax is unsafe")
        root = Path(value)
        if not root.is_absolute():
            root = Path.cwd() / root
        _check_no_symlink_ancestors(root)
        info = root.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise UnsafeInput("repository root is not a directory")
        git = root / ".git"
        git_info = git.lstat()
        if stat.S_ISLNK(git_info.st_mode) or not (
            stat.S_ISDIR(git_info.st_mode) or stat.S_ISREG(git_info.st_mode)
        ):
            raise UnsafeInput("repository metadata is unsafe")
        return root
    except UnsafeInput:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise UnsafeInput(
            "repository root could not be inspected safely") from exc


def _read_safe_repository_file(root: Path, relative: str, limit: int,
                               *, required: bool = True) -> Optional[bytes]:
    safe = _safe_relative(relative)
    path = root.joinpath(*PurePosixPath(safe).parts)
    current = root
    try:
        for component in PurePosixPath(safe).parts:
            current = current / component
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise UnsafeInput(
                    "repository file path contains a symbolic link")
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise UnsafeInput("repository input is not a regular file")
        if info.st_size > limit:
            raise UnsafeInput("repository input exceeds its byte limit")
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise UnsafeInput("repository input exceeds its byte limit")
        return data
    except FileNotFoundError:
        if required:
            raise UnsafeInput("repository input does not exist")
        return None
    except UnsafeInput:
        raise
    except OSError as exc:
        raise UnsafeInput("repository input could not be read safely") from exc


def _decode_utf8(data: bytes, label: str) -> str:
    try:
        return data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise UnsafeInput(label + " is not strict UTF-8") from exc


def _json_no_duplicates(text: str) -> Any:
    def pairs(items: List[Tuple[str, Any]]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise UnsafeInput("JSON contains a duplicate key")
            result[key] = value
        return result

    def invalid_constant(_value: str) -> None:
        raise UnsafeInput("JSON contains a non-finite number")
    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant)
    except UnsafeInput:
        raise
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise UnsafeInput("JSON is malformed") from exc


def _is_name(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) is not None


def _is_string(value: Any) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 500


def _validate_project_shape(parsed: Dict[str, Any]) -> None:
    roots = parsed.get("roots")
    root_fields = {"specs", "work", "adrs", "evidence", "domain_context"}
    if not isinstance(roots, dict) or set(roots) != root_fields:
        raise UnsafeInput("project roots are invalid")
    for field, value in roots.items():
        if value is None and field in {"adrs", "evidence", "domain_context"}:
            continue
        if not _is_string(value):
            raise UnsafeInput("project root is invalid")
        _safe_relative(value)
    repositories = parsed.get("repositories")
    if not isinstance(repositories, list) or len(repositories) > 100:
        raise UnsafeInput("project repositories are invalid")
    repository_ids = set()
    for repository in repositories:
        if not isinstance(repository, dict) or set(repository) != {"id", "path", "remote"}:
            raise UnsafeInput("project repository is invalid")
        if not _is_name(repository["id"]) or repository["id"] in repository_ids:
            raise UnsafeInput("project repository id is invalid")
        repository_ids.add(repository["id"])
        if not _is_string(repository["path"]):
            raise UnsafeInput("project repository path is invalid")
        if repository["remote"] is not None and not _is_string(repository["remote"]):
            raise UnsafeInput("project repository remote is invalid")
    modules = parsed.get("enabled_modules")
    if (not isinstance(modules, list) or len(modules) > 100
            or any(not _is_name(item) for item in modules) or len(modules) != len(set(modules))):
        raise UnsafeInput("project enabled modules are invalid")
    tracker = parsed.get("tracker")
    if not isinstance(tracker, dict) or set(tracker) != {"kind", "location", "labels"}:
        raise UnsafeInput("project tracker is invalid")
    if not _is_name(tracker["kind"]):
        raise UnsafeInput("project tracker kind is invalid")
    if tracker["location"] is not None and not _is_string(tracker["location"]):
        raise UnsafeInput("project tracker location is invalid")
    labels = tracker["labels"]
    if not isinstance(labels, dict) or any(not _is_string(key) or not _is_string(value)
                                           for key, value in labels.items()):
        raise UnsafeInput("project tracker labels are invalid")
    agent = parsed.get("agent")
    review = parsed.get("review")
    if not isinstance(agent, dict) or set(agent) != {"mode"} or agent["mode"] not in {
        "guided", "autonomous-within-rules",
    }:
        raise UnsafeInput("project agent mode is invalid")
    if not isinstance(review, dict) or set(review) != {"mode"} or review["mode"] not in {
        "risk-based", "always-independent",
    }:
        raise UnsafeInput("project review mode is invalid")
    approval = parsed.get("approval_policy")
    if not isinstance(approval, dict) or set(approval) != {"rules"} or not isinstance(approval["rules"], list):
        raise UnsafeInput("project approval policy is invalid")
    if len(approval["rules"]) > 100:
        raise UnsafeInput("project approval policy is too large")
    policy_keys = set()
    for rule in approval["rules"]:
        if not isinstance(rule, dict) or set(rule) != {"risk", "action", "required_roles", "independent"}:
            raise UnsafeInput("project approval rule is invalid")
        if rule["risk"] not in {"low", "medium", "high"} or not _is_name(rule["action"]):
            raise UnsafeInput("project approval rule is invalid")
        key = (rule["risk"], rule["action"])
        if key in policy_keys or type(rule["independent"]) is not bool:
            raise UnsafeInput("project approval rule is invalid")
        policy_keys.add(key)
        roles = rule["required_roles"]
        if not isinstance(roles, list) or not roles or len(roles) > 100:
            raise UnsafeInput("project approval roles are invalid")
        seen_roles = set()
        for role in roles:
            if not isinstance(role, dict) or set(role) != {"role", "minimum"}:
                raise UnsafeInput("project approval role is invalid")
            if (not _is_name(role["role"]) or role["role"] in seen_roles
                    or type(role["minimum"]) is not int or not 1 <= role["minimum"] <= 100):
                raise UnsafeInput("project approval role is invalid")
            seen_roles.add(role["role"])
        if rule["risk"] == "high" and not rule["independent"]:
            raise UnsafeInput("project high-risk approval rule is invalid")


def _project_contribution(root: Path) -> Optional[Dict[str, Any]]:
    legacy = root / ".agents" / "project.md"
    try:
        legacy.lstat()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise UnsafeInput(
            "legacy project configuration could not be inspected") from exc
    else:
        raise UnsafeInput("unsupported legacy project configuration exists")
    data = _read_safe_repository_file(
        root, ".agents/project.json", MAX_FILE_BYTES, required=False)
    if data is None:
        return None
    parsed = _json_no_duplicates(_decode_utf8(data, "project configuration"))
    if not isinstance(parsed, dict) or set(parsed) != ROOT_PROJECT_FIELDS:
        raise UnsafeInput(
            "project configuration does not match the closed v2 shape")
    if parsed.get("schema_version") != 2 or _contains_secret(parsed):
        raise UnsafeInput("project configuration is invalid or sensitive")
    if _contains_forbidden_value(parsed):
        raise UnsafeInput(
            "project configuration contains forbidden characters")
    _validate_project_shape(parsed)
    contribution = parsed.get("contribution")
    if not isinstance(contribution, dict) or set(contribution) != CONTRIBUTION_FIELDS:
        raise UnsafeInput("project contribution policy is invalid")
    mode = contribution.get("commit_mode")
    base = contribution.get("base_branch")
    trailers = contribution.get("required_trailers")
    template = contribution.get("pull_request_template")
    merge = contribution.get("merge_strategy")
    if mode not in {"discover", "classic", "conventional"}:
        raise UnsafeInput("project contribution commit mode is invalid")
    if base is not None and (
        not isinstance(base, str) or len(base) > 500
        or _contains_forbidden_text(base, allow_newline=False)
        or any(token in base for token in (" ", "..", "@{", "~", "^", ":", "?", "*", "[", "\\"))
        or base.startswith(("-", "/")) or base.endswith(("/", ".", ".lock"))
        or any(part in {"", ".", ".."} or part.startswith(".") for part in base.split("/"))
    ):
        raise UnsafeInput("project contribution base branch is invalid")
    if not isinstance(trailers, list) or len(trailers) > 100 or any(
        not isinstance(item, str) or re.fullmatch(
            r"[A-Za-z0-9-]+", item) is None
        for item in trailers
    ) or len(trailers) != len(set(trailers)):
        raise UnsafeInput("project contribution trailers are invalid")
    if template is not None:
        _safe_relative(template)
    if merge not in {"unknown", "merge", "squash", "rebase"}:
        raise UnsafeInput("project contribution merge strategy is invalid")
    return contribution


def _allowed_git(arguments: Sequence[str]) -> bool:
    args = list(arguments)
    if len(args) == 3 and args[:2] == ["check-ref-format", "--branch"]:
        return True
    if args == ["status", "--porcelain=v1", "-z"]:
        return True
    if args == ["diff", "--cached", "--check", "--no-ext-diff", "--no-textconv"]:
        return True
    if args == ["diff", "--cached", "--no-ext-diff", "--no-textconv", "--no-color", "--unified=0"]:
        return True
    if args == ["log", "-n", "25", "--format=%s"]:
        return True
    if len(args) == 4 and args[:2] == ["rev-parse", "--verify"] and args[3] == "--":
        return not args[2].startswith("-") and args[2].endswith("^{commit}")
    return False


def _stop_process(process: subprocess.Popen) -> None:
    if process.poll() is None:
        try:
            process.terminate()
            process.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
        except OSError:
            pass
    for stream in (process.stdout, process.stderr):
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass


def _run_git(root: Path, arguments: Sequence[str], *, allow_failure: bool = False,
             timeout: int = GIT_TIMEOUT_SECONDS,
             max_output: int = MAX_GIT_OUTPUT) -> Tuple[int, bytes]:
    """Run one allowlisted read-only Git command with bounded incremental pipes."""
    if not _allowed_git(arguments):
        raise GitInspectionError("Git command is not allowlisted")
    if not isinstance(timeout, int) or timeout < 1 or timeout > 120:
        raise GitInspectionError("Git timeout is outside its safe range")
    if not isinstance(max_output, int) or max_output < 1 or max_output > 64_000_000:
        raise GitInspectionError("Git output limit is outside its safe range")
    environment = {
        key: value for key, value in os.environ.items()
        if not key.startswith("GIT_")
    }
    environment.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_CONFIG_COUNT": "4",
        "GIT_CONFIG_KEY_0": "core.fsmonitor",
        "GIT_CONFIG_VALUE_0": "false",
        "GIT_CONFIG_KEY_1": "credential.interactive",
        "GIT_CONFIG_VALUE_1": "false",
        "GIT_CONFIG_KEY_2": "core.untrackedcache",
        "GIT_CONFIG_VALUE_2": "false",
        "GIT_CONFIG_KEY_3": "status.showUntrackedFiles",
        "GIT_CONFIG_VALUE_3": "all",
        "LC_ALL": "C",
    })
    process: Optional[subprocess.Popen] = None
    selector = selectors.DefaultSelector()
    output = bytearray()
    total = 0
    deadline = time.monotonic() + timeout
    try:
        process = subprocess.Popen(
            ["git", *arguments], cwd=str(root), env=environment,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            shell=False,
        )
        assert process.stdout is not None and process.stderr is not None
        selector.register(process.stdout, selectors.EVENT_READ, True)
        selector.register(process.stderr, selectors.EVENT_READ, False)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise GitInspectionError("Git inspection timed out")
            events = selector.select(min(remaining, 0.1))
            if not events and process.poll() is not None:
                events = [(key, selectors.EVENT_READ)
                          for key in selector.get_map().values()]
            for key, _ in events:
                chunk = os.read(key.fileobj.fileno(), min(
                    65_536, max_output - total + 1))
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                total += len(chunk)
                if total > max_output:
                    raise GitInspectionError(
                        "Git inspection output exceeded its limit")
                if key.data:
                    output.extend(chunk)
        return_code = process.wait(timeout=max(
            0.01, deadline - time.monotonic()))
        if return_code != 0 and not allow_failure:
            raise GitInspectionError("Git inspection failed")
        return return_code, bytes(output)
    except (OSError, subprocess.SubprocessError) as exc:
        if isinstance(exc, GitInspectionError):
            raise
        raise GitInspectionError("Git could not be inspected safely") from exc
    finally:
        selector.close()
        if process is not None:
            _stop_process(process)


def _source(level: int, path: str, kind: str, finding: str, *,
            state: str = "observed", relevant_lines: Sequence[int] = (),
            relevant_terms: Sequence[str] = ()) -> Dict[str, Any]:
    return {
        "level": level,
        "path": path,
        "kind": kind,
        "finding": finding,
        "state": state,
        "relevant_lines": list(relevant_lines)[:MAX_RELEVANT_LINES],
        "relevant_terms": sorted(set(relevant_terms)),
    }


def _matching_instruction_names(directory: Path, *, contributing: bool) -> List[str]:
    try:
        info = directory.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise UnsafeInput(
                "repository instruction directory is a symbolic link")
        if not stat.S_ISDIR(info.st_mode):
            return []
        matches = []
        for child in directory.iterdir():
            name = child.name
            is_agents = name.startswith("AGENTS") and name.endswith(".md")
            is_contributing = contributing and name.startswith("CONTRIBUTING")
            if is_agents or is_contributing:
                if _contains_secret(name) or _contains_forbidden_text(
                    name, allow_newline=False
                ):
                    raise UnsafeInput(
                        "repository instruction filename is unsafe")
                matches.append(name)
                if len(matches) > MAX_POLICY_FILES:
                    raise UnsafeInput("too many repository instruction files")
        return sorted(matches)
    except FileNotFoundError:
        return []
    except UnsafeInput:
        raise
    except OSError as exc:
        raise UnsafeInput(
            "repository instructions could not be inspected") from exc


def _instruction_paths(root: Path, expected: Sequence[str]) -> List[str]:
    directories: Dict[str, bool] = {"": True, ".github": True}
    for relative in expected:
        parts = PurePosixPath(relative).parts[:-1]
        for index in range(1, len(parts) + 1):
            directories[PurePosixPath(*parts[:index]).as_posix()] = False
    paths: List[str] = []
    for relative_directory, contributing in sorted(
        directories.items(),
        key=lambda item: (len(PurePosixPath(item[0]).parts), item[0]),
    ):
        directory = root if not relative_directory else root.joinpath(
            *PurePosixPath(relative_directory).parts)
        for name in _matching_instruction_names(directory, contributing=contributing):
            relative = (
                PurePosixPath(relative_directory, name).as_posix()
                if relative_directory else name
            )
            paths.append(relative)
            if len(paths) > MAX_POLICY_FILES:
                raise UnsafeInput("too many repository instruction files")
    return paths


def _instruction_relevance(text: str) -> Dict[str, List[int]]:
    relevant: Dict[str, List[int]] = {"commit": [], "branch": []}
    for line_number, line in enumerate(text.splitlines(), 1):
        normalized = line.casefold()
        if re.search(r"\b(?:commit|commits|conventional|classic)\b", normalized):
            relevant["commit"].append(line_number)
        if re.search(r"\b(?:branch|branches)\b", normalized):
            relevant["branch"].append(line_number)
    return relevant


def _safe_branch_prefix(prefix: str) -> bool:
    parts = prefix[:-1].split("/") if prefix.endswith("/") else []
    return not (
        len(prefix) > 100
        or not parts
        or _contains_forbidden_text(prefix, allow_newline=False)
        or _contains_secret(prefix)
        or any(character.isspace() for character in prefix)
        or any(token in prefix for token in ("..", "@{", "~", "^", ":", "?", "*", "[", "\\"))
        or prefix.startswith(("-", "/", "."))
        or any(
            not part or part.startswith(".") or part.endswith((".", ".lock"))
            for part in parts
        )
    )


def _strip_js_comments(text: str) -> str:
    if len(text) > MAX_FILE_BYTES:
        raise UnsafeInput("executable policy exceeds its parsing limit")
    output: List[str] = []
    index = 0
    quote: Optional[str] = None
    while index < len(text):
        character = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if quote is not None:
            output.append(character)
            if character == "\\" and index + 1 < len(text):
                index += 1
                output.append(text[index])
            elif character == quote:
                quote = None
            index += 1
            continue
        if character in {"'", '"', "`"}:
            quote = character
            output.append(character)
            index += 1
            continue
        if character == "/" and following == "/":
            index += 2
            while index < len(text) and text[index] != "\n":
                index += 1
            continue
        if character == "/" and following == "*":
            index += 2
            while index < len(text):
                if text[index] == "\n":
                    output.append("\n")
                if text[index:index + 2] == "*/":
                    index += 2
                    break
                index += 1
            continue
        output.append(character)
        index += 1
    return "".join(output)


def _has_conventional_reference(value: Any) -> bool:
    if isinstance(value, str):
        return re.search(
            r"(?:config[-_/]?conventional|conventional(?:commits?|changelog))",
            value.casefold(),
        ) is not None
    if isinstance(value, list):
        return any(_has_conventional_reference(item) for item in value)
    if isinstance(value, dict):
        return any(_has_conventional_reference(item) for item in value.values())
    return False


def _json_commitlint_requires(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    for key, item in value.items():
        normalized_key = "".join(
            character for character in key.casefold()
            if character not in {"-", "_"}
        )
        if normalized_key in {"extends", "parserpreset"}:
            if _has_conventional_reference(item):
                return True
        if normalized_key == "commitlint" and _json_commitlint_requires(item):
            return True
    return False


def _quoted_end(text: str, start: int, bound: int) -> Optional[int]:
    quote = text[start]
    index = start + 1
    while index < bound:
        if text[index] == "\\" and index + 1 < bound:
            index += 2
            continue
        if text[index] == quote:
            return index + 1
        index += 1
    return None


def _configured_value(text: str, start: int, key_start: int) -> str:
    bound = min(len(text), start + 500)
    index = start
    crossed_line = False
    while index < bound and text[index].isspace():
        crossed_line = crossed_line or text[index] in {"\r", "\n"}
        index += 1
    if index >= bound:
        return ""
    if text[index] in {"'", '"', "`"}:
        end = _quoted_end(text, index, bound)
        return text[index:end] if end is not None else ""
    if text[index] in {"[", "{"}:
        pairs = {"[": "]", "{": "}"}
        stack = [pairs[text[index]]]
        cursor = index + 1
        while cursor < bound:
            if text[cursor] in {"'", '"', "`"}:
                end = _quoted_end(text, cursor, bound)
                if end is None:
                    return ""
                cursor = end
                continue
            if text[cursor] in pairs:
                stack.append(pairs[text[cursor]])
            elif text[cursor] == stack[-1]:
                stack.pop()
                if not stack:
                    return text[index:cursor + 1]
            cursor += 1
        return ""
    if not crossed_line:
        end = index
        while end < bound and text[end] not in "\r\n,;}":
            end += 1
        return text[index:end]

    key_line_start = text.rfind("\n", 0, key_start) + 1
    key_indent = len(text[key_line_start:key_start].expandtabs(8))
    end = index
    while end < bound:
        newline = text.find("\n", end, bound)
        if newline < 0:
            return text[index:bound]
        next_start = newline + 1
        next_end = text.find("\n", next_start, bound)
        if next_end < 0:
            next_end = bound
        next_line = text[next_start:next_end]
        if next_line.strip():
            indentation = len(next_line) - len(next_line.lstrip(" \t"))
            if indentation <= key_indent:
                return text[index:newline]
        end = next_start
    return text[index:bound]


def _configured_commitlint_values(text: str) -> List[str]:
    values: List[str] = []
    index = 0
    while index < len(text):
        key_start = index
        key = ""
        if text[index] in {"'", '"'}:
            end = _quoted_end(text, index, len(text))
            if end is None:
                break
            key = text[index + 1:end - 1]
            index = end
        elif text[index].isalnum() or text[index] in {"_", "-"}:
            while index < len(text) and (
                text[index].isalnum() or text[index] in {"_", "-"}
            ):
                index += 1
            key = text[key_start:index]
        else:
            index += 1
            continue

        normalized_key = "".join(
            character for character in key.casefold()
            if character not in {"-", "_"}
        )
        if normalized_key not in {"extends", "parserpreset"}:
            continue
        line_start = text.rfind("\n", 0, key_start) + 1
        context = text[line_start:key_start].rstrip()
        if context and context[-1] not in {"{", ","}:
            continue
        separator = index
        while separator < len(text) and text[separator].isspace():
            separator += 1
        if separator >= len(text) or text[separator] not in {":", "="}:
            continue
        value = _configured_value(text, separator + 1, key_start)
        if value:
            values.append(value)
    return values


def _has_conventional_config_argument(value: Any) -> bool:
    if isinstance(value, str):
        reference = (
            r"(?:config[-_/]?conventional|"
            r"conventional(?:commits?|changelog))"
        )
        return re.search(
            r"(?:^|\s)(?:--config|-c)(?:\s+|\s*=\s*)[\"']?"
            r"[^\s\"']{0,200}" + reference,
            value.casefold(),
            re.MULTILINE,
        ) is not None
    if isinstance(value, list):
        return any(_has_conventional_config_argument(item) for item in value)
    if isinstance(value, dict):
        return any(
            _has_conventional_config_argument(item) for item in value.values()
        )
    return False


def _commitlint_requires_conventional(text: str) -> bool:
    stripped = _strip_js_comments(text)
    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, RecursionError, ValueError):
        parsed = None
    if parsed is not None and _json_commitlint_requires(parsed):
        return True
    configured = parsed is None and any(
        _has_conventional_reference(value)
        for value in _configured_commitlint_values(stripped)
    )
    argument_source = parsed if parsed is not None else stripped
    return configured or _has_conventional_config_argument(argument_source)


def _discover_policy(root: Path, expected: Sequence[str], report: Dict[str, Any],
                     *, include_template_evidence: bool,
                     confirmed_commit_mode: Optional[str] = None,
                     confirmed_branch_prefix: Optional[str] = None,
                     policy_source: Optional[str] = None) -> None:
    structured: List[Tuple[str, str]] = []
    executable: List[Tuple[str, str]] = []
    prose_relevance: Dict[str, Dict[str, List[int]]] = {}
    project = _project_contribution(root)
    if project is not None:
        mode = project["commit_mode"]
        report["policy_sources"].append(_source(
            1, ".agents/project.json", "project-config",
            "commit-mode-" + mode if mode != "discover" else "commit-mode-discover",
        ))
        if mode != "discover":
            structured.append((".agents/project.json", mode))
        report["policy"]["required_trailers"] = list(
            project["required_trailers"])
        if include_template_evidence and project["merge_strategy"] != "unknown":
            report["policy_sources"].append(_source(
                3, ".agents/project.json", "merge-evidence",
                "merge-strategy-" + project["merge_strategy"],
            ))
        if include_template_evidence and project["pull_request_template"] is not None:
            report["policy_sources"].append(_source(
                3, ".agents/project.json", "template-evidence", "configured-pr-template",
            ))
    _, policy_status = _run_git(root, ["status", "--porcelain=v1", "-z"])
    staged_paths, unstaged_paths, untracked_paths, _ = _parse_status(
        policy_status)
    applicable_paths = sorted(set(expected) | set(
        staged_paths) | set(unstaged_paths) | set(untracked_paths))
    instruction_paths = _instruction_paths(root, applicable_paths)
    for relative in instruction_paths:
        try:
            data = _read_safe_repository_file(root, relative, MAX_FILE_BYTES)
        except UnsafeInput as exc:
            if relative == policy_source:
                raise UnsafePolicySource(
                    "confirmed policy source could not be read safely") from exc
            raise
        assert data is not None
        text = _decode_utf8(data, "repository instructions")
        if _contains_secret(text):
            if relative == policy_source:
                raise UnsafePolicySource(
                    "confirmed policy source contains sensitive content")
            raise UnsafeInput(
                "repository instructions contain sensitive content")
        relevance = _instruction_relevance(text)
        prose_relevance[relative] = relevance
        terms = [topic for topic in ("commit", "branch") if relevance[topic]]
        relevant_lines = sorted(set(
            relevance["commit"] + relevance["branch"]))
        report["policy_sources"].append(_source(
            1, relative, "repository-instructions",
            "relevant-prose-observed" if terms else "instructions-observed",
            state="confirmation-required" if terms else "observed",
            relevant_lines=relevant_lines,
            relevant_terms=terms,
        ))

    executable_candidates = [
        ".commitlintrc", ".commitlintrc.json", ".commitlintrc.yaml", ".commitlintrc.yml",
        "commitlint.config.js", "commitlint.config.cjs", "commitlint.config.mjs",
        "package.json", ".git/hooks/commit-msg",
    ]
    ci_root = root / ".github" / "workflows"
    try:
        if ci_root.is_dir() and not ci_root.is_symlink():
            for child in sorted(ci_root.iterdir(), key=lambda item: item.name):
                if child.suffix in {".yml", ".yaml"} and len(executable_candidates) < MAX_POLICY_FILES:
                    executable_candidates.append(
                        ".github/workflows/" + child.name)
    except OSError as exc:
        raise UnsafeInput("executable policy could not be inspected") from exc
    for relative in executable_candidates:
        data = _read_safe_repository_file(
            root, relative, MAX_FILE_BYTES, required=False)
        if data is None:
            continue
        text = _decode_utf8(data, "executable policy")
        lowered = text.lower()
        if _contains_secret(text):
            raise UnsafeInput("executable policy contains sensitive content")
        commitlint_evidence = "commitlint" in relative.casefold() or "commitlint" in lowered
        requires = _commitlint_requires_conventional(text)
        if requires:
            finding = "requires-conventional-commits"
        elif commitlint_evidence:
            finding = "commitlint-requirement-unknown"
            report["warnings"].append(_issue(
                "executable-policy-ambiguous",
                "Commitlint evidence does not clearly require Conventional Commits.",
                path=relative, field="policy.commit_mode",
            ))
        else:
            finding = "executable-policy-observed"
        report["policy_sources"].append(
            _source(2, relative, "executable-config", finding))
        if requires:
            executable.append((relative, "conventional"))

    if include_template_evidence:
        template_candidates = [
            ".github/pull_request_template.md", ".github/PULL_REQUEST_TEMPLATE.md",
            "PULL_REQUEST_TEMPLATE.md", "docs/pull_request_template.md",
        ]
        for relative in template_candidates:
            data = _read_safe_repository_file(
                root, relative, MAX_FILE_BYTES, required=False)
            if data is not None:
                report["policy_sources"].append(
                    _source(3, relative, "template-evidence", "pull-request-template-observed"))

    _, log_bytes = _run_git(
        root, ["log", "-n", "25", "--format=%s"], allow_failure=True)
    log_text = _decode_utf8(log_bytes, "Git history")
    subjects = [line for line in log_text.splitlines() if line]
    conventional_count = sum(CC_HEADER_RE.fullmatch(
        line) is not None for line in subjects)
    if len(subjects) >= 3 and conventional_count == len(subjects):
        finding = "consistent-conventional-style-history"
    elif subjects:
        finding = "history-style-inconclusive"
    else:
        finding = "history-empty"
    report["policy_sources"].append(
        _source(4, "history", "style-evidence", finding))

    structured_modes = {mode for _, mode in structured}
    executable_modes = {mode for _, mode in executable}
    conflict = len(structured_modes) > 1 or len(executable_modes) > 1
    if structured_modes and executable_modes and structured_modes != executable_modes:
        conflict = True
    if conflict:
        report["errors"].append(_issue(
            "policy-conflict",
            "Structured contribution policy conflicts with executable checks.",
            field="policy.commit_mode",
        ))
    if len(structured_modes) == 1:
        mode = next(iter(structured_modes))
        source_path = next(path for path, found in structured if found == mode)
    elif len(structured_modes) > 1:
        mode = sorted(structured_modes)[0]
        source_path = "conflict"
    elif len(executable_modes) == 1:
        mode = next(iter(executable_modes))
        source_path = next(path for path, found in executable if found == mode)
    elif len(executable_modes) > 1:
        mode = sorted(executable_modes)[0]
        source_path = "conflict"
    else:
        mode = "classic"
        source_path = "fallback"
        report["policy_sources"].append(_source(
            5, "kit-fallback", "fallback", "commit-mode-classic",
            state="resolved",
        ))
    report["policy"]["commit_mode"] = mode
    report["policy"]["commit_mode_source"] = source_path

    commit_sources = sorted(
        path for path, relevance in prose_relevance.items()
        if relevance["commit"]
    )
    branch_sources = sorted(
        path for path, relevance in prose_relevance.items()
        if relevance["branch"]
    )
    if commit_sources:
        report["policy"]["commit_mode_state"] = "confirmation-required"
    if branch_sources:
        report["policy"]["branch_prefix_state"] = "confirmation-required"

    confirmed_topic = (
        "commit" if confirmed_commit_mode is not None else
        "branch" if confirmed_branch_prefix is not None else None
    )
    confirmed_source: Optional[str] = None
    if confirmed_topic is not None:
        assert policy_source is not None
        try:
            if _contains_secret(policy_source):
                raise UnsafeInput("confirmed policy source is sensitive")
            confirmed_source = _safe_relative(policy_source)
            data = _read_safe_repository_file(
                root, confirmed_source, MAX_FILE_BYTES)
        except UnsafeInput as exc:
            raise UnsafePolicySource(
                "confirmed policy source could not be inspected safely") from exc
        assert data is not None
        basename = PurePosixPath(confirmed_source).name
        allowed_name = (
            basename.startswith("CONTRIBUTING")
            or (basename.startswith("AGENTS") and basename.endswith(".md"))
        )
        source_relevance = prose_relevance.get(confirmed_source)
        if (
            not allowed_name
            or confirmed_source not in instruction_paths
            or source_relevance is None
            or not source_relevance[confirmed_topic]
        ):
            report["errors"].append(_issue(
                "confirmed-policy-source-mismatch",
                "The confirmed source is not an applicable repository instruction with relevant text for this decision.",
                path=confirmed_source, field="policy.confirmed.policy_source",
            ))
            confirmed_source = None

    if confirmed_commit_mode is not None and confirmed_source is not None:
        known_modes = structured_modes | executable_modes
        report["policy"]["confirmed"] = {
            "policy_source": confirmed_source,
            "commit_mode": confirmed_commit_mode,
            "branch_prefix": None,
        }
        report["policy"]["commit_mode_state"] = "resolved"
        if known_modes and known_modes != {confirmed_commit_mode}:
            report["errors"].append(_issue(
                "policy-conflict",
                "The confirmed prose decision conflicts with structured or executable policy.",
                path=confirmed_source, field="policy.commit_mode",
            ))
        else:
            report["policy"]["commit_mode"] = confirmed_commit_mode
            report["policy"]["commit_mode_source"] = confirmed_source
    elif confirmed_branch_prefix is not None and confirmed_source is not None:
        if not _safe_branch_prefix(confirmed_branch_prefix):
            raise UnsafePolicySource(
                "confirmed branch prefix is outside safe bounds")
        report["policy"]["branch_prefixes"] = [confirmed_branch_prefix]
        report["policy"]["branch_prefix_state"] = "resolved"
        report["policy"]["confirmed"] = {
            "policy_source": confirmed_source,
            "commit_mode": None,
            "branch_prefix": confirmed_branch_prefix,
        }

    if report["policy"]["commit_mode_state"] == "confirmation-required":
        report["warnings"].append(_issue(
            "policy-confirmation-required",
            "Relevant commit-policy prose was found; an agent or user must confirm the mode because the checker does not interpret its direction.",
            path=commit_sources[0], field="policy.commit_mode",
        ))
    if report["policy"]["branch_prefix_state"] == "confirmation-required":
        report["warnings"].append(_issue(
            "policy-confirmation-required",
            "Relevant branch-policy prose was found; an agent or user must confirm any prefix because the checker does not interpret its direction.",
            path=branch_sources[0], field="policy.branch_prefixes",
        ))
    report["policy_sources"].sort(key=lambda item: (
        item["level"], item["path"], item["finding"]))


def _parse_status(data: bytes) -> Tuple[List[str], List[str], List[str], bool]:
    text = _decode_utf8(data, "Git status")
    records = text.split("\0")
    staged: List[str] = []
    unstaged: List[str] = []
    untracked: List[str] = []
    conflicted = False
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if len(record) < 4 or record[2] != " ":
            raise GitInspectionError("Git status output is malformed")
        state = record[:2]
        path = record[3:]
        try:
            path = _safe_relative(path)
        except UnsafeInput as exc:
            raise GitInspectionError(
                "Git status contains an unsafe path") from exc
        if state == "??":
            untracked.append(path)
            continue
        if state in CONFLICT_STATUS:
            conflicted = True
        if state[0] not in {" ", "?"}:
            staged.append(path)
        if state[1] not in {" ", "?"}:
            unstaged.append(path)
        if state[0] in {"R", "C"}:
            if index >= len(records) or not records[index]:
                raise GitInspectionError(
                    "Git status rename output is malformed")
            index += 1
    return sorted(set(staged)), sorted(set(unstaged)), sorted(set(untracked)), conflicted


def _matches_expected(path: str, expected: Sequence[str]) -> bool:
    return any(path == item or path.startswith(item.rstrip("/") + "/") for item in expected)


def _inspect_scope(root: Path, expected: Sequence[str], base_ref: Optional[str],
                   report: Dict[str, Any]) -> None:
    normalized = sorted(set(_safe_relative(item) for item in expected))
    if len(normalized) > MAX_EXPECTED_PATHS:
        raise UnsafeInput("too many expected paths")
    report["scope"]["expected_paths"] = normalized
    if base_ref is not None:
        if (len(base_ref) > 500 or _contains_forbidden_text(base_ref, allow_newline=False)
                or base_ref.startswith("-") or SECRET_RE.search(base_ref)):
            raise UnsafeInput("base ref is unsafe")
        code, _ = _run_git(
            root, ["rev-parse", "--verify", base_ref + "^{commit}", "--"],
            allow_failure=True,
        )
        if code != 0:
            report["errors"].append(_issue(
                "base-ref-not-found", "The requested local base ref does not resolve to a commit.",
                field="scope.base_ref",
            ))
        else:
            report["scope"]["base_ref"] = base_ref
    _, status = _run_git(root, ["status", "--porcelain=v1", "-z"])
    staged, unstaged, untracked, conflicted = _parse_status(status)
    report["scope"]["staged"] = staged
    report["scope"]["unstaged"] = unstaged
    report["scope"]["untracked"] = untracked
    if normalized:
        unexpected = sorted(
            path for path in staged if not _matches_expected(path, normalized))
        report["scope"]["unexpected_staged"] = unexpected
        if unexpected:
            report["warnings"].append(_issue(
                "unexpected-staged-path", "Staged paths exist outside the declared expected scope.",
                field="scope.unexpected_staged",
            ))
    if conflicted:
        report["errors"].append(_issue(
            "unmerged-index", "The Git index contains an unresolved merge state.", field="scope.staged"))
    code, _ = _run_git(
        root, ["diff", "--cached", "--check",
               "--no-ext-diff", "--no-textconv"],
        allow_failure=True,
    )
    if code != 0:
        report["errors"].append(_issue(
            "staged-whitespace-error", "The staged diff fails Git whitespace checks.",
            field="scope.staged",
        ))
    _, diff = _run_git(
        root, ["diff", "--cached", "--no-ext-diff", "--no-textconv", "--no-color", "--unified=0"])
    diff_text = _decode_utf8(diff, "staged diff")
    conflict_marker = False
    for line in diff_text.splitlines():
        if line.startswith("+++"):
            continue
        if line.startswith("+") and re.match(r"^(?:<<<<<<< |=======|>>>>>>> )", line[1:]):
            conflict_marker = True
            break
    if conflict_marker:
        report["errors"].append(_issue(
            "staged-conflict-marker", "The staged diff adds a conflict marker.", field="scope.staged"))
    if staged:
        report["advice"].append(_issue(
            "review-atomicity", "Confirm as agent judgment that staged changes form one coherent logical change and include related tests.",
            field="scope.staged",
        ))


def _read_message(root: Path, value: str) -> str:
    try:
        if value == "-":
            data = sys.stdin.buffer.read(MAX_MESSAGE_BYTES + 1)
            if len(data) > MAX_MESSAGE_BYTES:
                raise UnsafeInput("message input exceeds its byte limit")
        else:
            data = _read_safe_repository_file(root, value, MAX_MESSAGE_BYTES)
            assert data is not None
        text = _decode_utf8(data, "commit message")
        if len(text.splitlines()) > MAX_MESSAGE_LINES:
            raise UnsafeInput("commit message exceeds its line limit")
        if _contains_forbidden_text(text) or _contains_secret(text):
            raise UnsafeInput(
                "commit message contains forbidden or sensitive content")
        if not text or text.strip("\n") == "" or text.startswith("\n"):
            raise UnsafeInput("commit message bounds are invalid")
        return text[:-1] if text.endswith("\n") else text
    except UnsafeInput as exc:
        raise UnsafeMessageInput(
            "commit message could not be inspected safely") from exc


def _read_pull_request_input(root: Path, value: str, error_type: type[UnsafeInput],
                             label: str, max_lines: int) -> str:
    try:
        if value == "-":
            data = sys.stdin.buffer.read(MAX_MESSAGE_BYTES + 1)
            if len(data) > MAX_MESSAGE_BYTES:
                raise UnsafeInput(label + " exceeds its byte limit")
        else:
            data = _read_safe_repository_file(root, value, MAX_MESSAGE_BYTES)
            assert data is not None
        text = _decode_utf8(data, label)
        if len(text.splitlines()) > max_lines:
            raise UnsafeInput(label + " exceeds its line limit")
        if _contains_forbidden_text(text) or _contains_secret(text):
            raise UnsafeInput(
                label + " contains forbidden or sensitive content")
        return text[:-1] if text.endswith("\n") else text
    except UnsafeInput as exc:
        raise error_type(label + " could not be inspected safely") from exc


def _pull_request_template(root: Path, report: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    project = _project_contribution(root)
    candidates: List[str] = []
    configured = project["pull_request_template"] if project is not None else None
    if configured is not None:
        candidates.append(configured)
        configured_data = _read_safe_repository_file(
            root, configured, MAX_FILE_BYTES, required=False)
        if configured_data is None:
            report["warnings"].append(_issue(
                "configured-template-missing",
                "The configured pull-request template was not found; default candidates were inspected.",
                path=configured, field="pull_request.template"))
    candidates.extend([
        ".github/pull_request_template.md", ".github/PULL_REQUEST_TEMPLATE.md",
        "PULL_REQUEST_TEMPLATE.md", "docs/pull_request_template.md",
    ])
    seen: set[str] = set()
    for relative in candidates:
        if relative in seen:
            continue
        seen.add(relative)
        data = _read_safe_repository_file(
            root, relative, MAX_FILE_BYTES, required=False)
        if data is not None:
            return relative, _decode_utf8(data, "pull-request template")
    return None, None


def _validate_observation_shape(parsed: Any) -> List[Dict[str, Any]]:
    if not isinstance(parsed, dict) or set(parsed) != {"schema_version", "checks"}:
        raise UnsafeObservationsInput(
            "observations must use the closed schema")
    if parsed["schema_version"] != 2 or not isinstance(parsed["checks"], list):
        raise UnsafeObservationsInput(
            "observations schema version or checks are invalid")
    if len(parsed["checks"]) > MAX_OBSERVATION_CHECKS:
        raise UnsafeObservationsInput("too many observed checks")
    checks: List[Dict[str, Any]] = []
    names: set[str] = set()
    for item in parsed["checks"]:
        if not isinstance(item, dict) or set(item) != {
            "name", "scope", "status", "evidence_reference"
        }:
            raise UnsafeObservationsInput("observation check shape is invalid")
        name = item["name"]
        scope = item["scope"]
        evidence = item["evidence_reference"]
        if (
            not isinstance(name, str) or not 1 <= len(name) <= 500
            or not isinstance(scope, str) or not 1 <= len(scope) <= 500
            or (evidence is not None and (
                not isinstance(evidence, str) or not 1 <= len(evidence) <= 500))
            or item["status"] not in {"passed", "failed", "not-run"}
            or name in names
            or any(_contains_forbidden_text(value, allow_newline=False)
                   or _contains_secret(value)
                   for value in (name, scope)
                   if isinstance(value, str))
            or (isinstance(evidence, str) and (
                _contains_forbidden_text(evidence, allow_newline=False)
                or _contains_secret(evidence)))
        ):
            raise UnsafeObservationsInput(
                "observation check contains unsafe content")
        names.add(name)
        checks.append({
            "name": name, "scope": scope, "status": item["status"],
            "evidence_reference": evidence,
        })
    return checks


def _read_observations(root: Path, value: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    text = _read_pull_request_input(
        root, value, UnsafeObservationsInput, "observations input", MAX_MESSAGE_LINES)
    try:
        parsed = _json_no_duplicates(text)
        checks = _validate_observation_shape(parsed)
    except UnsafeObservationsInput:
        raise
    except UnsafeInput as exc:
        raise UnsafeObservationsInput(
            "observations input could not be inspected safely") from exc
    return checks, None if value == "-" else _safe_relative(value)


def _validate_pull_request(root: Path, draft: str,
                           observations: Optional[Tuple[List[Dict[str, Any]], Optional[str]]],
                           report: Dict[str, Any]) -> None:
    lines = draft.split("\n")
    title: Optional[str] = None
    if lines and re.fullmatch(r"# [^#\s].*?\S", lines[0]):
        title = lines[0][2:]
    else:
        report["errors"].append(_issue(
            "draft-title-invalid", "Draft must begin with one ATX H1 title.",
            field="pull_request.title"))
    headings: List[str] = []
    for line in lines[1:]:
        if line.startswith("## "):
            heading = line[3:].strip()
            if heading in headings:
                report["errors"].append(_issue(
                    "draft-section-duplicate", "Draft sections must not be duplicated.",
                    field="pull_request.sections"))
            headings.append(heading)
    for heading in PR_REQUIRED_SECTIONS:
        if heading not in headings:
            report["errors"].append(_issue(
                "draft-section-missing", "Draft is missing a required section.",
                field="pull_request.sections"))
    if PLACEHOLDER_RE.search(draft):
        report["errors"].append(_issue(
            "draft-placeholder-unresolved", "Draft contains an unresolved placeholder.",
            field="pull_request"))
    template_path, template = _pull_request_template(root, report)
    if template is not None:
        template_tokens = sorted(set(PLACEHOLDER_RE.findall(template)))
        if template_tokens:
            report["advice"].append(_issue(
                "template-placeholder-unresolved",
                "Resolve the local template placeholders in the draft: " +
                ", ".join(template_tokens),
                path=template_path, field="pull_request.template"))
    project = _project_contribution(root)
    merge_strategy = project["merge_strategy"] if project is not None else "unknown"
    if merge_strategy == "squash":
        if report["policy"]["commit_mode_state"] == "confirmation-required":
            report["errors"].append(_issue(
                "policy-confirmation-required",
                "Commit policy prose requires an explicit confirmed mode and source before squash-title validation.",
                field="policy.commit_mode"))
        if title is not None:
            _validate_message(title, report["policy"]["commit_mode"],
                              report["policy"]["required_trailers"], report)
    elif title is not None:
        report["advice"].append(_issue(
            "pr-title-advisory", "The pull-request title is advisory unless squash merge policy applies.",
            field="pull_request.title"))
    observed: List[str] = []
    omitted: List[str] = []
    if observations is None:
        report["warnings"].append(_issue(
            "checks-omitted", "No observations were supplied; checks remain omitted.",
            field="pull_request.checks"))
    else:
        checks, source = observations
        for check in checks:
            if check["status"] == "not-run":
                omitted.append(check["name"])
                report["warnings"].append(_issue(
                    "check-not-run", "An observed check was not run.",
                    path=source, field="pull_request.checks"))
            else:
                observed.append(check["name"])
            if check["status"] == "failed":
                report["errors"].append(_issue(
                    "check-failed", "An observed check failed.",
                    path=source, field="pull_request.checks"))
    report["pull_request"] = {
        "title": title,
        "sections": sorted(set(headings)),
        "template": template_path,
        "merge_strategy": merge_strategy,
        "observed_checks": sorted(observed),
        "omitted_checks": sorted(omitted),
    }


def _trailers(lines: Sequence[str]) -> Tuple[Dict[str, List[str]], Optional[int]]:
    if len(lines) < 3:
        return {}, None
    candidate_start = 2
    for index in range(len(lines) - 1, 1, -1):
        if lines[index] == "":
            candidate_start = index + 1
            break
    found: Dict[str, List[str]] = {}
    current: Optional[str] = None
    for line in lines[candidate_start:]:
        if line.startswith(("BREAKING CHANGE", "BREAKING-CHANGE")) and re.fullmatch(
            r"(?:BREAKING CHANGE|BREAKING-CHANGE): \S(?:.*\S)?", line
        ) is None:
            return {}, None
        match = TRAILER_RE.fullmatch(line)
        if match:
            token = match.group("token")
            if token == "BREAKING-CHANGE":
                token = "BREAKING CHANGE"
            found.setdefault(token, []).append(match.group("value"))
            current = token
        elif line.startswith((" ", "\t")) and current is not None and line.strip():
            found[current][-1] += "\n" + line.strip()
        else:
            return {}, None
    return (found, candidate_start) if found else ({}, None)


def _validate_message(text: str, mode: str, required: Sequence[str],
                      report: Dict[str, Any]) -> None:
    lines = text.split("\n")
    subject = lines[0]
    if len(subject) > 50:
        report["warnings"].append(_issue(
            "subject-over-50", "Subject exceeds the advisory 50-character width.", field="commit.subject"))
    long_body = next((index for index, line in enumerate(
        lines[2:], 3) if len(line) > 72), None)
    if long_body is not None:
        report["warnings"].append(_issue(
            "body-line-over-72", "A body or footer line exceeds the advisory 72-character width.",
            field="commit.body",
        ))
    if len(lines) > 1 and lines[1] != "":
        report["errors"].append(_issue(
            "body-separator-missing", "Message body must be separated from the subject by one blank line.",
            field="commit.body",
        ))
    empty_body_separator = (
        len(lines) > 1 and lines[1] == ""
        and all(not line.strip() for line in lines[2:])
    )
    if empty_body_separator:
        report["errors"].append(_issue(
            "empty-message-body",
            "A trailing body separator must introduce meaningful body or footer content.",
            field="commit.body",
        ))
    trailing_blank_lines = (
        len(lines) > 2
        and any(line.strip() for line in lines[2:-1])
        and not lines[-1].strip()
    )
    if trailing_blank_lines:
        report["errors"].append(_issue(
            "trailing-blank-lines",
            "A message may end with one terminal newline, not a trailing blank paragraph.",
            field="commit.body",
        ))
    malformed_breaking = any(
        line.startswith(("BREAKING CHANGE", "BREAKING-CHANGE"))
        and re.fullmatch(r"(?:BREAKING CHANGE|BREAKING-CHANGE): \S(?:.*\S)?", line) is None
        for line in lines[1:]
    )
    if malformed_breaking:
        report["errors"].append(_issue(
            "breaking-change-footer-invalid",
            "A reserved breaking-change footer requires exact ': <nonempty>' syntax.",
            field="commit.trailers",
        ))
    trailers, trailer_start = _trailers(lines)
    valid_breaking_lines = [
        index for index, line in enumerate(lines[1:], 1)
        if re.fullmatch(r"(?:BREAKING CHANGE|BREAKING-CHANGE): \S(?:.*\S)?", line)
    ]
    if valid_breaking_lines and (
        trailer_start is None
        or any(index < trailer_start for index in valid_breaking_lines)
    ):
        report["errors"].append(_issue(
            "breaking-change-footer-not-final",
            "A reserved breaking-change line must belong to the final trailer block.",
            field="commit.trailers",
        ))
    for token in required:
        if token not in trailers:
            report["errors"].append(_issue(
                "required-trailer-missing", "A repository-required trailer token is missing; no identity or value was invented.",
                field="commit.trailers",
            ))
            break
    body_end = trailer_start if trailer_start is not None else len(lines)
    body = [
        line for line in lines[2:body_end]
        if line.strip() and not line.startswith(("BREAKING CHANGE", "BREAKING-CHANGE"))
    ]
    if body:
        report["advice"].append(_issue(
            "review-body-what-why", "Confirm as agent judgment that the body explains material what and why without narrating the diff.",
            field="commit.body",
        ))
    if body and any(re.search(r"(?i)\b(?:all tests pass|guarantees?|fully complete)\b", line) for line in body):
        report["warnings"].append(_issue(
            "body-overclaim-review", "Review the body for mechanical or unsupported completion claims.",
            field="commit.body",
        ))
    if mode == "conventional":
        match = CC_HEADER_RE.fullmatch(subject)
        if match is None:
            report["errors"].append(_issue(
                "conventional-header-invalid", "Subject does not match Conventional Commits 1.0 type(scope)!: description grammar.",
                field="commit.subject",
            ))
        elif match.group("type") in {"feat", "fix"}:
            report["advice"].append(_issue(
                "feat-fix-semantics", "Confirm that feat denotes a feature and fix denotes a bug fix as defined by Conventional Commits.",
                field="commit.subject",
            ))
        breaking = "BREAKING CHANGE" in trailers
        if breaking and match is not None and not match.group("breaking"):
            report["advice"].append(_issue(
                "breaking-change-footer", "A BREAKING CHANGE footer validly marks the change without a header exclamation mark.",
                field="commit.trailers",
            ))
    else:
        words = subject.split()
        first = words[0].casefold() if words else ""
        normalized_words = re.findall(r"[a-z0-9]+", subject.casefold())
        significant_words = [
            word for word in normalized_words if word not in {"a", "an", "the"}
        ]
        known_generic_phrases = {
            ("fix", "bug"), ("fix", "issue"),
            ("improve", "problem"), ("improve", "code"),
            ("update", "files"), ("update", "code"),
            ("change", "things"), ("add", "stuff"),
            ("add", "changes"), ("remove", "code"),
            ("remove", "misc"), ("resolve", "issue"),
            ("correct", "problem"), ("modify", "files"),
            ("refactor", "code"), ("repair", "bug"),
            ("handle", "issue"), ("tweak", "code"),
        }
        generic_nouns = {
            "bug", "bugs", "issue", "issues", "problem", "problems",
            "code", "file", "files", "change", "changes", "stuff",
            "thing", "things", "misc",
        }
        normalized_subject = tuple(significant_words)
        known_placeholder = normalized_subject in known_generic_phrases or significant_words in (
            ["change"], ["changes"], ["misc"], ["misc", "changes"],
            ["wip"], ["updated"],
        ) or (
            len(significant_words) == 2
            and significant_words[0] == "phase"
            and significant_words[1].isdigit()
        )
        heuristic_generic = (
            len(significant_words) == 2
            and significant_words[1] in generic_nouns
            and normalized_subject not in known_generic_phrases
        )
        issue_only = re.fullmatch(
            r"(?:#|[A-Z]+-)?\d+[:.]?", subject) is not None
        non_imperative = first.endswith("ed") or first.endswith("ing")
        if (len(words) < 2 or known_placeholder or issue_only
                or non_imperative or subject.endswith(".")):
            report["errors"].append(_issue(
                "classic-subject-not-concrete", "Classic subject must be concrete, standalone, and imperative.",
                field="commit.subject",
            ))
        elif heuristic_generic:
            report["advice"].append(_issue(
                "review-subject-concreteness",
                "Review whether this subject is concrete; the checker does not claim complete natural-language understanding.",
                field="commit.subject",
            ))
        if CC_HEADER_RE.fullmatch(subject) is not None:
            report["warnings"].append(_issue(
                "conventional-style-not-required", "Conventional syntax was not required; history alone never makes it mandatory.",
                field="commit.subject",
            ))
    report["commit"] = {
        "mode": mode,
        "subject_length": len(subject),
        "body_present": bool(body),
        "trailers": sorted(trailers),
    }


def _validate_branch(root: Path, name: str, report: Dict[str, Any]) -> None:
    if (not isinstance(name, str) or not name or len(name) > 500
            or _contains_forbidden_text(name, allow_newline=False) or SECRET_RE.search(name)):
        report["errors"].append(_issue(
            "invalid-branch-name", "Candidate branch name is not a safe valid Git branch ref.",
            field="branch.name",
        ))
        return
    code, _ = _run_git(
        root, ["check-ref-format", "--branch", name], allow_failure=True)
    if code != 0:
        report["errors"].append(_issue(
            "invalid-branch-name", "Candidate branch name is not a safe valid Git branch ref.",
            field="branch.name",
        ))
        return
    prefixes = report["policy"]["branch_prefixes"]
    if prefixes and not any(name.startswith(prefix) for prefix in prefixes):
        report["errors"].append(_issue(
            "branch-policy-mismatch", "Candidate branch does not follow the explicit repository prefix policy.",
            field="branch.name",
        ))
        return
    report["branch"] = {"name": name, "created": False, "switched": False}


def _finalize(report: Dict[str, Any]) -> None:
    report["valid"] = not report["errors"]
    report["summary"] = "validation passed" if report["valid"] else "validation failed"


def _render_human(report: Dict[str, Any]) -> str:
    lines = [
        "contribution check", "valid: " + str(report["valid"]).lower(),
        "summary: " + report["summary"],
        "commit mode: " + report["policy"]["commit_mode"],
        "commit mode source: " + report["policy"]["commit_mode_source"],
        "commit mode state: " + report["policy"]["commit_mode_state"],
        "branch prefix state: " + report["policy"]["branch_prefix_state"],
        "confirmed policy source: " + (
            report["policy"]["confirmed"]["policy_source"] or "none"),
        "confirmed commit mode: " + (
            report["policy"]["confirmed"]["commit_mode"] or "none"),
        "confirmed branch prefix: " + (
            report["policy"]["confirmed"]["branch_prefix"] or "none"),
        "pull request: " +
        ("prepared" if report["pull_request"] is not None else "none"),
        "side effects: none", "action boundary: inspect and validate only",
    ]
    scope = report["scope"]
    for field in ("expected_paths", "staged", "unstaged", "untracked", "unexpected_staged"):
        lines.append(" ".join(field.split("_")) + ": " +
                     (", ".join(scope[field]) or "none"))
    for heading in ("errors", "warnings", "advice"):
        lines.append(heading + ":")
        entries = report[heading]
        if not entries:
            lines.append("- none")
        else:
            for item in entries:
                location = item["path"] or item["field"] or "report"
                lines.append(
                    "- " + item["code"] + " [" + location + "]: " + item["message"])
    lines.append("policy sources:")
    for source in report["policy_sources"]:
        rendered_lines = ",".join(str(item)
                                  for item in source["relevant_lines"])
        rendered_terms = ",".join(source["relevant_terms"])
        lines.append(
            "- level {level} {path}: {finding}; state={state}; lines={lines}; terms={terms}".format(
                **source, lines=rendered_lines or "none",
                terms=rendered_terms or "none",
            )
        )
    if not report["policy_sources"]:
        lines.append("- none")
    lines.append("canonical report json:")
    lines.append(json.dumps(report, ensure_ascii=False,
                 sort_keys=True, indent=2))
    return "\n".join(lines) + "\n"


def _parser() -> argparse.ArgumentParser:
    parser = _SafeArgumentParser(
        description=(
            "Read-only offline contribution inspector. Inputs are a safe local Git repository "
            "and explicit branch/message/scope values; '-' reads bounded strict-UTF-8 stdin. "
            "Output is deterministic human or JSON. Environment disables prompts, optional locks, lazy fetch, external diff behavior, "

            "and fsmonitor. Side effects: none. Exits: 0 valid, 1 policy/validation, 2 unsafe/invocation."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    command_help = {
        "inspect": "report policy and local Git scope without executing checks",
        "branch": "validate one candidate name without creating or switching",
        "commit": "validate one message and staged scope without hooks or commits",
        "pull-request": "validate one pull-request draft and local observations without publication",
    }
    for command in ("inspect", "branch", "commit", "pull-request"):
        sub = subparsers.add_parser(
            command, help=command_help[command],
            description=(
                command_help[command] +
                ". Inputs are bounded and local; output is human or JSON. "
                "Git prompts, locks, lazy fetch, external behavior, and filesystem monitors are disabled. "
                "Side effects: none. Exits: 0 valid, 1 policy/validation, 2 unsafe/invocation."
            ),
        )
        sub.add_argument("--root", required=True,
                         help="existing safe local Git repository root")
        sub.add_argument("--format", choices=("human", "json"), default="human",
                         help="deterministic output schema (default: human)")
        if command in {"inspect", "commit", "pull-request"}:
            sub.add_argument(
                "--base-ref", help="optional explicit local base commit ref")
            sub.add_argument("--expected-path", action="append", default=[],
                             help="repeatable repository-relative intended scope")
        if command == "branch":
            sub.add_argument("--name", required=True,
                             help="candidate only; never creates or switches")
            sub.add_argument(
                "--confirmed-branch-prefix",
                help="confirmed safe branch prefix from the paired prose policy source",
            )
            sub.add_argument(
                "--policy-source",
                help="paired applicable AGENTS*.md or CONTRIBUTING* source",
            )
        if command == "commit":
            sub.add_argument("--message-file", required=True,
                             help="safe repository-relative message file or - for bounded stdin")
            sub.add_argument(
                "--confirmed-commit-mode", choices=("classic", "conventional"),
                help="confirmed commit mode from the paired prose policy source",
            )
            sub.add_argument(
                "--policy-source",
                help="paired applicable AGENTS*.md or CONTRIBUTING* source",
            )
        if command == "pull-request":
            sub.add_argument("--draft-file", required=True,
                             help="safe repository-relative draft file or - for bounded stdin")
            sub.add_argument("--observations",
                             help="safe repository-relative observations file or - for bounded stdin")
            sub.add_argument(
                "--confirmed-commit-mode", choices=("classic", "conventional"),
                help="confirmed commit mode from the paired prose policy source",
            )
            sub.add_argument(
                "--policy-source",
                help="paired applicable AGENTS*.md or CONTRIBUTING* source",
            )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the documented read-only CLI and return its stable exit status."""
    raw_arguments = list(sys.argv[1:] if argv is None else argv)
    if "--name" in raw_arguments:
        name_index = raw_arguments.index("--name")
        if name_index + 1 < len(raw_arguments) and raw_arguments[name_index + 1].startswith("-"):
            # Preserve dash-leading candidates for ref validation instead of parser rejection.
            raw_arguments[name_index:name_index +
                          2] = ["--name=" + raw_arguments[name_index + 1]]
    argument_parser = _parser()
    arguments = argument_parser.parse_args(raw_arguments)
    if (
        arguments.command == "pull-request"
        and arguments.draft_file == "-"
        and arguments.observations == "-"
    ):
        argument_parser.error(
            "pull-request draft and observations cannot both consume stdin")
    confirmed_value = (
        getattr(arguments, "confirmed_branch_prefix", None)
        if arguments.command == "branch"
        else getattr(arguments, "confirmed_commit_mode", None)
    )
    if (confirmed_value is None) != (getattr(arguments, "policy_source", None) is None):
        argument_parser.error(
            "confirmed policy flags must be supplied together")
    report = _empty_report()
    unsafe = False
    try:
        root = _safe_root(arguments.root)
        expected = getattr(arguments, "expected_path", [])
        normalized_expected = sorted(
            set(_safe_relative(item) for item in expected))
        _discover_policy(
            root, normalized_expected, report,
            include_template_evidence=arguments.command in {
                "inspect", "pull-request"},
            confirmed_commit_mode=getattr(
                arguments, "confirmed_commit_mode", None),
            confirmed_branch_prefix=getattr(
                arguments, "confirmed_branch_prefix", None),
            policy_source=getattr(arguments, "policy_source", None),
        )
        if arguments.command in {"inspect", "commit", "pull-request"}:
            _inspect_scope(root, normalized_expected,
                           arguments.base_ref, report)
        if arguments.command == "branch":
            if report["policy"]["branch_prefix_state"] == "confirmation-required":
                report["errors"].append(_issue(
                    "policy-confirmation-required",
                    "Branch policy prose requires an explicit confirmed prefix and source before validation.",
                    field="policy.branch_prefixes",
                ))
            _validate_branch(root, arguments.name, report)
        elif arguments.command == "commit":
            if report["policy"]["commit_mode_state"] == "confirmation-required":
                report["errors"].append(_issue(
                    "policy-confirmation-required",
                    "Commit policy prose requires an explicit confirmed mode and source before validation.",
                    field="policy.commit_mode",
                ))
            text = _read_message(root, arguments.message_file)
            _validate_message(
                text, report["policy"]["commit_mode"],
                report["policy"]["required_trailers"], report,
            )
            if not report["scope"]["staged"]:
                report["errors"].append(_issue(
                    "no-staged-changes", "No staged change is available for the proposed commit.",
                    field="scope.staged",
                ))
        elif arguments.command == "pull-request":
            draft = _read_pull_request_input(
                root, arguments.draft_file, UnsafeDraftInput,
                "pull-request draft", MAX_DRAFT_LINES)
            observations = None
            if arguments.observations is not None:
                observations = _read_observations(root, arguments.observations)
            _validate_pull_request(root, draft, observations, report)
    except UnsafePolicySource:
        unsafe = True
        report = _empty_report()
        report["errors"].append(_issue(
            "unsafe-policy-source",
            "The confirmed policy source or value could not be inspected safely.",
            field="policy.confirmed.policy_source",
        ))
    except UnsafeMessageInput:
        unsafe = True
        report = _empty_report()
        report["errors"].append(_issue(
            "unsafe-message-input",
            "An input or repository path could not be inspected safely.", field="input"))
    except UnsafeDraftInput:
        unsafe = True
        report = _empty_report()
        report["errors"].append(_issue(
            "unsafe-draft-input",
            "An input or repository path could not be inspected safely.", field="input"))
    except UnsafeObservationsInput:
        unsafe = True
        report = _empty_report()
        report["errors"].append(_issue(
            "unsafe-observations-input",
            "An input or repository path could not be inspected safely.", field="input"))
    except UnsafeInput:
        unsafe = True
        report = _empty_report()
        report["errors"].append(_issue(
            "unsafe-project-config",
            "An input or repository path could not be inspected safely.", field="input"))
    _finalize(report)
    if arguments.format == "json":
        sys.stdout.write(json.dumps(report, ensure_ascii=False,
                         sort_keys=True, separators=(",", ":")) + "\n")
    else:
        sys.stdout.write(_render_human(report))
    if unsafe:
        return 2
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

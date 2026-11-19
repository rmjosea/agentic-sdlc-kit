#!/usr/bin/env python3
"""Query issued artifact IDs or scan current IDs across all local Git history.

Invocation::

    python3 .agents/tools/check_artifact_ids.py query --root ROOT \
        --candidate ID [--candidate ID ...] [--format human|json]
    python3 .agents/tools/check_artifact_ids.py scan --root ROOT \
        [--format human|json]

Candidates are explicit global IDs (for example ``SPEC-002``) or qualified local
IDs (for example ``SPEC-002#REQ-001``). ``query`` classifies each candidate as
existing, available, reused, duplicate, or unverified. ``scan`` reports current
global/local duplicates and more than one task graph for a PLAN namespace. Both
modes inspect every commit reachable from all local refs and also a detached
HEAD; no caller-selected base narrows issued-ID history. Canonically named
owner assets ending in ``.template.md`` (including ``.v2.template.md``) are
contract inputs, not issued artifacts, and are omitted identically in current
and historical trees. Explicit legacy frontmatter is scanned conservatively. A document that attempts schema version
2 but fails the strict parser contributes only unambiguous recovered IDs and
makes history unverified; ambiguous namespace/parent data is never guessed.

The command is read-only and offline. It requires Python 3, Git, a safe local
repository root, and the source-checkout Markdown parser. It invokes only
allowlisted read-only Git argument arrays, with no shell, hooks, network, or
writes. Exit 0 means the current scan is structurally valid or all queried IDs
are permitted; an existing issued ID remains permitted with an explicit
unverified-history warning. Exit 1 means a deterministic duplicate/reuse
violation. Exit 2 means invalid input, or incomplete history when a query needs
to prove that an ID was never issued. An unborn repository with no commits or
refs is a complete empty history. Human and JSON output are stable.
"""

from __future__ import annotations

import json
import os
import re
import selectors
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Optional


sys.dont_write_bytecode = True
_SOURCE_ROOT = Path(__file__).resolve().parents[2]
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from scripts.contracts import catalog, markdown  # noqa: E402


ALLOWED_METADATA_KEYS = frozenset({
    "schema_version", "id", "type", "sources", "status", "parent",
    "fragment_id", "namespace", "source_revisions", "risk",
    "risk_rationale", "date", "supersedes", "superseded_by", "snapshot_at",
    "verdict", "evidence_reference", "depends_on", "children",
})
ARTIFACT_ID_RE = re.compile(r"^[A-Z]+-[0-9]+(?:-[A-Z]+-[0-9]+)?$")
QUALIFIED_ID_RE = re.compile(
    r"^([A-Z]+-[0-9]+(?:-[A-Z]+-[0-9]+)?)#((?:REQ|AC|TASK)-[0-9]+)$")
HEX_OBJECT_RE = re.compile(r"^[0-9a-f]{40,64}$")
TREE_ENTRY_RE = re.compile(
    rb"^(100644|100755|120000|160000) (blob|commit) ([0-9a-f]{40,64}) +(-|[0-9]+)\t(.*)$",
    re.DOTALL,
)

HARD_MAX_COMMITS = 100000
HARD_MAX_FILES = 1000000
HARD_MAX_BYTES = 500000000
HARD_MAX_OUTPUT_IDS = 500000
HARD_MAX_GIT_OUTPUT = 64000000


class HistoryError(ValueError):
    """Repository input or Git history cannot be inspected safely."""


@dataclass(frozen=True)
class HistoryLimits:
    """Finite ceilings for one current/all-ref ID scan.

    All limits are positive and capped by implementation hard maxima. File and
    byte ceilings apply independently to the current tree and committed-history
    traversal; cached historical blobs are charged once for bytes but every tree
    entry is charged as a file. ``git_timeout_seconds`` applies to each Git
    process. ``max_git_output_bytes`` is one incremental combined ceiling for
    stdout plus discarded stderr; neither stream is captured beyond it.
    """

    max_commits: int = 10000
    max_files: int = 250000
    max_bytes: int = 100000000
    max_output_ids: int = 100000
    git_timeout_seconds: int = 15
    max_git_output_bytes: int = 16000000

    def __post_init__(self) -> None:
        values = (
            ("max_commits", self.max_commits, HARD_MAX_COMMITS),
            ("max_files", self.max_files, HARD_MAX_FILES),
            ("max_bytes", self.max_bytes, HARD_MAX_BYTES),
            ("max_output_ids", self.max_output_ids, HARD_MAX_OUTPUT_IDS),
            ("git_timeout_seconds", self.git_timeout_seconds, 120),
            ("max_git_output_bytes", self.max_git_output_bytes, HARD_MAX_GIT_OUTPUT),
        )
        for name, value, maximum in values:
            if type(value) is not int or value < 1 or value > maximum:
                raise HistoryError(f"{name} is outside its safe range")


@dataclass
class _Extracted:
    artifacts: list[str]
    locals: list[str]
    task_namespaces: list[str]
    malformed: bool = False


@dataclass
class _History:
    complete: bool
    commits_scanned: int
    files_scanned: int
    bytes_scanned: int
    artifacts: set[str]
    locals: set[str]
    diagnostics: list[dict[str, str]]


def _diagnostic(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _is_owner_template_path(relative: str) -> bool:
    """Return whether one safe path is a canonically named owner template."""
    parts = PurePosixPath(relative).parts
    return (
        len(parts) >= 5
        and parts[0] == ".agents"
        and parts[1] in {"skills", "modules"}
        and parts[3] == "assets"
        and parts[-1].endswith(".template.md")
    )


def _safe_root(repository_root: Path | str) -> Path:
    try:
        root = catalog._repository_boundary(Path(repository_root))
        git_marker = root / ".git"
        info = git_marker.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise HistoryError("repository metadata path is a symlink")
        if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
            raise HistoryError("repository metadata path is invalid")
        return root
    except HistoryError:
        raise
    except (catalog.CatalogError, OSError, RuntimeError, ValueError) as exc:
        raise HistoryError(
            "repository root could not be inspected safely") from exc


def _allowed_git(arguments: list[str]) -> bool:
    if arguments == ["rev-parse", "--show-toplevel"]:
        return True
    if arguments == ["rev-parse", "--is-shallow-repository"]:
        return True
    if arguments == ["rev-parse", "--verify", "HEAD^{commit}"]:
        return True
    if (
        len(arguments) == 3
        and arguments[0] == "rev-list"
        and arguments[1].startswith("--max-count=")
        and arguments[2] in {"--all", "HEAD"}
    ):
        return arguments[1][12:].isdigit()
    if (
        len(arguments) == 5
        and arguments[:4] == ["ls-tree", "-r", "-z", "--long"]
        and HEX_OBJECT_RE.fullmatch(arguments[4]) is not None
    ):
        return True
    if (
        len(arguments) == 3
        and arguments[:2] == ["cat-file", "blob"]
        and HEX_OBJECT_RE.fullmatch(arguments[2]) is not None
    ):
        return True
    return False


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    """Stop one child promptly without collecting any remaining pipe output."""
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
            try:
                process.kill()
            except OSError:
                pass
    for stream in (process.stdout, process.stderr):
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass


def _run_git(
    root: Path,
    arguments: list[str],
    *,
    timeout: int = 15,
    max_output_bytes: int = 16000000,
    allow_failure: bool = False,
) -> bytes | tuple[int, bytes]:
    """Run allowlisted Git while incrementally bounding stdout plus stderr.

    At most ``max_output_bytes`` combined bytes are read from both child pipes.
    Stderr is counted and discarded; stdout is retained only within that same
    ceiling. Timeout or limit failure terminates, then if necessary kills, the
    child without materializing its unread output.
    """
    if not _allowed_git(arguments):
        raise HistoryError("Git command is not allowlisted")
    if type(timeout) is not int or timeout < 1:
        raise HistoryError("Git timeout is outside its safe range")
    if type(max_output_bytes) is not int or max_output_bytes < 1:
        raise HistoryError("Git output limit is outside its safe range")
    environment = os.environ.copy()
    environment.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_LAZY_FETCH": "1",
        "LC_ALL": "C",
    })
    process: Optional[subprocess.Popen[bytes]] = None
    selector = selectors.DefaultSelector()
    stdout = bytearray()
    total = 0
    deadline = time.monotonic() + timeout
    try:
        process = subprocess.Popen(
            ["git", *arguments],
            cwd=str(root),
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if process.stdout is None or process.stderr is None:
            raise HistoryError("Git pipes could not be opened safely")
        for label, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, label)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise HistoryError("Git inspection timed out")
            events = selector.select(remaining)
            if not events:
                raise HistoryError("Git inspection timed out")
            for key, _mask in events:
                allowance = max_output_bytes - total
                try:
                    chunk = os.read(key.fileobj.fileno(),
                                    min(65536, allowance + 1))
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                total += len(chunk)
                if total > max_output_bytes:
                    raise HistoryError("Git inspection output limit exceeded")
                if key.data == "stdout":
                    stdout.extend(chunk)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise HistoryError("Git inspection timed out")
        try:
            return_code = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            raise HistoryError("Git inspection timed out") from exc
        if allow_failure:
            return return_code, bytes(stdout)
        if return_code != 0:
            raise HistoryError("Git inspection failed")
        return bytes(stdout)
    except HistoryError:
        if process is not None:
            _stop_process(process)
        raise
    except (OSError, ValueError) as exc:
        if process is not None:
            _stop_process(process)
        raise HistoryError("Git could not be executed safely") from exc
    finally:
        selector.close()
        if process is not None:
            for stream in (process.stdout, process.stderr):
                if stream is not None and not stream.closed:
                    stream.close()


def _frontmatter_values(
    lines: list[str], key: str
) -> tuple[list[str], int]:
    """Recover bounded scalar strings without accepting metadata as valid."""
    values: list[str] = []
    occurrences = 0
    prefix = key + ":"
    for line in lines:
        if not line.startswith(prefix):
            continue
        occurrences += 1
        raw = line[len(prefix):].strip(" \t")
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, RecursionError):
            value = raw
        if isinstance(value, str):
            values.append(value)
    return values, occurrences


def _unique_valid(values: list[str], pattern: re.Pattern[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if pattern.fullmatch(value) is not None and value not in result:
            result.append(value)
    return result


def _v2_intent(frontmatter: list[str]) -> bool:
    for line in frontmatter:
        if not line.startswith("schema_version:"):
            continue
        value = line.split(":", 1)[1]
        if re.search(r"(?<![0-9])2(?![0-9])", value) is not None:
            return True
    return False


def _fallback_local_declarations(body: str) -> list[str]:
    masked = markdown._mask_markdown(body, ())
    result: list[str] = []
    for line in masked.split("\n"):
        match = markdown.LOCAL_ID_RE.match(line)
        if match is not None:
            result.append(match.group(1))
    return result


def _recover_document(
    frontmatter: list[str], body: str, *, malformed: bool
) -> _Extracted:
    id_values, id_occurrences = _frontmatter_values(frontmatter, "id")
    identifiers = _unique_valid(id_values, ARTIFACT_ID_RE)
    if id_occurrences == 0:
        return _Extracted([], [], [], False)
    type_values, type_occurrences = _frontmatter_values(frontmatter, "type")
    namespace_values, namespace_occurrences = _frontmatter_values(
        frontmatter, "namespace")
    parent_values, parent_occurrences = _frontmatter_values(
        frontmatter, "parent")
    types = _unique_valid(type_values, re.compile(r"^[a-z][a-z0-9-]*$"))
    namespaces = _unique_valid(namespace_values, ARTIFACT_ID_RE)
    parents = _unique_valid(parent_values, ARTIFACT_ID_RE)
    declarations = _fallback_local_declarations(body)

    qualifier: Optional[str] = None
    task_graph = types == ["task-graph"]
    task_namespaces: list[str] = (
        namespaces if "task-graph" in types else [])
    if task_graph:
        if (
            namespace_occurrences == 1
            and len(namespaces) == 1
            and namespaces[0].startswith("PLAN-")
        ):
            qualifier = namespaces[0]
    elif (
        type_occurrences == 1
        and len(types) == 1
        and types[0] in {"specification-fragment", "plan-fragment"}
    ):
        if parent_occurrences == 1 and len(parents) == 1:
            qualifier = parents[0]
    elif id_occurrences == 1 and len(identifiers) == 1:
        qualifier = identifiers[0]

    local_ids = (
        [f"{qualifier}#{local_id}" for local_id in declarations]
        if qualifier is not None
        else []
    )
    return _Extracted(identifiers, local_ids, task_namespaces, malformed)


def _extract_document(data: bytes) -> _Extracted:
    try:
        text = markdown.normalize_text(data)
    except markdown.MarkdownError:
        return _Extracted([], [], [], False)
    lines = text.split("\n")
    if not lines or lines[0] != "---":
        return _Extracted([], [], [], False)
    try:
        end = lines.index("---", 1)
    except ValueError:
        frontmatter = lines[1:257]
        return _recover_document(
            frontmatter, "", malformed=_v2_intent(frontmatter))
    frontmatter = lines[1:end]
    body = markdown.normalize_text("\n".join(lines[end + 1:]))
    v2 = _v2_intent(frontmatter)
    id_values, id_occurrences = _frontmatter_values(frontmatter, "id")
    if id_occurrences == 0:
        return _Extracted([], [], [], False)
    if not v2:
        return _recover_document(frontmatter, body, malformed=False)
    try:
        model = markdown.parse_markdown(
            data,
            allowed_metadata_keys=ALLOWED_METADATA_KEYS,
            mode="rendered",
        )
    except markdown.MarkdownError:
        return _recover_document(frontmatter, body, malformed=True)

    metadata = model["metadata"]
    identifier = metadata.get("id")
    if (
        not isinstance(identifier, str)
        or ARTIFACT_ID_RE.fullmatch(identifier) is None
        or len(_unique_valid(id_values, ARTIFACT_ID_RE)) != 1
    ):
        return _recover_document(frontmatter, body, malformed=True)
    parent = metadata.get("namespace") or metadata.get("parent") or identifier
    if not isinstance(parent, str) or ARTIFACT_ID_RE.fullmatch(parent) is None:
        return _recover_document(frontmatter, body, malformed=True)
    namespaces: list[str] = []
    if metadata.get("type") == "task-graph":
        namespace = metadata.get("namespace")
        if (
            not isinstance(namespace, str)
            or not namespace.startswith("PLAN-")
            or ARTIFACT_ID_RE.fullmatch(namespace) is None
        ):
            return _recover_document(frontmatter, body, malformed=True)
        namespaces.append(namespace)
    local_ids = [f"{parent}#{item['id']}" for item in model["local_ids"]]
    return _Extracted([identifier], local_ids, namespaces, False)


def _current_tree(root: Path, limits: HistoryLimits) -> tuple[
    list[str], list[str], list[str], list[dict[str, str]], int, int
]:
    artifacts: list[str] = []
    local_ids: list[str] = []
    namespaces: list[str] = []
    diagnostics: list[dict[str, str]] = []
    files_scanned = 0
    bytes_scanned = 0
    limit_hit = False
    for directory, directory_names, file_names in os.walk(root, followlinks=False):
        directory_names.sort()
        file_names.sort()
        if Path(directory) == root:
            directory_names[:] = [
                name for name in directory_names if name != ".git"]
        safe_directories: list[str] = []
        for name in directory_names:
            candidate = Path(directory) / name
            if candidate.is_symlink():
                diagnostics.append(_diagnostic(
                    "CURRENT_PATH_UNSAFE",
                    "A current-tree directory is a symlink and was not traversed.",
                ))
            else:
                safe_directories.append(name)
        directory_names[:] = safe_directories
        for name in file_names:
            path = Path(directory) / name
            files_scanned += 1
            if files_scanned > limits.max_files:
                diagnostics.append(_diagnostic(
                    "CURRENT_LIMIT", "Current-tree file limit exceeded."))
                limit_hit = True
                break
            if path.suffix.lower() != ".md":
                continue
            try:
                relative = path.relative_to(root).as_posix()
                catalog._safe_relative(relative, "current artifact")
                if path.is_symlink() or not path.is_file():
                    raise HistoryError("unsafe current artifact")
                if _is_owner_template_path(relative):
                    continue
                size = path.stat().st_size
                bytes_scanned += size
                if bytes_scanned > limits.max_bytes:
                    diagnostics.append(_diagnostic(
                        "CURRENT_LIMIT", "Current-tree byte limit exceeded."))
                    limit_hit = True
                    break
                extracted = _extract_document(path.read_bytes())
            except (OSError, RuntimeError, ValueError, catalog.CatalogError, HistoryError):
                diagnostics.append(_diagnostic(
                    "CURRENT_PATH_UNSAFE",
                    "A current Markdown path could not be inspected safely.",
                ))
                continue
            if extracted.malformed:
                diagnostics.append(_diagnostic(
                    "CURRENT_DOCUMENT_INVALID",
                    "A current v2 artifact is malformed and its IDs are unverified.",
                ))
            artifacts.extend(extracted.artifacts)
            local_ids.extend(extracted.locals)
            namespaces.extend(extracted.task_namespaces)
            if len(artifacts) + len(local_ids) > limits.max_output_ids:
                diagnostics.append(_diagnostic(
                    "CURRENT_LIMIT", "Current-tree ID limit exceeded."))
                limit_hit = True
                break
        if limit_hit:
            break
    return artifacts, local_ids, namespaces, diagnostics, files_scanned, bytes_scanned


def _commit_ids(root: Path, limits: HistoryLimits) -> tuple[list[str], bool]:
    count_argument = f"--max-count={limits.max_commits + 1}"
    all_output = _run_git(
        root, ["rev-list", count_argument, "--all"],
        timeout=limits.git_timeout_seconds,
        max_output_bytes=limits.max_git_output_bytes,
    )
    assert isinstance(all_output, bytes)
    commits = set(line for line in all_output.decode(
        "ascii").splitlines() if line)
    head_result = _run_git(
        root, ["rev-parse", "--verify", "HEAD^{commit}"],
        timeout=limits.git_timeout_seconds,
        max_output_bytes=1024,
        allow_failure=True,
    )
    assert isinstance(head_result, tuple)
    head_code, head_output = head_result
    if head_code == 0:
        head = head_output.decode("ascii").strip()
        head_history = _run_git(
            root, ["rev-list", count_argument, "HEAD"],
            timeout=limits.git_timeout_seconds,
            max_output_bytes=limits.max_git_output_bytes,
        )
        assert isinstance(head_history, bytes)
        commits.update(
            line for line in head_history.decode("ascii").splitlines() if line)
        if head:
            commits.add(head)
    if any(HEX_OBJECT_RE.fullmatch(commit) is None for commit in commits):
        raise HistoryError("Git returned an invalid commit identifier")
    exceeded = len(commits) > limits.max_commits
    return sorted(commits)[:limits.max_commits], exceeded


def _history(root: Path, limits: HistoryLimits) -> _History:
    diagnostics: list[dict[str, str]] = []
    artifacts: set[str] = set()
    local_ids: set[str] = set()
    commits_scanned = 0
    files_scanned = 0
    bytes_scanned = 0
    complete = True
    try:
        top_output = _run_git(
            root, ["rev-parse", "--show-toplevel"],
            timeout=limits.git_timeout_seconds, max_output_bytes=4096)
        assert isinstance(top_output, bytes)
        top = Path(os.fsdecode(top_output).strip()).resolve(strict=True)
        if top != root:
            raise HistoryError("root is not the repository top level")
        shallow_output = _run_git(
            root, ["rev-parse", "--is-shallow-repository"],
            timeout=limits.git_timeout_seconds, max_output_bytes=1024)
        assert isinstance(shallow_output, bytes)
        shallow = shallow_output.strip() == b"true"
        if shallow:
            complete = False
            diagnostics.append(_diagnostic(
                "HISTORY_SHALLOW",
                "Repository history is shallow; non-reuse is unverified.",
            ))
        commits, commit_limit = _commit_ids(root, limits)
        if commit_limit:
            complete = False
            diagnostics.append(_diagnostic(
                "HISTORY_LIMIT", "Commit scan limit exceeded."))
        blob_cache: dict[str, _Extracted] = {}
        for commit in commits:
            tree_output = _run_git(
                root, ["ls-tree", "-r", "-z", "--long", commit],
                timeout=limits.git_timeout_seconds,
                max_output_bytes=limits.max_git_output_bytes,
            )
            assert isinstance(tree_output, bytes)
            commits_scanned += 1
            for raw_entry in tree_output.split(b"\0"):
                if not raw_entry:
                    continue
                match = TREE_ENTRY_RE.fullmatch(raw_entry)
                if match is None:
                    raise HistoryError("Git tree entry is malformed")
                mode, object_type, raw_oid, raw_size, raw_path = match.groups()
                files_scanned += 1
                if files_scanned > limits.max_files:
                    complete = False
                    diagnostics.append(_diagnostic(
                        "HISTORY_LIMIT", "Historical file scan limit exceeded."))
                    return _History(
                        complete, commits_scanned, files_scanned, bytes_scanned,
                        artifacts, local_ids, diagnostics)
                if object_type != b"blob" or mode == b"120000":
                    if mode == b"120000" and raw_path.lower().endswith(b".md"):
                        complete = False
                        diagnostics.append(_diagnostic(
                            "HISTORY_PATH_UNSAFE",
                            "A historical Markdown path is a symlink.",
                        ))
                    continue
                try:
                    path_text = raw_path.decode("utf-8")
                    catalog._safe_relative(path_text, "historical path")
                except (UnicodeError, catalog.CatalogError):
                    complete = False
                    diagnostics.append(_diagnostic(
                        "HISTORY_PATH_UNSAFE",
                        "A historical path is not a safe portable path.",
                    ))
                    continue
                if _is_owner_template_path(path_text):
                    continue
                if PurePosixPath(path_text).suffix.lower() != ".md":
                    continue
                oid = raw_oid.decode("ascii")
                extracted = blob_cache.get(oid)
                if extracted is None:
                    if raw_size == b"-":
                        raise HistoryError("Git blob size is unavailable")
                    size = int(raw_size)
                    bytes_scanned += size
                    if bytes_scanned > limits.max_bytes:
                        complete = False
                        diagnostics.append(_diagnostic(
                            "HISTORY_LIMIT", "Historical byte scan limit exceeded."))
                        return _History(
                            complete, commits_scanned, files_scanned, bytes_scanned,
                            artifacts, local_ids, diagnostics)
                    blob_output = _run_git(
                        root, ["cat-file", "blob", oid],
                        timeout=limits.git_timeout_seconds,
                        max_output_bytes=min(
                            limits.max_git_output_bytes, limits.max_bytes + 1),
                    )
                    assert isinstance(blob_output, bytes)
                    extracted = _extract_document(blob_output)
                    blob_cache[oid] = extracted
                if extracted.malformed:
                    complete = False
                    diagnostics.append(_diagnostic(
                        "HISTORY_DOCUMENT_INVALID",
                        "A committed v2 artifact is malformed; history is unverified.",
                    ))
                artifacts.update(extracted.artifacts)
                local_ids.update(extracted.locals)
                if len(artifacts) + len(local_ids) > limits.max_output_ids:
                    complete = False
                    diagnostics.append(_diagnostic(
                        "HISTORY_LIMIT", "Historical ID limit exceeded."))
                    return _History(
                        complete, commits_scanned, files_scanned, bytes_scanned,
                        artifacts, local_ids, diagnostics)
    except (HistoryError, OSError, RuntimeError, UnicodeError, ValueError):
        complete = False
        diagnostics.append(_diagnostic(
            "HISTORY_UNREADABLE",
            "All locally reachable Git objects could not be inspected.",
        ))
    return _History(
        complete, commits_scanned, files_scanned, bytes_scanned,
        artifacts, local_ids, diagnostics)


def _duplicates(values: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return sorted(value for value, count in counts.items() if count > 1)


def _scan(
    repository_root: Path | str,
    candidates: Optional[list[str]],
    limits: Optional[HistoryLimits],
) -> dict[str, Any]:
    active_limits = limits or HistoryLimits()
    root = _safe_root(repository_root)
    artifacts, local_ids, namespaces, diagnostics, current_files, current_bytes = (
        _current_tree(root, active_limits)
    )
    artifact_duplicates = _duplicates(artifacts)
    local_duplicates = _duplicates(local_ids)
    namespace_duplicates = _duplicates(namespaces)
    for _identifier in artifact_duplicates:
        diagnostics.append(_diagnostic(
            "CURRENT_ARTIFACT_DUPLICATE",
            "A global artifact ID occurs more than once in the current tree.",
        ))
    for _identifier in local_duplicates:
        diagnostics.append(_diagnostic(
            "CURRENT_LOCAL_DUPLICATE",
            "A qualified local ID occurs more than once in the current tree.",
        ))
    for _namespace in namespace_duplicates:
        diagnostics.append(_diagnostic(
            "TASK_NAMESPACE_DUPLICATE",
            "More than one current task graph uses the same PLAN namespace.",
        ))
    history = _history(root, active_limits)
    diagnostics.extend(history.diagnostics)
    current_errors = bool(
        artifact_duplicates or local_duplicates or namespace_duplicates
        or any(item["code"].startswith("CURRENT_") for item in diagnostics)
    )
    candidate_reports: list[dict[str, Any]] = []
    if candidates is not None:
        if not candidates or len(candidates) != len(set(candidates)):
            raise HistoryError("query candidates must be non-empty and unique")
        for identifier in candidates:
            local = QUALIFIED_ID_RE.fullmatch(identifier) is not None
            if not local and ARTIFACT_ID_RE.fullmatch(identifier) is None:
                raise HistoryError("candidate ID has invalid syntax")
            current_count = (
                local_ids.count(identifier) if local else artifacts.count(identifier))
            issued = identifier in (
                history.locals if local else history.artifacts)
            if current_count > 1:
                state = "duplicate"
                allowed = False
            elif issued and current_count == 1:
                state = "existing"
                allowed = True
            elif issued:
                state = "reused"
                allowed = False
            elif history.complete:
                state = "available"
                allowed = True
            else:
                state = "unverified"
                allowed = False
            candidate_reports.append({
                "id": identifier,
                "kind": "qualified-local" if local else "global-artifact",
                "current_count": current_count,
                "historically_issued": issued,
                "state": state,
                "allowed": allowed,
            })
        valid = not current_errors and all(
            item["allowed"] for item in candidate_reports)
    else:
        valid = not current_errors
    return {
        "mode": "query" if candidates is not None else "scan",
        "valid": valid,
        "history": {
            "complete": history.complete,
            "state": "complete" if history.complete else "unverified",
            "commits_scanned": history.commits_scanned,
            "files_scanned": history.files_scanned,
            "bytes_scanned": history.bytes_scanned,
            "artifact_ids_issued": len(history.artifacts),
            "local_ids_issued": len(history.locals),
        },
        "current": {
            "files_scanned": current_files,
            "bytes_scanned": current_bytes,
            "artifact_ids": sorted(set(artifacts)),
            "local_ids": sorted(set(local_ids)),
            "task_namespaces": sorted(set(namespaces)),
        },
        "candidates": candidate_reports,
        "diagnostics": diagnostics,
    }


def scan_ids(
    repository_root: Path | str,
    *,
    limits: Optional[HistoryLimits] = None,
) -> dict[str, Any]:
    """Scan current IDs and all locally reachable committed history read-only.

    The deterministic report detects current global/qualified-local duplicates,
    duplicate task graphs per PLAN namespace, and whether history is complete.
    Scan validity describes the current tree; incomplete history remains an
    explicit warning and blocks only a later query that needs proof of non-use.
    No caller-selected base or ref is accepted. Git and filesystem state are not
    changed. Unsafe roots raise :class:`HistoryError`; Git/object degradation is
    represented as explicit ``history.state == "unverified"``.
    """
    return _scan(repository_root, None, limits)


def query_ids(
    repository_root: Path | str,
    candidates: list[str],
    *,
    limits: Optional[HistoryLimits] = None,
) -> dict[str, Any]:
    """Classify explicit candidate IDs against current and all-ref history.

    A historically issued ID absent from the current tree is ``reused``. A
    current ID found historically is ``existing`` even when shallow history
    prevents new issuance. A never-observed ID is ``available`` only with
    complete history, including verified-empty unborn history. This function is
    read-only and accepts no arbitrary base.
    """
    return _scan(repository_root, candidates, limits)


def _report_exit(report: dict[str, Any]) -> int:
    if report["valid"]:
        return 0
    if any(item["state"] == "unverified" for item in report["candidates"]):
        return 2
    if any(item["code"] in {
        "CURRENT_LIMIT", "CURRENT_PATH_UNSAFE", "CURRENT_DOCUMENT_INVALID"
    } for item in report["diagnostics"]):
        return 2
    return 1


def _render(report: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(
            report, ensure_ascii=False, separators=(",", ":")) + "\n"
    state = "VALID" if report["valid"] else "BLOCKED"
    history = report["history"]
    current = report["current"]
    lines = [
        f"Artifact ID {report['mode']}: {state}",
        f"History: {history['state']} ({history['commits_scanned']} commits, "
        f"{history['files_scanned']} files, {history['bytes_scanned']} bytes)",
        f"Current: {len(current['artifact_ids'])} artifact IDs, "
        f"{len(current['local_ids'])} qualified local IDs, "
        f"{len(current['task_namespaces'])} task namespaces",
    ]
    for candidate in report["candidates"]:
        lines.append(
            f"- {candidate['id']}: {candidate['state']} "
            f"(current={candidate['current_count']}, "
            f"issued={'yes' if candidate['historically_issued'] else 'no'})"
        )
    for diagnostic in report["diagnostics"]:
        lines.append(f"- [{diagnostic['code']}]: {diagnostic['message']}")
    return "\n".join(lines) + "\n"


def _help() -> str:
    return (
        "Usage: check_artifact_ids.py query --root ROOT --candidate ID "
        "[--candidate ID ...] [--format human|json]\n"
        "       check_artifact_ids.py scan --root ROOT [--format human|json]\n"
        "Optional finite ceilings: --max-commits N --max-files N --max-bytes N "
        "--max-output-ids N.\n"
        "Read-only inputs: safe local Git repository and explicit query IDs; no base.\n"
        "Output: deterministic current/all-ref issuance and completeness report.\n"
        "Environment: Python 3 and Git; offline, no hooks or network.\n"
        "Side effects: none. Exit 0=current-valid/permitted (including existing IDs), "
        "1=violation, 2=error or non-use unverified.\n"
    )


def _parse_args(argv: list[str]) -> tuple[
    Optional[str], Optional[str], list[str], str, Optional[HistoryLimits], Optional[str]
]:
    if argv == ["--help"] or argv == ["-h"]:
        return None, None, [], "human", None, "help"
    if not argv or argv[0] not in {"query", "scan"}:
        return None, None, [], "human", None, "Invalid invocation."
    mode = argv[0]
    root: Optional[str] = None
    candidates: list[str] = []
    output_format = "human"
    values: dict[str, int] = {}
    option_names = {
        "--max-commits": "max_commits",
        "--max-files": "max_files",
        "--max-bytes": "max_bytes",
        "--max-output-ids": "max_output_ids",
    }
    index = 1
    while index < len(argv):
        argument = argv[index]
        if index + 1 >= len(argv):
            return None, None, [], output_format, None, "Invalid invocation."
        value = argv[index + 1]
        if argument == "--root" and root is None:
            root = value
        elif argument == "--candidate":
            candidates.append(value)
        elif argument == "--format" and value in {"human", "json"}:
            output_format = value
        elif argument in option_names and option_names[argument] not in values:
            try:
                values[option_names[argument]] = int(value)
            except ValueError:
                return None, None, [], output_format, None, "Invalid invocation."
        else:
            return None, None, [], output_format, None, "Invalid invocation."
        index += 2
    if root is None or (mode == "query") != bool(candidates):
        return None, None, [], output_format, None, "Invalid invocation."
    try:
        limits = HistoryLimits(**values)
    except HistoryError:
        return None, None, [], output_format, None, "Invalid invocation."
    return mode, root, candidates, output_format, limits, None


def main(argv: Optional[list[str]] = None) -> int:
    """Run the documented read-only query/scan CLI and return its stable exit."""
    arguments = sys.argv[1:] if argv is None else argv
    mode, root, candidates, output_format, limits, error = _parse_args(
        arguments)
    if error == "help":
        sys.stdout.write(_help())
        return 0
    if error:
        report = {
            "mode": mode or "invalid", "valid": False,
            "history": {"complete": False, "state": "unverified", "commits_scanned": 0,
                        "files_scanned": 0, "bytes_scanned": 0,
                        "artifact_ids_issued": 0, "local_ids_issued": 0},
            "current": {"files_scanned": 0, "bytes_scanned": 0,
                        "artifact_ids": [], "local_ids": [], "task_namespaces": []},
            "candidates": [],
            "diagnostics": [_diagnostic("INVOCATION_INVALID", error)],
        }
        sys.stdout.write(_render(report, output_format))
        return 2
    try:
        assert root is not None and mode is not None
        report = (
            query_ids(root, candidates, limits=limits)
            if mode == "query"
            else scan_ids(root, limits=limits)
        )
    except Exception:
        report = {
            "mode": mode, "valid": False,
            "history": {"complete": False, "state": "unverified", "commits_scanned": 0,
                        "files_scanned": 0, "bytes_scanned": 0,
                        "artifact_ids_issued": 0, "local_ids_issued": 0},
            "current": {"files_scanned": 0, "bytes_scanned": 0,
                        "artifact_ids": [], "local_ids": [], "task_namespaces": []},
            "candidates": [],
            "diagnostics": [_diagnostic(
                "INSPECTION_ERROR", "Repository IDs could not be inspected safely.")],
        }
        sys.stdout.write(_render(report, output_format))
        return 2
    sys.stdout.write(_render(report, output_format))
    return _report_exit(report)


if __name__ == "__main__":
    sys.exit(main())

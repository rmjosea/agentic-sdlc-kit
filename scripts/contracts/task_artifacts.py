"""Validate parallel v2 task, handoff, and fragment semantics.

The semantic functions accept JSON-like values or normalized models returned by
:mod:`scripts.contracts.markdown`.  The fragment loader is the sole filesystem
entry point: it performs bounded, read-only loading below an explicit catalog
root and rejects every symlink in that lexical boundary.  No function performs
Git, network, or mutation operations.  Structural Markdown validation remains
owned by the owner-local JSON schemas; this module enforces cross-record
identity, graph, readiness, recovery-snapshot, and split reciprocity rules that
the repository's bounded JSON Schema profile cannot express clearly.

Every malformed input raises :class:`TaskArtifactError` with a deterministic,
non-sensitive message.  Collection and string ceilings are checked before set,
sort, or graph operations.
"""

from __future__ import annotations

import datetime as _datetime
import os
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Optional


MAX_COLLECTION_ITEMS = 10000
MAX_TOTAL_ITEMS = 50000
MAX_STRING_LENGTH = 100000

_TASK_RE = re.compile(r"^TASK-[0-9]+$")
_PLAN_RE = re.compile(r"^PLAN-[0-9]+$")
_GRAPH_RE = re.compile(r"^TASKS-[0-9]+$")
_HANDOFF_RE = re.compile(r"^HANDOFF-[0-9]+$")
_QUALIFIED_TASK_RE = re.compile(r"^(PLAN-[0-9]+)#(TASK-[0-9]+)$")
_QUALIFIED_REFERENCE_RE = re.compile(
    r"^[A-Z]+-[0-9]+(?:-[A-Z]+-[0-9]+)?#(?:REQ|AC|TASK)-[0-9]+$")
_LOCAL_REFERENCE_RE = re.compile(r"^(?:REQ|AC|TASK)-[0-9]+$")
_FRAGMENT_ID_RE = re.compile(r"^FRAG-[0-9]+$")
_FRAGMENT_GLOBAL_RE = re.compile(r"^(SPEC|PLAN)-([0-9]+)-FRAG-([0-9]+)$")
_UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")

_DOCUMENT_FIELDS = {
    "metadata", "h1", "sections", "local_ids", "references", "placeholders",
}
_GRAPH_METADATA_FIELDS = {"schema_version",
                          "id", "type", "sources", "namespace"}
_GRAPH_FIELDS = {"metadata", "controls", "tasks"}
_CONTROL_FIELDS = {
    "topology", "review_capacity", "maximum_in_progress", "review_queue",
}
_TASK_FIELDS = {
    "id", "title", "plan", "source_items", "type", "risk", "risk_rationale",
    "state", "depends_on", "blocker", "execution", "execution_rationale",
    "change_surface", "conflicts_with", "what", "why", "scope", "evidence",
    "contract_risk", "agent_roles", "review_focus", "rollback_point",
    "green_gate", "acceptance_evidence", "validation", "result",
}
_TASK_STATES = {"blocked", "ready", "in-progress", "done", "stale"}
_TASK_RISKS = {"low", "medium", "high"}
_HANDOFF_SECTIONS = (
    "Baseline and working-tree state", "Current task", "Objective last progress",
    "Exact checks and results", "Agent topology and roles", "Consumed limits",
    "Stop reason", "Risks and blockers", "Next safe action",
)
_CONTROL_LABELS = (
    "Topology", "Topology decision", "Review/integration capacity",
    "Maximum in-progress", "Review queue",
)
_TASK_LABELS = (
    "Plan", "Source items", "Type", "Risk", "Risk rationale", "State",
    "Depends on", "Blocker", "Execution", "Execution rationale",
    "Change surface", "Conflicts with", "What", "Why", "Scope", "Evidence",
    "Contract risk", "Agent roles", "Review focus", "Rollback point",
    "Green gate", "Acceptance evidence", "Validation commands/procedure",
    "Result",
)
_HANDOFF_DECLARATION = (
    "> Recovery snapshot only. The referenced task graph, never this handoff, remains\n"
    "> authoritative for task state."
)
_HANDOFF_AUTHORITY_CLAIM_RE = re.compile(
    r"\b(?:authority|authorities|authoritative|authoritatively)\b|"
    r"\bsource(?:\s+|-)of(?:\s+|-)truth\b|"
    r"\b(?:owns|controls|assigns)\s+(?:the\s+)?task\s+state\b",
    re.IGNORECASE,
)


class TaskArtifactError(ValueError):
    """A task graph, handoff, fragment, or split relationship is malformed."""


def _object(value: object, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise TaskArtifactError(f"{label} must be an object")
    if len(value) > MAX_COLLECTION_ITEMS:
        raise TaskArtifactError(f"{label} exceeds the collection limit")
    for key in value:
        if not isinstance(key, str):
            raise TaskArtifactError(f"{label} keys must be strings")
        if len(key) > MAX_STRING_LENGTH:
            raise TaskArtifactError(f"{label} key exceeds the string limit")
    return value


def _exact(value: object, fields: set[str], label: str) -> dict[str, Any]:
    record = _object(value, label)
    actual = set(record)
    missing = sorted(fields - actual)
    unknown = sorted(actual - fields)
    if missing:
        raise TaskArtifactError(f"{label} missing field: {missing[0]}")
    if unknown:
        raise TaskArtifactError(f"{label} unknown field: {unknown[0]}")
    return record


def _array(value: object, label: str, *, nonempty: bool = False) -> list[Any]:
    if type(value) is not list:
        raise TaskArtifactError(f"{label} must be an array")
    if len(value) > MAX_COLLECTION_ITEMS:
        raise TaskArtifactError(f"{label} exceeds the collection limit")
    if nonempty and not value:
        raise TaskArtifactError(f"{label} must be non-empty")
    return value


def _string(value: object, label: str, *, allow_pending: bool = True) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaskArtifactError(f"{label} must be a non-empty string")
    if len(value) > MAX_STRING_LENGTH:
        raise TaskArtifactError(f"{label} exceeds the string limit")
    if not allow_pending and value.strip().lower() == "pending":
        raise TaskArtifactError(f"{label} must contain an observed result")
    return value


def _string_sequence(value: object, label: str, *, nonempty: bool = False) -> list[str]:
    values = _array(value, label, nonempty=nonempty)
    return [_string(item, f"{label}[{index}]")
            for index, item in enumerate(values)]


def _strings(value: object, label: str, *, nonempty: bool = False) -> list[str]:
    result = _string_sequence(value, label, nonempty=nonempty)
    seen: set[str] = set()
    for text in result:
        if text in seen:
            raise TaskArtifactError(f"{label} entries must be unique")
        seen.add(text)
    return result


def _positive_integer(value: object, label: str) -> int:
    if type(value) is not int or value < 1:
        raise TaskArtifactError(f"{label} must be a positive integer")
    return value


def _metadata(document: object, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    model = _exact(document, _DOCUMENT_FIELDS, label)
    metadata = _object(model["metadata"], f"{label} metadata")
    _string(model["h1"], f"{label} h1")
    # Heading sequences preserve structural repetition (for example one
    # ``Change contract`` per task); owner semantics validate their order.
    _string_sequence(model["sections"], f"{label} sections")
    local_ids = _array(model["local_ids"], f"{label} local_ids")
    for index, local in enumerate(local_ids):
        item = _exact(local, {"kind", "id"}, f"{label} local_ids[{index}]")
        _string(item["kind"], f"{label} local_ids[{index}].kind")
        _string(item["id"], f"{label} local_ids[{index}].id")
    _strings(model["references"], f"{label} references")
    _strings(model["placeholders"], f"{label} placeholders")
    return model, metadata


def _validate_graph_metadata(value: object) -> dict[str, Any]:
    metadata = _exact(value, _GRAPH_METADATA_FIELDS, "task graph metadata")
    if type(metadata["schema_version"]) is not int or metadata["schema_version"] != 2:
        raise TaskArtifactError("task graph schema_version must be 2")
    identifier = _string(metadata["id"], "task graph id")
    if _GRAPH_RE.fullmatch(identifier) is None:
        raise TaskArtifactError("task graph id must use TASKS-N")
    if metadata["type"] != "task-graph":
        raise TaskArtifactError("task graph type must be task-graph")
    namespace = _string(metadata["namespace"], "task graph namespace")
    if _PLAN_RE.fullmatch(namespace) is None:
        raise TaskArtifactError("task graph namespace must use PLAN-N")
    sources = _strings(metadata["sources"],
                       "task graph sources", nonempty=True)
    if sources != [namespace]:
        raise TaskArtifactError("task graph sources must equal [namespace]")
    return metadata


def _source_text(source: object, label: str) -> str:
    if not isinstance(source, (bytes, str)):
        raise TaskArtifactError(f"{label} must be bytes or string")
    try:
        text = source.decode("utf-8") if isinstance(source, bytes) else source
        if isinstance(source, str):
            source.encode("utf-8")
    except UnicodeError as exc:
        raise TaskArtifactError(f"{label} must be UTF-8") from exc
    if len(text) > MAX_STRING_LENGTH * 10:
        raise TaskArtifactError(f"{label} exceeds the string limit")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _bound_source_text(
    document: dict[str, Any], source: object, label: str
) -> str:
    text = _source_text(source, label)
    try:
        from scripts.contracts import markdown
        parsed = markdown.parse_markdown(text, allowed_metadata_keys={
            "schema_version", "id", "type", "sources", "namespace",
            "snapshot_at", "parent", "fragment_id", "status", "children",
            "depends_on", "source_revisions", "risk", "risk_rationale",
        })
    except Exception as exc:
        raise TaskArtifactError(
            f"{label} is not valid rendered Markdown") from exc
    if parsed != document:
        raise TaskArtifactError(f"{label} does not match its normalized model")
    return text


def _section_range(lines: list[str], heading: str, next_heading: str) -> tuple[int, int]:
    starts = [index for index, line in enumerate(lines) if line == heading]
    ends = [index for index, line in enumerate(lines) if line == next_heading]
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        raise TaskArtifactError(
            f"Markdown section boundary is invalid: {heading}")
    return starts[0] + 1, ends[0]


def _canonical_fields(
    lines: list[str], labels: tuple[str, ...], label: str
) -> dict[str, str]:
    values: dict[str, str] = {}
    for canonical in labels:
        prefix = f"- {canonical}:"
        matches = [line[len(prefix):].strip()
                   for line in lines if line.startswith(prefix)]
        if len(matches) != 1:
            raise TaskArtifactError(
                f"{label} requires canonical field exactly once: {canonical}")
        values[canonical] = _string(matches[0], f"{label}.{canonical}")
    return values


def _markdown_list(value: str, label: str, *, nonempty: bool = False) -> list[str]:
    if value.strip().lower() in {"none", "empty"}:
        if nonempty:
            raise TaskArtifactError(f"{label} must be non-empty")
        return []
    values = [item.strip() for item in value.split(",")]
    return _strings(values, label, nonempty=nonempty)


def _markdown_positive_integer(value: str, label: str) -> int:
    if re.fullmatch(r"[0-9]+", value) is None:
        raise TaskArtifactError(f"{label} must be a positive integer")
    return _positive_integer(int(value), label)


def _semantic_graph_from_markdown(
    metadata: dict[str, Any], task_ids: list[str], source: object
) -> dict[str, Any]:
    text = _source_text(source, "task graph source")
    lines = text.split("\n")
    control_start, control_end = _section_range(
        lines, "## Execution controls", "## Tasks")
    controls_raw = _canonical_fields(
        lines[control_start:control_end], _CONTROL_LABELS, "execution controls")
    task_starts: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        match = re.fullmatch(r"### (TASK-[0-9]+): (\S.*)", line)
        if match is not None:
            task_starts.append((index, match.group(1), match.group(2)))
    if [item[1] for item in task_starts] != task_ids:
        raise TaskArtifactError(
            "tasks must be declared only as ### TASK-N: title in model order")
    coverage = [index for index, line in enumerate(
        lines) if line == "## Coverage"]
    if len(coverage) != 1 or not task_starts or task_starts[-1][0] >= coverage[0]:
        raise TaskArtifactError("task Markdown section boundaries are invalid")

    tasks: list[dict[str, Any]] = []
    field_names = {
        "Plan": "plan", "Source items": "source_items", "Type": "type",
        "Risk": "risk", "Risk rationale": "risk_rationale", "State": "state",
        "Depends on": "depends_on", "Blocker": "blocker", "Execution": "execution",
        "Execution rationale": "execution_rationale", "Change surface": "change_surface",
        "Conflicts with": "conflicts_with", "What": "what", "Why": "why",
        "Scope": "scope", "Evidence": "evidence", "Contract risk": "contract_risk",
        "Agent roles": "agent_roles", "Review focus": "review_focus",
        "Rollback point": "rollback_point", "Green gate": "green_gate",
        "Acceptance evidence": "acceptance_evidence",
        "Validation commands/procedure": "validation", "Result": "result",
    }
    for position, (start, identifier, title) in enumerate(task_starts):
        end = task_starts[position + 1][0] if position + \
            1 < len(task_starts) else coverage[0]
        raw = _canonical_fields(
            lines[start + 1:end], _TASK_LABELS, f"task {identifier}")
        item: dict[str, Any] = {
            "id": identifier,
            "title": title,
            **{field_names[key]: value for key, value in raw.items()},
        }
        item["source_items"] = _markdown_list(
            raw["Source items"], f"task {identifier}.source_items", nonempty=True)
        item["depends_on"] = _markdown_list(
            raw["Depends on"], f"task {identifier}.depends_on")
        item["change_surface"] = _markdown_list(
            raw["Change surface"], f"task {identifier}.change_surface", nonempty=True)
        item["conflicts_with"] = _markdown_list(
            raw["Conflicts with"], f"task {identifier}.conflicts_with")
        item["blocker"] = None if raw["Blocker"].lower(
        ) == "none" else raw["Blocker"]
        tasks.append(item)
    return {
        "metadata": dict(metadata),
        "controls": {
            "topology": controls_raw["Topology"],
            "review_capacity": _markdown_positive_integer(
                controls_raw["Review/integration capacity"],
                "execution controls.review_capacity"),
            "maximum_in_progress": _markdown_positive_integer(
                controls_raw["Maximum in-progress"],
                "execution controls.maximum_in_progress"),
            "review_queue": _markdown_list(
                controls_raw["Review queue"], "execution controls.review_queue"),
        },
        "tasks": tasks,
    }


def validate_task_graph_model(
    model: object, *, source: Optional[bytes | str] = None,
    external_tasks: Optional[Mapping[str, object]] = None,
) -> dict[str, Any]:
    """Validate one normalized task-graph document and its raw Markdown.

    When ``source`` is supplied, execution controls and every task are parsed
    within their exact heading boundaries.  Every canonical field must occur
    exactly once in its own record, then the resulting semantic graph is passed
    through :func:`validate_task_graph`.  ``external_tasks`` has the same
    explicit cross-plan blocker contract as that function.
    """
    document, metadata = _metadata(model, "task graph model")
    _validate_graph_metadata(metadata)
    local_ids = document["local_ids"]
    task_ids: list[str] = []
    for index, item in enumerate(local_ids):
        if item["kind"] != "task" or _TASK_RE.fullmatch(item["id"]) is None:
            raise TaskArtifactError(
                f"task graph local_ids[{index}] must be a task ID")
        if item["id"] in task_ids:
            raise TaskArtifactError("task graph local task IDs must be unique")
        task_ids.append(item["id"])
    if not task_ids:
        raise TaskArtifactError("task graph requires at least one task")
    expected_sections: list[str] = ["Execution controls", "Tasks"]
    actual_sections = document["sections"]
    task_headings = [section for section in actual_sections
                     if re.fullmatch(r"TASK-[0-9]+: \S.*", section)]
    if [heading.split(":", 1)[0] for heading in task_headings] != task_ids:
        raise TaskArtifactError(
            "task headings must declare local tasks in order")
    for heading in task_headings:
        expected_sections.extend((heading, "Change contract"))
    expected_sections.append("Coverage")
    if actual_sections != expected_sections:
        raise TaskArtifactError(
            "task graph sections do not match the v2 contract")
    declared = set(task_ids)
    for reference in document["references"]:
        if _TASK_RE.fullmatch(reference) is not None and reference not in declared:
            raise TaskArtifactError("task graph local reference is unresolved")
        if "TASK-" in reference and (_TASK_RE.fullmatch(reference) is None
                                     and _QUALIFIED_TASK_RE.fullmatch(reference) is None):
            raise TaskArtifactError(
                "external task references must be PLAN-N#TASK-N")
    if source is not None:
        _bound_source_text(document, source, "task graph source")
        semantic = _semantic_graph_from_markdown(metadata, task_ids, source)
        validate_task_graph(semantic, external_tasks=external_tasks)
    elif external_tasks is not None:
        raise TaskArtifactError(
            "external_tasks requires raw task graph source")
    return document


def _task_reference(value: str, label: str) -> None:
    if "TASK-" in value and (_TASK_RE.fullmatch(value) is None
                             and _QUALIFIED_TASK_RE.fullmatch(value) is None):
        raise TaskArtifactError(f"{label} task reference must be qualified")


def _external_states(value: object) -> dict[str, str]:
    records = _object(value, "external_tasks")
    result: dict[str, str] = {}
    for reference, state in records.items():
        if _QUALIFIED_TASK_RE.fullmatch(reference) is None:
            raise TaskArtifactError(
                "external_tasks keys must use PLAN-N#TASK-N")
        if not isinstance(state, str) or state not in _TASK_STATES:
            raise TaskArtifactError(
                f"external_tasks[{reference}] state is invalid")
        result[reference] = state
    return result


def validate_task_graph(
    value: object, *, external_tasks: Optional[Mapping[str, object]] = None
) -> dict[str, Any]:
    """Validate and return one closed semantic task graph.

    The input has ``metadata``, ``controls``, and ``tasks``.  Dependencies and
    conflicts are local ``TASK-N`` IDs.  A qualified cross-plan blocker is
    rejected unless ``external_tasks`` explicitly maps that
    ``PLAN-N#TASK-N`` reference to its current state.  Runnable and done tasks
    require done dependencies, cycles fail, blocked tasks require a live
    blocker, and done tasks require an observed result.
    """
    graph = _exact(value, _GRAPH_FIELDS, "task graph")
    metadata = _validate_graph_metadata(graph["metadata"])
    namespace = metadata["namespace"]
    resolved_external = (
        None if external_tasks is None else _external_states(external_tasks))
    controls = _exact(graph["controls"],
                      _CONTROL_FIELDS, "task graph controls")
    _string(controls["topology"], "task graph controls.topology")
    review_capacity = _positive_integer(
        controls["review_capacity"], "task graph controls.review_capacity")
    maximum_in_progress = _positive_integer(
        controls["maximum_in_progress"], "task graph controls.maximum_in_progress")
    review_queue = _strings(
        controls["review_queue"], "task graph controls.review_queue")

    raw_tasks = _array(graph["tasks"], "task graph tasks", nonempty=True)
    if len(raw_tasks) > MAX_COLLECTION_ITEMS:
        raise TaskArtifactError(
            "task graph tasks exceeds the collection limit")
    normalized_tasks: list[dict[str, Any]] = []
    task_by_id: dict[str, dict[str, Any]] = {}
    for index, raw_task in enumerate(raw_tasks):
        item = _exact(raw_task, _TASK_FIELDS, f"tasks[{index}]")
        identifier = _string(item["id"], f"tasks[{index}].id")
        if _TASK_RE.fullmatch(identifier) is None:
            raise TaskArtifactError(f"tasks[{index}].id must use TASK-N")
        if identifier in task_by_id:
            raise TaskArtifactError(f"duplicate local task ID: {identifier}")
        if item["plan"] != namespace:
            raise TaskArtifactError(
                f"tasks[{index}].plan must equal graph namespace")
        for field in (
            "title", "type", "risk_rationale", "execution", "execution_rationale",
            "what", "why", "scope", "evidence", "contract_risk", "agent_roles",
            "review_focus", "rollback_point", "green_gate", "acceptance_evidence",
            "validation",
        ):
            _string(item[field], f"tasks[{index}].{field}")
        risk = item["risk"]
        if not isinstance(risk, str) or risk not in _TASK_RISKS:
            raise TaskArtifactError(f"tasks[{index}].risk is invalid")
        state = item["state"]
        if not isinstance(state, str) or state not in _TASK_STATES:
            raise TaskArtifactError(f"tasks[{index}].state is invalid")
        sources = _strings(item["source_items"],
                           f"tasks[{index}].source_items", nonempty=True)
        for source in sources:
            _task_reference(source, f"tasks[{index}].source_items")
            if _LOCAL_REFERENCE_RE.fullmatch(source) is not None:
                raise TaskArtifactError(
                    "task source_items local references must be qualified")
        dependencies = _strings(
            item["depends_on"], f"tasks[{index}].depends_on")
        for dependency in dependencies:
            if _TASK_RE.fullmatch(dependency) is None:
                raise TaskArtifactError(
                    "task dependencies must be local TASK-N IDs")
        conflicts = _strings(item["conflicts_with"],
                             f"tasks[{index}].conflicts_with")
        for conflict in conflicts:
            if _TASK_RE.fullmatch(conflict) is None:
                raise TaskArtifactError(
                    "task conflicts must be local TASK-N IDs")
        _strings(item["change_surface"],
                 f"tasks[{index}].change_surface", nonempty=True)
        blocker = item["blocker"]
        if blocker is not None:
            blocker = _string(blocker, f"tasks[{index}].blocker")
            if (_TASK_RE.fullmatch(blocker) is None
                    and _QUALIFIED_TASK_RE.fullmatch(blocker) is None):
                raise TaskArtifactError(
                    "task blocker must be local or PLAN-N#TASK-N")
        result = _string(item["result"], f"tasks[{index}].result",
                         allow_pending=item["state"] != "done")
        normalized = dict(item)
        normalized.update({
            "source_items": sources, "depends_on": dependencies,
            "conflicts_with": conflicts, "blocker": blocker, "result": result,
        })
        normalized_tasks.append(normalized)
        task_by_id[identifier] = normalized

    known_ids = set(task_by_id)
    total_edges = 0
    for item in normalized_tasks:
        identifier = item["id"]
        if identifier in item["depends_on"]:
            raise TaskArtifactError(
                f"task {identifier} cannot depend on itself")
        missing = [dependency for dependency in item["depends_on"]
                   if dependency not in known_ids]
        if missing:
            raise TaskArtifactError(
                f"task {identifier} dependency is unresolved: {missing[0]}")
        bad_conflicts = [conflict for conflict in item["conflicts_with"]
                         if conflict not in known_ids or conflict == identifier]
        if bad_conflicts:
            raise TaskArtifactError(
                f"task {identifier} conflict is invalid: {bad_conflicts[0]}")
        total_edges += len(item["depends_on"]) + len(item["conflicts_with"])
        if total_edges > MAX_TOTAL_ITEMS:
            raise TaskArtifactError("task graph exceeds the total edge limit")

    # Iterative tri-color DFS keeps valid and cyclic deep graphs bounded by the
    # declared collection/edge ceilings rather than Python's recursion limit.
    # 0 white, 1 gray, 2 black
    colors = {identifier: 0 for identifier in task_by_id}
    for root in task_by_id:
        if colors[root] != 0:
            continue
        colors[root] = 1
        stack: list[tuple[str, int]] = [(root, 0)]
        while stack:
            identifier, dependency_index = stack[-1]
            dependencies = task_by_id[identifier]["depends_on"]
            if dependency_index >= len(dependencies):
                colors[identifier] = 2
                stack.pop()
                continue
            dependency = dependencies[dependency_index]
            stack[-1] = (identifier, dependency_index + 1)
            color = colors[dependency]
            if color == 1:
                raise TaskArtifactError(
                    f"task dependency cycle includes {dependency}")
            if color == 0:
                colors[dependency] = 1
                stack.append((dependency, 0))

    for item in normalized_tasks:
        identifier = item["id"]
        dependency_states = [task_by_id[dependency]["state"]
                             for dependency in item["depends_on"]]
        if item["state"] in {"ready", "in-progress", "done"} and any(
                state != "done" for state in dependency_states):
            raise TaskArtifactError(
                f"task {identifier} has an unfinished dependency")
        blocker = item["blocker"]
        if item["state"] == "blocked" and blocker is None:
            raise TaskArtifactError(
                f"blocked task {identifier} requires a blocker")
        if item["state"] != "blocked" and blocker is not None:
            raise TaskArtifactError(
                f"non-blocked task {identifier} cannot have a blocker")
        if blocker is not None:
            local_blocker: Optional[str] = None
            if _TASK_RE.fullmatch(blocker) is not None:
                local_blocker = blocker
            else:
                match = _QUALIFIED_TASK_RE.fullmatch(blocker)
                assert match is not None
                if match.group(1) == namespace:
                    local_blocker = match.group(2)
                else:
                    if resolved_external is None:
                        raise TaskArtifactError(
                            f"task {identifier} external blocker requires explicit resolution")
                    if blocker not in resolved_external:
                        raise TaskArtifactError(
                            f"task {identifier} external blocker is unresolved")
                    if resolved_external[blocker] == "done":
                        raise TaskArtifactError(
                            f"task {identifier} external blocker is already done")
            if local_blocker is not None:
                if local_blocker not in known_ids:
                    raise TaskArtifactError(
                        f"task {identifier} blocker is unresolved")
                if local_blocker not in item["depends_on"]:
                    raise TaskArtifactError(
                        f"task {identifier} blocker must be a dependency")
                if task_by_id[local_blocker]["state"] == "done":
                    raise TaskArtifactError(
                        f"task {identifier} blocker is already done")

    in_progress = sum(
        item["state"] == "in-progress" for item in normalized_tasks)
    if in_progress > maximum_in_progress:
        raise TaskArtifactError("task graph exceeds maximum_in_progress")
    if len(review_queue) > review_capacity:
        raise TaskArtifactError(
            "task graph review queue exceeds review_capacity")
    for queued in review_queue:
        if _TASK_RE.fullmatch(queued) is None or queued not in known_ids:
            raise TaskArtifactError(
                "task graph review queue contains an unresolved task")

    return {
        "metadata": dict(metadata),
        "controls": {
            "topology": controls["topology"],
            "review_capacity": review_capacity,
            "maximum_in_progress": maximum_in_progress,
            "review_queue": review_queue,
        },
        "tasks": normalized_tasks,
    }


def validate_task_graphs(values: object) -> list[dict[str, Any]]:
    """Validate graph namespaces and resolve qualified blockers across them.

    Exactly one graph may own each plan namespace.  Local task IDs remain scoped
    by namespace, while each qualified external blocker must identify a task in
    another supplied graph whose state is not ``done``.
    """
    graphs = _array(values, "task graphs", nonempty=True)
    namespaces: set[str] = set()
    graph_ids: set[str] = set()
    task_states: dict[str, str] = {}
    total_tasks = 0
    for graph_index, value in enumerate(graphs):
        raw_graph = _object(value, f"task graphs[{graph_index}]")
        if "metadata" not in raw_graph or "tasks" not in raw_graph:
            raise TaskArtifactError(
                f"task graphs[{graph_index}] requires metadata and tasks")
        metadata = _validate_graph_metadata(raw_graph["metadata"])
        namespace = metadata["namespace"]
        graph_id = metadata["id"]
        if namespace in namespaces:
            raise TaskArtifactError(
                f"duplicate task graph namespace: {namespace}")
        if graph_id in graph_ids:
            raise TaskArtifactError(
                f"duplicate global task graph id: {graph_id}")
        namespaces.add(namespace)
        graph_ids.add(graph_id)
        raw_tasks = _array(
            raw_graph["tasks"], f"task graphs[{graph_index}].tasks", nonempty=True)
        total_tasks += len(raw_tasks)
        if total_tasks > MAX_TOTAL_ITEMS:
            raise TaskArtifactError("task graphs exceed the total task limit")
        for task_index, raw_task in enumerate(raw_tasks):
            item = _object(
                raw_task, f"task graphs[{graph_index}].tasks[{task_index}]")
            if "id" not in item or "state" not in item:
                raise TaskArtifactError(
                    "task graph task requires id and state")
            identifier = _string(item["id"], "task graph task id")
            if _TASK_RE.fullmatch(identifier) is None:
                raise TaskArtifactError("task graph task id must use TASK-N")
            state = item["state"]
            if not isinstance(state, str) or state not in _TASK_STATES:
                raise TaskArtifactError("task graph task state is invalid")
            qualified = f"{namespace}#{identifier}"
            if qualified in task_states:
                raise TaskArtifactError(
                    f"duplicate local task ID: {identifier}")
            task_states[qualified] = state
    return [validate_task_graph(value, external_tasks=task_states)
            for value in graphs]


def validate_handoff_model(
    model: object, *, source: Optional[bytes | str] = None
) -> dict[str, Any]:
    """Validate a source-backed recovery snapshot with no lifecycle authority.

    ``source`` is mandatory because the normalized Markdown model does not retain
    field values or prose.  The canonical recovery-only declaration and exactly
    one ``Current task reference`` are checked in their raw section; metadata
    ``sources`` must equal that current task.
    """
    document, raw_metadata = _metadata(model, "handoff model")
    metadata = _exact(
        raw_metadata,
        {"schema_version", "id", "type", "sources", "snapshot_at"},
        "handoff metadata",
    )
    if type(metadata["schema_version"]) is not int or metadata["schema_version"] != 2:
        raise TaskArtifactError("handoff schema_version must be 2")
    if _HANDOFF_RE.fullmatch(_string(metadata["id"], "handoff id")) is None:
        raise TaskArtifactError("handoff id must use HANDOFF-N")
    if metadata["type"] != "handoff":
        raise TaskArtifactError("handoff type must be handoff")
    sources = _strings(metadata["sources"], "handoff sources", nonempty=True)
    if any(_QUALIFIED_TASK_RE.fullmatch(item) is None for item in sources):
        raise TaskArtifactError(
            "handoff sources must be qualified PLAN-N#TASK-N references")
    text = _bound_source_text(document, source, "handoff source")
    if text.count(_HANDOFF_DECLARATION) != 1:
        raise TaskArtifactError(
            "handoff requires the canonical recovery-only declaration")
    remaining = text.replace(_HANDOFF_DECLARATION, "", 1)
    if _HANDOFF_AUTHORITY_CLAIM_RE.search(remaining) is not None:
        raise TaskArtifactError("handoff cannot contain authoritative wording")
    lines = text.split("\n")
    current_start, current_end = _section_range(
        lines, "## Current task", "## Objective last progress")
    current = _canonical_fields(
        lines[current_start:current_end], ("Current task reference",),
        "handoff current task",
    )["Current task reference"]
    if _QUALIFIED_TASK_RE.fullmatch(current) is None:
        raise TaskArtifactError(
            "handoff current task must use PLAN-N#TASK-N")
    if sources != [current]:
        raise TaskArtifactError(
            "handoff sources must equal [current task reference]")
    timestamp = _string(metadata["snapshot_at"], "handoff snapshot_at")
    if _UTC_RE.fullmatch(timestamp) is None:
        raise TaskArtifactError(
            "handoff snapshot_at must be strict UTC date-time")
    try:
        parsed = _datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise TaskArtifactError(
            "handoff snapshot_at must be a real UTC date-time") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != timestamp:
        raise TaskArtifactError(
            "handoff snapshot_at must be canonical UTC date-time")
    if tuple(document["sections"]) != _HANDOFF_SECTIONS:
        raise TaskArtifactError(
            "handoff sections do not match the recovery snapshot contract")
    if document["local_ids"]:
        raise TaskArtifactError("handoff cannot declare local IDs")
    if any(_QUALIFIED_TASK_RE.fullmatch(reference) is None
           for reference in document["references"]):
        raise TaskArtifactError("handoff task references must be qualified")
    return document


def validate_fragment_model(model: object) -> dict[str, Any]:
    """Validate one normalized spec or plan fragment with exact parent identity."""
    document, raw_metadata = _metadata(model, "fragment model")
    metadata = _exact(
        raw_metadata,
        {"schema_version", "id", "type", "sources", "parent", "fragment_id"},
        "fragment metadata",
    )
    if type(metadata["schema_version"]) is not int or metadata["schema_version"] != 2:
        raise TaskArtifactError("fragment schema_version must be 2")
    kind = metadata["type"]
    if not isinstance(kind, str) or kind not in {
            "specification-fragment", "plan-fragment"}:
        raise TaskArtifactError("fragment type is invalid")
    identifier = _string(metadata["id"], "fragment id")
    match = _FRAGMENT_GLOBAL_RE.fullmatch(identifier)
    if match is None:
        raise TaskArtifactError(
            "fragment id must use SPEC-N-FRAG-N or PLAN-N-FRAG-N")
    expected_prefix = "SPEC" if kind == "specification-fragment" else "PLAN"
    if match.group(1) != expected_prefix:
        raise TaskArtifactError("fragment id prefix does not match type")
    parent = _string(metadata["parent"], "fragment parent")
    expected_parent = f"{match.group(1)}-{match.group(2)}"
    if parent != expected_parent:
        raise TaskArtifactError(
            "fragment parent does not match global fragment id")
    fragment_id = _string(metadata["fragment_id"], "fragment fragment_id")
    if _FRAGMENT_ID_RE.fullmatch(fragment_id) is None or fragment_id != f"FRAG-{match.group(3)}":
        raise TaskArtifactError(
            "fragment_id does not match global fragment id")
    sources = _strings(metadata["sources"], "fragment sources", nonempty=True)
    if sources != [parent]:
        raise TaskArtifactError("fragment sources must equal [parent]")
    if not document["sections"]:
        raise TaskArtifactError("fragment requires cohesive content sections")
    if kind == "plan-fragment" and document["local_ids"]:
        raise TaskArtifactError("plan fragments cannot declare local IDs")
    if kind == "specification-fragment":
        for item in document["local_ids"]:
            if item["kind"] not in {"requirement", "acceptance-criterion"}:
                raise TaskArtifactError(
                    "specification fragment local ID kind is invalid")
    for reference in document["references"]:
        if kind == "plan-fragment" and _QUALIFIED_REFERENCE_RE.fullmatch(reference) is None:
            raise TaskArtifactError(
                "plan fragment references must be qualified")
    return document


def _safe_path(value: object, label: str) -> str:
    path = _string(value, label)
    if (len(path) > 500 or path.startswith("/") or path.endswith("/") or "\\" in path
            or "//" in path or _WINDOWS_DRIVE_RE.match(path) is not None
            or any(part in {"", ".", ".."} for part in path.split("/"))
            or any(ord(character) < 32 or ord(character) == 127 for character in path)):
        raise TaskArtifactError(f"{label} must be a safe relative path")
    return path


def validate_fragment_set(parent: object, children: object) -> list[dict[str, Any]]:
    """Validate reciprocal parent children in declared navigation order.

    ``parent`` is a compact ``id``/``type`` descriptor with an optional
    ``children`` array of ``{"id", "path"}`` records.  Each supplied child is a
    ``{"path", "model"}`` record.  Omitting ``children`` and supplying no child
    is the valid cohesive no-split case.
    """
    parent_record = _object(parent, "fragment parent")
    if "metadata" in parent_record:
        parent_record = _object(
            parent_record["metadata"], "fragment parent metadata")
    if "id" not in parent_record or "type" not in parent_record:
        raise TaskArtifactError("fragment parent requires id and type")
    parent_id = _string(parent_record["id"], "fragment parent id")
    parent_type = parent_record["type"]
    if not isinstance(parent_type, str) or parent_type not in {"specification", "plan"}:
        raise TaskArtifactError(
            "fragment parent type must be specification or plan")
    expected_prefix = "SPEC" if parent_type == "specification" else "PLAN"
    if re.fullmatch(rf"{expected_prefix}-[0-9]+", parent_id) is None:
        raise TaskArtifactError(
            "fragment parent id does not match parent type")
    declarations = _array(parent_record.get(
        "children", []), "fragment parent children")
    supplied = _array(children, "fragment children")
    if len(declarations) != len(supplied):
        raise TaskArtifactError(
            "fragment parent and supplied child counts differ")
    declared_ids: set[str] = set()
    declared_paths: set[str] = set()
    normalized_declarations: list[tuple[str, str]] = []
    for index, raw in enumerate(declarations):
        item = _exact(raw, {"id", "path"},
                      f"fragment parent children[{index}]")
        child_id = _string(item["id"], f"fragment parent children[{index}].id")
        path = _safe_path(
            item["path"], f"fragment parent children[{index}].path")
        if child_id in declared_ids or path in declared_paths:
            raise TaskArtifactError(
                "fragment parent children must have unique IDs and paths")
        declared_ids.add(child_id)
        declared_paths.add(path)
        normalized_declarations.append((child_id, path))

    normalized_children: list[dict[str, Any]] = []
    for index, raw in enumerate(supplied):
        item = _exact(raw, {"path", "model"}, f"fragment children[{index}]")
        path = _safe_path(item["path"], f"fragment children[{index}].path")
        model = validate_fragment_model(item["model"])
        child_id = model["metadata"]["id"]
        if model["metadata"]["parent"] != parent_id:
            raise TaskArtifactError("fragment child parent is not reciprocal")
        if (child_id, path) != normalized_declarations[index]:
            raise TaskArtifactError(
                "fragment children do not match parent order")
        expected_kind = f"{parent_type}-fragment" if parent_type == "specification" else "plan-fragment"
        if model["metadata"]["type"] != expected_kind:
            raise TaskArtifactError(
                "fragment child type does not match parent")
        normalized_children.append({"path": path, "model": model})
    return normalized_children


def _repository_file(root: Path, relative: str, label: str) -> Path:
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    try:
        current = root
        for part in PurePosixPath(relative).parts:
            current = current / part
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise TaskArtifactError(f"{label} traverses a symlink")
        file_info = candidate.lstat()
        if not stat.S_ISREG(file_info.st_mode):
            raise TaskArtifactError(f"{label} must be a regular file")
        if file_info.st_size > MAX_STRING_LENGTH * 10:
            raise TaskArtifactError(f"{label} exceeds the file size limit")
    except TaskArtifactError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise TaskArtifactError(f"{label} cannot be inspected safely") from exc
    return candidate


def _fragment_scope_files(root: Path, scope_relative: str) -> list[str]:
    scope = root.joinpath(*PurePosixPath(scope_relative).parts)
    try:
        current = root
        for part in PurePosixPath(scope_relative).parts:
            current = current / part
            if not current.exists():
                return []
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise TaskArtifactError("fragment scope traverses a symlink")
        if not stat.S_ISDIR(scope.lstat().st_mode):
            raise TaskArtifactError("fragment scope must be a directory")
        discovered: list[str] = []
        with os.scandir(scope) as entries:
            for entry in entries:
                if not entry.name.endswith(".md"):
                    continue
                if len(discovered) >= MAX_COLLECTION_ITEMS:
                    raise TaskArtifactError(
                        "fragment scope exceeds the collection limit")
                if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                    raise TaskArtifactError(
                        "fragment scope Markdown entries must be regular files")
                discovered.append(
                    f"{scope_relative}/{entry.name}" if scope_relative else entry.name)
        return sorted(discovered)
    except TaskArtifactError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise TaskArtifactError(
            "fragment scope cannot be inspected safely") from exc


def load_fragment_set(catalog_root: object, parent_path: object) -> dict[str, Any]:
    """Load and validate one parent and its fragments below ``catalog_root``.

    Args:
        catalog_root: Repository root containing the additive artifact catalog.
            Its lexical root and ancestors must not be symlinks.
        parent_path: Safe repository-relative path to a v2 specification or plan.
            Declared children must be direct ``.md`` files in the sibling
            ``fragments`` directory and are loaded in declaration order.

    Returns:
        A normalized ``path``/``model`` parent record and reciprocal children.

    Raises:
        TaskArtifactError: The root, any path, file kind, owner model, schema,
            declaration, sibling discovery, or reciprocal relationship is
            malformed.  The operation is read-only and performs no discovery
            outside the one sibling ``fragments`` directory.
    """
    if not isinstance(catalog_root, (str, os.PathLike)):
        raise TaskArtifactError("catalog_root must be a filesystem path")
    parent_relative = _safe_path(parent_path, "fragment parent path")
    try:
        from scripts.contracts import catalog, markdown, schema, source_lifecycle

        lexical_root = Path(os.path.abspath(os.fspath(catalog_root)))
        contracts = {
            item.id: item for item in catalog.resolve_artifact_contracts(lexical_root)
        }
        registry_path = _repository_file(
            lexical_root, ".agents/schemas/markdown-document.schema.json",
            "Markdown schema",
        )
        registry = [catalog.load_json(registry_path)]
        allowed_metadata = {
            "schema_version", "id", "type", "sources", "namespace",
            "snapshot_at", "parent", "fragment_id", "status", "children",
            "depends_on", "source_revisions", "risk", "risk_rationale",
        }

        def parse_owner(relative: str, artifact_id: str) -> tuple[dict[str, Any], bytes]:
            path = _repository_file(lexical_root, relative, artifact_id)
            source = path.read_bytes()
            model = markdown.parse_markdown(
                source, allowed_metadata_keys=allowed_metadata)
            contract = contracts.get(artifact_id)
            if contract is None:
                raise TaskArtifactError(
                    f"artifact catalog is missing {artifact_id}")
            variants = [variant for variant in contract.variants
                        if variant.schema_version == 2]
            if len(variants) != 1 or variants[0].schema is None:
                raise TaskArtifactError(
                    f"artifact catalog requires one {artifact_id} v2 schema")
            decision = schema.validate(
                model, catalog.load_json(variants[0].schema), registry=registry)
            if not decision.valid:
                raise TaskArtifactError(
                    f"{artifact_id} owner model violates its v2 schema")
            return model, source

        parent_file = _repository_file(
            lexical_root, parent_relative, "fragment parent")
        parent_source = parent_file.read_bytes()
        parent_model = markdown.parse_markdown(
            parent_source, allowed_metadata_keys=allowed_metadata)
        raw_metadata = _object(
            parent_model.get("metadata"), "fragment parent metadata")
        parent_type = raw_metadata.get("type")
        if parent_type not in {"specification", "plan"}:
            raise TaskArtifactError(
                "fragment parent type must be specification or plan")
        parent_artifact = "specification" if parent_type == "specification" else "plan"
        # Parse the parent again through its catalog-selected owner schema so the
        # filesystem entry point cannot bypass structural validation.
        parent_model, _ = parse_owner(parent_relative, parent_artifact)
        if parent_type == "specification":
            source_lifecycle.validate_specification_model(parent_model)
            child_artifact = "specification-fragment"
        else:
            source_lifecycle.validate_plan_model(parent_model)
            child_artifact = "plan-fragment"

        declarations = _array(
            parent_model["metadata"].get("children", []),
            "fragment parent children")
        parent_posix = PurePosixPath(parent_relative)
        scope = parent_posix.parent / "fragments"
        scope_relative = scope.as_posix()
        supplied: list[dict[str, Any]] = []
        declared_paths: list[str] = []
        for index, declaration in enumerate(declarations):
            item = _exact(
                declaration, {"id", "path"},
                f"fragment parent children[{index}]")
            child_relative = _safe_path(
                item["path"], f"fragment parent children[{index}].path")
            child_posix = PurePosixPath(child_relative)
            if child_posix.parent != scope or child_posix.suffix != ".md":
                raise TaskArtifactError(
                    "fragment children must be direct Markdown siblings in fragments")
            child_model, _ = parse_owner(child_relative, child_artifact)
            declared_paths.append(child_relative)
            supplied.append({"path": child_relative, "model": child_model})
        discovered = _fragment_scope_files(
            lexical_root, scope_relative)
        if discovered != sorted(declared_paths):
            raise TaskArtifactError(
                "declared and discovered fragment sibling paths differ")
        children = validate_fragment_set(parent_model, supplied)
        return {
            "path": parent_relative,
            "model": parent_model,
            "children": children,
        }
    except TaskArtifactError:
        raise
    except Exception as exc:
        # All parser/schema/catalog/filesystem implementations used here expose
        # typed ValueError/OSError failures.  Normalize them at this public trust
        # boundary so malformed JSON-like or filesystem input never leaks a
        # traceback-specific exception contract.
        raise TaskArtifactError(
            f"fragment filesystem validation failed: {type(exc).__name__}") from exc


def assess_split(token_count: object, warning_tokens: object, *, cohesive: object) -> dict[str, bool]:
    """Return an advisory split warning; token thresholds never require a split."""
    if type(token_count) is not int or token_count < 0:
        raise TaskArtifactError("token_count must be a non-negative integer")
    if warning_tokens is not None and (type(warning_tokens) is not int or warning_tokens < 1):
        raise TaskArtifactError(
            "warning_tokens must be null or a positive integer")
    if type(cohesive) is not bool:
        raise TaskArtifactError("cohesive must be a boolean")
    warning = warning_tokens is not None and token_count > warning_tokens
    return {"warning": warning, "split_required": False}

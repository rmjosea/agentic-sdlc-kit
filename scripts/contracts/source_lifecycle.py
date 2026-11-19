"""Evaluate v2 spec/plan lifecycle and source freshness in memory.

This source-only module complements the bounded schema and Markdown parsers.  It
checks relationships that the supported JSON Schema profile cannot express:
source-map keys must agree with source IDs, plan sources must have one matching
revision record, and freshness compares the plan record, owner-local companion,
and current fingerprint.  It performs no filesystem, Git, network, or mutation
operations.

Call :func:`assess_plan_freshness` with fingerprints produced by
``.agents/tools/fingerprint_artifact.py``.  Call :func:`verify_spec_seal` with a
previously accepted seal; evidence owns the eventual persisted seal shape.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any, Collection, Mapping


ARTIFACT_ID_RE = re.compile(r"^[A-Z]+-[0-9]+(?:-[A-Z]+-[0-9]+)?$")
QUALIFIED_SOURCE_ITEM_RE = re.compile(
    r"^([A-Z]+-[0-9]+(?:-[A-Z]+-[0-9]+)?)#(?:REQ|AC)-[0-9]+$")
QUALIFIED_REFERENCE_RE = re.compile(
    r"^[A-Z]+-[0-9]+(?:-[A-Z]+-[0-9]+)?#(?:REQ|AC|TASK)-[0-9]+$")
LOCAL_REFERENCE_RE = re.compile(r"^(?:REQ|AC|TASK)-[0-9]+$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
MAX_COLLECTION_ITEMS = 10000
MAX_TOTAL_ITEMS = 50000
MAX_STRING_LENGTH = 100000
TRANSITIONS = {
    "specification": frozenset({
        ("draft", "approved"),
        ("approved", "implemented"),
        ("implemented", "verified"),
    }),
    "plan": frozenset({
        ("draft", "approved"),
        ("approved", "stale"),
        ("approved", "implemented"),
        ("stale", "approved"),
    }),
}
SPEC_SECTIONS = (
    "Context", "Confirmed rationale", "Outcome", "Actors and scenarios",
    "Scope", "In scope", "Out of scope", "Requirements", "Business rules",
    "Failure behavior and edge cases", "Quality constraints",
    "Dependencies and confirmed constraints", "Acceptance criteria",
    "Open questions",
)
PLAN_SECTIONS = (
    "Goal and source intent", "Repository findings and facts",
    "Confirmed constraints", "Assumptions", "Agent inferences", "Unknowns",
    "Confirmed technical decisions and rationale", "Design summary",
    "Native interface contracts", "Source coverage and impact map",
    "Verification strategy", "Risks and mitigations", "Open questions",
)


class SourceLifecycleError(ValueError):
    """A lifecycle, source relationship, fingerprint, or seal is malformed."""


def transition_allowed(artifact_type: str, before: str, after: str) -> bool:
    """Return whether one explicit v2 lifecycle transition is legal.

    Unknown string artifact types or statuses return ``False``. Repeating the
    current status is not a transition. Non-string JSON values are malformed.
    """
    if not all(isinstance(value, str) for value in (artifact_type, before, after)):
        raise SourceLifecycleError("lifecycle type and states must be strings")
    return (before, after) in TRANSITIONS.get(artifact_type, frozenset())


def require_transition(artifact_type: str, before: str, after: str) -> None:
    """Raise :class:`SourceLifecycleError` unless the transition is legal."""
    if not transition_allowed(artifact_type, before, after):
        raise SourceLifecycleError(
            f"forbidden {artifact_type} transition: {before} -> {after}")


def _string_key_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SourceLifecycleError(f"{label} must be an object")
    if len(value) > MAX_COLLECTION_ITEMS:
        raise SourceLifecycleError(f"{label} exceeds the collection limit")
    if any(not isinstance(key, str) for key in value):
        raise SourceLifecycleError(f"{label} keys must be strings")
    if any(len(key) > MAX_STRING_LENGTH for key in value):
        raise SourceLifecycleError(f"{label} key exceeds the string limit")
    return value


def _exact_mapping(value: object, fields: set[str], label: str) -> Mapping[str, Any]:
    record = _string_key_mapping(value, label)
    actual = set(record)
    missing = sorted(fields - actual)
    unknown = sorted(actual - fields)
    if missing:
        raise SourceLifecycleError(f"{label} missing field: {missing[0]}")
    if unknown:
        raise SourceLifecycleError(f"{label} unknown field: {unknown[0]}")
    return record


def _exact_mapping_with_optional(
    value: object, fields: set[str], optional: set[str], label: str
) -> Mapping[str, Any]:
    record = _string_key_mapping(value, label)
    actual = set(record)
    missing = sorted(fields - actual)
    unknown = sorted(actual - fields - optional)
    if missing:
        raise SourceLifecycleError(f"{label} missing field: {missing[0]}")
    if unknown:
        raise SourceLifecycleError(f"{label} unknown field: {unknown[0]}")
    return record


def _string_sequence(
    value: object, label: str, *, nonempty: bool = False
) -> list[str]:
    if not isinstance(value, list):
        raise SourceLifecycleError(f"{label} must be an array")
    if len(value) > MAX_COLLECTION_ITEMS:
        raise SourceLifecycleError(f"{label} exceeds the collection limit")
    if nonempty and not value:
        raise SourceLifecycleError(f"{label} must be non-empty")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise SourceLifecycleError(
            f"{label} entries must be non-empty strings")
    if any(len(item) > MAX_STRING_LENGTH for item in value):
        raise SourceLifecycleError(f"{label} entry exceeds the string limit")
    return value


def _string_list(
    value: object, label: str, *, nonempty: bool = False
) -> list[str]:
    result = _string_sequence(value, label, nonempty=nonempty)
    if len(result) != len(set(result)):
        raise SourceLifecycleError(f"{label} entries must be unique")
    return result


def _require_exact_keys(
    value: object, expected: set[str], label: str
) -> Mapping[str, Any]:
    record = _string_key_mapping(value, label)
    actual = set(record)
    if actual != expected:
        missing = ",".join(sorted(expected - actual)) or "none"
        extra = ",".join(sorted(actual - expected)) or "none"
        raise SourceLifecycleError(
            f"{label} keys must match exactly: missing={missing}; extra={extra}")
    return record


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or DIGEST_RE.fullmatch(value) is None:
        raise SourceLifecycleError(f"{label} must be a SHA-256 digest")
    return value


def _artifact_id(value: object, label: str) -> str:
    if not isinstance(value, str) or ARTIFACT_ID_RE.fullmatch(value) is None:
        raise SourceLifecycleError(f"{label} must be a global artifact ID")
    return value


def _nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SourceLifecycleError(f"{label} must be a non-empty string")
    if len(value) > MAX_STRING_LENGTH:
        raise SourceLifecycleError(f"{label} exceeds the string limit")
    return value


def _fingerprint_payload(
    value: object,
    label: str,
    *,
    require_schema_version: bool,
    require_items: bool = False,
) -> dict[str, Any]:
    fields = {"source_id", "source_revision", "item_revisions"}
    if require_schema_version:
        fields.add("schema_version")
    record = _exact_mapping(value, fields, label)
    if require_schema_version and (
        type(record["schema_version"]
             ) is not int or record["schema_version"] != 2
    ):
        raise SourceLifecycleError(f"{label}.schema_version must be 2")
    source_id = _artifact_id(record["source_id"], f"{label}.source_id")
    source_revision = _digest(
        record["source_revision"], f"{label}.source_revision")
    raw_items = _string_key_mapping(
        record["item_revisions"], f"{label}.item_revisions")
    if require_items and not raw_items:
        raise SourceLifecycleError(
            f"{label}.item_revisions requires at least one REQ/AC item")
    item_revisions: dict[str, str] = {}
    for item_id in sorted(raw_items):
        match = QUALIFIED_SOURCE_ITEM_RE.fullmatch(item_id)
        if match is None or match.group(1) != source_id:
            raise SourceLifecycleError(
                f"{label}.item_revisions key must be qualified by source_id")
        item_revisions[item_id] = _digest(
            raw_items[item_id], f"{label}.item_revisions[{item_id}]")
    return {
        "source_id": source_id,
        "source_revision": source_revision,
        "item_revisions": item_revisions,
    }


def validate_source_fingerprint_map(value: object) -> dict[str, Any]:
    """Validate and return one normalized closed source-fingerprint companion.

    This semantic check supplements the owner JSON schema by requiring every
    qualified REQ/AC key to use the record's exact ``source_id``.
    """
    normalized = _fingerprint_payload(
        value, "source fingerprint map", require_schema_version=True,
        require_items=True)
    return {"schema_version": 2, **normalized}


def validate_specification_model(model: object) -> Mapping[str, Any]:
    """Check semantic constraints of a parsed specification model."""
    document = _exact_mapping(
        model,
        {"metadata", "h1", "sections", "local_ids", "references", "placeholders"},
        "specification model",
    )
    metadata = _exact_mapping_with_optional(
        document["metadata"],
        {"schema_version", "id", "type", "sources", "status", "depends_on"},
        {"children"},
        "specification metadata",
    )
    if (type(metadata["schema_version"]) is not int
            or metadata["schema_version"] != 2
            or not isinstance(metadata["type"], str)
            or metadata["type"] != "specification"):
        raise SourceLifecycleError("specification identity is invalid")
    status = metadata["status"]
    if not isinstance(status, str) or status not in {
        "draft", "approved", "implemented", "verified"
    }:
        raise SourceLifecycleError("specification status is invalid")
    _string_list(metadata["sources"], "specification sources", nonempty=True)
    depends_on = _string_list(
        metadata["depends_on"], "specification depends_on")
    if any(not item.startswith("SPEC-")
           or ARTIFACT_ID_RE.fullmatch(item) is None for item in depends_on):
        raise SourceLifecycleError(
            "specification depends_on must contain spec IDs")
    identifier = _artifact_id(metadata["id"], "specification id")
    if not identifier.startswith("SPEC-") or identifier.count("-") != 1:
        raise SourceLifecycleError("specification id must use SPEC-NNN")
    if "children" in metadata:
        _validate_fragment_children(metadata["children"], identifier, "SPEC")
    _nonempty_string(document["h1"], "specification h1")
    sections = _string_sequence(
        document["sections"], "specification sections", nonempty=True)
    if tuple(sections) != SPEC_SECTIONS:
        raise SourceLifecycleError(
            "specification sections do not match the v2 contract")
    local_ids = document["local_ids"]
    if not isinstance(local_ids, list) or len(local_ids) > MAX_COLLECTION_ITEMS:
        raise SourceLifecycleError(
            "specification local_ids must be a bounded array")
    kinds: set[str] = set()
    for index, value in enumerate(local_ids):
        item = _exact_mapping(
            value, {"kind", "id"}, f"specification local_ids[{index}]")
        if not isinstance(item["kind"], str) or not isinstance(item["id"], str):
            raise SourceLifecycleError(
                "specification local ID fields must be strings")
        kinds.add(item["kind"])
    if not {"requirement", "acceptance-criterion"}.issubset(kinds):
        raise SourceLifecycleError(
            "specification requires REQ and AC declarations")
    references = _string_list(
        document["references"], "specification references")
    if any(LOCAL_REFERENCE_RE.fullmatch(reference) is None
           and QUALIFIED_REFERENCE_RE.fullmatch(reference) is None
           for reference in references):
        raise SourceLifecycleError("specification reference is malformed")
    _string_list(document["placeholders"], "specification placeholders")
    return document


def validate_plan_model(model: object) -> Mapping[str, Any]:
    """Check parsed plan sections and exact source/source-revision relationships."""
    document = _exact_mapping(
        model,
        {"metadata", "h1", "sections", "local_ids", "references", "placeholders"},
        "plan model",
    )
    metadata = _exact_mapping_with_optional(
        document["metadata"],
        {"schema_version", "id", "type", "sources", "source_revisions",
         "status", "risk", "risk_rationale"},
        {"children"},
        "plan metadata",
    )
    _validate_plan_metadata(metadata)
    _nonempty_string(document["h1"], "plan h1")
    sections = _string_sequence(
        document["sections"], "plan sections", nonempty=True)
    if tuple(sections) != PLAN_SECTIONS:
        raise SourceLifecycleError(
            "plan sections do not match the v2 contract")
    local_ids = document["local_ids"]
    if not isinstance(local_ids, list) or local_ids:
        raise SourceLifecycleError("plan local_ids must be an empty array")
    references = _string_list(document["references"], "plan references")
    if any(LOCAL_REFERENCE_RE.fullmatch(reference) is not None
           for reference in references):
        raise SourceLifecycleError(
            "plan contains a local reference; qualify every REQ/AC/TASK reference")
    if any(QUALIFIED_REFERENCE_RE.fullmatch(reference) is None
           for reference in references):
        raise SourceLifecycleError("plan reference is malformed")
    if any(
        not any(reference.startswith(f"{source_id}#")
                for reference in references)
        for source_id in metadata["sources"]
    ):
        raise SourceLifecycleError(
            "plan coverage must qualify an item from every source")
    _string_list(document["placeholders"], "plan placeholders")
    return document


def _safe_relative_path(value: object) -> bool:
    if (not isinstance(value, str) or not value or len(value) > 500
            or "\\" in value or re.match(r"^[A-Za-z]:", value) is not None
            or any(ord(character) < 32 or ord(character) == 127 for character in value)
            or "<" in value or ">" in value):
        return False
    path = PurePosixPath(value)
    return (not path.is_absolute() and not value.endswith("/") and "//" not in value
            and all(part not in {"", ".", ".."} for part in value.split("/")))


def _validate_fragment_children(
    value: object, parent_id: str, prefix: str
) -> list[dict[str, str]]:
    raw_children = value
    if not isinstance(raw_children, list):
        raise SourceLifecycleError("fragment children must be an array")
    if len(raw_children) > MAX_COLLECTION_ITEMS:
        raise SourceLifecycleError(
            "fragment children exceeds the collection limit")
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    normalized: list[dict[str, str]] = []
    for index, raw_child in enumerate(raw_children):
        child = _exact_mapping(
            raw_child, {"id", "path"}, f"fragment children[{index}]")
        child_id = _artifact_id(child["id"], f"fragment children[{index}].id")
        expected = rf"{re.escape(parent_id)}-FRAG-[0-9]+"
        if prefix not in {"SPEC", "PLAN"} or re.fullmatch(expected, child_id) is None:
            raise SourceLifecycleError(
                "fragment child ID must belong to its parent")
        path = child["path"]
        if not _safe_relative_path(path):
            raise SourceLifecycleError(
                "fragment child path must be safe and relative")
        assert isinstance(path, str)
        if child_id in seen_ids or path in seen_paths:
            raise SourceLifecycleError(
                "fragment children IDs and paths must be unique")
        seen_ids.add(child_id)
        seen_paths.add(path)
        normalized.append({"id": child_id, "path": path})
    return normalized


def _validate_plan_metadata(metadata: object) -> Mapping[str, Any]:
    record = _exact_mapping_with_optional(
        metadata,
        {"schema_version", "id", "type", "sources", "source_revisions",
         "status", "risk", "risk_rationale"},
        {"children"},
        "plan metadata",
    )
    if (type(record["schema_version"]) is not int
            or record["schema_version"] != 2
            or not isinstance(record["type"], str)
            or record["type"] != "plan"):
        raise SourceLifecycleError("plan identity is invalid")
    status = record["status"]
    if not isinstance(status, str) or status not in {
        "draft", "approved", "stale", "implemented"
    }:
        raise SourceLifecycleError("plan status is invalid")
    risk = record["risk"]
    if not isinstance(risk, str) or risk not in {"low", "medium", "high"}:
        raise SourceLifecycleError("plan risk is invalid")
    _nonempty_string(record["risk_rationale"], "plan risk_rationale")
    identifier = _artifact_id(record["id"], "plan id")
    if not identifier.startswith("PLAN-") or identifier.count("-") != 1:
        raise SourceLifecycleError("plan id must use PLAN-NNN")
    if "children" in record:
        _validate_fragment_children(record["children"], identifier, "PLAN")
    sources = _string_list(record["sources"], "plan sources", nonempty=True)
    for source_id in sources:
        _artifact_id(source_id, "plan source")
    revisions = _string_key_mapping(
        record["source_revisions"], "plan source_revisions")
    if set(revisions) != set(sources):
        raise SourceLifecycleError(
            "plan sources and source_revisions keys must match exactly")
    companion_paths: set[str] = set()
    for source_id in sources:
        _artifact_id(source_id, "plan source")
        source = _exact_mapping(
            revisions[source_id], {"source_revision", "source_items"},
            f"plan source_revisions[{source_id}]",
        )
        _digest(source["source_revision"], "plan source revision")
        path = source["source_items"]
        if not _safe_relative_path(path) or path in companion_paths:
            raise SourceLifecycleError(
                "plan source_items must be unique safe relative paths")
        companion_paths.add(path)
    return record


def _coverage_map(value: object) -> dict[str, list[str]]:
    coverage = _string_key_mapping(value, "coverage")
    result: dict[str, list[str]] = {}
    total_targets = 0
    for item_id in sorted(coverage):
        if QUALIFIED_SOURCE_ITEM_RE.fullmatch(item_id) is None:
            raise SourceLifecycleError(
                "coverage keys must be qualified source item IDs")
        targets = _string_list(
            coverage[item_id], f"coverage[{item_id}] targets")
        total_targets += len(targets)
        if total_targets > MAX_TOTAL_ITEMS:
            raise SourceLifecycleError("coverage exceeds the total item limit")
        result[item_id] = sorted(targets)
    return result


def assess_plan_freshness(
    metadata: object,
    companions: Mapping[str, object],
    current_fingerprints: Mapping[str, object],
    coverage: Mapping[str, Collection[str]],
) -> dict[str, Any]:
    """Compare an exact plan source record with companions and current sources.

    Args:
        metadata: Parsed v2 plan metadata.
        companions: Owner-local companion values keyed by ``source_items`` path.
        current_fingerprints: Current fingerprint-tool results keyed by source ID.
        coverage: Qualified source item to affected plan-area/task identifiers.

    Returns:
        A deterministic JSON-compatible freshness and impact report. An approved
        mismatching plan has effective status ``stale``; an implemented plan is
        historical and never reopens. A fresh stale plan is only *eligible* for
        explicit reconciliation to approved.

    Raises:
        SourceLifecycleError: Any supplied shape or cross-record identity is
            malformed. Ordinary content mismatches are returned in the report.
    """
    plan = _validate_plan_metadata(metadata)
    source_ids = set(plan["sources"])
    expected_paths = {
        plan["source_revisions"][source_id]["source_items"]
        for source_id in plan["sources"]
    }
    companion_records = _require_exact_keys(
        companions, expected_paths, "companions")
    current_records = _require_exact_keys(
        current_fingerprints, source_ids, "current_fingerprints")
    coverage_map = _coverage_map(coverage)
    if any(item_id.split("#", 1)[0] not in source_ids for item_id in coverage_map):
        raise SourceLifecycleError(
            "coverage items must belong to a plan source")
    changed: set[str] = set()
    removed: set[str] = set()
    new: set[str] = set()
    unchanged: set[str] = set()
    current_items: set[str] = set()
    source_states: dict[str, dict[str, Any]] = {}
    records_match = True
    total_fingerprint_items = 0
    for source_id in sorted(plan["sources"]):
        source_record = plan["source_revisions"][source_id]
        path = source_record["source_items"]
        companion = _fingerprint_payload(
            companion_records[path], f"companion {path}",
            require_schema_version=True, require_items=True)
        current_value = current_records[source_id]
        require_version = isinstance(
            current_value, Mapping) and "schema_version" in current_value
        current = _fingerprint_payload(
            current_value, f"current fingerprint {source_id}",
            require_schema_version=require_version,
        )
        total_fingerprint_items += (
            len(companion["item_revisions"]) + len(current["item_revisions"]))
        if total_fingerprint_items > MAX_TOTAL_ITEMS:
            raise SourceLifecycleError(
                "freshness fingerprints exceed the total item limit")
        if companion["source_id"] != source_id or current["source_id"] != source_id:
            raise SourceLifecycleError(
                "source key, companion, and current source_id must match")
        frontmatter_matches = source_record["source_revision"] == companion["source_revision"]
        revision_matches = companion["source_revision"] == current["source_revision"]
        expected_items = companion["item_revisions"]
        actual_items = current["item_revisions"]
        current_items.update(actual_items)
        local_changed = sorted(
            item for item in expected_items.keys() & actual_items.keys()
            if expected_items[item] != actual_items[item])
        local_removed = sorted(expected_items.keys() - actual_items.keys())
        local_new = sorted(actual_items.keys() - expected_items.keys())
        local_unchanged = sorted(
            item for item in expected_items.keys() & actual_items.keys()
            if expected_items[item] == actual_items[item])
        items_match = not local_changed and not local_removed and not local_new
        source_match = frontmatter_matches and revision_matches and items_match
        records_match = records_match and source_match
        changed.update(local_changed)
        removed.update(local_removed)
        new.update(local_new)
        unchanged.update(local_unchanged)
        source_states[source_id] = {
            "fresh": source_match,
            "frontmatter_matches_companion": frontmatter_matches,
            "revision_matches_current": revision_matches,
            "items_match_current": items_match,
        }
    changed_items = sorted(changed)
    removed_items = sorted(removed)
    new_items = sorted(new)
    affected_items = sorted(changed | removed | new)
    unaffected_items = sorted(unchanged)
    affected_targets = {
        item: coverage_map.get(item, []) for item in affected_items
    }
    unmapped_items = sorted(current_items - coverage_map.keys())
    coverage_complete = not unmapped_items
    fresh = records_match and coverage_complete
    status = plan["status"]
    effective_status = (
        "implemented" if status == "implemented"
        else "stale" if status in ("approved", "stale") and not fresh
        else status
    )
    eligible_transition = (
        "approved" if status == "stale" and fresh else None)
    planned = status == "approved" and fresh
    return {
        "fresh": fresh,
        "source_fresh": records_match,
        "coverage_complete": coverage_complete,
        "planned": planned,
        "can_implement": planned,
        "effective_status": effective_status,
        "eligible_transition": eligible_transition,
        "reopen": False,
        "source_states": source_states,
        "changed_items": changed_items,
        "removed_items": removed_items,
        "new_items": new_items,
        "affected_items": affected_items,
        "unaffected_items": unaffected_items,
        "affected_targets": affected_targets,
        "unaffected_targets": {
            item: coverage_map.get(item, []) for item in unaffected_items
        },
        "unmapped_items": unmapped_items,
        "unmapped_new_items": [item for item in new_items if item not in coverage_map],
    }


def verify_spec_seal(
    status: str, current_fingerprint: object, sealed_fingerprint: object
) -> dict[str, Any]:
    """Compare current spec semantics with an accepted seal input.

    Seals are enforced only when ``status`` is ``verified``. This keeps the API
    independent of the future evidence-v2 persisted shape while still making a
    verified spec terminal and detecting overall, changed, removed, or new item
    mutations.
    """
    if not isinstance(status, str) or status not in {
        "draft", "approved", "implemented", "verified"
    }:
        raise SourceLifecycleError("specification status is invalid")
    current_versioned = (
        isinstance(current_fingerprint, Mapping)
        and "schema_version" in current_fingerprint)
    sealed_versioned = (
        isinstance(sealed_fingerprint, Mapping)
        and "schema_version" in sealed_fingerprint)
    current = _fingerprint_payload(
        current_fingerprint, "current spec fingerprint",
        require_schema_version=current_versioned,
    )
    sealed = _fingerprint_payload(
        sealed_fingerprint, "sealed spec fingerprint",
        require_schema_version=sealed_versioned, require_items=True,
    )
    if current["source_id"] != sealed["source_id"]:
        raise SourceLifecycleError("current and sealed spec IDs must match")
    current_items = current["item_revisions"]
    sealed_items = sealed["item_revisions"]
    changed_items = sorted(
        item for item in current_items.keys() & sealed_items.keys()
        if current_items[item] != sealed_items[item])
    removed_items = sorted(sealed_items.keys() - current_items.keys())
    new_items = sorted(current_items.keys() - sealed_items.keys())
    revision_changed = current["source_revision"] != sealed["source_revision"]
    matches = not revision_changed and not changed_items and not removed_items and not new_items
    enforced = status == "verified"
    return {
        "valid": matches or not enforced,
        "enforced": enforced,
        "revision_changed": revision_changed,
        "changed_items": changed_items,
        "removed_items": removed_items,
        "new_items": new_items,
    }

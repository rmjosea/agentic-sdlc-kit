"""Validate additive v2 review, evidence, and compliance contracts in memory.

The public functions consume normalized Markdown models, JSON-like records, or
UTF-8 JSONL text. They perform no filesystem, Git, subprocess, network, dynamic
import, authentication, approval-policy migration, or mutation operation.
Structural schemas remain owner-local; this module enforces source-backed
section fields, adaptive ownership, evidence truthfulness, and ordered audit-log
semantics that the repository's bounded JSON Schema profile cannot express.

Malformed and resource-exhausting input raises :class:`ReviewEvidenceError`
with a deterministic non-sensitive message. Actor and reviewer identifiers are
only declarations; successful validation is not cryptographic or legal proof.
"""

from __future__ import annotations

import datetime as _datetime
import hashlib
import json
import math
import re
from typing import Any, Iterable, Optional

from scripts.contracts import markdown


MAX_ITEMS = 10_000
MAX_OBJECT_FIELDS = 1_000
MAX_STRING = 100_000
MAX_SOURCE_BYTES = 1_000_000
MAX_AUDIT_BYTES = MAX_SOURCE_BYTES * 10
MAX_AUDIT_EVENTS = 10_000

SIGNALS = (
    "Correctness", "Security", "Compatibility", "Maintainability", "Performance",
    "Accessibility", "Observability", "Cost", "Understandability",
)
STANDALONE_SECTIONS = (
    "Scope", "Reviewer role and independence", "Authoritative sources", "Risk",
    "Change contract and review focus", "Selected quality signals",
    "Checks and evidence", "Findings", "Acceptance coverage", "Residual risk",
    "Verdict",
)
EVIDENCE_REVIEW_SECTIONS = (
    "Evidence reference", "Findings", "Acceptance gaps", "Residual risk", "Verdict",
)
FORBIDDEN_EVIDENCE_SECTIONS = frozenset({
    "Scope", "Reviewer role and independence", "Authoritative sources", "Risk",
    "Change contract and review focus", "Selected quality signals",
    "Checks and evidence", "Acceptance coverage",
})

_DOCUMENT_FIELDS = {
    "metadata", "h1", "sections", "local_ids", "references", "placeholders",
}
_STANDALONE_METADATA = {"schema_version", "id", "type", "sources", "verdict"}
_EVIDENCE_METADATA = _STANDALONE_METADATA | {"evidence_reference"}
_EVIDENCE_FIELDS = {
    "schema_version", "id", "change_id", "authoritative_sources", "lifecycle",
    "risk", "change_contract", "repository_scope", "source_seals",
    "requirement_coverage", "quality_signals", "checks", "review", "known_limits",
    "remaining_risks", "follow_ups",
}
_REPOSITORY_FIELDS = {
    "repository_id", "base", "head", "committed_range", "uncommitted_entries",
    "snapshot_sha256",
}
_CHECK_FIELDS = {
    "id", "requirement_ids", "repository_ids", "kind", "required", "applicability",
    "not_applicable_reason", "status", "observed_result", "evidence_class",
    "output_reference",
}
_AUDIT_FIELDS = (
    "schema_version", "event_id", "sequence", "timestamp", "change_id", "actor",
    "action", "previous_lifecycle", "new_lifecycle",
    "authoritative_source_references", "evidence_references", "approvals",
    "repositories",
)
_REVIEW_ID_RE = re.compile(r"^REVIEW-[0-9]+$")
_EVIDENCE_ID_RE = re.compile(r"^EVIDENCE-[0-9]+$")
_ARTIFACT_ID_RE = re.compile(r"^[A-Z]+-[0-9]+(?:-[A-Z]+-[0-9]+)?$")
_QUALIFIED_ITEM_RE = re.compile(
    r"^([A-Z]+-[0-9]+(?:-[A-Z]+-[0-9]+)?)#(?:REQ|AC|TASK)-[0-9]+$")
_REVISION_RE = re.compile(r"^[0-9a-f]{7,64}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_EVENT_ID_RE = re.compile(r"^EVENT-[0-9]+$")
_ACTIONS = frozenset({
    "evidence-updated", "lifecycle-transition", "review-recorded",
    "approval-recorded", "check-recorded", "task-state-changed", "change-started",
})
_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
_FINDING_RE = re.compile(r"^(critical|high|medium|low):\s+\S.*$")
_CLAIM_RE = re.compile(
    r"\b(?:cryptographic(?:ally)?\s+(?:proof|proven)|legal(?:ly)?\s+certif(?:y|ied|ication)|"
    r"authenticated\s+identity|compliance\s+guarantee|digital\s+signature)\b",
    re.IGNORECASE,
)


class ReviewEvidenceError(ValueError):
    """A v2 review, evidence record, or compliance event log is malformed."""


def _invalid_text(value: str) -> bool:
    return any(
        ord(character) < 32
        or ord(character) == 127
        or 0xD800 <= ord(character) <= 0xDFFF
        for character in value
    )


def _validate_json_value(value: object, label: str, *, max_nodes: int = 50_000) -> None:
    """Reject non-JSON values, recursion, controls, DEL, and Unicode surrogates."""
    stack: list[tuple[object, bool]] = [(value, False)]
    active: set[int] = set()
    nodes = 0
    while stack:
        current, leaving = stack.pop()
        if leaving:
            active.remove(id(current))
            continue
        nodes += 1
        if nodes > max_nodes:
            raise ReviewEvidenceError(f"{label} exceeds the node limit")
        if isinstance(current, str):
            if len(current) > MAX_STRING or _invalid_text(current):
                raise ReviewEvidenceError(
                    f"{label} contains invalid Unicode or controls")
        elif type(current) in (list, dict):
            identity = id(current)
            if identity in active:
                raise ReviewEvidenceError(
                    f"{label} contains a recursive value")
            active.add(identity)
            stack.append((current, True))
            if type(current) is dict:
                if len(current) > MAX_OBJECT_FIELDS:
                    raise ReviewEvidenceError(
                        f"{label} exceeds the object limit")
                for key in current:
                    if not isinstance(key, str) or len(key) > MAX_STRING \
                            or _invalid_text(key):
                        raise ReviewEvidenceError(
                            f"{label} contains an invalid field name")
                stack.extend((current[key], False)
                             for key in reversed(tuple(current)))
            else:
                if len(current) > MAX_ITEMS:
                    raise ReviewEvidenceError(
                        f"{label} exceeds the item limit")
                stack.extend((item, False) for item in reversed(current))
        elif current is None or type(current) in (bool, int):
            continue
        elif type(current) is float and math.isfinite(current):
            continue
        else:
            raise ReviewEvidenceError(f"{label} contains a non-JSON value")


def _object(value: object, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ReviewEvidenceError(f"{label} must be an object")
    if len(value) > MAX_OBJECT_FIELDS:
        raise ReviewEvidenceError(f"{label} exceeds the object limit")
    for key in value:
        if not isinstance(key, str) or len(key) > MAX_STRING or _invalid_text(key):
            raise ReviewEvidenceError(
                f"{label} contains an invalid field name")
    return value


def _exact(value: object, fields: Iterable[str], label: str) -> dict[str, Any]:
    result = _object(value, label)
    expected = set(fields)
    missing = sorted(expected - set(result))
    unknown = sorted(set(result) - expected)
    if missing:
        raise ReviewEvidenceError(f"{label} missing field: {missing[0]}")
    if unknown:
        raise ReviewEvidenceError(f"{label} unknown field: {unknown[0]}")
    return result


def _array(value: object, label: str, *, nonempty: bool = False,
           maximum: int = MAX_ITEMS) -> list[Any]:
    if type(value) is not list:
        raise ReviewEvidenceError(f"{label} must be an array")
    if len(value) > maximum:
        raise ReviewEvidenceError(f"{label} exceeds the item limit")
    if nonempty and not value:
        raise ReviewEvidenceError(f"{label} must be non-empty")
    return value


def _string(value: object, label: str, *, maximum: int = 500) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewEvidenceError(f"{label} must be a non-empty string")
    if len(value) > maximum:
        raise ReviewEvidenceError(f"{label} exceeds the string limit")
    if _invalid_text(value):
        raise ReviewEvidenceError(
            f"{label} contains invalid Unicode or a control character")
    return value


def _nullable_string(value: object, label: str) -> Optional[str]:
    return None if value is None else _string(value, label)


def _strings(value: object, label: str, *, nonempty: bool = False,
             maximum: int = MAX_ITEMS) -> list[str]:
    values = _array(value, label, nonempty=nonempty, maximum=maximum)
    result = [_string(item, f"{label}[{index}]")
              for index, item in enumerate(values)]
    if len(result) != len(set(result)):
        raise ReviewEvidenceError(f"{label} entries must be unique")
    return result


def _enum(value: object, choices: set[str], label: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise ReviewEvidenceError(f"{label} is invalid")
    return value


def _source_text(source: object, label: str) -> str:
    if type(source) is bytes:
        if len(source) > MAX_SOURCE_BYTES:
            raise ReviewEvidenceError(f"{label} exceeds the byte limit")
    elif type(source) is str:
        try:
            encoded = source.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ReviewEvidenceError(
                f"{label} contains invalid Unicode") from exc
        if len(encoded) > MAX_SOURCE_BYTES:
            raise ReviewEvidenceError(f"{label} exceeds the byte limit")
    else:
        raise ReviewEvidenceError(f"{label} must be UTF-8 bytes or text")
    try:
        return markdown.normalize_text(source)
    except (markdown.MarkdownError, UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise ReviewEvidenceError(f"{label} is invalid Markdown") from exc


def _review_model(model: object, metadata_fields: set[str], sections: tuple[str, ...],
                  label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_json_value(model, label)
    document = _exact(model, _DOCUMENT_FIELDS, label)
    metadata = _exact(document["metadata"],
                      metadata_fields, f"{label} metadata")
    if type(metadata["schema_version"]) is not int or metadata["schema_version"] != 2:
        raise ReviewEvidenceError(f"{label} schema_version must be 2")
    review_id = _string(metadata["id"], f"{label} id", maximum=100)
    if _REVIEW_ID_RE.fullmatch(review_id) is None:
        raise ReviewEvidenceError(f"{label} id must use REVIEW-N")
    if metadata["type"] != "review-report":
        raise ReviewEvidenceError(f"{label} type must be review-report")
    _strings(metadata["sources"],
             f"{label} sources", nonempty=True, maximum=100)
    _enum(metadata["verdict"], {"approved", "changes-required", "blocked"},
          f"{label} verdict")
    _string(document["h1"], f"{label} h1")
    actual_sections = _strings(
        document["sections"], f"{label} sections", maximum=1000)
    expected_set = set(sections)
    extras = [(index, item) for index, item in enumerate(actual_sections)
              if item not in expected_set]
    if "Findings" not in actual_sections:
        raise ReviewEvidenceError(
            f"{label} sections must match the exact v2 contract")
    finding_index = actual_sections.index("Findings")
    following = "Acceptance coverage" if "Acceptance coverage" in sections else "Acceptance gaps"
    if following not in actual_sections:
        raise ReviewEvidenceError(
            f"{label} sections must match the exact v2 contract")
    next_index = actual_sections.index(following)
    if any(index <= finding_index or index >= next_index for index, _ in extras):
        raise ReviewEvidenceError(
            f"{label} finding sections must remain inside Findings")
    if any(_FINDING_RE.fullmatch(item) is None for _, item in extras):
        raise ReviewEvidenceError(
            "finding severity must be critical, high, medium, or low")
    canonical_sections = [
        item for item in actual_sections if item in expected_set]
    if canonical_sections != list(sections):
        raise ReviewEvidenceError(
            f"{label} sections must match the exact v2 contract")
    if _array(document["local_ids"], f"{label} local_ids"):
        raise ReviewEvidenceError(f"{label} must not declare local IDs")
    _strings(document["references"], f"{label} references", maximum=1000)
    if _array(document["placeholders"], f"{label} placeholders"):
        raise ReviewEvidenceError(f"{label} must not contain placeholders")
    return document, metadata


def _section_bodies(text: str, expected: tuple[str, ...], label: str) -> dict[str, str]:
    lines = text.splitlines()
    headings = [(index, line[3:]) for index, line in enumerate(lines)
                if line.startswith("## ") and not line.startswith("### ")]
    if [title for _, title in headings] != list(expected):
        raise ReviewEvidenceError(
            f"{label} source sections must match the exact v2 contract")
    bodies: dict[str, str] = {}
    for position, (start, title) in enumerate(headings):
        end = headings[position + 1][0] if position + \
            1 < len(headings) else len(lines)
        body = "\n".join(lines[start + 1:end]).strip()
        if not body:
            raise ReviewEvidenceError(
                f"{label} section {title} must be non-empty")
        bodies[title] = body
    return bodies


def _source_backed(document: dict[str, Any], source: object, label: str,
                   sections: tuple[str, ...]) -> tuple[str, dict[str, str]]:
    text = _source_text(source, f"{label} source")
    try:
        parsed = markdown.parse_markdown(
            text, allowed_metadata_keys={
                "schema_version", "id", "type", "sources", "verdict",
                "evidence_reference",
            }, mode="rendered")
    except (markdown.MarkdownError, ValueError, TypeError, RecursionError) as exc:
        raise ReviewEvidenceError(
            f"{label} source is invalid Markdown") from exc
    if parsed != document:
        raise ReviewEvidenceError(
            f"{label} source does not match the normalized model")
    return text, _section_bodies(text, sections, label)


def _fields(body: str, labels: tuple[str, ...], section: str) -> dict[str, str]:
    result: dict[str, str] = {}
    parsed: list[tuple[str, str]] = []
    for line in body.splitlines():
        if not line.startswith("- ") or ":" not in line:
            continue
        raw_label, value = line[2:].split(":", 1)
        parsed.append((raw_label, value.strip()))
    for label in labels:
        matches = [value for raw_label, value in parsed
                   if raw_label.casefold() == label.casefold()]
        if len(matches) != 1:
            raise ReviewEvidenceError(
                f"{section} requires field exactly once: {label}")
        value = matches[0]
        if value in {"", "``"}:
            raise ReviewEvidenceError(
                f"{section} field {label} must be non-empty")
        result[label] = value.strip("`")
    return result


def _table_rows(body: str, columns: int, section: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in body.splitlines():
        if not line.startswith("|") or not line.endswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in line[1:-1].split("|")]
        if len(cells) != columns:
            raise ReviewEvidenceError(
                f"{section} table has an invalid column count")
        if all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        rows.append(cells)
    if len(rows) < 2:
        raise ReviewEvidenceError(
            f"{section} requires a header and at least one row")
    return rows[1:]


def _findings(body: str) -> list[dict[str, str]]:
    headings = [line[4:]
                for line in body.splitlines() if line.startswith("### ")]
    if not headings:
        if body.strip().casefold() != "none":
            raise ReviewEvidenceError(
                "Findings must be 'none' or canonical finding records")
        return []
    result: list[dict[str, str]] = []
    blocks = re.split(r"(?m)^### ", body)[1:]
    for block in blocks:
        lines = block.splitlines()
        heading = lines[0]
        if _FINDING_RE.fullmatch(heading) is None:
            raise ReviewEvidenceError(
                "finding severity must be critical, high, medium, or low")
        fields = _fields("\n".join(lines[1:]),
                         ("Evidence class", "Evidence",
                          "Location", "Impact", "Minimal action"),
                         "finding")
        if fields["Evidence class"] not in {
                "observed evidence", "source-based inference", "unverified claim"}:
            raise ReviewEvidenceError("finding evidence class is invalid")
        result.append({"severity": heading.split(":", 1)[0], **fields})
    return result


def _verdict(body: str, metadata_verdict: str) -> None:
    fields = _fields(body, ("Selected verdict", "Rationale"), "Verdict")
    if fields["Selected verdict"] != metadata_verdict:
        raise ReviewEvidenceError(
            "Verdict section must match metadata verdict")


def _is_none(value: str) -> bool:
    return value.strip().strip("`").casefold() == "none"


def _fact_identity(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())


def validate_standalone_review(model: object, *, source: Optional[bytes | str] = None
                               ) -> dict[str, Any]:
    """Validate a standalone v2 review and return its normalized semantic facts.

    With ``source`` supplied, exact section fields, tables, finding records,
    acceptance coverage, evidence classes, verdict effects, and high-risk
    independence are validated against the same rendered Markdown bytes.
    """
    document, metadata = _review_model(
        model, _STANDALONE_METADATA, STANDALONE_SECTIONS, "standalone review")
    result: dict[str, Any] = {"document": document,
                              "quality_signals": [], "findings": []}
    if source is None:
        return result
    _, bodies = _source_backed(
        document, source, "standalone review", STANDALONE_SECTIONS)
    scope = _fields(bodies["Scope"],
                    ("Fixed base", "Fixed head", "Committed range", "Uncommitted scope",
                     "Scope notes"), "Scope")
    role = _fields(bodies["Reviewer role and independence"],
                   ("Reviewer role", "Reviewer ID", "Implementers", "Prior participation",
                    "Fresh context", "Independence", "Independence basis",
                    "Independence required", "Independence met"),
                   "Reviewer role and independence")
    independence = _enum(role["Independence"], {"independent", "self-review"},
                         "review independence")
    implementers = {item.strip() for item in role["Implementers"].split(",")
                    if item.strip()}
    participation = {item.strip() for item in role["Prior participation"].split(",")
                     if item.strip() and item.strip() != "none"}
    if independence == "independent" and (
            role["Reviewer ID"] in implementers or "implementation" in participation):
        raise ReviewEvidenceError(
            "independent review requires a reviewer without implementation participation")
    if independence == "self-review" and (
            role["Reviewer ID"] not in implementers or "implementation" not in participation):
        raise ReviewEvidenceError(
            "self-review independence must identify an implementer and implementation participation")
    source_rows = _table_rows(
        bodies["Authoritative sources"], 4, "Authoritative sources")
    declared_sources = metadata["sources"]
    if [row[1] for row in source_rows] != declared_sources:
        raise ReviewEvidenceError(
            "Authoritative sources must exactly match metadata sources in order")
    risk = _fields(bodies["Risk"],
                   ("Reviewer-assessed risk", "Risk rationale",
                    "Required review depth/evidence"),
                   "Risk")
    reviewer_risk = _enum(
        risk["Reviewer-assessed risk"], {"low", "medium", "high"}, "review risk")
    contract = _fields(bodies["Change contract and review focus"],
                       ("What", "Authoritative why", "Contract scope", "Required evidence",
                        "Contract risk", "Agent roles", "Review focus",
                        "Risk comparison/deviation", "Missing-contract impact"),
                       "Change contract and review focus")
    contract_risk = _enum(
        contract["Contract risk"], {"low", "medium", "high"}, "contract risk")
    risk_rank = {"low": 0, "medium": 1, "high": 2}
    if (risk_rank[reviewer_risk] < risk_rank[contract_risk]
            and _is_none(contract["Risk comparison/deviation"])):
        raise ReviewEvidenceError(
            "reviewer risk is an undeclared downgrade from contract risk")
    effective_risk = max((reviewer_risk, contract_risk),
                         key=risk_rank.__getitem__)
    signal_rows = _table_rows(bodies["Selected quality signals"], 4,
                              "Selected quality signals")
    if [row[0] for row in signal_rows] != list(SIGNALS):
        raise ReviewEvidenceError(
            "quality signals must contain exactly the canonical nine")
    for row in signal_rows:
        if row[1] not in {"selected", "N/A"} or not row[2]:
            raise ReviewEvidenceError(
                "quality signals require a disposition and trigger")
        if row[1] == "selected" and not row[3]:
            raise ReviewEvidenceError(
                "selected quality signals require evidence")
        result["quality_signals"].append({
            "signal": row[0], "disposition": row[1], "trigger": row[2], "evidence": row[3],
        })
    check_rows = _table_rows(
        bodies["Checks and evidence"], 9, "Checks and evidence")
    compatible_scopes = {
        _fact_identity(scope["Uncommitted scope"]),
        _fact_identity(scope["Committed range"]),
    }
    check_records: list[dict[str, Any]] = []
    for row in check_rows:
        if not all(row):
            raise ReviewEvidenceError(
                "checks require scope, applicability, reason, evidence, status, and coverage")
        required = _enum(row[2], {"yes", "no"}, "check required") == "yes"
        applicability = _enum(
            row[3], {"applicable", "not-applicable"}, "check applicability")
        reason = row[4]
        check_status = _enum(
            row[5], {"passed", "failed", "not-run",
                     "skipped", "not-applicable"},
            "check status")
        observed_result = row[6]
        evidence_class = _enum(
            row[7], {"observed evidence", "source-based inference",
                     "unverified claim", "none"},
            "check evidence class")
        if _QUALIFIED_ITEM_RE.fullmatch(row[8]) is None:
            raise ReviewEvidenceError(
                "check requirement coverage must be qualified")
        if check_status in {"passed", "failed"} and (
                applicability != "applicable" or evidence_class != "observed evidence"
                or _is_none(observed_result) or not _is_none(reason)):
            raise ReviewEvidenceError(
                "passed or failed check requires an observed result and observed evidence")
        if check_status in {"not-run", "skipped"} and (
                applicability != "applicable" or evidence_class != "none"
                or not _is_none(observed_result) or not _is_none(reason)):
            raise ReviewEvidenceError(
                "not-run or skipped check cannot declare observed result or evidence")
        if check_status == "not-applicable" and (
                required or applicability != "not-applicable" or _is_none(
                    reason)
                or not _is_none(observed_result) or evidence_class != "none"):
            raise ReviewEvidenceError(
                "not-applicable check requires optional status, a reason, and no execution evidence")
        if applicability == "not-applicable" and check_status != "not-applicable":
            raise ReviewEvidenceError(
                "not-applicable decision requires not-applicable status")
        if applicability == "applicable" and check_status == "not-applicable":
            raise ReviewEvidenceError(
                "applicable check cannot have not-applicable status")
        check_records.append({
            "id": row[0], "scope": row[1], "required": required,
            "applicability": applicability, "not_applicable_reason": reason,
            "status": check_status, "observed_result": observed_result,
            "evidence_class": evidence_class, "requirement_id": row[8],
        })
    for signal in result["quality_signals"]:
        if signal["disposition"] != "selected":
            continue
        if not any(
            item["id"] == signal["evidence"]
            and item["status"] == "passed"
            and item["applicability"] == "applicable"
            and item["evidence_class"] == "observed evidence"
            for item in check_records
        ):
            raise ReviewEvidenceError(
                "selected quality signal must link to a passed observed applicable check")
    findings = _findings(bodies["Findings"])
    coverage_rows = _table_rows(
        bodies["Acceptance coverage"], 4, "Acceptance coverage")
    for row in coverage_rows:
        if _QUALIFIED_ITEM_RE.fullmatch(row[0]) is None:
            raise ReviewEvidenceError(
                "acceptance coverage source items must be qualified")
        if row[3] not in {"met", "covered", "not-met", "blocked", "N/A"}:
            raise ReviewEvidenceError("acceptance coverage result is invalid")
        if not row[2]:
            raise ReviewEvidenceError(
                "acceptance coverage requires check evidence")
        if row[3] in {"met", "covered"}:
            linked = [item for item in check_records if item["id"] == row[2]]
            if not linked or not any(
                    item["status"] == "passed"
                    and item["applicability"] == "applicable"
                    and item["evidence_class"] == "observed evidence"
                    for item in linked):
                raise ReviewEvidenceError(
                    "met coverage must link to a passed check")
            if not any(item["status"] == "passed"
                       and item["applicability"] == "applicable"
                       and item["evidence_class"] == "observed evidence"
                       and item["requirement_id"] == row[0] for item in linked):
                raise ReviewEvidenceError(
                    "met coverage check must cover the same requirement")
            if not any(item["status"] == "passed"
                       and item["applicability"] == "applicable"
                       and item["evidence_class"] == "observed evidence"
                       and item["requirement_id"] == row[0]
                       and _fact_identity(item["scope"]) in compatible_scopes
                       for item in linked):
                raise ReviewEvidenceError(
                    "met coverage check has incompatible repository scope")
    acceptance = _fields(bodies["Acceptance coverage"],
                         ("Missing behavior", "Extra behavior", "Scope deviations"),
                         "Acceptance coverage")
    residual = _fields(
        bodies["Residual risk"],
        ("Residual risks", "Unverified areas", "Required follow-up"), "Residual risk")
    _verdict(bodies["Verdict"], metadata["verdict"])
    if effective_risk == "high" and not (
        independence == "independent"
        and role["Fresh context"] == "yes"
        and role["Independence required"] == "yes"
        and role["Independence met"] == "yes"
        and role["Reviewer ID"] not in implementers
        and "implementation" not in participation
    ):
        raise ReviewEvidenceError(
            "high-risk independence requires fresh independent participation")
    incomplete_check = any(
        item["required"] and item["applicability"] == "applicable"
        and (item["status"] != "passed" or item["evidence_class"] == "unverified claim")
        for item in check_records
    )
    acceptance_gap = any(
        not _is_none(acceptance[field])
        for field in ("Missing behavior", "Extra behavior", "Scope deviations")
    ) or any(
        not _is_none(residual[field])
        for field in ("Unverified areas", "Required follow-up")
    )
    if metadata["verdict"] == "approved" and (
            findings or incomplete_check or acceptance_gap
            or any(row[3] in {"not-met", "blocked"} for row in coverage_rows)):
        raise ReviewEvidenceError(
            "approved verdict cannot retain findings, required gaps, scope deviations, "
            "or unrun required checks")
    if metadata["verdict"] == "changes-required" and not (
            findings or any(row[3] == "not-met" for row in coverage_rows)):
        raise ReviewEvidenceError(
            "changes-required verdict requires an established defect")
    result.update({
        "scope": scope, "reviewer": role, "risk": risk, "contract": contract,
        "effective_risk": effective_risk, "checks": check_records,
        "findings": findings, "coverage": coverage_rows,
    })
    return result


def validate_evidence_review(model: object, *, evidence: object,
                             source: Optional[bytes | str] = None) -> dict[str, Any]:
    """Validate a reduced evidence-backed review against one v2 evidence record."""
    document, metadata = _review_model(
        model, _EVIDENCE_METADATA, EVIDENCE_REVIEW_SECTIONS, "evidence-backed review")
    if FORBIDDEN_EVIDENCE_SECTIONS.intersection(document["sections"]):
        raise ReviewEvidenceError(
            "evidence-backed review contains a forbidden machine section")
    record = validate_evidence_record(evidence)
    reference = _string(metadata["evidence_reference"],
                        "evidence reference", maximum=100)
    if _EVIDENCE_ID_RE.fullmatch(reference) is None:
        raise ReviewEvidenceError("evidence reference must use EVIDENCE-N")
    if metadata["sources"] != [reference] or reference != record["id"]:
        raise ReviewEvidenceError(
            "evidence sources and evidence reference must match the linked record")
    if metadata["verdict"] != record["review"]["verdict"]:
        raise ReviewEvidenceError(
            "review verdict must match linked evidence verdict")
    result = {"document": document, "evidence": record, "findings": []}
    if source is not None:
        _, bodies = _source_backed(
            document, source, "evidence-backed review", EVIDENCE_REVIEW_SECTIONS)
        machine_labels = {
            "fixed", "fix", "fixedbase", "baserevision", "baselinerevision",
            "fixedhead",
            "headrevision", "committedrange", "commitrange", "uncommittedscope",
            "scopenotes", "reviewer", "reviewerrole", "reviewerid", "implementers",
            "priorparticipation", "freshcontext", "independence", "independencebasis",
            "independencerequired", "independencemet", "authoritativesources", "sources",
            "reviewerassessedrisk", "riskrationale", "risk", "requiredreviewdepthevidence",
            "contractscope", "contractrisk", "requiredevidence", "agentroles",
            "reviewfocus", "riskcomparisondeviation", "missingcontractimpact",
            "repositoryscope", "required", "applicability", "notapplicablereason",
            "status", "actualresult", "requirementriskcovered",
            "sourceitemcriterion", "implementationevidence", "checkevidence",
            "missingbehavior", "extrabehavior", "scopedeviations", "qualitysignals",
            "selectedqualitysignals", "checks", "checksandevidence", "coverage",
            "acceptancecoverage",
        }
        for line in "\n".join(bodies.values()).splitlines():
            if ":" not in line:
                continue
            raw_label = line.split(":", 1)[0]
            label_identity = "".join(
                character for character in raw_label.casefold()
                if character.isalnum()
            )
            if label_identity in machine_labels:
                raise ReviewEvidenceError(
                    "evidence-backed review duplicates a forbidden machine fact")
        if bodies["Evidence reference"].strip("`") != reference:
            raise ReviewEvidenceError(
                "Evidence reference section must match metadata")
        result["findings"] = _findings(bodies["Findings"])
        _verdict(bodies["Verdict"], metadata["verdict"])
        if metadata["verdict"] == "approved" and (
                result["findings"] or not _is_none(bodies["Acceptance gaps"])):
            raise ReviewEvidenceError(
                "approved verdict requires canonical Acceptance gaps: none")
    return result


def _canonical_json(value: object) -> bytes:
    _validate_json_value(value, "canonical JSON")
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":")).encode("utf-8")
    except (UnicodeEncodeError, ValueError, TypeError, RecursionError) as exc:
        raise ReviewEvidenceError(
            "canonical JSON contains invalid Unicode") from exc


def _validate_evidence_check(item: object, index: int, requirement_ids: set[str],
                             repository_ids: set[str]) -> dict[str, Any]:
    label = f"checks[{index}]"
    check = _exact(item, _CHECK_FIELDS, label)
    _string(check["id"], f"{label}.id")
    requirements = _strings(
        check["requirement_ids"], f"{label}.requirement_ids", nonempty=True)
    if not set(requirements).issubset(requirement_ids):
        raise ReviewEvidenceError(f"{label} links an unknown requirement")
    repositories = _strings(
        check["repository_ids"], f"{label}.repository_ids", nonempty=True)
    if not set(repositories).issubset(repository_ids):
        raise ReviewEvidenceError(f"{label} links an unknown repository")
    _enum(check["kind"], {"scoped", "regression", "failure-path", "recovery-rollback",
                          "static", "other"}, f"{label}.kind")
    if type(check["required"]) is not bool:
        raise ReviewEvidenceError(f"{label}.required must be boolean")
    applicability = _enum(check["applicability"], {"applicable", "not-applicable"},
                          f"{label}.applicability")
    status = _enum(check["status"], {"passed", "failed", "skipped", "not-run",
                                     "not-applicable"}, f"{label}.status")
    reason = _nullable_string(
        check["not_applicable_reason"], f"{label}.not_applicable_reason")
    result = _nullable_string(
        check["observed_result"], f"{label}.observed_result")
    evidence_class = check["evidence_class"]
    if evidence_class is not None:
        _enum(evidence_class, {"observed evidence", "source-based inference", "unverified claim"},
              f"{label}.evidence_class")
    _nullable_string(check["output_reference"], f"{label}.output_reference")
    if applicability == "not-applicable":
        if check["required"] or not reason or status != "not-applicable" or result is not None \
                or evidence_class is not None or check["output_reference"] is not None:
            raise ReviewEvidenceError(
                f"{label} not-applicable decision is inconsistent")
    elif reason is not None or status == "not-applicable":
        raise ReviewEvidenceError(
            f"{label} applicable decision is inconsistent")
    if status in {"passed", "failed"} and (not result or evidence_class != "observed evidence"):
        raise ReviewEvidenceError(
            f"{label} executed result requires observed evidence")
    if status in {"skipped", "not-run"} and any(
            value is not None for value in (result, evidence_class, check["output_reference"])):
        raise ReviewEvidenceError(
            f"{label} unexecuted result must not claim evidence")
    return check


def validate_evidence_record(value: object) -> dict[str, Any]:
    """Validate one closed evidence v2 record and cross-record truthfulness rules.

    Every authoritative source ID must be a global artifact ID with exactly one
    seal. Free-form or otherwise non-artifact source IDs fail closed because
    they cannot satisfy the deterministic source-seal contract.
    """
    _validate_json_value(value, "evidence")
    record = _exact(value, _EVIDENCE_FIELDS, "evidence")
    if type(record["schema_version"]) is not int or record["schema_version"] != 2:
        raise ReviewEvidenceError("evidence schema_version must be 2")
    evidence_id = _string(record["id"], "evidence id", maximum=100)
    if _EVIDENCE_ID_RE.fullmatch(evidence_id) is None:
        raise ReviewEvidenceError("evidence id must use EVIDENCE-N")
    change_id = _string(record["change_id"], "evidence.change_id", maximum=100)
    if _ARTIFACT_ID_RE.fullmatch(change_id) is None:
        raise ReviewEvidenceError(
            "evidence.change_id must be a valid global ID")

    source_ids: list[str] = []
    for index, raw in enumerate(_array(record["authoritative_sources"],
                                       "authoritative_sources", nonempty=True, maximum=100)):
        source = _exact(raw, {"id", "reference"},
                        f"authoritative_sources[{index}]")
        source_id = _string(
            source["id"], f"authoritative_sources[{index}].id", maximum=100)
        if _ARTIFACT_ID_RE.fullmatch(source_id) is None:
            raise ReviewEvidenceError(
                "authoritative source IDs must be valid global artifact IDs")
        source_ids.append(source_id)
        _string(source["reference"],
                f"authoritative_sources[{index}].reference")
    if len(source_ids) != len(set(source_ids)):
        raise ReviewEvidenceError("authoritative source IDs must be unique")

    lifecycle = _exact(record["lifecycle"], {"status", "transition", "evidence_references"},
                       "lifecycle")
    status = _enum(lifecycle["status"], {"in-progress", "blocked", "complete"},
                   "lifecycle.status")
    transition = _enum(lifecycle["transition"], {"not-requested", "implemented", "verified"},
                       "lifecycle.transition")
    _strings(lifecycle["evidence_references"],
             "lifecycle.evidence_references", nonempty=True)
    risk = _exact(record["risk"], {"level", "rationale"}, "risk")
    risk_level = _enum(risk["level"], {"low", "medium", "high"}, "risk.level")
    _string(risk["rationale"], "risk.rationale")
    contract = _exact(record["change_contract"],
                      {"intent", "confirmed_why", "scope", "expected_evidence",
                       "agent_roles", "review_focus"}, "change_contract")
    for field in ("intent", "confirmed_why", "scope"):
        _string(contract[field], f"change_contract.{field}")
    for field in ("expected_evidence", "agent_roles", "review_focus"):
        _strings(contract[field], f"change_contract.{field}", nonempty=True)

    repository_ids: list[str] = []
    for index, raw in enumerate(_array(record["repository_scope"], "repository_scope",
                                       nonempty=True, maximum=100)):
        item = _exact(raw, _REPOSITORY_FIELDS, f"repository_scope[{index}]")
        repository_id = _string(item["repository_id"],
                                f"repository_scope[{index}].repository_id")
        repository_ids.append(repository_id)
        entries = _array(item["uncommitted_entries"],
                         f"repository_scope[{index}].uncommitted_entries")
        identities: list[tuple[str, str]] = []
        for position, raw_entry in enumerate(entries):
            entry = _exact(raw_entry, {"path", "state", "sha256"},
                           f"repository_scope[{index}].uncommitted_entries[{position}]")
            path = _string(entry["path"], "uncommitted path")
            state = _enum(entry["state"], {"staged", "unstaged", "untracked"},
                          "uncommitted state")
            if not isinstance(entry["sha256"], str) or _SHA_RE.fullmatch(entry["sha256"]) is None:
                raise ReviewEvidenceError("uncommitted sha256 is invalid")
            identities.append((path, state))
        if identities != sorted(identities) or len(identities) != len(set(identities)):
            raise ReviewEvidenceError(
                "uncommitted entries must be ordered and unique")
        if status == "complete":
            for field in ("base", "head"):
                revision = item[field]
                if revision != "not-applicable" and (
                        not isinstance(revision, str) or _REVISION_RE.fullmatch(revision) is None):
                    raise ReviewEvidenceError(
                        f"complete repository {field} must be immutable")
            _string(item["committed_range"],
                    "complete repository committed_range")
            expected_snapshot = hashlib.sha256(
                _canonical_json(entries)).hexdigest()
            if item["snapshot_sha256"] != expected_snapshot:
                raise ReviewEvidenceError(
                    "repository snapshot sha256 does not match entries")
        else:
            for field in ("base", "head"):
                revision = item[field]
                if revision is not None and revision != "not-applicable" and (
                        not isinstance(revision, str) or _REVISION_RE.fullmatch(revision) is None):
                    raise ReviewEvidenceError(
                        f"repository {field} must be immutable or null")
            _nullable_string(item["committed_range"],
                             "repository committed_range")
            snapshot = item["snapshot_sha256"]
            if snapshot is not None and (not isinstance(snapshot, str)
                                         or _SHA_RE.fullmatch(snapshot) is None):
                raise ReviewEvidenceError(
                    "repository snapshot sha256 is invalid")
    if len(repository_ids) != len(set(repository_ids)):
        raise ReviewEvidenceError("repository IDs must be unique")
    repository_id_set = set(repository_ids)

    sealed_items: set[str] = set()
    seal_ids: list[str] = []
    if record["source_seals"] == []:
        raise ReviewEvidenceError("source seal list must be non-empty")
    for index, raw in enumerate(_array(record["source_seals"], "source_seals",
                                       nonempty=True, maximum=100)):
        seal = _exact(raw, {"artifact_id", "overall_digest", "item_digests"},
                      f"source_seals[{index}]")
        artifact_id = _string(
            seal["artifact_id"], f"source_seals[{index}].artifact_id", maximum=100)
        if _ARTIFACT_ID_RE.fullmatch(artifact_id) is None:
            raise ReviewEvidenceError("source seal artifact ID is invalid")
        if artifact_id not in source_ids:
            raise ReviewEvidenceError(
                "source seal artifact ID is not authoritative")
        seal_ids.append(artifact_id)
        if not isinstance(seal["overall_digest"], str) or _DIGEST_RE.fullmatch(
                seal["overall_digest"]) is None:
            raise ReviewEvidenceError("source seal overall digest is invalid")
        item_map = _object(seal["item_digests"],
                           f"source_seals[{index}].item_digests")
        if not item_map:
            raise ReviewEvidenceError("source seal item map must be non-empty")
        for item_id, digest in item_map.items():
            match = _QUALIFIED_ITEM_RE.fullmatch(item_id)
            if match is None or match.group(1) != artifact_id:
                raise ReviewEvidenceError(
                    "source seal item IDs must be qualified by artifact ID")
            if not isinstance(digest, str) or _DIGEST_RE.fullmatch(digest) is None:
                raise ReviewEvidenceError("source seal item digest is invalid")
            sealed_items.add(item_id)
    if len(seal_ids) != len(set(seal_ids)):
        raise ReviewEvidenceError("source seal artifact IDs must be unique")
    if set(seal_ids) != set(source_ids):
        raise ReviewEvidenceError(
            "authoritative artifact sources require exactly one source seal with no extras")

    coverage_ids: list[str] = []
    coverage_records = _array(record["requirement_coverage"], "requirement_coverage",
                              nonempty=True)
    for index, raw in enumerate(coverage_records):
        item = _exact(raw, {"requirement_id", "repository_ids", "status",
                            "implementation_references", "evidence_references"},
                      f"requirement_coverage[{index}]")
        requirement_id = _string(
            item["requirement_id"], f"requirement_coverage[{index}].requirement_id")
        if _QUALIFIED_ITEM_RE.fullmatch(requirement_id) is None:
            raise ReviewEvidenceError(
                "coverage requirement IDs must be qualified")
        if requirement_id not in sealed_items:
            raise ReviewEvidenceError(
                "coverage requirement lacks a source seal")
        coverage_ids.append(requirement_id)
        linked_repositories = _strings(item["repository_ids"],
                                       f"requirement_coverage[{index}].repository_ids",
                                       nonempty=True)
        if not set(linked_repositories).issubset(repository_id_set):
            raise ReviewEvidenceError("coverage links an unknown repository")
        coverage_status = _enum(item["status"], {"covered", "partial", "not-covered"},
                                f"requirement_coverage[{index}].status")
        implementation_refs = _strings(item["implementation_references"],
                                       f"requirement_coverage[{index}].implementation_references")
        _strings(item["evidence_references"],
                 f"requirement_coverage[{index}].evidence_references", nonempty=True)
        if coverage_status == "covered" and not implementation_refs:
            raise ReviewEvidenceError(
                "covered requirement needs implementation evidence")
    if len(coverage_ids) != len(set(coverage_ids)):
        raise ReviewEvidenceError("coverage requirement IDs must be unique")

    checks = [_validate_evidence_check(item, index, set(coverage_ids), repository_id_set)
              for index, item in enumerate(_array(record["checks"], "checks", nonempty=True))]
    check_ids = [item["id"] for item in checks]
    if len(check_ids) != len(set(check_ids)):
        raise ReviewEvidenceError("check IDs must be unique")
    check_id_set = set(check_ids)
    for item in coverage_records:
        linked = [check for check in checks
                  if check["id"] in item["evidence_references"]]
        if not linked:
            raise ReviewEvidenceError(
                "coverage evidence must link at least one check")
        if item["status"] == "covered" and not any(
            check["requirement_ids"] == [item["requirement_id"]]
            and check["repository_ids"] == item["repository_ids"]
            and check["applicability"] == "applicable"
            and check["status"] == "passed"
            for check in linked
        ):
            raise ReviewEvidenceError(
                "covered requirement needs an exact passed check for the same requirement "
                "and repository set")

    signals = _array(record["quality_signals"],
                     "quality_signals", nonempty=True, maximum=9)
    if len(signals) != 9:
        raise ReviewEvidenceError(
            "quality signals must contain exactly nine items")
    actual_signals: list[str] = []
    for index, raw in enumerate(signals):
        item = _exact(raw, {"signal", "disposition", "trigger", "evidence_references"},
                      f"quality_signals[{index}]")
        actual_signals.append(_enum(item["signal"], set(SIGNALS),
                                    f"quality_signals[{index}].signal"))
        disposition = _enum(item["disposition"], {"selected", "N/A"},
                            f"quality_signals[{index}].disposition")
        _string(item["trigger"], f"quality_signals[{index}].trigger")
        references = _strings(item["evidence_references"],
                              f"quality_signals[{index}].evidence_references")
        if disposition == "selected" and (
            not references
            or not set(references).issubset(check_id_set)
            or any(
                not any(
                    check["id"] == reference
                    and check["status"] == "passed"
                    and check["applicability"] == "applicable"
                    and check["evidence_class"] == "observed evidence"
                    for check in checks
                )
                for reference in references
            )
        ):
            raise ReviewEvidenceError(
                "selected quality signal requires a passed observed applicable check")
        if disposition == "N/A" and references:
            raise ReviewEvidenceError(
                "N/A quality signal must not claim evidence")
    if actual_signals != list(SIGNALS):
        raise ReviewEvidenceError(
            "quality signals must use the canonical order without duplicates")

    review = _exact(record["review"],
                    {"reviewer_role", "reviewer_id", "implementers", "prior_participation",
                     "fresh_context", "independence", "independence_basis", "verdict",
                     "reference"}, "review")
    for field in ("reviewer_role", "reviewer_id", "independence_basis", "reference"):
        _string(review[field], f"review.{field}")
    implementers = _strings(review["implementers"], "review.implementers", nonempty=True,
                            maximum=100)
    participation = _strings(review["prior_participation"], "review.prior_participation",
                             maximum=10)
    if not set(participation).issubset(
            {"implementation", "planning", "validation", "review", "other"}):
        raise ReviewEvidenceError("review prior participation is invalid")
    if type(review["fresh_context"]) is not bool:
        raise ReviewEvidenceError("review fresh_context must be boolean")
    independence = _enum(review["independence"], {"self-review", "independent"},
                         "review.independence")
    verdict = _enum(review["verdict"], {"approved", "changes-required", "blocked"},
                    "review.verdict")
    if independence == "independent" and (
            not review["fresh_context"] or "implementation" in participation
            or review["reviewer_id"] in implementers):
        raise ReviewEvidenceError(
            "independent review requires a fresh non-implementer")
    if independence == "self-review" and (
            review["reviewer_id"] not in implementers or "implementation" not in participation):
        raise ReviewEvidenceError(
            "self-review must declare implementation participation")

    kinds = {item["kind"] for item in checks}
    if "scoped" not in kinds:
        raise ReviewEvidenceError("evidence requires a scoped check")
    if risk_level in {"medium", "high"}:
        for required_kind in ("regression", "failure-path"):
            if required_kind not in kinds:
                raise ReviewEvidenceError(
                    f"{risk_level}-risk evidence requires {required_kind}")
    if risk_level == "high" and "recovery-rollback" not in kinds:
        raise ReviewEvidenceError(
            "high-risk evidence requires recovery-rollback")
    if risk_level == "high" and status == "complete" and verdict == "approved":
        def passed_required(item: dict[str, Any]) -> bool:
            return (
                item["required"] is True
                and item["applicability"] == "applicable"
                and item["status"] == "passed"
                and item["evidence_class"] == "observed evidence"
            )

        def explicitly_not_applicable(item: dict[str, Any]) -> bool:
            return (
                item["required"] is False
                and item["applicability"] == "not-applicable"
                and item["status"] == "not-applicable"
                and isinstance(item["not_applicable_reason"], str)
                and bool(item["not_applicable_reason"].strip())
                and item["observed_result"] is None
                and item["evidence_class"] is None
                and item["output_reference"] is None
            )

        for kind in ("regression", "failure-path", "recovery-rollback"):
            decisions = [item for item in checks if item["kind"] == kind]
            if not decisions or not all(
                passed_required(item) or explicitly_not_applicable(item)
                for item in decisions
            ):
                raise ReviewEvidenceError(
                    f"high-risk {kind} must pass as required observed evidence or be "
                    "explicitly not-applicable with a reason")
    if status != "complete" and transition != "not-requested":
        raise ReviewEvidenceError(
            "implemented or verified transition requires complete evidence")
    if status == "complete":
        if transition == "not-requested":
            raise ReviewEvidenceError(
                "complete evidence requires an implemented or verified transition")
        if verdict != "approved":
            raise ReviewEvidenceError(
                "complete evidence requires an approved review")
        for check in checks:
            if check["required"] and check["applicability"] == "applicable" \
                    and check["status"] != "passed":
                raise ReviewEvidenceError(
                    "complete evidence has an unpassed required check")
        if any(check["status"] == "failed" for check in checks):
            raise ReviewEvidenceError(
                "complete evidence cannot contain a failed check")
        if any(item["status"] != "covered" for item in coverage_records):
            raise ReviewEvidenceError(
                "complete evidence requires covered requirements")
    if verdict == "approved" and status != "complete":
        raise ReviewEvidenceError("approved review requires complete evidence")
    if (risk_level == "low" and status == "complete" and transition != "verified"
            and verdict == "approved" and independence != "self-review"):
        raise ReviewEvidenceError(
            "complete low-risk evidence requires accurately labeled self-review")
    if risk_level == "high" and verdict == "approved" and independence != "independent":
        raise ReviewEvidenceError(
            "high-risk approval requires independent review")
    if transition == "verified" and not (
            status == "complete" and verdict == "approved" and independence == "independent"
            and record["source_seals"]):
        raise ReviewEvidenceError(
            "verified transition requires approved independent review and a source seal")

    known = record["known_limits"]
    if known != "not-tracked":
        _strings(known, "known_limits")
    _strings(record["remaining_risks"], "remaining_risks")
    _strings(record["follow_ups"], "follow_ups")
    return record


def _duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if not isinstance(key, str) or _invalid_text(key):
            raise ReviewEvidenceError("JSON object contains an invalid key")
        if key in result:
            raise ReviewEvidenceError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _audit_event(value: object, label: str) -> dict[str, Any]:
    _validate_json_value(value, label)
    event = _exact(value, _AUDIT_FIELDS, label)
    if tuple(event) != _AUDIT_FIELDS:
        raise ReviewEvidenceError(f"{label} fields must use canonical order")
    if type(event["schema_version"]) is not int or event["schema_version"] != 2:
        raise ReviewEvidenceError(f"{label} schema_version must be 2")
    event_id = _string(event["event_id"], f"{label}.event_id", maximum=100)
    if _EVENT_ID_RE.fullmatch(event_id) is None:
        raise ReviewEvidenceError(f"{label} event_id must use EVENT-N")
    if type(event["sequence"]) is not int or not 1 <= event["sequence"] <= 1_000_000:
        raise ReviewEvidenceError(f"{label} sequence is invalid")
    timestamp = event["timestamp"]
    if not isinstance(timestamp, str) or _TIMESTAMP_RE.fullmatch(timestamp) is None:
        raise ReviewEvidenceError(
            f"{label} timestamp must be real RFC3339 UTC")
    try:
        _datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ReviewEvidenceError(
            f"{label} timestamp must be real RFC3339 UTC") from exc
    change_id = _string(event["change_id"], f"{label}.change_id", maximum=100)
    if _ARTIFACT_ID_RE.fullmatch(change_id) is None:
        raise ReviewEvidenceError(
            f"{label} change_id must be a valid global ID")
    actor = _exact(event["actor"], ("actor_id", "role"), f"{label}.actor")
    if tuple(actor) != ("actor_id", "role"):
        raise ReviewEvidenceError(
            f"{label} actor fields must use canonical order")
    actor_id = _string(actor["actor_id"], f"{label}.actor.actor_id")
    _string(actor["role"], f"{label}.actor.role")
    action = event["action"]
    if not isinstance(action, str) or action not in _ACTIONS:
        raise ReviewEvidenceError(
            f"{label} action is not in the closed action enum")
    states = {"draft", "approved", "implemented", "verified"}
    if action == "lifecycle-transition":
        _enum(event["previous_lifecycle"], states,
              f"{label}.previous_lifecycle")
        _enum(event["new_lifecycle"], states, f"{label}.new_lifecycle")
        if (event["previous_lifecycle"], event["new_lifecycle"]) not in {
                ("draft", "approved"), ("approved", "implemented"),
                ("implemented", "verified")}:
            raise ReviewEvidenceError(
                f"{label} lifecycle transition is illegal")
    elif event["previous_lifecycle"] is not None or event["new_lifecycle"] is not None:
        raise ReviewEvidenceError(
            f"{label} lifecycle fields require lifecycle-transition")
    for field in ("authoritative_source_references", "evidence_references"):
        references = _strings(
            event[field], f"{label}.{field}", nonempty=True, maximum=1000)
        if references != sorted(references):
            raise ReviewEvidenceError(
                f"{label}.{field} must use deterministic order")
    approvals = _array(event["approvals"], f"{label}.approvals", maximum=1000)
    approval_keys: list[tuple[str, str]] = []
    for index, raw in enumerate(approvals):
        approval = _exact(raw, ("actor_id", "role", "reference"),
                          f"{label}.approvals[{index}]")
        if tuple(approval) != ("actor_id", "role", "reference"):
            raise ReviewEvidenceError(
                f"{label} approval fields must use canonical order")
        approval_id = _string(approval["actor_id"], "approval.actor_id")
        role = _string(approval["role"], "approval.role")
        _string(approval["reference"], "approval.reference")
        if approval_id == actor_id:
            raise ReviewEvidenceError(
                f"{label} event actor cannot self-approve the same event")
        approval_keys.append((role, approval_id))
    if approval_keys != sorted(approval_keys) or len(approval_keys) != len(set(approval_keys)):
        raise ReviewEvidenceError(
            f"{label} approvals must be sorted and unique")
    repositories = _array(event["repositories"], f"{label}.repositories", nonempty=True,
                          maximum=100)
    repository_ids: list[str] = []
    for index, raw in enumerate(repositories):
        repository = _exact(raw, ("repository_id", "revision"),
                            f"{label}.repositories[{index}]")
        if tuple(repository) != ("repository_id", "revision"):
            raise ReviewEvidenceError(
                f"{label} repository fields must use canonical order")
        repository_id = _string(
            repository["repository_id"], "repository.repository_id")
        revision = repository["revision"]
        if not isinstance(revision, str) or _REVISION_RE.fullmatch(revision) is None:
            raise ReviewEvidenceError(
                f"{label} repository revision must be immutable")
        repository_ids.append(repository_id)
    if repository_ids != sorted(repository_ids) or len(repository_ids) != len(set(repository_ids)):
        raise ReviewEvidenceError(
            f"{label} repositories must be sorted and unique")
    for string in _walk_strings(event):
        if _CLAIM_RE.search(string):
            raise ReviewEvidenceError(
                f"{label} contains a prohibited proof or legal claim")
    return event


def _walk_strings(value: object) -> Iterable[str]:
    stack = [value]
    seen = 0
    while stack:
        current = stack.pop()
        seen += 1
        if seen > 50_000:
            raise ReviewEvidenceError("audit input exceeds the node limit")
        if isinstance(current, str):
            yield current
        elif type(current) is list:
            stack.extend(reversed(current))
        elif type(current) is dict:
            stack.extend(current[key] for key in reversed(tuple(current)))


def canonical_audit_event(value: object) -> str:
    """Return one validated compact v2 event JSON object in canonical field order."""
    event = _audit_event(value, "audit event")
    try:
        rendered = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        rendered.encode("utf-8")
        return rendered
    except (UnicodeEncodeError, ValueError, TypeError, RecursionError) as exc:
        raise ReviewEvidenceError(
            "audit event contains invalid Unicode") from exc


def validate_audit_jsonl(text: object, *, evidence: Optional[object] = None
                         ) -> list[dict[str, Any]]:
    """Validate one compact canonical audit JSONL sequence.

    Sequences start at one and remain contiguous. Timestamps strictly increase,
    event IDs are unique, transitions exclude ``planned``, and optional evidence
    linkage checks source, review, repository, and lifecycle declarations.
    """
    if not isinstance(text, str):
        raise ReviewEvidenceError("audit JSONL must be text")
    try:
        encoded = text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ReviewEvidenceError(
            "audit JSONL contains invalid Unicode") from exc
    if len(encoded) > MAX_AUDIT_BYTES:
        raise ReviewEvidenceError("audit JSONL exceeds the byte limit")
    if not text or not text.endswith("\n"):
        raise ReviewEvidenceError(
            "audit JSONL must end each event with a newline")
    lines = text.splitlines()
    if not lines or len(lines) > MAX_AUDIT_EVENTS:
        raise ReviewEvidenceError("audit JSONL exceeds the event limit")
    if any(not line.startswith("{") or not line.endswith("}") for line in lines):
        raise ReviewEvidenceError(
            "audit JSONL requires one compact object per line")
    events: list[dict[str, Any]] = []
    times: list[_datetime.datetime] = []
    for index, line in enumerate(lines):
        if not line or line != line.strip() or "\n" in line or "\r" in line:
            raise ReviewEvidenceError(
                "audit JSONL requires one compact object per line")
        try:
            raw = json.loads(line, object_pairs_hook=_duplicate_object)
        except ReviewEvidenceError:
            raise
        except (json.JSONDecodeError, UnicodeError, RecursionError, ValueError, TypeError) as exc:
            raise ReviewEvidenceError(
                "audit JSONL contains malformed JSON") from exc
        event = _audit_event(raw, f"audit event[{index}]")
        canonical = json.dumps(event, ensure_ascii=False,
                               separators=(",", ":"))
        if line != canonical:
            raise ReviewEvidenceError(
                "audit JSONL requires compact canonical serialization")
        events.append(event)
        times.append(_datetime.datetime.strptime(
            event["timestamp"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_datetime.timezone.utc))
    latest_lifecycle: Optional[str] = None
    for event in events:
        if event["action"] == "lifecycle-transition":
            if (latest_lifecycle is not None
                    and event["previous_lifecycle"] != latest_lifecycle):
                raise ReviewEvidenceError(
                    "audit lifecycle transition continuity is broken")
            latest_lifecycle = event["new_lifecycle"]
    if [item["sequence"] for item in events] != list(range(1, len(events) + 1)):
        raise ReviewEvidenceError(
            "audit sequence must be increasing and contiguous from 1")
    if len({item["event_id"] for item in events}) != len(events):
        raise ReviewEvidenceError("audit event IDs must be unique")
    if any(left >= right for left, right in zip(times, times[1:])):
        raise ReviewEvidenceError(
            "audit timestamps must be strictly increasing")
    if len({item["timestamp"] for item in events}) != len(events):
        raise ReviewEvidenceError("audit timestamps must be unique")
    change_ids = {item["change_id"] for item in events}
    if len(change_ids) != 1:
        raise ReviewEvidenceError("audit change ID must be consistent")

    if evidence is not None:
        record = validate_evidence_record(evidence)
        if change_ids != {record["change_id"]}:
            raise ReviewEvidenceError(
                "audit change ID does not match evidence")
        source_refs = {item["id"] for item in record["authoritative_sources"]} | {
            item["reference"] for item in record["authoritative_sources"]
        }
        evidence_refs = {record["id"], record["review"]["reference"]} | set(
            record["lifecycle"]["evidence_references"])
        scopes = {item["repository_id"]
            : item for item in record["repository_scope"]}
        for event in events:
            if not set(event["authoritative_source_references"]).issubset(source_refs):
                raise ReviewEvidenceError(
                    "audit authoritative source reference is unresolved")
            if not set(event["evidence_references"]).issubset(evidence_refs):
                raise ReviewEvidenceError(
                    "audit evidence reference is unresolved")
            for repository in event["repositories"]:
                if repository["repository_id"] not in scopes:
                    raise ReviewEvidenceError(
                        "audit repository is absent from evidence scope")
                scope = scopes[repository["repository_id"]]
                fixed = {scope["base"], scope["head"]} - \
                    {None, "not-applicable"}
                if fixed and repository["revision"] not in fixed:
                    raise ReviewEvidenceError(
                        "audit repository revision disagrees with evidence")
            if event["action"] == "lifecycle-transition":
                target = event["new_lifecycle"]
                if target == "implemented" and not (
                        record["lifecycle"]["status"] == "complete"
                        and record["lifecycle"]["transition"] in {"implemented", "verified"}):
                    raise ReviewEvidenceError(
                        "implemented transition disagrees with evidence")
                if target == "verified" and record["lifecycle"]["transition"] != "verified":
                    raise ReviewEvidenceError(
                        "verified transition disagrees with evidence")
                if target == "verified":
                    implementers = set(record["review"]["implementers"])
                    approvals = event["approvals"]
                    if any(item["actor_id"] in implementers for item in approvals):
                        raise ReviewEvidenceError(
                            "independent verified approval cannot come from an implementer")
                    if record["risk"]["level"] == "high":
                        reviewer_id = record["review"]["reviewer_id"]
                        resolvable_references = set(event["evidence_references"]) | {
                            record["id"], record["review"]["reference"],
                        }
                        counted_approvals = [
                            item for item in approvals
                            if item["reference"] in resolvable_references
                        ]
                        if (record["review"]["independence"] != "independent"
                                or not record["review"]["fresh_context"]
                                or reviewer_id in implementers
                                or reviewer_id not in {
                                    item["actor_id"] for item in counted_approvals
                        }):
                            raise ReviewEvidenceError(
                                "high-risk verified approval requires the independent evidence "
                                "reviewer and a resolvable approval reference")
    return events

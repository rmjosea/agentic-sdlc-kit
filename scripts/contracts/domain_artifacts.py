"""Validate parallel v2 ADR and glossary semantics entirely in memory.

The public validators accept normalized models from :mod:`scripts.contracts.markdown`.
Glossary validation also requires the raw Markdown because term fields and their
values are intentionally not promoted into the shared parser model. ADR raw
Markdown is optional for set validation and, when supplied, proves that every
published section has non-empty content. All inputs are bounded before sorting
or graph work. This module performs no filesystem, Git, subprocess, or network
operation.

Glossary relationships resolve only to exact canonical headings in the same
artifact. They never create cross-artifact term authority. Canonical terms,
relationships, and rejected synonyms use NFC plus Unicode case folding for
identity; emitted ordering is deterministic by that identity.
"""

from __future__ import annotations

import datetime as _datetime
import re
import unicodedata
from typing import Any, Optional

from scripts.contracts import markdown


MAX_OBJECT_ITEMS = 1000
MAX_MODEL_ARRAY_ITEMS = 1000
MAX_ADR_SET_ITEMS = 1000
MAX_SOURCES = 100
MAX_SUPERSEDES = 100
MAX_ADR_SECTIONS = 8
MAX_GLOSSARY_TERMS = 1000
MAX_GLOSSARY_SECTIONS = MAX_GLOSSARY_TERMS + 1
MAX_SOURCE_BYTES = 1_000_000
MAX_STRING_LENGTH = 100_000
MAX_TERM_LENGTH = 200
MAX_FIELD_LENGTH = 2_000
MAX_REFERENCE_LENGTH = 500

_ADR_RE = re.compile(r"^ADR-[0-9]+$")
_GLOSSARY_RE = re.compile(r"^GLOSSARY-[0-9]+$")
_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_QUALIFIED_REFERENCE_RE = re.compile(
    r"^[A-Z]+-[0-9]+(?:-[A-Z]+-[0-9]+)?#(?:REQ|AC|TASK)-[0-9]+$")
_LOCAL_REFERENCE_RE = re.compile(r"^(?:REQ|AC|TASK)-[0-9]+$")
_HEADING_RE = re.compile(r"^(#{2,6})[ \t]+(.+?)$")

_DOCUMENT_FIELDS = {
    "metadata", "h1", "sections", "local_ids", "references", "placeholders",
}
_ADR_METADATA_FIELDS = {
    "schema_version", "id", "type", "sources", "status", "date",
    "supersedes", "superseded_by",
}
_GLOSSARY_METADATA_FIELDS = {
    "schema_version", "id", "type", "sources", "status",
}
_ADR_STATUSES = {"proposed", "accepted", "deprecated", "superseded"}
_GLOSSARY_STATUSES = {"draft", "active", "archived"}
_TRANSITIONS = {
    "architecture-decision": frozenset({
        ("proposed", "accepted"),
        ("accepted", "deprecated"),
        ("accepted", "superseded"),
    }),
    "domain-context": frozenset({
        ("draft", "active"),
        ("active", "archived"),
    }),
}
_ADR_SECTION_ORDER = (
    "Context", "Decision", "Alternatives", "Confirmed rationale",
    "Repository evidence", "Agent inference", "Unknowns", "Consequences",
)
_ADR_CORE_SECTIONS = {"Context", "Decision", "Consequences"}
_TERM_FIELDS = (
    "Meaning", "Relationships", "Rejected ambiguous synonyms", "Source",
)
_ALLOWED_METADATA = {
    "schema_version", "id", "type", "sources", "status", "date",
    "supersedes", "superseded_by",
}


class DomainArtifactError(ValueError):
    """An ADR, glossary, lifecycle, or domain reference is malformed."""


def _has_disallowed_control(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def _object(value: object, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise DomainArtifactError(f"{label} must be an object")
    if len(value) > MAX_OBJECT_ITEMS:
        raise DomainArtifactError(f"{label} exceeds the object limit")
    for key in value:
        if not isinstance(key, str):
            raise DomainArtifactError(f"{label} keys must be strings")
        if len(key) > MAX_STRING_LENGTH:
            raise DomainArtifactError(f"{label} key exceeds the string limit")
        if _has_disallowed_control(key):
            raise DomainArtifactError(
                f"{label} key contains a control character")
    return value


def _exact(value: object, fields: set[str], label: str) -> dict[str, Any]:
    record = _object(value, label)
    actual = set(record)
    missing = sorted(fields - actual)
    unknown = sorted(actual - fields)
    if missing:
        raise DomainArtifactError(f"{label} missing field: {missing[0]}")
    if unknown:
        raise DomainArtifactError(f"{label} unknown field: {unknown[0]}")
    return record


def _array(
    value: object, label: str, *, nonempty: bool = False,
    max_items: int = MAX_MODEL_ARRAY_ITEMS,
) -> list[Any]:
    if type(value) is not list:
        raise DomainArtifactError(f"{label} must be an array")
    if len(value) > max_items:
        raise DomainArtifactError(f"{label} exceeds the item limit")
    if nonempty and not value:
        raise DomainArtifactError(f"{label} must be non-empty")
    return value


def _string(value: object, label: str, *, limit: int = MAX_STRING_LENGTH) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DomainArtifactError(f"{label} must be a non-empty string")
    if len(value) > limit:
        raise DomainArtifactError(f"{label} exceeds the string limit")
    if _has_disallowed_control(value):
        raise DomainArtifactError(f"{label} contains a control character")
    return value


def _strings(
    value: object, label: str, *, nonempty: bool = False,
    limit: int = MAX_STRING_LENGTH, max_items: int = MAX_MODEL_ARRAY_ITEMS,
) -> list[str]:
    values = _array(
        value, label, nonempty=nonempty, max_items=max_items)
    result = [
        _string(item, f"{label}[{index}]", limit=limit)
        for index, item in enumerate(values)
    ]
    if len(result) != len(set(result)):
        raise DomainArtifactError(f"{label} entries must be unique")
    return result


def _identity(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def _document(
    value: object, label: str, *, max_sections: int,
) -> dict[str, Any]:
    document = _exact(value, _DOCUMENT_FIELDS, label)
    _object(document["metadata"], f"{label} metadata")
    _string(document["h1"], f"{label} h1", limit=MAX_REFERENCE_LENGTH)
    _strings(
        document["sections"], f"{label} sections", max_items=max_sections)
    if _array(document["local_ids"], f"{label} local_ids"):
        raise DomainArtifactError(f"{label} must not declare local IDs")
    references = _strings(
        document["references"], f"{label} references", limit=MAX_REFERENCE_LENGTH)
    if any(_QUALIFIED_REFERENCE_RE.fullmatch(item) is None for item in references):
        raise DomainArtifactError(f"{label} references must be qualified")
    if _array(document["placeholders"], f"{label} placeholders"):
        raise DomainArtifactError(f"{label} must not contain placeholders")
    return document


def _metadata_common(metadata: dict[str, Any], artifact_type: str, label: str) -> None:
    if type(metadata["schema_version"]) is not int or metadata["schema_version"] != 2:
        raise DomainArtifactError(f"{label} schema_version must be 2")
    if metadata["type"] != artifact_type:
        raise DomainArtifactError(f"{label} type is invalid")
    sources = _strings(
        metadata["sources"], f"{label} sources", nonempty=True,
        limit=MAX_REFERENCE_LENGTH, max_items=MAX_SOURCES)
    if any(_LOCAL_REFERENCE_RE.fullmatch(item) is not None for item in sources):
        raise DomainArtifactError(
            f"{label} sources must not use local references")


def _source_text(source: object, label: str) -> str:
    if type(source) is bytes:
        if len(source) > MAX_SOURCE_BYTES:
            raise DomainArtifactError(f"{label} exceeds the byte limit")
    elif type(source) is str:
        if len(source) > MAX_SOURCE_BYTES:
            raise DomainArtifactError(f"{label} exceeds the character limit")
    else:
        raise DomainArtifactError(f"{label} must be UTF-8 bytes or text")
    try:
        return markdown.normalize_text(source)
    except (markdown.MarkdownError, UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise DomainArtifactError(f"{label} is invalid Markdown") from exc


def _source_backed(model: dict[str, Any], source: object, label: str) -> str:
    text = _source_text(source, label)
    try:
        parsed = markdown.parse_markdown(
            text, allowed_metadata_keys=_ALLOWED_METADATA, mode="rendered")
    except (markdown.MarkdownError, ValueError, TypeError, RecursionError) as exc:
        raise DomainArtifactError(f"{label} is invalid Markdown") from exc
    if parsed != model:
        raise DomainArtifactError(
            f"{label} does not match the normalized model")
    return text


def _heading_blocks(text: str, label: str) -> list[tuple[int, str, str]]:
    lines = text.splitlines()
    try:
        frontmatter_end = lines.index("---", 1)
    except ValueError as exc:
        raise DomainArtifactError(
            f"{label} frontmatter is not closed") from exc
    headings: list[tuple[int, str, int]] = []
    for index in range(frontmatter_end + 1, len(lines)):
        match = _HEADING_RE.fullmatch(lines[index])
        if match is not None:
            if len(headings) >= MAX_GLOSSARY_SECTIONS:
                raise DomainArtifactError(f"{label} exceeds the heading limit")
            headings.append((len(match.group(1)), match.group(2), index))
    blocks: list[tuple[int, str, str]] = []
    for index, (level, title, start) in enumerate(headings):
        end = headings[index + 1][2] if index + \
            1 < len(headings) else len(lines)
        body = "\n".join(lines[start + 1:end]).strip()
        if len(body) > MAX_STRING_LENGTH:
            raise DomainArtifactError(
                f"{label} section exceeds the string limit")
        blocks.append((level, title, body))
    return blocks


def transition_allowed(artifact_type: object, before: object, after: object) -> bool:
    """Return whether one explicit ADR or glossary lifecycle transition is legal.

    Unknown string types or states return ``False``. Non-string values raise the
    module's typed error. Repeating a status is not a transition, and archived,
    deprecated, and superseded records are terminal.
    """
    if not all(isinstance(value, str) for value in (artifact_type, before, after)):
        raise DomainArtifactError("lifecycle type and states must be strings")
    return (before, after) in _TRANSITIONS.get(artifact_type, frozenset())


def require_transition(artifact_type: object, before: object, after: object) -> None:
    """Raise :class:`DomainArtifactError` unless the transition is legal."""
    if not transition_allowed(artifact_type, before, after):
        raise DomainArtifactError(
            f"forbidden {artifact_type} transition: {before} -> {after}")


def validate_adr_model(
    model: object, *, source: Optional[bytes | str] = None,
) -> dict[str, Any]:
    """Validate one closed ADR model and optionally its non-empty section bodies.

    The Nygard core sections are always required. Optional evidence sections may
    be omitted, but any present section must occupy its one canonical position.
    Set-level supersession reciprocity is checked by :func:`validate_adr_set`.
    """
    document = _document(
        model, "ADR model", max_sections=MAX_ADR_SECTIONS)
    metadata = _exact(
        document["metadata"], _ADR_METADATA_FIELDS, "ADR metadata")
    _metadata_common(metadata, "architecture-decision", "ADR metadata")
    identifier = metadata["id"]
    if not isinstance(identifier, str) or _ADR_RE.fullmatch(identifier) is None:
        raise DomainArtifactError("ADR id must be an ADR ID")
    status = metadata["status"]
    if not isinstance(status, str) or status not in _ADR_STATUSES:
        raise DomainArtifactError("ADR status is invalid")
    date = metadata["date"]
    if not isinstance(date, str) or _DATE_RE.fullmatch(date) is None:
        raise DomainArtifactError("ADR date must use YYYY-MM-DD")
    try:
        parsed_date = _datetime.date.fromisoformat(date)
    except ValueError as exc:
        raise DomainArtifactError("ADR date must be a real date") from exc
    if parsed_date.isoformat() != date:
        raise DomainArtifactError("ADR date must be canonical")

    supersedes = _strings(
        metadata["supersedes"], "ADR supersedes", limit=MAX_REFERENCE_LENGTH,
        max_items=MAX_SUPERSEDES)
    if any(_ADR_RE.fullmatch(item) is None for item in supersedes):
        raise DomainArtifactError("ADR supersedes entries must be ADR IDs")
    if identifier in supersedes:
        raise DomainArtifactError("ADR must not supersede itself")
    replacement = metadata["superseded_by"]
    if status == "superseded":
        if not isinstance(replacement, str) or _ADR_RE.fullmatch(replacement) is None:
            raise DomainArtifactError(
                "superseded ADR requires one replacement ADR ID")
        if replacement == identifier:
            raise DomainArtifactError("ADR must not be superseded by itself")
    elif replacement is not None:
        raise DomainArtifactError(
            "proposed, accepted, and deprecated ADRs require superseded_by null")

    expected_prefix = f"{identifier}: "
    h1 = document["h1"]
    title = h1[len(expected_prefix):] if h1.startswith(expected_prefix) else ""
    if not title or title != title.strip():
        raise DomainArtifactError("ADR H1 must be 'ADR-N: title'")
    sections = document["sections"]
    if not _ADR_CORE_SECTIONS.issubset(sections):
        raise DomainArtifactError(
            "ADR requires Context, Decision, and Consequences")
    expected_sections = [
        name for name in _ADR_SECTION_ORDER if name in sections]
    if sections != expected_sections:
        raise DomainArtifactError(
            "ADR sections must use canonical order without duplicates")

    if source is not None:
        text = _source_backed(document, source, "ADR source")
        blocks = _heading_blocks(text, "ADR source")
        if [(level, title) for level, title, _ in blocks] != [
            (2, title) for title in sections
        ]:
            raise DomainArtifactError(
                "ADR source headings do not match its sections")
        for _, title, body in blocks:
            if not body:
                raise DomainArtifactError(
                    f"ADR section {title} must be non-empty")
    return document


def validate_adr_set(models: object) -> list[dict[str, Any]]:
    """Validate bounded ADR identity, replacement reciprocity, and acyclicity.

    Every ``supersedes`` target must exist, be in ``superseded`` status, and
    point back through ``superseded_by``. Every superseded ADR has exactly one
    existing replacement whose ``supersedes`` array includes it. One replacement
    may supersede multiple old ADRs. Results are returned in ID order.
    """
    values = _array(models, "ADR set", max_items=MAX_ADR_SET_ITEMS)
    validated = [validate_adr_model(value) for value in values]
    by_id: dict[str, dict[str, Any]] = {}
    for document in validated:
        identifier = document["metadata"]["id"]
        if identifier in by_id:
            raise DomainArtifactError(f"duplicate ADR ID: {identifier}")
        by_id[identifier] = document

    for identifier in sorted(by_id):
        metadata = by_id[identifier]["metadata"]
        replacement = metadata["superseded_by"]
        if metadata["status"] == "superseded":
            if replacement not in by_id:
                raise DomainArtifactError(
                    f"ADR {identifier} replacement is missing")
            if identifier not in by_id[replacement]["metadata"]["supersedes"]:
                raise DomainArtifactError(
                    f"ADR {identifier} replacement is not reciprocal")
        for old_id in metadata["supersedes"]:
            if old_id not in by_id:
                raise DomainArtifactError(
                    f"ADR {identifier} supersedes target is missing")
            old = by_id[old_id]["metadata"]
            if old["status"] != "superseded" or old["superseded_by"] != identifier:
                raise DomainArtifactError(
                    f"ADR {identifier} supersedes target is not reciprocal")

    for start in sorted(by_id):
        seen: set[str] = set()
        current = start
        while by_id[current]["metadata"]["status"] == "superseded":
            if current in seen:
                raise DomainArtifactError(
                    "ADR supersession graph contains a cycle")
            seen.add(current)
            replacement = by_id[current]["metadata"]["superseded_by"]
            if replacement not in by_id:
                break
            current = replacement
    return [by_id[identifier] for identifier in sorted(by_id)]


def _comma_values(value: str, label: str) -> list[str]:
    if value == "none":
        return []
    parts = [part.strip() for part in value.split(",")]
    if any(not part for part in parts) or value != ", ".join(parts):
        raise DomainArtifactError(
            f"{label} must be 'none' or a comma-separated list with canonical spacing")
    identities = [_identity(part) for part in parts]
    if len(identities) != len(set(identities)):
        raise DomainArtifactError(f"{label} entries must be unique")
    if identities != sorted(identities):
        raise DomainArtifactError(
            f"{label} entries must use deterministic order")
    return parts


def validate_glossary_model(model: object, *, source: bytes | str) -> dict[str, Any]:
    """Validate and normalize one source-backed v2 domain glossary.

    Terms are H3 canonical headings below the sole ``Terms`` H2. Each term has
    exactly four single-line fields. Meanings and per-term sources are non-empty
    and bounded. Relationships use exact canonical terms from this artifact and
    reject self-relations. Rejected synonyms are unique across the artifact and
    cannot collide with any canonical term under NFC/casefold identity.
    """
    document = _document(
        model, "glossary model", max_sections=MAX_GLOSSARY_SECTIONS)
    metadata = _exact(
        document["metadata"], _GLOSSARY_METADATA_FIELDS, "glossary metadata")
    _metadata_common(metadata, "domain-context", "glossary metadata")
    identifier = metadata["id"]
    if not isinstance(identifier, str) or _GLOSSARY_RE.fullmatch(identifier) is None:
        raise DomainArtifactError("glossary id must be a GLOSSARY ID")
    status = metadata["status"]
    if not isinstance(status, str) or status not in _GLOSSARY_STATUSES:
        raise DomainArtifactError("glossary status is invalid")

    text = _source_backed(document, source, "glossary source")
    blocks = _heading_blocks(text, "glossary source")
    sections = document["sections"]
    if not blocks or blocks[0][0:2] != (2, "Terms"):
        raise DomainArtifactError(
            "glossary requires one leading ## Terms section")
    if blocks[0][2]:
        raise DomainArtifactError(
            "glossary Terms section may contain only term records")
    if len(blocks) < 2:
        raise DomainArtifactError("glossary requires at least one term")
    if [(level, title) for level, title, _ in blocks] != [
        (2, "Terms"), *[(3, title) for title in sections[1:]]
    ] or sections[0] != "Terms":
        raise DomainArtifactError(
            "glossary headings must be ## Terms then canonical H3 terms")

    raw_terms: list[dict[str, Any]] = []
    canonical_by_identity: dict[str, str] = {}
    for index, (_, term, body) in enumerate(blocks[1:]):
        _string(term, f"term[{index}] canonical heading",
                limit=MAX_TERM_LENGTH)
        if (term != term.strip() or "," in term
                or _identity(term) in {"none", "terms"}):
            raise DomainArtifactError(
                f"term[{index}] canonical heading is invalid")
        identity = _identity(term)
        if identity in canonical_by_identity:
            raise DomainArtifactError(f"duplicate canonical term: {term}")
        canonical_by_identity[identity] = term
        lines = [line for line in body.splitlines() if line]
        if len(lines) != len(_TERM_FIELDS):
            raise DomainArtifactError(
                f"term {term} must contain exactly four fields")
        fields: dict[str, str] = {}
        for field_index, field in enumerate(_TERM_FIELDS):
            prefix = f"- {field}: "
            line = lines[field_index]
            if not line.startswith(prefix):
                raise DomainArtifactError(
                    f"term {term} field {field_index + 1} must be {field}")
            value = line[len(prefix):]
            field_limit = MAX_REFERENCE_LENGTH if field == "Source" else MAX_FIELD_LENGTH
            fields[field] = _string(
                value, f"term {term} {field}", limit=field_limit)
        if fields["Source"] == "none":
            raise DomainArtifactError(
                f"term {term} Source must identify a source")
        raw_terms.append({"term": term, "fields": fields})

    term_identities = [_identity(item["term"]) for item in raw_terms]
    if term_identities != sorted(term_identities):
        raise DomainArtifactError(
            "canonical terms must use deterministic order")

    rejected_owners: dict[str, str] = {}
    normalized_terms: list[dict[str, Any]] = []
    for item in raw_terms:
        term = item["term"]
        fields = item["fields"]
        relationships = _comma_values(
            fields["Relationships"], f"term {term} Relationships")
        resolved: list[str] = []
        for related in relationships:
            identity = _identity(related)
            canonical = canonical_by_identity.get(identity)
            if canonical is None or canonical != related:
                raise DomainArtifactError(
                    f"term {term} relationship does not resolve to an exact canonical term")
            if identity == _identity(term):
                raise DomainArtifactError(
                    f"term {term} must not relate to itself")
            resolved.append(canonical)

        synonyms = _comma_values(
            fields["Rejected ambiguous synonyms"],
            f"term {term} Rejected ambiguous synonyms")
        for synonym in synonyms:
            identity = _identity(synonym)
            if identity in canonical_by_identity:
                raise DomainArtifactError(
                    f"rejected synonym {synonym} collides with a canonical term")
            if identity in rejected_owners:
                raise DomainArtifactError(
                    f"rejected synonym {synonym} is duplicated")
            rejected_owners[identity] = term
        normalized_terms.append({
            "term": term,
            "meaning": fields["Meaning"],
            "relationships": resolved,
            "rejected_ambiguous_synonyms": synonyms,
            "source": fields["Source"],
        })
    return {
        "metadata": metadata,
        "h1": document["h1"],
        "terms": normalized_terms,
    }

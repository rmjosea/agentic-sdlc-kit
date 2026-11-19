"""Evaluate the repository's bounded JSON Schema profile in memory.

``validate`` accepts an instance, one schema, and optional preloaded schemas. It
never reads a URI or path: external references resolve only to absolute URNs in
the supplied in-memory registry. The result contains deterministic structured
diagnostics instead of raising for malformed instances or schemas.

This is deliberately not a complete JSON Schema 2020-12 implementation. Every
schema keyword outside ``SUPPORTED_KEYWORDS`` is rejected, and ``format`` has no
semantics because it is outside that allowlist.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Optional, Sequence


DIALECT = "https://json-schema.org/draft/2020-12/schema"
SUPPORTED_KEYWORDS = frozenset({
    "$schema", "$id", "$defs", "$ref", "type", "properties", "required",
    "additionalProperties", "const", "enum", "oneOf", "anyOf", "allOf",
    "not", "if", "then", "else", "items", "minItems", "maxItems",
    "uniqueItems", "pattern", "minLength", "maxLength", "minimum", "maximum",
})
TYPE_NAMES = frozenset({
    "object", "array", "string", "integer", "number", "boolean", "null",
})
URN_RE = re.compile(
    r"^urn:[A-Za-z0-9][A-Za-z0-9-]*"
    r"(?::[A-Za-z0-9][A-Za-z0-9._-]*)*:v[1-9][0-9]*$"
)


@dataclass(frozen=True)
class Limits:
    """Resource ceilings for schema inspection and instance evaluation.

    All limits are positive integers. Depth applies to schemas, reference chains,
    and instances; node ceilings count schema objects and instance values.
    Strings, arrays, regular-expression source, and emitted diagnostics have
    independent ceilings.
    """

    max_depth: int = 64
    max_schema_nodes: int = 10000
    max_input_nodes: int = 50000
    max_errors: int = 100
    max_string_length: int = 100000
    max_array_length: int = 10000
    max_pattern_length: int = 1000
    max_evaluations: int = 100000


@dataclass(frozen=True)
class Diagnostic:
    """One stable validation failure at JSON Pointer instance/schema paths."""

    code: str
    instance_path: str
    schema_path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-serializable diagnostic with fixed keys."""
        return asdict(self)


@dataclass(frozen=True)
class ValidationResult:
    """The deterministic outcome returned by :func:`validate`."""

    valid: bool
    diagnostics: tuple[Diagnostic, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable result while preserving diagnostic order."""
        return {
            "valid": self.valid,
            "diagnostics": [item.as_dict() for item in self.diagnostics],
        }


class _Collector:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.items: list[Diagnostic] = []
        self.stopped = False

    def add(self, code: str, instance_path: str, schema_path: str, message: str) -> None:
        if self.stopped:
            return
        diagnostic = Diagnostic(code, instance_path, schema_path, message)
        if len(self.items) < self.limit:
            self.items.append(diagnostic)
            return
        self.items[-1] = Diagnostic(
            "limit.errors", "", "", "diagnostic limit exceeded")
        self.stopped = True


@dataclass
class _Context:
    documents: dict[str, Mapping[str, Any]]
    root: Mapping[str, Any]
    limits: Limits
    evaluations: int = 0
    exhausted: bool = False


class _SchemaIssue(Exception):
    def __init__(self, diagnostic: Diagnostic) -> None:
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


def _pointer(path: str, token: object) -> str:
    escaped = str(token).replace("~", "~0").replace("/", "~1")
    return f"{path}/{escaped}" if path else f"/{escaped}"


def _issue(code: str, schema_path: str, message: str) -> _SchemaIssue:
    return _SchemaIssue(Diagnostic(code, "", schema_path, message))


def _valid_limits(limits: Limits) -> bool:
    return all(type(value) is int and value > 0 for value in asdict(limits).values())


def _is_number(value: object) -> bool:
    return type(value) in (int, float) and not (
        isinstance(value, float) and not math.isfinite(value))


def _json_type(value: object, expected: str) -> bool:
    if expected == "object":
        return type(value) is dict
    if expected == "array":
        return type(value) is list
    if expected == "string":
        return type(value) is str
    if expected == "integer":
        return type(value) is int or (
            type(value) is float and math.isfinite(value) and value.is_integer())
    if expected == "number":
        return _is_number(value)
    if expected == "boolean":
        return type(value) is bool
    return value is None


def _json_key(value: object) -> object:
    if _is_number(value):
        return ("number", value)
    if value is None:
        return ("null",)
    if type(value) is bool:
        return ("boolean", value)
    if isinstance(value, str):
        return ("string", value)
    if isinstance(value, list):
        return ("array", tuple(_json_key(item) for item in value))
    if isinstance(value, dict):
        return ("object", tuple(
            (key, _json_key(value[key])) for key in sorted(value)))
    raise TypeError("not a JSON value")


def _json_equal(left: object, right: object) -> bool:
    return _json_key(left) == _json_key(right)


def _quantifier_end(pattern: str, index: int) -> int:
    if index >= len(pattern) or pattern[index] not in "*+?{":
        return index
    if pattern[index] in "*+?":
        return index + 1
    close = pattern.find("}", index + 1)
    if close < 0:
        return -1
    body = pattern[index + 1:close]
    if re.fullmatch(r"[0-9]+(?:,[0-9]*)?", body) is None:
        return -1
    parts = body.split(",", 1)
    minimum = int(parts[0])
    maximum = int(parts[1]) if len(parts) == 2 and parts[1] else None
    if minimum > 10000 or (maximum is not None and maximum > 10000):
        return -1
    if maximum is not None and maximum < minimum:
        return -1
    return close + 1


def _safe_repeated_group(body: str) -> bool:
    if not body or body[0] not in "-/:._#" or any(
        token in body for token in ("(", ")", "|", ".*", ".+", "?")
    ):
        return False
    if re.search(r"(?:^|[^\\])(?:[*]|\{0(?:,|\}))", body):
        return False
    return True


def _pattern_is_safe(pattern: str) -> bool:
    """Recognize a linear-time regex subset before the Python engine runs.

    The subset permits literals, classes, anchors, lookaheads, non-capturing
    groups, and ordinary atom quantifiers. Any quantified pattern must begin
    with ``^`` so ``re.search`` cannot restart it at every input position.
    Captures and engine extensions are
    rejected. Unbounded group repetition is accepted only for a flat,
    non-nullable group beginning with a mandatory separator, such as the
    repository's ``(?:-[a-z0-9]+)*`` name suffix. Adjacent quantified atoms,
    repeated alternations, nested repeated groups, and multiple wildcard repeats
    in one group are rejected rather than analyzed optimistically.
    """
    stack: list[tuple[int, str, int, bool]] = []
    groups: list[tuple[int, int, str, int]] = []
    wildcard_repeats: dict[int, int] = {0: 0}
    previous_quantified = False
    has_quantifier = False
    index = 0
    while index < len(pattern):
        character = pattern[index]
        if character == "\\":
            if index + 1 >= len(pattern):
                return False
            escaped_character = pattern[index + 1]
            if (escaped_character.isalnum() and escaped_character != "u") \
                    or pattern.startswith("\\g<", index):
                return False
            if escaped_character == "u":
                if (index + 6 > len(pattern)
                        or re.fullmatch(r"[0-9A-Fa-f]{4}", pattern[index + 2:index + 6]) is None):
                    return False
                index += 6
            else:
                index += 2
            quantifier = _quantifier_end(pattern, index)
            if quantifier < 0 or (quantifier > index and previous_quantified):
                return False
            if quantifier > index:
                has_quantifier = True
            previous_quantified = quantifier > index
            index = quantifier
            continue
        if character == "[":
            close = index + 1
            if close < len(pattern) and pattern[close] == "^":
                close += 1
            if close < len(pattern) and pattern[close] == "]":
                close += 1
            escaped = False
            while close < len(pattern):
                if not escaped and pattern[close] == "]":
                    break
                escaped = not escaped and pattern[close] == "\\"
                if pattern[close] != "\\":
                    escaped = False
                close += 1
            if close >= len(pattern):
                return False
            index = close + 1
            quantifier = _quantifier_end(pattern, index)
            if quantifier < 0 or (quantifier > index and previous_quantified):
                return False
            if quantifier > index:
                has_quantifier = True
            previous_quantified = quantifier > index
            index = quantifier
            continue
        if character == "(":
            if pattern.startswith("(?:", index):
                kind, content_start = "group", index + 3
            elif pattern.startswith("(?=", index) or pattern.startswith("(?!", index):
                kind, content_start = "lookahead", index + 3
            else:
                return False
            stack.append((index, kind, content_start, previous_quantified))
            wildcard_repeats[len(stack)] = 0
            previous_quantified = False
            index = content_start
            continue
        if character == ")":
            if not stack:
                return False
            start, kind, content_start, repeated_before = stack.pop()
            groups.append((start, index, kind, content_start))
            index += 1
            quantifier = _quantifier_end(pattern, index)
            if quantifier < 0:
                return False
            body = pattern[content_start:index - 1]
            if quantifier > index:
                has_quantifier = True
                if kind != "group" or not _safe_repeated_group(body):
                    return False
            elif kind == "group" and body not in ("^|/", "/|$"):
                return False
            previous_quantified = (
                repeated_before if kind == "lookahead" else quantifier > index)
            index = quantifier
            continue
        if character == ".":
            quantifier = _quantifier_end(pattern, index + 1)
            if quantifier > index + 1:
                has_quantifier = True
                depth = len(stack)
                wildcard_repeats[depth] = wildcard_repeats.get(depth, 0) + 1
                if wildcard_repeats[depth] > 1 or previous_quantified:
                    return False
                previous_quantified = True
                index = quantifier
            else:
                previous_quantified = False
                index += 1
            continue
        if character in "*+?{}]":
            return False
        if character == "|":
            if not stack or stack[-1][1] != "group":
                return False
            previous_quantified = False
            index += 1
            continue
        if character in "^$":
            index += 1
            continue
        quantifier = _quantifier_end(pattern, index + 1)
        if quantifier < 0 or (quantifier > index + 1 and previous_quantified):
            return False
        if quantifier > index + 1:
            has_quantifier = True
        previous_quantified = quantifier > index + 1
        index = quantifier
    if stack or (has_quantifier and not pattern.startswith("^")):
        return False
    for start, end, _, _ in groups:
        next_index = _quantifier_end(pattern, end + 1)
        if next_index < 0:
            return False
        if next_index > end + 1 and any(
            inner_start > start and inner_end < end
            for inner_start, inner_end, _, _ in groups
        ):
            return False
    return True


def _search_pattern(pattern: str, value: str) -> bool:
    """Run only a pattern already accepted by :func:`_pattern_is_safe`."""
    return re.search(pattern, value) is not None


def _measure_json(value: object, limits: Limits) -> Optional[Diagnostic]:
    stack: list[tuple[object, int, str]] = [(value, 1, "")]
    nodes = 0
    while stack:
        current, depth, path = stack.pop()
        nodes += 1
        if nodes > limits.max_input_nodes:
            return Diagnostic(
                "limit.input_nodes", "", "", "input node limit exceeded")
        if depth > limits.max_depth:
            return Diagnostic("limit.depth", path, "", "input depth limit exceeded")
        if isinstance(current, str):
            if len(current) > limits.max_string_length:
                return Diagnostic("limit.string", path, "", "string limit exceeded")
        elif type(current) is list:
            if len(current) > limits.max_array_length:
                return Diagnostic("limit.array", path, "", "array limit exceeded")
            for index in range(len(current) - 1, -1, -1):
                stack.append((current[index], depth +
                             1, _pointer(path, index)))
        elif type(current) is dict:
            for key in current:
                if not isinstance(key, str):
                    return Diagnostic(
                        "input.object_key", path, "", "object keys must be strings")
                if len(key) > limits.max_string_length:
                    return Diagnostic("limit.string", path, "", "string limit exceeded")
            for key in sorted(current, reverse=True):
                stack.append((current[key], depth + 1, _pointer(path, key)))
        elif current is not None and type(current) not in (bool, int, float):
            return Diagnostic(
                "input.type", path, "", "input is not a JSON-compatible value")
        elif isinstance(current, float) and not math.isfinite(current):
            return Diagnostic(
                "input.number", path, "", "input number must be finite")
    return None


def _schema_children(value: Mapping[str, Any], path: str) -> list[tuple[object, str]]:
    children: list[tuple[object, str]] = []
    definitions = value.get("$defs")
    if isinstance(definitions, dict):
        children.extend(
            (definitions[key], _pointer(_pointer(path, "$defs"), key))
            for key in sorted(definitions)
        )
    properties = value.get("properties")
    if isinstance(properties, dict):
        children.extend(
            (properties[key], _pointer(_pointer(path, "properties"), key))
            for key in sorted(properties)
        )
    additional = value.get("additionalProperties")
    if isinstance(additional, dict):
        children.append((additional, _pointer(path, "additionalProperties")))
    for keyword in ("oneOf", "anyOf", "allOf"):
        alternatives = value.get(keyword)
        if isinstance(alternatives, list):
            children.extend(
                (child, _pointer(_pointer(path, keyword), index))
                for index, child in enumerate(alternatives)
            )
    for keyword in ("not", "if", "then", "else", "items"):
        if keyword in value and isinstance(value[keyword], dict):
            children.append((value[keyword], _pointer(path, keyword)))
    return children


def _inspect_shape(value: object, path: str, limits: Limits) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise _issue("schema.shape", path, "schema must be an object")
    if len(value) > limits.max_array_length:
        raise _issue("limit.array", path, "schema object field limit exceeded")
    for key in value:
        if not isinstance(key, str):
            raise _issue("schema.shape", path,
                         "schema keyword must be a string")
        if len(key) > limits.max_string_length:
            raise _issue("limit.string", path,
                         "schema keyword string limit exceeded")
    unknown = sorted(set(value) - SUPPORTED_KEYWORDS)
    if unknown:
        raise _issue(
            "schema.unsupported_keyword", _pointer(path, unknown[0]),
            f"unsupported schema keyword: {unknown[0]}",
        )
    dialect = value.get("$schema")
    if dialect is not None:
        if not isinstance(dialect, str):
            raise _issue("schema.shape", _pointer(path, "$schema"),
                         "$schema must be a string")
        if len(dialect) > limits.max_string_length:
            raise _issue("limit.string", _pointer(path, "$schema"),
                         "$schema string limit exceeded")
        if dialect != DIALECT:
            raise _issue("schema.dialect", _pointer(path, "$schema"),
                         "unsupported schema dialect")
    identifier = value.get("$id")
    if identifier is not None:
        if not isinstance(identifier, str):
            raise _issue("schema.id", _pointer(path, "$id"),
                         "schema ID must be a string")
        if len(identifier) > limits.max_string_length:
            raise _issue("limit.string", _pointer(path, "$id"),
                         "schema ID string limit exceeded")
        if URN_RE.fullmatch(identifier) is None:
            raise _issue("schema.id", _pointer(path, "$id"),
                         "schema ID must be an absolute versioned URN")
    definitions = value.get("$defs")
    if definitions is not None:
        if not isinstance(definitions, dict) or len(definitions) > limits.max_array_length:
            raise _issue("schema.shape", _pointer(path, "$defs"),
                         "$defs must be a bounded object")
        for key in definitions:
            if not isinstance(key, str) or not key:
                raise _issue("schema.shape", _pointer(path, "$defs"),
                             "$defs keys must be non-empty strings")
            if len(key) > limits.max_string_length:
                raise _issue("limit.string", _pointer(path, "$defs"),
                             "$defs key string limit exceeded")
    reference = value.get("$ref")
    if reference is not None:
        if not isinstance(reference, str):
            raise _issue("schema.shape", _pointer(path, "$ref"),
                         "$ref must be a string")
        if len(reference) > limits.max_string_length:
            raise _issue("limit.string", _pointer(path, "$ref"),
                         "$ref string limit exceeded")
    expected = value.get("type")
    if expected is not None:
        if not isinstance(expected, str):
            raise _issue("schema.shape", _pointer(path, "type"),
                         "type must be one supported type name")
        if len(expected) > limits.max_string_length:
            raise _issue("limit.string", _pointer(path, "type"),
                         "type string limit exceeded")
        if expected not in TYPE_NAMES:
            raise _issue("schema.shape", _pointer(path, "type"),
                         "type must be one supported type name")
    properties = value.get("properties")
    if properties is not None:
        if not isinstance(properties, dict) or len(properties) > limits.max_array_length:
            raise _issue("schema.shape", _pointer(path, "properties"),
                         "properties must be a bounded object")
        for key in properties:
            if not isinstance(key, str):
                raise _issue("schema.shape", _pointer(path, "properties"),
                             "property names must be strings")
            if len(key) > limits.max_string_length:
                raise _issue("limit.string", _pointer(path, "properties"),
                             "property name string limit exceeded")
    required = value.get("required")
    if required is not None:
        if not isinstance(required, list) or len(required) > limits.max_array_length:
            raise _issue("schema.shape", _pointer(path, "required"),
                         "required must be a bounded array")
        for item in required:
            if not isinstance(item, str):
                raise _issue("schema.shape", _pointer(path, "required"),
                             "required entries must be strings")
            if len(item) > limits.max_string_length:
                raise _issue("limit.string", _pointer(path, "required"),
                             "required entry string limit exceeded")
        if len(required) != len(set(required)):
            raise _issue("schema.shape", _pointer(path, "required"),
                         "required entries must be unique")
    additional = value.get("additionalProperties")
    if additional is not None and type(additional) is not bool and not isinstance(additional, dict):
        raise _issue("schema.shape", _pointer(path, "additionalProperties"),
                     "additionalProperties must be a boolean or schema")
    enumeration = value.get("enum")
    if enumeration is not None:
        if not isinstance(enumeration, list) or not enumeration:
            raise _issue("schema.shape", _pointer(path, "enum"),
                         "enum must be a non-empty array of unique JSON values")
        issue = _measure_json(enumeration, limits)
        if issue is not None:
            raise _issue(
                issue.code if issue.code.startswith(
                    "limit.") else "schema.shape",
                _pointer(path, "enum"), "enum must contain bounded JSON values")
        keys = [_json_key(item) for item in enumeration]
        if len(keys) != len(set(keys)):
            raise _issue("schema.shape", _pointer(path, "enum"),
                         "enum must be a non-empty array of unique JSON values")
    if "const" in value:
        issue = _measure_json(value["const"], limits)
        if issue is not None:
            raise _issue(
                issue.code if issue.code.startswith(
                    "limit.") else "schema.shape",
                _pointer(path, "const"), "const must be a bounded JSON value")
    for keyword in ("oneOf", "anyOf", "allOf"):
        alternatives = value.get(keyword)
        if alternatives is not None and (
            not isinstance(alternatives, list) or not alternatives
            or len(alternatives) > limits.max_array_length
        ):
            raise _issue("schema.shape", _pointer(path, keyword),
                         f"{keyword} must be a non-empty array of schemas")
    for keyword in ("not", "if", "then", "else", "items"):
        if keyword in value and not isinstance(value[keyword], dict):
            raise _issue("schema.shape", _pointer(path, keyword),
                         f"{keyword} must be a schema object")
    if ("then" in value or "else" in value) and "if" not in value:
        keyword = "then" if "then" in value else "else"
        raise _issue("schema.shape", _pointer(path, keyword),
                     "then and else require if")
    for keyword in ("minItems", "maxItems", "minLength", "maxLength"):
        bound = value.get(keyword)
        if bound is not None and (type(bound) is not int or bound < 0):
            raise _issue("schema.shape", _pointer(path, keyword),
                         f"{keyword} must be a non-negative integer")
    for minimum, maximum in (("minItems", "maxItems"), ("minLength", "maxLength")):
        if minimum in value and maximum in value and value[minimum] > value[maximum]:
            raise _issue("schema.shape", _pointer(path, maximum),
                         f"{maximum} must not be less than {minimum}")
    unique = value.get("uniqueItems")
    if unique is not None and type(unique) is not bool:
        raise _issue("schema.shape", _pointer(path, "uniqueItems"),
                     "uniqueItems must be a boolean")
    for keyword in ("minimum", "maximum"):
        if keyword in value and not _is_number(value[keyword]):
            raise _issue("schema.shape", _pointer(path, keyword),
                         f"{keyword} must be a finite number")
    pattern = value.get("pattern")
    if pattern is not None:
        if not isinstance(pattern, str):
            raise _issue("schema.pattern", _pointer(path, "pattern"),
                         "pattern must be a string")
        if len(pattern) > limits.max_string_length:
            raise _issue("limit.string", _pointer(path, "pattern"),
                         "pattern string limit exceeded")
        if len(pattern) > limits.max_pattern_length:
            raise _issue("schema.pattern", _pointer(path, "pattern"),
                         "pattern exceeds the regex profile limit")
        if not _pattern_is_safe(pattern):
            raise _issue("schema.pattern", _pointer(path, "pattern"),
                         "pattern is outside the safe regular-expression subset")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise _issue("schema.pattern", _pointer(path, "pattern"),
                         "pattern is not a valid regular expression") from exc
    return value


def _inspect_document(
    document: Mapping[str, Any],
    limits: Limits,
    locations: dict[int, tuple[Mapping[str, Any], str]],
    nodes: int,
) -> int:
    stack: list[tuple[object, str, int]] = [(document, "", 1)]
    while stack:
        value, path, depth = stack.pop()
        nodes += 1
        if nodes > limits.max_schema_nodes:
            raise _issue("limit.schema_nodes", "",
                         "schema node limit exceeded")
        if depth > limits.max_depth:
            raise _issue("limit.depth", path, "schema depth limit exceeded")
        inspected = _inspect_shape(value, path, limits)
        locations[id(inspected)] = (inspected, path)
        children = _schema_children(inspected, path)
        for child, child_path in reversed(children):
            stack.append((child, child_path, depth + 1))
    return nodes


def _prepare_schemas(
    root: object,
    registry: Optional[Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]]],
    limits: Limits,
) -> tuple[
    Mapping[str, Any], dict[str, Mapping[str, Any]],
    list[Mapping[str, Any]], dict[int, tuple[Mapping[str, Any], str]],
]:
    if not isinstance(root, dict):
        raise _issue("schema.shape", "", "schema must be an object")
    documents: dict[str, Mapping[str, Any]] = {}
    roots: list[Mapping[str, Any]] = [root]
    locations: dict[int, tuple[Mapping[str, Any], str]] = {}
    nodes = _inspect_document(root, limits, locations, 0)
    root_identifier = root.get("$id")
    if isinstance(root_identifier, str):
        documents[root_identifier] = root

    def add_document(document: object, declared_key: Optional[str]) -> None:
        nonlocal nodes
        if not isinstance(document, dict):
            raise _issue("schema.shape", "",
                         "registry entries must be schema objects")
        nodes = _inspect_document(document, limits, locations, nodes)
        identifier = document.get("$id")
        if identifier is None:
            raise _issue("schema.registry", "",
                         "registry schemas must declare $id")
        assert isinstance(identifier, str)
        if declared_key is not None and declared_key != identifier:
            raise _issue("schema.registry", "",
                         "registry key must match schema $id")
        if identifier in documents:
            raise _issue("schema.registry", "", "duplicate schema URN")
        documents[identifier] = document
        roots.append(document)

    if registry is None:
        return root, documents, roots, locations
    if isinstance(registry, Mapping):
        if len(registry) > limits.max_array_length:
            raise _issue("limit.array", "", "registry entry limit exceeded")
        keys: list[str] = []
        for key in registry:
            if not isinstance(key, str):
                raise _issue("schema.registry", "",
                             "registry keys must be strings")
            if len(key) > limits.max_string_length:
                raise _issue("limit.string", "",
                             "registry key string limit exceeded")
            if URN_RE.fullmatch(key) is None:
                raise _issue("schema.registry", "",
                             "registry key must be an absolute versioned URN")
            keys.append(key)
            if len(keys) > limits.max_array_length:
                raise _issue("limit.array", "",
                             "registry entry limit exceeded")
        for key in sorted(keys):
            add_document(registry[key], key)
        return root, documents, roots, locations

    for index, document in enumerate(registry, 1):
        if index > limits.max_array_length:
            raise _issue("limit.array", "", "registry entry limit exceeded")
        add_document(document, None)
    return root, documents, roots, locations


def _decode_fragment(document: Mapping[str, Any], fragment: str) -> Mapping[str, Any]:
    if not fragment:
        return document
    if not fragment.startswith("/"):
        raise _issue("schema.ref_unsafe", "",
                     "reference fragment must be a JSON Pointer")
    current: object = document
    for raw in fragment[1:].split("/"):
        if re.search(r"~(?:[^01]|$)", raw):
            raise _issue("schema.ref_unsafe", "",
                         "reference contains an invalid escape")
        token = raw.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            raise _issue("schema.ref_unknown", "",
                         "reference target is unknown")
        current = current[token]
    if not isinstance(current, dict):
        raise _issue("schema.ref_unknown", "",
                     "reference target is not a schema")
    return current


def _resolve_ref(
    reference: str,
    current_root: Mapping[str, Any],
    documents: Mapping[str, Mapping[str, Any]],
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    if reference.startswith("#"):
        return _decode_fragment(current_root, reference[1:]), current_root
    base, separator, fragment = reference.partition("#")
    if URN_RE.fullmatch(base) is None:
        raise _issue("schema.ref_unsafe", "",
                     "reference must be local or an absolute URN")
    if base not in documents:
        raise _issue("schema.ref_unknown", "",
                     "reference URN is not preloaded")
    document = documents[base]
    return _decode_fragment(document, fragment if separator else ""), document


def _reject_reference_cycles(
    locations: Mapping[int, tuple[Mapping[str, Any], str]],
    documents: Mapping[str, Mapping[str, Any]],
    roots: Sequence[Mapping[str, Any]],
    limits: Limits,
) -> None:
    edges: dict[int, int] = {}
    root_by_node: dict[int, Mapping[str, Any]] = {}
    for root in roots:
        stack = [root]
        seen: set[int] = set()
        while stack:
            node = stack.pop()
            if id(node) in seen:
                continue
            seen.add(id(node))
            root_by_node[id(node)] = root
            stack.extend(child for child, _ in _schema_children(
                node, "") if isinstance(child, dict))
    for identity, (node, path) in locations.items():
        reference = node.get("$ref")
        if reference is not None:
            try:
                target, _ = _resolve_ref(
                    reference, root_by_node[identity], documents)
            except _SchemaIssue as exc:
                raise _issue(exc.diagnostic.code, _pointer(path, "$ref"),
                             exc.diagnostic.message) from exc
            if id(target) not in locations:
                raise _issue("schema.ref_unknown", _pointer(path, "$ref"),
                             "reference target is not a declared schema location")
            edges[identity] = id(target)
    state: dict[int, int] = {}

    def visit(identity: int, depth: int) -> None:
        if depth > limits.max_depth:
            raise _issue("limit.depth", "", "reference depth limit exceeded")
        marker = state.get(identity, 0)
        if marker == 1:
            path = locations.get(identity, ({}, ""))[1]
            raise _issue("schema.ref_cycle", _pointer(path, "$ref"),
                         "cyclic schema reference")
        if marker == 2:
            return
        state[identity] = 1
        target = edges.get(identity)
        if target is not None:
            visit(target, depth + 1)
        state[identity] = 2

    for identity in sorted(edges, key=lambda item: locations[item][1]):
        visit(identity, 1)


def _branch_valid(
    instance: object,
    contract: Mapping[str, Any],
    path: str,
    schema_path: str,
    context: _Context,
    current_root: Mapping[str, Any],
    depth: int,
) -> bool:
    collector = _Collector(1)
    _evaluate(instance, contract, path, schema_path, context,
              collector, current_root, depth)
    return not collector.items


def _evaluate(
    instance: object,
    contract: Mapping[str, Any],
    path: str,
    schema_path: str,
    context: _Context,
    collector: _Collector,
    current_root: Mapping[str, Any],
    depth: int,
) -> None:
    if collector.stopped:
        return
    context.evaluations += 1
    if context.evaluations > context.limits.max_evaluations:
        context.exhausted = True
        collector.add("limit.evaluations", path, schema_path,
                      "evaluation node limit exceeded")
        return
    if depth > context.limits.max_depth:
        collector.add("limit.depth", path, schema_path,
                      "evaluation depth limit exceeded")
        return
    reference = contract.get("$ref")
    if isinstance(reference, str):
        try:
            target, target_root = _resolve_ref(
                reference, current_root, context.documents)
        except _SchemaIssue as exc:
            diagnostic = exc.diagnostic
            collector.add(diagnostic.code, path, _pointer(schema_path, "$ref"),
                          diagnostic.message)
            return
        _evaluate(instance, target, path, _pointer(schema_path, "$ref"), context,
                  collector, target_root, depth + 1)
    expected = contract.get("type")
    type_matches = not isinstance(
        expected, str) or _json_type(instance, expected)
    if not type_matches:
        collector.add("type", path, _pointer(schema_path, "type"),
                      "instance has the wrong type")
    if "const" in contract and not _json_equal(instance, contract["const"]):
        collector.add("const", path, _pointer(schema_path, "const"),
                      "instance does not equal const")
    if "enum" in contract:
        instance_key = _json_key(instance)
        enum_keys = {_json_key(item) for item in contract["enum"]}
        if instance_key not in enum_keys:
            collector.add("enum", path, _pointer(schema_path, "enum"),
                          "instance is not in enum")
    for keyword in ("allOf",):
        for index, child in enumerate(contract.get(keyword, [])):
            _evaluate(instance, child, path, _pointer(_pointer(schema_path, keyword), index),
                      context, collector, current_root, depth + 1)
    alternatives = contract.get("anyOf")
    if isinstance(alternatives, list) and not any(
        _branch_valid(instance, child, path,
                      _pointer(_pointer(schema_path, "anyOf"), index),
                      context, current_root, depth + 1)
        for index, child in enumerate(alternatives)
    ):
        collector.add("anyOf", path, _pointer(schema_path, "anyOf"),
                      "instance does not match any alternative")
    alternatives = contract.get("oneOf")
    if isinstance(alternatives, list):
        matches = sum(
            _branch_valid(instance, child, path,
                          _pointer(_pointer(schema_path, "oneOf"), index),
                          context, current_root, depth + 1)
            for index, child in enumerate(alternatives)
        )
        if matches != 1:
            collector.add("oneOf", path, _pointer(schema_path, "oneOf"),
                          "instance must match exactly one alternative")
    excluded = contract.get("not")
    if isinstance(excluded, dict) and _branch_valid(
        instance, excluded, path, _pointer(schema_path, "not"),
        context, current_root, depth + 1,
    ):
        collector.add("not", path, _pointer(schema_path, "not"),
                      "instance matches the excluded schema")
    condition = contract.get("if")
    if isinstance(condition, dict):
        matched = _branch_valid(
            instance, condition, path, _pointer(schema_path, "if"),
            context, current_root, depth + 1)
        selected = "then" if matched else "else"
        child = contract.get(selected)
        if isinstance(child, dict):
            _evaluate(instance, child, path, _pointer(schema_path, selected),
                      context, collector, current_root, depth + 1)
    if context.exhausted:
        collector.add("limit.evaluations", path, schema_path,
                      "evaluation node limit exceeded")
        return
    if type(instance) is dict:
        properties = contract.get("properties", {})
        required = contract.get("required", [])
        for key in sorted(required):
            if key not in instance:
                collector.add("required", path, _pointer(schema_path, "required"),
                              f"required property is missing: {key}")
        additional = contract.get("additionalProperties", True)
        for key in sorted(instance):
            child = properties.get(key) if isinstance(
                properties, dict) else None
            if child is not None:
                _evaluate(instance[key], child, _pointer(path, key),
                          _pointer(_pointer(schema_path, "properties"), key),
                          context, collector, current_root, depth + 1)
            elif additional is False:
                collector.add(
                    "additionalProperties", _pointer(path, key),
                    _pointer(schema_path, "additionalProperties"),
                    "additional property is not allowed",
                )
            elif isinstance(additional, dict):
                _evaluate(instance[key], additional, _pointer(path, key),
                          _pointer(schema_path, "additionalProperties"),
                          context, collector, current_root, depth + 1)
    if type(instance) is list:
        length = len(instance)
        if "minItems" in contract and length < contract["minItems"]:
            collector.add("minItems", path, _pointer(schema_path, "minItems"),
                          "array has too few items")
        if "maxItems" in contract and length > contract["maxItems"]:
            collector.add("maxItems", path, _pointer(schema_path, "maxItems"),
                          "array has too many items")
        if contract.get("uniqueItems") is True:
            item_keys = [_json_key(item) for item in instance]
            if len(item_keys) != len(set(item_keys)):
                collector.add("uniqueItems", path,
                              _pointer(schema_path, "uniqueItems"),
                              "array items are not unique")
        child = contract.get("items")
        if isinstance(child, dict):
            for index, item in enumerate(instance):
                _evaluate(item, child, _pointer(path, index),
                          _pointer(schema_path, "items"), context,
                          collector, current_root, depth + 1)
    if isinstance(instance, str):
        length = len(instance)
        if "minLength" in contract and length < contract["minLength"]:
            collector.add("minLength", path, _pointer(schema_path, "minLength"),
                          "string is too short")
        if "maxLength" in contract and length > contract["maxLength"]:
            collector.add("maxLength", path, _pointer(schema_path, "maxLength"),
                          "string is too long")
        pattern = contract.get("pattern")
        if isinstance(pattern, str) and not _search_pattern(pattern, instance):
            collector.add("pattern", path, _pointer(schema_path, "pattern"),
                          "string does not match pattern")
    if _is_number(instance):
        if "minimum" in contract and instance < contract["minimum"]:
            collector.add("minimum", path, _pointer(schema_path, "minimum"),
                          "number is below minimum")
        if "maximum" in contract and instance > contract["maximum"]:
            collector.add("maximum", path, _pointer(schema_path, "maximum"),
                          "number is above maximum")


def validate(
    instance: object,
    contract: object,
    *,
    registry: Optional[
        Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]]
    ] = None,
    limits: Optional[Limits] = None,
) -> ValidationResult:
    """Validate one JSON-compatible value against the bounded schema profile.

    Args:
        instance: In-memory JSON-compatible value to evaluate.
        contract: Root schema object. Unsupported keywords are errors.
        registry: Optional in-memory schemas, as an iterable or URN-keyed map.
            Each schema must declare the same absolute ``:vN`` URN in ``$id``.
            Iteration and mapping keys are bounded before storage or sorting; no
            URI is fetched when a reference is absent.
        limits: Positive resource ceilings. Defaults are intentionally finite.

    Returns:
        A result whose diagnostics have stable codes, JSON Pointer paths, and
        deterministic ordering. Malformed input and schema data are represented
        as diagnostics rather than exceptions.

    Side effects:
        None. This function performs no filesystem, subprocess, or network I/O.
    """
    active_limits = limits or Limits()
    if not isinstance(active_limits, Limits) or not _valid_limits(active_limits):
        diagnostic = Diagnostic(
            "limit.configuration", "", "", "all limits must be positive integers")
        return ValidationResult(False, (diagnostic,))
    input_issue = _measure_json(instance, active_limits)
    if input_issue is not None:
        return ValidationResult(False, (input_issue,))
    try:
        root, documents, all_documents, locations = _prepare_schemas(
            contract, registry, active_limits)
        _reject_reference_cycles(locations, documents,
                                 all_documents, active_limits)
        context = _Context(documents, root, active_limits)
        collector = _Collector(active_limits.max_errors)
        _evaluate(instance, root, "", "", context, collector, root, 1)
        diagnostics = tuple(collector.items)
        return ValidationResult(not diagnostics, diagnostics)
    except _SchemaIssue as exc:
        return ValidationResult(False, (exc.diagnostic,))
    except (RecursionError, RuntimeError, TypeError, ValueError, OverflowError):
        diagnostic = Diagnostic(
            "schema.invalid", "", "", "schema could not be evaluated safely")
        return ValidationResult(False, (diagnostic,))

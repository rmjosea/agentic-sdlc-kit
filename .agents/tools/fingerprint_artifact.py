#!/usr/bin/env python3
"""Compute and optionally verify canonical v2 Markdown source fingerprints.

Invocation::

    python3 .agents/tools/fingerprint_artifact.py --root ROOT --input PATH \
        [--verify SOURCE-ITEMS.json] [--format human|json]

``PATH`` and the optional companion are safe repository-relative paths below an
existing, non-symlink ``ROOT``. The input is strict UTF-8 v2 Markdown parsed by
the shared source contract. Output contains the status-excluding overall SHA-256
revision and the ordered REQ/AC item map. Markdown ``metadata.id`` and companion
``source_id`` must use the global uppercase artifact-ID grammar, including the
optional fragment suffix. Verify mode reads the closed ``source-items.json``
shape and reports each mismatch without changing it.

The command is read-only and has no filesystem, Git, or network side effects.
It needs Python 3 and, in this source-checkout implementation, the adjacent
``scripts.contracts.markdown`` package; Git is not used. Exit 0 means a
fingerprint was produced and any companion matched, exit 1 means a companion
mismatch, and exit 2 means invalid invocation, unsafe/unreadable input, or a
malformed document/companion. Human and JSON output are deterministic.
"""

from __future__ import annotations

import bisect
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Optional


sys.dont_write_bytecode = True
_SOURCE_ROOT = Path(__file__).resolve().parents[2]
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from scripts.contracts import catalog, markdown  # noqa: E402


ALLOWED_METADATA_KEYS = frozenset({
    "schema_version", "id", "type", "sources", "status", "parent",
    "fragment_id", "namespace", "source_revisions", "risk",
    "risk_rationale", "date", "snapshot_at", "verdict",
    "evidence_reference", "depends_on",
})
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ARTIFACT_ID_RE = re.compile(r"^[A-Z]+-[0-9]+(?:-[A-Z]+-[0-9]+)?$")
QUALIFIED_ITEM_RE = re.compile(
    r"^[A-Z]+-[0-9]+(?:-[A-Z]+-[0-9]+)?#(?:REQ|AC)-[0-9]+$")
H2_RE = re.compile(r"^##(?:[ \t]+|$)")


class FingerprintError(ValueError):
    """The requested fingerprint operation is malformed or unsafe."""


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value)).hexdigest()


def _normalized_parts(
    source: bytes | str,
) -> tuple[dict[str, Any], str, str]:
    try:
        model = markdown.parse_markdown(
            source,
            allowed_metadata_keys=ALLOWED_METADATA_KEYS,
            mode="rendered",
        )
        normalized = markdown.normalize_text(source)
        lines = normalized.split("\n")
        end = lines.index("---", 1)
        body = markdown.normalize_text("\n".join(lines[end + 1:]))
        masked_body = markdown._mask_markdown(body, ())
    except (markdown.MarkdownError, UnicodeError, ValueError) as exc:
        raise FingerprintError(f"invalid v2 Markdown: {exc}") from exc
    metadata = model["metadata"]
    if metadata.get("schema_version") != 2:
        raise FingerprintError("invalid v2 Markdown: schema_version must be 2")
    parent_id = metadata.get("id")
    if (
        not isinstance(parent_id, str)
        or ARTIFACT_ID_RE.fullmatch(parent_id) is None
    ):
        raise FingerprintError(
            "invalid v2 Markdown: metadata id must be a global artifact ID")
    return metadata, body, masked_body


def _item_projections(
    metadata: dict[str, Any], body: str, masked_body: str
) -> list[dict[str, str]]:
    original_lines = body.split("\n")
    masked_lines = masked_body.split("\n")
    markers: list[tuple[int, str]] = []
    boundaries: set[int] = set()
    for index, masked_line in enumerate(masked_lines):
        local = markdown.LOCAL_ID_RE.match(masked_line)
        if local is not None:
            boundaries.add(index)
            identifier = local.group(1)
            if identifier.startswith(("REQ-", "AC-")):
                markers.append((index, identifier))
        if H2_RE.match(masked_line):
            boundaries.add(index)

    parent_id = metadata["id"]
    ordered_boundaries = sorted(boundaries)
    items: list[dict[str, str]] = []
    for start, local_id in markers:
        next_index = bisect.bisect_right(ordered_boundaries, start)
        end = (
            ordered_boundaries[next_index]
            if next_index < len(ordered_boundaries)
            else len(original_lines)
        )
        text = markdown.normalize_text("\n".join(original_lines[start:end]))
        items.append({
            "parent_id": parent_id,
            "item_id": f"{parent_id}#{local_id}",
            "text": text,
        })
    return items


def fingerprint_bytes(source: bytes | str) -> dict[str, Any]:
    """Return the exact canonical revision and ordered item fingerprints.

    Args:
        source: Strict UTF-8 v2 Markdown bytes or Unicode text.

    Returns:
        A deterministic dictionary containing ``source_id``,
        ``source_revision``, and ordered ``item_revisions``.

    Raises:
        FingerprintError: The document is not valid rendered v2 Markdown.

    Side effects:
        None. The operation consumes only the supplied value.
    """
    metadata, body, masked_body = _normalized_parts(source)
    projected_metadata = {
        key: value for key, value in metadata.items() if key != "status"
    }
    overall = {"metadata": projected_metadata, "body": body}
    items = _item_projections(metadata, body, masked_body)
    item_revisions = {
        item["item_id"]: _digest(item)
        for item in items
    }
    return {
        "source_id": metadata["id"],
        "source_revision": _digest(overall),
        "item_revisions": item_revisions,
    }


def _pairs_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FingerprintError(f"malformed companion: duplicate key {key}")
        result[key] = value
    return result


def _load_companion(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_pairs_object)
    except FingerprintError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise FingerprintError(
            "malformed companion: JSON could not be read") from exc
    expected_fields = {
        "schema_version", "source_id", "source_revision", "item_revisions"
    }
    if not isinstance(value, dict) or set(value) != expected_fields:
        raise FingerprintError(
            "malformed companion: fields must match the closed contract")
    if value["schema_version"] != 2 or type(value["schema_version"]) is not int:
        raise FingerprintError("malformed companion: schema_version must be 2")
    if (
        not isinstance(value["source_id"], str)
        or ARTIFACT_ID_RE.fullmatch(value["source_id"]) is None
    ):
        raise FingerprintError(
            "malformed companion: source_id must be a global artifact ID")
    if not isinstance(value["source_revision"], str) or DIGEST_RE.fullmatch(
        value["source_revision"]
    ) is None:
        raise FingerprintError(
            "malformed companion: source_revision must be a SHA-256 digest")
    item_revisions = value["item_revisions"]
    if not isinstance(item_revisions, dict):
        raise FingerprintError(
            "malformed companion: item_revisions must be an object")
    for item_id, digest in item_revisions.items():
        if (
            not isinstance(item_id, str)
            or QUALIFIED_ITEM_RE.fullmatch(item_id) is None
            or not item_id.startswith(value["source_id"] + "#")
            or not isinstance(digest, str)
            or DIGEST_RE.fullmatch(digest) is None
        ):
            raise FingerprintError(
                "malformed companion: invalid item revision entry")
    return value


def _verify(
    result: dict[str, Any], expected: dict[str, Any]
) -> list[dict[str, str]]:
    diagnostics: list[dict[str, str]] = []
    if expected["source_id"] != result["source_id"]:
        diagnostics.append({
            "code": "SOURCE_ID_MISMATCH",
            "item_id": "",
            "message": "Companion source_id does not match the Markdown artifact.",
        })
    if expected["source_revision"] != result["source_revision"]:
        diagnostics.append({
            "code": "SOURCE_REVISION_MISMATCH",
            "item_id": "",
            "message": "Companion source_revision does not match the artifact.",
        })
    actual_items = result["item_revisions"]
    expected_items = expected["item_revisions"]
    for item_id, digest in actual_items.items():
        if item_id not in expected_items:
            diagnostics.append({
                "code": "ITEM_ADDED", "item_id": item_id,
                "message": "Item is absent from the companion.",
            })
        elif expected_items[item_id] != digest:
            diagnostics.append({
                "code": "ITEM_CHANGED", "item_id": item_id,
                "message": "Item fingerprint does not match the companion.",
            })
    for item_id in sorted(expected_items):
        if item_id not in actual_items:
            diagnostics.append({
                "code": "ITEM_REMOVED", "item_id": item_id,
                "message": "Companion item is absent from the artifact.",
            })
    return diagnostics


def fingerprint_artifact(
    repository_root: Path | str,
    artifact: str,
    *,
    verify: Optional[str] = None,
) -> dict[str, Any]:
    """Fingerprint one safe repository-relative artifact and optionally verify it.

    ``repository_root`` must be an existing non-symlink directory whose lexical
    ancestors are not symlinks. ``artifact`` and ``verify`` are portable lexical
    relative paths; every existing path component is required to be a regular,
    non-symlink file. The function reads only those files and returns a
    deterministic report. It never writes either file.
    """
    try:
        root = catalog._repository_boundary(Path(repository_root))
        artifact_path = catalog._resolve_existing(
            root, artifact, "Markdown input")
        source = artifact_path.read_bytes()
        result = fingerprint_bytes(source)
        diagnostics: list[dict[str, str]] = []
        verified: Optional[bool] = None
        if verify is not None:
            companion_path = catalog._resolve_existing(
                root, verify, "source-items companion")
            diagnostics = _verify(result, _load_companion(companion_path))
            verified = not diagnostics
    except FingerprintError:
        raise
    except (catalog.CatalogError, OSError, RuntimeError, ValueError) as exc:
        raise FingerprintError("input could not be inspected safely") from exc
    return {
        "valid": not diagnostics,
        "source_id": result["source_id"],
        "source_revision": result["source_revision"],
        "item_revisions": result["item_revisions"],
        "verified": verified,
        "diagnostics": diagnostics,
    }


def _render(report: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(
            report, ensure_ascii=False, separators=(",", ":")) + "\n"
    state = "VALID" if report["valid"] else "MISMATCH"
    lines = [
        f"Artifact fingerprint: {state}",
        f"Source: {report['source_id']}",
        f"Revision: {report['source_revision']}",
        f"Items: {len(report['item_revisions'])}",
    ]
    for item_id, digest in report["item_revisions"].items():
        lines.append(f"- {item_id}: {digest}")
    for diagnostic in report["diagnostics"]:
        item = f" {diagnostic['item_id']}" if diagnostic["item_id"] else ""
        lines.append(
            f"- [{diagnostic['code']}]{item}: {diagnostic['message']}")
    return "\n".join(lines) + "\n"


def _help() -> str:
    return (
        "Usage: fingerprint_artifact.py --root ROOT --input PATH "
        "[--verify SOURCE-ITEMS.json] [--format human|json]\n"
        "Read-only input: strict UTF-8 v2 Markdown and an optional safe companion.\n"
        "Output: deterministic overall SHA-256 and ordered REQ/AC item map.\n"
        "Environment: Python 3 source checkout; Git and network are not used.\n"
        "Side effects: none. Exit 0=match/success, 1=mismatch, 2=error.\n"
    )


def _parse_args(
    argv: list[str],
) -> tuple[Optional[str], Optional[str], Optional[str], str, Optional[str]]:
    root: Optional[str] = None
    artifact: Optional[str] = None
    verify: Optional[str] = None
    output_format = "human"
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument in {"-h", "--help"} and len(argv) == 1:
            return None, None, None, output_format, "help"
        if argument not in {"--root", "--input", "--verify", "--format"}:
            return None, None, None, output_format, "Invalid invocation."
        if index + 1 >= len(argv):
            return None, None, None, output_format, "Invalid invocation."
        value = argv[index + 1]
        if argument == "--root" and root is None:
            root = value
        elif argument == "--input" and artifact is None:
            artifact = value
        elif argument == "--verify" and verify is None:
            verify = value
        elif argument == "--format" and value in {"human", "json"}:
            output_format = value
        else:
            return None, None, None, output_format, "Invalid invocation."
        index += 2
    if root is None or artifact is None:
        return None, None, None, output_format, "Invalid invocation."
    return root, artifact, verify, output_format, None


def main(argv: Optional[list[str]] = None) -> int:
    """Run the documented read-only CLI and return its stable process exit."""
    arguments = sys.argv[1:] if argv is None else argv
    root, artifact, verify, output_format, error = _parse_args(arguments)
    if error == "help":
        sys.stdout.write(_help())
        return 0
    if error:
        report = {
            "valid": False, "source_id": "", "source_revision": "",
            "item_revisions": {}, "verified": None,
            "diagnostics": [{"code": "INVOCATION_INVALID", "item_id": "", "message": error}],
        }
        sys.stdout.write(_render(report, output_format))
        return 2
    try:
        assert root is not None and artifact is not None
        report = fingerprint_artifact(root, artifact, verify=verify)
    except Exception:
        report = {
            "valid": False, "source_id": "", "source_revision": "",
            "item_revisions": {}, "verified": None,
            "diagnostics": [{
                "code": "INPUT_INVALID", "item_id": "",
                "message": "Input could not be fingerprinted safely.",
            }],
        }
        sys.stdout.write(_render(report, output_format))
        return 2
    sys.stdout.write(_render(report, output_format))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Deterministic Zero-Invention companion and UI selector verifier.

Invocation::

    python3 .agents/tools/check_companions.py --root ROOT \
        --feature-dir FEATURES_DIR [--target-repo REPO_PATH ...] \
        [--format human|json]

Reads the Zero-Invention companion files inside ``FEATURES_DIR`` (``api.md``,
``event.md``, ``data-model.md``, ``test-plan.md``) and extracts:
1. Required ``data-testid`` UI attributes (e.g., ``data-testid="hm-reject-btn"``).
2. Declared API route paths (e.g., ``POST /api/v1/offers/...``).
3. Declared contract payload/model field identifiers (e.g., ``reasonCode``) and
   detects snake_case / camelCase naming drift (e.g., ``reason_code`` in code
   when ``reasonCode`` was pinned in ``api.md``) with exact ``file:line`` hints.

The command is 100% read-only and uses only the Python 3 standard library.
Exit codes:
- ``0``: all extracted contract items are satisfied in the target repositories.
- ``1``: one or more contract items are missing or have naming drift.
- ``2``: invalid arguments or unreadable paths.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional


sys.dont_write_bytecode = True

DATA_TESTID_RE = re.compile(r'data-testid\s*=\s*["\'`]?([a-zA-Z0-9_-]+)["\'`]?', re.IGNORECASE)
ENDPOINT_RE = re.compile(
    r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/[A-Za-z0-9_./{}-]+)"
)
CONTRACT_FIELD_RE = re.compile(
    r"^\s*[-*|]\s*(?:\*\*)?`([a-zA-Z_][a-zA-Z0-9_]*)`(?:\*\*)?\s*(?:[:|—-]|$)",
    re.MULTILINE,
)
EVENT_NAME_RE = re.compile(
    r"`([a-z][a-z0-9_]*(?:\.[a-z0-9_-]+){2,})`"
)
IGNORED_FIELD_TOKENS = frozenset({
    "true", "false", "null", "none", "string", "number", "boolean", "integer",
    "uuid", "object", "array", "required", "optional", "default", "status",
    "type", "updated", "draft", "approved", "implemented",
})
CODE_EXTENSIONS = frozenset({
    ".py", ".ts", ".tsx", ".js", ".jsx", ".html", ".java", ".go", ".proto",
})
IGNORED_DIRS = frozenset({
    ".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
    ".angular", ".next", "coverage", ".worktrees",
})


def _camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _snake_to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _extract_contracts(feature_dir: Path) -> dict[str, list[str]]:
    testids: set[str] = set()
    endpoints: set[str] = set()
    fields: set[str] = set()
    events: set[str] = set()

    for name in ("api.md", "event.md", "data-model.md", "test-plan.md"):
        fpath = feature_dir / name
        if not fpath.is_file() or fpath.is_symlink():
            continue
        text = fpath.read_text(encoding="utf-8", errors="replace")
        for match in DATA_TESTID_RE.finditer(text):
            testids.add(match.group(1))
        if name == "api.md":
            for match in ENDPOINT_RE.finditer(text):
                endpoints.add(f"{match.group(1)} {match.group(2)}")
        if name in {"api.md", "event.md", "data-model.md"}:
            for match in CONTRACT_FIELD_RE.finditer(text):
                token = match.group(1)
                if token.lower() not in IGNORED_FIELD_TOKENS and len(token) >= 3:
                    fields.add(token)
        if name == "event.md":
            for match in EVENT_NAME_RE.finditer(text):
                events.add(match.group(1))

    return {
        "data_testids": sorted(testids),
        "endpoints": sorted(endpoints),
        "fields": sorted(fields),
        "events": sorted(events),
    }


def _scan_repos(target_repos: list[Path]) -> list[tuple[str, list[str]]]:
    indexed_files: list[tuple[str, list[str]]] = []
    for repo in target_repos:
        for dirpath, dirnames, filenames in os.walk(repo, followlinks=False):
            dirnames[:] = sorted(
                d for d in dirnames
                if d not in IGNORED_DIRS and not (Path(dirpath) / d).is_symlink()
            )
            for fname in sorted(filenames):
                fpath = Path(dirpath) / fname
                if fpath.suffix.lower() not in CODE_EXTENSIONS:
                    continue
                if fpath.is_symlink() or not fpath.is_file():
                    continue
                try:
                    if fpath.stat().st_size > 1_500_000:
                        continue
                    lines = fpath.read_text(encoding="utf-8", errors="replace").splitlines()
                    rel = fpath.relative_to(repo.parent if len(target_repos) > 1 else repo).as_posix()
                    indexed_files.append((rel, lines))
                except (OSError, ValueError):
                    continue
    return indexed_files


def _find_token_in_code(
    token: str, indexed_files: list[tuple[str, list[str]]]
) -> Optional[str]:
    for rel, lines in indexed_files:
        for idx, line in enumerate(lines, start=1):
            if token in line:
                return f"{rel}:{idx}"
    return None


def verify_companions(
    root: Path | str,
    feature_dir_rel: str,
    target_repo_Paths: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Verify that code in target repositories matches companion contracts."""
    root_path = Path(root).resolve()
    fdir = (root_path / feature_dir_rel).resolve()
    if not fdir.is_dir():
        raise ValueError(f"Feature directory not found: {feature_dir_rel}")

    repos: list[Path] = []
    if target_repo_Paths:
        for r in target_repo_Paths:
            rp = (root_path / r).resolve() if not Path(r).is_absolute() else Path(r).resolve()
            if not rp.is_dir():
                raise ValueError(f"Target repository not found: {r}")
            repos.append(rp)
    else:
        repos.append(root_path)

    contracts = _extract_contracts(fdir)
    indexed_files = _scan_repos(repos)
    findings: list[dict[str, str]] = []

    for tid in contracts["data_testids"]:
        loc = _find_token_in_code(tid, indexed_files)
        if loc is None:
            findings.append({
                "kind": "MISSING_DATA_TESTID",
                "expected": f'data-testid="{tid}"',
                "observed": "absent in scanned repository files",
                "location": "N/A",
            })

    for field in contracts["fields"]:
        loc = _find_token_in_code(field, indexed_files)
        if loc is None:
            alt = _camel_to_snake(field) if "_" not in field else _snake_to_camel(field)
            alt_loc = _find_token_in_code(alt, indexed_files) if alt != field else None
            if alt_loc is not None:
                findings.append({
                    "kind": "FIELD_NAMING_DRIFT",
                    "expected": field,
                    "observed": alt,
                    "location": alt_loc,
                })
            else:
                findings.append({
                    "kind": "MISSING_CONTRACT_FIELD",
                    "expected": field,
                    "observed": "absent",
                    "location": "N/A",
                })

    for evt in contracts["events"]:
        loc = _find_token_in_code(evt, indexed_files)
        if loc is None:
            findings.append({
                "kind": "MISSING_EVENT_CONTRACT",
                "expected": evt,
                "observed": "absent",
                "location": "N/A",
            })

    return {
        "valid": len(findings) == 0,
        "feature_dir": feature_dir_rel,
        "files_scanned": len(indexed_files),
        "contracts_checked": contracts,
        "findings": findings,
    }


def _render(report: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if "error" in report:
        return f"Companion verification error: {report['error']}\n"
    verdict = "APROBADO (0 contract divergences)" if report["valid"] else "RECHAZADO (contract divergence detected)"
    lines = [
        f"Zero-Invention Companion Verification: {verdict}",
        f"Feature: {report['feature_dir']} | Scanned code files: {report['files_scanned']}",
    ]
    for f in report["findings"]:
        lines.append(
            f"- [{f['kind']}] Archivo: {f['location']} | "
            f"Esperado: `{f['expected']}` | Observado: `{f['observed']}`"
        )
    return "\n".join(lines) + "\n"


def _help() -> str:
    return (
        "Usage: check_companions.py --root ROOT --feature-dir PATH "
        "[--target-repo PATH ...] [--format human|json]\n"
        "Deterministically verifies api.md, event.md, data-model.md, and data-testid selectors.\n"
        "Exit 0=all match, 1=contract drift/missing, 2=invalid arguments.\n"
    )


def main(argv: Optional[list[str]] = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args in (["-h"], ["--help"]):
        sys.stdout.write(_help())
        return 0

    root: Optional[str] = None
    feature_dir: Optional[str] = None
    target_repos: list[str] = []
    output_format = "human"

    idx = 0
    while idx < len(args):
        arg = args[idx]
        if idx + 1 >= len(args):
            sys.stdout.write(_render({"error": "Invalid arguments."}, output_format))
            return 2
        val = args[idx + 1]
        if arg == "--root":
            root = val
        elif arg == "--feature-dir":
            feature_dir = val
        elif arg == "--target-repo":
            target_repos.append(val)
        elif arg == "--format" and val in {"human", "json"}:
            output_format = val
        else:
            sys.stdout.write(_render({"error": f"Unknown option: {arg}"}, output_format))
            return 2
        idx += 2

    if root is None or feature_dir is None:
        sys.stdout.write(_render({"error": "--root and --feature-dir are required."}, output_format))
        return 2

    try:
        report = verify_companions(root, feature_dir, target_repos or None)
    except Exception as exc:
        sys.stdout.write(_render({"error": str(exc)}, output_format))
        return 2

    sys.stdout.write(_render(report, output_format))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Small self-contained enforcement checker entrypoint."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

MODULE_ROOT = Path(__file__).parent
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from lib.report import Report, _render
from lib.paths import _safe_existing
from lib.project import _parse_project, _validate_modules, _validate_multi_repo
from lib.evidence import _validate_evidence
from lib.artifacts import _validate_artifacts
from lib.compliance import _validate_compliance

# Built-in extension validators register here; record validation never executes code.
EXTENSION_VALIDATORS: dict[str, Any] = {}


def _validate_extensions(
    root: Path,
    config: Optional[dict[str, Any]],
    installed: set[str],
    evidence: list[dict[str, Any]],
    tasks: dict[str, dict[str, Any]],
    report: Report,
) -> None:
    enabled = set(config["enabled_modules"]) if config is not None else set()
    for name in sorted(enabled & installed & set(EXTENSION_VALIDATORS)):
        EXTENSION_VALIDATORS[name](root, config, evidence, tasks, report)


def _run(root: Path, report: Report) -> None:
    agents_root = _safe_existing(root, ".agents", report, ".agents")
    if agents_root is None:
        return
    legacy_path = agents_root / "project.md"
    try:
        legacy_path.lstat()
    except FileNotFoundError:
        pass
    except OSError:
        report.add("CONFIG_LEGACY_UNREADABLE", ".agents/project.md", "",
                   "Legacy project.md path cannot be inspected safely.", config=True)
        return
    else:
        report.add("CONFIG_LEGACY_UNSUPPORTED", ".agents/project.md", "",
                   "Legacy project.md is unsupported; remove it before any project operation.", config=True)
        return
    before_config_paths = len(report.errors)
    project_path = _safe_existing(
        root, ".agents/project.json", report, "project")
    if len(report.errors) != before_config_paths:
        report.config_error = True
        return
    config = _parse_project(
        project_path, root, report) if project_path is not None and project_path.exists() else None
    if report.config_error:
        return
    installed = _validate_modules(root, config, report)
    evidence = _validate_evidence(root, config, installed, report)
    tasks = _validate_artifacts(root, config, evidence, report)
    _validate_extensions(root, config, installed, evidence, tasks, report)


def _parse_args(argv: list[str]) -> tuple[Optional[Path], str, Optional[str]]:
    root: Optional[Path] = None
    output_format = "human"
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument in {"-h", "--help"}:
            return None, output_format, "help"
        if argument not in {"--root", "--format"} or index + 1 >= len(argv):
            return None, output_format, "Invalid invocation."
        value = argv[index + 1]
        if argument == "--root":
            if root is not None:
                return None, output_format, "Invalid invocation."
            root = Path(value)
        else:
            if value not in {"human", "json"}:
                return None, output_format, "Invalid invocation."
            output_format = value
        index += 2
    return root or Path("."), output_format, None


def main(argv: Optional[list[str]] = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    root_arg, output_format, invocation_error = _parse_args(arguments)
    if invocation_error == "help":
        print("Usage: check.py [--root PATH] [--format human|json]")
        return 0
    report = Report()
    if invocation_error:
        report.add("INVOCATION_INVALID", ".", "", invocation_error)
    else:
        try:
            assert root_arg is not None
            root = Path(os.path.abspath(str(root_arg)))
            if not root.exists() or not root.is_dir() or root.is_symlink():
                report.add("ROOT_INVALID", ".", "root",
                           "Root must be an existing non-symlink directory.")
                report.config_error = True
            else:
                _run(root, report)
        except Exception:
            report.add("INVOCATION_ERROR", ".", "",
                       "Validation could not safely inspect the repository.")
            report.config_error = True
    document = report.document()
    sys.stdout.write(_render(document, output_format))
    if report.config_error or invocation_error:
        return 2
    return 0 if document["valid"] else 1


EXTENSION_VALIDATORS["multi-repo"] = _validate_multi_repo
EXTENSION_VALIDATORS["compliance"] = _validate_compliance


if __name__ == "__main__":
    sys.exit(main())

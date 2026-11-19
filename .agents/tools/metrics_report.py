#!/usr/bin/env python3
"""Execution telemetry collector and empirical benchmark report generator.

Invocation::

    python3 .agents/tools/metrics_report.py --root ROOT \
        [--tasks PATH] [--metrics-jsonl PATH] [--format human|json]

Summarizes task completion progress from ``tasks.md`` and execution telemetry
from ``metrics.jsonl`` (produced by ``.agents/tools/run-tasks.sh``) to measure:
- Total tasks, completed ``[x]`` tasks, and breakdown by repository and modality
  (``[A]``, ``[I]``, ``[*]``).
- Total agent sessions executed, ``Pass@1`` first-attempt success rate, Circuit
  Breaker stops, and ``.env`` bureaucratic iterations saved compared to legacy
  loops (where every capability switch consumed an extra agent iteration).

The command is read-only and uses only the Python 3 standard library.
Exit 0 on success, 2 on invalid arguments.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Optional


sys.dont_write_bytecode = True

TASK_LINE_RE = re.compile(r"^-\s+\[([ xX])\]\s+\*\*(T[0-9]+)\*\*")
MOD_RE = re.compile(r"\[(A|I|\*)\]")
HEADER_REPO_RE = re.compile(r"^###\s+([A-Za-z0-9_.-]+)")
INLINE_REPO_RE = re.compile(r"repo:\s*`?([A-Za-z0-9_.-]+)`?")


def _parse_tasks_file(tasks_path: Path) -> dict[str, Any]:
    lines = tasks_path.read_text(encoding="utf-8", errors="replace").splitlines()
    current_repo = "default"
    total = 0
    completed = 0
    by_modality = {"A": 0, "I": 0, "*": 0}
    by_repo: dict[str, dict[str, int]] = {}

    for line in lines:
        m_head = HEADER_REPO_RE.match(line.strip())
        if m_head:
            current_repo = m_head.group(1)
            continue
        m_task = TASK_LINE_RE.match(line)
        if not m_task:
            continue
        checked = m_task.group(1).lower() == "x"
        m_mod = MOD_RE.search(line)
        modality = m_mod.group(1) if m_mod else "*"
        m_repo = INLINE_REPO_RE.search(line)
        repo = m_repo.group(1) if m_repo else current_repo

        total += 1
        if checked:
            completed += 1
        by_modality[modality] = by_modality.get(modality, 0) + 1
        repo_stats = by_repo.setdefault(repo, {"total": 0, "done": 0})
        repo_stats["total"] += 1
        if checked:
            repo_stats["done"] += 1

    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "pending_tasks": total - completed,
        "by_modality": by_modality,
        "by_repo": by_repo,
    }


def _parse_metrics_jsonl(metrics_path: Path) -> dict[str, Any]:
    if not metrics_path.is_file():
        return {
            "sessions_executed": 0,
            "tasks_passed": 0,
            "pass_at_1_count": 0,
            "pass_at_1_rate": 0.0,
            "circuit_breaker_stops": 0,
            "total_duration_sec": 0,
            "legacy_env_iterations_saved": 0,
        }

    records: list[dict[str, Any]] = []
    for raw in metrics_path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        try:
            records.append(json.loads(stripped))
        except json.JSONDecodeError:
            continue

    sessions = len(records)
    passed_Attempt1 = sum(
        1 for r in records if r.get("status") == "passed" and r.get("attempt") == 1
    )
    passed_total = sum(1 for r in records if r.get("status") == "passed")
    failed_attempts: dict[str, int] = {}
    for r in records:
        if r.get("status") == "failed":
            tid = str(r.get("task_id", ""))
            failed_attempts[tid] = failed_attempts.get(tid, 0) + 1

    cb_stops = sum(1 for count in failed_attempts.values() if count >= 2)
    total_duration = sum(int(r.get("duration_sec", 0)) for r in records)
    pass_rate = round((passed_Attempt1 / max(passed_total, 1)) * 100.0, 1) if passed_total else 0.0

    return {
        "sessions_executed": sessions,
        "tasks_passed": passed_total,
        "pass_at_1_count": passed_Attempt1,
        "pass_at_1_rate": pass_rate,
        "circuit_breaker_stops": cb_stops,
        "total_duration_sec": total_duration,
        "legacy_env_iterations_saved": passed_total,
    }


def build_metrics_report(
    root: Path | str,
    tasks_rel: Optional[str] = None,
    metrics_rel: Optional[str] = None,
) -> dict[str, Any]:
    """Build a deterministic telemetry summary from tasks.md and metrics.jsonl."""
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise ValueError(f"Root directory not found: {root}")

    tasks_summary: Optional[dict[str, Any]] = None
    if tasks_rel is not None:
        tpath = (root_path / tasks_rel).resolve()
        if not tpath.is_file():
            raise ValueError(f"Tasks file not found: {tasks_rel}")
        tasks_summary = _parse_tasks_file(tpath)

    mpath = (root_path / (metrics_rel or ".work/metrics.jsonl")).resolve()
    telemetry = _parse_metrics_jsonl(mpath)

    return {
        "valid": True,
        "tasks_summary": tasks_summary,
        "telemetry": telemetry,
    }


def _render(report: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if not report.get("valid", False):
        return f"Metrics report error: {report.get('error', 'Invalid invocation')}\n"

    lines = ["=== Agentic SDLC Telemetry & Benchmark Report ==="]
    ts = report.get("tasks_summary")
    if ts:
        lines.append(
            f"Tasks: {ts['completed_tasks']}/{ts['total_tasks']} done "
            f"(Modality: [A]={ts['by_modality'].get('A', 0)}, "
            f"[I]={ts['by_modality'].get('I', 0)}, "
            f"[*]={ts['by_modality'].get('*', 0)})"
        )
        for repo, counts in ts["by_repo"].items():
            lines.append(f"  - repo {repo}: {counts['done']}/{counts['total']} [x]")
    tel = report["telemetry"]
    lines.extend([
        f"Agent sessions executed: {tel['sessions_executed']}",
        f"Pass@1 rate: {tel['pass_at_1_rate']}% ({tel['pass_at_1_count']}/{tel['tasks_passed']})",
        f"Circuit Breaker stops (cap=2): {tel['circuit_breaker_stops']}",
        f"Bureaucratic .env iterations saved: {tel['legacy_env_iterations_saved']}",
        f"Total execution time: {tel['total_duration_sec']}s",
    ])
    return "\n".join(lines) + "\n"


def _help() -> str:
    return (
        "Usage: metrics_report.py --root ROOT [--tasks PATH] "
        "[--metrics-jsonl PATH] [--format human|json]\n"
        "Read-only telemetry collector and benchmark report generator.\n"
    )


def main(argv: Optional[list[str]] = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args in (["-h"], ["--help"]):
        sys.stdout.write(_help())
        return 0

    root: Optional[str] = None
    tasks_rel: Optional[str] = None
    metrics_rel: Optional[str] = None
    output_format = "human"

    idx = 0
    while idx < len(args):
        arg = args[idx]
        if idx + 1 >= len(args):
            sys.stdout.write(_render({"valid": False, "error": "Invalid arguments."}, output_format))
            return 2
        val = args[idx + 1]
        if arg == "--root":
            root = val
        elif arg == "--tasks":
            tasks_rel = val
        elif arg == "--metrics-jsonl":
            metrics_rel = val
        elif arg == "--format" and val in {"human", "json"}:
            output_format = val
        else:
            sys.stdout.write(_render({"valid": False, "error": f"Unknown option: {arg}"}, output_format))
            return 2
        idx += 2

    if root is None:
        sys.stdout.write(_render({"valid": False, "error": "--root is required."}, output_format))
        return 2

    try:
        report = build_metrics_report(root, tasks_rel, metrics_rel)
    except Exception as exc:
        sys.stdout.write(_render({"valid": False, "error": str(exc)}, output_format))
        return 2

    sys.stdout.write(_render(report, output_format))
    return 0


if __name__ == "__main__":
    sys.exit(main())

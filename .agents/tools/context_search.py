#!/usr/bin/env python3
"""Universal context and codebase search tool with 3-cycle Iterative Retrieval.

Invocation::

    python3 .agents/tools/context_search.py --root ROOT --query TERM \
        [--query TERM ...] [--scope auto|vault|code] [--top-k N] \
        [--min-score FLOAT] [--format human|json]

This read-only tool implements the Universal Context Discovery and Iterative
Retrieval pattern defined in ``.agents/conventions/loading-recipes.md`` using
only the Python 3 standard library:

1. **Vault / Domain Context discovery (any folder layout)**: if ``vault/`` or a
   configured ``roots.domain_context`` directory exists (whether organized as
   ``vault/repositorios/``, ``vault/20-Repos/``, ``vault/componentes/``, or flat
   Markdown), it indexes YAML frontmatter tags, headings, ``[[wikilinks]]``, UI
   component selectors, and cited source paths.
2. **Codebase verification (Code as Source of Truth)**: for every source file
   path cited inside a vault card (and across ``AGENTS.md``, package manifests,
   and code modules when no vault exists or ``--scope code`` is used), it checks
   whether the path exists on disk so stale documentation never misleads planning.
3. **Iterative Retrieval scoring & vocabulary expansion**: scores each file in
   ``[0.0, 1.0]``, flags high-relevance matches (``>= 0.7``), and extracts
   co-occurring codebase terms to refine subsequent search cycles.

Exit codes:
- ``0``: search completed successfully.
- ``2``: invalid arguments or unsafe/unreadable root path.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional


sys.dont_write_bytecode = True

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
HEADING_RE = re.compile(r"^(#{1,4})\s+(.+?)\s*$", re.MULTILINE)
CODE_PATH_RE = re.compile(
    r"`((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.(?:py|ts|js|html|scss|css|json|yaml|yml|proto|java|go|md))(?::[0-9]+(?:-[0-9]+)?)?`"
)
SELECTOR_RE = re.compile(
    r"(?:Selector(?:\s+CSS)?|selector|tag)\s*[:|=]\s*['\"`]?([a-z][a-z0-9-]{2,})['\"`]?",
    re.IGNORECASE,
)
SYMBOL_LINE_RE = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?"
    r"(?:(class|interface|def|function|enum|type)\s+([A-Za-z_][A-Za-z0-9_]*)"
    r"|@(Component|Controller|Injectable|Module|router\.(?:get|post|put|delete|patch)|app\.(?:get|post|put|delete|patch))\b([^\n]{0,60}))"
)
TOKEN_RE = re.compile(r"[a-zA-Z0-9_/-]{3,}")
STOPWORDS = frozenset({
    "the", "and", "for", "with", "from", "that", "this", "when", "para", "con",
    "del", "las", "los", "una", "uno", "por", "como", "mas", "pero", "sobre",
    "entre", "cada", "solo", "todo", "toda", "todos", "este", "esta", "estos",
    "son", "sea", "sin", "sus", "nos", "les", "que", "como", "donde", "cuando",
})
CODE_EXTENSIONS = frozenset({
    ".py", ".ts", ".js", ".html", ".json", ".yaml", ".yml", ".proto", ".java", ".go", ".md",
})
IGNORED_DIRS = frozenset({
    ".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
    ".next", ".angular", ".cache", ".worktrees", ".ralph", "coverage",
})


def _safe_root(raw_root: str) -> Path:
    path = Path(raw_root)
    if path.is_symlink():
        raise ValueError("Repository root must not be a symlink.")
    resolved = path.resolve()
    if not resolved.is_dir():
        raise ValueError("Repository root does not exist or is not a directory.")
    return resolved


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end_idx: Optional[int] = None
    for idx in range(1, min(len(lines), 120)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        return {}, text
    meta: dict[str, Any] = {}
    current_key: Optional[str] = None
    for line in lines[1:end_idx]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_key is not None:
            existing = meta.get(current_key)
            item = stripped[2:].strip().strip("\"'")
            if isinstance(existing, list):
                existing.append(item)
            else:
                meta[current_key] = [item]
            continue
        if ":" in line and not line.startswith((" ", "\t")):
            key, raw_val = line.split(":", 1)
            key = key.strip()
            val = raw_val.strip().strip("\"'")
            current_key = key
            meta[key] = val if val else []
    body = "\n".join(lines[end_idx + 1:])
    return meta, body


def _discover_vault_dirs(root: Path) -> list[Path]:
    candidates: list[Path] = []
    project_json = root / ".agents" / "project.json"
    if project_json.is_file() and not project_json.is_symlink():
        try:
            cfg = json.loads(project_json.read_text(encoding="utf-8"))
            dom = cfg.get("roots", {}).get("domain_context")
            if isinstance(dom, str) and dom.strip():
                dom_path = root / dom.strip()
                if dom_path.exists() and not dom_path.is_symlink():
                    candidates.append(dom_path if dom_path.is_dir() else dom_path.parent)
        except (OSError, UnicodeError, json.JSONDecodeError):
            pass
    default_vault = root / "vault"
    if default_vault.is_dir() and not default_vault.is_symlink():
        if default_vault not in candidates:
            candidates.append(default_vault)
    return candidates


def _verify_cited_paths(root: Path, cited: list[str]) -> tuple[list[str], list[str]]:
    verified: list[str] = []
    missing: list[str] = []
    seen: set[str] = set()
    for rel in cited:
        if rel in seen:
            continue
        seen.add(rel)
        direct = root / rel
        parent_sibling = root.parent / rel
        if (direct.exists() and not direct.is_symlink()) or (
            parent_sibling.exists() and not parent_sibling.is_symlink()
        ):
            verified.append(rel)
        else:
            missing.append(rel)
    return verified[:10], missing[:10]


def _score_document(
    rel_path: str,
    text: str,
    queries: list[str],
    root: Path,
) -> Optional[dict[str, Any]]:
    meta, body = _parse_frontmatter(text)
    lower_path = rel_path.lower()
    lower_body = body.lower()
    headings = [m.group(2).strip() for m in HEADING_RE.finditer(body)]
    lower_headings = " ".join(headings).lower()
    tags_raw = meta.get("tags", [])
    tags = tags_raw if isinstance(tags_raw, list) else ([str(tags_raw)] if tags_raw else [])
    lower_tags = " ".join(str(t).lower() for t in tags)

    matched_queries: list[str] = []
    per_query_scores: list[float] = []
    for q in queries:
        q_low = q.lower().strip()
        if not q_low:
            continue
        terms = [t for t in re.split(r"\s+", q_low) if t]
        q_score = 0.0
        if q_low in lower_path:
            q_score += 0.55
        if q_low in lower_tags:
            q_score += 0.35
        if q_low in lower_headings:
            q_score += 0.40
        if q_low in lower_body:
            occurrences = min(lower_body.count(q_low), 6)
            q_score += 0.25 + (0.05 * occurrences)
        if q_score == 0.0 and len(terms) > 1:
            term_hits = sum(
                1 for t in terms
                if t in lower_path or t in lower_headings or t in lower_tags or t in lower_body
            )
            if term_hits > 0:
                q_score += 0.45 * (term_hits / len(terms))
        if q_score > 0.0:
            matched_queries.append(q)
            per_query_scores.append(min(1.0, q_score))

    if not matched_queries:
        return None

    best_single = max(per_query_scores)
    multi_bonus = 0.12 * (len(matched_queries) - 1)
    normalized_score = round(min(1.0, best_single + multi_bonus), 3)
    wikilinks = sorted(set(WIKILINK_RE.findall(body)))[:12]
    selectors = sorted(set(SELECTOR_RE.findall(body)))[:8]
    cited_paths = CODE_PATH_RE.findall(body)
    verified_paths, missing_paths = _verify_cited_paths(root, cited_paths)
    content_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    symbols: list[str] = []
    matched_lines: list[str] = []
    q_lows = [q.lower().strip() for q in matched_queries if q.strip()]
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        if len(symbols) < 12:
            m_sym = SYMBOL_LINE_RE.match(raw_line)
            if m_sym:
                if m_sym.group(1) and m_sym.group(2):
                    symbols.append(f"{m_sym.group(1)} {m_sym.group(2)} (L{line_no})")
                elif m_sym.group(3):
                    detail = (m_sym.group(4) or "").strip()
                    symbols.append(f"@{m_sym.group(3)}{detail[:40]} (L{line_no})")
        if len(matched_lines) < 5:
            low_line = raw_line.lower()
            if any(ql in low_line for ql in q_lows):
                snippet = raw_line.strip()
                if snippet:
                    matched_lines.append(f"L{line_no}: {snippet[:110]}")

    return {
        "path": rel_path,
        "score": normalized_score,
        "high_relevance": normalized_score >= 0.7,
        "matched_queries": matched_queries,
        "title": headings[0] if headings else Path(rel_path).stem,
        "tags": tags[:10],
        "headings": headings[:8],
        "symbols": symbols,
        "matched_lines": matched_lines,
        "selectors": selectors,
        "wikilinks": wikilinks,
        "verified_code_paths": verified_paths,
        "unverified_code_paths": missing_paths,
        "content_hash_prefix": content_sha256,
    }


def _collect_candidate_files(root: Path, scope: str) -> tuple[str, list[Path]]:
    vault_dirs = _discover_vault_dirs(root)
    files: list[Path] = []

    if scope in {"auto", "vault"} and vault_dirs:
        for vdir in vault_dirs:
            for dirpath, dirnames, filenames in os.walk(vdir, followlinks=False):
                dirnames[:] = sorted(
                    d for d in dirnames
                    if d not in IGNORED_DIRS and not d.startswith(".")
                )
                for fname in sorted(filenames):
                    if not fname.endswith(".md"):
                        continue
                    fpath = Path(dirpath) / fname
                    if not fpath.is_symlink() and fpath.is_file():
                        files.append(fpath)
        if scope == "vault" or files:
            return "vault", files

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in IGNORED_DIRS and not (Path(dirpath) / d).is_symlink()
        )
        for fname in sorted(filenames):
            fpath = Path(dirpath) / fname
            if fpath.suffix.lower() not in CODE_EXTENSIONS:
                continue
            if not fpath.is_symlink() and fpath.is_file():
                files.append(fpath)
    return "code", files


def search_context(
    repository_root: Path | str,
    queries: list[str],
    *,
    scope: str = "auto",
    top_k: int = 8,
    min_score: float = 0.25,
) -> dict[str, Any]:
    """Search repository context and return ranked candidates plus refinement terms."""
    root = _safe_root(str(repository_root))
    clean_queries = [q.strip() for q in queries if q and q.strip()]
    if not clean_queries:
        raise ValueError("At least one non-empty --query term is required.")
    if scope not in {"auto", "vault", "code"}:
        raise ValueError("Scope must be one of: auto, vault, code.")

    resolved_scope, candidate_files = _collect_candidate_files(root, scope)
    results: list[dict[str, Any]] = []
    vocab_counter: dict[str, int] = {}
    lower_query_tokens = {
        t.lower() for q in clean_queries for t in TOKEN_RE.findall(q.lower())
    }

    for fpath in candidate_files:
        try:
            if fpath.stat().st_size > 2_000_000:
                continue
            text = fpath.read_text(encoding="utf-8", errors="replace")
            rel = fpath.relative_to(root).as_posix()
        except (OSError, ValueError):
            continue
        scored = _score_document(rel, text, clean_queries, root)
        if scored is None or scored["score"] < min_score:
            continue
        results.append(scored)
        if scored["score"] >= 0.5:
            for link in scored["wikilinks"]:
                token = link.strip()
                if token.lower() not in lower_query_tokens:
                    vocab_counter[token] = vocab_counter.get(token, 0) + 3
            for h in scored["headings"]:
                for tok in TOKEN_RE.findall(h.lower()):
                    if tok not in STOPWORDS and tok not in lower_query_tokens:
                        vocab_counter[tok] = vocab_counter.get(tok, 0) + 1

    results.sort(key=lambda item: (-item["score"], item["path"]))
    top_results = results[:top_k]
    high_relevance_count = sum(1 for r in top_results if r["high_relevance"])
    suggested_terms = [
        term for term, _count in sorted(
            vocab_counter.items(), key=lambda kv: (-kv[1], kv[0])
        )[:8]
    ]

    return {
        "valid": True,
        "scope_used": resolved_scope,
        "files_scanned": len(candidate_files),
        "queries": clean_queries,
        "high_relevance_count": high_relevance_count,
        "stop_condition_met": high_relevance_count >= 3,
        "suggested_refinement_terms": suggested_terms,
        "results": top_results,
    }


def _render(report: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if not report.get("valid", False):
        return f"Context search error: {report.get('error', 'Invalid invocation')}\n"
    lines = [
        f"Context search ({report['scope_used']} mode): "
        f"{len(report['results'])} top match(es) from {report['files_scanned']} files "
        f"(high-relevance >=0.7: {report['high_relevance_count']}, "
        f"stop_condition_met={report['stop_condition_met']})",
    ]
    if report["suggested_refinement_terms"]:
        lines.append(
            "Suggested cycle-2 terms: " + ", ".join(report["suggested_refinement_terms"])
        )
    for item in report["results"]:
        flag = "[HIGH]" if item["high_relevance"] else "[MED]"
        lines.append(
            f"- {flag} {item['score']:.2f} | {item['path']} — {item['title']}"
        )
        if item["selectors"]:
            lines.append(f"    selectors: {', '.join(item['selectors'])}")
        if item.get("symbols"):
            lines.append(f"    symbols: {', '.join(item['symbols'][:6])}")
        if item.get("matched_lines"):
            lines.append(f"    hit: {item['matched_lines'][0]}")
        if item["wikilinks"]:
            lines.append(f"    links: {', '.join(item['wikilinks'][:6])}")
        if item["verified_code_paths"]:
            lines.append(
                f"    verified code paths: {', '.join(item['verified_code_paths'][:4])}"
            )
    return "\n".join(lines) + "\n"


def _help() -> str:
    return (
        "Usage: context_search.py --root ROOT --query TERM [--query TERM ...] "
        "[--scope auto|vault|code] [--top-k N] [--min-score FLOAT] [--format human|json]\n"
        "Read-only universal context and codebase search with 3-cycle Iterative Retrieval.\n"
        "Exit 0=success, 2=invalid invocation or unsafe root.\n"
    )


def main(argv: Optional[list[str]] = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args in (["-h"], ["--help"]):
        sys.stdout.write(_help())
        return 0

    root: Optional[str] = None
    queries: list[str] = []
    scope = "auto"
    top_k = 8
    min_score = 0.25
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
        elif arg == "--query":
            queries.append(val)
        elif arg == "--scope" and val in {"auto", "vault", "code"}:
            scope = val
        elif arg == "--top-k" and val.isdigit() and int(val) > 0:
            top_k = int(val)
        elif arg == "--min-score":
            try:
                min_score = float(val)
            except ValueError:
                return 2
        elif arg == "--format" and val in {"human", "json"}:
            output_format = val
        else:
            sys.stdout.write(_render({"valid": False, "error": f"Unknown or invalid option: {arg}"}, output_format))
            return 2
        idx += 2

    if root is None or not queries:
        sys.stdout.write(_render({"valid": False, "error": "--root and at least one --query are required."}, output_format))
        return 2

    try:
        report = search_context(
            root, queries, scope=scope, top_k=top_k, min_score=min_score
        )
    except Exception as exc:
        sys.stdout.write(_render({"valid": False, "error": str(exc)}, output_format))
        return 2

    sys.stdout.write(_render(report, output_format))
    return 0


if __name__ == "__main__":
    sys.exit(main())

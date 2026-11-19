#!/usr/bin/env python3
"""Validate the portable Agent Skills in this repository."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional
try:
    from scripts.contracts.project import (
        ProjectConfigError,
        load_project,
        validate_project,
    )
# Direct ``python3 scripts/validate.py`` invocation.
except ModuleNotFoundError:
    from contracts.project import ProjectConfigError, load_project, validate_project
ROOT = Path(__file__).resolve().parents[2]
CATALOG_SCHEMA_VERSION = 1
SKILL_GROUPS = ("core", "utilities", "optional")
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://|#)([^)]+)\)")
MARKDOWN_DESTINATION_RE = re.compile(r"\]\(([^)\s]+)\)")
PUBLIC_DOCUMENT_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/usage-guide.md",
    "tests/scenarios.md",
)
PROVIDER_PATHS = (".claude/", ".cursor/", ".codex/")
SPEC_STATES = {"draft", "approved", "planned", "implemented", "verified"}
PROJECT_CONFIG_SCHEMA_VERSION = 2
PROJECT_CONFIG_PATH = Path(".agents/project.json")
PROJECT_SCHEMA_PATH = Path(".agents/skills/setup/assets/project.schema.json")
REVIEW_SIGNALS = (
    "Correctness",
    "Security",
    "Compatibility",
    "Maintainability",
    "Performance",
    "Accessibility",
    "Observability",
    "Cost",
    "Understandability",
)
REVIEW_EVIDENCE_CLASSES = (
    "observed evidence",
    "source-based inference",
    "unverified claim",
)
REVIEW_VERDICTS = ("approved", "changes-required", "blocked")
EVIDENCE_SCHEMA_VERSION = 1
EVIDENCE_FIELDS = (
    "schema_version",
    "change_id",
    "authoritative_sources",
    "lifecycle",
    "risk",
    "change_contract",
    "repository_scope",
    "requirement_coverage",
    "checks",
    "review",
    "known_limits",
    "remaining_risks",
    "follow_ups",
)
EVIDENCE_CHECK_KINDS = {
    "scoped", "regression", "failure-path", "recovery-rollback", "static", "other"
}
EVIDENCE_CHECK_STATUSES = {
    "passed", "failed", "skipped", "not-run", "not-applicable"
}
EVIDENCE_DEF_FIELDS = {
    "source": ("id", "reference"),
    "lifecycle": ("status", "transition", "evidence_references"),
    "risk": ("level", "rationale"),
    "change_contract": (
        "intent", "confirmed_why", "scope", "expected_evidence", "agent_roles",
        "review_focus",
    ),
    "repository_scope": (
        "repository_id", "base", "head", "committed_range", "uncommitted_entries",
        "snapshot_sha256",
    ),
    "uncommitted_entry": ("path", "state", "sha256"),
    "coverage": (
        "requirement_id", "repository_ids", "status", "implementation_references",
        "evidence_references",
    ),
    "check": (
        "id", "requirement_ids", "repository_ids", "kind", "required", "applicability",
        "not_applicable_reason", "status", "observed_result", "evidence_class",
        "output_reference",
    ),
    "review": (
        "reviewer_role", "reviewer_id", "implementers", "prior_participation",
        "fresh_context", "independence", "independence_basis", "verdict", "reference",
    ),
}
EVIDENCE_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EVIDENCE_REVISION_RE = re.compile(r"^[0-9a-f]{7,64}$")
COMPLIANCE_EVENT_FIELDS = (
    "schema_version", "event_id", "sequence", "timestamp", "change_id", "actor",
    "action", "previous_lifecycle", "new_lifecycle",
    "authoritative_source_references", "evidence_references", "approvals",
    "repositories",
)
COMPLIANCE_EVENT_DEF_FIELDS = {
    "actor": ("actor_id", "role"),
    "approval": ("actor_id", "role", "reference"),
    "repository": ("repository_id", "revision"),
}
COMPLIANCE_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
COMMON_CREDENTIAL_RE = re.compile(
    r"(?:\bghp_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b|"
    r"\bsk-[A-Za-z0-9]{20,}\b)"
)
SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?:api[-_ ]?key|credential|password|secret|token)\s*[:=]", re.IGNORECASE
)
PERSONAL_DATA_RE = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
SENSITIVE_QUERY_KEYS = {
    "token",
    "accesstoken",
    "authtoken",
    "refreshtoken",
    "idtoken",
    "apikey",
    "secret",
    "clientsecret",
    "password",
    "passwd",
    "credential",
    "credentials",
}
SENSITIVE_QUERY_SUFFIXES = (
    "token",
    "apikey",
    "secret",
    "password",
    "passwd",
    "credential",
    "credentials",
)


class DuplicateJSONObjectKey(ValueError):
    pass


def _markdown_anchors(text: str) -> set[str]:
    anchors: set[str] = set()
    duplicates: dict[str, int] = {}
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if not match:
            continue
        heading = re.sub(r"\s+#+\s*$", "", match.group(1)).strip().lower()
        heading = re.sub(r"<[^>]+>", "", heading)
        heading = re.sub(r"[^\w\- ]", "", heading)
        base = re.sub(r"\s", "-", heading)
        occurrence = duplicates.get(base, 0)
        anchor = base if occurrence == 0 else f"{base}-{occurrence}"
        duplicates[base] = occurrence + 1
        anchors.add(anchor)
    return anchors


def validate_agents_bootstrap(root: Path) -> list[str]:
    """Validate the compact installed entrypoint and its conditional path contracts."""
    errors: list[str] = []
    agents_path = root / "AGENTS.md"
    try:
        text = agents_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"Cannot read AGENTS.md bootstrap {agents_path}: {exc}"]

    required_pointers = (
        ".agents/kit-catalog.json",
        ".agents/skills/<name>/SKILL.md",
        ".agents/project.json",
        ".agents/project.md",
        ".agents/skills/setup/assets/project.schema.json",
        ".agents/skills/setup/references/project-config.md",
        ".agents/agentic-sdlc-kit.json",
        ".agents/modules/<name>/MODULE.md",
        "scripts/validate.py",
        ".agents/modules/enforcement/check.py",
        "roots.specs",
        "roots.work",
        "docs/usage-guide.md",
    )
    for pointer in required_pointers:
        if pointer not in text:
            errors.append(
                f"{agents_path}: missing canonical bootstrap pointer: {pointer}"
            )

    if len(text.splitlines()) > 260:
        errors.append(f"{agents_path}: bootstrap exceeds 260 lines")
    forbidden_readme = root / ".agents" / "README.md"
    if forbidden_readme.exists() or forbidden_readme.is_symlink():
        errors.append(
            f"{forbidden_readme}: forbidden context layer; use AGENTS.md navigation"
        )

    try:
        catalog = json.loads(
            (root / ".agents" / "kit-catalog.json").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError):
        catalog = None
    profiles = catalog.get("profiles") if isinstance(catalog, dict) else None
    if isinstance(profiles, dict):
        blocks = [block.lower() for block in re.split(r"\n\s*\n", text)]
        for profile_name in ("default", "full"):
            profile = profiles.get(profile_name)
            if not isinstance(profile, dict):
                continue
            skills = profile.get("skills")
            modules = profile.get("modules")
            if not isinstance(skills, list) or not isinstance(modules, list):
                continue
            members = skills + modules
            if not members or not all(isinstance(item, str) for item in members):
                continue
            if any(
                all(
                    re.search(
                        rf"(?<![a-z0-9-]){re.escape(member.lower())}(?![a-z0-9-])",
                        block,
                    )
                    for member in members
                )
                for block in blocks
            ):
                errors.append(
                    f"{agents_path}: complete profile membership copied into one "
                    f"paragraph or block: {profile_name}"
                )
    if any(field in text for field in ("schema_version", '"tracker"', '"contribution"')):
        errors.append(
            f"{agents_path}: bootstrap must not copy project schema fields")

    required_source_paths = (
        (root / ".agents" / "kit-catalog.json", "file"),
        (root / ".agents" / "skills", "directory"),
        (root / ".agents" / "skills" / "setup" /
         "references" / "project-config.md", "file"),
        (root / ".agents" / "modules", "directory"),
        (root / "scripts" / "validate.py", "file"),
        (root / ".agents" / "modules" / "enforcement" / "check.py", "file"),
        (root / "docs" / "usage-guide.md", "file"),
    )
    for path, kind in required_source_paths:
        present = path.is_file() if kind == "file" else path.is_dir()
        if not present:
            errors.append(
                f"{agents_path}: canonical bootstrap {kind} is missing: {path}")

    consumer_contracts = {
        "write-spec": ("roots.specs", "specs/", "<specs-root>/"),
        "plan": ("roots.work", ".work/", "<work-root>/"),
        "decompose-tasks": ("roots.work", ".work/", "<work-root>/"),
        "implement": ("roots.work", ".work/", "<work-root>/"),
        "review": ("roots.work", ".work/", "<work-root>/"),
    }
    shared_tokens = (
        ".agents/project.json",
        ".agents/project.md",
        ".agents/skills/setup/assets/project.schema.json",
        ".agents/skills/setup/references/project-config.md",
        "invalid",
        "unsupported",
        "stop",
    )
    for name, specific_tokens in consumer_contracts.items():
        skill_path = root / ".agents" / "skills" / name / "SKILL.md"
        try:
            skill_text = skill_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(
                f"Cannot read configured-root consumer {skill_path}: {exc}")
            continue
        lowered_skill_text = skill_text.lower()
        missing = [
            token for token in shared_tokens + specific_tokens
            if token.lower() not in lowered_skill_text
        ]
        if missing:
            errors.append(
                f"{skill_path}: configured-root consumer contract missing: "
                + ", ".join(missing)
            )
    return errors


def validate_markdown_links(root: Path, paths: list[Path]) -> list[str]:
    errors: list[str] = []
    root_absolute = root.resolve()
    text_cache: dict[Path, str] = {}
    for path in paths:
        try:
            text_cache[path] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"Cannot read documentation {path}: {exc}")

    for path, text in text_cache.items():
        for match in MARKDOWN_DESTINATION_RE.finditer(text):
            destination = match.group(1)
            if (
                destination.startswith(("http://", "https://", "mailto:"))
                or any(token in destination for token in ("<", ">"))
            ):
                continue
            target_text, separator, fragment = destination.partition("#")
            target = path if not target_text else path.parent / target_text
            try:
                target_absolute = target.resolve()
                target_absolute.relative_to(root_absolute)
            except (OSError, ValueError):
                errors.append(
                    f"{path}: documentation link leaves repository: {destination}"
                )
                continue
            if not target_absolute.exists():
                errors.append(
                    f"{path}: missing documentation link target: {destination}"
                )
                continue
            if separator and fragment:
                if not target_absolute.is_file() or target_absolute.suffix.lower() != ".md":
                    errors.append(
                        f"{path}: documentation fragment target is not Markdown: {destination}"
                    )
                    continue
                target_path = target_absolute
                try:
                    target_text_content = target_path.read_text(
                        encoding="utf-8")
                except (OSError, UnicodeError) as exc:
                    errors.append(
                        f"Cannot read documentation fragment target {target_path}: {exc}"
                    )
                    continue
                if fragment not in _markdown_anchors(target_text_content):
                    errors.append(
                        f"{path}: missing documentation heading for link: {destination}"
                    )
    return errors


def _contract_table(
    text: str,
    name: str,
    headers: tuple[str, ...],
    path: Path,
    errors: list[str],
) -> Optional[list[list[str]]]:
    start_marker = f"<!-- contract:{name}:start -->"
    end_marker = f"<!-- contract:{name}:end -->"
    if text.count(start_marker) != 1 or text.count(end_marker) != 1:
        errors.append(
            f"{path}: contract table markers must occur once: {name}")
        return None
    start = text.index(start_marker) + len(start_marker)
    end = text.index(end_marker)
    if end <= start:
        errors.append(f"{path}: contract table markers are reversed: {name}")
        return None
    lines = [line.strip()
             for line in text[start:end].splitlines() if line.strip()]
    if len(lines) < 2 or any(
        not line.startswith("|") or not line.endswith("|") for line in lines
    ):
        errors.append(f"{path}: malformed contract table: {name}")
        return None
    rows = [[cell.strip() for cell in line.strip("|").split("|")]
            for line in lines]
    if tuple(rows[0]) != headers or len(rows[1]) != len(headers) or not all(
        re.fullmatch(r":?-{3,}:?", cell) for cell in rows[1]
    ):
        errors.append(f"{path}: invalid contract table header: {name}")
        return None
    data = rows[2:]
    if any(len(row) != len(headers) for row in data):
        errors.append(f"{path}: invalid contract table row width: {name}")
        return None
    return data


def _render_name_list(values: list[str]) -> str:
    return "none" if not values else ", ".join(f"`{value}`" for value in values)


def _expect_contract_table(
    text: str,
    name: str,
    headers: tuple[str, ...],
    expected: list[list[str]],
    path: Path,
    label: str,
    errors: list[str],
) -> None:
    actual = _contract_table(text, name, headers, path, errors)
    if actual is not None and actual != expected:
        errors.append(f"{path}: {label} mismatch")


def _markdown_heading_section(
    text: str, heading: str, path: Path, errors: list[str]
) -> Optional[str]:
    lines = text.splitlines()
    positions = [index for index, line in enumerate(lines) if line == heading]
    if len(positions) != 1:
        errors.append(f"{path}: heading must occur once: {heading}")
        return None
    depth = len(heading) - len(heading.lstrip("#"))
    start = positions[0] + 1
    end = len(lines)
    in_fence = False
    for index in range(start, len(lines)):
        if lines[index].startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        match = None if in_fence else re.match(r"^(#{1,6})\s+", lines[index])
        if match and len(match.group(1)) <= depth:
            end = index
            break
    return "\n".join(lines[start:end])


def _expect_section_commands(
    text: str,
    heading: str,
    expected: list[str],
    path: Path,
    label: str,
    errors: list[str],
) -> None:
    section = _markdown_heading_section(text, heading, path, errors)
    if section is None:
        return
    commands = [
        line.strip()
        for line in section.splitlines()
        if line.strip().startswith("python3 ")
    ]
    if commands != expected:
        errors.append(f"{path}: {label} mismatch")


def validate_readme_skill_table(
    text: str, catalog: dict[str, Any], path: Path
) -> list[str]:
    """Validate the README workflow skill table against the catalog."""
    errors: list[str] = []
    expected = [
        name for group in SKILL_GROUPS for name in catalog.get("skill_groups", {}).get(group, [])
    ]
    rows = {
        match.group(1): match.group(0)
        for match in re.finditer(r"^\| `([^`]+)`[^\n]*$", text, re.MULTILINE)
    }
    for name in expected:
        row = rows.get(name)
        if row is None or row.count("|") != 4 or "| BROKEN |" in row:
            errors.append(f"{path}: workflow skill table row mismatch: {name}")
    return errors


def validate_documented_counts(
    guide: str, catalog: dict[str, Any], path: Path
) -> list[str]:
    groups = catalog.get("skill_groups", {})
    skills = [name for group in SKILL_GROUPS for name in groups.get(group, [])]
    profiles = catalog.get("profiles", {})
    default_count = len(profiles.get("default", {}).get("skills", []))
    full_count = len(profiles.get("full", {}).get("skills", []))
    modules_count = len(catalog.get("modules", []))
    words = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four",
             5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine",
             10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen",
             14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen",
             18: "eighteen", 19: "nineteen", 20: "twenty"}
    expected = (
        (f"{full_count} available skills",
         f"{words.get(full_count, full_count)} available skills"),
        (f"{modules_count} modules",
         f"{words.get(modules_count, modules_count)} modules"),
        (f"default profile installs {default_count} skills",
         f"default profile installs {words.get(default_count, default_count)} skills"),
        (f"full installs all {full_count} skills",
         f"full installs all {words.get(full_count, full_count)} skills"),
    )
    compact = " ".join(guide.split())
    if not all(any(value in compact for value in alternatives) for alternatives in expected):
        return [f"{path}: documented catalog counts mismatch"]
    return []


def validate_public_documentation(root: Path, catalog: dict[str, Any]) -> list[str]:
    """Parse canonical public tables and compare them with catalog/CLI contracts."""
    errors: list[str] = []
    documents: dict[str, str] = {}
    paths = [root / relative for relative in PUBLIC_DOCUMENT_PATHS]
    for relative, path in zip(PUBLIC_DOCUMENT_PATHS, paths):
        if not path.is_file():
            errors.append(f"Missing public documentation: {path}")
            continue
        try:
            documents[relative] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"Cannot read public documentation {path}: {exc}")
    errors.extend(validate_markdown_links(
        root, [path for path in paths if path.is_file()]))
    if len(documents) != len(PUBLIC_DOCUMENT_PATHS):
        return errors

    groups = catalog.get("skill_groups")
    modules = catalog.get("modules")
    profiles = catalog.get("profiles")
    if not isinstance(groups, dict) or not isinstance(modules, list) or not isinstance(profiles, dict):
        return errors
    if not all(isinstance(groups.get(name), list) for name in SKILL_GROUPS):
        return errors
    if not all(
        isinstance(item, dict)
        and isinstance(item.get("name"), str)
        and isinstance(item.get("depends_on"), list)
        for item in modules
    ):
        return errors
    if not all(
        isinstance(profiles.get(name), dict)
        and isinstance(profiles[name].get("skills"), list)
        and isinstance(profiles[name].get("modules"), list)
        for name in ("default", "full")
    ):
        return errors

    guide_path = root / "docs" / "usage-guide.md"
    scenarios_path = root / "tests" / "scenarios.md"
    guide = documents["docs/usage-guide.md"]
    scenarios = documents["tests/scenarios.md"]
    group_rows = [
        [name, _render_name_list(groups[name])] for name in SKILL_GROUPS
    ] + [["modules", _render_name_list([item["name"] for item in modules])]]
    _expect_contract_table(
        guide, "catalog-groups", ("Group", "Members"), group_rows,
        guide_path, "catalog group table", errors,
    )
    profile_rows = [
        [
            name,
            _render_name_list(profiles[name]["skills"]),
            _render_name_list(profiles[name]["modules"]),
        ]
        for name in ("default", "full")
    ]
    _expect_contract_table(
        guide, "profiles", ("Profile", "Skills", "Modules"), profile_rows,
        guide_path, "profile table", errors,
    )
    dependency_rows = [
        [item["name"], _render_name_list(item["depends_on"])] for item in modules
    ]
    _expect_contract_table(
        guide, "module-dependencies", ("Module", "Depends on"),
        dependency_rows, guide_path, "module dependency table", errors,
    )

    target_safety_rows = [
        ["target", "existing local Git repository root"],
        ["symlinks", "target and every inspected ancestor must not be a symlink"],
        ["macOS", "use canonical `/private/...` for locations exposed through `/var`, `/tmp`, or another symlinked system path"],
    ]
    _expect_contract_table(
        guide, "installer-target-safety", ("Rule", "Requirement"),
        target_safety_rows, guide_path, "installer target-safety table", errors,
    )
    ownership_rows = [
        ["copy", "selected source is written", "managed and hashed"],
        ["update", "intact managed selection is updated", "managed and hashed"],
        ["adopt", "identical selected content is not rewritten", "managed and hashed"],
        ["unchanged", "intact selected content is not rewritten",
            "existing managed hash retained"],
        ["keep", "no write; conflicting component remains project-owned", "unmanifested"],
        ["manual-merge", "no write; existing AGENTS.md is preserved",
            "AGENTS.md excluded"],
    ]
    _expect_contract_table(
        guide, "installer-ownership",
        ("Outcome", "Filesystem", "Ownership manifest"), ownership_rows,
        guide_path, "installer ownership table", errors,
    )
    installer_exit_rows = [
        ["`0`", "success, already current, or dry run"],
        ["`1`", "conflict, abort, handled installation failure, or manual recovery required"],
        ["`2`", "invalid arguments or preflight input"],
        ["`3`", "applied; AGENTS.md semantic merge required"],
        ["`130`", "keyboard interrupt or cancellation"],
    ]
    _expect_contract_table(
        guide, "installer-exit-codes", ("Code", "Meaning"),
        installer_exit_rows, guide_path, "installer exit-code table", errors,
    )
    enforcement_exit_rows = [
        ["`0`", "valid"],
        ["`1`", "consistency failures"],
        ["`2`", "invalid invocation; malformed/unrecognized configuration; invalid/uninspectable/symlink root; safe-inspection failure"],
    ]
    guide_enforcement_exits = _contract_table(
        guide, "enforcement-exit-codes", ("Code", "Meaning"),
        guide_path, errors,
    )
    if guide_enforcement_exits is not None and guide_enforcement_exits != enforcement_exit_rows:
        errors.append(f"{guide_path}: enforcement exit-code table mismatch")
    module_path = root / ".agents" / "modules" / "enforcement" / "MODULE.md"
    try:
        module_text = module_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(
            f"Cannot read enforcement module documentation {module_path}: {exc}")
    else:
        module_enforcement_exits = _contract_table(
            module_text, "enforcement-exit-codes", ("Code", "Meaning"),
            module_path, errors,
        )
        if module_enforcement_exits is not None and (
            module_enforcement_exits != enforcement_exit_rows
            or module_enforcement_exits != guide_enforcement_exits
        ):
            errors.append(
                f"{module_path}: enforcement module exit-code table mismatch"
            )
    limitation_rows = [
        ["cryptographic chain or signature", "not provided"],
        ["authenticated identity", "not provided"],
        ["legal certification", "not provided"],
        ["compliance guarantee", "not provided"],
        ["external publication", "not provided"],
    ]
    _expect_contract_table(
        guide, "compliance-limitations", ("Capability", "Status"),
        limitation_rows, guide_path, "compliance limitation table", errors,
    )
    baseline_rows = [
        ["arms", "frozen comparable tasks and repository revision; no-kit, pinned prior/base kit, and pinned v1 kit"],
        ["controls", "same model and version, prompts/settings, context, tools, permissions, environment, and time/budget limits"],
        ["sessions", "fresh session for every task and arm; randomized order where practical; no carried discoveries"],
        ["rubric", "acceptance oracle, required checks, pass signals, and regression thresholds declared before runs"],
        ["scoring", "same rubric; blinded and independent where practical; scorer involvement, disagreements, and deviations disclosed"],
        ["measures", "success, false completion, scope creep, human corrections/time, escaped defects, skill/module activation and non-activation, cost, elapsed time, and tool steps"],
        ["reporting", "repeated independent samples; per-run results, raw counts, denominators, and uncertainty; missing measurements explicit"],
        ["thresholds", "project-set for the frozen tasks and risks, not universal numbers"],
    ]
    _expect_contract_table(
        guide, "baseline-protocol", ("Element", "Requirement"), baseline_rows,
        guide_path, "baseline protocol table", errors,
    )
    claim_rows = [
        ["causal effect", "prohibited without an appropriately powered design and supporting evidence"],
        ["universal speed or performance",
            "prohibited without an appropriately powered design and supporting evidence"],
    ]
    actual_claims = _contract_table(
        guide, "baseline-claim-limitations", ("Claim", "Policy"),
        guide_path, errors,
    )
    if actual_claims is not None and (
        actual_claims != claim_rows
        or any(not row[1].lower().startswith("prohibited") for row in actual_claims)
    ):
        errors.append(
            f"{guide_path}: baseline claim-limitation polarity mismatch")

    _expect_section_commands(
        guide,
        "### Selection and dry runs",
        [
            "python3 scripts/install.py /path/to/repository --profile default --dry-run",
            "python3 scripts/install.py /path/to/repository --profile default",
            "python3 scripts/install.py /path/to/repository --with domain-model",
            "python3 scripts/install.py /path/to/repository --with evidence --with enforcement",
            "python3 scripts/install.py /path/to/repository --with multi-repo,compliance",
            "python3 scripts/install.py /path/to/repository --profile full",
        ],
        guide_path,
        "installer command section",
        errors,
    )
    _expect_section_commands(
        guide,
        "## 15. Validation commands",
        [
            "python3 scripts/validate.py",
            "python3 .agents/modules/enforcement/check.py --root . --format human",
            "python3 .agents/modules/enforcement/check.py --root . --format json",
        ],
        guide_path,
        "validation command section",
        errors,
    )

    scenario_numbers = [
        int(value) for value in re.findall(r"^## ([0-9]+)\.", scenarios, re.MULTILINE)
    ]
    if scenario_numbers != list(range(1, len(scenario_numbers) + 1)):
        errors.append(
            f"{scenarios_path}: scenario headings must be sequential from 1")
    guide_numbers = [
        int(value) for value in re.findall(r"^## ([0-9]+)\.", guide, re.MULTILINE)
    ]
    if guide_numbers != list(range(1, len(guide_numbers) + 1)):
        errors.append(
            f"{guide_path}: numbered headings must be sequential from 1")
    return errors


def validate_provider_neutrality(path: Path) -> list[str]:
    errors: list[str] = []
    files = [path] if path.is_file() else sorted(
        item for item in path.rglob("*") if item.is_file())
    for file_path in files:
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            errors.append(
                f"{file_path}: cannot inspect provider neutrality: {exc}")
            continue
        for provider_path in PROVIDER_PATHS:
            if provider_path in text:
                errors.append(
                    f"{file_path}: provider-specific path in portable content: {provider_path}"
                )
    return errors


def validate_document_links(root, paths):
    """Validate a selected public-document link set."""
    return validate_markdown_links(root, paths)

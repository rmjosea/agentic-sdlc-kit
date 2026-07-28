#!/usr/bin/env python3
"""Validate the portable Agent Skills in this repository."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / ".agents" / "skills"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://|#)([^)]+)\)")
EXPECTED = {
    "shape-idea",
    "write-spec",
    "plan",
    "decompose-tasks",
    "implement",
    "review",
    "create-skill",
}
PROVIDER_PATHS = (".claude/", ".cursor/", ".codex/")
SPEC_STATES = {"draft", "approved", "planned", "implemented", "verified"}


def parse_frontmatter(text: str, path: Path) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError(f"{path}: missing opening YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError(f"{path}: missing closing YAML frontmatter") from exc

    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"{path}: invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata


def validate_skill(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        return [f"{skill_dir}: missing SKILL.md"]

    text = skill_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    try:
        metadata = parse_frontmatter(text, skill_file)
    except ValueError as exc:
        return [str(exc)]

    name = metadata.get("name", "")
    description = metadata.get("description", "")
    if name != skill_dir.name:
        errors.append(f"{skill_file}: name must match directory ({skill_dir.name})")
    if not NAME_RE.fullmatch(name):
        errors.append(f"{skill_file}: invalid skill name {name!r}")
    if not description:
        errors.append(f"{skill_file}: description is required")
    elif "Use when" not in description:
        errors.append(f"{skill_file}: description must state 'Use when'")
    if len(lines) > 500:
        errors.append(f"{skill_file}: exceeds 500-line hard limit")
    elif len(lines) > 200:
        errors.append(f"{skill_file}: exceeds 200-line project target")

    for relative in LINK_RE.findall(text):
        target = (skill_dir / relative).resolve()
        try:
            target.relative_to(skill_dir.resolve())
        except ValueError:
            errors.append(f"{skill_file}: reference leaves skill root: {relative}")
            continue
        if not target.exists():
            errors.append(f"{skill_file}: missing local reference: {relative}")

    for provider_path in PROVIDER_PATHS:
        if provider_path in text:
            errors.append(
                f"{skill_file}: provider-specific path in portable instructions: "
                f"{provider_path}"
            )
    return errors


def main() -> int:
    errors: list[str] = []
    if not (ROOT / "AGENTS.md").is_file():
        errors.append("Missing AGENTS.md")

    found = {path.name for path in SKILLS_ROOT.iterdir() if path.is_dir()}
    if found != EXPECTED:
        errors.append(
            f"Skill set mismatch: expected {sorted(EXPECTED)}, found {sorted(found)}"
        )

    for skill_dir in sorted(SKILLS_ROOT.iterdir()):
        if skill_dir.is_dir():
            errors.extend(validate_skill(skill_dir))

    spec_template = (
        SKILLS_ROOT / "write-spec" / "assets" / "spec.template.md"
    ).read_text(encoding="utf-8")
    for required in ("id:", "title:", "status: draft", "depends_on: []"):
        if required not in spec_template:
            errors.append(f"Spec template missing metadata field: {required}")
    index_template = (
        SKILLS_ROOT / "write-spec" / "assets" / "spec-index.template.md"
    ).read_text(encoding="utf-8")
    for state in sorted(SPEC_STATES):
        if f"`{state}`" not in index_template:
            errors.append(f"Spec index missing lifecycle state: {state}")

    plan_template = (
        SKILLS_ROOT / "plan" / "assets" / "plan.template.md"
    ).read_text(encoding="utf-8")
    for required in ("id: PLAN-", "specs:", "status: draft", "risk: low"):
        if required not in plan_template:
            errors.append(f"Plan template missing field: {required}")

    task_template = (
        SKILLS_ROOT / "decompose-tasks" / "assets" / "tasks.template.md"
    ).read_text(encoding="utf-8")
    for required in (
        "Plan:",
        "Requirements:",
        "Type:",
        "Risk:",
        "State:",
        "Depends on:",
        "Parallel:",
        "Conflicts with:",
        "Completion evidence:",
        "Validation:",
    ):
        if required not in task_template:
            errors.append(f"Task template missing field: {required}")

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Validation passed: {len(found)} skills")
    return 0


if __name__ == "__main__":
    sys.exit(main())

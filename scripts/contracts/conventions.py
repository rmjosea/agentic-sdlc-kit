"""Validate SOA-aligned conventions, Shape A/B/C frontmatter, templates, and rubrics."""

from __future__ import annotations

import re
from pathlib import Path

TYPES_A = {
    "user-persona",
    "user-journey",
    "user-story",
    "spec",
    "adr",
    "decision",
    "business-context",
    "plan",
    "tasks",
    "estimate",
}
STATUSES_A = {
    "draft",
    "review",
    "needs-work",
    "approved",
    "implemented",
    "archived",
    "superseded",
    "legacy-pending-review",
}
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
EXPECTED_CONVENTIONS = {
    "change-lanes.md",
    "composition.md",
    "context-cleanup.md",
    "conventions.md",
    "frontmatter-schema.md",
    "how-to-invoke-skills.md",
    "loading-recipes.md",
    "naming-and-language.md",
    "output-splitting.md",
    "progressive-disclosure.md",
    "runtimes.md",
    "security.md",
    "skill-schema.md",
}
EXPECTED_JUDGE_RUBRICS = {
    "rubric-adr.md",
    "rubric-plan.md",
    "rubric-spec.md",
    "rubric-tasks.md",
    "rubric-user-journey.md",
    "rubric-user-story.md",
}
EXPECTED_JUEZ_RUBRICS = {
    "frontend.md",
    "java.md",
    "node-ts.md",
    "python.md",
}


def extract_frontmatter(text: str, path: Path) -> dict[str, str]:
    """Extract top-level YAML frontmatter key-value pairs."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path}: missing opening YAML frontmatter")
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        raise ValueError(f"{path}: missing closing YAML frontmatter")

    metadata: dict[str, str] = {}
    current_key: str | None = None
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0].isspace() or line.lstrip().startswith("- "):
            if current_key is not None and not metadata[current_key]:
                metadata[current_key] = line.strip()
            continue
        if ":" not in line:
            raise ValueError(f"{path}: invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        clean_key = key.strip()
        clean_val = value.strip().strip('"').strip("'")
        if clean_val in ("|", ">"):
            clean_val = ""
        metadata[clean_key] = clean_val
        current_key = clean_key
    return metadata


def validate_shape_c(path: Path) -> list[str]:
    """Validate Shape C infrastructure/rubric frontmatter (title + updated) and related links."""
    try:
        text = path.read_text(encoding="utf-8")
        fm = extract_frontmatter(text, path)
    except (OSError, UnicodeError, ValueError) as exc:
        return [str(exc)]
    errors: list[str] = []
    for required in ("title", "updated"):
        if not fm.get(required):
            errors.append(f"{path}: Shape C missing required field '{required}'")
    updated = fm.get("updated", "")
    if updated and not DATE_RE.fullmatch(updated):
        errors.append(f"{path}: Shape C 'updated' must be YYYY-MM-DD (got {updated!r})")

    lines = text.splitlines()
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), 0)
    in_related = False
    for line in lines[1:end]:
        if line.startswith("related:"):
            in_related = True
            continue
        if in_related:
            if line.startswith("  - ") or line.startswith("- "):
                rel_target = line.split("- ", 1)[1].strip().strip('"').strip("'")
                if rel_target and not (path.parent / rel_target).exists():
                    errors.append(
                        f"{path}: Shape C 'related' target does not exist: {rel_target}"
                    )
            elif not line[0].isspace():
                in_related = False
    return errors


def validate_shape_a(path: Path, *, allow_template_date: bool = False) -> list[str]:
    """Validate Shape A project artifact or template frontmatter (type, status, updated)."""
    try:
        text = path.read_text(encoding="utf-8")
        fm = extract_frontmatter(text, path)
    except (OSError, UnicodeError, ValueError) as exc:
        return [str(exc)]
    errors: list[str] = []
    for required in ("type", "status", "updated"):
        if not fm.get(required):
            errors.append(f"{path}: Shape A missing required field '{required}'")
    artifact_type = fm.get("type", "")
    status = fm.get("status", "")
    updated = fm.get("updated", "")
    if artifact_type and artifact_type not in TYPES_A:
        errors.append(f"{path}: Shape A invalid type {artifact_type!r}")
    if status and status not in STATUSES_A:
        errors.append(f"{path}: Shape A invalid status {status!r}")
    if status != "legacy-pending-review" and updated:
        valid_date = DATE_RE.fullmatch(updated) is not None or (
            allow_template_date and updated == "YYYY-MM-DD"
        )
        if not valid_date:
            errors.append(
                f"{path}: Shape A 'updated' must be YYYY-MM-DD (got {updated!r})"
            )
    return errors


def validate_conventions_and_rubrics(root: Path) -> list[str]:
    """Validate .agents/conventions/, judge-spec rubrics, implement juez rubrics, and Shape A templates."""
    errors: list[str] = []
    conventions_dir = root / ".agents" / "conventions"
    if not conventions_dir.is_dir():
        return [f"Missing conventions directory: {conventions_dir}"]

    found_conventions = {path.name for path in conventions_dir.glob("*.md")}
    for missing in sorted(EXPECTED_CONVENTIONS - found_conventions):
        errors.append(f"{conventions_dir}: missing convention file: {missing}")
    for path in sorted(conventions_dir.glob("*.md")):
        errors.extend(validate_shape_c(path))

    judge_dir = root / ".agents" / "skills" / "judge-spec"
    if judge_dir.is_dir():
        found_rubrics = {path.name for path in judge_dir.glob("rubric-*.md")}
        for missing in sorted(EXPECTED_JUDGE_RUBRICS - found_rubrics):
            errors.append(f"{judge_dir}: missing artifact rubric: {missing}")
        for path in sorted(judge_dir.glob("rubric-*.md")):
            errors.extend(validate_shape_c(path))

    juez_dir = root / ".agents" / "skills" / "implement" / "rubrics"
    if juez_dir.is_dir():
        found_juez = {path.name for path in juez_dir.glob("*.md")}
        for missing in sorted(EXPECTED_JUEZ_RUBRICS - found_juez):
            errors.append(f"{juez_dir}: missing stack juez rubric: {missing}")
        for path in sorted(juez_dir.glob("*.md")):
            errors.extend(validate_shape_c(path))

    shape_a_templates = (
        root / ".agents" / "skills" / "save-output" / "assets" / "spec.template.md",
        root / ".agents" / "skills" / "save-output" / "assets" / "user-journey.template.md",
        root / ".agents" / "skills" / "save-output" / "assets" / "user-story.template.md",
        root / ".agents" / "skills" / "save-output" / "assets" / "adr.template.md",
        root / ".agents" / "skills" / "plan-feature" / "assets" / "plan.template.md",
        root / ".agents" / "skills" / "breakdown-tasks" / "assets" / "tasks.template.md",
    )
    for template_path in shape_a_templates:
        if not template_path.is_file():
            errors.append(f"Missing required Shape A template: {template_path}")
        else:
            errors.extend(validate_shape_a(template_path, allow_template_date=True))

    for business_dir_name in (
        "personas",
        "journeys",
        "features",
        "business-context",
        "architecture",
        "estimaciones",
    ):
        business_dir = root / business_dir_name
        if not business_dir.is_dir():
            continue
        for md_path in sorted(business_dir.rglob("*.md")):
            if md_path.name == "README.md":
                continue
            errors.extend(validate_shape_a(md_path))

    try:
        from scripts.validation.documentation import validate_markdown_links
    except ModuleNotFoundError:
        from validation.documentation import validate_markdown_links

    shape_c_docs = (
        sorted(conventions_dir.glob("*.md"))
        + sorted(judge_dir.glob("rubric-*.md"))
        + sorted(juez_dir.glob("*.md"))
    )
    calibration = (
        root / ".agents" / "skills" / "estimate-effort" / "references" / "calibration.md"
    )
    if calibration.is_file():
        errors.extend(validate_shape_c(calibration))
        shape_c_docs.append(calibration)
    errors.extend(validate_markdown_links(root, shape_c_docs))

    return errors

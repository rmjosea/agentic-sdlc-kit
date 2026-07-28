#!/usr/bin/env python3
"""Install Agentic SDLC Kit into an existing repository."""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path


KIT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_SKILLS = KIT_ROOT / ".agents" / "skills"
SOURCE_AGENTS = KIT_ROOT / "AGENTS.md"


def same_tree(left: Path, right: Path) -> bool:
    comparison = filecmp.dircmp(left, right)
    if comparison.left_only or comparison.right_only or comparison.funny_files:
        return False
    if comparison.diff_files:
        return False
    return all(
        same_tree(left / name, right / name)
        for name in comparison.common_dirs
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install the portable SDLC skills and engineering contract."
    )
    parser.add_argument(
        "target",
        type=Path,
        help="Path to an existing repository root.",
    )
    parser.add_argument(
        "--force-skills",
        action="store_true",
        help="Replace conflicting skill directories after explicit review.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the installation result without writing files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = args.target.expanduser().resolve()
    if not target.is_dir():
        print(f"Error: target is not an existing directory: {target}")
        return 2
    if not (target / ".git").exists():
        print(f"Error: target does not appear to be a repository root: {target}")
        return 2

    target_skills = target / ".agents" / "skills"
    actions: list[tuple[str, Path, Path]] = []
    conflicts: list[Path] = []

    for source in sorted(SOURCE_SKILLS.iterdir()):
        if not source.is_dir():
            continue
        destination = target_skills / source.name
        if not destination.exists():
            actions.append(("copy", source, destination))
        elif same_tree(source, destination):
            actions.append(("unchanged", source, destination))
        elif args.force_skills:
            actions.append(("replace", source, destination))
        else:
            conflicts.append(destination)

    if conflicts:
        print("Installation stopped. Conflicting skills already exist:")
        for path in conflicts:
            print(f"- {path}")
        print("Review them first, then rerun with --force-skills if replacement is intended.")
        return 1

    target_agents = target / "AGENTS.md"
    agents_action = "copy"
    if target_agents.exists():
        agents_action = (
            "unchanged"
            if target_agents.read_bytes() == SOURCE_AGENTS.read_bytes()
            else "manual-merge"
        )

    print(f"Target: {target}")
    for action, _, destination in actions:
        print(f"- {action}: {destination.relative_to(target)}")
    print(f"- {agents_action}: AGENTS.md")

    if args.dry_run:
        print("Dry run complete; no files changed.")
        return 0

    for action, source, destination in actions:
        if action == "unchanged":
            continue
        if action == "replace":
            shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination)

    if agents_action == "copy":
        shutil.copy2(SOURCE_AGENTS, target_agents)

    print("Skills installed successfully.")
    if agents_action == "manual-merge":
        print(
            "AGENTS.md was preserved. Manually merge the kit's engineering "
            f"contract from: {SOURCE_AGENTS}"
        )
        return 3
    print("Engineering contract installed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


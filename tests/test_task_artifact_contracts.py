from __future__ import annotations

import copy
import hashlib
import json
import random
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.contracts import catalog, markdown, schema, source_lifecycle, task_artifacts


ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / ".agents"
TASK_ASSETS = AGENTS / "skills" / "decompose-tasks" / "assets"
HANDOFF_ASSETS = AGENTS / "skills" / "implement" / "assets"
SPEC_ASSETS = AGENTS / "skills" / "write-spec" / "assets"
PLAN_ASSETS = AGENTS / "skills" / "plan" / "assets"
ALLOWED_METADATA = {
    "schema_version", "id", "type", "sources", "namespace", "snapshot_at",
    "parent", "fragment_id", "status", "children", "depends_on",
}
V1_HASHES = {
    TASK_ASSETS / "tasks.template.md": "c42f85e118d2506cfe57aeeec00bcb230bf5beb49f5dd2ee2a330529a1e6fe6a",
    HANDOFF_ASSETS / "handoff.template.md": "8b33cac454acdde7140e3968f339a7ce3a81993ab5b02e44d5fdec903c3e77b7",
    SPEC_ASSETS / "spec.template.md": "5f7457c53eee844a6600a40fc340065b9909e03a2348b4df7032918f9c08123b",
    SPEC_ASSETS / "spec-index.template.md": "3a891dafc2eba9c9ed2828f60d5a6111719bd160d278e7564f79493d8f724d72",
    PLAN_ASSETS / "plan.template.md": "ca45da853442270c2b679a6de4ced8245f7feed0e39546e69ccb6a78d39a88b3",
}


def load_json(path: Path) -> dict[str, object]:
    return catalog.load_json(path)


def registry() -> list[dict[str, object]]:
    return [load_json(AGENTS / "schemas" / "markdown-document.schema.json")]


def render(path: Path, replacements: dict[str, str]) -> bytes:
    text = path.read_text(encoding="utf-8")
    for before, after in replacements.items():
        text = text.replace(before, after)
    return text.encode()


def parse_validate(path: Path, source: bytes) -> dict[str, object]:
    model = markdown.parse_markdown(
        source, allowed_metadata_keys=ALLOWED_METADATA)
    decision = schema.validate(model, load_json(path), registry=registry())
    if not decision.valid:
        raise AssertionError(decision.as_dict())
    return model


def render_tasks(plan: str = "PLAN-901", graph: str = "TASKS-901") -> bytes:
    return render(TASK_ASSETS / "tasks.v2.template.md", {
        "TASKS-<NNN>": graph,
        "PLAN-<NNN>": plan,
        "<Feature>": "Rendered feature",
        "<TOPOLOGY>": "primary-agent",
        "<TOPOLOGY-DECISION>": "Confirmed by the coordinator.",
        "<REVIEW-CAPACITY>": "1",
        "<MAX-IN-PROGRESS>": "1",
        "<TASK-TITLE>": "Build the bounded result",
        "<SOURCE-ITEMS>": "SPEC-901#REQ-001",
        "<TASK-TYPE>": "feature",
        "<RISK>": "low",
        "<RISK-RATIONALE>": "The surface is bounded.",
        "<EXECUTION>": "exclusive",
        "<EXECUTION-RATIONALE>": "One writer owns the surface.",
        "<CHANGE-SURFACE>": "The owner-local assets.",
        "<WHAT>": "Publish the result.",
        "<WHY>": "PLAN-901 design.",
        "<SCOPE>": "Only the bounded result.",
        "<EVIDENCE>": "Focused tests.",
        "<CONTRACT-RISK>": "Incorrect ordering.",
        "<AGENT-ROLES>": "One implementer and one reviewer.",
        "<REVIEW-FOCUS>": "Ordering and identity.",
        "<ROLLBACK-POINT>": "Remove the additive result.",
        "<GREEN-GATE>": "Run focused tests.",
        "<ACCEPTANCE-EVIDENCE>": "The render validates.",
        "<VALIDATION>": "python3 -m unittest tests.test_task_artifact_contracts",
    })


def render_two_tasks(
    *, first_state: str = "ready", first_depends: str = "none",
    first_blocker: str = "none", second_state: str = "ready",
    second_depends: str = "none", second_blocker: str = "none",
) -> bytes:
    source = render_tasks()
    text = source.decode()
    start = text.index("### TASK-001:")
    end = text.index("## Coverage")
    original = text[start:end]
    first = original.replace("- State: ready", f"- State: {first_state}").replace(
        "- Depends on: none", f"- Depends on: {first_depends}").replace(
        "- Blocker: none", f"- Blocker: {first_blocker}")
    second = original.replace("TASK-001", "TASK-002").replace(
        "- State: ready", f"- State: {second_state}").replace(
        "- Depends on: none", f"- Depends on: {second_depends}").replace(
        "- Blocker: none", f"- Blocker: {second_blocker}")
    text = text[:start] + first + second + text[end:]
    return text.replace("| SPEC-901#REQ-001 | TASK-001 |",
                        "| SPEC-901#REQ-001 | TASK-001, TASK-002 |").encode()


def validate_task_markdown(source: bytes) -> dict[str, object]:
    model = parse_validate(TASK_ASSETS / "tasks.v2.schema.json", source)
    task_artifacts.validate_task_graph_model(model, source=source)
    return model


def render_handoff() -> bytes:
    return render(HANDOFF_ASSETS / "handoff.v2.template.md", {
        "HANDOFF-<NNN>": "HANDOFF-901",
        "PLAN-<PLAN>": "PLAN-901",
        "TASK-<TASK>": "TASK-001",
        "<SNAPSHOT-AT>": "2025-09-08T12:34:56Z",
        "<Feature>": "Rendered feature",
        "<BASELINE>": "0eec26a",
        "<WORKTREE>": "clean checkout",
        "<PATHS>": "none",
        "<TASKS-PATH>": ".work/901/tasks.md",
        "<CURRENT-TASK>": "PLAN-901#TASK-001",
        "<PROGRESS>": "Templates rendered.",
        "<CHANGES>": "Owner-local additions.",
        "<CHECK>": "focused suite: passed",
        "<TOPOLOGY>": "primary-agent",
        "<EXPLORATION>": "implementer",
        "<IMPLEMENTATION>": "implementer",
        "<VALIDATION>": "fresh reviewer",
        "<LIMITS>": "not-tracked",
        "<STOP-REASON>": "bounded checkpoint",
        "<RISKS>": "none",
        "<NEXT-ACTION>": "Run the next read-only check.",
    })


def render_fragment(kind: str, number: str = "001") -> bytes:
    if kind == "specification-fragment":
        path = SPEC_ASSETS / "spec-fragment.v2.template.md"
        replacements = {
            "<SPEC-FRAGMENT-ID>": f"SPEC-901-FRAG-{number}",
            "SPEC-<NNN>": "SPEC-901",
            "<FRAGMENT-ID>": f"FRAG-{number}",
            "<Fragment title>": "Rendered specification fragment",
            "<Fragment scope>": "One cohesive requirement area.",
            "<Requirement>": "The fragment remains reciprocal.",
        }
    else:
        path = PLAN_ASSETS / "plan-fragment.v2.template.md"
        replacements = {
            "<PLAN-FRAGMENT-ID>": f"PLAN-901-FRAG-{number}",
            "PLAN-<NNN>": "PLAN-901",
            "<FRAGMENT-ID>": f"FRAG-{number}",
            "<Fragment title>": "Rendered plan fragment",
            "<Design scope>": "One cohesive design area.",
            "<Design detail>": "Implement the accepted parent plan.",
            "<SOURCE-ITEM>": "SPEC-901#REQ-001",
        }
    return render(path, replacements)


def graph_metadata(namespace: str = "PLAN-901", graph_id: str = "TASKS-901") -> dict[str, object]:
    return {
        "schema_version": 2,
        "id": graph_id,
        "type": "task-graph",
        "sources": [namespace],
        "namespace": namespace,
    }


def task(identifier: str, state: str = "blocked", depends_on: list[str] | None = None,
         blocker: str | None = None, result: str = "pending") -> dict[str, object]:
    return {
        "id": identifier,
        "title": f"Outcome {identifier}",
        "plan": "PLAN-901",
        "source_items": ["SPEC-901#REQ-001"],
        "type": "feature",
        "risk": "low",
        "risk_rationale": "Bounded surface.",
        "state": state,
        "depends_on": [] if depends_on is None else depends_on,
        "blocker": blocker,
        "execution": "exclusive",
        "execution_rationale": "One writer.",
        "change_surface": ["owner-local assets"],
        "conflicts_with": [],
        "what": "Publish the bounded outcome.",
        "why": "PLAN-901 accepted design.",
        "scope": "Only the declared surface.",
        "evidence": "Focused tests.",
        "contract_risk": "Ordering error.",
        "agent_roles": "Implementer and reviewer.",
        "review_focus": "Identity and ordering.",
        "rollback_point": "Remove additive files.",
        "green_gate": "Focused suite passes.",
        "acceptance_evidence": "Schemas and semantics pass.",
        "validation": "Run focused tests.",
        "result": result,
    }


def graph(tasks: list[dict[str, object]] | None = None, namespace: str = "PLAN-901",
          graph_id: str = "TASKS-901") -> dict[str, object]:
    return {
        "metadata": graph_metadata(namespace, graph_id),
        "controls": {
            "topology": "primary-agent",
            "review_capacity": 1,
            "maximum_in_progress": 1,
            "review_queue": [],
        },
        "tasks": tasks if tasks is not None else [task("TASK-001", "ready")],
    }


class FormatTests(unittest.TestCase):
    def test_templates_validate_in_template_mode_and_rendered_documents_validate(self) -> None:
        cases = (
            (TASK_ASSETS / "tasks.v2.template.md", TASK_ASSETS / "tasks.v2.schema.json",
             render_tasks(), lambda model, raw: task_artifacts.validate_task_graph_model(
                 model, source=raw)),
            (HANDOFF_ASSETS / "handoff.v2.template.md", HANDOFF_ASSETS / "handoff.v2.schema.json",
             render_handoff(), lambda model, raw: task_artifacts.validate_handoff_model(
                 model, source=raw)),
            (SPEC_ASSETS / "spec-fragment.v2.template.md", SPEC_ASSETS / "spec-fragment.v2.schema.json",
             render_fragment("specification-fragment"),
             lambda model, _raw: task_artifacts.validate_fragment_model(model)),
            (PLAN_ASSETS / "plan-fragment.v2.template.md", PLAN_ASSETS / "plan-fragment.v2.schema.json",
             render_fragment("plan-fragment"),
             lambda model, _raw: task_artifacts.validate_fragment_model(model)),
        )
        for template, owner_schema, rendered, semantic in cases:
            with self.subTest(template=template.name):
                placeholders = set(markdown.PLACEHOLDER_RE.findall(
                    template.read_text(encoding="utf-8")))
                model = markdown.parse_markdown(
                    template.read_bytes(), allowed_metadata_keys=ALLOWED_METADATA,
                    mode="template", declared_placeholders=placeholders,
                )
                self.assertTrue(schema.validate(model, load_json(
                    owner_schema), registry=registry()).valid)
                with self.assertRaises(markdown.MarkdownError):
                    markdown.parse_markdown(
                        template.read_bytes(), allowed_metadata_keys=ALLOWED_METADATA)
                rendered_model = parse_validate(owner_schema, rendered)
                semantic(rendered_model, rendered)

    def test_closed_metadata_rejects_missing_unknown_status_and_wrong_identity(self) -> None:
        cases = (
            (render_tasks(), TASK_ASSETS / "tasks.v2.schema.json"),
            (render_handoff(), HANDOFF_ASSETS / "handoff.v2.schema.json"),
            (render_fragment("specification-fragment"),
             SPEC_ASSETS / "spec-fragment.v2.schema.json"),
            (render_fragment("plan-fragment"),
             PLAN_ASSETS / "plan-fragment.v2.schema.json"),
        )
        for source, owner_schema in cases:
            for changed in (
                source.replace(b"schema_version: 2\n", b""),
                source.replace(b"---\n\n#", b'unknown: true\n---\n\n#', 1),
                source.replace(b"---\n\n#", b'status: "draft"\n---\n\n#', 1),
            ):
                with self.subTest(schema=owner_schema.name):
                    try:
                        model = markdown.parse_markdown(
                            changed, allowed_metadata_keys=ALLOWED_METADATA | {"unknown"})
                    except markdown.MarkdownError:
                        continue
                    self.assertFalse(schema.validate(model, load_json(
                        owner_schema), registry=registry()).valid)

    def test_task_headings_and_handoff_sections_are_canonical(self) -> None:
        task_model = parse_validate(
            TASK_ASSETS / "tasks.v2.schema.json", render_tasks())
        self.assertEqual(task_model["local_ids"], [
                         {"kind": "task", "id": "TASK-001"}])
        for changed in (
            render_tasks().replace(b"### TASK-001:", b"## TASK-001:"),
            render_tasks().replace(b"#### Change contract", b"#### Other contract"),
            render_tasks().replace(b"- Result: pending", b"- Outcome: pending"),
        ):
            model = markdown.parse_markdown(
                changed, allowed_metadata_keys=ALLOWED_METADATA)
            with self.assertRaises(task_artifacts.TaskArtifactError):
                task_artifacts.validate_task_graph_model(model, source=changed)
        repeated = validate_task_markdown(render_two_tasks())
        self.assertEqual(repeated["sections"].count("Change contract"), 2)
        for changed in (
            render_tasks().replace(
                b"- Review queue: none",
                b"- Review queue: empty\n- Review queue: empty"),
            render_tasks().replace(
                b"- Maximum in-progress: 1", b"- Maximum in-progress: many"),
        ):
            model = parse_validate(
                TASK_ASSETS / "tasks.v2.schema.json", changed)
            with self.assertRaises(task_artifacts.TaskArtifactError):
                task_artifacts.validate_task_graph_model(model, source=changed)

        handoff = parse_validate(
            HANDOFF_ASSETS / "handoff.v2.schema.json", render_handoff())
        self.assertNotIn("Authoritative task state", handoff["sections"])
        for section in ("Current task", "Objective last progress", "Risks and blockers"):
            self.assertIn(section, handoff["sections"])
        with self.assertRaises(task_artifacts.TaskArtifactError):
            task_artifacts.validate_handoff_model(
                copy.deepcopy(handoff) | {
                    "sections": handoff["sections"][:-1]},
                source=render_handoff())

    def test_handoff_requires_strict_utc_timestamp_and_qualified_task_sources(self) -> None:
        valid = parse_validate(
            HANDOFF_ASSETS / "handoff.v2.schema.json", render_handoff())
        task_artifacts.validate_handoff_model(valid, source=render_handoff())
        for timestamp in ("2025-02-29T12:00:00Z", "2025-01-01T12:00:00+00:00", "2025-1-01T00:00:00Z"):
            changed = copy.deepcopy(valid)
            changed["metadata"]["snapshot_at"] = timestamp
            with self.assertRaises(task_artifacts.TaskArtifactError):
                task_artifacts.validate_handoff_model(
                    changed, source=render_handoff())
        for sources in ([], ["TASK-001"], ["PLAN-901"], ["PLAN-901#TASK-001", 1]):
            changed = copy.deepcopy(valid)
            changed["metadata"]["sources"] = sources
            with self.assertRaises(task_artifacts.TaskArtifactError):
                task_artifacts.validate_handoff_model(
                    changed, source=render_handoff())

    def test_handoff_is_source_aware_recovery_only_and_exactly_one_current_task(self) -> None:
        raw = render_handoff()
        model = parse_validate(
            HANDOFF_ASSETS / "handoff.v2.schema.json", raw)
        with self.assertRaises(task_artifacts.TaskArtifactError):
            task_artifacts.validate_handoff_model(model)
        changed_sources = copy.deepcopy(model)
        changed_sources["metadata"]["sources"] = [
            "PLAN-901#TASK-001", "PLAN-902#TASK-002"]
        cases = (
            (model, raw.replace(
                b"PLAN-901#TASK-001", b"PLAN-902#TASK-002")),
            (model, raw.replace(
                b"- Current task reference: PLAN-901#TASK-001",
                b"- Current task reference: PLAN-901#TASK-001\n"
                b"- Current task reference: PLAN-901#TASK-001")),
            (model, raw.replace(b"Recovery snapshot only", b"Checkpoint only")),
            (model, raw + b"\nThis handoff is authoritative.\n"),
            (changed_sources, raw),
        )
        for changed_model, changed_raw in cases:
            with self.subTest(raw=changed_raw[-80:]), self.assertRaises(
                    task_artifacts.TaskArtifactError):
                task_artifacts.validate_handoff_model(
                    changed_model, source=changed_raw)

        # The canonical notice is the sole permitted authority-family wording.
        task_artifacts.validate_handoff_model(model, source=raw)
        authority_claims = (
            "This snapshot authoritatively assigns task state.",
            "This snapshot claims authority over recovery.",
            "These snapshots are AUTHORITIES for task state.",
            "This handoff is Authoritative for task state.",
            "This snapshot is the source of truth.",
            "This snapshot is the SOURCE-OF-TRUTH.",
            "This snapshot owns task state.",
            "This snapshot CONTROLS the task state.",
            "This snapshot assigns task state.",
        )
        for claim in authority_claims:
            changed_raw = raw + f"\n{claim}\n".encode()
            with self.subTest(claim=claim), self.assertRaises(
                    task_artifacts.TaskArtifactError):
                task_artifacts.validate_handoff_model(
                    model, source=changed_raw)
        unrelated = (
            "The author iteratively records recovery notes.",
            "Authorization checks remain unchanged.",
            "Task state controls are described in the referenced graph.",
            "Truthful source notes are preserved for recovery.",
        )
        for statement in unrelated:
            task_artifacts.validate_handoff_model(
                model, source=raw + f"\n{statement}\n".encode())

    def test_fragment_identity_parent_and_no_lifecycle_are_strict(self) -> None:
        for kind, path in (
            ("specification-fragment", SPEC_ASSETS / "spec-fragment.v2.schema.json"),
            ("plan-fragment", PLAN_ASSETS / "plan-fragment.v2.schema.json"),
        ):
            model = parse_validate(path, render_fragment(kind))
            task_artifacts.validate_fragment_model(model)
            for field, value in (
                ("parent", "SPEC-902" if kind.startswith("spec") else "PLAN-902"),
                ("fragment_id", "FRAG-002"),
                ("sources", ["SPEC-902"]
                 if kind.startswith("spec") else ["PLAN-902"]),
                ("status", "draft"),
            ):
                changed = copy.deepcopy(model)
                changed["metadata"][field] = value
                with self.assertRaises(task_artifacts.TaskArtifactError):
                    task_artifacts.validate_fragment_model(changed)

    def test_parser_recognizes_qualified_refs_with_fragment_parents(self) -> None:
        source = render_fragment("plan-fragment").replace(
            b"Implement the accepted parent plan.",
            b"Implement SPEC-901-FRAG-001#REQ-004 and PLAN-901-FRAG-002#TASK-003.",
        )
        model = parse_validate(
            PLAN_ASSETS / "plan-fragment.v2.schema.json", source)
        self.assertEqual(model["references"], [
            "SPEC-901-FRAG-001#REQ-004", "PLAN-901-FRAG-002#TASK-003",
            "SPEC-901#REQ-001",
        ])
        task_artifacts.validate_fragment_model(model)


class GraphSemanticTests(unittest.TestCase):
    def test_valid_graph_is_normalized_deterministically(self) -> None:
        tasks = [
            task("TASK-001", "done", result="Completed with passing tests."),
            task("TASK-002", "ready", ["TASK-001"]),
            task("TASK-003", "blocked", ["TASK-002"], "TASK-002"),
        ]
        value = graph(tasks)
        expected = task_artifacts.validate_task_graph(value)
        self.assertEqual(
            expected, task_artifacts.validate_task_graph(copy.deepcopy(value)))
        self.assertEqual([item["id"] for item in expected["tasks"]], [
                         "TASK-001", "TASK-002", "TASK-003"])

    def test_published_markdown_reaches_all_graph_semantics(self) -> None:
        one_task_cases = (
            render_tasks().replace(b"- State: ready", b"- State: nonsense"),
            render_tasks().replace(b"- Depends on: none", b"- Depends on: TASK-001"),
            render_tasks().replace(b"- Depends on: none", b"- Depends on: TASK-999"),
            render_tasks().replace(b"- State: ready", b"- State: blocked"),
            render_tasks().replace(b"- State: ready", b"- State: done"),
            render_tasks().replace(
                b"- State: ready\n- Depends on: none\n- Blocker: none",
                b"- State: blocked\n- Depends on: none\n"
                b"- Blocker: PLAN-902#TASK-004"),
        )
        for changed in one_task_cases:
            with self.subTest(source=changed[-120:]), self.assertRaises(
                    task_artifacts.TaskArtifactError):
                validate_task_markdown(changed)

        cycle = render_two_tasks(
            first_state="blocked", first_depends="TASK-002",
            first_blocker="TASK-002", second_state="blocked",
            second_depends="TASK-001", second_blocker="TASK-001")
        two_wip = render_two_tasks(
            first_state="in-progress", second_state="in-progress")
        over_review = render_two_tasks().replace(
            b"- Review queue: none",
            b"- Review queue: TASK-001, TASK-002")
        done_blocker = render_two_tasks(
            first_state="done", second_state="blocked",
            second_depends="TASK-001", second_blocker="TASK-001").replace(
                b"- Result: pending", b"- Result: Completed.", 1)
        for changed in (cycle, two_wip, over_review, done_blocker):
            with self.subTest(source=changed[-120:]), self.assertRaises(
                    task_artifacts.TaskArtifactError):
                validate_task_markdown(changed)

    def test_iterative_dfs_handles_deep_acyclic_and_cyclic_graphs(self) -> None:
        count = 1301
        deep = [task(f"TASK-{index:04d}", "stale",
                     [] if index == 0 else [f"TASK-{index - 1:04d}"])
                for index in range(count)]
        result = task_artifacts.validate_task_graph(graph(deep))
        self.assertEqual(len(result["tasks"]), count)
        cyclic = copy.deepcopy(deep)
        cyclic[0]["depends_on"] = [f"TASK-{count - 1:04d}"]
        with self.assertRaises(task_artifacts.TaskArtifactError):
            task_artifacts.validate_task_graph(graph(cyclic))

    def test_metadata_sources_namespace_and_global_graph_id_are_exact(self) -> None:
        mutations = (
            ("sources", []), ("sources", ["PLAN-902"]),
            ("sources", ["PLAN-901", "PLAN-902"]), ("namespace", "SPEC-901"),
            ("id", "PLAN-901"), ("status", "ready"),
        )
        for field, value in mutations:
            changed = graph()
            changed["metadata"][field] = value
            with self.subTest(field=field), self.assertRaises(task_artifacts.TaskArtifactError):
                task_artifacts.validate_task_graph(changed)

    def test_unique_local_ids_dependencies_and_cycles_fail_closed(self) -> None:
        cases = (
            [task("TASK-001", "ready"), task("TASK-001", "ready")],
            [task("TASK-001", "blocked", ["TASK-999"], "TASK-999")],
            [task("TASK-001", "blocked", ["PLAN-901#TASK-002"], "PLAN-901#TASK-002")],
            [task("TASK-001", "blocked", ["TASK-002"], "TASK-002"),
             task("TASK-002", "blocked", ["TASK-001"], "TASK-001")],
        )
        for tasks in cases:
            with self.subTest(tasks=tasks), self.assertRaises(task_artifacts.TaskArtifactError):
                task_artifacts.validate_task_graph(graph(tasks))

    def test_runnable_and_done_tasks_require_done_dependencies(self) -> None:
        for state in ("ready", "in-progress", "done"):
            dependent = task(
                "TASK-002", state, ["TASK-001"], result="Completed." if state == "done" else "pending")
            with self.subTest(state=state), self.assertRaises(task_artifacts.TaskArtifactError):
                task_artifacts.validate_task_graph(
                    graph([task("TASK-001", "blocked", blocker="external"), dependent]))
        task_artifacts.validate_task_graph(graph([
            task("TASK-001", "done", result="Completed."),
            task("TASK-002", "ready", ["TASK-001"]),
        ]))

    def test_blocker_consistency_and_done_result_are_enforced(self) -> None:
        invalid = (
            task("TASK-001", "blocked"),
            task("TASK-001", "ready", blocker="PLAN-902#TASK-004"),
            task("TASK-001", "done", result="pending"),
            task("TASK-001", "done", result="  "),
        )
        for item in invalid:
            with self.subTest(item=item), self.assertRaises(task_artifacts.TaskArtifactError):
                task_artifacts.validate_task_graph(graph([item]))
        external = graph([
            task("TASK-001", "blocked", blocker="PLAN-902#TASK-004")])
        with self.assertRaises(task_artifacts.TaskArtifactError):
            task_artifacts.validate_task_graph(external)
        task_artifacts.validate_task_graph(
            external, external_tasks={"PLAN-902#TASK-004": "blocked"})
        for resolver in ({}, {"PLAN-902#TASK-004": "done"},
                         {"PLAN-902#TASK-004": "nonsense"}):
            with self.assertRaises(task_artifacts.TaskArtifactError):
                task_artifacts.validate_task_graph(
                    external, external_tasks=resolver)

    def test_states_wip_maximum_and_review_capacity_are_semantic(self) -> None:
        two_running = graph(
            [task("TASK-001", "in-progress"), task("TASK-002", "in-progress")])
        with self.assertRaises(task_artifacts.TaskArtifactError):
            task_artifacts.validate_task_graph(two_running)
        for field, value in (("maximum_in_progress", 0), ("maximum_in_progress", True),
                             ("review_capacity", 0), ("review_queue", ["TASK-999"])):
            changed = graph()
            changed["controls"][field] = value
            with self.subTest(field=field), self.assertRaises(task_artifacts.TaskArtifactError):
                task_artifacts.validate_task_graph(changed)
        changed = graph([task("TASK-001", "in-progress"),
                        task("TASK-002", "ready")])
        changed["controls"]["review_queue"] = ["TASK-001", "TASK-002"]
        with self.assertRaises(task_artifacts.TaskArtifactError):
            task_artifacts.validate_task_graph(changed)

    def test_external_task_references_are_qualified_and_local_conflicts_exist(self) -> None:
        changed = graph()
        changed["tasks"][0]["source_items"] = ["TASK-999"]
        with self.assertRaises(task_artifacts.TaskArtifactError):
            task_artifacts.validate_task_graph(changed)
        changed = graph([task("TASK-001", "ready"), task("TASK-002", "ready")])
        changed["tasks"][0]["conflicts_with"] = ["TASK-999"]
        with self.assertRaises(task_artifacts.TaskArtifactError):
            task_artifacts.validate_task_graph(changed)
        changed["tasks"][0]["conflicts_with"] = ["TASK-002"]
        task_artifacts.validate_task_graph(changed)

    def test_graph_set_rejects_duplicate_namespace_and_global_id_but_allows_same_local_id(self) -> None:
        first = graph(namespace="PLAN-901", graph_id="TASKS-901")
        second = graph(namespace="PLAN-902", graph_id="TASKS-902")
        second["tasks"][0]["plan"] = "PLAN-902"
        normalized = task_artifacts.validate_task_graphs([first, second])
        self.assertEqual([item["tasks"][0]["id"]
                         for item in normalized], ["TASK-001", "TASK-001"])
        for changed in (
            graph(namespace="PLAN-901", graph_id="TASKS-902"),
            graph(namespace="PLAN-902", graph_id="TASKS-901"),
        ):
            if changed["metadata"]["namespace"] == "PLAN-902":
                changed["tasks"][0]["plan"] = "PLAN-902"
            with self.assertRaises(task_artifacts.TaskArtifactError):
                task_artifacts.validate_task_graphs([first, changed])

    def test_graph_set_resolves_external_blockers_across_namespaces(self) -> None:
        first = graph([
            task("TASK-001", "blocked", blocker="PLAN-902#TASK-001")],
            namespace="PLAN-901", graph_id="TASKS-901")
        second = graph([task("TASK-001", "ready")],
                       namespace="PLAN-902", graph_id="TASKS-902")
        second["tasks"][0]["plan"] = "PLAN-902"
        task_artifacts.validate_task_graphs([first, second])
        with self.assertRaises(task_artifacts.TaskArtifactError):
            task_artifacts.validate_task_graphs([first])
        done = copy.deepcopy(second)
        done["tasks"][0]["state"] = "done"
        done["tasks"][0]["result"] = "Completed."
        with self.assertRaises(task_artifacts.TaskArtifactError):
            task_artifacts.validate_task_graphs([first, done])


class FragmentSetTests(unittest.TestCase):
    def child(self, kind: str, number: str, path: str) -> dict[str, object]:
        schema_path = (SPEC_ASSETS / "spec-fragment.v2.schema.json" if kind.startswith("spec")
                       else PLAN_ASSETS / "plan-fragment.v2.schema.json")
        return {"path": path, "model": parse_validate(schema_path, render_fragment(kind, number))}

    def parent(self, kind: str = "specification") -> dict[str, object]:
        prefix = "SPEC" if kind == "specification" else "PLAN"
        return {
            "id": f"{prefix}-901", "type": kind,
            "children": [
                {"id": f"{prefix}-901-FRAG-001", "path": "fragments/001.md"},
                {"id": f"{prefix}-901-FRAG-002", "path": "fragments/002.md"},
            ],
        }

    def test_reciprocal_children_validate_in_parent_order(self) -> None:
        children = [
            self.child("specification-fragment", "001", "fragments/001.md"),
            self.child("specification-fragment", "002", "fragments/002.md"),
        ]
        result = task_artifacts.validate_fragment_set(self.parent(), children)
        self.assertEqual([item["path"] for item in result], [
                         "fragments/001.md", "fragments/002.md"])

    def test_missing_extra_wrong_order_duplicate_and_unsafe_children_fail(self) -> None:
        children = [
            self.child("specification-fragment", "001", "fragments/001.md"),
            self.child("specification-fragment", "002", "fragments/002.md"),
        ]
        mutations = []
        mutations.append((self.parent(), children[:1]))
        mutations.append((self.parent(), children +
                         [copy.deepcopy(children[0])]))
        mutations.append((self.parent(), list(reversed(children))))
        duplicate = self.parent()
        duplicate["children"][1]["id"] = duplicate["children"][0]["id"]
        mutations.append((duplicate, children))
        unsafe = self.parent()
        unsafe["children"][0]["path"] = "../escape.md"
        mutations.append((unsafe, children))
        for parent, supplied in mutations:
            with self.subTest(parent=parent), self.assertRaises(task_artifacts.TaskArtifactError):
                task_artifacts.validate_fragment_set(parent, supplied)

    def test_parent_mismatch_and_child_status_fail(self) -> None:
        children = [
            self.child("specification-fragment", "001", "fragments/001.md"),
            self.child("specification-fragment", "002", "fragments/002.md"),
        ]
        changed = copy.deepcopy(children)
        changed[0]["model"]["metadata"]["parent"] = "SPEC-902"
        with self.assertRaises(task_artifacts.TaskArtifactError):
            task_artifacts.validate_fragment_set(self.parent(), changed)
        changed = copy.deepcopy(children)
        changed[0]["model"]["metadata"]["status"] = "draft"
        with self.assertRaises(task_artifacts.TaskArtifactError):
            task_artifacts.validate_fragment_set(self.parent(), changed)

    def test_split_parent_schema_and_source_semantics_accept_closed_children(self) -> None:
        source = render(SPEC_ASSETS / "spec.v2.template.md", {
            "<NNN>": "901",
            "<Capability name>": "Split parent",
            "<authoritative source link or confirmed input>": "confirmed-request",
            "<Material product why with source links, or Unknown; no implementation rationale.>": "Confirmed rationale.",
            "<Observable requirement>": "The parent lists its child.",
            "<Observable acceptance criterion>": "The relationship validates.",
        })
        model = markdown.parse_markdown(
            source, allowed_metadata_keys=ALLOWED_METADATA)
        model["metadata"]["children"] = [
            {"id": "SPEC-901-FRAG-001", "path": "fragments/001.md"},
        ]
        decision = schema.validate(
            model, load_json(SPEC_ASSETS / "spec.v2.schema.json"), registry=registry())
        self.assertTrue(decision.valid, decision.as_dict())
        source_lifecycle.validate_specification_model(model)

    def test_cohesive_parent_needs_no_split_and_token_threshold_is_warning_only(self) -> None:
        self.assertEqual(task_artifacts.validate_fragment_set(
            {"id": "SPEC-901", "type": "specification"}, []), [])
        below = task_artifacts.assess_split(100, 3000, cohesive=True)
        above = task_artifacts.assess_split(3001, 3000, cohesive=True)
        self.assertFalse(below["warning"])
        self.assertTrue(above["warning"])
        self.assertFalse(above["split_required"])


class FragmentFilesystemTests(unittest.TestCase):
    def make_tree(self, workspace: Path) -> str:
        feature = workspace / "901-split"
        fragments = feature / "fragments"
        fragments.mkdir(parents=True)
        workspace_relative = workspace.relative_to(ROOT).as_posix()
        child_paths = [
            f"{workspace_relative}/901-split/fragments/001.md",
            f"{workspace_relative}/901-split/fragments/002.md",
        ]
        children = [
            {"id": "SPEC-901-FRAG-001", "path": child_paths[0]},
            {"id": "SPEC-901-FRAG-002", "path": child_paths[1]},
        ]
        parent = render(SPEC_ASSETS / "spec.v2.template.md", {
            "<NNN>": "901",
            "<Capability name>": "Filesystem split parent",
            "<authoritative source link or confirmed input>": "confirmed-request",
            "<Material product why with source links, or Unknown; no implementation rationale.>": "Confirmed rationale.",
            "<Observable requirement>": "The loader remains within its root.",
            "<Observable acceptance criterion>": "Declared children are reciprocal.",
        })
        declaration = f"children: {json.dumps(children, separators=(',', ':'))}\n".encode(
        )
        parent = parent.replace(b"depends_on: []\n",
                                b"depends_on: []\n" + declaration)
        (feature / "spec.md").write_bytes(parent)
        (fragments / "001.md").write_bytes(
            render_fragment("specification-fragment", "001"))
        (fragments / "002.md").write_bytes(
            render_fragment("specification-fragment", "002"))
        return f"{workspace_relative}/901-split/spec.md"

    def test_filesystem_loader_parses_owner_models_and_reciprocal_order(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".task206-", dir=ROOT) as temporary:
            parent_path = self.make_tree(Path(temporary))
            loaded = task_artifacts.load_fragment_set(ROOT, parent_path)
            self.assertEqual([item["model"]["metadata"]["fragment_id"]
                              for item in loaded["children"]],
                             ["FRAG-001", "FRAG-002"])

    def test_filesystem_loader_rejects_missing_and_extra_fragment_siblings(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".task206-", dir=ROOT) as temporary:
            workspace = Path(temporary)
            parent_path = self.make_tree(workspace)
            (workspace / "901-split/fragments/001.md").unlink()
            with self.assertRaises(task_artifacts.TaskArtifactError):
                task_artifacts.load_fragment_set(ROOT, parent_path)
        with tempfile.TemporaryDirectory(prefix=".task206-", dir=ROOT) as temporary:
            workspace = Path(temporary)
            parent_path = self.make_tree(workspace)
            (workspace / "901-split/fragments/003.md").write_bytes(
                render_fragment("specification-fragment", "003"))
            with self.assertRaises(task_artifacts.TaskArtifactError):
                task_artifacts.load_fragment_set(ROOT, parent_path)

    def test_filesystem_loader_rejects_symlink_file_ancestor_and_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".task206-", dir=ROOT) as temporary:
            workspace = Path(temporary)
            parent_path = self.make_tree(workspace)
            first = workspace / "901-split/fragments/001.md"
            first.unlink()
            first.symlink_to("002.md")
            with self.assertRaises(task_artifacts.TaskArtifactError):
                task_artifacts.load_fragment_set(ROOT, parent_path)
        with tempfile.TemporaryDirectory(prefix=".task206-", dir=ROOT) as temporary:
            workspace = Path(temporary)
            parent_path = self.make_tree(workspace)
            fragments = workspace / "901-split/fragments"
            actual = workspace / "actual-fragments"
            fragments.rename(actual)
            fragments.symlink_to(actual, target_is_directory=True)
            with self.assertRaises(task_artifacts.TaskArtifactError):
                task_artifacts.load_fragment_set(ROOT, parent_path)
        with tempfile.TemporaryDirectory(prefix=".task206-", dir=ROOT) as temporary:
            workspace = Path(temporary)
            parent_path = self.make_tree(workspace)
            parent = workspace / "901-split/spec.md"
            actual_parent = workspace / "actual-spec.md"
            parent.rename(actual_parent)
            parent.symlink_to(actual_parent)
            with self.assertRaises(task_artifacts.TaskArtifactError):
                task_artifacts.load_fragment_set(ROOT, parent_path)
        with tempfile.TemporaryDirectory(prefix="task206-root-") as temporary:
            alias = Path(temporary) / "repository-link"
            alias.symlink_to(ROOT, target_is_directory=True)
            with self.assertRaises(task_artifacts.TaskArtifactError):
                task_artifacts.load_fragment_set(
                    alias, "specs/example/spec.md")

    def test_filesystem_loader_rejects_drive_control_and_traversal_paths_typed(self) -> None:
        unsafe_paths = (
            "../escape.md", "C:/escape.md", "folder\\escape.md",
            "folder/../escape.md", "folder/\x01escape.md", "/absolute.md",
        )
        for parent_path in unsafe_paths:
            with self.subTest(parent_path=repr(parent_path)), self.assertRaises(
                    task_artifacts.TaskArtifactError):
                task_artifacts.load_fragment_set(ROOT, parent_path)
        for child_path in unsafe_paths:
            with tempfile.TemporaryDirectory(prefix=".task206-", dir=ROOT) as temporary:
                workspace = Path(temporary)
                parent_path = self.make_tree(workspace)
                parent_file = workspace / "901-split/spec.md"
                valid_child = (
                    f"{workspace.relative_to(ROOT).as_posix()}/"
                    "901-split/fragments/001.md")
                parent_file.write_bytes(parent_file.read_bytes().replace(
                    valid_child.encode(), child_path.encode(), 1))
                with self.subTest(child_path=repr(child_path)), self.assertRaises(
                        task_artifacts.TaskArtifactError):
                    task_artifacts.load_fragment_set(ROOT, parent_path)


class CatalogAndRobustnessTests(unittest.TestCase):
    def test_catalog_variants_resolve_in_owner_and_bases_stay_nonactive(self) -> None:
        data = catalog.load_artifact_catalog(ROOT)
        entries = {entry["id"]: entry for entry in data["artifacts"]}
        self.assertEqual(list(entries), sorted(entries))
        for identifier in ("task-graph", "handoff"):
            entry = entries[identifier]
            self.assertEqual(entry["writable_schema_version"], 2)
            self.assertTrue(entry["template"].endswith(".template.md"))
            self.assertIsNone(entry["schema"])
            self.assertEqual([variant["id"]
                             for variant in entry["variants"]], ["v2"])
        for identifier in ("specification-fragment", "plan-fragment"):
            entry = entries[identifier]
            self.assertEqual(entry["writable_schema_version"], 2)
            self.assertIsNone(entry["template"])
            self.assertIsNone(entry["schema"])
            self.assertIsNone(entry["lifecycle"])
            self.assertEqual([variant["id"]
                             for variant in entry["variants"]], ["v2"])
        resolved = {
            item.id: item for item in catalog.resolve_artifact_contracts(ROOT, data)}
        for identifier in ("task-graph", "handoff", "specification-fragment", "plan-fragment"):
            variant = resolved[identifier].variants[0]
            self.assertEqual(variant.id, "v2")
            self.assertEqual(variant.schema_version, 2)
            self.assertTrue(variant.template and variant.template.is_relative_to(
                resolved[identifier].owner_directory))
            self.assertTrue(variant.schema and variant.schema.is_relative_to(
                resolved[identifier].owner_directory))

    def test_catalog_has_no_future_missing_pointers(self) -> None:
        for artifact in catalog.resolve_artifact_contracts(ROOT):
            for variant in artifact.variants:
                for pointer in (variant.template, variant.schema):
                    if pointer is not None:
                        self.assertTrue(pointer.is_file())

    def test_json_like_type_validation_is_typed_and_deterministic(self) -> None:
        bad_values = [None, True, 1, "graph", [], {1: "mixed"}]
        calls = []
        for value in bad_values:
            calls.extend((
                lambda value=value: task_artifacts.validate_task_graph(value),
                lambda value=value: task_artifacts.validate_task_graphs(value),
                lambda value=value: task_artifacts.validate_task_graph_model(
                    value),
                lambda value=value: task_artifacts.validate_handoff_model(
                    value),
                lambda value=value: task_artifacts.validate_fragment_model(
                    value),
                lambda value=value: task_artifacts.validate_fragment_set(
                    value, []),
                lambda value=value: task_artifacts.assess_split(
                    value, value, cohesive=value),
            ))
        for call in calls:
            messages = []
            for _ in range(2):
                with self.assertRaises(task_artifacts.TaskArtifactError) as caught:
                    call()
                messages.append(str(caught.exception))
            self.assertEqual(messages[0], messages[1])

    def test_reasonable_malformed_fuzz_never_leaks_untyped_errors(self) -> None:
        randomizer = random.Random(206)
        atoms: list[object] = [None, True,
                               False, -1, 0, 1, "", "TASK-001", [], {}]
        for _ in range(200):
            value = randomizer.choice(atoms)
            if randomizer.randrange(2):
                value = {randomizer.choice(
                    ("metadata", "tasks", "controls", 1)): value}
            try:
                task_artifacts.validate_task_graph(value)
            except task_artifacts.TaskArtifactError:
                pass
            except Exception as exc:  # pragma: no cover - contract assertion
                self.fail(
                    f"untyped exception leaked: {type(exc).__name__}: {exc}")
        for field in ("risk", "state", "depends_on", "source_items", "blocker"):
            value = graph()
            value["tasks"][0][field] = []
            try:
                task_artifacts.validate_task_graph(value)
            except task_artifacts.TaskArtifactError:
                pass
            except Exception as exc:  # pragma: no cover - contract assertion
                self.fail(
                    f"nested untyped exception leaked: {type(exc).__name__}: {exc}")
        external = graph([
            task("TASK-001", "blocked", blocker="PLAN-902#TASK-001")])
        for resolver in ({1: "blocked"}, {"PLAN-902#TASK-001": []}, []):
            try:
                task_artifacts.validate_task_graph(
                    external, external_tasks=resolver)
            except task_artifacts.TaskArtifactError:
                pass
            except Exception as exc:  # pragma: no cover - contract assertion
                self.fail(
                    f"resolver exception leaked: {type(exc).__name__}: {exc}")

    def test_collection_limits_fail_before_unbounded_graph_work(self) -> None:
        changed = graph()
        changed["tasks"] = [task(f"TASK-{index:05d}", "ready")
                            for index in range(task_artifacts.MAX_COLLECTION_ITEMS + 1)]
        with self.assertRaisesRegex(task_artifacts.TaskArtifactError, "limit"):
            task_artifacts.validate_task_graph(changed)

    def test_real_id_scan_is_valid_and_history_complete_from_task206_baseline(self) -> None:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", "576cd93", "HEAD"],
            cwd=ROOT, check=True, capture_output=True, text=True)
        completed = subprocess.run(
            ["python3", ".agents/tools/check_artifact_ids.py", "scan",
             "--root", ".", "--format", "json"],
            cwd=ROOT, check=True, capture_output=True, text=True)
        report = json.loads(completed.stdout)
        self.assertTrue(report["valid"], report["diagnostics"])
        self.assertTrue(report["history"]["complete"], report["diagnostics"])
        codes = [item["code"] for item in report["diagnostics"]]
        self.assertNotIn("CURRENT_DOCUMENT_INVALID", codes)
        self.assertNotIn("HISTORY_DOCUMENT_INVALID", codes)

    def test_unrelated_v1_templates_remain_byte_identical(self) -> None:
        for path, expected in V1_HASHES.items():
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256(
                    path.read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()

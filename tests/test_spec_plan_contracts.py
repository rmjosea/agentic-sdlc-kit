from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.contracts import catalog, markdown, schema, source_lifecycle


ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / ".agents"
SPEC_ASSETS = AGENTS / "skills" / "write-spec" / "assets"
PLAN_ASSETS = AGENTS / "skills" / "plan" / "assets"
DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64
V1_HASHES = {
    SPEC_ASSETS / "spec.template.md": "5f7457c53eee844a6600a40fc340065b9909e03a2348b4df7032918f9c08123b",
    SPEC_ASSETS / "spec-index.template.md": "3a891dafc2eba9c9ed2828f60d5a6111719bd160d278e7564f79493d8f724d72",
    PLAN_ASSETS / "plan.template.md": "ca45da853442270c2b679a6de4ced8245f7feed0e39546e69ccb6a78d39a88b3",
}
SPEC_PLACEHOLDERS = {
    "<NNN>", "<Capability name>",
    "<authoritative source link or confirmed input>",
    "<Material product why with source links, or Unknown; no implementation rationale.>",
    "<Observable requirement>", "<Observable acceptance criterion>",
}
PLAN_PLACEHOLDERS = {
    "<NNN>", "<SOURCE-ID>", "<SOURCE-REVISION>",
    "<Feature>", "<Why this level applies>", "<source item>",
    "<implementation path>", "<plan section/decision>",
}


def load_json(path: Path) -> dict[str, object]:
    return catalog.load_json(path)


def registry() -> list[dict[str, object]]:
    return [load_json(AGENTS / "schemas" / "markdown-document.schema.json")]


def render_spec() -> bytes:
    text = (SPEC_ASSETS / "spec.v2.template.md").read_text(encoding="utf-8")
    replacements = {
        "<NNN>": "999",
        "<Capability name>": "Rendered capability",
        "<authoritative source link or confirmed input>": "confirmed-request",
        "<Material product why with source links, or Unknown; no implementation rationale.>": "Confirmed rationale.",
        "<Observable requirement>": "The result is observable.",
        "<Observable acceptance criterion>": "The result is accepted.",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode()


def render_plan() -> bytes:
    text = (PLAN_ASSETS / "plan.v2.template.md").read_text(encoding="utf-8")
    replacements = {
        "<NNN>": "999", "<SOURCE-ID>": "SPEC-999",
        "<SOURCE-REVISION>": "a" * 64, "<Feature>": "Rendered feature",
        "<Why this level applies>": "The change is bounded.",
        "<source item>": "SPEC-999#REQ-001",
        "<implementation path>": "Implement the requirement.",
        "<plan section/decision>": "Design summary",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode()


def parse_and_validate(source: bytes, owner_schema: Path) -> dict[str, object]:
    model = markdown.parse_markdown(
        source,
        allowed_metadata_keys={
            "schema_version", "id", "type", "sources", "status",
            "depends_on", "source_revisions", "risk", "risk_rationale",
        },
    )
    decision = schema.validate(model, load_json(
        owner_schema), registry=registry())
    if not decision.valid:
        raise AssertionError(decision.as_dict())
    return model


def fingerprint(source_id: str, revision: str, items: dict[str, str]) -> dict[str, object]:
    return {
        "schema_version": 2,
        "source_id": source_id,
        "source_revision": revision,
        "item_revisions": items,
    }


def plan_metadata(status: str = "approved") -> dict[str, object]:
    return {
        "schema_version": 2,
        "id": "PLAN-999",
        "type": "plan",
        "sources": ["SPEC-999"],
        "source_revisions": {
            "SPEC-999": {
                "source_revision": DIGEST_A,
                "source_items": "source-items.json",
            }
        },
        "status": status,
        "risk": "low",
        "risk_rationale": "Bounded change.",
    }


class V2FormatTests(unittest.TestCase):
    def test_templates_parse_only_in_declared_template_mode_and_renders_validate(self) -> None:
        cases = (
            (SPEC_ASSETS / "spec.v2.template.md", SPEC_PLACEHOLDERS,
             SPEC_ASSETS / "spec.v2.schema.json", render_spec(), "specification"),
            (PLAN_ASSETS / "plan.v2.template.md", PLAN_PLACEHOLDERS,
             PLAN_ASSETS / "plan.v2.schema.json", render_plan(), "plan"),
        )
        for template, placeholders, owner_schema, rendered, kind in cases:
            with self.subTest(kind=kind):
                model = markdown.parse_markdown(
                    template.read_bytes(),
                    allowed_metadata_keys={
                        "schema_version", "id", "type", "sources", "status",
                        "depends_on", "source_revisions", "risk", "risk_rationale",
                    },
                    mode="template", declared_placeholders=placeholders,
                )
                self.assertEqual(set(model["placeholders"]), placeholders)
                template_decision = schema.validate(
                    model, load_json(owner_schema), registry=registry())
                self.assertTrue(template_decision.valid,
                                template_decision.as_dict())
                with self.assertRaisesRegex(markdown.MarkdownError, "placeholder"):
                    markdown.parse_markdown(
                        template.read_bytes(),
                        allowed_metadata_keys=set(model["metadata"]),
                        mode="rendered",
                    )
                rendered_model = parse_and_validate(rendered, owner_schema)
                self.assertEqual(rendered_model["metadata"]["type"], kind)

    def test_spec_metadata_declarations_sections_and_status_are_closed(self) -> None:
        valid = render_spec()
        model = parse_and_validate(valid, SPEC_ASSETS / "spec.v2.schema.json")
        source_lifecycle.validate_specification_model(model)
        self.assertEqual(model["metadata"], {
            "schema_version": 2, "id": "SPEC-999", "type": "specification",
            "sources": ["confirmed-request"], "status": "draft", "depends_on": [],
        })
        self.assertEqual([item["id"]
                         for item in model["local_ids"]], ["REQ-001", "AC-001"])
        for old, new in (
            (b'status: "draft"', b'status: "planned"'),
            (b'type: "specification"', b'type: "plan"'),
            (b'id: "SPEC-999"', b'id: "PLAN-999"'),
            (b'sources: ["confirmed-request"]', b'sources: []'),
            (b'depends_on: []', b'depends_on: ["not-an-id"]'),
            (b'## Outcome', b'## Unsupported outcome'),
            (b'**REQ-001**:', b'REQ-001:'),
            (b'**AC-001**:', b'AC-001:'),
        ):
            with self.subTest(new=new):
                changed = valid.replace(old, new)
                model = markdown.parse_markdown(
                    changed,
                    allowed_metadata_keys={
                        "schema_version", "id", "type", "sources", "status", "depends_on"
                    },
                )
                self.assertFalse(schema.validate(
                    model, load_json(SPEC_ASSETS / "spec.v2.schema.json"), registry=registry()
                ).valid)

    def test_plan_metadata_sections_coverage_and_native_interface_guidance_are_closed(self) -> None:
        valid = render_plan()
        model = parse_and_validate(valid, PLAN_ASSETS / "plan.v2.schema.json")
        source_lifecycle.validate_plan_model(model)
        self.assertIn("Native interface contracts", model["sections"])
        self.assertIn(
            "Use OpenAPI, AsyncAPI, or JSON Schema only", valid.decode())
        for old, new in (
            (b'status: "draft"', b'status: "verified"'),
            (b'risk: "low"', b'risk: "critical"'),
            (b'type: "plan"', b'type: "specification"'),
            (b'"SPEC-999":{"source_revision"',
             b'"SPEC-998":{"source_revision"'),
            (b'## Native interface contracts', b'## Generic interfaces'),
            (b'| SPEC-999#REQ-001 |', b'| REQ-001 |'),
        ):
            with self.subTest(new=new):
                changed = valid.replace(old, new)
                try:
                    changed_model = parse_and_validate(
                        changed, PLAN_ASSETS / "plan.v2.schema.json")
                    source_lifecycle.validate_plan_model(changed_model)
                except (AssertionError, markdown.MarkdownError, source_lifecycle.SourceLifecycleError):
                    continue
                self.fail("invalid plan mutation was accepted")

    def test_reference_contract_allows_spec_locals_and_fragment_parents_but_plan_requires_qualified(self) -> None:
        spec_source = render_spec().replace(
            b"The result is observable.",
            b"The result is observable and follows REQ-777 from prior discussion.",
        )
        spec_model = parse_and_validate(
            spec_source, SPEC_ASSETS / "spec.v2.schema.json")
        self.assertIn("REQ-777", spec_model["references"])
        source_lifecycle.validate_specification_model(spec_model)

        plan_source = render_plan().replace(
            b"| SPEC-999#REQ-001 |",
            b"| SPEC-999-FRAG-1#REQ-001 and REQ-777 and TASK-009 |",
        )
        plan_model = markdown.parse_markdown(
            plan_source,
            allowed_metadata_keys={
                "schema_version", "id", "type", "sources", "source_revisions",
                "status", "risk", "risk_rationale",
            },
        )
        self.assertEqual(plan_model["references"], [
            "SPEC-999-FRAG-1#REQ-001", "REQ-777", "TASK-009"])
        decision = schema.validate(
            plan_model, load_json(PLAN_ASSETS / "plan.v2.schema.json"),
            registry=registry())
        self.assertFalse(decision.valid)
        with self.assertRaisesRegex(
                source_lifecycle.SourceLifecycleError, "local reference"):
            source_lifecycle.validate_plan_model(plan_model)

        fragment_plan = render_plan().replace(
            b"SPEC-999", b"SPEC-999-FRAG-1")
        fragment_model = parse_and_validate(
            fragment_plan, PLAN_ASSETS / "plan.v2.schema.json")
        source_lifecycle.validate_plan_model(fragment_model)
        self.assertIn("SPEC-999-FRAG-1#REQ-001", fragment_model["references"])

    def test_current_spec_002_and_real_source_items_are_an_exact_valid_pair(self) -> None:
        companion_path = ROOT / ".work" / "002-harness-v2" / "source-items.json"
        companion = load_json(companion_path)
        contract = load_json(
            PLAN_ASSETS / "source-fingerprint-map.schema.json")
        self.assertTrue(schema.validate(companion, contract).valid)
        source_lifecycle.validate_source_fingerprint_map(companion)
        completed = subprocess.run(
            [sys.executable, str(AGENTS / "tools" / "fingerprint_artifact.py"),
             "--root", str(ROOT), "--input", "specs/002-harness-v2/spec.md",
             "--verify", ".work/002-harness-v2/source-items.json", "--format", "json"],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0,
                         completed.stderr or completed.stdout)
        report = json.loads(completed.stdout)
        self.assertTrue(report["valid"])
        self.assertEqual(report["source_revision"],
                         companion["source_revision"])
        self.assertEqual(report["item_revisions"], companion["item_revisions"])
        self.assertEqual(len(report["item_revisions"]), 75)

    def test_source_fingerprint_map_schema_and_semantic_keys_are_exact(self) -> None:
        contract = load_json(
            PLAN_ASSETS / "source-fingerprint-map.schema.json")
        valid = fingerprint("SPEC-999", DIGEST_A,
                            {"SPEC-999#REQ-001": DIGEST_B})
        self.assertTrue(schema.validate(valid, contract).valid)
        source_lifecycle.validate_source_fingerprint_map(valid)
        mutations = []
        for field in valid:
            changed = copy.deepcopy(valid)
            del changed[field]
            mutations.append(changed)
        for field, value in (
            ("schema_version", 1), ("source_id", "spec-999"),
            ("source_id", "SPEC-999-FRAG-1-MORE-2"),
            ("source_revision", "a" * 64),
            ("item_revisions", {"SPEC-998#REQ-001": DIGEST_B}),
            ("item_revisions", {"SPEC-999#TASK-001": DIGEST_B}),
        ):
            changed = copy.deepcopy(valid)
            changed[field] = value
            mutations.append(changed)
        changed = copy.deepcopy(valid)
        changed["unknown"] = True
        mutations.append(changed)
        for changed in mutations:
            with self.subTest(changed=changed):
                decision = schema.validate(changed, contract)
                if decision.valid:
                    with self.assertRaises(source_lifecycle.SourceLifecycleError):
                        source_lifecycle.validate_source_fingerprint_map(
                            changed)
                else:
                    self.assertFalse(decision.valid)

    def test_fragment_fingerprint_keys_are_valid_but_empty_and_huge_maps_fail_closed(self) -> None:
        contract = load_json(
            PLAN_ASSETS / "source-fingerprint-map.schema.json")
        fragment = fingerprint(
            "SPEC-999-FRAG-1", DIGEST_A,
            {"SPEC-999-FRAG-1#REQ-001": DIGEST_B},
        )
        self.assertTrue(schema.validate(fragment, contract).valid)
        self.assertEqual(
            source_lifecycle.validate_source_fingerprint_map(fragment), fragment)

        empty = fingerprint("SPEC-999", DIGEST_A, {})
        self.assertFalse(schema.validate(empty, contract).valid)
        with self.assertRaisesRegex(
                source_lifecycle.SourceLifecycleError, "at least one"):
            source_lifecycle.validate_source_fingerprint_map(empty)

        huge = fingerprint("SPEC-999", DIGEST_A, {
            f"SPEC-999#REQ-{index}": DIGEST_B for index in range(10001)
        })
        with self.assertRaisesRegex(
                source_lifecycle.SourceLifecycleError, "limit"):
            source_lifecycle.validate_source_fingerprint_map(huge)


class LifecycleTests(unittest.TestCase):
    def test_every_spec_and_plan_transition(self) -> None:
        profiles = {
            "specification": (
                {"draft", "approved", "implemented", "verified"},
                {("draft", "approved"), ("approved", "implemented"),
                 ("implemented", "verified")},
            ),
            "plan": (
                {"draft", "approved", "stale", "implemented"},
                {("draft", "approved"), ("approved", "stale"),
                 ("approved", "implemented"), ("stale", "approved")},
            ),
        }
        for kind, (states, allowed) in profiles.items():
            for before in states:
                for after in states:
                    with self.subTest(kind=kind, before=before, after=after):
                        self.assertEqual(
                            source_lifecycle.transition_allowed(
                                kind, before, after),
                            (before, after) in allowed,
                        )
        self.assertFalse(source_lifecycle.transition_allowed(
            "review", "draft", "approved"))

    def test_verified_spec_seal_rejects_any_semantic_mutation(self) -> None:
        sealed = fingerprint("SPEC-999", DIGEST_A,
                             {"SPEC-999#REQ-001": DIGEST_B})
        unchanged = source_lifecycle.verify_spec_seal(
            "verified", sealed, sealed)
        self.assertTrue(unchanged["valid"])
        for changed in (
            fingerprint("SPEC-999", DIGEST_C, {"SPEC-999#REQ-001": DIGEST_B}),
            fingerprint("SPEC-999", DIGEST_A, {"SPEC-999#REQ-001": DIGEST_C}),
            fingerprint("SPEC-999", DIGEST_A, {}),
            fingerprint("SPEC-999", DIGEST_A, {
                "SPEC-999#REQ-001": DIGEST_B, "SPEC-999#AC-001": DIGEST_C}),
        ):
            with self.subTest(changed=changed):
                result = source_lifecycle.verify_spec_seal(
                    "verified", changed, sealed)
                self.assertFalse(result["valid"])
                self.assertTrue(result["changed_items"] or result["removed_items"]
                                or result["new_items"] or result["revision_changed"])
        self.assertTrue(source_lifecycle.verify_spec_seal(
            "approved", changed, sealed)["valid"])


class FreshnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.expected = fingerprint("SPEC-999", DIGEST_A, {
            "SPEC-999#REQ-001": DIGEST_A,
            "SPEC-999#REQ-002": DIGEST_B,
        })
        self.coverage = {
            "SPEC-999#REQ-001": ["plan-area-a", "PLAN-999#TASK-001"],
            "SPEC-999#REQ-002": ["plan-area-b", "PLAN-999#TASK-002"],
        }

    def assess(self, current: dict[str, object], status: str = "approved") -> dict[str, object]:
        return source_lifecycle.assess_plan_freshness(
            plan_metadata(status), {"source-items.json": self.expected},
            {"SPEC-999": current}, self.coverage,
        )

    def test_exact_match_derives_planned_only_for_approved_plan(self) -> None:
        result = self.assess(self.expected)
        self.assertTrue(result["fresh"])
        self.assertTrue(result["planned"])
        self.assertTrue(result["can_implement"])
        self.assertEqual(result["effective_status"], "approved")
        self.assertEqual(result["unaffected_items"], [
            "SPEC-999#REQ-001", "SPEC-999#REQ-002"])
        self.assertEqual(result["affected_items"], [])
        draft = self.assess(self.expected, "draft")
        self.assertTrue(draft["fresh"])
        self.assertFalse(draft["planned"])

    def test_body_source_new_removed_and_single_item_changes_have_exact_impact(self) -> None:
        cases = (
            (fingerprint("SPEC-999", DIGEST_C, {
                "SPEC-999#REQ-001": DIGEST_C, "SPEC-999#REQ-002": DIGEST_B}),
             ["SPEC-999#REQ-001"], [], [], ["SPEC-999#REQ-002"]),
            (fingerprint("SPEC-999", DIGEST_C, {
                "SPEC-999#REQ-001": DIGEST_A}),
             [], ["SPEC-999#REQ-002"], [], ["SPEC-999#REQ-001"]),
            (fingerprint("SPEC-999", DIGEST_C, {
                "SPEC-999#REQ-001": DIGEST_A, "SPEC-999#REQ-002": DIGEST_B,
                "SPEC-999#AC-001": DIGEST_C}),
             [], [], ["SPEC-999#AC-001"], ["SPEC-999#REQ-001", "SPEC-999#REQ-002"]),
            (fingerprint("SPEC-999", DIGEST_C, self.expected["item_revisions"]),
             [], [], [], ["SPEC-999#REQ-001", "SPEC-999#REQ-002"]),
        )
        for current, changed, removed, new, unaffected in cases:
            with self.subTest(current=current):
                result = self.assess(current)
                self.assertFalse(result["fresh"])
                self.assertFalse(result["planned"])
                self.assertEqual(result["effective_status"], "stale")
                self.assertEqual(result["changed_items"], changed)
                self.assertEqual(result["removed_items"], removed)
                self.assertEqual(result["new_items"], new)
                self.assertEqual(result["unaffected_items"], unaffected)
        one = self.assess(cases[0][0])
        self.assertEqual(one["affected_targets"], {
            "SPEC-999#REQ-001": ["PLAN-999#TASK-001", "plan-area-a"]})
        self.assertNotIn("PLAN-999#TASK-002",
                         json.dumps(one["affected_targets"]))

    def test_status_only_unchanged_stale_reconciliation_and_implemented_history(self) -> None:
        self.assertTrue(self.assess(self.expected)["fresh"])
        stale = self.assess(self.expected, "stale")
        self.assertEqual(stale["eligible_transition"], "approved")
        self.assertFalse(stale["planned"])
        changed = fingerprint("SPEC-999", DIGEST_C, {
            "SPEC-999#REQ-001": DIGEST_C, "SPEC-999#REQ-002": DIGEST_B})
        implemented = self.assess(changed, "implemented")
        self.assertEqual(implemented["effective_status"], "implemented")
        self.assertFalse(implemented["reopen"])
        self.assertEqual(implemented["affected_items"], ["SPEC-999#REQ-001"])

    def test_reconciled_new_item_remains_blocked_until_coverage_is_mapped(self) -> None:
        expanded = fingerprint("SPEC-999", DIGEST_C, {
            "SPEC-999#REQ-001": DIGEST_A, "SPEC-999#REQ-002": DIGEST_B,
            "SPEC-999#AC-001": DIGEST_C,
        })
        metadata = plan_metadata()
        metadata["source_revisions"]["SPEC-999"]["source_revision"] = DIGEST_C
        blocked = source_lifecycle.assess_plan_freshness(
            metadata, {"source-items.json": expanded}, {"SPEC-999": expanded},
            self.coverage,
        )
        self.assertTrue(blocked["source_fresh"])
        self.assertFalse(blocked["fresh"])
        self.assertFalse(blocked["planned"])
        self.assertEqual(blocked["unmapped_items"], ["SPEC-999#AC-001"])
        mapped_coverage = copy.deepcopy(self.coverage)
        mapped_coverage["SPEC-999#AC-001"] = ["plan-area-c"]
        reconciled = source_lifecycle.assess_plan_freshness(
            metadata, {"source-items.json": expanded}, {"SPEC-999": expanded},
            mapped_coverage,
        )
        self.assertTrue(reconciled["fresh"])
        self.assertTrue(reconciled["planned"])

    def test_freshness_requires_exact_companion_paths_and_current_source_keys(self) -> None:
        cases = (
            ({}, {"SPEC-999": self.expected},
             "companions keys.*missing=source-items.json.*extra=none"),
            ({"source-items.json": self.expected, "extra.json": self.expected},
             {"SPEC-999": self.expected},
             "companions keys.*missing=none.*extra=extra.json"),
            ({"source-items.json": self.expected}, {},
             "current_fingerprints keys.*missing=SPEC-999.*extra=none"),
            ({"source-items.json": self.expected},
             {"SPEC-999": self.expected, "SPEC-998": self.expected},
             "current_fingerprints keys.*missing=none.*extra=SPEC-998"),
        )
        for companions, current, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(
                    source_lifecycle.SourceLifecycleError, message):
                source_lifecycle.assess_plan_freshness(
                    plan_metadata(), companions, current, self.coverage)

    def test_empty_companion_cannot_derive_planned(self) -> None:
        empty = fingerprint("SPEC-999", DIGEST_A, {})
        with self.assertRaisesRegex(
                source_lifecycle.SourceLifecycleError, "at least one"):
            source_lifecycle.assess_plan_freshness(
                plan_metadata(), {"source-items.json": empty},
                {"SPEC-999": empty}, {})

    def test_plan_requires_both_frontmatter_revision_and_companion_match(self) -> None:
        bad_metadata = plan_metadata()
        bad_metadata["source_revisions"]["SPEC-999"]["source_revision"] = DIGEST_B
        result = source_lifecycle.assess_plan_freshness(
            bad_metadata, {"source-items.json": self.expected},
            {"SPEC-999": self.expected}, self.coverage,
        )
        self.assertFalse(result["fresh"])
        self.assertFalse(result["planned"])
        bad_items = copy.deepcopy(self.expected)
        bad_items["item_revisions"]["SPEC-999#REQ-001"] = DIGEST_C
        result = source_lifecycle.assess_plan_freshness(
            plan_metadata(), {"source-items.json": bad_items},
            {"SPEC-999": self.expected}, self.coverage,
        )
        self.assertFalse(result["fresh"])
        self.assertFalse(result["planned"])


class MalformedInputTests(unittest.TestCase):
    def test_all_json_like_malformed_shapes_raise_contract_errors_not_type_errors(self) -> None:
        spec_model = parse_and_validate(
            render_spec(), SPEC_ASSETS / "spec.v2.schema.json")
        plan_model = parse_and_validate(
            render_plan(), PLAN_ASSETS / "plan.v2.schema.json")
        expected = fingerprint(
            "SPEC-999", DIGEST_A, {"SPEC-999#REQ-001": DIGEST_B})
        coverage = {"SPEC-999#REQ-001": ["plan-area"]}

        bad_spec_sources = copy.deepcopy(spec_model)
        bad_spec_sources["metadata"]["sources"] = [{}]
        bad_spec_dependencies = copy.deepcopy(spec_model)
        bad_spec_dependencies["metadata"]["depends_on"] = [[]]
        bad_plan_sources = copy.deepcopy(plan_model)
        bad_plan_sources["metadata"]["sources"] = [[]]
        bad_plan_ids = copy.deepcopy(plan_model)
        bad_plan_ids["local_ids"] = None
        bad_metadata = plan_metadata()
        bad_metadata["source_revisions"] = {1: {}}

        calls = (
            lambda: source_lifecycle.transition_allowed(
                [], "draft", "approved"),
            lambda: source_lifecycle.transition_allowed(
                "plan", {}, "approved"),
            lambda: source_lifecycle.validate_source_fingerprint_map({
                "schema_version": 2, "source_id": "SPEC-999",
                "source_revision": DIGEST_A, "item_revisions": {1: DIGEST_B},
            }),
            lambda: source_lifecycle.validate_source_fingerprint_map({
                1: True, "schema_version": 2, "source_id": "SPEC-999",
                "source_revision": DIGEST_A, "item_revisions": {},
            }),
            lambda: source_lifecycle.validate_specification_model(
                bad_spec_sources),
            lambda: source_lifecycle.validate_specification_model(
                bad_spec_dependencies),
            lambda: source_lifecycle.validate_plan_model(bad_plan_sources),
            lambda: source_lifecycle.validate_plan_model(bad_plan_ids),
            lambda: source_lifecycle.assess_plan_freshness(
                bad_metadata, {"source-items.json": expected},
                {"SPEC-999": expected}, coverage),
            lambda: source_lifecycle.assess_plan_freshness(
                plan_metadata(), {1: expected}, {"SPEC-999": expected}, coverage),
            lambda: source_lifecycle.assess_plan_freshness(
                plan_metadata(), {"source-items.json": expected},
                {1: expected}, coverage),
            lambda: source_lifecycle.assess_plan_freshness(
                plan_metadata(), {"source-items.json": expected},
                {"SPEC-999": expected}, {1: ["plan-area"]}),
            lambda: source_lifecycle.verify_spec_seal({}, expected, expected),
        )
        for call in calls:
            with self.subTest(call=call), self.assertRaises(
                    source_lifecycle.SourceLifecycleError):
                call()


class CatalogVariantTests(unittest.TestCase):
    def test_v2_variants_resolve_without_changing_v1_bases(self) -> None:
        data = catalog.load_artifact_catalog(ROOT)
        entries = {entry["id"]: entry for entry in data["artifacts"]}
        for identifier in ("specification", "plan"):
            entry = entries[identifier]
            self.assertEqual(entry["writable_schema_version"], 2)
            self.assertTrue(entry["template"].endswith(".template.md"))
            self.assertIsNone(entry["schema"])
            self.assertTrue(entry["lifecycle"].endswith("-v1"))
            self.assertEqual([variant["id"]
                             for variant in entry["variants"]], ["v2"])
        source_map = entries["source-fingerprint-map"]
        self.assertEqual(source_map["writable_schema_version"], 2)
        self.assertEqual(source_map["variants"][0]["schema_version"], 2)
        resolved = {
            item.id: item for item in catalog.resolve_artifact_contracts(ROOT, data)}
        for identifier in ("specification", "plan", "source-fingerprint-map"):
            variant = resolved[identifier].variants[0]
            self.assertEqual(variant.id, "v2")
            self.assertEqual(variant.schema_version, 2)
            self.assertTrue(variant.schema and variant.schema.is_file())
            if identifier != "source-fingerprint-map":
                self.assertTrue(
                    variant.template and variant.template.is_file())

    def test_variant_shape_order_and_pointer_mutations_fail_closed(self) -> None:
        data = catalog.load_artifact_catalog(ROOT)
        spec = next(
            entry for entry in data["artifacts"] if entry["id"] == "specification")
        mutations = []
        changed = copy.deepcopy(data)
        target = next(
            entry for entry in changed["artifacts"] if entry["id"] == "specification")
        target["variants"][0]["unknown"] = True
        mutations.append(changed)
        changed = copy.deepcopy(data)
        target = next(
            entry for entry in changed["artifacts"] if entry["id"] == "specification")
        target["variants"].append(copy.deepcopy(target["variants"][0]))
        mutations.append(changed)
        changed = copy.deepcopy(data)
        target = next(
            entry for entry in changed["artifacts"] if entry["id"] == "specification")
        target["variants"][0]["schema"] = "skills/plan/assets/plan.v2.schema.json"
        mutations.append(changed)
        self.assertEqual(spec["variants"][0]["requires_modules"], [])
        self.assertEqual(spec["variants"][0]["forbids_sections"], [])
        for changed in mutations:
            with self.subTest(changed=changed):
                with self.assertRaises(catalog.CatalogError):
                    catalog.resolve_artifact_contracts(ROOT, changed)

    def test_variant_ids_are_unique_independent_of_version_and_order_is_separate(self) -> None:
        data = catalog.load_artifact_catalog(ROOT)
        catalog_schema = load_json(
            AGENTS / "schemas" / "artifact-catalog.schema.json")

        duplicate_id = copy.deepcopy(data)
        target = next(entry for entry in duplicate_id["artifacts"]
                      if entry["id"] == "specification")
        second = copy.deepcopy(target["variants"][0])
        second["schema_version"] = 3
        target["variants"].append(second)
        self.assertTrue(schema.validate(duplicate_id, catalog_schema).valid)
        with self.assertRaisesRegex(catalog.CatalogError, "duplicate variant id"):
            catalog.validate_artifact_catalog(duplicate_id)

        wrong_order = copy.deepcopy(data)
        target = next(entry for entry in wrong_order["artifacts"]
                      if entry["id"] == "specification")
        second = copy.deepcopy(target["variants"][0])
        second["id"] = "v3"
        second["schema_version"] = 3
        target["variants"].insert(0, second)
        with self.assertRaisesRegex(catalog.CatalogError, "ordered by schema_version and id"):
            catalog.validate_artifact_catalog(wrong_order)

        exact_duplicate = copy.deepcopy(data)
        target = next(entry for entry in exact_duplicate["artifacts"]
                      if entry["id"] == "specification")
        target["variants"].append(copy.deepcopy(target["variants"][0]))
        self.assertFalse(schema.validate(
            exact_duplicate, catalog_schema).valid)

    def test_v1_template_bytes_remain_exact(self) -> None:
        for path, expected in V1_HASHES.items():
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256(
                    path.read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()

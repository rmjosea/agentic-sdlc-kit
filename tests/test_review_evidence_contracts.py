from __future__ import annotations

import ast
import copy
import hashlib
import json
import random
import unittest
from pathlib import Path

from scripts.contracts import catalog, markdown, review_evidence, schema


ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / ".agents"
REVIEW_ASSETS = AGENTS / "skills" / "review" / "assets"
REVIEW_SKILL = AGENTS / "skills" / "review" / "SKILL.md"
REVIEW_COMMENTS = AGENTS / "skills" / "review" / \
    "references" / "review-comments.md"
EVIDENCE_ASSETS = AGENTS / "modules" / "evidence" / "assets"
COMPLIANCE_ASSETS = AGENTS / "modules" / "compliance" / "assets"
COMPLIANCE_V2_ASSETS = COMPLIANCE_ASSETS / "v2"
COMMON_SCHEMA = AGENTS / "schemas" / "markdown-document.schema.json"
ALLOWED_METADATA = {
    "schema_version", "id", "type", "sources", "verdict", "evidence_reference",
}
SIGNALS = [
    "Correctness", "Security", "Compatibility", "Maintainability", "Performance",
    "Accessibility", "Observability", "Cost", "Understandability",
]
FORBIDDEN_REDUCED = {
    "Scope", "Reviewer role and independence", "Authoritative sources", "Risk",
    "Change contract and review focus", "Selected quality signals",
    "Checks and evidence", "Acceptance coverage",
}
V1_HASHES = {
    REVIEW_ASSETS / "review.template.md":
        "66bc900908dd68755b743affc4a8999975cf5820ca5395880df2e933e3c77019",
    EVIDENCE_ASSETS / "evidence.template.json":
        "c936a636a1908448b383c7596d14c10fd135f487cccaa31f0fbae550d3530b5f",
    EVIDENCE_ASSETS / "evidence.schema.json":
        "4e0accb338351647f1f5daebd0942d67d357459230d383ad6a14835e1123dc34",
    COMPLIANCE_ASSETS / "audit-event.template.json":
        "ea30ccb642c42bfc1acdac5e4ea31edb75ecd92acd51e7b492dcdb3c276ff7a9",
    COMPLIANCE_ASSETS / "audit-event.schema.json":
        "ae9cc781e22f15e1f54a8119349cbc4e8120870d0d5a72e303f9662017a5797c",
}


def load_json(path: Path) -> dict[str, object]:
    return catalog.load_json(path)


def parse_review(source: bytes | str, *, template: bool = False,
                 placeholders: set[str] | None = None) -> dict[str, object]:
    arguments: dict[str, object] = {
        "allowed_metadata_keys": ALLOWED_METADATA,
        "mode": "template" if template else "rendered",
    }
    if template:
        arguments["declared_placeholders"] = placeholders or set()
    return markdown.parse_markdown(source, **arguments)


def render_standalone() -> bytes:
    text = (REVIEW_ASSETS / "review-standalone.v2.template.md").read_text()
    replacements = {
        "REVIEW-<N>": "REVIEW-901",
        "<authoritative source>": "SPEC-002",
        "<change>": "TASK-208",
        "<fixed base>": "72593eb",
        "<fixed head>": "working-tree-snapshot",
        "<committed range>": "72593eb..72593eb",
        "<uncommitted scope>": "TASK-208 files",
        "<scope notes>": "No exclusions.",
        "<reviewer role>": "fresh validator",
        "<reviewer id>": "validator-1",
        "<implementers>": "implementer-1",
        "<prior participation>": "none",
        "<independence basis>": "Fresh context and no implementation participation.",
        "<priority>": "1",
        "<authority for>": "accepted behavior",
        "<gaps or conflicts>": "none",
        "<risk rationale>": "Format contracts affect assurance claims.",
        "<required depth and evidence>": "Focused and regression checks.",
        "<what>": "Add parallel v2 formats.",
        "<authoritative why>": "PLAN-002#TASK-208",
        "<contract scope>": "Owner-local additive assets only.",
        "<required evidence>": "Focused and full tests.",
        "<agent roles>": "implementer and fresh validator",
        "<review focus>": "Truthfulness and no cutover.",
        "<risk comparison or deviation>": "none",
        "<missing-contract impact>": "none",
        "<trigger or N/A reason>": "Contract behavior changes.",
        "<evidence>": "python3 -m unittest tests.test_review_evidence_contracts",
        "<check or procedure>": "python3 -m unittest tests.test_review_evidence_contracts",
        "<fixed check scope>": "TASK-208 files",
        "<actual result>": "passed",
        "<requirement or risk>": "SPEC-002#AC-009",
        "<finding records or none>": "none",
        "<source item or criterion>": "SPEC-002#AC-009",
        "<implementation evidence>": "owner-local assets",
        "<check evidence>": "python3 -m unittest tests.test_review_evidence_contracts",
        "<missing behavior>": "none",
        "<extra behavior>": "none",
        "<scope deviations>": "none",
        "<residual risks>": "none",
        "<unverified areas>": "none",
        "<required follow-up>": "none",
        "<verdict rationale>": "All required evidence is present and independence is met.",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode()


def render_reduced(verdict: str = "blocked") -> bytes:
    text = (REVIEW_ASSETS / "review-with-evidence.v2.template.md").read_text()
    replacements = {
        "REVIEW-<N>": "REVIEW-902", "EVIDENCE-<N>": "EVIDENCE-901",
        "<change>": "TASK-208", "<finding records or none>": "none",
        "<acceptance gaps or none>": "Required checks remain pending.",
        "<residual risks or none>": "Validation is incomplete.",
        "<one exact verdict>": verdict,
        "<verdict rationale>": "The evidence record has the same blocked verdict.",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode()


def evidence_record(*, risk: str = "low", status: str = "in-progress",
                    transition: str = "not-requested", verdict: str = "blocked",
                    independence: str = "self-review") -> dict[str, object]:
    record = load_json(EVIDENCE_ASSETS / "evidence.v2.template.json")
    record["risk"]["level"] = risk
    record["lifecycle"]["status"] = status
    record["lifecycle"]["transition"] = transition
    record["review"]["verdict"] = verdict
    record["review"]["independence"] = independence
    if independence == "independent":
        record["review"].update({
            "reviewer_id": "validator-1", "reviewer_role": "fresh validator",
            "implementers": ["implementer-1"], "prior_participation": [],
            "fresh_context": True,
            "independence_basis": "Fresh context and no implementation participation.",
        })
    if status == "complete":
        scope = record["repository_scope"][0]
        scope.update({
            "base": "a" * 40, "head": "b" * 40,
            "committed_range": "a" * 40 + ".." + "b" * 40,
            "snapshot_sha256": hashlib.sha256(b"[]").hexdigest(),
        })
        record["checks"][0].update({
            "status": "passed", "observed_result": "Focused checks passed.",
            "evidence_class": "observed evidence", "output_reference": "focused.log",
        })
        record["requirement_coverage"][0].update({
            "status": "covered", "implementation_references": ["implementation.py:1"],
        })
    return record


def event(sequence: int, timestamp: str, *, action: str = "evidence-updated",
          previous: str | None = None, new: str | None = None) -> dict[str, object]:
    value = load_json(COMPLIANCE_V2_ASSETS / "audit-event.v2.template.json")
    value["event_id"] = f"EVENT-{sequence:06d}"
    value["sequence"] = sequence
    value["timestamp"] = timestamp
    value["action"] = action
    value["previous_lifecycle"] = previous
    value["new_lifecycle"] = new
    return value


def audit_text(*events: dict[str, object]) -> str:
    return "".join(review_evidence.canonical_audit_event(item) + "\n" for item in events)


class ReviewTemplateTests(unittest.TestCase):
    def test_review_comment_reference_defines_progressive_contract(self) -> None:
        skill = REVIEW_SKILL.read_text(encoding="utf-8")
        reference = REVIEW_COMMENTS.read_text(encoding="utf-8")
        self.assertTrue(REVIEW_COMMENTS.is_file())
        self.assertIn("review-comments.md", skill)
        self.assertIn("converting findings into comments", skill)
        for value in ("critical", "high", "medium", "low",
                      "Required", "Optional", "Nit", "Question", "FYI"):
            self.assertIn(value, reference)
        self.assertIn("independent axes", reference)
        self.assertIn("cannot independently produce a", reference)
        self.assertIn("addresses the code, not the person", reference)
        self.assertIn("one problem", reference)
        self.assertIn("location", reference)
        self.assertIn("evidence", reference)
        self.assertIn("disposition", reference)

    def test_templates_parse_only_as_templates_and_renders_validate(self) -> None:
        placeholders = {
            "standalone": set(parse_review(
                (REVIEW_ASSETS / "review-standalone.v2.template.md").read_bytes(),
                template=True,
                placeholders={token for token in [
                    "<N>", "<authoritative source>", "<change>", "<fixed base>",
                    "<fixed head>", "<committed range>", "<uncommitted scope>",
                    "<scope notes>", "<reviewer role>", "<reviewer id>",
                    "<implementers>", "<prior participation>", "<independence basis>",
                    "<priority>", "<authority for>", "<gaps or conflicts>",
                    "<risk rationale>", "<required depth and evidence>", "<what>",
                    "<authoritative why>", "<contract scope>", "<required evidence>",
                    "<agent roles>", "<review focus>", "<risk comparison or deviation>",
                    "<missing-contract impact>", "<trigger or N/A reason>", "<evidence>",
                    "<check or procedure>", "<fixed check scope>", "<actual result>",
                    "<requirement or risk>", "<finding records or none>",
                    "<source item or criterion>", "<implementation evidence>",
                    "<check evidence>", "<missing behavior>", "<extra behavior>",
                    "<scope deviations>", "<residual risks>", "<unverified areas>",
                    "<required follow-up>", "<verdict rationale>",
                ]}
            )["placeholders"]),
            "evidence": set(parse_review(
                (REVIEW_ASSETS / "review-with-evidence.v2.template.md").read_bytes(),
                template=True,
                placeholders={"<N>", "<change>", "<finding records or none>",
                              "<acceptance gaps or none>", "<residual risks or none>",
                              "<one exact verdict>", "<verdict rationale>"}
            )["placeholders"]),
        }
        self.assertIn("<N>", placeholders["standalone"])
        for kind, rendered in (("standalone", render_standalone()),
                               ("with-evidence", render_reduced())):
            model = parse_review(rendered)
            owner = load_json(REVIEW_ASSETS / f"review-{kind}.v2.schema.json")
            decision = schema.validate(model, owner, registry=[
                                       load_json(COMMON_SCHEMA)])
            self.assertTrue(decision.valid, decision.as_dict())
            if kind == "standalone":
                review_evidence.validate_standalone_review(
                    model, source=rendered)
            else:
                review_evidence.validate_evidence_review(
                    model, source=rendered, evidence=evidence_record())

    def test_metadata_and_exact_sections_are_closed_without_status(self) -> None:
        standalone = parse_review(render_standalone())
        self.assertEqual(standalone["metadata"], {
            "schema_version": 2, "id": "REVIEW-901", "type": "review-report",
            "sources": ["SPEC-002"], "verdict": "approved",
        })
        self.assertNotIn("status", standalone["metadata"])
        review_evidence.validate_standalone_review(
            standalone, source=render_standalone())
        for field in ("status", "author"):
            changed = copy.deepcopy(standalone)
            changed["metadata"][field] = "draft"
            with self.assertRaises(review_evidence.ReviewEvidenceError):
                review_evidence.validate_standalone_review(
                    changed, source=render_standalone())
        changed = copy.deepcopy(standalone)
        changed["sections"].append("Extra")
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "sections"):
            review_evidence.validate_standalone_review(changed)

    def test_standalone_requires_fixed_scope_independence_nine_signals_and_coverage(self) -> None:
        source = render_standalone()
        model = parse_review(source)
        normalized = review_evidence.validate_standalone_review(
            model, source=source)
        self.assertEqual([item["signal"]
                         for item in normalized["quality_signals"]], SIGNALS)
        mutations = (
            (b"- Fixed base: `72593eb`", b"- Fixed base: ``", "Fixed base"),
            (b"- Independence: `independent`",
             b"- Independence: `self-review`", "independence"),
            (b"| Cost | `selected`", b"| Costly | `selected`", "quality signals"),
            (b"observed evidence", b"invented evidence", "evidence class"),
            (b"| SPEC-002#AC-009 |", b"| AC-009 |", "qualified"),
        )
        for old, new, message in mutations:
            with self.subTest(message=message):
                changed = source.replace(old, new, 1)
                with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, message):
                    review_evidence.validate_standalone_review(
                        parse_review(changed), source=changed)

    def test_findings_severity_and_verdict_effects(self) -> None:
        source = render_standalone().replace(
            b"none\n\n## Acceptance coverage",
            b"### high: Broken contract\n\n- Evidence class: `observed evidence`\n"
            b"- Evidence: Invalid record accepted.\n- Location: `schema.json:1`\n"
            b"- Impact: Acceptance is false.\n- Minimal action: Reject the record.\n\n"
            b"## Acceptance coverage",
        )
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "approved"):
            review_evidence.validate_standalone_review(
                parse_review(source), source=source)
        accepted = source.replace(b'verdict: "approved"', b'verdict: "changes-required"').replace(
            b"Selected verdict: `approved`", b"Selected verdict: `changes-required`")
        review_evidence.validate_standalone_review(
            parse_review(accepted), source=accepted)
        malformed = accepted.replace(b"### high:", b"### urgent:")
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "severity"):
            review_evidence.validate_standalone_review(
                parse_review(malformed), source=malformed)

    def test_reduced_review_has_no_machine_sections_and_matches_evidence(self) -> None:
        record = evidence_record()
        source = render_reduced()
        model = parse_review(source)
        self.assertEqual(model["metadata"]["sources"], ["EVIDENCE-901"])
        self.assertEqual(model["metadata"]
                         ["evidence_reference"], "EVIDENCE-901")
        self.assertTrue(FORBIDDEN_REDUCED.isdisjoint(model["sections"]))
        review_evidence.validate_evidence_review(
            model, source=source, evidence=record)
        for field, value in (("evidence_reference", "EVIDENCE-999"),
                             ("verdict", "approved")):
            changed = copy.deepcopy(model)
            changed["metadata"][field] = value
            with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "evidence|verdict"):
                review_evidence.validate_evidence_review(
                    changed, evidence=record)
        duplicated = source.replace(
            b"## Findings", b"## Scope\n\nduplicate\n\n## Findings")
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "forbidden|sections"):
            review_evidence.validate_evidence_review(parse_review(duplicated), source=duplicated,
                                                     evidence=record)

    def test_effective_risk_rejects_downgrade_and_requires_fresh_independence(self) -> None:
        source = render_standalone()
        self.assertEqual(review_evidence.validate_standalone_review(
            parse_review(source), source=source)["effective_risk"], "high")
        downgraded = source.replace(
            b"Reviewer-assessed risk: `high`", b"Reviewer-assessed risk: `low`")
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError,
                                    "downgrade|contract risk"):
            review_evidence.validate_standalone_review(
                parse_review(downgraded), source=downgraded)
        declared = downgraded.replace(
            b"- Risk comparison/deviation: none",
            b"- Risk comparison/deviation: reviewer low; contract and effective risk high")
        self.assertEqual(review_evidence.validate_standalone_review(
            parse_review(declared), source=declared)["effective_risk"], "high")

        stale = source.replace(b"- Fresh context: `yes`",
                               b"- Fresh context: `no`")
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "fresh"):
            review_evidence.validate_standalone_review(
                parse_review(stale), source=stale)

    def test_field_labels_are_canonical_but_case_insensitive(self) -> None:
        source = render_standalone().replace(
            b"- Contract risk: `high`", b"- cOnTrAcT RiSk: `high`").replace(
            b"- Reviewer-assessed risk: `high`",
            b"- rEvIeWeR-AsSeSsEd RiSk: `high`")
        review_evidence.validate_standalone_review(
            parse_review(source), source=source)
        malformed = source.replace(b"- Fixed base:", b"- Fixed_base:")
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "Fixed base"):
            review_evidence.validate_standalone_review(
                parse_review(malformed), source=malformed)

    def test_met_coverage_requires_same_passed_check_and_compatible_scope(self) -> None:
        source = render_standalone()
        wrong_requirement = source.replace(
            b"| SPEC-002#AC-009 | owner-local assets |",
            b"| SPEC-002#AC-008 | owner-local assets |")
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "same requirement"):
            review_evidence.validate_standalone_review(
                parse_review(wrong_requirement), source=wrong_requirement)
        wrong_link = source.replace(
            b"| SPEC-002#AC-009 | owner-local assets | python3 -m unittest tests.test_review_evidence_contracts |",
            b"| SPEC-002#AC-009 | owner-local assets | unknown-check |")
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "passed check"):
            review_evidence.validate_standalone_review(
                parse_review(wrong_link), source=wrong_link)
        wrong_scope = source.replace(
            b"| python3 -m unittest tests.test_review_evidence_contracts | TASK-208 files |",
            b"| python3 -m unittest tests.test_review_evidence_contracts | OTHER files |")
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "scope"):
            review_evidence.validate_standalone_review(
                parse_review(wrong_scope), source=wrong_scope)

    def test_approved_rejects_missing_required_or_deviated_acceptance(self) -> None:
        source = render_standalone()
        mutations = (
            source.replace(b"- Missing behavior: none",
                           b"- Missing behavior: required behavior"),
            source.replace(b"- Scope deviations: none",
                           b"- Scope deviations: extra file"),
            source.replace(b"- Required follow-up: none",
                           b"- Required follow-up: run required check"),
            source.replace(
                b"| none | `passed` | passed | `observed evidence` |",
                b"| none | not-run | none | `none` |"),
        )
        for changed in mutations:
            with self.subTest(changed=changed[-100:]), self.assertRaisesRegex(
                    review_evidence.ReviewEvidenceError,
                    "approved|required|deviation|passed check|quality signal"):
                review_evidence.validate_standalone_review(
                    parse_review(changed), source=changed)

    def test_reduced_approved_requires_no_gaps_and_rejects_obfuscated_machine_labels(self) -> None:
        record = evidence_record(status="complete", transition="implemented",
                                 verdict="approved")
        pending = render_reduced("approved")
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError,
                                    "Acceptance gaps|pending|required"):
            review_evidence.validate_evidence_review(
                parse_review(pending), source=pending, evidence=record)
        clean = pending.replace(b"Required checks remain pending.", b"none")
        clean = clean.replace(b"Validation is incomplete.", b"none")
        review_evidence.validate_evidence_review(
            parse_review(clean), source=clean, evidence=record)
        for duplicate in (
            b"F.i.x.e.d base: 72593eb", b"F_I_X: 72593eb",
            b"Base revision: 72593eb", b"Baseline revision: 72593eb",
            b"B.a.s.e.l.i.n.e___revision: 72593eb",
            b"AUTHORITATIVE---SOURCES: SPEC-002",
            b"reviewer---i.d.: validator-1", b"CONTRACT_scope: files",
            b"coverage: complete", b"checks: passed",
        ):
            changed = clean.replace(b"## Acceptance gaps\n\nnone",
                                    b"## Acceptance gaps\n\n" + duplicate)
            with self.subTest(duplicate=duplicate), self.assertRaisesRegex(
                    review_evidence.ReviewEvidenceError, "machine fact"):
                review_evidence.validate_evidence_review(
                    parse_review(changed), source=changed, evidence=record)

        randomizer = random.Random(210)
        for _ in range(80):
            separator = randomizer.choice((".", "_", "-", "!", " "))
            words = randomizer.choice(("fixed base", "baseline revision"))
            label = " ".join(separator.join(word)
                             for word in words.split()) + ": 72593eb"
            changed = clean.replace(
                b"## Acceptance gaps\n\nnone",
                b"## Acceptance gaps\n\n" + label.encode("ascii"))
            with self.assertRaises(review_evidence.ReviewEvidenceError):
                review_evidence.validate_evidence_review(
                    parse_review(changed), source=changed, evidence=record)

        prose = render_reduced().replace(
            b"Required checks remain pending.",
            b"Normal prose: risk, sources, and the baseline revision are discussed "
            b"without declaring those machine fields.")
        review_evidence.validate_evidence_review(
            parse_review(prose), source=prose, evidence=evidence_record())

    def test_exact_check_status_signal_support_and_unverified_areas_gate_approval(self) -> None:
        source = render_standalone()
        ambiguous = source.replace(
            b"| none | `passed` | passed | `observed evidence` |",
            b"| none | passed but not-run | passed | `observed evidence` |")
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "status|passed"):
            review_evidence.validate_standalone_review(
                parse_review(ambiguous), source=ambiguous)

        inferred = source.replace(
            b"| none | `passed` | passed | `observed evidence` |",
            b"| none | `passed` | passed | `source-based inference` |")
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError,
                                    "observed evidence|coverage|signal"):
            review_evidence.validate_standalone_review(
                parse_review(inferred), source=inferred)

        unsupported_signal = source.replace(
            b"| Correctness | `selected` | Contract behavior changes. | python3 -m unittest tests.test_review_evidence_contracts |",
            b"| Correctness | `selected` | Contract behavior changes. | unknown-check |")
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "signal"):
            review_evidence.validate_standalone_review(
                parse_review(unsupported_signal), source=unsupported_signal)

        unverified = source.replace(
            b"- Unverified areas: none", b"- Unverified areas: deployment behavior")
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError,
                                    "Unverified|approved"):
            review_evidence.validate_standalone_review(
                parse_review(unverified), source=unverified)

    def test_all_unrelated_checks_obey_status_evidence_and_applicability_matrix(self) -> None:
        base = render_standalone()

        def with_check(row: str) -> bytes:
            return base.replace(
                b"\n## Findings",
                ("\n" + row + "\n\n## Findings").encode("utf-8"),
            )

        valid_rows = (
            "| optional-not-run | TASK-208 files | `no` | `applicable` | none | not-run | none | `none` | SPEC-002#REQ-031 |",
            "| explicit-na | TASK-208 files | `no` | `not-applicable` | Not relevant to this format. | not-applicable | none | `none` | SPEC-002#REQ-031 |",
        )
        for row in valid_rows:
            source = with_check(row)
            review_evidence.validate_standalone_review(
                parse_review(source), source=source)

        invalid_rows = (
            "| inferred-pass | TASK-208 files | `no` | `applicable` | none | passed | Result observed. | `source-based inference` | SPEC-002#REQ-031 |",
            "| inferred-fail | TASK-208 files | `no` | `applicable` | none | failed | Failure observed. | `source-based inference` | SPEC-002#REQ-031 |",
            "| claimed-not-run | TASK-208 files | `no` | `applicable` | none | not-run | Claimed result. | `observed evidence` | SPEC-002#REQ-031 |",
            "| claimed-skipped | TASK-208 files | `no` | `applicable` | none | skipped | Claimed result. | `observed evidence` | SPEC-002#REQ-031 |",
            "| no-reason | TASK-208 files | `no` | `not-applicable` | none | not-applicable | none | `none` | SPEC-002#REQ-031 |",
            "| required-not-run | TASK-208 files | `yes` | `applicable` | none | not-run | none | `none` | SPEC-002#REQ-031 |",
        )
        for row in invalid_rows:
            source = with_check(row)
            with self.subTest(row=row), self.assertRaises(
                    review_evidence.ReviewEvidenceError):
                review_evidence.validate_standalone_review(
                    parse_review(source), source=source)


class EvidenceRecordTests(unittest.TestCase):
    def test_template_and_complete_records_validate_against_schema_and_semantics(self) -> None:
        owner = load_json(EVIDENCE_ASSETS / "evidence.v2.schema.json")
        for record in (evidence_record(), evidence_record(
                status="complete", transition="implemented", verdict="approved")):
            decision = schema.validate(record, owner)
            self.assertTrue(decision.valid, decision.as_dict())
            review_evidence.validate_evidence_record(record)
        self.assertEqual(evidence_record()["schema_version"], 2)
        self.assertEqual(evidence_record()["id"], "EVIDENCE-901")

    def test_closed_fields_source_seals_and_exact_nine_signals(self) -> None:
        record = evidence_record()
        self.assertEqual([item["signal"]
                         for item in record["quality_signals"]], SIGNALS)
        review_evidence.validate_evidence_record(record)
        mutations = []
        extra = copy.deepcopy(record)
        extra["invented"] = True
        mutations.append(extra)
        missing = copy.deepcopy(record)
        del missing["source_seals"]
        mutations.append(missing)
        empty_map = copy.deepcopy(record)
        empty_map["source_seals"][0]["item_digests"] = {}
        mutations.append(empty_map)
        bad_item = copy.deepcopy(record)
        bad_item["source_seals"][0]["item_digests"] = {
            "REQ-001": "sha256:" + "a" * 64}
        mutations.append(bad_item)
        eight = copy.deepcopy(record)
        eight["quality_signals"].pop()
        mutations.append(eight)
        duplicate = copy.deepcopy(record)
        duplicate["quality_signals"][-1]["signal"] = "Correctness"
        mutations.append(duplicate)
        for changed in mutations:
            with self.assertRaises(review_evidence.ReviewEvidenceError):
                review_evidence.validate_evidence_record(changed)

    def test_coverage_checks_truthfulness_and_completion_are_linked(self) -> None:
        complete = evidence_record(
            status="complete", transition="implemented", verdict="approved")
        review_evidence.validate_evidence_record(complete)
        cases = []
        unlinked = copy.deepcopy(complete)
        unlinked["requirement_coverage"][0]["evidence_references"] = [
            "missing-check"]
        cases.append(unlinked)
        failed = copy.deepcopy(complete)
        failed["checks"][0].update(
            {"status": "failed", "observed_result": "failed"})
        cases.append(failed)
        false_result = copy.deepcopy(complete)
        false_result["checks"][0]["evidence_class"] = "unverified claim"
        cases.append(false_result)
        incomplete = copy.deepcopy(complete)
        incomplete["lifecycle"]["status"] = "in-progress"
        cases.append(incomplete)
        for changed in cases:
            with self.assertRaises(review_evidence.ReviewEvidenceError):
                review_evidence.validate_evidence_record(changed)

    def test_high_risk_approval_and_verified_transition_require_independence_and_seals(self) -> None:
        valid = evidence_record(risk="high", status="complete", transition="verified",
                                verdict="approved", independence="independent")
        for identifier, kind in (("regression", "regression"),
                                 ("failure-path", "failure-path"),
                                 ("recovery", "recovery-rollback")):
            required_check = copy.deepcopy(valid["checks"][0])
            required_check.update({"id": identifier, "kind": kind})
            valid["checks"].append(required_check)
            valid["requirement_coverage"][0]["evidence_references"].append(
                identifier)
        review_evidence.validate_evidence_record(valid)
        for mutate in (
            lambda value: value["review"].update({"independence": "self-review",
                                                  "reviewer_id": "declared-implementer",
                                                  "implementers": ["declared-implementer"],
                                                  "prior_participation": ["implementation"],
                                                  "fresh_context": False}),
            lambda value: value.update({"source_seals": []}),
            lambda value: value["review"].update(
                {"reviewer_id": "implementer-1"}),
        ):
            changed = copy.deepcopy(valid)
            mutate(changed)
            with self.assertRaisesRegex(review_evidence.ReviewEvidenceError,
                                        "independent|source seal|implementer"):
                review_evidence.validate_evidence_record(changed)

    def test_medium_and_high_risk_required_check_classes_are_explicit(self) -> None:
        medium = evidence_record(risk="medium", status="complete",
                                 transition="implemented", verdict="approved")
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "regression"):
            review_evidence.validate_evidence_record(medium)
        high = evidence_record(risk="high", status="complete", transition="implemented",
                               verdict="approved", independence="independent")
        for identifier, kind in (("regression", "regression"),
                                 ("failure-path", "failure-path")):
            required_check = copy.deepcopy(high["checks"][0])
            required_check.update({"id": identifier, "kind": kind})
            high["checks"].append(required_check)
            high["requirement_coverage"][0]["evidence_references"].append(
                identifier)
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "recovery-rollback"):
            review_evidence.validate_evidence_record(high)

    def test_malformed_missing_extra_and_limits_fail_without_traceback(self) -> None:
        for value in (None, [], "record"):
            with self.subTest(value=value), self.assertRaises(review_evidence.ReviewEvidenceError):
                review_evidence.validate_evidence_record(value)
        huge = evidence_record()
        huge["follow_ups"] = ["x"] * (review_evidence.MAX_ITEMS + 1)
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "limit"):
            review_evidence.validate_evidence_record(huge)

    def test_change_and_authoritative_source_ids_require_exact_global_seals(self) -> None:
        owner = load_json(EVIDENCE_ASSETS / "evidence.v2.schema.json")
        invalid_change = evidence_record()
        invalid_change["change_id"] = "not global"
        self.assertFalse(schema.validate(invalid_change, owner).valid)
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "change_id|global"):
            review_evidence.validate_evidence_record(invalid_change)

        non_artifact = evidence_record()
        non_artifact["authoritative_sources"][0]["id"] = "accepted-request"
        self.assertFalse(schema.validate(non_artifact, owner).valid)
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "source.*artifact|global"):
            review_evidence.validate_evidence_record(non_artifact)

        missing = evidence_record()
        missing["authoritative_sources"].append(
            {"id": "PLAN-002", "reference": ".work/002-harness-v2/plan.md"})
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "exact.*seal|source seal"):
            review_evidence.validate_evidence_record(missing)

        extra = evidence_record()
        duplicate = copy.deepcopy(extra["source_seals"][0])
        duplicate["artifact_id"] = "PLAN-002"
        duplicate["item_digests"] = {
            "PLAN-002#TASK-208": "sha256:" + "c" * 64}
        extra["source_seals"].append(duplicate)
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "extra|authoritative"):
            review_evidence.validate_evidence_record(extra)

    def test_covered_requirement_requires_exact_passed_check_and_repository_set(self) -> None:
        complete = evidence_record(status="complete", transition="implemented",
                                   verdict="approved")
        cases = []
        wrong_requirement = copy.deepcopy(complete)
        wrong_requirement["checks"][0]["requirement_ids"] = [
            "SPEC-002#REQ-031"]
        cases.append((wrong_requirement, "requirement"))
        wrong_repository = copy.deepcopy(complete)
        wrong_repository["repository_scope"].append(copy.deepcopy(
            wrong_repository["repository_scope"][0]))
        wrong_repository["repository_scope"][1]["repository_id"] = "secondary"
        wrong_repository["requirement_coverage"][0]["repository_ids"] = [
            "current", "secondary"]
        cases.append((wrong_repository, "repository"))
        not_passed = copy.deepcopy(complete)
        not_passed["checks"][0].update({
            "required": False, "status": "not-run", "observed_result": None,
            "evidence_class": None, "output_reference": None})
        cases.append((not_passed, "passed"))
        for changed, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(
                    review_evidence.ReviewEvidenceError, message):
                review_evidence.validate_evidence_record(changed)

    def test_lifecycle_review_consistency_is_bidirectional(self) -> None:
        complete_blocked = evidence_record(status="complete", transition="implemented",
                                           verdict="blocked")
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "complete.*approved"):
            review_evidence.validate_evidence_record(complete_blocked)
        implemented_in_progress = evidence_record()
        implemented_in_progress["lifecycle"]["transition"] = "implemented"
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError,
                                    "transition|complete"):
            review_evidence.validate_evidence_record(implemented_in_progress)

    def test_recursive_surrogates_controls_and_fuzz_raise_only_typed_errors(self) -> None:
        owner = load_json(EVIDENCE_ASSETS / "evidence.v2.schema.json")
        for field_value in ("bad\ud800", "bad\x00", "bad\x7f"):
            changed = evidence_record()
            changed["follow_ups"] = [field_value]
            self.assertFalse(schema.validate(changed, owner).valid)
            with self.assertRaises(review_evidence.ReviewEvidenceError):
                review_evidence.validate_evidence_record(changed)
        changed = evidence_record()
        changed["source_seals"][0]["item_digests"]["bad\udfff"] = "sha256:" + "c" * 64
        with self.assertRaises(review_evidence.ReviewEvidenceError):
            review_evidence.validate_evidence_record(changed)

        randomizer = random.Random(208)
        atoms: list[object] = [None, True, 1, 1.5, "", "x", "\ud800", b"bytes"]
        for _ in range(200):
            candidate = randomizer.choice(atoms + [
                [randomizer.choice(atoms)], {"x": randomizer.choice(atoms)},
            ])
            try:
                review_evidence.validate_evidence_record(candidate)
            except review_evidence.ReviewEvidenceError:
                pass
            except Exception as exc:  # pragma: no cover - assertion reports the type
                self.fail(f"unexpected exception {type(exc).__name__}: {exc}")

    def test_high_risk_required_kinds_and_selected_signals_need_real_evidence(self) -> None:
        high = evidence_record(risk="high", status="complete", transition="verified",
                               verdict="approved", independence="independent")
        for identifier, kind in (("regression", "regression"),
                                 ("failure-path", "failure-path"),
                                 ("recovery", "recovery-rollback")):
            required_check = copy.deepcopy(high["checks"][0])
            required_check.update({"id": identifier, "kind": kind})
            high["checks"].append(required_check)
            high["requirement_coverage"][0]["evidence_references"].append(
                identifier)
        review_evidence.validate_evidence_record(high)

        optional_regression = copy.deepcopy(high)
        next(item for item in optional_regression["checks"]
             if item["kind"] == "regression").update({
                 "required": False, "status": "not-run", "observed_result": None,
                 "evidence_class": None, "output_reference": None})
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "regression"):
            review_evidence.validate_evidence_record(optional_regression)

        incomplete_failure = copy.deepcopy(high)
        next(item for item in incomplete_failure["checks"]
             if item["kind"] == "failure-path").update({
                 "required": False, "status": "not-run", "observed_result": None,
                 "evidence_class": None, "output_reference": None})
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "failure-path"):
            review_evidence.validate_evidence_record(incomplete_failure)

        explicit_na = copy.deepcopy(high)
        for kind in ("regression", "failure-path", "recovery-rollback"):
            next(item for item in explicit_na["checks"] if item["kind"] == kind).update({
                "required": False, "applicability": "not-applicable",
                "not_applicable_reason": f"{kind} does not apply to this bounded format change.",
                "status": "not-applicable", "observed_result": None,
                "evidence_class": None, "output_reference": None})
        review_evidence.validate_evidence_record(explicit_na)

        optional = copy.deepcopy(high["checks"][0])
        optional.update({
            "id": "optional-not-run", "kind": "other", "required": False,
            "status": "not-run", "observed_result": None, "evidence_class": None,
            "output_reference": None})
        unsupported_signal = copy.deepcopy(high)
        unsupported_signal["checks"].append(optional)
        unsupported_signal["quality_signals"][0].update({
            "disposition": "selected", "trigger": "Correctness is applicable.",
            "evidence_references": ["scoped-check", "optional-not-run"],
        })
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "quality signal"):
            review_evidence.validate_evidence_record(unsupported_signal)

        duplicate_ref = copy.deepcopy(high)
        duplicate_ref["quality_signals"][0].update({
            "disposition": "selected", "trigger": "Correctness is applicable.",
            "evidence_references": ["scoped-check", "scoped-check"],
        })
        with self.assertRaises(review_evidence.ReviewEvidenceError):
            review_evidence.validate_evidence_record(duplicate_ref)
        unknown_ref = copy.deepcopy(high)
        unknown_ref["quality_signals"][0].update({
            "disposition": "selected", "trigger": "Correctness is applicable.",
            "evidence_references": ["missing-check"],
        })
        with self.assertRaises(review_evidence.ReviewEvidenceError):
            review_evidence.validate_evidence_record(unknown_ref)


class AuditEventTests(unittest.TestCase):
    def test_template_schema_and_valid_canonical_jsonl(self) -> None:
        template = load_json(COMPLIANCE_V2_ASSETS /
                             "audit-event.v2.template.json")
        self.assertEqual(template["action"], "change-started")
        value = event(1, "2025-01-01T00:00:00Z")
        owner = load_json(COMPLIANCE_V2_ASSETS / "audit-event.v2.schema.json")
        self.assertTrue(schema.validate(value, owner).valid)
        result = review_evidence.validate_audit_jsonl(
            audit_text(value), evidence=evidence_record())
        self.assertEqual(result, [value])
        self.assertNotIn("planned", json.dumps(owner))

    def test_sequence_timestamp_event_identity_and_change_consistency(self) -> None:
        first = event(1, "2025-01-01T00:00:00Z")
        second = event(2, "2025-01-01T00:00:01Z")
        review_evidence.validate_audit_jsonl(
            audit_text(first, second), evidence=evidence_record())
        mutations = (
            (lambda a, b: b.update({"sequence": 3}), "contiguous"),
            (lambda a, b: b.update(
                {"timestamp": a["timestamp"]}), "timestamp"),
            (lambda a, b: b.update({"event_id": a["event_id"]}), "event"),
            (lambda a, b: b.update({"change_id": "OTHER"}), "change"),
        )
        for mutate, message in mutations:
            a, b = copy.deepcopy(first), copy.deepcopy(second)
            mutate(a, b)
            with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, message):
                review_evidence.validate_audit_jsonl(
                    audit_text(a, b), evidence=evidence_record())

    def test_real_utc_and_legal_transition_matrix_without_planned(self) -> None:
        allowed = {("draft", "approved"), ("approved", "implemented"),
                   ("implemented", "verified")}
        states = ("draft", "approved", "implemented", "verified")
        for before in states:
            for after in states:
                value = event(1, "2024-02-29T23:59:59Z", action="lifecycle-transition",
                              previous=before, new=after)
                if (before, after) in allowed:
                    linked = evidence_record()
                    if after == "implemented":
                        linked = evidence_record(status="complete", transition="implemented",
                                                 verdict="approved")
                    elif after == "verified":
                        linked = evidence_record(status="complete", transition="verified",
                                                 verdict="approved", independence="independent")
                    review_evidence.validate_audit_jsonl(
                        audit_text(value), evidence=linked)
                else:
                    with self.assertRaisesRegex(review_evidence.ReviewEvidenceError,
                                                "transition"):
                        review_evidence.validate_audit_jsonl(audit_text(value),
                                                             evidence=evidence_record())
        for invalid in ("2023-02-29T00:00:00Z", "2025-01-01T24:00:00Z",
                        "2025-01-01T00:00:00+00:00"):
            with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "timestamp"):
                review_evidence.validate_audit_jsonl(audit_text(event(1, invalid)),
                                                     evidence=evidence_record())

    def test_actors_approvals_references_and_repository_revisions_match_evidence(self) -> None:
        valid = event(1, "2025-01-01T00:00:00Z")
        valid["approvals"] = [{"actor_id": "validator-1", "role": "reviewer",
                               "reference": "review.md"}]
        review_evidence.validate_audit_jsonl(
            audit_text(valid), evidence=evidence_record())
        mutations = (
            lambda value: value["approvals"].append(
                copy.deepcopy(value["approvals"][0])),
            lambda value: value["authoritative_source_references"].__setitem__(
                0, "UNKNOWN"),
            lambda value: value["evidence_references"].__setitem__(
                0, "other.json"),
            lambda value: value["repositories"][0].update(
                {"repository_id": "other"}),
            lambda value: value["repositories"][0].update(
                {"revision": "mutable"}),
        )
        for mutate in mutations:
            changed = copy.deepcopy(valid)
            mutate(changed)
            with self.assertRaises(review_evidence.ReviewEvidenceError):
                review_evidence.validate_audit_jsonl(
                    audit_text(changed), evidence=evidence_record())

        self_approval = copy.deepcopy(valid)
        self_approval["approvals"] = [
            {"actor_id": "declared-actor", "role": "implementer", "reference": "review.md"}]
        with self.assertRaises(review_evidence.ReviewEvidenceError):
            review_evidence.validate_audit_jsonl(
                audit_text(self_approval), evidence=evidence_record())

        high = evidence_record(risk="high", status="complete", transition="verified",
                               verdict="approved", independence="independent")
        for identifier, kind in (("regression", "regression"),
                                 ("failure-path", "failure-path"),
                                 ("recovery", "recovery-rollback")):
            required_check = copy.deepcopy(high["checks"][0])
            required_check.update({"id": identifier, "kind": kind})
            high["checks"].append(required_check)
            high["requirement_coverage"][0]["evidence_references"].append(
                identifier)
        verified = event(1, "2025-01-01T00:00:00Z", action="lifecycle-transition",
                         previous="implemented", new="verified")
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "approval"):
            review_evidence.validate_audit_jsonl(
                audit_text(verified), evidence=high)

    def test_canonical_compact_serialization_and_duplicate_json_keys_are_required(self) -> None:
        value = event(1, "2025-01-01T00:00:00Z")
        canonical = audit_text(value)
        self.assertNotIn(": ", canonical)
        pretty = json.dumps(value, indent=2) + "\n"
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "one compact|canonical"):
            review_evidence.validate_audit_jsonl(
                pretty, evidence=evidence_record())
        duplicate = canonical.replace(
            '"sequence":1', '"sequence":1,"sequence":1')
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "duplicate"):
            review_evidence.validate_audit_jsonl(
                duplicate, evidence=evidence_record())

    def test_no_crypto_or_legal_claim_is_accepted(self) -> None:
        for claim in ("cryptographic proof", "legally certified", "authenticated identity"):
            value = event(1, "2025-01-01T00:00:00Z")
            value["action"] = "evidence-updated"
            value["approvals"] = [{"actor_id": "validator-1", "role": "reviewer",
                                   "reference": claim}]
            with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "claim"):
                review_evidence.validate_audit_jsonl(
                    audit_text(value), evidence=evidence_record())

    def test_event_and_change_ids_actions_and_transition_continuity_are_closed(self) -> None:
        valid_actions = {
            "evidence-updated", "lifecycle-transition", "review-recorded",
            "approval-recorded", "check-recorded", "task-state-changed", "change-started",
        }
        owner = load_json(COMPLIANCE_V2_ASSETS / "audit-event.v2.schema.json")
        self.assertEqual(
            set(owner["properties"]["action"]["enum"]), valid_actions)
        for action in valid_actions - {"lifecycle-transition"}:
            value = event(1, "2025-01-01T00:00:00Z", action=action)
            review_evidence.validate_audit_jsonl(
                audit_text(value), evidence=evidence_record())
        for field, invalid in (("event_id", "bad-event"), ("change_id", "not global"),
                               ("action", "invented-action")):
            value = event(1, "2025-01-01T00:00:00Z")
            value[field] = invalid
            self.assertFalse(schema.validate(value, owner).valid)
            with self.subTest(field=field), self.assertRaises(
                    review_evidence.ReviewEvidenceError):
                review_evidence.validate_audit_jsonl(audit_text(value),
                                                     evidence=evidence_record())

        first = event(1, "2025-01-01T00:00:00Z", action="lifecycle-transition",
                      previous="draft", new="approved")
        disconnected = event(2, "2025-01-01T00:00:01Z", action="lifecycle-transition",
                             previous="implemented", new="verified")
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "continuity"):
            review_evidence.validate_audit_jsonl(
                audit_text(first, disconnected))
        middle = event(2, "2025-01-01T00:00:01Z", action="review-recorded")
        last = event(3, "2025-01-01T00:00:02Z", action="lifecycle-transition",
                     previous="approved", new="implemented")
        review_evidence.validate_audit_jsonl(audit_text(first, middle, last))

    def test_event_actor_cannot_approve_same_event_and_high_verified_matches_reviewer(self) -> None:
        same_actor = event(1, "2025-01-01T00:00:00Z")
        same_actor["approvals"] = [{
            "actor_id": same_actor["actor"]["actor_id"], "role": "reviewer",
            "reference": "review.md"}]
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "actor|self"):
            review_evidence.validate_audit_jsonl(
                audit_text(same_actor), evidence=evidence_record())

        high = evidence_record(risk="high", status="complete", transition="verified",
                               verdict="approved", independence="independent")
        for identifier, kind in (("regression", "regression"),
                                 ("failure-path", "failure-path"),
                                 ("recovery", "recovery-rollback")):
            required_check = copy.deepcopy(high["checks"][0])
            required_check.update({"id": identifier, "kind": kind})
            high["checks"].append(required_check)
            high["requirement_coverage"][0]["evidence_references"].append(
                identifier)
        verified = event(1, "2025-01-01T00:00:00Z", action="lifecycle-transition",
                         previous="implemented", new="verified")
        verified["approvals"] = [{
            "actor_id": "other-validator", "role": "reviewer", "reference": "review.md"}]
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "reviewer"):
            review_evidence.validate_audit_jsonl(
                audit_text(verified), evidence=high)
        verified["approvals"][0]["actor_id"] = high["review"]["reviewer_id"]
        verified["approvals"][0]["reference"] = "unresolved-approval.md"
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError,
                                    "reference|approval|reviewer"):
            review_evidence.validate_audit_jsonl(
                audit_text(verified), evidence=high)
        randomizer = random.Random(211)
        for _ in range(40):
            unresolved = copy.deepcopy(verified)
            unresolved["approvals"][0]["reference"] = (
                f"unresolved-{randomizer.randrange(1_000_000)}.md")
            with self.assertRaises(review_evidence.ReviewEvidenceError):
                review_evidence.validate_audit_jsonl(
                    audit_text(unresolved), evidence=high)
        verified["approvals"][0]["reference"] = "review.md"
        verified["approvals"].insert(0, {
            "actor_id": "advisory-validator", "role": "reviewer",
            "reference": "unresolved-advisory.md"})
        review_evidence.validate_audit_jsonl(
            audit_text(verified), evidence=high)

    def test_utf8_byte_limit_surrogates_keys_and_fuzz_never_leak_unicode_errors(self) -> None:
        value = event(1, "2025-01-01T00:00:00Z")
        value["actor"]["actor_id"] = "bad\ud800"
        with self.assertRaises(review_evidence.ReviewEvidenceError):
            review_evidence.canonical_audit_event(value)
        raw = audit_text(event(1, "2025-01-01T00:00:00Z"))
        surrogate = raw.replace("declared-actor", "bad\\ud800")
        with self.assertRaises(review_evidence.ReviewEvidenceError):
            review_evidence.validate_audit_jsonl(surrogate)
        duplicate_key_surrogate = raw.replace(
            '"actor_id":', '"bad\\udfff":1,"actor_id":')
        with self.assertRaises(review_evidence.ReviewEvidenceError):
            review_evidence.validate_audit_jsonl(duplicate_key_surrogate)
        oversized = "é" * (review_evidence.MAX_AUDIT_BYTES // 2 + 1)
        with self.assertRaisesRegex(review_evidence.ReviewEvidenceError, "byte limit"):
            review_evidence.validate_audit_jsonl(oversized)

        randomizer = random.Random(209)
        for _ in range(200):
            candidate: object = randomizer.choice([
                None, [], {}, "x", {"event_id": "\ud800"},
                event(1, "2025-01-01T00:00:00Z"),
            ])
            try:
                review_evidence.canonical_audit_event(candidate)
            except review_evidence.ReviewEvidenceError:
                pass
            except Exception as exc:  # pragma: no cover - assertion reports the type
                self.fail(f"unexpected exception {type(exc).__name__}: {exc}")


class CatalogAndBoundaryTests(unittest.TestCase):
    def test_catalog_variants_are_owner_local_ordered_and_v1_bases_stay_active(self) -> None:
        data = catalog.load_artifact_catalog(ROOT)
        entries = {entry["id"]: entry for entry in data["artifacts"]}
        expected = {
            "review-report": ["evidence-v2", "standalone-v2"],
            "evidence-record": ["v2"],
            "compliance-event": ["v2"],
        }
        resolved = {
            item.id: item for item in catalog.resolve_artifact_contracts(ROOT, data)}
        for identifier, ids in expected.items():
            entry = entries[identifier]
            self.assertEqual(entry["writable_schema_version"], 2)
            self.assertEqual([item["id"] for item in entry["variants"]], ids)
            self.assertEqual(
                [item.id for item in resolved[identifier].variants], ids)
            for variant in resolved[identifier].variants:
                self.assertTrue(
                    variant.template and variant.template.is_file())
                self.assertTrue(variant.schema and variant.schema.is_file())
                self.assertTrue(variant.template.is_relative_to(
                    resolved[identifier].owner_directory))
                self.assertTrue(variant.schema.is_relative_to(
                    resolved[identifier].owner_directory))
        reduced = entries["review-report"]["variants"][0]
        self.assertEqual(reduced["requires_modules"], ["evidence"])
        self.assertEqual(set(reduced["forbids_sections"]), FORBIDDEN_REDUCED)
        self.assertEqual(entries["evidence-record"]["variants"][0]["requires_modules"],
                         ["evidence"])
        self.assertEqual(entries["compliance-event"]["variants"][0]["requires_modules"],
                         ["compliance", "enforcement", "evidence"])

    def test_all_format_catalog_gate_resolves_every_v2_variant(self) -> None:
        resolved = catalog.resolve_artifact_contracts(ROOT)
        variants = [
            variant for artifact in resolved for variant in artifact.variants]
        self.assertGreaterEqual(len(variants), 13)
        for variant in variants:
            if variant.schema is not None:
                contract = load_json(variant.schema)
                self.assertEqual(contract["$schema"], schema.DIALECT)
                self.assertNotIn("schema.unsupported_keyword", {
                    item.code for item in schema.validate({}, contract).diagnostics})

    def test_source_only_module_has_no_io_dynamic_import_or_traceback_surface(self) -> None:
        path = ROOT / "scripts" / "contracts" / "review_evidence.py"
        tree = ast.parse(path.read_text())
        imports = {alias.name.split(".")[0] for node in ast.walk(tree)
                   if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
        self.assertTrue(imports.isdisjoint({"os", "pathlib", "socket", "subprocess",
                                           "urllib", "requests"}))
        calls = {node.func.id for node in ast.walk(tree)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertTrue(calls.isdisjoint(
            {"eval", "exec", "open", "__import__"}))

    def test_unrelated_v1_assets_and_active_catalog_pointers_are_unchanged(self) -> None:
        for path, expected in V1_HASHES.items():
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256(
                    path.read_bytes()).hexdigest(), expected)
        entries = {entry["id"]: entry for entry in catalog.load_artifact_catalog(ROOT)[
            "artifacts"]}
        self.assertTrue(entries["review-report"]
                        ["template"].endswith("review.template.md"))
        self.assertTrue(entries["evidence-record"]
                        ["template"].endswith("evidence.template.json"))
        self.assertTrue(entries["compliance-event"]
                        ["template"].endswith("audit-event.template.json"))


if __name__ == "__main__":
    unittest.main()

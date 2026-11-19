from __future__ import annotations

import ast
import copy
import hashlib
import json
import random
import subprocess
import unittest
from pathlib import Path

from scripts.contracts import catalog, domain_artifacts, markdown, schema


ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / ".agents"
ASSETS = AGENTS / "skills" / "domain-model" / "assets"
COMMON_SCHEMA = AGENTS / "schemas" / "markdown-document.schema.json"
ALLOWED_METADATA = {
    "schema_version", "id", "type", "sources", "status", "date",
    "supersedes", "superseded_by",
}
ADR_PLACEHOLDERS = {
    "<NNN>", "<authoritative source link or confirmed input>", "<YYYY-MM-DD>",
    "<decision title>",
    "<Confirmed forces and background that make the decision necessary.>",
    "<The architecture decision.>",
    "<Material benefits, costs, risks, and constraints caused by the decision.>",
}
GLOSSARY_PLACEHOLDERS = {
    "<NNN>", "<authoritative source link or confirmed input>",
    "<Domain context title>", "<canonical term>",
    "<confirmed canonical meaning>", "<source for this meaning>",
}
V1_HASHES = {
    ASSETS / "adr.template.md":
        "6ac2ac3d9566ec007eb57aca15295a0325d2b37d12d1233a8a3db4ef8e3013af",
    ASSETS / "glossary.template.md":
        "2616ee058b9e0a08923240c2e900ccd611b14892fd09d7db049fb08572cdaa41",
}


def load_json(path: Path) -> dict[str, object]:
    return catalog.load_json(path)


def registry() -> list[dict[str, object]]:
    return [load_json(COMMON_SCHEMA)]


def parse(source: bytes | str) -> dict[str, object]:
    return markdown.parse_markdown(
        source, allowed_metadata_keys=ALLOWED_METADATA, mode="rendered")


def owner_decision(kind: str, model: object) -> schema.ValidationResult:
    return schema.validate(
        model, load_json(ASSETS / f"{kind}.v2.schema.json"), registry=registry())


def render_adr(
    identifier: str = "ADR-901", *, status: str = "proposed",
    date: str = "2024-02-29", supersedes: list[str] | None = None,
    superseded_by: str | None = None, source_ref: str = "confirmed request",
    source_refs: list[str] | None = None,
    body_reference: str = "SPEC-901#REQ-001",
) -> bytes:
    text = (ASSETS / "adr.v2.template.md").read_text(encoding="utf-8")
    sources = source_refs if source_refs is not None else [source_ref]
    replacements = {
        "ADR-<NNN>": identifier,
        'sources: ["<authoritative source link or confirmed input>"]':
            "sources: " + json.dumps(sources),
        'status: "proposed"': f'status: "{status}"',
        'date: "<YYYY-MM-DD>"': f'date: "{date}"',
        "supersedes: []": "supersedes: " + json.dumps(supersedes or []),
        "superseded_by: null": "superseded_by: " + json.dumps(superseded_by),
        "<decision title>": "Choose a bounded contract",
        "<Confirmed forces and background that make the decision necessary.>":
            f"A durable boundary is required by {body_reference}.",
        "<The architecture decision.>": "Use one explicit owner-local contract.",
        "<Material benefits, costs, risks, and constraints caused by the decision.>":
            "The boundary is clear but requires maintenance.",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode("utf-8")


def adr_model(*args: object, **kwargs: object) -> dict[str, object]:
    return parse(render_adr(*args, **kwargs))


def term_block(
    term: str, *, meaning: str = "A confirmed domain boundary.",
    relationships: str = "none", synonyms: str = "none",
    source: str = "confirmed request",
) -> str:
    return (
        f"### {term}\n\n"
        f"- Meaning: {meaning}\n"
        f"- Relationships: {relationships}\n"
        f"- Rejected ambiguous synonyms: {synonyms}\n"
        f"- Source: {source}"
    )


def render_glossary(
    terms: list[str] | None = None, *, identifier: str = "GLOSSARY-901",
    status: str = "draft", source_ref: str = "confirmed request",
    source_refs: list[str] | None = None,
) -> bytes:
    records = terms if terms is not None else [term_block("Account")]
    sources = source_refs if source_refs is not None else [source_ref]
    return (
        "---\n"
        "schema_version: 2\n"
        f'id: "{identifier}"\n'
        'type: "domain-context"\n'
        f"sources: {json.dumps(sources)}\n"
        f'status: "{status}"\n'
        "---\n\n"
        "# Billing domain context\n\n"
        "## Terms\n\n"
        + "\n\n".join(records)
        + "\n"
    ).encode("utf-8")


def glossary_model(source: bytes | str) -> dict[str, object]:
    return parse(source)


class TemplateAndSchemaTests(unittest.TestCase):
    def test_templates_parse_only_in_declared_mode_and_renders_validate(self) -> None:
        cases = (
            ("adr", ADR_PLACEHOLDERS, render_adr()),
            ("glossary", GLOSSARY_PLACEHOLDERS, render_glossary()),
        )
        for kind, placeholders, rendered in cases:
            with self.subTest(kind=kind):
                template = ASSETS / f"{kind}.v2.template.md"
                model = markdown.parse_markdown(
                    template.read_bytes(), allowed_metadata_keys=ALLOWED_METADATA,
                    mode="template", declared_placeholders=placeholders)
                self.assertEqual(set(model["placeholders"]), placeholders)
                decision = owner_decision(kind, model)
                self.assertTrue(decision.valid, decision.as_dict())
                with self.assertRaisesRegex(markdown.MarkdownError, "placeholder"):
                    parse(template.read_bytes())
                rendered_model = parse(rendered)
                decision = owner_decision(kind, rendered_model)
                self.assertTrue(decision.valid, decision.as_dict())
                if kind == "adr":
                    domain_artifacts.validate_adr_model(
                        rendered_model, source=rendered)
                else:
                    normalized = domain_artifacts.validate_glossary_model(
                        rendered_model, source=rendered)
                    self.assertEqual([item["term"] for item in normalized["terms"]],
                                     ["Account"])

    def test_owner_metadata_is_closed_and_required(self) -> None:
        for kind, valid in (("adr", adr_model()),
                            ("glossary", glossary_model(render_glossary()))):
            with self.subTest(kind=kind):
                changed = copy.deepcopy(valid)
                changed["metadata"]["author"] = "invented"
                self.assertFalse(owner_decision(kind, changed).valid)
                changed = copy.deepcopy(valid)
                del changed["metadata"]["sources"]
                self.assertFalse(owner_decision(kind, changed).valid)
                changed = copy.deepcopy(valid)
                changed["metadata"]["sources"] = []
                self.assertFalse(owner_decision(kind, changed).valid)
        glossary = glossary_model(render_glossary())
        glossary["metadata"]["date"] = "2024-01-01"
        self.assertFalse(owner_decision("glossary", glossary).valid)
        for forbidden in ("updated", "title", "author"):
            self.assertNotIn(forbidden, adr_model()["metadata"])

    def test_identity_status_h1_and_local_namespace_are_closed(self) -> None:
        mutations = (
            ("adr", adr_model(), "id", "DECISION-901"),
            ("adr", adr_model(), "type", "adr"),
            ("adr", adr_model(), "status", "draft"),
            ("glossary", glossary_model(render_glossary()), "id", "TERM-901"),
            ("glossary", glossary_model(render_glossary()), "type", "glossary"),
            ("glossary", glossary_model(render_glossary()), "status", "proposed"),
        )
        for kind, model, field, value in mutations:
            with self.subTest(kind=kind, field=field):
                model["metadata"][field] = value
                self.assertFalse(owner_decision(kind, model).valid)
        changed = adr_model()
        changed["h1"] = "A title without its ADR ID"
        self.assertFalse(owner_decision("adr", changed).valid)
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError, "H1"):
            domain_artifacts.validate_adr_model(changed)
        changed = adr_model()
        changed["h1"] = "ADR-901:  noncanonical spacing"
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError, "H1"):
            domain_artifacts.validate_adr_model(changed)
        model = glossary_model(render_glossary())
        self.assertEqual(model["local_ids"], [])
        self.assertNotIn("TERM-", render_glossary().decode())

    def test_common_metadata_schema_declares_only_needed_adr_fields(self) -> None:
        common = load_json(COMMON_SCHEMA)
        properties = common["$defs"]["metadata"]["properties"]
        self.assertIn("supersedes", properties)
        self.assertIn("superseded_by", properties)
        for field in ("updated", "title", "author"):
            self.assertNotIn(field, properties)

    def test_qualified_references_are_valid_and_local_references_fail(self) -> None:
        valid_source = render_adr(body_reference="SPEC-901#REQ-002")
        valid = parse(valid_source)
        self.assertTrue(owner_decision("adr", valid).valid)
        domain_artifacts.validate_adr_model(valid, source=valid_source)

        local_source = render_adr(body_reference="REQ-002")
        local = parse(local_source)
        self.assertFalse(owner_decision("adr", local).valid)
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError, "qualified"):
            domain_artifacts.validate_adr_model(local, source=local_source)
        source_model = adr_model()
        source_model["metadata"]["sources"] = ["REQ-002"]
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError, "local references"):
            domain_artifacts.validate_adr_model(source_model)


class LifecycleAndDateTests(unittest.TestCase):
    def test_every_adr_transition_pair(self) -> None:
        expected = {
            ("proposed", "accepted"),
            ("accepted", "deprecated"),
            ("accepted", "superseded"),
        }
        states = ("proposed", "accepted", "deprecated", "superseded")
        for before in states:
            for after in states:
                with self.subTest(before=before, after=after):
                    self.assertEqual(domain_artifacts.transition_allowed(
                        "architecture-decision", before, after),
                        (before, after) in expected)

    def test_every_glossary_transition_pair_and_archived_is_terminal(self) -> None:
        expected = {("draft", "active"), ("active", "archived")}
        states = ("draft", "active", "archived")
        for before in states:
            for after in states:
                with self.subTest(before=before, after=after):
                    self.assertEqual(domain_artifacts.transition_allowed(
                        "domain-context", before, after),
                        (before, after) in expected)
        for after in states:
            self.assertFalse(domain_artifacts.transition_allowed(
                "domain-context", "archived", after))

    def test_transition_failures_are_typed(self) -> None:
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError, "forbidden"):
            domain_artifacts.require_transition(
                "architecture-decision", "proposed", "superseded")
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError, "strings"):
            domain_artifacts.transition_allowed(
                "domain-context", None, "active")
        self.assertFalse(domain_artifacts.transition_allowed(
            "unknown", "draft", "active"))

    def test_dates_require_real_canonical_calendar_days(self) -> None:
        for valid in ("2024-02-29", "2000-02-29", "0001-01-01", "9999-12-31"):
            with self.subTest(valid=valid):
                source = render_adr(date=valid)
                model = parse(source)
                self.assertTrue(owner_decision("adr", model).valid)
                domain_artifacts.validate_adr_model(model, source=source)
        for invalid in ("2023-02-29", "1900-02-29", "2024-04-31", "0000-01-01"):
            with self.subTest(invalid=invalid):
                model = adr_model(date=invalid)
                with self.assertRaisesRegex(domain_artifacts.DomainArtifactError,
                                            "real date"):
                    domain_artifacts.validate_adr_model(model)
        for malformed in ("2024-2-09", "2024-02-9", "24-02-09"):
            with self.subTest(malformed=malformed):
                model = adr_model(date=malformed)
                self.assertFalse(owner_decision("adr", model).valid)
                with self.assertRaisesRegex(domain_artifacts.DomainArtifactError,
                                            "YYYY-MM-DD"):
                    domain_artifacts.validate_adr_model(model)


class AdrSemanticTests(unittest.TestCase):
    def test_core_is_required_and_optional_sections_have_one_canonical_order(self) -> None:
        source = render_adr()
        minimal = parse(source)
        domain_artifacts.validate_adr_model(minimal, source=source)
        optional = (
            "## Alternatives\n\nUse a shared mutable record.\n\n"
            "## Confirmed rationale\n\nConfirmed by the source.\n\n"
            "## Repository evidence\n\nOne owner exists.\n\n"
            "## Agent inference\n\nThe boundary should remain small.\n\n"
            "## Unknowns\n\nFuture scale is unknown.\n\n"
        )
        full_source = source.replace(
            b"## Consequences\n", optional.encode() + b"## Consequences\n")
        full = parse(full_source)
        self.assertTrue(owner_decision("adr", full).valid)
        domain_artifacts.validate_adr_model(full, source=full_source)

        missing = copy.deepcopy(minimal)
        missing["sections"].remove("Decision")
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError, "requires"):
            domain_artifacts.validate_adr_model(missing)
        wrong = copy.deepcopy(full)
        wrong["sections"][1], wrong["sections"][2] = (
            wrong["sections"][2], wrong["sections"][1])
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError,
                                    "canonical order"):
            domain_artifacts.validate_adr_model(wrong)

    def test_empty_present_sections_and_source_model_mismatch_fail(self) -> None:
        source = render_adr().replace(
            b"## Decision\n\nUse one explicit owner-local contract.\n",
            b"## Decision\n")
        model = parse(source)
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError, "non-empty"):
            domain_artifacts.validate_adr_model(model, source=source)
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError, "does not match"):
            domain_artifacts.validate_adr_model(
                adr_model(), source=render_adr("ADR-902"))

    def test_valid_multi_supersession_is_reciprocal_and_sorted(self) -> None:
        old_a = adr_model("ADR-101", status="superseded",
                          superseded_by="ADR-300")
        old_b = adr_model("ADR-202", status="superseded",
                          superseded_by="ADR-300")
        replacement = adr_model(
            "ADR-300", status="accepted", supersedes=["ADR-101", "ADR-202"])
        result = domain_artifacts.validate_adr_set(
            [replacement, old_b, old_a])
        self.assertEqual([item["metadata"]["id"] for item in result],
                         ["ADR-101", "ADR-202", "ADR-300"])

    def test_missing_and_nonreciprocal_supersession_fail(self) -> None:
        cases = (
            ([adr_model("ADR-101", status="superseded",
                        superseded_by="ADR-300")], "replacement is missing"),
            ([adr_model("ADR-101", status="superseded", superseded_by="ADR-300"),
              adr_model("ADR-300", status="accepted")], "not reciprocal"),
            ([adr_model("ADR-300", status="accepted",
                        supersedes=["ADR-101"])], "target is missing"),
            ([adr_model("ADR-101"),
              adr_model("ADR-300", status="accepted",
                        supersedes=["ADR-101"])], "not reciprocal"),
        )
        for values, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(
                    domain_artifacts.DomainArtifactError, message):
                domain_artifacts.validate_adr_set(values)

    def test_self_duplicate_and_cycle_fail(self) -> None:
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError, "itself"):
            domain_artifacts.validate_adr_model(
                adr_model("ADR-101", status="accepted", supersedes=["ADR-101"]))
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError, "duplicate ADR"):
            domain_artifacts.validate_adr_set([adr_model(), adr_model()])
        first = adr_model("ADR-101", status="superseded",
                          supersedes=["ADR-202"], superseded_by="ADR-202")
        second = adr_model("ADR-202", status="superseded",
                           supersedes=["ADR-101"], superseded_by="ADR-101")
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError, "cycle"):
            domain_artifacts.validate_adr_set([first, second])

    def test_superseded_by_is_status_dependent(self) -> None:
        for status in ("proposed", "accepted", "deprecated"):
            with self.subTest(status=status):
                model = adr_model(status=status, superseded_by="ADR-999")
                self.assertFalse(owner_decision("adr", model).valid)
                with self.assertRaisesRegex(domain_artifacts.DomainArtifactError, "null"):
                    domain_artifacts.validate_adr_model(model)
        model = adr_model(status="superseded")
        self.assertFalse(owner_decision("adr", model).valid)
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError, "replacement"):
            domain_artifacts.validate_adr_model(model)


class GlossarySemanticTests(unittest.TestCase):
    def validate(self, source: bytes | str) -> dict[str, object]:
        model = parse(source)
        decision = owner_decision("glossary", model)
        self.assertTrue(decision.valid, decision.as_dict())
        return domain_artifacts.validate_glossary_model(model, source=source)

    def test_valid_terms_relations_synonyms_and_normalized_output(self) -> None:
        source = render_glossary([
            term_block("Account", relationships="Invoice",
                       synonyms="Customer account"),
            term_block("Invoice", synonyms="Bill", source="SPEC-901#REQ-001"),
        ], status="active")
        result = self.validate(source)
        self.assertEqual([item["term"] for item in result["terms"]],
                         ["Account", "Invoice"])
        self.assertEqual(result["terms"][0]["relationships"], ["Invoice"])
        self.assertEqual(result["terms"][1]["rejected_ambiguous_synonyms"],
                         ["Bill"])

    def test_duplicate_terms_fail_under_nfc_and_casefold(self) -> None:
        cases = (
            [term_block("Account"), term_block("account")],
            [term_block("Café"), term_block("Cafe\u0301")],
        )
        for terms in cases:
            with self.subTest(terms=terms):
                source = render_glossary(terms)
                model = parse(source)
                with self.assertRaisesRegex(domain_artifacts.DomainArtifactError,
                                            "duplicate|unique"):
                    domain_artifacts.validate_glossary_model(
                        model, source=source)

    def test_relationships_must_resolve_exactly_and_must_not_be_self(self) -> None:
        cases = (
            ([term_block("Account", relationships="Invoice")], "does not resolve"),
            ([term_block("Account", relationships="account")], "exact canonical"),
            ([term_block("Account", relationships="Account")], "itself"),
        )
        for terms, message in cases:
            with self.subTest(message=message):
                source = render_glossary(terms)
                with self.assertRaisesRegex(domain_artifacts.DomainArtifactError,
                                            message):
                    domain_artifacts.validate_glossary_model(
                        parse(source), source=source)

    def test_relationship_lists_are_unique_sorted_and_canonically_spaced(self) -> None:
        cases = (
            "Invoice, Invoice",
            "Invoice, Account",
            "Account,Invoice",
            "Account,, Invoice",
        )
        for relationships in cases:
            with self.subTest(relationships=relationships):
                source = render_glossary([
                    term_block("Account"),
                    term_block("Invoice", relationships=relationships),
                ])
                with self.assertRaises(domain_artifacts.DomainArtifactError):
                    domain_artifacts.validate_glossary_model(
                        parse(source), source=source)

    def test_synonyms_are_globally_unique_and_never_canonical_terms(self) -> None:
        cases = (
            [term_block("Account", synonyms="Invoice"), term_block("Invoice")],
            [term_block("Account", synonyms="Bill"),
             term_block("Invoice", synonyms="bill")],
            [term_block("Account", synonyms="Café"),
             term_block("Invoice", synonyms="Cafe\u0301")],
        )
        for terms in cases:
            with self.subTest(terms=terms):
                source = render_glossary(terms)
                with self.assertRaisesRegex(domain_artifacts.DomainArtifactError,
                                            "collides|duplicated"):
                    domain_artifacts.validate_glossary_model(
                        parse(source), source=source)

    def test_term_and_synonym_order_is_deterministic(self) -> None:
        wrong_terms = render_glossary([
            term_block("Invoice"), term_block("Account")])
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError,
                                    "canonical terms.*order"):
            domain_artifacts.validate_glossary_model(
                parse(wrong_terms), source=wrong_terms)
        wrong_synonyms = render_glossary([
            term_block("Account", synonyms="Receipt, Bill")])
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError,
                                    "deterministic order"):
            domain_artifacts.validate_glossary_model(
                parse(wrong_synonyms), source=wrong_synonyms)

    def test_malformed_missing_extra_and_reordered_fields_fail(self) -> None:
        valid = render_glossary()
        mutations = (
            valid.replace(b"- Source: confirmed request\n", b""),
            valid.replace(b"- Source: confirmed request\n",
                          b"- Source: confirmed request\n- Extra: no\n"),
            valid.replace(
                b"- Meaning: A confirmed domain boundary.\n- Relationships: none\n",
                b"- Relationships: none\n- Meaning: A confirmed domain boundary.\n"),
            valid.replace(b"- Meaning: A confirmed domain boundary.",
                          b"- Definition: A confirmed domain boundary."),
        )
        for source in mutations:
            with self.subTest(source=source), self.assertRaises(
                    domain_artifacts.DomainArtifactError):
                domain_artifacts.validate_glossary_model(
                    parse(source), source=source)

    def test_meaning_and_source_are_nonempty_bounded_and_source_is_real(self) -> None:
        cases = (
            render_glossary([term_block("Account", meaning=" ")]),
            render_glossary([term_block("Account", source=" ")]),
            render_glossary([term_block("Account", source="none")]),
            render_glossary([term_block(
                "Account", meaning="x" * (domain_artifacts.MAX_FIELD_LENGTH + 1))]),
            render_glossary([term_block(
                "Account", source="x" * (domain_artifacts.MAX_REFERENCE_LENGTH + 1))]),
        )
        for source in cases:
            with self.subTest(length=len(source)), self.assertRaises(
                    domain_artifacts.DomainArtifactError):
                domain_artifacts.validate_glossary_model(
                    parse(source), source=source)

    def test_only_terms_h2_and_canonical_h3_records_are_accepted(self) -> None:
        no_terms = render_glossary([])
        model = parse(no_terms)
        self.assertFalse(owner_decision("glossary", model).valid)
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError,
                                    "at least one term"):
            domain_artifacts.validate_glossary_model(model, source=no_terms)
        reserved = render_glossary([term_block("Terms")])
        with self.assertRaises(domain_artifacts.DomainArtifactError):
            domain_artifacts.validate_glossary_model(
                parse(reserved), source=reserved)
        backticked = render_glossary([term_block("`Account`")])
        self.assertFalse(owner_decision("glossary", parse(backticked)).valid)

    def test_source_model_mismatch_and_unqualified_reference_fail_typed(self) -> None:
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError, "does not match"):
            domain_artifacts.validate_glossary_model(
                parse(render_glossary()), source=render_glossary(identifier="GLOSSARY-902"))
        local = render_glossary([term_block("Account", source="REQ-001")])
        model = parse(local)
        self.assertFalse(owner_decision("glossary", model).valid)
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError, "qualified"):
            domain_artifacts.validate_glossary_model(model, source=local)


class BoundsCatalogAndRegressionTests(unittest.TestCase):
    def test_malformed_json_like_values_and_fuzz_never_leak_untyped_errors(self) -> None:
        rng = random.Random(207)
        atoms: list[object] = [None, True, False,
                               0, 1.5, "text", b"bytes", [], {}]
        values = atoms + [
            [rng.choice(atoms) for _ in range(rng.randrange(5))]
            for _ in range(100)
        ]
        for value in values:
            calls = (
                lambda value=value: domain_artifacts.validate_adr_model(value),
                lambda value=value: domain_artifacts.validate_adr_set(value),
                lambda value=value: domain_artifacts.validate_glossary_model(
                    value, source=value),
            )
            for call in calls:
                try:
                    call()
                except domain_artifacts.DomainArtifactError:
                    pass
                except Exception as exc:  # pragma: no cover - contract assertion
                    self.fail(
                        f"untyped exception leaked: {type(exc).__name__}: {exc}")

        controls = [chr(value) for value in range(32)] + [chr(127)]
        fields = ("h1", "sources", "references")
        for _ in range(100):
            model = adr_model()
            field = rng.choice(fields)
            control = rng.choice(controls)
            if field == "h1":
                model[field] += control
            elif field == "sources":
                model["metadata"][field] = ["fuzz" + control]
            else:
                model[field] = ["SPEC-901#REQ-001" + control]
            try:
                domain_artifacts.validate_adr_model(model)
            except domain_artifacts.DomainArtifactError:
                pass
            except Exception as exc:  # pragma: no cover - contract assertion
                self.fail(
                    f"untyped structured fuzz error: {type(exc).__name__}: {exc}")
            else:  # pragma: no cover - contract assertion
                self.fail("structured control fuzz was accepted")

    def test_c0_and_del_are_typed_for_direct_adr_and_glossary_models(self) -> None:
        valid_glossary_source = render_glossary()
        controls = [chr(value) for value in range(32)] + [chr(127)]
        for control in controls:
            direct_models = []
            for base in (adr_model(), glossary_model(valid_glossary_source)):
                changed = copy.deepcopy(base)
                changed["h1"] += control
                direct_models.append((changed, "h1"))
                changed = copy.deepcopy(base)
                changed["metadata"]["sources"] = ["confirmed" + control]
                direct_models.append((changed, "sources"))
                changed = copy.deepcopy(base)
                changed["references"] = ["SPEC-901#REQ-001" + control]
                direct_models.append((changed, "references"))
            changed = glossary_model(valid_glossary_source)
            changed["sections"][1] += control
            direct_models.append((changed, "term"))
            for model, field in direct_models:
                with self.subTest(codepoint=ord(control), field=field):
                    if model["metadata"]["type"] == "architecture-decision":
                        def call(): return domain_artifacts.validate_adr_model(model)
                    else:
                        def call(): return domain_artifacts.validate_glossary_model(
                            model, source=valid_glossary_source)
                    try:
                        call()
                    except domain_artifacts.DomainArtifactError as exc:
                        self.assertIn("control character", str(exc))
                    except Exception as exc:  # pragma: no cover - contract assertion
                        self.fail(
                            f"untyped control error: {type(exc).__name__}: {exc}")
                    else:  # pragma: no cover - contract assertion
                        self.fail("control character was accepted")

    def test_c0_and_del_in_every_raw_glossary_field_fail_typed(self) -> None:
        controls = [chr(value) for value in range(32)] + [chr(127)]
        valid_source = render_glossary()
        valid_model = glossary_model(valid_source)
        replacements = (
            ("### Account", "### Acc{}ount"),
            ("A confirmed domain boundary.", "A confirmed{} domain boundary."),
            ("Relationships: none", "Relationships: no{}ne"),
            ("synonyms: none", "synonyms: no{}ne"),
            ("Source: confirmed request", "Source: confirmed{} request"),
        )
        for control in controls:
            for original, replacement in replacements:
                source = valid_source.decode().replace(
                    original, replacement.format(control), 1)
                with self.subTest(codepoint=ord(control), field=original):
                    try:
                        domain_artifacts.validate_glossary_model(
                            valid_model, source=source)
                    except domain_artifacts.DomainArtifactError:
                        pass
                    except Exception as exc:  # pragma: no cover - contract assertion
                        self.fail(
                            f"untyped raw control error: {type(exc).__name__}: {exc}")
                    else:  # pragma: no cover - contract assertion
                        self.fail("raw control character was accepted")

    def test_sources_schema_runtime_boundary_parity_is_100(self) -> None:
        accepted = [f"source-{index:03d}" for index in range(
            domain_artifacts.MAX_SOURCES)]
        rejected = accepted + ["source-100"]
        for kind, renderer, validator in (
            ("adr", render_adr, lambda model, source:
             domain_artifacts.validate_adr_model(model, source=source)),
            ("glossary", render_glossary, lambda model, source:
             domain_artifacts.validate_glossary_model(model, source=source)),
        ):
            with self.subTest(kind=kind, count=len(accepted)):
                source = renderer(source_refs=accepted)
                model = parse(source)
                self.assertTrue(owner_decision(kind, model).valid)
                validator(model, source)
            with self.subTest(kind=kind, count=len(rejected)):
                source = renderer(source_refs=rejected)
                model = parse(source)
                self.assertFalse(owner_decision(kind, model).valid)
                with self.assertRaisesRegex(
                        domain_artifacts.DomainArtifactError, "item limit"):
                    validator(model, source)

    def test_supersedes_schema_runtime_boundary_parity_is_100(self) -> None:
        accepted = [f"ADR-{index + 1}" for index in range(
            domain_artifacts.MAX_SUPERSEDES)]
        rejected = accepted + ["ADR-101"]
        for values, expected in ((accepted, True), (rejected, False)):
            with self.subTest(count=len(values)):
                source = render_adr(
                    "ADR-901", status="accepted", supersedes=values)
                model = parse(source)
                self.assertEqual(owner_decision("adr", model).valid, expected)
                if expected:
                    domain_artifacts.validate_adr_model(model, source=source)
                else:
                    with self.assertRaisesRegex(
                            domain_artifacts.DomainArtifactError, "item limit"):
                        domain_artifacts.validate_adr_model(
                            model, source=source)

    def test_glossary_term_schema_runtime_boundary_parity_is_1000(self) -> None:
        accepted_terms = [
            term_block(f"Term {index:04d}")
            for index in range(domain_artifacts.MAX_GLOSSARY_TERMS)
        ]
        accepted_source = render_glossary(accepted_terms)
        accepted_model = parse(accepted_source)
        self.assertEqual(len(accepted_model["sections"]),
                         domain_artifacts.MAX_GLOSSARY_SECTIONS)
        self.assertTrue(owner_decision("glossary", accepted_model).valid)
        normalized = domain_artifacts.validate_glossary_model(
            accepted_model, source=accepted_source)
        self.assertEqual(len(normalized["terms"]),
                         domain_artifacts.MAX_GLOSSARY_TERMS)

        rejected_source = render_glossary(
            accepted_terms + [term_block("Term 1000")])
        rejected_model = parse(rejected_source)
        self.assertFalse(owner_decision("glossary", rejected_model).valid)
        with self.assertRaisesRegex(
                domain_artifacts.DomainArtifactError, "item limit"):
            domain_artifacts.validate_glossary_model(
                rejected_model, source=rejected_source)

    def test_collection_and_raw_source_limits_fail_typed(self) -> None:
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError, "limit"):
            domain_artifacts.validate_adr_set(
                [adr_model(f"ADR-{index + 1}")
                 for index in range(domain_artifacts.MAX_ADR_SET_ITEMS + 1)])
        huge = "x" * (domain_artifacts.MAX_SOURCE_BYTES + 1)
        with self.assertRaisesRegex(domain_artifacts.DomainArtifactError, "limit"):
            domain_artifacts.validate_glossary_model(
                glossary_model(render_glossary()), source=huge)

    def test_errors_and_normalized_results_are_deterministic(self) -> None:
        source = render_glossary(
            [term_block("Account", relationships="Missing")])
        messages = []
        for _ in range(3):
            try:
                domain_artifacts.validate_glossary_model(
                    parse(source), source=source)
            except domain_artifacts.DomainArtifactError as exc:
                messages.append(str(exc))
        self.assertEqual(len(set(messages)), 1)
        first = domain_artifacts.validate_adr_set(
            [adr_model("ADR-002"), adr_model("ADR-001")])
        second = domain_artifacts.validate_adr_set(
            [adr_model("ADR-001"), adr_model("ADR-002")])
        self.assertEqual(first, second)

    def test_catalog_variants_resolve_owner_local_while_v1_bases_stay_writable(self) -> None:
        data = catalog.load_artifact_catalog(ROOT)
        entries = {entry["id"]: entry for entry in data["artifacts"]}
        expectations = {
            "architecture-decision": ("adr.template.md", "adr-v1", "adr-v2"),
            "domain-context": ("glossary.template.md", None, "glossary-v2"),
        }
        resolved = {
            item.id: item for item in catalog.resolve_artifact_contracts(ROOT, data)}
        for identifier, (base_name, base_lifecycle, variant_lifecycle) in expectations.items():
            with self.subTest(identifier=identifier):
                entry = entries[identifier]
                self.assertEqual(entry["writable_schema_version"], 2)
                self.assertTrue(entry["template"].endswith(base_name))
                self.assertIsNone(entry["schema"])
                self.assertEqual(entry["lifecycle"], base_lifecycle)
                self.assertEqual([variant["id"]
                                 for variant in entry["variants"]], ["v2"])
                variant = resolved[identifier].variants[0]
                self.assertEqual((variant.id, variant.schema_version, variant.lifecycle),
                                 ("v2", 2, variant_lifecycle))
                self.assertTrue(
                    variant.template and variant.template.is_file())
                self.assertTrue(variant.schema and variant.schema.is_file())
                self.assertTrue(variant.template.is_relative_to(
                    resolved[identifier].owner_directory))
                self.assertTrue(variant.schema.is_relative_to(
                    resolved[identifier].owner_directory))

    def test_variant_order_owner_escape_and_future_pointers_fail_closed(self) -> None:
        data = catalog.load_artifact_catalog(ROOT)
        target = next(entry for entry in data["artifacts"]
                      if entry["id"] == "architecture-decision")
        changed = copy.deepcopy(data)
        changed_target = next(entry for entry in changed["artifacts"]
                              if entry["id"] == "architecture-decision")
        future = copy.deepcopy(changed_target["variants"][0])
        future["id"] = "v3"
        future["schema_version"] = 3
        changed_target["variants"].insert(0, future)
        with self.assertRaisesRegex(catalog.CatalogError, "ordered"):
            catalog.validate_artifact_catalog(changed)
        changed = copy.deepcopy(data)
        changed_target = next(entry for entry in changed["artifacts"]
                              if entry["id"] == "architecture-decision")
        changed_target["variants"][0]["schema"] = (
            "skills/write-spec/assets/spec.v2.schema.json")
        with self.assertRaisesRegex(catalog.CatalogError, "outside owner"):
            catalog.resolve_artifact_contracts(ROOT, changed)
        for artifact in catalog.resolve_artifact_contracts(ROOT):
            for variant in artifact.variants:
                for pointer in (variant.template, variant.schema):
                    if pointer is not None:
                        self.assertTrue(pointer.is_file())
        self.assertEqual(target["variants"][0]["requires_modules"], [])
        self.assertEqual(target["variants"][0]["forbids_sections"], [])

    def test_source_only_module_has_no_io_or_dynamic_import_surface(self) -> None:
        path = ROOT / "scripts" / "contracts" / "domain_artifacts.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertTrue(imports.isdisjoint({
            "os", "pathlib", "socket", "subprocess", "urllib", "requests",
        }))
        calls = {
            node.func.id for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue(calls.isdisjoint(
            {"eval", "exec", "open", "__import__"}))

    def test_unrelated_v1_assets_are_byte_identical(self) -> None:
        for path, expected in V1_HASHES.items():
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256(
                    path.read_bytes()).hexdigest(), expected)

    def test_real_id_scan_is_valid_and_history_complete(self) -> None:
        completed = subprocess.run(
            ["python3", ".agents/tools/check_artifact_ids.py", "scan",
             "--root", ".", "--format", "json"],
            cwd=ROOT, check=True, capture_output=True, text=True)
        report = json.loads(completed.stdout)
        self.assertTrue(report["valid"], report["diagnostics"])
        self.assertTrue(report["history"]["complete"], report["diagnostics"])
        scanner = (AGENTS / "tools" / "check_artifact_ids.py").read_text(
            encoding="utf-8")
        self.assertIn('"supersedes", "superseded_by"', scanner)


if __name__ == "__main__":
    unittest.main()

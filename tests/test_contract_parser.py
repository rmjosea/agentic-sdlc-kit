from __future__ import annotations

import ast
import json
import time
import unittest
from collections.abc import Iterator, Mapping
from pathlib import Path
from unittest import mock

from scripts.contracts import markdown, schema


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_METADATA = {
    "schema_version", "id", "type", "sources", "status", "risk_rationale"
}
VALID_MARKDOWN = b"""---
schema_version: 2
id: "SPEC-002"
type: "specification"
sources: ["confirmed request"]
status: "approved"
---

# Harness v2

## Context

**REQ-001**: Keep the parser bounded.

### Detail

See PLAN-002#TASK-203 and <declared value>.
"""


def codes(result: schema.ValidationResult) -> list[str]:
    return [item.code for item in result.diagnostics]


class MarkdownParserTests(unittest.TestCase):
    def test_valid_spec_style_frontmatter_and_exact_model(self) -> None:
        model = markdown.parse_markdown(
            VALID_MARKDOWN,
            allowed_metadata_keys=ALLOWED_METADATA,
            mode="template",
            declared_placeholders={"<declared value>"},
        )
        self.assertEqual(set(model), {
            "metadata", "h1", "sections", "local_ids", "references", "placeholders"
        })
        self.assertEqual(model["metadata"], {
            "schema_version": 2,
            "id": "SPEC-002",
            "type": "specification",
            "sources": ["confirmed request"],
            "status": "approved",
        })
        self.assertEqual(model["h1"], "Harness v2")
        self.assertEqual(model["sections"], ["Context", "Detail"])
        self.assertEqual(
            model["local_ids"], [{"kind": "requirement", "id": "REQ-001"}])
        self.assertEqual(model["references"], ["PLAN-002#TASK-203"])
        self.assertEqual(model["placeholders"], ["<declared value>"])

    def test_normalization_handles_lf_crlf_nfc_and_whitespace(self) -> None:
        decomposed = VALID_MARKDOWN.decode().replace(
            "# Harness v2", "# Cafe\u0301   \t").replace(
                "\n\n### Detail\n", "\n\n\n### Detail   \t\n")
        crlf = decomposed.replace("\n", "\r\n").encode()
        model = markdown.parse_markdown(
            crlf,
            allowed_metadata_keys=ALLOWED_METADATA,
            mode="template",
            declared_placeholders={"<declared value>"},
        )
        self.assertEqual(model["h1"], "Caf\u00e9")
        self.assertEqual(model["sections"], ["Context", "Detail"])
        normalized = markdown.normalize_text(b"  \r\nA  \t\r\n\r\n\rB\r\n \t")
        self.assertEqual(normalized, "A\n\n\nB")

    def test_frontmatter_rejects_non_utf8_delimiters_duplicates_and_unknowns(self) -> None:
        cases = (
            ("UTF-8", b"\xff---\n---\n# Title\n"),
            ("opening", b" ---\n---\n# Title\n"),
            ("opening", b"--- \n---\n# Title\n"),
            ("closing", b"---\nid: \"SPEC-002\"\n--- \n# Title\n"),
            ("closing", b"---\nid: \"SPEC-002\"\n# Title\n"),
            ("duplicate", b"---\nid: \"SPEC-002\"\nid: \"SPEC-003\"\n---\n# Title\n"),
            ("unknown", b"---\nlegacy: true\n---\n# Title\n"),
        )
        for message, value in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(markdown.MarkdownError, message):
                    markdown.parse_markdown(
                        value, allowed_metadata_keys=ALLOWED_METADATA)

    def test_frontmatter_rejects_implicit_multiline_alias_tag_comment_and_controls(self) -> None:
        lines = (
            ("JSON value", "id: SPEC-002"),
            ("one key and JSON value", "sources:\n  - \"request\""),
            ("JSON value", "sources: *shared"),
            ("JSON value", "id: !!str \"SPEC-002\""),
            ("JSON value", "id: \"SPEC-002\" # comment"),
            ("control", 'id: "bad\\u0000value"'),
        )
        for message, line in lines:
            with self.subTest(line=line):
                document = f"---\n{line}\n---\n# Title\n".encode()
                with self.assertRaisesRegex(markdown.MarkdownError, message):
                    markdown.parse_markdown(
                        document, allowed_metadata_keys=ALLOWED_METADATA)

    def test_frontmatter_rejects_overflow_and_normalizes_decoded_json_recursively(self) -> None:
        for raw_value in ("1e400", "-1e400", "[0, {\"value\": 1e400}]"):
            with self.subTest(raw_value=raw_value):
                document = (
                    f"---\nrisk_rationale: {raw_value}\n---\n# Title\n".encode()
                )
                with self.assertRaisesRegex(markdown.MarkdownError, "finite JSON"):
                    markdown.parse_markdown(
                        document, allowed_metadata_keys=ALLOWED_METADATA)
        normalized = markdown.parse_markdown(
            b'---\nrisk_rationale: {"label":"Cafe\\u0301","items":["A\\u030a"]}\n---\n# Title\n',
            allowed_metadata_keys=ALLOWED_METADATA,
        )
        self.assertEqual(normalized["metadata"]["risk_rationale"], {
            "label": "Caf\u00e9", "items": ["\u00c5"]
        })
        duplicate = b'---\nrisk_rationale: {"Caf\\u00e9":1,"Cafe\\u0301":2}\n---\n# Title\n'
        with self.assertRaisesRegex(markdown.MarkdownError, "normalized JSON key"):
            markdown.parse_markdown(
                duplicate, allowed_metadata_keys=ALLOWED_METADATA)

    def test_body_requires_one_nonempty_h1_as_first_content(self) -> None:
        bodies = (
            ("begin with exactly one H1", "## Wrong\n"),
            ("begin with exactly one H1", "text\n# Late\n"),
            ("non-empty H1", "#   \n"),
            ("exactly one H1", "# First\n\n# Second\n"),
        )
        for message, body in bodies:
            with self.subTest(body=body):
                document = f"---\nid: \"SPEC-002\"\n---\n{body}".encode()
                with self.assertRaisesRegex(markdown.MarkdownError, message):
                    markdown.parse_markdown(
                        document, allowed_metadata_keys=ALLOWED_METADATA)

    def test_fenced_headings_and_ids_are_not_document_structure(self) -> None:
        document = b'''---\nid: "SPEC-002"\n---\n# Title\n\n```markdown\n# Example\n## Example section\n**REQ-001**: Example\n```\n\n## Real\n'''
        model = markdown.parse_markdown(
            document, allowed_metadata_keys=ALLOWED_METADATA)
        self.assertEqual(model["sections"], ["Real"])
        self.assertEqual(model["local_ids"], [])

    def test_one_mask_handles_tricky_fences_inline_code_html_and_autolinks(self) -> None:
        document = b'''---
id: "SPEC-002"
---
# Title

````python
# fenced H1
## fenced section
**REQ-900**: fenced
SPEC-900#REQ-900 <fenced token>
``` trailing text
~~~
```
`````\x20\x20\x20

~~~ info ` is allowed
SPEC-901#REQ-901 <tilde token>
~~~~

```bad`info
## Visible after invalid backtick opener

`SPEC-902#REQ-902 <inline token>`
``SPEC-906#REQ-906 ` <long inline token>``
<div data-ref="SPEC-903#REQ-903"><span>text</span></div>
<https://example.test/SPEC-904#REQ-904>
<user-SPEC-905#REQ-905@example.test>

## Real
**REQ-001**: Real
SPEC-002#REQ-001 <real token>
'''
        model = markdown.parse_markdown(
            document,
            allowed_metadata_keys=ALLOWED_METADATA,
            mode="template",
            declared_placeholders={"<real token>"},
        )
        self.assertEqual(
            model["sections"], ["Visible after invalid backtick opener", "Real"])
        self.assertEqual(
            model["local_ids"], [{"kind": "requirement", "id": "REQ-001"}])
        self.assertEqual(model["references"], ["SPEC-002#REQ-001"])
        self.assertEqual(model["placeholders"], ["<real token>"])

    def test_four_space_fence_indent_is_not_a_fence(self) -> None:
        document = b'''---\nid: "SPEC-002"\n---\n# Title\n\n    ```python\n## Visible\n'''
        model = markdown.parse_markdown(
            document, allowed_metadata_keys=ALLOWED_METADATA)
        self.assertEqual(model["sections"], ["Visible"])

    def test_html_svg_mathml_custom_and_quoted_gt_are_masked_case_insensitively(self) -> None:
        document = b'''---
id: "SPEC-002"
---
# Title

<SVG title="1 > 0" data-ref="SPEC-100#REQ-100"><path d="M0 > 1"></path></SVG>
<VIDEO title='2 > 1' data-ref="SPEC-101#REQ-101"><source src="movie.mp4"></video>
<math><mrow data-ref="SPEC-102#REQ-102"><mi>x</mi></mrow></math>
<my-widget title="3 > 2" data-ref="SPEC-103#REQ-103"></my-widget>
<!DOCTYPE html><!-- SPEC-104#REQ-104 -->
'''
        model = markdown.parse_markdown(
            document, allowed_metadata_keys=ALLOWED_METADATA)
        self.assertEqual(model["references"], [])
        self.assertEqual(model["placeholders"], [])

    def test_multiline_html_comment_and_nested_element_blocks_share_the_mask(self) -> None:
        document = b'''---
id: "PLAN-002"
---
# Title

<!--
# hidden H1
### TASK-900: hidden comment task
SPEC-900#REQ-900 <hidden comment>
-->
<div>
### TASK-901: hidden element task
**REQ-901**: hidden requirement
SPEC-901#REQ-901 <hidden element>
<section>
### TASK-902: hidden nested task
</section>
</div>
### TASK-001: Visible task
SPEC-002#REQ-001 <visible token>
'''
        model = markdown.parse_markdown(
            document,
            allowed_metadata_keys=ALLOWED_METADATA,
            mode="template",
            declared_placeholders={"<visible token>"},
        )
        self.assertEqual(model["sections"], ["TASK-001: Visible task"])
        self.assertEqual(
            model["local_ids"], [{"kind": "task", "id": "TASK-001"}])
        self.assertEqual(model["references"], ["SPEC-002#REQ-001"])
        self.assertEqual(model["placeholders"], ["<visible token>"])

    def test_each_nested_raw_tag_suspends_outer_element_stack(self) -> None:
        for raw_tag in ("script", "pre", "style", "textarea"):
            with self.subTest(raw_tag=raw_tag):
                document = f'''---
id: "PLAN-002"
---
# Title

<div class="outer">
<{raw_tag.upper()} data-kind="later">
</div>
### TASK-940: raw text is hidden
SPEC-940#REQ-940 <raw later token>
</{raw_tag.upper()}>
<{raw_tag} data-kind="same"> </section> SPEC-941#REQ-941 <raw same token> </{raw_tag.upper()}>
### TASK-942: still hidden by outer div
</div>
### TASK-004: Visible after outer close
SPEC-002#REQ-004 <visible nested raw token>
'''.encode()
                model = markdown.parse_markdown(
                    document,
                    allowed_metadata_keys=ALLOWED_METADATA,
                    mode="template",
                    declared_placeholders={"<visible nested raw token>"},
                )
                self.assertEqual(
                    model["local_ids"], [{"kind": "task", "id": "TASK-004"}])
                self.assertEqual(model["references"], ["SPEC-002#REQ-004"])
                self.assertEqual(
                    model["placeholders"], ["<visible nested raw token>"])

    def test_raw_inside_nested_elements_and_unclosed_raw_fail_closed(self) -> None:
        closed = b'''---
id: "PLAN-002"
---
# Title

<div><section>
<script type="text/plain">
</section></div>
<pre>not a nested state</pre>
### TASK-950: hidden script text
</SCRIPT>
### TASK-951: hidden by section
</section></div>
### TASK-005: Visible
'''
        model = markdown.parse_markdown(
            closed, allowed_metadata_keys=ALLOWED_METADATA)
        self.assertEqual(
            model["local_ids"], [{"kind": "task", "id": "TASK-005"}])

        unclosed = b'''---
id: "PLAN-002"
---
# Title

<div>
<style media="all">
</div>
### TASK-952: hidden to EOF
SPEC-952#REQ-952 <hidden nested EOF>
'''
        model = markdown.parse_markdown(
            unclosed, allowed_metadata_keys=ALLOWED_METADATA)
        self.assertEqual(model["sections"], [])
        self.assertEqual(model["local_ids"], [])
        self.assertEqual(model["references"], [])
        self.assertEqual(model["placeholders"], [])

    def test_raw_processing_declaration_and_cdata_blocks_mask_until_terminator(self) -> None:
        document = b'''---
id: "SPEC-002"
---
# Title

<script>
### TASK-910: script
SPEC-910#REQ-910 <script token>
</script>
<pre>
**REQ-911**: pre
</pre>
<style>
### TASK-912: style
</style>
<textarea>
### TASK-913: textarea
</textarea>
<?processing
### TASK-914: processing
?>
<!DECLARATION
### TASK-915: declaration
>
<![CDATA[
### TASK-916: cdata
]]>
## Visible
'''
        model = markdown.parse_markdown(
            document, allowed_metadata_keys=ALLOWED_METADATA)
        self.assertEqual(model["sections"], ["Visible"])
        self.assertEqual(model["local_ids"], [])
        self.assertEqual(model["references"], [])
        self.assertEqual(model["placeholders"], [])

    def test_html_blank_boundary_and_explicit_close_preserve_following_markdown(self) -> None:
        document = b'''---
id: "PLAN-002"
---
# Title

<table>
### TASK-920: hidden

### TASK-002: Visible after blank boundary
<svg>
### TASK-921: hidden svg
</svg>
### TASK-003: Visible after close
<ordinary placeholder>
'''
        model = markdown.parse_markdown(
            document,
            allowed_metadata_keys=ALLOWED_METADATA,
            mode="template",
            declared_placeholders={"<ordinary placeholder>"},
        )
        self.assertEqual(model["local_ids"], [
            {"kind": "task", "id": "TASK-002"},
            {"kind": "task", "id": "TASK-003"},
        ])
        self.assertEqual(model["placeholders"], ["<ordinary placeholder>"])

    def test_unclosed_html_blocks_fail_closed_to_eof_without_hanging(self) -> None:
        for opening in ("<div>", "<!--", "<script>"):
            with self.subTest(opening=opening):
                document = f'''---
id: "PLAN-002"
---
# Title

{opening}
### TASK-930: hidden to EOF
SPEC-930#REQ-930 <hidden to EOF>
'''.encode()
                model = markdown.parse_markdown(
                    document, allowed_metadata_keys=ALLOWED_METADATA)
                self.assertEqual(model["sections"], [])
                self.assertEqual(model["local_ids"], [])
                self.assertEqual(model["references"], [])
                self.assertEqual(model["placeholders"], [])

    def test_declared_placeholder_and_malformed_or_unclosed_tags_are_not_masked(self) -> None:
        malformed = '<video =bad data-ref="SPEC-201#REQ-201">'
        document = f'''---
id: "SPEC-002"
---
# <FAKE>

{malformed}
<video title="unterminated SPEC-202#REQ-202
'''.encode()
        model = markdown.parse_markdown(
            document,
            allowed_metadata_keys=ALLOWED_METADATA,
            mode="template",
            declared_placeholders={"<FAKE>", malformed},
        )
        self.assertEqual(
            model["references"], ["SPEC-201#REQ-201", "SPEC-202#REQ-202"])
        self.assertEqual(model["placeholders"], ["<FAKE>", malformed])

    def test_html_tags_are_not_rendered_placeholders_but_declared_tokens_are(self) -> None:
        rendered = b'---\nid: "SPEC-002"\n---\n# Title\n\n<div><Title></Title></div>\n'
        self.assertEqual(markdown.parse_markdown(
            rendered, allowed_metadata_keys=ALLOWED_METADATA)["placeholders"], [])
        template = b'---\nid: "SPEC-<NNN>"\n---\n# <Title>\n'
        model = markdown.parse_markdown(
            template,
            allowed_metadata_keys=ALLOWED_METADATA,
            mode="template",
            declared_placeholders={"<NNN>", "<Title>"},
        )
        self.assertEqual(model["placeholders"], ["<NNN>", "<Title>"])

    def test_plain_id_prose_and_non_declarative_forms_never_create_local_ids(self) -> None:
        document = b'''---
id: "PLAN-002"
---
# Recovery notes

TASK-218 makes no fixes.
AC-010 requires a regression test.
REQ-007 remains satisfied.
TASK-219: plain text with a colon is still prose.
REQ-008: plain requirement prose.
**TASK-220**: bold is not the task declaration form.
### TASK-221 missing the required colon
SPEC-002#REQ-001 is a qualified reference.
`### TASK-222: inline code`
<div>### TASK-223: HTML text</div>
'''
        model = markdown.parse_markdown(
            document, allowed_metadata_keys=ALLOWED_METADATA)
        self.assertEqual(model["local_ids"], [])
        self.assertEqual(model["references"], [
            "TASK-218", "AC-010", "REQ-007", "TASK-219", "REQ-008",
            "TASK-220", "TASK-221", "SPEC-002#REQ-001",
        ])

    def test_declarations_are_not_references_but_same_line_candidates_remain(self) -> None:
        document = b'''---
id: "PLAN-002"
---
# Work

**REQ-001**: See SPEC-999#REQ-004 and AC-099.
**AC-010**: Covered by SPEC-999-FRAG-1#REQ-005.
### TASK-218: Implement PLAN-002#TASK-217 and TASK-219
'''
        model = markdown.parse_markdown(
            document, allowed_metadata_keys=ALLOWED_METADATA)
        self.assertEqual(model["local_ids"], [
            {"kind": "requirement", "id": "REQ-001"},
            {"kind": "acceptance-criterion", "id": "AC-010"},
            {"kind": "task", "id": "TASK-218"},
        ])
        self.assertEqual(model["references"], [
            "SPEC-999#REQ-004", "AC-099",
            "SPEC-999-FRAG-1#REQ-005",
            "PLAN-002#TASK-217", "TASK-219",
        ])

    def test_reference_candidates_support_local_simple_and_fragmented_parents(self) -> None:
        document = b'''---
id: "SPEC-002"
---
# References

REQ-777 AC-010 TASK-218
SPEC-999#REQ-001 PLAN-002#TASK-004
SPEC-999-FRAG-1#REQ-002 PLAN-002-FRAG-20#TASK-005
SPEC-999#REQ-001 REQ-777
'''
        model = markdown.parse_markdown(
            document, allowed_metadata_keys=ALLOWED_METADATA)
        self.assertEqual(model["references"], [
            "REQ-777", "AC-010", "TASK-218",
            "SPEC-999#REQ-001", "PLAN-002#TASK-004",
            "SPEC-999-FRAG-1#REQ-002", "PLAN-002-FRAG-20#TASK-005",
        ])

    def test_reference_candidate_boundaries_reject_near_misses_without_suffixes(self) -> None:
        document = b'''---
id: "SPEC-002"
---
# Boundaries

XREQ-001 REQ-001X A-REQ-002 #REQ-003 req-004 REQ-X
SPEC-999-FRAG#REQ-004 SPEC-999-FRAG-1#REQ-005X
(SPEC-999-FRAG-1#REQ-006), [AC-007]; TASK-008.
'''
        model = markdown.parse_markdown(
            document, allowed_metadata_keys=ALLOWED_METADATA)
        self.assertEqual(model["references"], [
            "SPEC-999-FRAG-1#REQ-006", "AC-007", "TASK-008",
        ])

    def test_only_explicit_current_declaration_forms_create_ordered_local_ids(self) -> None:
        document = b'''---
id: "PLAN-002"
---
# Work

**REQ-001**: Observable requirement.
**AC-010**: Acceptance criterion.
### TASK-218: Recover the parser
'''
        model = markdown.parse_markdown(
            document, allowed_metadata_keys=ALLOWED_METADATA)
        self.assertEqual(model["local_ids"], [
            {"kind": "requirement", "id": "REQ-001"},
            {"kind": "acceptance-criterion", "id": "AC-010"},
            {"kind": "task", "id": "TASK-218"},
        ])

    def test_duplicate_local_declarations_are_rejected_but_repeated_refs_are_deduped(self) -> None:
        duplicates = (
            b"---\nid: \"SPEC-002\"\n---\n# T\n\n**REQ-001**: A\n\n**REQ-001**: B\n",
            b"---\nid: \"PLAN-002\"\n---\n# T\n\n### TASK-001: A\n\n### TASK-001: B\n",
        )
        for duplicate in duplicates:
            with self.subTest(document=duplicate):
                with self.assertRaisesRegex(markdown.MarkdownError, "duplicate local ID"):
                    markdown.parse_markdown(
                        duplicate, allowed_metadata_keys=ALLOWED_METADATA)
        referenced = b"---\nid: \"SPEC-002\"\n---\n# T\n\nSPEC-002#REQ-001 SPEC-002#REQ-001\n"
        model = markdown.parse_markdown(
            referenced, allowed_metadata_keys=ALLOWED_METADATA)
        self.assertEqual(model["references"], ["SPEC-002#REQ-001"])

    def test_local_id_kinds_and_reference_order_are_deterministic(self) -> None:
        document = b"""---
id: "PLAN-002"
---
# Work

**AC-002**: Accept

### TASK-003: Build

**REQ-001**: Need

SPEC-009#REQ-002 PLAN-002#TASK-003 SPEC-009#REQ-002
"""
        expected = {
            "metadata": {"id": "PLAN-002"},
            "h1": "Work",
            "sections": ["TASK-003: Build"],
            "local_ids": [
                {"kind": "acceptance-criterion", "id": "AC-002"},
                {"kind": "task", "id": "TASK-003"},
                {"kind": "requirement", "id": "REQ-001"},
            ],
            "references": ["SPEC-009#REQ-002", "PLAN-002#TASK-003"],
            "placeholders": [],
        }
        for _ in range(3):
            self.assertEqual(markdown.parse_markdown(
                document, allowed_metadata_keys=ALLOWED_METADATA), expected)

    def test_template_and_rendered_placeholder_modes(self) -> None:
        document = b"---\nid: \"SPEC-<NNN>\"\n---\n# <Title>\n"
        with self.assertRaisesRegex(markdown.MarkdownError, "rendered.*placeholder"):
            markdown.parse_markdown(
                document, allowed_metadata_keys=ALLOWED_METADATA)
        with self.assertRaisesRegex(markdown.MarkdownError, "undeclared placeholder"):
            markdown.parse_markdown(
                document,
                allowed_metadata_keys=ALLOWED_METADATA,
                mode="template",
                declared_placeholders={"<Title>"},
            )
        model = markdown.parse_markdown(
            document,
            allowed_metadata_keys=ALLOWED_METADATA,
            mode="template",
            declared_placeholders={"<NNN>", "<Title>"},
        )
        self.assertEqual(model["placeholders"], ["<NNN>", "<Title>"])

    def test_markdown_input_size_is_bounded(self) -> None:
        with self.assertRaisesRegex(markdown.MarkdownError, "character limit"):
            markdown.parse_markdown(
                b"---\nid: \"SPEC-002\"\n---\n# Title\n",
                allowed_metadata_keys={"id"},
                max_characters=10,
            )

    def test_optional_metadata_schema_is_applied(self) -> None:
        metadata_schema = {
            "type": "object",
            "required": ["id"],
            "additionalProperties": False,
            "properties": {"id": {"const": "SPEC-002"}},
        }
        model = markdown.parse_markdown(
            b"---\nid: \"SPEC-002\"\n---\n# Title\n",
            allowed_metadata_keys={"id"},
            metadata_schema=metadata_schema,
        )
        self.assertEqual(model["metadata"]["id"], "SPEC-002")
        with self.assertRaisesRegex(markdown.MarkdownError, "metadata does not match schema"):
            markdown.parse_markdown(
                b"---\nid: \"SPEC-003\"\n---\n# Title\n",
                allowed_metadata_keys={"id"},
                metadata_schema=metadata_schema,
            )


class SchemaKeywordTests(unittest.TestCase):
    def assertDecision(
        self, contract: object, accepted: object, rejected: object, expected: str
    ) -> None:
        self.assertTrue(schema.validate(accepted, contract).valid)
        result = schema.validate(rejected, contract)
        self.assertFalse(result.valid)
        self.assertIn(expected, codes(result))

    def test_type_const_enum_and_numeric_bounds(self) -> None:
        cases = [
            ({"type": "string"}, "ok", 1, "type"),
            ({"const": {"x": 1}}, {"x": 1}, {"x": 2}, "const"),
            ({"enum": ["a", "b"]}, "a", "c", "enum"),
            ({"type": "number", "minimum": 1, "maximum": 2}, 1.5, 0, "minimum"),
            ({"type": "integer", "minimum": 1, "maximum": 2}, 2, 3, "maximum"),
        ]
        for contract, accepted, rejected, expected in cases:
            with self.subTest(contract=contract):
                self.assertDecision(contract, accepted, rejected, expected)
        self.assertFalse(schema.validate(True, {"type": "integer"}).valid)

    def test_object_keywords_positive_and_negative(self) -> None:
        contract = {
            "type": "object",
            "required": ["name"],
            "additionalProperties": False,
            "properties": {"name": {"type": "string"}},
        }
        self.assertTrue(schema.validate({"name": "kit"}, contract).valid)
        self.assertIn("required", codes(schema.validate({}, contract)))
        self.assertIn(
            "additionalProperties", codes(schema.validate({"name": "kit", "x": 1}, contract)))
        self.assertIn("type", codes(schema.validate({"name": 1}, contract)))
        open_contract = {"type": "object",
                         "additionalProperties": {"type": "integer"}}
        self.assertTrue(schema.validate({"x": 1}, open_contract).valid)
        self.assertFalse(schema.validate({"x": "1"}, open_contract).valid)

    def test_boolean_composition_keywords(self) -> None:
        cases = [
            ({"oneOf": [{"type": "integer"}, {"const": 2}]}, 1, 2, "oneOf"),
            ({"anyOf": [{"const": "a"}, {"const": "b"}]}, "a", "c", "anyOf"),
            ({"allOf": [{"type": "integer"}, {"minimum": 2}]}, 2, 1, "minimum"),
            ({"not": {"type": "null"}}, "x", None, "not"),
        ]
        for contract, accepted, rejected, expected in cases:
            with self.subTest(contract=contract):
                self.assertDecision(contract, accepted, rejected, expected)

    def test_conditionals_apply_only_selected_branch(self) -> None:
        contract = {
            "if": {"type": "integer"},
            "then": {"minimum": 2},
            "else": {"type": "string"},
        }
        self.assertTrue(schema.validate(2, contract).valid)
        self.assertTrue(schema.validate("x", contract).valid)
        self.assertIn("minimum", codes(schema.validate(1, contract)))
        self.assertIn("type", codes(schema.validate(None, contract)))

    def test_array_keywords_positive_and_negative(self) -> None:
        contract = {
            "type": "array", "items": {"type": "integer"},
            "minItems": 1, "maxItems": 2, "uniqueItems": True,
        }
        self.assertTrue(schema.validate([1, 2], contract).valid)
        for value, expected in (([], "minItems"), ([1, 2, 3], "maxItems"),
                                ([1, 1], "uniqueItems"), (["1"], "type")):
            with self.subTest(value=value):
                self.assertIn(expected, codes(
                    schema.validate(value, contract)))

    def test_string_keywords_positive_and_negative(self) -> None:
        contract = {
            "type": "string", "pattern": "^[a-z]+$", "minLength": 2, "maxLength": 4
        }
        self.assertTrue(schema.validate("kit", contract).valid)
        self.assertIn("pattern", codes(schema.validate("K2", contract)))
        self.assertIn("minLength", codes(schema.validate("a", contract)))
        self.assertIn("maxLength", codes(schema.validate("agent", contract)))

    def test_current_normalized_markdown_schema_accepts_parser_output(self) -> None:
        contract = json.loads((
            ROOT / ".agents" / "schemas" / "markdown-document.schema.json"
        ).read_text(encoding="utf-8"))
        document = VALID_MARKDOWN.replace(
            b" and <declared value>", b"")
        model = markdown.parse_markdown(
            document, allowed_metadata_keys=ALLOWED_METADATA)
        self.assertTrue(schema.validate(model, contract).valid)

    def test_schema_meta_id_defs_and_local_ref(self) -> None:
        contract = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "urn:test:root:v2",
            "$defs": {"name": {"type": "string", "minLength": 1}},
            "$ref": "#/$defs/name",
        }
        self.assertTrue(schema.validate("kit", contract).valid)
        self.assertIn("minLength", codes(schema.validate("", contract)))


class SchemaSafetyTests(unittest.TestCase):
    def test_absolute_urn_registry_resolution_and_fragments(self) -> None:
        external = {
            "$id": "urn:test:common:v2",
            "$defs": {"positive": {"type": "integer", "minimum": 1}},
            "$ref": "#/$defs/positive",
        }
        self.assertTrue(schema.validate(
            2, {"$ref": "urn:test:common:v2"}, registry=[external]).valid)
        self.assertFalse(schema.validate(
            0, {"$ref": "urn:test:common:v2#/$defs/positive"},
            registry=[external]).valid)
        self.assertTrue(schema.validate(
            2, {"$ref": "urn:test:common:v2"},
            registry={"urn:test:common:v2": external}).valid)

    def test_ref_siblings_keep_their_2020_12_semantics(self) -> None:
        external = {"$id": "urn:test:number:v1", "type": "integer"}
        contract = {"$ref": "urn:test:number:v1", "minimum": 2}
        self.assertTrue(schema.validate(
            2, contract, registry=[external]).valid)
        self.assertIn("minimum", codes(schema.validate(
            1, contract, registry=[external])))
        self.assertIn("type", codes(schema.validate(
            "2", contract, registry=[external])))

    def test_registry_iterables_and_mappings_stop_at_bounds_before_sorting(self) -> None:
        consumed = 0

        def infinite_registry() -> Iterator[dict[str, object]]:
            nonlocal consumed
            index = 1
            while True:
                consumed += 1
                yield {"$id": f"urn:test:item:v{index}", "type": "integer"}
                index += 1

        limits = schema.Limits(max_schema_nodes=20, max_array_length=2)
        result = schema.validate(
            1, {}, registry=infinite_registry(), limits=limits)
        self.assertIn("limit.array", codes(result))
        self.assertEqual(consumed, 3)

        consumed_deep = 0

        def deep_registry() -> Iterator[dict[str, object]]:
            nonlocal consumed_deep
            consumed_deep += 1
            yield {
                "$id": "urn:test:deep:v1",
                "$defs": {"child": {"type": "integer"}},
            }
            consumed_deep += 1
            raise AssertionError("registry consumed after schema-node limit")

        result = schema.validate(
            1, {}, registry=deep_registry(),
            limits=schema.Limits(max_schema_nodes=2, max_array_length=10),
        )
        self.assertIn("limit.schema_nodes", codes(result))
        self.assertEqual(consumed_deep, 1)

        class OversizedMapping(Mapping[str, dict[str, object]]):
            def __len__(self) -> int:
                return 3

            def __iter__(self) -> Iterator[str]:
                raise AssertionError(
                    "oversized mapping was iterated or sorted")

            def __getitem__(self, key: str) -> dict[str, object]:
                raise AssertionError(f"oversized mapping key was read: {key}")

        result = schema.validate(
            1, {}, registry=OversizedMapping(),
            limits=schema.Limits(max_array_length=2),
        )
        self.assertIn("limit.array", codes(result))

    def test_registry_requires_unique_matching_urn_ids(self) -> None:
        external = {"$id": "urn:test:common:v2", "type": "integer"}
        for registry in (
            [{}],
            [external, external],
            {"urn:test:other:v2": external},
        ):
            with self.subTest(registry=registry):
                self.assertIn(
                    "schema.registry",
                    codes(schema.validate(1, {}, registry=registry)),
                )

    def test_only_positive_integer_versioned_urns_are_accepted(self) -> None:
        for identifier in (
            "urn:test:root", "urn:test:root:v0", "urn:test:root:v01",
            "urn:test:root:version2", "urn:test:v0",
        ):
            with self.subTest(identifier=identifier):
                self.assertIn(
                    "schema.id", codes(schema.validate(1, {"$id": identifier})))
                self.assertIn(
                    "schema.ref_unsafe",
                    codes(schema.validate(1, {"$ref": identifier})),
                )
        for identifier in ("urn:test:root:v1", "urn:agentic-sdlc-kit:root:v20"):
            with self.subTest(identifier=identifier):
                self.assertTrue(schema.validate(1, {"$id": identifier}).valid)

    def test_structural_strings_are_bounded_before_regex_sort_or_resolution(self) -> None:
        limits = schema.Limits(max_string_length=8, max_pattern_length=100)
        contracts = (
            {"$schema": "x" * 9},
            {"$id": "urn:test:root:v1"},
            {"$ref": "urn:test:root:v1"},
            {"pattern": "[a-z]" * 2},
            {"unknown_keyword_too_long": True},
            {"$defs": {"definition-too-long": {}}},
            {"properties": {"property-too-long": {}}},
            {"required": ["required-too-long"]},
        )
        for contract in contracts:
            with self.subTest(contract=contract):
                self.assertEqual(codes(schema.validate(
                    "x", contract, limits=limits))[0], "limit.string")

        class LongKeyMapping(Mapping[str, dict[str, object]]):
            def __len__(self) -> int:
                return 1

            def __iter__(self) -> Iterator[str]:
                yield "urn:test:registry-key-too-long:v1"

            def __getitem__(self, key: str) -> dict[str, object]:
                raise AssertionError(f"long registry key was resolved: {key}")

        self.assertEqual(codes(schema.validate(
            1, {}, registry=LongKeyMapping(), limits=limits))[0], "limit.string")

    def test_unknown_remote_file_and_cyclic_refs_are_rejected(self) -> None:
        refs = (
            ("urn:test:missing:v2", "schema.ref_unknown"),
            ("urn:missing", "schema.ref_unsafe"),
            ("https://example.invalid/schema", "schema.ref_unsafe"),
            ("file:///tmp/schema.json", "schema.ref_unsafe"),
            ("../schema.json", "schema.ref_unsafe"),
        )
        for reference, expected in refs:
            with self.subTest(reference=reference):
                result = schema.validate(1, {"$ref": reference})
                self.assertIn(expected, codes(result))
        cycle = [
            {"$id": "urn:test:a:v2", "$ref": "urn:test:b:v2"},
            {"$id": "urn:test:b:v2", "$ref": "urn:test:a:v2"},
        ]
        result = schema.validate(1, {"$ref": "urn:test:a:v2"}, registry=cycle)
        self.assertIn("schema.ref_cycle", codes(result))

    def test_unsupported_keyword_is_rejected_at_every_schema_depth(self) -> None:
        contracts = (
            {"format": "date"},
            {"properties": {"x": {"format": "date"}}},
            {"$defs": {"x": {"format": "date"}}},
            {"oneOf": [{"type": "string"}, {"contains": {"const": 1}}]},
        )
        for contract in contracts:
            with self.subTest(contract=contract):
                result = schema.validate({}, contract)
                self.assertIn("schema.unsupported_keyword", codes(result))

    def test_quantified_patterns_require_start_anchor_before_search(self) -> None:
        rejected = ("a*b", "a+$", "a{2}")
        hostile = "a" * schema.Limits().max_string_length
        started = time.monotonic()
        with mock.patch.object(
            schema, "_search_pattern",
            side_effect=AssertionError("unanchored quantifier reached search"),
        ) as search:
            for pattern in rejected:
                with self.subTest(pattern=pattern):
                    self.assertEqual(
                        codes(schema.validate(hostile, {"pattern": pattern})),
                        ["schema.pattern"],
                    )
            search.assert_not_called()
        self.assertLess(
            time.monotonic() - started, 5.0,
            "advisory: pre-search rejection exceeded its bounded-time budget",
        )

        self.assertTrue(schema.validate(
            "xxneedlexx", {"pattern": "needle"}).valid)
        self.assertIn(
            "pattern", codes(schema.validate("haystack", {"pattern": "needle"})))
        self.assertTrue(schema.validate("aaab", {"pattern": "^a*b"}).valid)
        self.assertIn("pattern", codes(
            schema.validate("caaab", {"pattern": "^a*b"})))

        for path in sorted((ROOT / ".agents" / "schemas").glob("*.json")):
            with self.subTest(current_schema=path.name):
                contract = json.loads(path.read_text(encoding="utf-8"))
                result = schema.validate({}, contract)
                self.assertNotIn("schema.pattern", codes(result))

    def test_regex_subset_rejects_nested_or_unanalysable_repetition_before_search(self) -> None:
        unsafe_patterns = (
            "^((a+))+$",
            "^(((a|aa)))+$",
            "^((a{1,3}))+$",
            "^(?:a?)*$",
            "^(?:a|aa)+$",
            "^(?:(?:a+))+$",
            "^(?:a+)(?:a+)$",
            "^a+a+$",
            "^(?P<name>a)+$",
            "^a{10001}$",
        )
        hostile = "a" * 50000 + "!"
        with mock.patch.object(
            schema, "_search_pattern",
            side_effect=AssertionError(
                "unsafe pattern reached regex executor"),
        ) as search:
            for pattern in unsafe_patterns:
                with self.subTest(pattern=pattern):
                    result = schema.validate(hostile, {"pattern": pattern})
                    self.assertEqual(codes(result), ["schema.pattern"])
            search.assert_not_called()
        safe_patterns = (
            "^[a-z0-9]+(?:-[a-z0-9]+)*$",
            "^(?!/)(?!.*//)[^\\u0000-\\u001F]+$",
            "^[A-Z]+-[0-9]+(?:-[A-Z]+-[0-9]+)?$",
        )
        for pattern in safe_patterns:
            with self.subTest(pattern=pattern):
                result = schema.validate("agent-2", {"pattern": pattern})
                self.assertNotIn("schema.pattern", codes(result))

    def test_invalid_schema_shapes_and_regex_are_structured(self) -> None:
        contracts = (
            {"$schema": "https://example.invalid/dialect"},
            {"$id": "https://example.invalid/schema"},
            {"$id": "urn:missing"},
            {"$defs": []},
            {"type": "mystery"},
            {"required": "x"},
            {"properties": []},
            {"minItems": -1},
            {"minimum": True},
            {"pattern": "["},
            {"pattern": "(a+)+$"},
            {"$defs": {"x": {"type": "string"}}, "$ref": "#/$defs/x/properties"},
            {"then": {"type": "string"}},
            {"enum": []},
        )
        for contract in contracts:
            with self.subTest(contract=contract):
                result = schema.validate(None, contract)
                self.assertFalse(result.valid)
                self.assertTrue(codes(result)[0].startswith("schema."))

    def test_depth_schema_node_input_node_string_array_and_error_limits(self) -> None:
        limits = schema.Limits(
            max_depth=3,
            max_schema_nodes=8,
            max_input_nodes=8,
            max_errors=2,
            max_string_length=4,
            max_array_length=3,
            max_pattern_length=20,
        )
        too_deep = {"not": {"not": {"not": {"not": {"const": 1}}}}}
        self.assertIn("limit.depth", codes(
            schema.validate(1, too_deep, limits=limits)))
        many_schema_nodes = {"allOf": [{"const": index} for index in range(9)]}
        node_limits = schema.Limits(max_schema_nodes=8)
        self.assertIn(
            "limit.schema_nodes",
            codes(schema.validate(1, many_schema_nodes, limits=node_limits)),
        )
        self.assertIn(
            "limit.input_nodes", codes(schema.validate(
                {str(index): index for index in range(8)}, {}, limits=limits)))
        self.assertIn("limit.string", codes(
            schema.validate("abcde", {}, limits=limits)))
        self.assertIn("limit.array", codes(
            schema.validate([1, 2, 3, 4], {}, limits=limits)))
        errors = schema.validate(
            {}, {"type": "object", "required": ["a", "b", "c"]},
            limits=schema.Limits(max_errors=2),
        )
        self.assertEqual(len(errors.diagnostics), 2)
        self.assertEqual(errors.diagnostics[-1].code, "limit.errors")
        evaluation_limits = schema.Limits(max_evaluations=1)
        evaluated = schema.validate(
            1, {"allOf": [{"const": 1}, {"const": 1}]}, limits=evaluation_limits)
        self.assertIn("limit.evaluations", codes(evaluated))

    def test_invalid_limit_configuration_is_reported(self) -> None:
        result = schema.validate(None, {}, limits=schema.Limits(max_depth=0))
        self.assertEqual(codes(result), ["limit.configuration"])

    def test_diagnostics_are_exact_stable_and_json_serializable(self) -> None:
        contract = {
            "type": "object", "required": ["b", "a"],
            "additionalProperties": False, "properties": {}
        }
        observed = []
        for _ in range(3):
            result = schema.validate({"z": 1}, contract)
            observed.append(result.as_dict())
            json.dumps(result.as_dict(), sort_keys=True)
        self.assertEqual(observed[0], observed[1])
        self.assertEqual(observed[1], observed[2])
        self.assertEqual(
            [item["code"] for item in observed[0]["diagnostics"]],
            ["required", "required", "additionalProperties"],
        )

    def test_evaluator_and_parser_perform_no_filesystem_or_network_io(self) -> None:
        with mock.patch("builtins.open", side_effect=AssertionError("file access")), \
                mock.patch("socket.socket", side_effect=AssertionError("network access")):
            self.assertTrue(schema.validate("x", {"type": "string"}).valid)
            self.assertEqual(
                markdown.parse_markdown(
                    b"---\nid: \"SPEC-002\"\n---\n# Title\n",
                    allowed_metadata_keys={"id"},
                )["h1"],
                "Title",
            )

    def test_source_ast_has_no_write_network_subprocess_or_dynamic_execution(self) -> None:
        forbidden_imports = {"subprocess",
                             "socket", "urllib", "http", "requests"}
        forbidden_calls = {"eval", "exec", "compile", "open"}
        for name in ("markdown.py", "schema.py"):
            path = ROOT / "scripts" / "contracts" / name
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports = {
                alias.name.split(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, (ast.Import, ast.ImportFrom))
                for alias in node.names
            }
            calls = {
                node.func.id
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            }
            self.assertFalse(imports & forbidden_imports)
            self.assertFalse(calls & forbidden_calls)
            self.assertNotIn("Path", {node.id for node in ast.walk(
                tree) if isinstance(node, ast.Name)})


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / ".agents" / "tools"
FINGERPRINT_PATH = TOOLS / "fingerprint_artifact.py"
IDS_PATH = TOOLS / "check_artifact_ids.py"
SPEC_002 = ROOT / "specs" / "002-harness-v2" / "spec.md"
EXPECTED_SOURCE_REVISION = "sha256:8d411302e1f1fe44028e6110820bc35b5ce777676e1e044a0c905dc6ab4f1626"
EXPECTED_ITEMS = json.loads(r'''{
  "SPEC-002#REQ-001":"sha256:137e22e48118baee094ecb8036922581cd55f2d0f6bc13e03817e05e8425f1a9",
  "SPEC-002#REQ-002":"sha256:d160a2a4f1177443df03532aaf9d69176d6c827286e3138ce252d8373ea398df",
  "SPEC-002#REQ-003":"sha256:4cd89d8eb27a194825143002aead8331941c911649fded66f6e6deb97f9dd14f",
  "SPEC-002#REQ-004":"sha256:4759ea7b098b79f8f287bbcbf45109b3b022a6c88af95b6c39433b1b40a2ead6",
  "SPEC-002#REQ-005":"sha256:1941a921f60a0aa345427c072304bfd0fa9a8b90c0fc24dcbe069e20423a9a80",
  "SPEC-002#REQ-006":"sha256:7beb8bd4dd950720eb08f32dc019d2794575e28fa5e0e23fb65a04a9161a51a7",
  "SPEC-002#REQ-007":"sha256:440b480f149ec22e74175139402494ed0de23ec56a3b2282352965cbb355dff8",
  "SPEC-002#REQ-008":"sha256:88e3235717ebc94f592a8d4da6f16716f1fdc1ea13dc368ccd50f1ccae1cf6dc",
  "SPEC-002#REQ-009":"sha256:85edf54d49f63255d69d730b81c406ecb3cf8b0972996aed39eac8efcb0e29fc",
  "SPEC-002#REQ-010":"sha256:d7aebcaa46af8bc3246ea615aceea28f7c721801edb4065723d61a6f943344c6",
  "SPEC-002#REQ-011":"sha256:0ec13c884540734f608d0034440203e2fdada6a7f9d8a4cc9ee0c9fddba91518",
  "SPEC-002#REQ-012":"sha256:4842da9f22d6df2d1758c068f802e2da8ae4c270a6839b95a622e914f9bc2f53",
  "SPEC-002#REQ-013":"sha256:63e1fdcf1dfdc13825d3ef879a51a27427b54123d2e0d5c07170faf54fe65240",
  "SPEC-002#REQ-014":"sha256:ad9abca5e03c2f932c7e0e96db73daf2c161b31115d72f6b0333086547ce4a74",
  "SPEC-002#REQ-015":"sha256:f1f49571d0a09c241d2a6626404007564efffb5d629680127ab07905863a7718",
  "SPEC-002#REQ-016":"sha256:005316790c3d60388e1927cd2a97123ef2078d6200810594df787e3f845f82a3",
  "SPEC-002#REQ-017":"sha256:83faf59819bec7fc5d465b31284158b852115b5c031a1a4c3ad35723d1c5fad6",
  "SPEC-002#REQ-018":"sha256:493871c1c89f4da5b34dd53234c45abacfec707efdd563bcf489c96cba353604",
  "SPEC-002#REQ-019":"sha256:a694d4f5753bbc59ef3e083e6648052760fd707a3156e325fcfddc6e73a161e1",
  "SPEC-002#REQ-020":"sha256:2140a98b6317c5603c564433986606fc8caac25cce98e5b70cdddf3e2343def9",
  "SPEC-002#REQ-021":"sha256:e5c1ee7e07153e7c36129817915ddb2723e432bc5b27e76432e8739c8312f604",
  "SPEC-002#REQ-022":"sha256:46312275a78ee7358990b34f19a2a785401cf6d63322e0cc874e6f019f794615",
  "SPEC-002#REQ-023":"sha256:31e295b0fe5886b618d353cd36cc56ae8df42759569493e51dd0b8b9dcccd8da",
  "SPEC-002#REQ-024":"sha256:08b404872f15e52057e879469007d49c94924e73d9eff36cac33e85d078a3281",
  "SPEC-002#REQ-025":"sha256:9aafb21a9e1af447be9d7c74fcc0fc498b7e90c6bbae220e3fa4a1eea965b81c",
  "SPEC-002#REQ-026":"sha256:81c33d4af5c795489fa1bc8f427e7ea140338b991d80da50fbdeb9bcd5be61a4",
  "SPEC-002#REQ-027":"sha256:640510fef4425fb8cea600efc18bfd0ed8c1a05a248fe5f58c9789bcd7c36ca4",
  "SPEC-002#REQ-028":"sha256:48ba10f6b4db238d04617f3840c903e0f3ab32834f0124e2fd2aef6a6a4955ef",
  "SPEC-002#REQ-029":"sha256:055f8afcfd598c406fcaf5b2177f57ad12ab29ced789e2982cd4e6c466a56db8",
  "SPEC-002#REQ-030":"sha256:be67f7db7550936fecdaeb8bb53e29b5ab196f0ac1d1a91408a46c735a1e8f75",
  "SPEC-002#REQ-031":"sha256:8581f2d7535cdc836f05b92a7a0703f8671975ddea50be256eed9a709e95ee1f",
  "SPEC-002#REQ-032":"sha256:f25d36880fa8371246799903d2d712b7fce18cbe0abc0c07d16d9bb40547d3f4",
  "SPEC-002#REQ-033":"sha256:9652b4f669fd89d4ad49feae5e331ac6cd9c6dda40547a7a4f597dd33ebfe506",
  "SPEC-002#REQ-034":"sha256:fd00134beee01ce8c4db8302ccbd6128c52aa3a13909f5c202f911b68d47b911",
  "SPEC-002#REQ-035":"sha256:04faf064096aaf77937f191a54ccbbf44dc19aa5ab112db9304977c8319d5bdd",
  "SPEC-002#REQ-036":"sha256:7a243c657812a8b4bb936a9e40da0f9ea0a459063a4388133abce75c3a599f62",
  "SPEC-002#REQ-037":"sha256:1d38447608934a05fb13accda358174afc961cc4537b652170499cebd0e9317c",
  "SPEC-002#REQ-038":"sha256:fc21de810d58a2b60fdcc39894563a383f22afa41420dc06b55fd95c1ddb9837",
  "SPEC-002#REQ-039":"sha256:8c12f8fa77d0a4b614a11050d504f1f353e2845c6248d6a4bbd7061fc25c254e",
  "SPEC-002#REQ-040":"sha256:2dc31c478cfafe41d62dc52c0f896e565595f80330d1321cba1a601a16c833d6",
  "SPEC-002#REQ-041":"sha256:36e12856262c86929c326dd78f726b9b36625cf2ffbc0c402017bf6f10cd4b3a",
  "SPEC-002#REQ-042":"sha256:0fd2301bd9dd159fd993fa01d388a3f3bec89b803690b5810211069c516d4ff5",
  "SPEC-002#REQ-043":"sha256:1c518dad7778947d0b8af5265c557faed82644bdd1b9f18893f23f9e34cb557a",
  "SPEC-002#REQ-044":"sha256:55cca33207938bc96b3a336ddd52e9582dc4fe74c91964d4a0e76e2306536332",
  "SPEC-002#REQ-045":"sha256:1e37f576db8204adabad3b1baf14e7d90a12cbe30945c33f781052278830cd82",
  "SPEC-002#REQ-046":"sha256:e9535a90f32da469b8e4039984eb20698cb3227468410defc23acfe6383292f3",
  "SPEC-002#REQ-047":"sha256:03df20a74bbcb05d8cd36ddd8bf47f3a9585b009d866583be34a8e4d96d6141b",
  "SPEC-002#REQ-048":"sha256:63ff608e6c91f3cdd0c734efa787a413b5fc8ecb830e0893e123b8f1fd2dc586",
  "SPEC-002#REQ-049":"sha256:e649f77a014761952970e32001778948d6902598f6c42bb9b38bfb8d4fbf82e2",
  "SPEC-002#REQ-050":"sha256:2caefc26259deca890b0a029b542cef7ea6abf0a78c644eb75d0944ab49535f0",
  "SPEC-002#REQ-051":"sha256:c41d4013041555ac76389859e96c639658416210637efbb4ef268473c35214d7",
  "SPEC-002#REQ-052":"sha256:4a4bd4c792111b5881e678dd18b62d65c041eebe76be271dd2877d4f7a480b00",
  "SPEC-002#REQ-053":"sha256:b0eb0aeedf605330ef1d7d5bb9a10b209d5a9faed404d534db2a222c6c605976",
  "SPEC-002#REQ-054":"sha256:d229eb6cd6a333652306e3570848d8bcadd31cb82a12b50dc6b05f04d73e7764",
  "SPEC-002#REQ-055":"sha256:26a871203a7b5d0ca61d878d669ffaa94dd47b69cf3e06571ea74dd6eb1b007b",
  "SPEC-002#REQ-056":"sha256:aa083917621075ea0a572966ae26fc57612e2389b55968d28bba6b20274109fb",
  "SPEC-002#REQ-057":"sha256:676de72a42026e0f7ff9e329950ae2be1329dca50240ce07cad58f506d64e85d",
  "SPEC-002#REQ-058":"sha256:2f8d9ce1ae57f9726a5382510f59983f9ceefb156c4a6db05d73a78bec3360f0",
  "SPEC-002#REQ-059":"sha256:937e10f404b7ad1bda8b9263d6a3797e6f608c6bbcf5020dd9cb7478a70485f1",
  "SPEC-002#AC-001":"sha256:0b5d518f6f6a769704d088d99688ea864f6ee6131acb38a989c36fa73862f175",
  "SPEC-002#AC-002":"sha256:d3ff08b17fefc19da14daba5903eca45d8ffad98dd42c496bba376caffae959e",
  "SPEC-002#AC-003":"sha256:fe15502bacace59fe45f29203abb7f26e851bc888f0265876db8f6229af55b9e",
  "SPEC-002#AC-004":"sha256:d9e4bf61dd451aafb9f89e0d4660c34d0112cfa2032cc594233e682e0fb9876d",
  "SPEC-002#AC-005":"sha256:7a0c2a3ef3d8b95f06162f042832ca8edd656dd73e2bc1fa20e84c74c7562909",
  "SPEC-002#AC-006":"sha256:3b0dc3d4960151491c42db8fc558ec4ac907da3bea574066b9f693d7a41e9426",
  "SPEC-002#AC-007":"sha256:c72976a3b8c39b60f76a93fe98c9421ef1c3261ac93bfb1d0718c56a5dcf800b",
  "SPEC-002#AC-008":"sha256:2b9d1b1f6c01b7a3466357b9c620415a2e5f52702b21cedd3f9b09fd47729eda",
  "SPEC-002#AC-009":"sha256:78265526c99188c7b86c9a82c0110dea6c7fd27482c7b6465e63808c75d4b093",
  "SPEC-002#AC-010":"sha256:f539f80185d94bac5ec3d93196ab5045f4022b922d6e95da703cb2173be12a78",
  "SPEC-002#AC-011":"sha256:e0db0655bdf83ada5d28a23506f49af842608ea5c1a8b491b59656fca307956c",
  "SPEC-002#AC-012":"sha256:c89b7304086e73764b008c7126ccf00cb85d0fb110c1410c56a9c859d5e0006f",
  "SPEC-002#AC-013":"sha256:0cf2815189beaadad1cf03c761960fb965be71f4856bd0a26a2f30a12fdfe43d",
  "SPEC-002#AC-014":"sha256:092b99da66fce9ef45df33da9a1e347fbaacf96dea90f449c3a29bbe9b19d146",
  "SPEC-002#AC-015":"sha256:7a5ff15f37d7e08d4414739e3c63d8db8e13733282824990ab6d8f1c9172ff53",
  "SPEC-002#AC-016":"sha256:0d676f0292cb82e36d696ca2589f1e8fb41ad420c5f937224b118297e34b6fa0"
}''')


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fingerprint = load_module("artifact_fingerprint_test", FINGERPRINT_PATH)
artifact_ids = load_module("artifact_ids_test", IDS_PATH)


def document(identifier: str, body: str, *, kind: str = "specification", namespace: str | None = None) -> str:
    extra = f'namespace: "{namespace}"\n' if namespace else ""
    return (
        "---\n"
        "schema_version: 2\n"
        f'id: "{identifier}"\n'
        f'type: "{kind}"\n'
        '[SOURCES]\n'
        f"{extra}"
        'sources: ["test"]\n'
        'status: "draft"\n'
        "---\n\n"
        f"# {identifier}\n\n{body}\n"
    ).replace("[SOURCES]\n", "")


class FingerprintTests(unittest.TestCase):
    def test_spec_002_exact_golden_overall_and_all_75_items(self) -> None:
        result = fingerprint.fingerprint_artifact(
            ROOT, "specs/002-harness-v2/spec.md")
        self.assertEqual(result["source_revision"], EXPECTED_SOURCE_REVISION)
        self.assertEqual(result["item_revisions"], EXPECTED_ITEMS)
        self.assertEqual(len(result["item_revisions"]), 75)

    def test_status_crlf_nfc_and_trailing_whitespace_are_ignored(self) -> None:
        base = document("SPEC-100", "## Réseau\n\n**REQ-001**: Café\n")
        variants = (
            base.replace('status: "draft"', 'status: "approved"'),
            base.replace("\n", "\r\n"),
            base.replace("Réseau", "Re\u0301seau").replace(
                "Café", "Cafe\u0301"),
            base.replace("## Réseau\n\n", "## Réseau  \t\n\n").replace(
                "Café\n", "Café  \t\n") + "\n\t\n",
        )
        expected = fingerprint.fingerprint_bytes(base.encode())
        for value in variants:
            with self.subTest(value=value[:30]):
                self.assertEqual(fingerprint.fingerprint_bytes(
                    value.encode()), expected)

    def test_body_source_and_section_order_changes_but_json_syntax_does_not(self) -> None:
        base = document(
            "SPEC-100",
            "## First\n\n**REQ-001**: One\n\n## Second\n\n**REQ-002**: Two\n",
        )
        before = fingerprint.fingerprint_bytes(base.encode())
        changes = (
            base.replace("**REQ-001**: One", "**REQ-001**: Changed"),
            base.replace('sources: ["test"]', 'sources: ["changed-source"]'),
            base.replace(
                "## First\n\n**REQ-001**: One\n\n## Second\n\n**REQ-002**: Two",
                "## Second\n\n**REQ-002**: Two\n\n## First\n\n**REQ-001**: One",
            ),
        )
        for changed in changes:
            self.assertNotEqual(
                before["source_revision"],
                fingerprint.fingerprint_bytes(changed.encode())[
                    "source_revision"],
            )
        syntax_only = base.replace(
            'type: "specification"\nsources: ["test"]',
            'sources: [ "test" ]\ntype: "specification"',
        )
        self.assertEqual(
            before["source_revision"],
            fingerprint.fingerprint_bytes(syntax_only.encode())[
                "source_revision"],
        )

    def test_one_source_item_change_is_local(self) -> None:
        base = document(
            "SPEC-100", "## Needs\n\n**REQ-001**: One\n\n**REQ-002**: Two\n")
        changed = base.replace("**REQ-001**: One", "**REQ-001**: Changed")
        before = fingerprint.fingerprint_bytes(base.encode())
        after = fingerprint.fingerprint_bytes(changed.encode())
        self.assertNotEqual(before["item_revisions"]["SPEC-100#REQ-001"],
                            after["item_revisions"]["SPEC-100#REQ-001"])
        self.assertEqual(before["item_revisions"]["SPEC-100#REQ-002"],
                         after["item_revisions"]["SPEC-100#REQ-002"])

    def test_item_ends_at_next_marker_or_h2_and_fences_do_not_create_items(self) -> None:
        value = document(
            "SPEC-100",
            "## Needs\n\n**REQ-001**: One\n\n### Detail\nText\n\n```\n**REQ-999**: fake\n```\n\n**AC-001**: Accept\n\n## End\nignored",
        )
        result = fingerprint.fingerprint_bytes(value.encode())
        self.assertEqual(list(result["item_revisions"]), [
                         "SPEC-100#REQ-001", "SPEC-100#AC-001"])
        metadata, body, masked = fingerprint._normalized_parts(value.encode())
        items = fingerprint._item_projections(metadata, body, masked)
        self.assertEqual(items[0]["text"],
                         "**REQ-001**: One\n\n### Detail\nText\n\n```\n**REQ-999**: fake\n```")
        self.assertEqual(items[1]["text"], "**AC-001**: Accept")

    def test_plain_id_leading_prose_is_not_an_item_or_item_boundary(self) -> None:
        value = document(
            "SPEC-100",
            "**REQ-001**: One\n\nTASK-218 makes no fixes.\nREQ-999: prose only.\nAC-010 remains satisfied.\n\nDetail stays in the item.",
        )
        result = fingerprint.fingerprint_bytes(value.encode())
        self.assertEqual(list(result["item_revisions"]), ["SPEC-100#REQ-001"])
        metadata, body, masked = fingerprint._normalized_parts(value.encode())
        item = fingerprint._item_projections(metadata, body, masked)[0]
        self.assertIn("TASK-218 makes no fixes.", item["text"])
        self.assertIn("Detail stays in the item.", item["text"])

    def test_artifact_and_companion_source_ids_use_global_id_grammar(self) -> None:
        valid_ids = (
            "SPEC-002", "PLAN-002", "TASKS-002", "ADR-012",
            "HANDOFF-003", "REVIEW-004", "EVIDENCE-005",
            "SPEC-002-FRAG-001", "PLAN-002-FRAG-001",
        )
        for identifier in valid_ids:
            with self.subTest(valid=identifier):
                self.assertEqual(
                    fingerprint.fingerprint_bytes(
                        document(identifier, "Text").encode())["source_id"],
                    identifier,
                )
        for identifier in ("../BAD", "spec-002", "free string", "SPEC", "SPEC-2-extra"):
            with self.subTest(invalid=identifier), self.assertRaises(fingerprint.FingerprintError):
                fingerprint.fingerprint_bytes(
                    document(identifier, "Text").encode())

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "spec.md").write_text(
                document("SPEC-100", "Text"), encoding="utf-8")
            result = fingerprint.fingerprint_artifact(root, "spec.md")
            for source_id in ("../BAD", "spec-100", "free string"):
                companion = root / "items.json"
                companion.write_text(json.dumps({
                    "schema_version": 2,
                    "source_id": source_id,
                    "source_revision": result["source_revision"],
                    "item_revisions": {},
                }), encoding="utf-8")
                with self.subTest(companion=source_id), self.assertRaises(fingerprint.FingerprintError):
                    fingerprint.fingerprint_artifact(
                        root, "spec.md", verify="items.json")

    def test_verify_rejects_duplicate_keys_and_reports_exact_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "spec.md").write_text(document("SPEC-100",
                                                   "**REQ-001**: One"), encoding="utf-8")
            result = fingerprint.fingerprint_artifact(root, "spec.md")
            companion = root / "items.json"
            companion.write_text(json.dumps({
                "schema_version": 2,
                "source_id": "SPEC-100",
                "source_revision": result["source_revision"],
                "item_revisions": {"SPEC-100#REQ-001": "sha256:" + "0" * 64, "SPEC-100#REQ-999": "sha256:" + "1" * 64},
            }), encoding="utf-8")
            checked = fingerprint.fingerprint_artifact(
                root, "spec.md", verify="items.json")
            self.assertFalse(checked["valid"])
            self.assertEqual([item["code"] for item in checked["diagnostics"]], [
                             "ITEM_CHANGED", "ITEM_REMOVED"])
            companion.write_text(
                '{"schema_version":2,"schema_version":2}', encoding="utf-8")
            with self.assertRaisesRegex(fingerprint.FingerprintError, "duplicate key"):
                fingerprint.fingerprint_artifact(
                    root, "spec.md", verify="items.json")

    def test_safe_paths_symlinks_controls_drives_and_root_ancestors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "spec.md").write_text(document("SPEC-100", "Text"), encoding="utf-8")
            for unsafe in ("../spec.md", "/spec.md", "C:/spec.md", "bad\\spec.md", "bad\x01.md"):
                with self.subTest(unsafe=unsafe), self.assertRaises(fingerprint.FingerprintError):
                    fingerprint.fingerprint_artifact(root, unsafe)
            if hasattr(os, "symlink"):
                os.symlink(root / "spec.md", root / "link.md")
                with self.assertRaises(fingerprint.FingerprintError):
                    fingerprint.fingerprint_artifact(root, "link.md")
                container = root / "real"
                container.mkdir()
                os.symlink(container, root / "alias")
                with self.assertRaises(fingerprint.FingerprintError):
                    fingerprint.fingerprint_artifact(root / "alias", "spec.md")

    def test_cli_human_json_help_deterministic_and_redacted(self) -> None:
        args = ["--root", str(ROOT), "--input", "specs/002-harness-v2/spec.md"]
        outputs = []
        for output_format in ("human", "json"):
            streams = []
            for _ in range(2):
                stream = io.StringIO()
                with contextlib.redirect_stdout(stream):
                    self.assertEqual(fingerprint.main(
                        args + ["--format", output_format]), 0)
                streams.append(stream.getvalue())
            self.assertEqual(streams[0], streams[1])
            outputs.append(streams[0])
        self.assertIn(EXPECTED_SOURCE_REVISION, outputs[0])
        self.assertEqual(json.loads(outputs[1])[
                         "source_revision"], EXPECTED_SOURCE_REVISION)
        help_output = io.StringIO()
        with contextlib.redirect_stdout(help_output):
            self.assertEqual(fingerprint.main(["--help"]), 0)
        for term in ("usage", "read-only", "Python", "exit"):
            self.assertIn(term.lower(), help_output.getvalue().lower())


class GitRepositoryCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def git(self, *arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments], cwd=self.root, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        ).stdout.strip()

    def write(self, path: str, value: str) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value, encoding="utf-8")

    def commit(self, message: str = "fixture") -> None:
        self.git("add", "-A")
        self.git("commit", "-qm", message)


class ArtifactIdHistoryTests(GitRepositoryCase):
    def test_unborn_is_complete_empty_history_and_candidate_is_available(self) -> None:
        report = artifact_ids.query_ids(
            self.root, ["SPEC-001", "SPEC-001#REQ-001"])
        self.assertTrue(report["history"]["complete"])
        self.assertEqual(report["history"]["commits_scanned"], 0)
        self.assertEqual([item["state"] for item in report["candidates"]], [
                         "available", "available"])
        self.assertTrue(report["valid"])

    def test_deleted_before_current_is_still_issued_and_reuse_is_blocked(self) -> None:
        self.write("spec.md", document("SPEC-100", "**REQ-001**: One"))
        self.commit("issue")
        (self.root / "spec.md").unlink()
        self.commit("delete")
        report = artifact_ids.query_ids(
            self.root, ["SPEC-100", "SPEC-100#REQ-001"])
        self.assertFalse(report["valid"])
        self.assertEqual([item["state"]
                         for item in report["candidates"]], ["reused", "reused"])

    def test_all_branches_tags_and_detached_head_are_included(self) -> None:
        self.write("base.md", document("SPEC-100", "Text"))
        self.commit("base")
        base = self.git("rev-parse", "HEAD")
        self.git("tag", "issued-tag")
        self.git("checkout", "-qb", "other")
        self.write("other.md", document("SPEC-200", "Text"))
        self.commit("other")
        self.git("checkout", "--detach", "-q", base)
        self.write("detached.md", document("SPEC-300", "Text"))
        self.commit("detached")
        report = artifact_ids.query_ids(
            self.root, ["SPEC-100", "SPEC-200", "SPEC-300"])
        self.assertEqual([item["historically_issued"]
                         for item in report["candidates"]], [True, True, True])

    def test_current_owner_templates_are_omitted_before_v2_parsing(self) -> None:
        template = document("SPEC-100", "**REQ-001**: Template item").replace(
            'sources: ["test"]',
            'sources: ["test"]\nsources: ["malformed-template"]',
        )
        self.write(
            ".agents/skills/write-spec/assets/example.template.md", template)
        self.write(
            ".agents/skills/write-spec/assets/example.v2.template.md", template)
        report = artifact_ids.scan_ids(self.root)
        self.assertTrue(report["valid"])
        self.assertTrue(report["history"]["complete"])
        self.assertEqual(report["current"]["artifact_ids"], [])
        self.assertEqual(report["current"]["local_ids"], [])
        self.assertNotIn("CURRENT_DOCUMENT_INVALID", [
            item["code"] for item in report["diagnostics"]])

    def test_committed_then_deleted_owner_templates_never_issue_ids(self) -> None:
        template = document("SPEC-100", "**REQ-001**: Template item").replace(
            'sources: ["test"]',
            'sources: ["test"]\nsources: ["malformed-template"]',
        )
        self.write(
            ".agents/skills/write-spec/assets/example.template.md", template)
        self.write(
            ".agents/skills/write-spec/assets/example.v2.template.md", template)
        self.commit("template only")
        shutil.rmtree(self.root / ".agents")
        self.commit("delete templates")
        report = artifact_ids.query_ids(
            self.root, ["SPEC-100", "SPEC-100#REQ-001"])
        self.assertTrue(report["valid"])
        self.assertTrue(report["history"]["complete"])
        self.assertEqual([item["state"] for item in report["candidates"]], [
            "available", "available"])
        self.assertNotIn("HISTORY_DOCUMENT_INVALID", [
            item["code"] for item in report["diagnostics"]])

    def test_template_near_misses_and_normal_artifacts_remain_fail_closed(self) -> None:
        malformed = document("SPEC-100", "**REQ-001**: Real item").replace(
            'sources: ["test"]',
            'sources: ["test"]\nsources: ["duplicate"]',
        )
        self.write(
            ".agents/skills/write-spec/assets/spec.template-copy.md", malformed)
        self.write("specs/template-feature/spec.md", malformed.replace(
            'id: "SPEC-100"', 'id: "SPEC-101"'))
        current = artifact_ids.scan_ids(self.root)
        self.assertFalse(current["valid"])
        self.assertEqual(
            [item["code"] for item in current["diagnostics"]].count(
                "CURRENT_DOCUMENT_INVALID"),
            2,
        )
        self.commit("malformed non-templates")
        shutil.rmtree(self.root / ".agents")
        shutil.rmtree(self.root / "specs")
        self.commit("delete malformed non-templates")
        historical = artifact_ids.scan_ids(self.root)
        self.assertTrue(historical["valid"])
        self.assertFalse(historical["history"]["complete"])
        self.assertIn("HISTORY_DOCUMENT_INVALID", [
            item["code"] for item in historical["diagnostics"]])

    def test_parent_children_metadata_is_scanned_without_owner_shape_validation(self) -> None:
        parent = document("SPEC-100", "**REQ-001**: Parent item").replace(
            'sources: ["test"]',
            'sources: ["test"]\nchildren: [{"id":"SPEC-100-FRAG-001","path":"fragments/001.md"}]',
        )
        self.write("spec.md", parent)
        self.commit("split parent")
        report = artifact_ids.scan_ids(self.root)
        self.assertTrue(report["valid"])
        self.assertTrue(report["history"]["complete"])
        self.assertEqual(report["current"]["artifact_ids"], ["SPEC-100"])
        self.assertEqual(report["current"]["local_ids"], [
            "SPEC-100#REQ-001"])
        self.assertNotIn("CURRENT_DOCUMENT_INVALID", [
            item["code"] for item in report["diagnostics"]])

    def test_prose_id_prefixes_do_not_duplicate_current_or_historical_ids(self) -> None:
        self.write("tasks.md", document(
            "TASKS-100",
            "### TASK-001: Real declaration\n\nTASK-001 makes no fixes.\nAC-010 remains prose.\nREQ-007 remains prose.",
            kind="task-graph",
            namespace="PLAN-100",
        ))
        self.commit("declaration-aware")
        report = artifact_ids.scan_ids(self.root)
        self.assertTrue(report["valid"])
        self.assertEqual(report["current"]["local_ids"], ["PLAN-100#TASK-001"])
        query = artifact_ids.query_ids(self.root, ["PLAN-100#TASK-001"])
        self.assertTrue(query["candidates"][0]["historically_issued"])

    def test_same_local_id_under_different_parents_is_allowed(self) -> None:
        self.write("one.md", document("SPEC-100", "**REQ-001**: One"))
        self.write("two.md", document("SPEC-200", "**REQ-001**: Two"))
        report = artifact_ids.scan_ids(self.root)
        self.assertTrue(report["valid"])
        self.assertEqual(report["current"]["local_ids"], [
                         "SPEC-100#REQ-001", "SPEC-200#REQ-001"])

    def test_duplicate_current_global_local_and_task_namespace_are_rejected(self) -> None:
        self.write("one.md", document(
            "SPEC-100", "**REQ-001**: One\n\n**REQ-001**: Duplicate"))
        self.write("two.md", document("SPEC-100", "Text"))
        self.write("tasks-a.md", document("TASKS-100",
                   "### TASK-001: One", kind="task-graph", namespace="PLAN-100"))
        self.write("tasks-b.md", document("TASKS-101",
                   "### TASK-002: Two", kind="task-graph", namespace="PLAN-100"))
        report = artifact_ids.scan_ids(self.root)
        self.assertFalse(report["valid"])
        codes = [item["code"] for item in report["diagnostics"]]
        self.assertIn("CURRENT_ARTIFACT_DUPLICATE", codes)
        self.assertIn("CURRENT_LOCAL_DUPLICATE", codes)
        self.assertIn("TASK_NAMESPACE_DUPLICATE", codes)

    def test_malformed_v2_recovers_unambiguous_ids_and_namespace_but_fails_closed(self) -> None:
        malformed = document(
            "TASKS-100", "### TASK-001: One",
            kind="task-graph", namespace="PLAN-100",
        ).replace('sources: ["test"]', 'sources: ["test"]\nsources: ["duplicate"]')
        extracted = artifact_ids._extract_document(malformed.encode())
        self.assertTrue(extracted.malformed)
        self.assertEqual(extracted.artifacts, ["TASKS-100"])
        self.assertEqual(extracted.locals, ["PLAN-100#TASK-001"])
        self.assertEqual(extracted.task_namespaces, ["PLAN-100"])

        self.write("tasks.md", malformed)
        current = artifact_ids.scan_ids(self.root)
        self.assertFalse(current["valid"])
        self.assertIn("CURRENT_DOCUMENT_INVALID", [
            item["code"] for item in current["diagnostics"]])
        self.commit("malformed v2")
        (self.root / "tasks.md").unlink()
        self.commit("delete malformed v2")
        historical = artifact_ids.query_ids(
            self.root,
            ["TASKS-100", "PLAN-100#TASK-001", "SPEC-999"],
        )
        self.assertFalse(historical["history"]["complete"])
        self.assertIn("HISTORY_DOCUMENT_INVALID", [
            item["code"] for item in historical["diagnostics"]])
        self.assertEqual(
            [item["state"] for item in historical["candidates"]],
            ["reused", "reused", "unverified"],
        )

    def test_malformed_v2_never_guesses_an_ambiguous_namespace(self) -> None:
        malformed = document(
            "TASKS-100", "### TASK-001: One",
            kind="task-graph", namespace="PLAN-100",
        ).replace(
            'namespace: "PLAN-100"',
            'namespace: "PLAN-100"\nnamespace: "PLAN-200"',
        )
        extracted = artifact_ids._extract_document(malformed.encode())
        self.assertTrue(extracted.malformed)
        self.assertEqual(extracted.artifacts, ["TASKS-100"])
        self.assertEqual(extracted.locals, [])
        self.assertEqual(
            extracted.task_namespaces, ["PLAN-100", "PLAN-200"])

    def test_shallow_history_is_unverified_and_blocks_new_but_not_known_current(self) -> None:
        self.write("old.md", document("SPEC-100", "Text"))
        self.commit("old")
        self.write("new.md", document("SPEC-200", "Text"))
        self.commit("new")
        with tempfile.TemporaryDirectory() as clone_dir:
            clone = Path(clone_dir) / "clone"
            subprocess.run(["git", "clone", "-q", "--depth", "1",
                           self.root.as_uri(), str(clone)], check=True)
            report = artifact_ids.query_ids(clone, ["SPEC-200", "SPEC-300"])
            self.assertFalse(report["history"]["complete"])
            self.assertEqual([item["state"] for item in report["candidates"]], [
                             "existing", "unverified"])
            self.assertFalse(report["valid"])
            existing_output = io.StringIO()
            with contextlib.redirect_stdout(existing_output):
                self.assertEqual(artifact_ids.main([
                    "query", "--root", str(clone),
                    "--candidate", "SPEC-200", "--format", "json",
                ]), 0)
            existing_report = json.loads(existing_output.getvalue())
            self.assertTrue(existing_report["valid"])
            self.assertFalse(existing_report["history"]["complete"])
            new_output = io.StringIO()
            with contextlib.redirect_stdout(new_output):
                self.assertEqual(artifact_ids.main([
                    "query", "--root", str(clone),
                    "--candidate", "SPEC-300", "--format", "json",
                ]), 2)
            self.assertFalse(json.loads(new_output.getvalue())["valid"])

    def test_missing_object_and_resource_bounds_are_explicit_unverified(self) -> None:
        self.write("one.md", document("SPEC-100", "Text"))
        self.commit("one")
        self.write("two.md", document("SPEC-200", "Text"))
        self.commit("two")
        bounded = artifact_ids.scan_ids(
            self.root, limits=artifact_ids.HistoryLimits(max_commits=1))
        self.assertFalse(bounded["history"]["complete"])
        self.assertIn("HISTORY_LIMIT", [item["code"]
                      for item in bounded["diagnostics"]])
        original = artifact_ids._run_git

        def fail_blob(root, arguments, **kwargs):
            if arguments and arguments[0] == "cat-file":
                raise artifact_ids.HistoryError("Git object could not be read")
            return original(root, arguments, **kwargs)

        with mock.patch.object(artifact_ids, "_run_git", side_effect=fail_blob):
            broken = artifact_ids.scan_ids(self.root)
        self.assertFalse(broken["history"]["complete"])
        self.assertIn("HISTORY_UNREADABLE", [
                      item["code"] for item in broken["diagnostics"]])

    def test_candidate_controls_and_symlink_repository_root_are_rejected(self) -> None:
        for candidate in ("../SPEC-100", "C:SPEC-100", "SPEC-100\x01"):
            with self.subTest(candidate=candidate), self.assertRaises(artifact_ids.HistoryError):
                artifact_ids.query_ids(self.root, [candidate])
        if hasattr(os, "symlink"):
            alias = self.root.parent / (self.root.name + "-alias")
            try:
                os.symlink(self.root, alias)
                with self.assertRaises(artifact_ids.HistoryError):
                    artifact_ids.scan_ids(alias)
            finally:
                alias.unlink(missing_ok=True)

    def test_git_and_filesystem_are_not_mutated_and_output_is_deterministic(self) -> None:
        self.write("spec.md", document("SPEC-100", "**REQ-001**: One"))
        self.commit()
        before_head = self.git("rev-parse", "HEAD")
        before_status = self.git(
            "status", "--porcelain=v2", "--untracked-files=all")
        before_index = hashlib.sha256(
            (self.root / ".git" / "index").read_bytes()).hexdigest()
        first = artifact_ids.query_ids(self.root, ["SPEC-100", "SPEC-999"])
        second = artifact_ids.query_ids(self.root, ["SPEC-100", "SPEC-999"])
        self.assertEqual(first, second)
        self.assertEqual(self.git("rev-parse", "HEAD"), before_head)
        self.assertEqual(self.git("status", "--porcelain=v2",
                         "--untracked-files=all"), before_status)
        self.assertEqual(hashlib.sha256(
            (self.root / ".git" / "index").read_bytes()).hexdigest(), before_index)

    def test_real_checkout_omits_all_ten_v2_owner_templates(self) -> None:
        templates = sorted(ROOT.glob(
            ".agents/skills/*/assets/*.v2.template.md"))
        self.assertEqual(len(templates), 10)
        report = artifact_ids.scan_ids(ROOT)
        self.assertTrue(report["valid"])
        self.assertTrue(report["history"]["complete"])
        codes = [item["code"] for item in report["diagnostics"]]
        self.assertNotIn("CURRENT_DOCUMENT_INVALID", codes)
        self.assertNotIn("HISTORY_DOCUMENT_INVALID", codes)

    def test_cli_query_and_scan_human_json_and_stable_exits(self) -> None:
        for args, expected in ((["scan"], 0), (["query", "--candidate", "SPEC-100"], 0)):
            for output_format in ("human", "json"):
                streams = []
                for _ in range(2):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(artifact_ids.main(
                            args + ["--root", str(self.root), "--format", output_format]), expected)
                    streams.append(output.getvalue())
                self.assertEqual(streams[0], streams[1])
                self.assertNotIn("Traceback", streams[0])
                if output_format == "json":
                    json.loads(streams[0])
        help_output = io.StringIO()
        with contextlib.redirect_stdout(help_output):
            self.assertEqual(artifact_ids.main(["--help"]), 0)
        for term in ("query", "scan", "read-only", "Git", "Python", "exit"):
            self.assertIn(term.lower(), help_output.getvalue().lower())


class GitProcessBoundTests(unittest.TestCase):
    def test_stdout_and_stderr_are_bounded_incrementally_and_producer_is_stopped(self) -> None:
        original_popen = subprocess.Popen
        processes = []
        producers = iter((
            "import os\nchunk = b'x' * 4096\nwhile True:\n    os.write(1, chunk)\n",
            "import os\nchunk = b'y' * 4096\nwhile True:\n    os.write(2, chunk)\n",
            "import os\nchunk = b'z' * 4096\nwhile True:\n    os.write(1, chunk)\n    os.write(2, chunk)\n",
        ))

        def fake_popen(_arguments, **kwargs):
            process = original_popen(
                [sys.executable, "-c", next(producers)],
                stdin=kwargs["stdin"],
                stdout=kwargs["stdout"],
                stderr=kwargs["stderr"],
                cwd=kwargs["cwd"],
                env=kwargs["env"],
            )
            processes.append(process)
            return process

        messages = []
        started = time.monotonic()
        for _ in range(3):
            with mock.patch.object(
                artifact_ids.subprocess, "Popen", side_effect=fake_popen
            ):
                with self.assertRaises(artifact_ids.HistoryError) as raised:
                    artifact_ids._run_git(
                        ROOT,
                        ["rev-parse", "--show-toplevel"],
                        timeout=2,
                        max_output_bytes=4096,
                    )
            messages.append(str(raised.exception))
        self.assertLess(time.monotonic() - started, 4)
        self.assertEqual(messages, [
            "Git inspection output limit exceeded",
            "Git inspection output limit exceeded",
            "Git inspection output limit exceeded",
        ])
        self.assertTrue(
            all(process.poll() is not None for process in processes))


class ArtifactToolStaticSafetyTests(unittest.TestCase):
    def test_ast_has_no_network_dynamic_execution_shell_or_mutating_git(self) -> None:
        forbidden_imports = {"socket", "urllib", "http", "requests", "ftplib"}
        forbidden_calls = {"eval", "exec", "compile", "__import__"}
        mutating_git = {"add", "commit", "checkout", "switch", "branch", "tag",
                        "reset", "clean", "update-ref", "repack", "gc", "fetch", "pull", "push"}
        for path in (FINGERPRINT_PATH, IDS_PATH):
            tree = ast.parse(path.read_text(
                encoding="utf-8"), filename=str(path))
            imports = {
                alias.name.split(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, (ast.Import, ast.ImportFrom))
                for alias in node.names
            }
            self.assertFalse(imports & forbidden_imports)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, forbidden_calls)
                if isinstance(node, ast.keyword) and node.arg == "shell":
                    self.assertIs(node.value, False)
            source = path.read_text(encoding="utf-8")
            self.assertNotIn(".communicate(", source)
            for command in mutating_git:
                self.assertNotIn(f'"{command}"', source)


if __name__ == "__main__":
    unittest.main()

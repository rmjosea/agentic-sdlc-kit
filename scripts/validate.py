#!/usr/bin/env python3
"""Compatibility entrypoint for the source validator."""

from __future__ import annotations

from pathlib import Path

try:
    from scripts.validation import artifacts, distribution, documentation, semantics
except ModuleNotFoundError:
    # Direct ``python3 scripts/validate.py`` invocation.
    from validation import artifacts, distribution, documentation, semantics

ROOT = semantics.ROOT

# Explicit compatibility surface consumed by tests and source tooling.
_EXPORTS = (
    "Any", "CATALOG_SCHEMA_VERSION", "COMMON_CREDENTIAL_RE",
    "COMPLIANCE_EVENT_DEF_FIELDS", "COMPLIANCE_EVENT_FIELDS",
    "COMPLIANCE_TIMESTAMP_RE", "DuplicateJSONObjectKey", "EVIDENCE_CHECK_KINDS",
    "EVIDENCE_CHECK_STATUSES", "EVIDENCE_DEF_FIELDS", "EVIDENCE_FIELDS",
    "EVIDENCE_REVISION_RE", "EVIDENCE_SCHEMA_VERSION", "EVIDENCE_SHA256_RE",
    "LINK_RE", "MARKDOWN_DESTINATION_RE", "NAME_RE", "Optional",
    "PERSONAL_DATA_RE", "PROJECT_CONFIG_PATH", "PROJECT_CONFIG_SCHEMA_VERSION",
    "PROJECT_SCHEMA_PATH", "PROVIDER_PATHS", "PUBLIC_DOCUMENT_PATHS",
    "REVIEW_EVIDENCE_CLASSES", "REVIEW_SIGNALS", "REVIEW_VERDICTS",
    "SENSITIVE_ASSIGNMENT_RE", "SENSITIVE_QUERY_KEYS", "SENSITIVE_QUERY_SUFFIXES",
    "SKILL_GROUPS", "SPEC_STATES", "annotations", "ast", "declared_string_tokens",
    "directory_names", "duplicate_values", "hashlib", "json", "load_catalog",
    "markdown_section", "module_cycle_errors", "parse_frontmatter",
    "parse_project_json", "parse_template_frontmatter", "re", "read_template",
    "string_list", "sys", "transitive_module_dependencies",
    "validate_agents_bootstrap", "validate_approval_policy", "validate_catalog",
    "validate_compliance_event", "validate_compliance_module",
    "validate_directory_set", "validate_enforcement_module",
    "validate_evidence_document", "validate_evidence_module",
    "validate_markdown_links", "validate_multi_repo_module",
    "validate_optional_compliance_module", "validate_optional_enforcement_module",
    "validate_optional_evidence_module", "validate_optional_multi_repo_module",
    "validate_project_config", "validate_provider_neutrality",
    "validate_public_documentation", "validate_review_template",
    "validate_skill", "validate_templates", "validate_v1_source_coverage",
)

_MODULES = (artifacts, distribution, documentation, semantics)
for _name in _EXPORTS:
    for _module in _MODULES:
        if hasattr(_module, _name):
            globals()[_name] = getattr(_module, _name)
            break
    else:
        raise AttributeError(
            f"validation responsibility does not export {_name}")

# CLI-compatible wrappers remain the only validator-facing bodies here.


def validate_repository(root: Path = ROOT) -> list[str]:
    return semantics.validate_repository(root)


def main(root: Path = ROOT) -> int:
    return semantics.main(root)


__all__ = list(_EXPORTS) + ["ROOT", "validate_repository", "main"]
del _module, _name, _MODULES

if __name__ == "__main__":
    raise SystemExit(main())

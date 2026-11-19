#!/usr/bin/env python3
"""Deterministic, dependency-free, read-only Agentic SDLC consistency checker."""

from __future__ import annotations
from lib.paths import (
    _config_key_safety, _git_ref, _load_json, _relative_path,
    _repository_path_syntax, _safe_checkout_path, _safe_config_string,
    _safe_existing, _safe_remote, _tree_hash,
)
from lib.report import Report

import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qsl, urlsplit

SCHEMA_VERSION = 1
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ID_PATTERNS = {
    "spec": re.compile(r"^SPEC-[0-9]+$"),
    "plan": re.compile(r"^PLAN-[0-9]+$"),
    "task": re.compile(r"^TASK-[0-9]+$"),
    "requirement": re.compile(r"^REQ-[0-9]+$"),
}
PROJECT_FIELDS = (
    "schema_version", "roots", "repositories", "enabled_modules", "tracker",
    "agent", "review", "approval_policy", "contribution",
)
ROOT_FIELDS = ("specs", "work", "adrs", "evidence", "domain_context")
ENV_PATH_RE = re.compile(r"^\$\{([A-Z_][A-Z0-9_]*)\}/(.+)$")
TRAILER_RE = re.compile(r"^[A-Za-z0-9-]+$")
EXECUTABLE_CONFIG_KEYS = {
    "command", "commands", "hook", "hooks", "plugin", "plugins", "regex",
    "regexp", "script", "scripts", "executable", "executables",
}
URI_SCHEME_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*):")
SCP_REMOTE_RE = re.compile(
    r"^(?:[A-Za-z0-9._-]+@)?"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*:"
    r"[A-Za-z0-9._~+-]+(?:/[A-Za-z0-9._~+-]+)*$"
)
EVIDENCE_FIELDS = (
    "schema_version", "change_id", "authoritative_sources", "lifecycle", "risk",
    "change_contract", "repository_scope", "requirement_coverage", "checks",
    "review", "known_limits", "remaining_risks", "follow_ups",
)
COMPLIANCE_EVENT_FIELDS = (
    "schema_version", "event_id", "sequence", "timestamp", "change_id", "actor",
    "action", "previous_lifecycle", "new_lifecycle",
    "authoritative_source_references", "evidence_references", "approvals",
    "repositories",
)
COMPLIANCE_NESTED_FIELDS = {
    "actor": ("actor_id", "role"),
    "approval": ("actor_id", "role", "reference"),
    "repository": ("repository_id", "revision"),
}
COMPLIANCE_IMPLEMENTATION_ROLES = {"implementer", "implementation"}
COMPLIANCE_TRANSITIONS = {
    ("draft", "approved"),
    ("approved", "planned"),
    ("approved", "implemented"),
    ("planned", "implemented"),
    ("implemented", "verified"),
}
COMPLIANCE_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
SENSITIVE_QUERY_KEYS = {
    "token", "accesstoken", "authtoken", "refreshtoken", "idtoken", "apikey",
    "secret", "clientsecret", "password", "passwd", "credential", "credentials",
}
SENSITIVE_QUERY_SUFFIXES = (
    "token", "apikey", "secret", "password", "passwd", "credential", "credentials",
)
COMMON_CREDENTIAL_RE = re.compile(
    r"(?:\bghp_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b|"
    r"\bsk-[A-Za-z0-9]{20,}\b|\bBearer\s+[A-Za-z0-9._~-]+)", re.IGNORECASE
)
SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?:api[-_ ]?key|credential|password|secret|token)\s*[:=]", re.IGNORECASE
)
PERSONAL_DATA_RE = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
# Later built-in module checks register here; records never load or execute code.
EXTENSION_VALIDATORS: dict[str, Any] = {}


def _parse_project(path: Path, root: Path, report: Report) -> Optional[dict[str, Any]]:
    try:
        if path.stat().st_size > 1_000_000:
            _config_issue(report, "CONFIG_SIZE", "",
                          "Project JSON exceeds the supported size.")
            return None
    except OSError:
        _config_issue(report, "CONFIG_UNREADABLE", "",
                      "Project JSON cannot be inspected safely.")
        return None
    config = _load_json(path, root, report, "CONFIG")
    if config is None:
        report.config_error = True
        return None
    if not isinstance(config, dict):
        _config_issue(report, "CONFIG_ROOT", "",
                      "Project configuration root must be an object.")
        return None
    _validate_project_v2(config, root, report)
    return None if report.config_error else config


def _config_issue(report: Report, code: str, field: str, message: str) -> None:
    report.add(code, ".agents/project.json", field, message, config=True)


def _validate_approval_policy_config(policy: Any, report: Report) -> None:
    if not isinstance(policy, dict) or set(policy) != {"rules"}:
        _config_issue(report, "CONFIG_APPROVAL_POLICY", "approval_policy",
                      "Approval policy must contain only rules.")
        return
    rules = policy.get("rules")
    if not isinstance(rules, list) or len(rules) > 100:
        _config_issue(report, "CONFIG_APPROVAL_POLICY", "approval_policy.rules",
                      "Approval policy rules must be a bounded array.")
        return
    seen_rules: set[tuple[str, str]] = set()
    for index, rule in enumerate(rules):
        field = f"approval_policy.rules[{index}]"
        if not isinstance(rule, dict) or set(rule) != {"risk", "action", "required_roles", "independent"}:
            _config_issue(report, "CONFIG_APPROVAL_POLICY", field,
                          "Policy rule must contain only risk, action, required_roles, and independent.")
            continue
        risk, action = rule.get("risk"), rule.get("action")
        if risk not in {"low", "medium", "high"}:
            _config_issue(report, "CONFIG_APPROVAL_POLICY", f"{field}.risk",
                          "Policy risk is not recognized.")
        if not isinstance(action, str) or not NAME_RE.fullmatch(action):
            _config_issue(report, "CONFIG_APPROVAL_POLICY", f"{field}.action",
                          "Policy action must be kebab-case.")
        if isinstance(risk, str) and isinstance(action, str):
            key = (risk, action)
            if key in seen_rules:
                _config_issue(report, "CONFIG_APPROVAL_POLICY", field,
                              "Policy risk/action pair must be unique.")
            seen_rules.add(key)
        independent = rule.get("independent")
        if type(independent) is not bool:
            _config_issue(report, "CONFIG_APPROVAL_POLICY", f"{field}.independent",
                          "Policy independence must be boolean.")
        elif risk == "high" and independent is False:
            _config_issue(report, "CONFIG_APPROVAL_POLICY", f"{field}.independent",
                          "Policy cannot weaken mandatory high-risk independence.")
        roles = rule.get("required_roles")
        if not isinstance(roles, list) or len(roles) > 100:
            _config_issue(report, "CONFIG_APPROVAL_POLICY", f"{field}.required_roles",
                          "Required roles must be a bounded array.")
            continue
        seen_roles: set[str] = set()
        for role_index, requirement in enumerate(roles):
            role_field = f"{field}.required_roles[{role_index}]"
            if not isinstance(requirement, dict) or set(requirement) != {"role", "minimum"}:
                _config_issue(report, "CONFIG_APPROVAL_POLICY", role_field,
                              "Role requirement must contain only role and minimum.")
                continue
            role, minimum = requirement.get("role"), requirement.get("minimum")
            if (not isinstance(role, str) or not role.strip() or len(role) > 500
                    or any(ord(character) < 32 or ord(character) == 127 for character in role)
                    or SENSITIVE_ASSIGNMENT_RE.search(role) or COMMON_CREDENTIAL_RE.search(role)
                    or PERSONAL_DATA_RE.search(role)):
                _config_issue(report, "CONFIG_APPROVAL_POLICY", f"{role_field}.role",
                              "Declared role must be a safe bounded single-line string.")
            elif role in seen_roles:
                _config_issue(report, "CONFIG_APPROVAL_POLICY", f"{role_field}.role",
                              "Declared roles must be unique within a rule.")
            else:
                seen_roles.add(role)
            if type(minimum) is not int or not 1 <= minimum <= 100:
                _config_issue(report, "CONFIG_APPROVAL_POLICY", f"{role_field}.minimum",
                              "Role minimum must be an integer from 1 to 100.")


def _validate_project_v2(config: dict[str, Any], root: Path, report: Report) -> None:
    if set(config) != set(PROJECT_FIELDS):
        _config_issue(report, "CONFIG_FIELDS", "",
                      "Project configuration must contain exactly the closed v2 fields.")
    if type(config.get("schema_version")) is not int or config.get("schema_version") != 2:
        _config_issue(report, "CONFIG_SCHEMA_VERSION", "schema_version",
                      "schema_version must be integer 2.")
    _config_key_safety(config, report)

    roots = config.get("roots")
    if not isinstance(roots, dict) or set(roots) != set(ROOT_FIELDS):
        _config_issue(report, "CONFIG_TYPE", "roots",
                      "Roots must contain exactly specs, work, adrs, evidence, and domain_context.")
    else:
        for key in ROOT_FIELDS:
            value = roots.get(key)
            if value is None and key not in {"specs", "work"}:
                continue
            field = f"roots.{key}"
            if not _relative_path(value) or any(token in value for token in ("$", "{", "}")):
                _config_issue(report, "CONFIG_PATH", field,
                              "Root must be a safe repository-relative path.")
                continue
            before_path_errors = len(report.errors)
            configured_root = _safe_existing(root, value, report, field)
            if len(report.errors) != before_path_errors:
                report.config_error = True
                continue
            if configured_root is None or not configured_root.exists():
                continue
            try:
                info = configured_root.lstat()
            except OSError:
                _config_issue(report, "CONFIG_ROOT_UNREADABLE", field,
                              "Configured root cannot be inspected safely.")
                continue
            file_or_directory = key in {"adrs", "domain_context"}
            valid_type = (
                stat.S_ISDIR(info.st_mode)
                or file_or_directory and stat.S_ISREG(info.st_mode)
            )
            if not valid_type:
                expected = "regular file or directory" if file_or_directory else "directory"
                _config_issue(report, "CONFIG_ROOT_TYPE", field,
                              f"Existing configured root must be a {expected}.")

    repositories = config.get("repositories")
    if not isinstance(repositories, list) or len(repositories) > 100:
        _config_issue(report, "CONFIG_TYPE", "repositories",
                      "Repositories must be a bounded array.")
    else:
        identifiers: set[str] = set()
        for index, repository in enumerate(repositories):
            field = f"repositories[{index}]"
            if not isinstance(repository, dict) or set(repository) != {"id", "path", "remote"}:
                _config_issue(report, "CONFIG_TYPE", field,
                              "Repository entry must contain only id, path, and remote.")
                continue
            identifier = repository.get("id")
            if (not isinstance(identifier, str) or not NAME_RE.fullmatch(identifier)
                    or identifier in identifiers):
                _config_issue(report, "CONFIG_TYPE", f"{field}.id",
                              "Repository ID must be unique kebab-case.")
            elif isinstance(identifier, str):
                identifiers.add(identifier)
            if not _repository_path_syntax(repository.get("path")):
                _config_issue(report, "CONFIG_PATH", f"{field}.path",
                              "Repository path must be '.', safe relative, or exact ${UPPER_ENV}/safe form.")
            remote = repository.get("remote")
            if remote is not None and not _safe_remote(remote):
                _config_issue(report, "CONFIG_REMOTE", f"{field}.remote",
                              "Remote must be a sanitized credential-free URI or scp-like identifier.")

    modules = config.get("enabled_modules")
    if (not isinstance(modules, list) or len(modules) > 100
            or any(not isinstance(item, str) or not NAME_RE.fullmatch(item) for item in modules)
            or len(modules) != len(set(modules))):
        _config_issue(report, "CONFIG_TYPE", "enabled_modules",
                      "Enabled modules must be unique catalog-name strings.")

    tracker = config.get("tracker")
    if not isinstance(tracker, dict) or set(tracker) != {"kind", "location", "labels"}:
        _config_issue(report, "CONFIG_TYPE", "tracker",
                      "Tracker must contain only kind, location, and labels.")
    else:
        kind, location, labels = tracker.get("kind"), tracker.get(
            "location"), tracker.get("labels")
        if not isinstance(kind, str) or not NAME_RE.fullmatch(kind):
            _config_issue(report, "CONFIG_TYPE", "tracker.kind",
                          "Tracker kind must be kebab-case.")
        if kind == "none" and location is not None:
            _config_issue(report, "CONFIG_CONSISTENCY", "tracker.location",
                          "Tracker location must be null when kind is none.")
        if kind != "none" and not _safe_config_string(location):
            _config_issue(report, "CONFIG_CONSISTENCY", "tracker.location",
                          "Configured tracker requires a sanitized location.")
        if not isinstance(labels, dict) or any(
            not _safe_config_string(key) or not _safe_config_string(item)
            for key, item in labels.items()
        ):
            _config_issue(report, "CONFIG_TYPE", "tracker.labels",
                          "Tracker labels must map safe non-empty strings.")

    agent = config.get("agent")
    if not isinstance(agent, dict) or set(agent) != {"mode"} or agent.get("mode") not in {"guided", "autonomous-within-rules"}:
        _config_issue(report, "CONFIG_ENUM", "agent.mode",
                      "Agent mode is not recognized.")
    review = config.get("review")
    if not isinstance(review, dict) or set(review) != {"mode"} or review.get("mode") not in {"risk-based", "always-independent"}:
        _config_issue(report, "CONFIG_ENUM", "review.mode",
                      "Review mode is not recognized.")

    _validate_approval_policy_config(config.get("approval_policy"), report)
    policy = config.get("approval_policy")
    if isinstance(policy, dict) and isinstance(policy.get("rules"), list):
        for index, rule in enumerate(policy["rules"]):
            roles = rule.get("required_roles") if isinstance(
                rule, dict) else None
            if isinstance(roles, list) and not roles:
                _config_issue(report, "CONFIG_APPROVAL_POLICY",
                              f"approval_policy.rules[{index}].required_roles",
                              "A policy rule requires at least one role.")
            if isinstance(roles, list):
                for role_index, requirement in enumerate(roles):
                    role = requirement.get("role") if isinstance(
                        requirement, dict) else None
                    if isinstance(role, str) and not NAME_RE.fullmatch(role):
                        _config_issue(report, "CONFIG_APPROVAL_POLICY",
                                      f"approval_policy.rules[{index}].required_roles[{role_index}].role",
                                      "Declared role must be kebab-case.")

    contribution = config.get("contribution")
    expected = {"commit_mode", "base_branch", "required_trailers",
                "pull_request_template", "merge_strategy"}
    if not isinstance(contribution, dict) or set(contribution) != expected:
        _config_issue(report, "CONFIG_TYPE", "contribution",
                      "Contribution must contain exactly the canonical fields.")
    else:
        if contribution.get("commit_mode") not in {"discover", "classic", "conventional"}:
            _config_issue(report, "CONFIG_ENUM", "contribution.commit_mode",
                          "Commit mode is not recognized.")
        base = contribution.get("base_branch")
        if base is not None and (not isinstance(base, str) or not _git_ref(base)):
            _config_issue(report, "CONFIG_REF", "contribution.base_branch",
                          "Base branch is not a safe Git ref.")
        trailers = contribution.get("required_trailers")
        if (not isinstance(trailers, list) or len(trailers) > 100
                or len(trailers) != len(set(item for item in trailers if isinstance(item, str)))
                or any(not isinstance(item, str) or not TRAILER_RE.fullmatch(item) for item in trailers)):
            _config_issue(report, "CONFIG_TRAILERS", "contribution.required_trailers",
                          "Required trailers must be unique letter, digit, and hyphen tokens.")
        template = contribution.get("pull_request_template")
        if template is not None and (not _relative_path(template) or any(token in template for token in ("$", "{", "}"))):
            _config_issue(report, "CONFIG_PATH", "contribution.pull_request_template",
                          "Pull request template must be a safe repository-relative path or null.")
        if contribution.get("merge_strategy") not in {"unknown", "merge", "squash", "rebase"}:
            _config_issue(report, "CONFIG_ENUM", "contribution.merge_strategy",
                          "Merge strategy is not recognized.")


def _catalog(root: Path, report: Report) -> tuple[dict[str, list[str]], set[str], bool]:
    path = _safe_existing(root, ".agents/kit-catalog.json", report, "catalog")
    if path is None or not path.exists():
        return {}, set(), False
    before_errors = len(report.errors)
    value = _load_json(path, root, report, "CATALOG")
    dependencies: dict[str, list[str]] = {}
    if not isinstance(value, dict):
        if value is not None:
            report.add("CATALOG_INVALID", ".agents/kit-catalog.json",
                       "", "Catalog root must be an object.")
        return dependencies, set(), False
    expected_fields = {"schema_version", "kit_version",
                       "skill_groups", "modules", "global_resources", "profiles"}
    if set(value) != expected_fields or type(value.get("schema_version")) is not int or value.get("schema_version") != 2 or value.get("kit_version") != "2.1.0":
        report.add("CATALOG_INVALID", ".agents/kit-catalog.json", "",
                   "Catalog root fields and schema metadata must match version 2.")
    global_resources = value.get("global_resources")
    if not isinstance(global_resources, list):
        report.add("CATALOG_INVALID", ".agents/kit-catalog.json", "global_resources",
                   "Catalog global_resources must be an array.")
    groups = value.get("skill_groups")
    if not isinstance(groups, dict) or set(groups) != {"core", "utilities", "optional"} or any(not isinstance(groups.get(name), list) for name in ("core", "utilities", "optional")):
        report.add("CATALOG_INVALID", ".agents/kit-catalog.json", "skill_groups",
                   "Catalog skill groups do not match schema version 1.")
    profiles = value.get("profiles")
    if not isinstance(profiles, dict) or not {"default", "full"}.issubset(profiles) or any(
        not isinstance(profile, dict) or set(profile) != {"skills", "modules"}
        or not isinstance(profile.get("skills"), list) or not isinstance(profile.get("modules"), list)
        for profile in profiles.values()
    ):
        report.add("CATALOG_INVALID", ".agents/kit-catalog.json", "profiles",
                   "Catalog profiles do not match schema version 1.")
    modules = value.get("modules")
    if not isinstance(modules, list):
        report.add("CATALOG_INVALID", ".agents/kit-catalog.json",
                   "modules", "Catalog modules must be an array.")
        return dependencies, set(), False
    for index, module in enumerate(modules):
        field = f"modules[{index}]"
        if not isinstance(module, dict) or set(module) != {"name", "description", "depends_on"}:
            report.add("CATALOG_INVALID", ".agents/kit-catalog.json",
                       field, "Catalog module entry has an invalid shape.")
            continue
        name, depends = module.get("name"), module.get("depends_on")
        if not isinstance(module.get("description"), str) or not module["description"].strip():
            report.add("CATALOG_INVALID", ".agents/kit-catalog.json",
                       f"{field}.description", "Catalog module description must be non-empty.")
        if not isinstance(name, str) or not NAME_RE.fullmatch(name) or name in dependencies:
            report.add("CATALOG_INVALID", ".agents/kit-catalog.json",
                       f"{field}.name", "Catalog module name is invalid or duplicated.")
            continue
        if not isinstance(depends, list) or any(not isinstance(item, str) or not NAME_RE.fullmatch(item) for item in depends) or len(depends) != len(set(depends)):
            report.add("CATALOG_INVALID", ".agents/kit-catalog.json",
                       f"{field}.depends_on", "Catalog dependencies must be unique module names.")
            continue
        dependencies[name] = depends
    known = set(dependencies)
    for name, depends in sorted(dependencies.items()):
        if set(depends) - known:
            report.add("CATALOG_INVALID", ".agents/kit-catalog.json",
                       name, "Catalog module has an unknown dependency.")
    for name in sorted(known):
        pending = [(name, ())]
        while pending:
            current, ancestors = pending.pop()
            if current in ancestors:
                report.add("CATALOG_INVALID", ".agents/kit-catalog.json",
                           "modules", "Catalog module dependencies contain a cycle.")
                pending.clear()
                break
            pending.extend((child, ancestors + (current,))
                           for child in dependencies.get(current, []))
    return dependencies, known, len(report.errors) == before_errors


def _dependency_closure(name: str, dependencies: dict[str, list[str]]) -> set[str]:
    result: set[str] = set()
    pending = list(dependencies.get(name, []))
    while pending:
        dependency = pending.pop()
        if dependency in result:
            continue
        result.add(dependency)
        pending.extend(dependencies.get(dependency, []))
    result.discard(name)
    return result


def _validate_modules(root: Path, config: Optional[dict[str, Any]], report: Report) -> set[str]:
    dependencies, catalog_names, catalog_valid = _catalog(root, report)
    modules_root = _safe_existing(root, ".agents/modules", report, "modules")
    installed: set[str] = set()
    if modules_root is not None and modules_root.is_dir():
        try:
            for entry in modules_root.iterdir():
                relative = f".agents/modules/{entry.name}"
                safe_entry = _safe_existing(root, relative, report, "modules")
                if safe_entry is None or not safe_entry.is_dir():
                    continue
                module_file = _safe_existing(
                    root, f"{relative}/MODULE.md", report, "modules"
                )
                if module_file is not None and module_file.is_file():
                    installed.add(entry.name)
        except OSError:
            report.add("MODULES_UNREADABLE", ".agents/modules", "",
                       "Installed modules cannot be inspected.")
    report.counts["modules"] = len(installed)
    if config is not None:
        enabled = set(config["enabled_modules"])
        if enabled and not catalog_valid:
            report.add("CATALOG_REQUIRED", ".agents/kit-catalog.json", "",
                       "Enabled modules require a present valid installed catalog.")
        for name in sorted(enabled):
            if name not in installed:
                report.add("MODULE_ENABLED_MISSING",
                           f".agents/modules/{name}", "enabled_modules", "Enabled module is not safely installed.")
            if name not in catalog_names:
                report.add("MODULE_NOT_CATALOGED", ".agents/kit-catalog.json", "modules",
                           "Enabled module is not declared by the installed catalog.")
            for dependency in sorted(_dependency_closure(name, dependencies)):
                if dependency not in enabled:
                    report.add("MODULE_DEPENDENCY_DISABLED", ".agents/project.json",
                               "enabled_modules", f"Enabled module dependency {dependency} is not enabled.")
                if dependency not in installed:
                    report.add("MODULE_DEPENDENCY_MISSING",
                               f".agents/modules/{dependency}", "", f"Enabled module dependency {dependency} is not installed.")
    _validate_manifest(root, catalog_names, report)
    return installed


def _validate_manifest(root: Path, catalog_names: set[str], report: Report) -> None:
    path = _safe_existing(
        root, ".agents/agentic-sdlc-kit.json", report, "manifest")
    if path is None or not path.exists():
        return
    manifest = _load_json(path, root, report, "MANIFEST")
    if not isinstance(manifest, dict):
        if manifest is not None:
            report.add("MANIFEST_INVALID", ".agents/agentic-sdlc-kit.json",
                       "", "Ownership manifest root must be an object.")
        return
    required = {"schema_version", "kit_version",
                "request", "components", "global_resources"}
    if set(manifest) != required:
        report.add("MANIFEST_INVALID", ".agents/agentic-sdlc-kit.json",
                   "", "Ownership manifest fields do not match schema version 2.")
        return
    components = manifest.get("components")
    resources = manifest.get("global_resources")
    if type(manifest.get("schema_version")) is not int or manifest.get("schema_version") != 2 or not isinstance(components, list) or not isinstance(resources, list):
        report.add("MANIFEST_INVALID", ".agents/agentic-sdlc-kit.json",
                   "", "Ownership manifest has invalid field types.")
        return
    records: list[tuple[str, str, str, str]] = []
    for index, item in enumerate(components):
        field = f"components[{index}]"
        if not isinstance(item, dict) or set(item) != {"kind", "name", "path", "ownership", "sha256"}:
            report.add("MANIFEST_INVALID", ".agents/agentic-sdlc-kit.json",
                       field, "Installed component record has an invalid shape.")
            continue
        kind, name, relative, ownership, expected = item["kind"], item[
            "name"], item["path"], item["ownership"], item["sha256"]
        if kind not in {"skill", "module"} or ownership not in {"managed", "project-owned"} or not isinstance(name, str) or not NAME_RE.fullmatch(name) or not isinstance(relative, str) or not _relative_path(relative) or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            report.add("MANIFEST_INVALID", ".agents/agentic-sdlc-kit.json",
                       field, "Installed component record has invalid values.")
            continue
        records.append((kind, name, relative, expected))
    for kind, name, relative, expected in sorted(records):
        canonical = f".agents/{'skills' if kind == 'skill' else 'modules'}/{name}"
        if relative != canonical:
            report.add("MANIFEST_PATH_MISMATCH", ".agents/agentic-sdlc-kit.json",
                       name, "Component path does not match its kind and name.")
            continue
        component = _safe_existing(root, relative, report, name)
        actual = _tree_hash(
            component) if component is not None and component.exists() else None
        if actual is None:
            report.add("MANIFEST_COMPONENT_MISSING", relative, name,
                       "Manifest component is missing or unsafe.")
        elif actual != expected:
            report.add("MANIFEST_HASH_MISMATCH", relative, name,
                       "Manifest hash does not match filesystem content.")
        if kind == "module" and catalog_names and name not in catalog_names:
            report.add("MANIFEST_CATALOG_MISMATCH", ".agents/agentic-sdlc-kit.json",
                       name, "Manifest module is absent from the catalog.")
    resource_paths = [item.get("path")
                      for item in resources if isinstance(item, dict)]
    if len(resource_paths) != len(set(resource_paths)) or ".agents/agentic-sdlc-kit.json" in resource_paths:
        report.add("MANIFEST_INVALID", ".agents/agentic-sdlc-kit.json", "global_resources",
                   "Global resource paths must be unique and must not include the manifest.")
    for index, item in enumerate(resources):
        field = f"global_resources[{index}]"
        if not isinstance(item, dict) or set(item) != {"path", "ownership", "sha256"} or item.get("ownership") not in {"managed", "project-owned"} or not isinstance(item.get("path"), str) or not isinstance(item.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", "")):
            report.add("MANIFEST_INVALID", ".agents/agentic-sdlc-kit.json",
                       field, "Global resource record is invalid.")
            continue
        managed_path = _safe_existing(root, item["path"], report, field)
        actual = _tree_hash(
            managed_path) if managed_path is not None and managed_path.exists() else None
        if actual is None:
            report.add("MANIFEST_COMPONENT_MISSING",
                       item["path"], field, "Global resource is missing or unsafe.")
        elif actual != item["sha256"]:
            report.add("MANIFEST_HASH_MISMATCH",
                       item["path"], field, "Manifest hash does not match filesystem content.")


def _validate_multi_repo(
    root: Path,
    config: dict[str, Any],
    evidence: list[dict[str, Any]],
    tasks: dict[str, dict[str, Any]],
    report: Report,
) -> None:
    from lib.artifacts import _split_refs
    repositories = config.get("repositories", [])
    known_ids = {
        item.get("id") for item in repositories
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    if not repositories:
        report.add(
            "MULTI_REPO_REPOSITORIES_REQUIRED",
            ".agents/project.json",
            "repositories",
            "Enabled multi-repo module requires at least one configured repository.",
        )
    for index, repository in enumerate(repositories):
        if not isinstance(repository, dict) or not isinstance(repository.get("path"), str):
            continue
        field = f"repositories[{index}].path"
        checkout = _safe_checkout_path(root, repository["path"], report, field)
        valid = checkout is not None
        if valid:
            try:
                valid = checkout.is_dir() and not checkout.is_symlink()
                marker = checkout / ".git"
                marker_info = marker.lstat() if valid else None
                valid = bool(
                    marker_info is not None
                    and not stat.S_ISLNK(marker_info.st_mode)
                    and (stat.S_ISDIR(marker_info.st_mode) or stat.S_ISREG(marker_info.st_mode))
                )
            except (FileNotFoundError, OSError):
                valid = False
        if not valid:
            report.add(
                "MULTI_REPO_CHECKOUT_INVALID",
                ".agents/project.json",
                field,
                "Configured repository must resolve to an existing non-symlink Git checkout.",
            )

    for task_id, task in sorted(tasks.items()):
        task_repositories = task.get("repositories", [])
        if len(task_repositories) != 1:
            report.add(
                "MULTI_REPO_TASK_REPOSITORY_REQUIRED",
                task["path"],
                "Repository",
                "Each task requires exactly one primary Repository ID.",
            )
            continue
        repository_id = task_repositories[0]
        if repository_id not in known_ids:
            report.add(
                "MULTI_REPO_TASK_REPOSITORY_UNKNOWN",
                task["path"],
                "Repository",
                "Task primary Repository ID is not configured.",
            )
        if not task.get("has_cross_dependencies") or not task.get("has_integration_evidence"):
            report.add(
                "MULTI_REPO_TASK_FIELD_REQUIRED",
                task["path"],
                "Cross-repo depends on",
                "Every task requires cross-repository dependency and integration-evidence fields.",
            )
        dependencies = set(task.get("dependencies", []))
        expected_cross = {
            dependency for dependency in dependencies
            if dependency in tasks
            and len(tasks[dependency].get("repositories", [])) == 1
            and tasks[dependency]["repositories"][0] != repository_id
        }
        declared_cross_list = task.get("cross_dependencies", [])
        declared_cross = set(declared_cross_list)
        if len(declared_cross_list) != len(declared_cross):
            report.add(
                "MULTI_REPO_TASK_CROSS_REPO_DUPLICATE",
                task["path"],
                "Cross-repo depends on",
                "Cross-repository dependency references must be unique.",
            )
        elif declared_cross != expected_cross:
            report.add(
                "MULTI_REPO_TASK_CROSS_REPO",
                task["path"],
                "Cross-repo depends on",
                "Cross-repository dependency references must exactly match Depends on.",
            )
        integration = str(task.get("integration_evidence", "")).strip().lower()
        if declared_cross and integration in {"", "none", "n/a", "pending", "not-applicable"}:
            report.add(
                "MULTI_REPO_TASK_CROSS_REPO",
                task["path"],
                "Integration evidence",
                "Cross-repository dependencies require planned or observed integration evidence.",
            )

        dirty = task.get("dirty_status")
        ownership = task.get("ownership")
        dirty_values = {
            "clean", "dirty-nonconflicting", "blocked-conflict", "unknown",
        }
        ownership_values = {
            "exclusive-owner", "isolated", "blocked-conflict", "unknown",
        }
        if dirty not in dirty_values:
            report.add(
                "MULTI_REPO_TASK_CONTROL_INVALID",
                task["path"],
                "Dirty status",
                "Dirty status must use its exact recognized enum.",
            )
        if ownership not in ownership_values:
            report.add(
                "MULTI_REPO_TASK_CONTROL_INVALID",
                task["path"],
                "Ownership/isolation",
                "Ownership/isolation must use its exact recognized enum.",
            )
        blocking_values = {"blocked-conflict", "unknown"}
        if task.get("state") in {"ready", "in-progress", "done"} and (
            dirty in blocking_values or ownership in blocking_values
        ):
            report.add(
                "MULTI_REPO_TASK_CONTROL_BLOCKED",
                task["path"],
                "Dirty status",
                "Runnable, active, or completed tasks cannot have blocked or unknown controls.",
            )
        required_blockers = set()
        if dirty in blocking_values:
            required_blockers.add(f"dirty-status:{dirty}")
        if ownership in blocking_values:
            required_blockers.add(f"ownership-isolation:{ownership}")
        blocker_references = set(_split_refs(task.get("blocker", "")))
        if task.get("state") == "blocked" and required_blockers - blocker_references:
            report.add(
                "MULTI_REPO_TASK_BLOCKER_MISMATCH",
                task["path"],
                "Blocker",
                "Blocked task controls require exact matching blocker references.",
            )

    evidence_root = config.get("roots", {}).get("evidence") or "evidence"
    for document in evidence:
        relative = f"{evidence_root}/{document.get('change_id', 'unknown')}/evidence.json"
        scopes = document.get("repository_scope", [])
        scope_ids = [
            item.get("repository_id") for item in scopes
            if isinstance(item, dict) and isinstance(item.get("repository_id"), str)
        ] if isinstance(scopes, list) else []
        if len(scope_ids) != len(set(scope_ids)):
            report.add(
                "MULTI_REPO_EVIDENCE_SCOPE_DUPLICATE",
                relative,
                "repository_scope",
                "Repository scope IDs must be unique.",
            )
        linked_ids: set[str] = set()
        linked_records = []
        for field in ("requirement_coverage", "checks"):
            value = document.get(field, [])
            if isinstance(value, list):
                linked_records.extend(
                    item for item in value if isinstance(item, dict))
        for item in linked_records:
            item_ids = item.get("repository_ids", [])
            if isinstance(item_ids, list):
                linked_ids.update(
                    repo_id for repo_id in item_ids if isinstance(repo_id, str))
        all_ids = set(scope_ids) | linked_ids
        if all_ids - known_ids:
            report.add(
                "MULTI_REPO_EVIDENCE_REPOSITORY_UNKNOWN",
                relative,
                "repository_ids",
                "Evidence references a repository ID not present in project configuration.",
            )
        coverage_repositories = {
            item.get("requirement_id"): set(item.get("repository_ids", []))
            for item in document.get("requirement_coverage", [])
            if isinstance(item, dict)
            and isinstance(item.get("requirement_id"), str)
            and isinstance(item.get("repository_ids"), list)
        } if isinstance(document.get("requirement_coverage"), list) else {}
        for check in document.get("checks", []) if isinstance(document.get("checks"), list) else []:
            if not isinstance(check, dict) or not isinstance(check.get("repository_ids"), list):
                continue
            covered = set()
            for requirement_id in check.get("requirement_ids", []):
                covered.update(coverage_repositories.get(
                    requirement_id, set()))
            if set(check["repository_ids"]) - covered:
                report.add(
                    "MULTI_REPO_EVIDENCE_COVERAGE_MISMATCH",
                    relative,
                    "checks.repository_ids",
                    "Check repository IDs must be covered by its linked requirements.",
                )
                break
        if set(scope_ids) != linked_ids:
            report.add(
                "MULTI_REPO_EVIDENCE_SCOPE_MISMATCH",
                relative,
                "repository_scope",
                "Repository scope must exactly match repositories affected by coverage and checks.",
            )


__all__ = ['_catalog', '_config_issue', '_dependency_closure', '_parse_project', '_validate_approval_policy_config',
           '_validate_manifest', '_validate_modules', '_validate_multi_repo', '_validate_project_v2']

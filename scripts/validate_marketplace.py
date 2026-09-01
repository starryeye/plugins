#!/usr/bin/env python3
"""Validate this repository's offline Codex marketplace contract."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


MARKETPLACE_PATH = Path(".agents/plugins/marketplace.json")
EXPECTED_MARKETPLACE_NAME = "starryeye"
EXPECTED_DISPLAY_NAME = "Starryeye Plugins"
EXPECTED_PLUGIN_VERSION = "0.5.1"
EXPECTED_SOURCE_URL = "https://github.com/starryeye/web-translator.git"
COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$", re.ASCII)
EXPECTED_POLICY = {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}
EXPECTED_CATEGORY = "Productivity"
EXPECTED_LISTING_METADATA = {
    "description": "Translate one public static HTML page or one local or public text-selectable PDF into reviewed Korean output.",
    "author": {"name": "starryeye"},
    "repository": "https://github.com/starryeye/web-translator",
    "interface": {
        "displayName": "Web Translator",
        "shortDescription": "Translate public HTML or local/public PDFs into reviewed Korean output.",
        "longDescription": "Provides separate workflows for a public static HTML page and a local or public text-selectable PDF while sharing contextual translation and master-review contracts.",
        "developerName": "starryeye",
        "category": "Productivity",
        "capabilities": ["Write"],
        "defaultPrompt": [
            "Translate this public HTML page into an offline Korean bundle, or translate this local or public text-selectable PDF into a reviewed Korean PDF."
        ],
    },
}
EXPECTED_ENTRY_FIELDS = {
    "name",
    "source",
    "version",
    "description",
    "author",
    "repository",
    "interface",
    "policy",
    "category",
}
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)"
    r"(?:-((?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$",
    re.ASCII,
)


def _read_json_object(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        errors.append(f"{path} is not readable JSON: {error}")
        return None

    if not isinstance(value, dict):
        errors.append(f"{path} must contain a JSON object, not {type(value).__name__}")
        return None
    return value


def _validate_catalog(
    root: Path, catalog: dict[str, Any], errors: list[str]
) -> dict[str, Any] | None:
    if catalog.get("name") != EXPECTED_MARKETPLACE_NAME:
        errors.append(
            "marketplace name must be "
            f"{EXPECTED_MARKETPLACE_NAME!r}; found {catalog.get('name')!r}"
        )

    interface = catalog.get("interface")
    display_name = interface.get("displayName") if isinstance(interface, dict) else None
    if display_name != EXPECTED_DISPLAY_NAME:
        errors.append(
            "marketplace display name must be "
            f"{EXPECTED_DISPLAY_NAME!r}; found {display_name!r}"
        )

    plugins = catalog.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 1:
        count = len(plugins) if isinstance(plugins, list) else "a non-list value"
        errors.append(
            "marketplace must contain exactly one plugin entry; "
            f"found {count}"
        )
        return None

    entry = plugins[0]
    if not isinstance(entry, dict):
        errors.append("the marketplace plugin entry must be a JSON object")
        return None

    if set(entry) != EXPECTED_ENTRY_FIELDS:
        errors.append("plugin entry fields do not match the remote release contract")
    if entry.get("name") != "web-translator":
        errors.append("plugin entry name must be 'web-translator'")
    version = entry.get("version")
    if not isinstance(version, str) or SEMVER_PATTERN.fullmatch(version) is None:
        errors.append("plugin release version must be a strict semantic version")
    elif version != EXPECTED_PLUGIN_VERSION:
        errors.append(f"plugin release version must be {EXPECTED_PLUGIN_VERSION!r}")
    source = entry.get("source")
    if not isinstance(source, dict) or source.get("source") != "url":
        errors.append("plugin source type must be 'url'")
    elif set(source) != {"source", "url", "ref", "sha"}:
        errors.append("plugin source fields must be source, url, ref, and sha")
    else:
        if source.get("url") != EXPECTED_SOURCE_URL:
            errors.append("plugin source URL is not the approved upstream")
        if source.get("ref") != f"v{EXPECTED_PLUGIN_VERSION}":
            errors.append("plugin release ref must match the catalog version")
        if not isinstance(source.get("sha"), str) or COMMIT_SHA.fullmatch(source["sha"]) is None:
            errors.append("plugin commit SHA must be 40 lowercase hexadecimal characters")
    for field, expected in EXPECTED_LISTING_METADATA.items():
        if entry.get(field) != expected:
            errors.append(f"plugin listing metadata mismatch: {field}")
    if entry.get("policy") != EXPECTED_POLICY:
        errors.append("plugin policy does not match the marketplace contract")
    if entry.get("category") != EXPECTED_CATEGORY:
        errors.append("plugin category does not match the marketplace contract")
    if os.path.lexists(root / "plugins" / "web-translator"):
        errors.append("vendored plugin directory must not exist")
    return entry


def validate_repository(root: Path) -> list[str]:
    errors: list[str] = []
    catalog = _read_json_object(root / MARKETPLACE_PATH, errors)
    if catalog is None:
        return errors

    _validate_catalog(root, catalog, errors)
    return errors


def _run_checked(
    arguments: list[str | os.PathLike[str]],
    label: str,
    errors: list[str],
) -> subprocess.CompletedProcess[str] | None:
    try:
        result = subprocess.run(
            arguments,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as error:
        errors.append(f"{label} failed: {error}")
        return None
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        errors.append(f"{label} failed: {detail}")
        return None
    return result


def _validate_remote_release(
    entry: dict[str, Any],
    errors: list[str],
    clone_url: str | None = None,
) -> None:
    source = entry["source"]
    url = clone_url or source["url"]
    ref_name = source["ref"]
    expected_sha = source["sha"]
    tag_ref = f"refs/tags/{ref_name}"

    remote = _run_checked(
        ["git", "ls-remote", "--tags", url, tag_ref],
        "remote tag lookup",
        errors,
    )
    if remote is None:
        return
    expected_line = f"{expected_sha}\t{tag_ref}"
    if expected_line not in remote.stdout.splitlines():
        errors.append("remote tag is missing or its commit does not match catalog commit SHA")
        return

    try:
        with tempfile.TemporaryDirectory(prefix="starryeye-plugin-") as directory:
            checkout = Path(directory) / "web-translator"
            cloned = _run_checked(
                [
                    "git",
                    "clone",
                    "--quiet",
                    "--depth",
                    "1",
                    "--branch",
                    ref_name,
                    url,
                    checkout,
                ],
                "remote release clone",
                errors,
            )
            if cloned is None:
                return
            head = _run_checked(
                ["git", "-C", checkout, "rev-parse", "HEAD"],
                "remote release commit check",
                errors,
            )
            if head is None:
                return
            if head.stdout.strip() != expected_sha:
                errors.append("cloned release commit does not match catalog commit SHA")
                return

            manifest = _read_json_object(
                checkout / ".codex-plugin" / "plugin.json", errors
            )
            if manifest is None:
                return
            if manifest.get("name") != "web-translator":
                errors.append("upstream manifest name is not 'web-translator'")
            if manifest.get("version") != entry.get("version"):
                errors.append("upstream manifest version does not match catalog")
            for field in EXPECTED_LISTING_METADATA:
                if manifest.get(field) != entry.get(field):
                    errors.append(f"upstream manifest metadata mismatch: {field}")

            _run_checked(
                [sys.executable, checkout / "scripts" / "version.py", "check"],
                "upstream version check",
                errors,
            )
    except OSError as error:
        errors.append(f"temporary release checkout failed: {error}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the starryeye marketplace remote release contract."
    )
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to the parent of this script's directory)",
    )
    parser.add_argument(
        "--verify-remote",
        action="store_true",
        help="verify the tagged upstream release after offline validation passes",
    )
    return parser.parse_args()


def main() -> int:
    arguments = _parse_args()
    root = arguments.root.resolve()
    errors = validate_repository(root)
    if not errors and arguments.verify_remote:
        catalog = _read_json_object(root / MARKETPLACE_PATH, errors)
        if catalog is not None:
            entry = _validate_catalog(root, catalog, errors)
            if entry is not None and not errors:
                _validate_remote_release(entry, errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(
            f"Marketplace validation failed with {len(errors)} error(s).",
            file=sys.stderr,
        )
        return 1

    print(f"Marketplace validation passed: {root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

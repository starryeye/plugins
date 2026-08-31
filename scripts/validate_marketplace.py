#!/usr/bin/env python3
"""Validate this repository's offline Codex marketplace contract."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


MARKETPLACE_PATH = Path(".agents/plugins/marketplace.json")
EXPECTED_MARKETPLACE_NAME = "starryeye"
EXPECTED_DISPLAY_NAME = "Starryeye Plugins"
EXPECTED_PLUGIN_VERSION = "0.4.0"
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
    return parser.parse_args()


def main() -> int:
    root = _parse_args().root.resolve()
    errors = validate_repository(root)
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

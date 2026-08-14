#!/usr/bin/env python3
"""Validate this repository's Codex marketplace contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any


MARKETPLACE_PATH = Path(".agents/plugins/marketplace.json")
EXPECTED_MARKETPLACE_NAME = "starryeye"
EXPECTED_DISPLAY_NAME = "Starryeye Plugins"
EXPECTED_PLUGIN_VERSION = "0.2.0"
EXPECTED_PLUGIN = {
    "name": "web-translator",
    "source": {"source": "local", "path": "./plugins/web-translator"},
    "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
    "category": "Productivity",
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
) -> tuple[dict[str, Any] | None, Path | None]:
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
        return None, None

    entry = plugins[0]
    if not isinstance(entry, dict):
        errors.append("the marketplace plugin entry must be a JSON object")
        return None, None

    if entry.get("name") != EXPECTED_PLUGIN["name"]:
        errors.append(
            f"plugin entry name must be {EXPECTED_PLUGIN['name']!r}; "
            f"found {entry.get('name')!r}"
        )
    if entry.get("source") != EXPECTED_PLUGIN["source"]:
        errors.append(
            "plugin local source must be exactly "
            f"{EXPECTED_PLUGIN['source']!r}; found {entry.get('source')!r}"
        )
    if entry.get("policy") != EXPECTED_PLUGIN["policy"]:
        errors.append(
            f"plugin policy must be exactly {EXPECTED_PLUGIN['policy']!r}; "
            f"found {entry.get('policy')!r}"
        )
    if entry.get("category") != EXPECTED_PLUGIN["category"]:
        errors.append(
            f"plugin category must be {EXPECTED_PLUGIN['category']!r}; "
            f"found {entry.get('category')!r}"
        )
    if set(entry) != set(EXPECTED_PLUGIN):
        errors.append(
            "plugin entry fields must be exactly "
            f"{sorted(EXPECTED_PLUGIN)}; found {sorted(entry)}"
        )

    source = entry.get("source")
    source_path = source.get("path") if isinstance(source, dict) else None
    if not isinstance(source_path, str):
        return entry, None

    plugin_root = (root / source_path).resolve()
    if not plugin_root.is_dir():
        errors.append(
            "referenced plugin directory does not exist: "
            f"{plugin_root} (from source path {source_path!r})"
        )
        return entry, None

    return entry, plugin_root


def _validate_manifest(
    plugin_root: Path, entry: dict[str, Any], errors: list[str]
) -> str | None:
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    manifest = _read_json_object(manifest_path, errors)
    if manifest is None:
        return None

    entry_name = entry.get("name")
    manifest_name = manifest.get("name")
    if not (
        isinstance(entry_name, str)
        and plugin_root.name == entry_name == manifest_name
    ):
        errors.append(
            "folder, marketplace entry, and manifest names must match; "
            f"found {plugin_root.name!r}, {entry_name!r}, and {manifest_name!r}"
        )

    version = manifest.get("version")
    if not isinstance(version, str) or SEMVER_PATTERN.fullmatch(version) is None:
        errors.append(
            "plugin manifest version must be a strict semantic version "
            f"(for example, '1.2.3' or '1.2.3-rc.1'); found {version!r}"
        )
        return None
    if version != EXPECTED_PLUGIN_VERSION:
        errors.append(
            "plugin manifest version must match the expected marketplace release "
            f"{EXPECTED_PLUGIN_VERSION!r}; found {version!r}"
        )

    skills = manifest.get("skills")
    if skills is not None:
        if not isinstance(skills, str) or not skills.strip():
            errors.append(
                "plugin manifest skills path must be a non-empty string; "
                f"found {skills!r}"
            )
        else:
            skills_path = plugin_root / skills
            if not skills_path.exists():
                errors.append(
                    "declared skills path does not exist: "
                    f"{skills_path} (from manifest value {skills!r})"
                )
    return version


def _validate_version_artifacts(
    root: Path, plugin_root: Path, manifest_version: str | None, errors: list[str]
) -> None:
    if manifest_version is None:
        return
    pyproject_path = plugin_root / "pyproject.toml"
    try:
        pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        project_version = pyproject["project"]["version"]
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, KeyError, TypeError) as error:
        errors.append(f"{pyproject_path} does not declare project.version: {error}")
        project_version = None

    package_path = plugin_root / "src" / "web_translator" / "__init__.py"
    try:
        package_text = package_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        errors.append(f"cannot read package version from {package_path}: {error}")
        package_version = None
    else:
        matches = re.findall(
            r'^__version__\s*=\s*"([^"]+)"\s*$', package_text, re.MULTILINE
        )
        if len(matches) != 1:
            errors.append(
                f"{package_path} must declare exactly one __version__; found {len(matches)}"
            )
            package_version = None
        else:
            package_version = matches[0]

    versions = {
        "manifest": manifest_version,
        "pyproject": project_version,
        "package": package_version,
    }
    if any(value != manifest_version for value in versions.values()):
        detail = ", ".join(f"{name}={value!r}" for name, value in versions.items())
        errors.append(f"plugin version mismatch: {detail}")

    readme_path = root / "README.md"
    expected_line = "- Version: `" + manifest_version + "`"
    try:
        readme = readme_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        errors.append(f"cannot read marketplace README: {error}")
    else:
        if expected_line not in readme:
            errors.append(f"README must display the marketplace plugin version as {expected_line!r}")


def validate_repository(root: Path) -> list[str]:
    errors: list[str] = []
    catalog = _read_json_object(root / MARKETPLACE_PATH, errors)
    if catalog is None:
        return errors

    entry, plugin_root = _validate_catalog(root, catalog, errors)
    if plugin_root is None or entry is None:
        return errors

    nested_git_paths = sorted(plugin_root.rglob(".git"))
    for nested_git_path in nested_git_paths:
        errors.append(f"nested Git metadata is not allowed: {nested_git_path}")

    manifest_version = _validate_manifest(plugin_root, entry, errors)
    _validate_version_artifacts(root, plugin_root, manifest_version, errors)
    return errors


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the starryeye marketplace and vendored plugin layout."
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

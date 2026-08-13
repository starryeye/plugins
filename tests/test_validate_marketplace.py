from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_VALIDATOR = (
    Path(__file__).resolve().parents[1] / "scripts" / "validate_marketplace.py"
)
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class MarketplaceValidatorTests(unittest.TestCase):
    def test_readme_documents_complete_remote_sparse_checkout(self) -> None:
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        install_command = (
            "codex plugin marketplace add https://github.com/starryeye/plugins.git "
            "--ref main --sparse .agents/plugins "
            "--sparse plugins/web-translator"
        )

        self.assertIn(install_command, readme)
        self.assertIn("codex plugin add web-translator@starryeye", readme)

    def test_accepts_the_supported_marketplace_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self._write_valid_repository(root)

            result = self._run_validator(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Marketplace validation passed", result.stdout)

    def test_rejects_wrong_marketplace_identity(self) -> None:
        cases = {
            "name": ("name", "someone-else", "marketplace name"),
            "display name": (
                "interface.displayName",
                "Someone Else's Plugins",
                "display name",
            ),
        }

        for label, (field, value, expected_message) in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as temporary_directory:
                root = Path(temporary_directory)
                self._write_valid_repository(root)
                catalog = self._read_json(self._marketplace_path(root))
                if field == "name":
                    catalog["name"] = value
                else:
                    catalog["interface"]["displayName"] = value
                self._write_json(self._marketplace_path(root), catalog)

                result = self._run_validator(root)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_message, result.stderr)

    def test_rejects_any_catalog_other_than_the_required_plugin_entry(self) -> None:
        def add_plugin(catalog: dict[str, object]) -> None:
            catalog["plugins"].append({"name": "unexpected"})

        def change_policy(catalog: dict[str, object]) -> None:
            catalog["plugins"][0]["policy"]["authentication"] = "NONE"

        def change_category(catalog: dict[str, object]) -> None:
            catalog["plugins"][0]["category"] = "Other"

        def change_local_path(catalog: dict[str, object]) -> None:
            catalog["plugins"][0]["source"]["path"] = "./plugins/renamed"

        cases = {
            "extra plugin": (add_plugin, "exactly one plugin"),
            "wrong policy": (change_policy, "policy"),
            "wrong category": (change_category, "category"),
            "wrong local path": (change_local_path, "local source"),
        }

        for label, (mutate, expected_message) in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as temporary_directory:
                root = Path(temporary_directory)
                self._write_valid_repository(root)
                catalog = self._read_json(self._marketplace_path(root))
                mutate(catalog)
                self._write_json(self._marketplace_path(root), catalog)

                result = self._run_validator(root)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_message, result.stderr)

    def test_rejects_a_missing_referenced_plugin_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self._write_valid_repository(root)
            self._plugin_root(root).rename(root / "plugins" / "not-web-translator")

            result = self._run_validator(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("referenced plugin directory does not exist", result.stderr)

    def test_rejects_names_that_do_not_align(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self._write_valid_repository(root)
            manifest_path = self._manifest_path(root)
            manifest = self._read_json(manifest_path)
            manifest["name"] = "renamed-plugin"
            self._write_json(manifest_path, manifest)

            result = self._run_validator(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("folder, marketplace entry, and manifest names must match", result.stderr)

    def test_rejects_manifest_versions_that_are_not_strict_semver(self) -> None:
        invalid_versions = ("1", "1.2", "01.2.3", "1.2.3-", "v1.2.3")

        for version in invalid_versions:
            with self.subTest(version), tempfile.TemporaryDirectory() as temporary_directory:
                root = Path(temporary_directory)
                self._write_valid_repository(root)
                manifest_path = self._manifest_path(root)
                manifest = self._read_json(manifest_path)
                manifest["version"] = version
                self._write_json(manifest_path, manifest)

                result = self._run_validator(root)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("strict semantic version", result.stderr)

    def test_accepts_a_strict_semver_prerelease_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self._write_valid_repository(root)
            manifest_path = self._manifest_path(root)
            manifest = self._read_json(manifest_path)
            manifest["version"] = "1.2.3-rc.1+build.5"
            self._write_json(manifest_path, manifest)

            result = self._run_validator(root)

            self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_a_missing_declared_skills_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self._write_valid_repository(root)
            manifest_path = self._manifest_path(root)
            manifest = self._read_json(manifest_path)
            manifest["skills"] = "./missing-skills/"
            self._write_json(manifest_path, manifest)

            result = self._run_validator(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("declared skills path does not exist", result.stderr)

    def test_rejects_nested_git_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self._write_valid_repository(root)
            (self._plugin_root(root) / "src" / ".git").mkdir(parents=True)

            result = self._run_validator(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("nested Git metadata", result.stderr)

    def test_reports_unreadable_json_without_a_traceback(self) -> None:
        for target in ("marketplace", "manifest"):
            with self.subTest(target), tempfile.TemporaryDirectory() as temporary_directory:
                root = Path(temporary_directory)
                self._write_valid_repository(root)
                path = (
                    self._marketplace_path(root)
                    if target == "marketplace"
                    else self._manifest_path(root)
                )
                path.write_text("{not JSON", encoding="utf-8")

                result = self._run_validator(root)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("is not readable JSON", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def _run_validator(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(REPOSITORY_VALIDATOR), str(root)],
            check=False,
            capture_output=True,
            text=True,
        )

    def _marketplace_path(self, root: Path) -> Path:
        return root / ".agents" / "plugins" / "marketplace.json"

    def _plugin_root(self, root: Path) -> Path:
        return root / "plugins" / "web-translator"

    def _manifest_path(self, root: Path) -> Path:
        return self._plugin_root(root) / ".codex-plugin" / "plugin.json"

    def _read_json(self, path: Path) -> dict[str, object]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, value: dict[str, object]) -> None:
        path.write_text(json.dumps(value), encoding="utf-8")

    def _write_valid_repository(self, root: Path) -> None:
        marketplace_path = self._marketplace_path(root)
        marketplace_path.parent.mkdir(parents=True)
        marketplace_path.write_text(
            json.dumps(
                {
                    "name": "starryeye",
                    "interface": {"displayName": "Starryeye Plugins"},
                    "plugins": [
                        {
                            "name": "web-translator",
                            "source": {
                                "source": "local",
                                "path": "./plugins/web-translator",
                            },
                            "policy": {
                                "installation": "AVAILABLE",
                                "authentication": "ON_INSTALL",
                            },
                            "category": "Productivity",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        plugin_root = self._plugin_root(root)
        manifest_path = self._manifest_path(root)
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "name": "web-translator",
                    "version": "0.1.0",
                    "skills": "./skills/",
                }
            ),
            encoding="utf-8",
        )
        (plugin_root / "skills").mkdir()


if __name__ == "__main__":
    unittest.main()

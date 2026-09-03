from __future__ import annotations

import contextlib
import copy
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import validate_marketplace as validator


REPOSITORY_VALIDATOR = (
    Path(__file__).resolve().parents[1] / "scripts" / "validate_marketplace.py"
)

VALID_SHA = "0123456789abcdef0123456789abcdef01234567"
VALID_ENTRY = {
    "name": "web-translator",
    "source": {
        "source": "url",
        "url": "https://github.com/starryeye/web-translator.git",
        "ref": "v0.5.2",
        "sha": VALID_SHA,
    },
    "version": "0.5.2",
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
    "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
    "category": "Productivity",
}


class MarketplaceValidatorTests(unittest.TestCase):
    def test_cli_runs_remote_verification_only_with_verify_remote_flag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository, sha = self._remote_fixture(root, tag=False)
            self._write_valid_repository(root)
            catalog = self._read_json(self._marketplace_path(root))
            catalog["plugins"][0]["source"].update(
                {"url": repository.as_uri(), "sha": sha}
            )
            self._write_json(self._marketplace_path(root), catalog)

            with mock.patch.object(
                validator, "EXPECTED_SOURCE_URL", repository.as_uri()
            ):
                without_flag, output = self._run_validator_main(root)
                with_flag, remote_output = self._run_validator_main(
                    root, "--verify-remote"
                )

            self.assertEqual(without_flag, 0, output)
            self.assertEqual(with_flag, 1, remote_output)
            self.assertIn("remote tag is missing", remote_output)

    def test_cli_skips_remote_verification_after_offline_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_valid_repository(root)
            self._marketplace_path(root).write_text("{not JSON", encoding="utf-8")

            status, output = self._run_validator_main(root, "--verify-remote")

            self.assertEqual(status, 1, output)
            self.assertIn("is not readable JSON", output)
            self.assertNotIn("remote tag lookup", output)

    def test_remote_verification_accepts_matching_lightweight_tag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository, sha = self._remote_fixture(Path(directory))
            entry = copy.deepcopy(VALID_ENTRY)
            entry["source"]["sha"] = sha
            errors: list[str] = []

            validator._validate_remote_release(
                entry, errors, clone_url=repository.as_uri()
            )

            self.assertEqual(errors, [])

    def test_remote_verification_accepts_matching_annotated_tag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository, sha = self._remote_fixture(
                Path(directory), annotated_tag=True
            )
            entry = copy.deepcopy(VALID_ENTRY)
            entry["source"]["sha"] = sha
            errors: list[str] = []

            validator._validate_remote_release(
                entry, errors, clone_url=repository.as_uri()
            )

            self.assertEqual(errors, [])

    def test_remote_verification_rejects_missing_tag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository, sha = self._remote_fixture(Path(directory), tag=False)
            entry = copy.deepcopy(VALID_ENTRY)
            entry["source"]["sha"] = sha
            errors: list[str] = []

            validator._validate_remote_release(
                entry, errors, clone_url=repository.as_uri()
            )

            self.assertTrue(any("tag" in error for error in errors), errors)

    def test_remote_verification_rejects_sha_manifest_and_version_check_failures(
        self,
    ) -> None:
        cases = (
            ({"catalog_sha": "f" * 40}, "commit"),
            ({"version": "0.4.1"}, "manifest version"),
            ({"version_check_exit": 7}, "version check"),
            ({"malformed_manifest": True}, "readable JSON"),
        )
        for options, message in cases:
            with self.subTest(message), tempfile.TemporaryDirectory() as directory:
                fixture_options = {
                    key: value for key, value in options.items() if key != "catalog_sha"
                }
                repository, sha = self._remote_fixture(
                    Path(directory), **fixture_options
                )
                entry = copy.deepcopy(VALID_ENTRY)
                entry["source"]["sha"] = options.get("catalog_sha", sha)
                errors: list[str] = []

                validator._validate_remote_release(
                    entry, errors, clone_url=repository.as_uri()
                )

                self.assertTrue(any(message in error for error in errors), errors)

    def test_remote_verification_reports_a_concise_tag_lookup_error(self) -> None:
        entry = copy.deepcopy(VALID_ENTRY)
        errors: list[str] = []

        validator._validate_remote_release(
            entry, errors, clone_url="file:///path/that/does/not/exist"
        )

        self.assertTrue(any("remote tag lookup failed" in error for error in errors), errors)
        self.assertFalse(any("Traceback" in error for error in errors), errors)

    def test_remote_verification_reports_clone_failure_after_tag_lookup_and_removes_checkout(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository, sha = self._remote_fixture(Path(directory))
            entry = copy.deepcopy(VALID_ENTRY)
            entry["source"]["sha"] = sha
            errors: list[str] = []
            checkout_directories: list[Path] = []
            temporary_directory = tempfile.TemporaryDirectory
            run_checked = validator._run_checked

            class RecordingTemporaryDirectory(temporary_directory):
                def __enter__(self) -> str:
                    created_directory = super().__enter__()
                    checkout_directories.append(Path(created_directory))
                    return created_directory

            def delete_tag_before_clone(
                arguments: list[str | Path], label: str, found_errors: list[str]
            ) -> subprocess.CompletedProcess[str] | None:
                if label == "remote release clone":
                    self._git(repository, "tag", "-d", "v0.5.2")
                return run_checked(arguments, label, found_errors)

            with (
                mock.patch.object(
                    validator, "_run_checked", side_effect=delete_tag_before_clone
                ),
                mock.patch.object(
                    validator.tempfile, "TemporaryDirectory", RecordingTemporaryDirectory
                ),
            ):
                validator._validate_remote_release(
                    entry, errors, clone_url=repository.as_uri()
                )

            self.assertTrue(
                any("remote release clone failed" in error for error in errors), errors
            )
            self.assertFalse(any("Traceback" in error for error in errors), errors)
            self.assertEqual(len(checkout_directories), 1)
            self.assertFalse(checkout_directories[0].exists())

    def test_remote_verification_reports_commit_check_failure_after_clone_and_removes_checkout(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository, sha = self._remote_fixture(Path(directory))
            entry = copy.deepcopy(VALID_ENTRY)
            entry["source"]["sha"] = sha
            errors: list[str] = []
            checkout_directories: list[Path] = []
            temporary_directory = tempfile.TemporaryDirectory
            run_checked = validator._run_checked

            class RecordingTemporaryDirectory(temporary_directory):
                def __enter__(self) -> str:
                    created_directory = super().__enter__()
                    checkout_directories.append(Path(created_directory))
                    return created_directory

            def remove_checkout_before_commit_check(
                arguments: list[str | Path], label: str, found_errors: list[str]
            ) -> subprocess.CompletedProcess[str] | None:
                if label == "remote release commit check":
                    shutil.rmtree(Path(arguments[2]))
                return run_checked(arguments, label, found_errors)

            with (
                mock.patch.object(
                    validator,
                    "_run_checked",
                    side_effect=remove_checkout_before_commit_check,
                ),
                mock.patch.object(
                    validator.tempfile, "TemporaryDirectory", RecordingTemporaryDirectory
                ),
            ):
                validator._validate_remote_release(
                    entry, errors, clone_url=repository.as_uri()
                )

            self.assertTrue(
                any("remote release commit check failed" in error for error in errors),
                errors,
            )
            self.assertFalse(any("Traceback" in error for error in errors), errors)
            self.assertEqual(len(checkout_directories), 1)
            self.assertFalse(checkout_directories[0].exists())

    def test_accepts_catalog_only_remote_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_valid_repository(root)
            result = self._run_validator(root)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_remote_source_contract_mutations(self) -> None:
        cases = {
            "source": ("local", "source type"),
            "url": ("https://example.com/plugin.git", "source URL"),
            "ref": ("main", "release ref"),
            "sha": ("ABC", "commit SHA"),
        }
        for field, (value, message) in cases.items():
            with self.subTest(field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self._write_valid_repository(root)
                catalog = self._read_json(self._marketplace_path(root))
                catalog["plugins"][0]["source"][field] = value
                self._write_json(self._marketplace_path(root), catalog)
                result = self._run_validator(root)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)

    def test_rejects_version_metadata_policy_and_category_drift(self) -> None:
        mutations = (
            (lambda entry: entry.__setitem__("version", "0.4.1"), "release version"),
            (lambda entry: entry.__setitem__("description", "drift"), "listing metadata"),
            (
                lambda entry: entry["policy"].__setitem__("authentication", "ON_USE"),
                "policy",
            ),
            (lambda entry: entry.__setitem__("category", "Other"), "category"),
        )
        for mutate, message in mutations:
            with self.subTest(message), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self._write_valid_repository(root)
                catalog = self._read_json(self._marketplace_path(root))
                mutate(catalog["plugins"][0])
                self._write_json(self._marketplace_path(root), catalog)
                result = self._run_validator(root)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)

    def test_rejects_non_semver_release_versions(self) -> None:
        for version in ("1", "1.2", "01.2.3", "v0.4.0"):
            with self.subTest(version), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self._write_valid_repository(root)
                catalog = self._read_json(self._marketplace_path(root))
                catalog["plugins"][0]["version"] = version
                self._write_json(self._marketplace_path(root), catalog)
                result = self._run_validator(root)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("strict semantic version", result.stderr)

    def test_rejects_reintroduced_vendored_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_valid_repository(root)
            (root / "plugins" / "web-translator").mkdir(parents=True)
            result = self._run_validator(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("vendored plugin directory", result.stderr)

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
            with self.subTest(label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
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

    def test_rejects_invalid_plugin_collection_and_entry_types(self) -> None:
        cases = {
            "plugins is not a list": ({"plugins": {}}, "exactly one plugin"),
            "plugin entry is not an object": ({"plugins": ["web-translator"]}, "JSON object"),
        }
        for label, (replacement, message) in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self._write_valid_repository(root)
                catalog = self._read_json(self._marketplace_path(root))
                catalog.update(replacement)
                self._write_json(self._marketplace_path(root), catalog)
                result = self._run_validator(root)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)

    def test_reports_unreadable_json_without_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_valid_repository(root)
            self._marketplace_path(root).write_text("{not JSON", encoding="utf-8")
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

    def _run_validator_main(self, root: Path, *arguments: str) -> tuple[int, str]:
        output = io.StringIO()
        with (
            mock.patch.object(
                sys, "argv", [str(REPOSITORY_VALIDATOR), *arguments, str(root)]
            ),
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(output),
        ):
            status = validator.main()
        return status, output.getvalue()

    def _marketplace_path(self, root: Path) -> Path:
        return root / ".agents" / "plugins" / "marketplace.json"

    def _read_json(self, path: Path) -> dict[str, object]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, value: dict[str, object]) -> None:
        path.write_text(json.dumps(value), encoding="utf-8")

    def _write_valid_repository(self, root: Path) -> None:
        marketplace_path = self._marketplace_path(root)
        marketplace_path.parent.mkdir(parents=True)
        self._write_json(
            marketplace_path,
            {
                "name": "starryeye",
                "interface": {"displayName": "Starryeye Plugins"},
                "plugins": [copy.deepcopy(VALID_ENTRY)],
            },
        )

    def _git(self, repository: Path, *arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def _remote_fixture(
        self,
        root: Path,
        *,
        version: str = "0.5.2",
        tag: bool = True,
        annotated_tag: bool = False,
        version_check_exit: int = 0,
        malformed_manifest: bool = False,
    ) -> tuple[Path, str]:
        repository = root / "remote"
        repository.mkdir()
        self._git(repository, "init")
        self._git(repository, "config", "user.name", "Marketplace Tests")
        self._git(repository, "config", "user.email", "marketplace-tests@example.invalid")
        manifest = copy.deepcopy(VALID_ENTRY)
        for field in ("source", "policy", "category"):
            manifest.pop(field)
        manifest["version"] = version
        manifest["skills"] = "./skills/"
        manifest_path = repository / ".codex-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)
        if malformed_manifest:
            manifest_path.write_text("{not JSON", encoding="utf-8")
        else:
            self._write_json(manifest_path, manifest)
        (repository / "skills").mkdir()
        script = repository / "scripts" / "version.py"
        script.parent.mkdir()
        script.write_text(f"raise SystemExit({version_check_exit})\n", encoding="utf-8")
        self._git(repository, "add", ".")
        self._git(repository, "commit", "-m", "release fixture")
        sha = self._git(repository, "rev-parse", "HEAD")
        if tag:
            arguments = ["tag"]
            if annotated_tag:
                arguments.extend(["-a", "-m", "release fixture"])
            arguments.extend(["v0.5.2", sha])
            self._git(repository, *arguments)
        return repository, sha

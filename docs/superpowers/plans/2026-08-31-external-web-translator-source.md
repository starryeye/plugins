# External Web Translator Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Release `web-translator` 0.4.0 and make `starryeye/plugins` install that exact tag and commit directly from GitHub instead of shipping a vendored copy.

**Architecture:** `starryeye/web-translator` becomes the sole code source and publishes an immutable `v0.4.0` release. The `starryeye/plugins` catalog keeps only remote listing metadata plus a Codex `url` source pinned by both tag and SHA; its validator checks the catalog offline and can materialize the declared release for opt-in remote verification.

**Tech Stack:** Python 3.11 standard library, `unittest`, Git, GitHub CLI, Codex native `.agents/plugins/marketplace.json`

**Spec:** `docs/superpowers/specs/2026-08-31-external-web-translator-source-design.md`

## Global Constraints

- Upstream release version is exactly `0.4.0`; its immutable lightweight tag is exactly `v0.4.0`.
- Marketplace Git URL is exactly `https://github.com/starryeye/web-translator.git`.
- The marketplace pins both `ref: v0.4.0` and the 40-character lowercase release commit SHA.
- `plugins/web-translator` must not exist after migration.
- Windows and macOS setup instructions require Python 3.11 or newer.
- Unit tests never access the public network; only explicit release verification may do so.
- Human-facing README prose is reviewed directly and by executing its install flow, never by grep-style tests.
- Every commit is pushed immediately after creation.
- Do not modify or remove `/Users/starryeye/play/plugins/.worktrees/web-translator-0.3.0`.
- Do not force-push branches or move/delete the `v0.4.0` tag.

---

### Task 1: Prepare the upstream 0.4.0 release commit

**Files:**
- Modify: `/Users/starryeye/play/web-translator/.worktrees/release-0.4.0/.codex-plugin/plugin.json`
- Modify: `/Users/starryeye/play/web-translator/.worktrees/release-0.4.0/pyproject.toml`
- Modify: `/Users/starryeye/play/web-translator/.worktrees/release-0.4.0/src/web_translator/__init__.py`
- Modify: `/Users/starryeye/play/web-translator/.worktrees/release-0.4.0/README.md`
- Verify: `/Users/starryeye/play/web-translator/.worktrees/release-0.4.0/tests/test_versioning.py`

**Interfaces:**
- Consumes: upstream `main` at merge `82bd38ba0f6bf3d6baa747bbef47309a2ddee1de` or its fast-forward successor before work starts.
- Produces: pushed branch `codex/release-0.4.0` whose three release declarations all equal `0.4.0`.

- [ ] **Step 1: Create the isolated upstream worktree and verify its baseline**

Use `superpowers:using-git-worktrees`. From `/Users/starryeye/play/web-translator`, create `.worktrees/release-0.4.0` on branch `codex/release-0.4.0` after verifying `.worktrees/` is ignored. Run:

~~~bash
python3.11 -m unittest tests/test_versioning.py -v
python3.11 scripts/version.py check
git status --short --branch
~~~

Expected: three version tests pass, the version check prints `0.3.0`, and the new worktree is clean.

- [ ] **Step 2: Update all release declarations with the tested helper**

~~~bash
python3.11 scripts/version.py set 0.4.0
~~~

Expected stdout: `0.3.0 -> 0.4.0`. Do not hand-edit the three generated version declarations.

- [ ] **Step 3: Replace the obsolete marketplace-versioning paragraph**

Use `apply_patch` to replace the final two sentences of the README Versioning section with:

~~~markdown
Use `patch` for compatible fixes, `minor` for backward-compatible features, and
`major` for breaking changes. Marketplace releases reference an immutable upstream
tag and commit SHA; Codex materializes the pinned Git source declared by the marketplace.
~~~

Do not add a test that searches README text; it is human documentation.

- [ ] **Step 4: Verify release metadata**

~~~bash
python3.11 -m unittest tests/test_versioning.py -v
python3.11 scripts/version.py check
python3.11 scripts/version.py show
git diff --check
git diff -- .codex-plugin/plugin.json pyproject.toml src/web_translator/__init__.py README.md
~~~

Expected: tests pass, both version commands print `0.4.0`, diff check exits zero, and no translation behavior files changed.

- [ ] **Step 5: Commit and immediately push**

~~~bash
git add .codex-plugin/plugin.json pyproject.toml src/web_translator/__init__.py README.md
git commit -m "chore: release 0.4.0"
git push -u origin codex/release-0.4.0
~~~

Expected: the branch tracks `origin/codex/release-0.4.0` and is clean.

---

### Task 2: Verify, merge, tag, and publish upstream 0.4.0

**Files:**
- Verify: `/Users/starryeye/play/web-translator/.worktrees/release-0.4.0/tests/`
- Verify: `/Users/starryeye/play/web-translator/.worktrees/release-0.4.0/skills/web-translator/`
- Verify: `/Users/starryeye/play/web-translator/.worktrees/release-0.4.0/skills/pdf-translator/`

**Interfaces:**
- Consumes: pushed `codex/release-0.4.0` from Task 1.
- Produces: `origin/main`, lightweight tag `v0.4.0`, GitHub Release `v0.4.0`, and a concrete `release_sha` consumed by marketplace tasks.

- [ ] **Step 1: Run fresh full upstream verification**

~~~bash
python3.11 -m pytest -q
python3.11 scripts/version.py check
python3.11 /Users/starryeye/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/web-translator
python3.11 /Users/starryeye/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/pdf-translator
python3.11 /Users/starryeye/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
git diff --check
git status --short --branch
~~~

Expected: zero failures, both skills and plugin validate, version is `0.4.0`, and the branch is clean. Stop before merge on any failure.

- [ ] **Step 2: Merge the release branch into upstream main and push**

From `/Users/starryeye/play/web-translator`:

~~~bash
git fetch origin
git status --short --branch
git pull --ff-only origin main
git merge --no-ff codex/release-0.4.0 -m "Merge branch 'codex/release-0.4.0'"
git push origin main
~~~

Expected: `main` and `origin/main` identify the new merge commit. Stop if the pre-merge checkout is not clean.

- [ ] **Step 3: Tag the exact merge commit and publish the tag**

~~~bash
release_sha=$(git rev-parse HEAD)
test "$(printf '%s' "$release_sha" | wc -c | tr -d ' ')" = 40
if git ls-remote --exit-code --tags origin refs/tags/v0.4.0; then
  echo "v0.4.0 already exists" >&2
  exit 1
else
  tag_lookup_status=$?
  test "$tag_lookup_status" = 2
fi
git tag v0.4.0 "$release_sha"
git push origin v0.4.0
git ls-remote --tags origin refs/tags/v0.4.0
~~~

Expected: the `ls-remote` line begins with the exact `release_sha`. Preserve that literal value for the catalog.

- [ ] **Step 4: Create and verify the GitHub release**

~~~bash
gh release create v0.4.0 \
  --repo starryeye/web-translator \
  --title "v0.4.0" \
  --notes "Adds the text-selectable PDF translation workflow alongside webpage translation, preserves selectable Korean text and original images, produces translated.pdf/manifest.json/review-report.md, and supports Windows and macOS. This release is the immutable upstream source for the Starryeye Codex marketplace."
gh release view v0.4.0 --repo starryeye/web-translator
~~~

Expected: one published `v0.4.0` release targeting the tag.

- [ ] **Step 5: Verify upstream main and tag identity**

~~~bash
release_sha=$(git rev-parse v0.4.0^{commit})
test "$(git rev-parse main)" = "$release_sha"
test "$(git rev-parse v0.4.0^{commit})" = "$release_sha"
test "$(git rev-parse origin/main)" = "$release_sha"
python3.11 scripts/version.py check
~~~

Expected: all comparisons succeed and the version command prints `0.4.0`.

---

### Task 3: Replace vendored validation with the offline remote contract

**Files:**
- Modify: `/Users/starryeye/play/plugins/.worktrees/external-web-translator-source/tests/test_validate_marketplace.py`
- Modify: `/Users/starryeye/play/plugins/.worktrees/external-web-translator-source/scripts/validate_marketplace.py`
- Modify: `/Users/starryeye/play/plugins/.worktrees/external-web-translator-source/.agents/plugins/marketplace.json`
- Delete: `/Users/starryeye/play/plugins/.worktrees/external-web-translator-source/plugins/web-translator/`

**Interfaces:**
- Consumes: the literal `release_sha` produced by Task 2.
- Produces: `validate_repository(root) -> list[str]` for a catalog-only repository and an entry ready for remote verification.

- [ ] **Step 1: Replace vendored-layout tests with failing catalog behavior tests**

Keep subprocess-based `_run_validator` plus JSON read/write helpers. Define this hand-derived valid entry:

~~~python
VALID_SHA = "0123456789abcdef0123456789abcdef01234567"
VALID_ENTRY = {
    "name": "web-translator",
    "source": {
        "source": "url",
        "url": "https://github.com/starryeye/web-translator.git",
        "ref": "v0.4.0",
        "sha": VALID_SHA,
    },
    "version": "0.4.0",
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
~~~

Make `_write_valid_repository` write only `.agents/plugins/marketplace.json` with a deep copy of this entry. Add:

~~~python
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
        (lambda entry: entry["policy"].__setitem__("authentication", "ON_USE"), "policy"),
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
~~~

Retain a malformed marketplace JSON test asserting nonzero exit, `is not readable JSON`, and no `Traceback`. Remove tests for README wording, local plugin files, nested Git metadata, and vendored package version drift.

- [ ] **Step 2: Run tests and verify RED**

~~~bash
python3.11 -m unittest tests/test_validate_marketplace.py -v
~~~

Expected: failures because the current validator requires a local source and vendored directory. Fix fixture errors until that is the reason.

- [ ] **Step 3: Implement the offline validator contract**

Retain `_read_json_object` and strict SemVer. Add:

~~~python
import os

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
    "name", "source", "version", "description", "author", "repository",
    "interface", "policy", "category",
}
~~~

Implement `def _validate_catalog(root: Path, catalog: dict[str, Any], errors: list[str]) -> dict[str, Any] | None` with these observable checks, returning the entry after validation:

~~~python
entry = plugins[0]
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
~~~

Delete `tomllib` and all local manifest/package validation. `validate_repository` parses the catalog, calls `_validate_catalog`, and returns collected errors.

- [ ] **Step 4: Apply the actual catalog and remove the vendored snapshot**

From upstream main, print the immutable release identity:

~~~bash
release_sha=$(git rev-parse v0.4.0^{commit})
test "$(git rev-parse origin/main)" = "$release_sha"
printf '%s\n' "$release_sha"
~~~

Copy that exact stdout literally into the `sha` JSON string with `apply_patch`. Use the full `VALID_ENTRY` shape, replacing only its fixture SHA. Remove the tracked snapshot:

~~~bash
git rm -r plugins/web-translator
~~~

- [ ] **Step 5: Verify GREEN**

~~~bash
python3.11 -m unittest tests/test_validate_marketplace.py -v
python3.11 scripts/validate_marketplace.py
git diff --check
~~~

Expected: all tests pass and offline validation reports `Marketplace validation passed`. Mutation check: URL, ref, SHA shape, version, metadata, policy, category, and vendored-directory mutations each fail a test.

- [ ] **Step 6: Commit and immediately push**

~~~bash
git add .agents/plugins/marketplace.json scripts/validate_marketplace.py tests/test_validate_marketplace.py
git add -u plugins/web-translator
git commit -m "Use external web translator release"
git push
~~~

Expected: the remote branch advances and is clean.

---

### Task 4: Add opt-in remote release verification

**Files:**
- Modify: `/Users/starryeye/play/plugins/.worktrees/external-web-translator-source/tests/test_validate_marketplace.py`
- Modify: `/Users/starryeye/play/plugins/.worktrees/external-web-translator-source/scripts/validate_marketplace.py`

**Interfaces:**
- Consumes: the validated entry returned by Task 3.
- Produces: `_validate_remote_release(entry, errors, clone_url=None) -> None` and CLI flag `--verify-remote`.

- [ ] **Step 1: Add a real local-Git fixture**

Import `copy` and `from scripts import validate_marketplace as validator`. Add a test-class helper:

~~~python
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
    version: str = "0.4.0",
    tag: bool = True,
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
        self._git(repository, "tag", "v0.4.0", sha)
    return repository, sha
~~~

- [ ] **Step 2: Add remote behavior tests**

~~~python
def test_remote_verification_accepts_matching_lightweight_tag(self) -> None:
    with tempfile.TemporaryDirectory() as directory:
        repository, sha = self._remote_fixture(Path(directory))
        entry = copy.deepcopy(VALID_ENTRY)
        entry["source"]["sha"] = sha
        errors: list[str] = []
        validator._validate_remote_release(entry, errors, clone_url=repository.as_uri())
        self.assertEqual(errors, [])

def test_remote_verification_rejects_missing_tag(self) -> None:
    with tempfile.TemporaryDirectory() as directory:
        repository, sha = self._remote_fixture(Path(directory), tag=False)
        entry = copy.deepcopy(VALID_ENTRY)
        entry["source"]["sha"] = sha
        errors: list[str] = []
        validator._validate_remote_release(entry, errors, clone_url=repository.as_uri())
        self.assertTrue(any("tag" in error for error in errors), errors)

def test_remote_verification_rejects_sha_manifest_and_version_check_failures(self) -> None:
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
            repository, sha = self._remote_fixture(Path(directory), **fixture_options)
            entry = copy.deepcopy(VALID_ENTRY)
            entry["source"]["sha"] = options.get("catalog_sha", sha)
            errors: list[str] = []
            validator._validate_remote_release(
                entry, errors, clone_url=repository.as_uri()
            )
            self.assertTrue(any(message in error for error in errors), errors)
~~~

Add one nonexistent `file:///` URL case and assert a concise Git error without `Traceback`.

- [ ] **Step 3: Run focused test and verify RED**

~~~bash
python3.11 -m unittest tests.test_validate_marketplace.MarketplaceValidatorTests.test_remote_verification_accepts_matching_lightweight_tag -v
~~~

Expected: failure because `_validate_remote_release` does not exist. Fix only fixture errors until that is the reason.

- [ ] **Step 4: Implement the remote verifier**

Import `subprocess` and `tempfile`. Add this process helper so every failure becomes validator evidence instead of an exception:

~~~python
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
    except (OSError, subprocess.TimeoutExpired) as error:
        errors.append(f"{label} failed: {error}")
        return None
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        errors.append(f"{label} failed: {detail}")
        return None
    return result
~~~

Implement the verifier with this control flow:

~~~python
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

    with tempfile.TemporaryDirectory(prefix="starryeye-plugin-") as directory:
        checkout = Path(directory) / "web-translator"
        cloned = _run_checked(
            [
                "git", "clone", "--quiet", "--depth", "1", "--branch",
                ref_name, url, checkout,
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
~~~

`TemporaryDirectory` owns checkout cleanup on every return path. The helper's argument array prevents shell interpretation of URLs and paths.

Add `--verify-remote` in `_parse_args`. `main` runs remote verification only after offline validation succeeds and the flag is present.

- [ ] **Step 5: Verify GREEN**

~~~bash
python3.11 -m unittest tests/test_validate_marketplace.py -v
python3.11 scripts/validate_marketplace.py
git diff --check
~~~

Expected: all fixture tests pass without public network access and offline validation passes.

- [ ] **Step 6: Commit and immediately push**

~~~bash
git add scripts/validate_marketplace.py tests/test_validate_marketplace.py
git commit -m "Verify remote plugin releases"
git push
~~~

Expected: remote branch advances and is clean.

---

### Task 5: Rewrite marketplace documentation

**Files:**
- Modify: `/Users/starryeye/play/plugins/.worktrees/external-web-translator-source/README.md`

**Interfaces:**
- Consumes: published `v0.4.0`, catalog-only layout, and `--verify-remote`.
- Produces: Windows/macOS instructions without vendored paths.

- [ ] **Step 1: Replace README with the approved catalog-only content**

Use `apply_patch`. Include this exact structure and commands:

~~~markdown
# Starryeye Plugins

This repository is a catalog-only Codex plugin marketplace maintained by
[starryeye](https://github.com/starryeye). Plugin code stays in its upstream
repository and each marketplace release pins an immutable Git tag and commit.

## Available plugins

### Web Translator

`web-translator` provides separate reviewed Korean translation workflows for one
supported public static HTML page and one local, attached, or public text-selectable
PDF. It supports Windows and macOS with Python 3.11 or newer.

- Upstream: <https://github.com/starryeye/web-translator>
- Release: [`v0.4.0`](https://github.com/starryeye/web-translator/releases/tag/v0.4.0)

## Install the marketplace and plugin

```text
codex plugin marketplace add https://github.com/starryeye/plugins.git --ref main --sparse .agents/plugins
codex plugin add web-translator@starryeye
```

The marketplace install loads the skills but does not install Python, Chromium, or
Poppler. Complete runtime setup in every workspace where translation tasks run.

## Runtime setup

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install "web-translator[test] @ git+https://github.com/starryeye/web-translator.git@v0.4.0"
& .\.venv\Scripts\python.exe -m playwright install chromium
winget install -e --id oschwartz10612.Poppler
```

Open a new PowerShell after Poppler installation.

### macOS POSIX shell

```bash
python3.11 -m venv .venv
./.venv/bin/python -m pip install "web-translator[test] @ git+https://github.com/starryeye/web-translator.git@v0.4.0"
./.venv/bin/python -m playwright install chromium
brew install poppler
```

Start a new Codex task from that workspace after setup. Both skills resolve `.venv`
relative to the active task workspace.

## Maintainer release flow

Release and push `starryeye/web-translator` first. Create an immutable SemVer tag,
copy its exact commit SHA into `.agents/plugins/marketplace.json`, update catalog
fallback metadata, and run:

```bash
python3.11 -m unittest tests/test_validate_marketplace.py -v
python3.11 scripts/validate_marketplace.py
python3.11 scripts/validate_marketplace.py --verify-remote
git diff --check
```

The standard validator is offline. `--verify-remote` accesses the declared Git
source, verifies tag and commit, compares manifest metadata, and runs the upstream
version consistency check.
~~~

Do not mention vendored sparse checkout, vendored editable installs, or snapshot replacement.

- [ ] **Step 2: Review documentation directly**

Read rendered Markdown and verify: catalog-only purpose, HTML/PDF support, `v0.4.0`, only `.agents/plugins` in sparse checkout, workspace-local `.venv`, Windows Chromium/Poppler, macOS Chromium/Poppler, and both validator modes. Do not add a string-presence test.

- [ ] **Step 3: Run repository checks**

~~~bash
python3.11 -m unittest tests/test_validate_marketplace.py -v
python3.11 scripts/validate_marketplace.py
git diff --check
git diff -- README.md
~~~

Expected: tests and offline validation remain green; README contains no vendored-install instructions.

- [ ] **Step 4: Commit and immediately push**

~~~bash
git add README.md
git commit -m "Document external plugin installation"
git push
~~~

Expected: remote branch advances and is clean.

---

### Task 6: Verify published source, smoke-test installation, and merge marketplace

**Files:**
- Verify: `/Users/starryeye/play/plugins/.worktrees/external-web-translator-source/.agents/plugins/marketplace.json`
- Verify: `/Users/starryeye/play/plugins/.worktrees/external-web-translator-source/scripts/validate_marketplace.py`
- Verify: `/Users/starryeye/play/plugins/.worktrees/external-web-translator-source/tests/test_validate_marketplace.py`
- Verify: `/Users/starryeye/play/plugins/.worktrees/external-web-translator-source/README.md`

**Interfaces:**
- Consumes: all pushed commits from Tasks 1–5.
- Produces: verified `origin/main` for `starryeye/plugins` and explicit smoke evidence or an exact CLI limitation.

- [ ] **Step 1: Run fresh final branch verification**

~~~bash
python3.11 -m unittest tests/test_validate_marketplace.py -v
python3.11 scripts/validate_marketplace.py
python3.11 scripts/validate_marketplace.py --verify-remote
git diff --check
git status --short --branch
~~~

Expected: all tests pass, both validators pass, diff check exits zero, and branch is clean.

- [ ] **Step 2: Attempt real Codex installation in isolated state**

~~~bash
command -v codex
~~~

If it prints a path:

~~~bash
smoke_codex_dir=$(mktemp -d)
CODEX_HOME="$smoke_codex_dir" codex plugin marketplace add "$PWD"
CODEX_HOME="$smoke_codex_dir" codex plugin add web-translator@starryeye
CODEX_HOME="$smoke_codex_dir" codex plugin list
printf 'Codex smoke home: %s\n' "$smoke_codex_dir"
~~~

Expected: list shows `web-translator@starryeye` at version `0.4.0`. Preserve the temporary path in evidence. If no executable is found, record exactly `Codex CLI unavailable on PATH; installation smoke test not run` and do not claim pass.

- [ ] **Step 3: Review complete branch diff**

~~~bash
git diff --stat main...HEAD
git diff --name-status main...HEAD
git log --oneline main..HEAD
~~~

Expected: approved spec/plan, marketplace JSON, validator/tests, README, and deletions under `plugins/web-translator` only.

- [ ] **Step 4: Merge marketplace branch and push**

From `/Users/starryeye/play/plugins`:

~~~bash
git fetch origin
git status --short --branch
git pull --ff-only origin main
git merge --no-ff codex/external-web-translator-source -m "Merge branch 'codex/external-web-translator-source'"
git push origin main
~~~

Expected: `main` and `origin/main` identify the merge commit. Stop if main is dirty.

- [ ] **Step 5: Re-run post-merge verification**

~~~bash
python3.11 -m unittest tests/test_validate_marketplace.py -v
python3.11 scripts/validate_marketplace.py
python3.11 scripts/validate_marketplace.py --verify-remote
git diff --check
test "$(git rev-parse main)" = "$(git rev-parse origin/main)"
~~~

Expected: all tests and validators pass and local/remote main SHAs match.

- [ ] **Step 6: Finish branches safely**

Invoke `superpowers:finishing-a-development-branch`. Remove only the new worktrees after verifying they are clean and reachable from main. Do not touch `/Users/starryeye/play/plugins/.worktrees/web-translator-0.3.0`. Delete remote feature branches only with explicit user approval.

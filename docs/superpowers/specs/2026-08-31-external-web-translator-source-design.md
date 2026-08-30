# External Web Translator Source Design

## Goal

Change the `starryeye/plugins` marketplace from a vendored `web-translator`
snapshot to a reproducible external Git source. Release `web-translator` 0.4.0,
pin the marketplace entry to the immutable `v0.4.0` tag and its exact commit,
and preserve a useful Codex marketplace listing before the remote source is
materialized.

## Scope

This release changes two repositories:

- `starryeye/web-translator` becomes the only source of plugin code and publishes
  version 0.4.0.
- `starryeye/plugins` becomes a catalog-only repository and removes
  `plugins/web-translator`.

The translation workflows, supported inputs, output contracts, and runtime
dependencies do not change as part of this migration. The already-merged PDF
translator is the feature that makes the upstream release a SemVer minor bump
from 0.3.0 to 0.4.0.

## Repository boundaries

`web-translator` owns all executable code, skills, tests, plugin metadata, and
Python packaging metadata. Its release version remains synchronized across
`.codex-plugin/plugin.json`, `pyproject.toml`, and
`src/web_translator/__init__.py` by `scripts/version.py`.

`plugins` owns only marketplace discovery metadata, installation and maintainer
documentation, marketplace validation, and tests for that validation. It must
not contain a `plugins/web-translator` directory after the migration. The
existing `codex/web-translator-0.3.0` worktree is unrelated historical state and
must not be changed or removed by this work.

## Upstream 0.4.0 release

The upstream release sequence is:

1. Run `scripts/version.py set 0.4.0` in `web-translator`.
2. Update upstream documentation that still says marketplace releases vendor a
   committed snapshot.
3. Run the complete deterministic test suite, both skill validators, the plugin
   validator, version validation, and repository diff checks.
4. Commit and push the release branch, merge it to `main`, and push `main`.
5. Create a lightweight `v0.4.0` tag at the resulting `main` release commit and
   push the tag without force.
6. Create the GitHub `v0.4.0` release with notes covering PDF translation,
   cross-platform support, and the external-marketplace source contract.

The tag is immutable. A failed or superseded release receives a new SemVer tag;
the release process never rewrites `v0.4.0`.

## Marketplace source contract

The `web-translator` entry in `.agents/plugins/marketplace.json` uses a Codex
native Git source object with all of these values:

- source type: `url`
- URL: `https://github.com/starryeye/web-translator.git`
- ref: `v0.4.0`
- SHA: the 40-character lowercase commit ID produced by
  `git rev-parse v0.4.0^{commit}` after the tag is pushed

The entry retains installation policy `AVAILABLE`, authentication policy
`ON_INSTALL`, and category `Productivity`. It also carries the release version,
description, author, repository, and non-path listing interface metadata copied
from the upstream 0.4.0 plugin manifest. This fallback metadata lets Codex render
the remote plugin before installation. Path-bearing interface assets are not
added to the catalog because Codex cannot resolve them before materializing a
remote source.

The catalog does not use Claude marketplace fields such as `strict`. Codex's
native `url`, `ref`, and `sha` fields provide the required source identity.

## Installation and runtime setup

The marketplace repository registration needs only its manifest in the sparse
checkout:

```text
codex plugin marketplace add https://github.com/starryeye/plugins.git --ref main --sparse .agents/plugins
codex plugin add web-translator@starryeye
```

Installing a Codex plugin materializes its skills but does not install the
plugin's Python, Chromium, or Poppler runtime. The README therefore directs the
user to create `.venv` in the workspace where translation tasks will run and
install the same pinned release with this PEP 508 direct reference:

```text
web-translator[test] @ git+https://github.com/starryeye/web-translator.git@v0.4.0
```

The README provides native Windows PowerShell and macOS POSIX commands for the
virtual environment, package installation, Chromium installation, and Poppler
installation. The skills continue to resolve `.venv` from the active task
workspace, so the documentation must state that this workspace-local setup is a
runtime requirement rather than an optional development environment.

## Marketplace validation

`scripts/validate_marketplace.py` keeps its standard-library-only offline mode
and adds an opt-in `--verify-remote` mode.

Offline validation checks:

- the marketplace identity and exactly one `web-translator` entry;
- the exact URL source shape, release ref, and expected release metadata;
- strict SemVer and the invariant `ref == "v" + version`;
- a 40-character lowercase hexadecimal SHA;
- the existing policy and category contract;
- catalog fallback metadata consistency; and
- the absence of `plugins/web-translator`.

Remote validation additionally creates an isolated temporary checkout of the
declared ref, then checks:

- the checked-out commit equals the declared SHA;
- `.codex-plugin/plugin.json` names `web-translator` and declares the catalog
  version;
- catalog fallback metadata matches the corresponding upstream manifest fields;
- upstream `scripts/version.py check` succeeds; and
- the declared tag exists and resolves to the same commit.

Git subprocesses receive argument arrays and never shell command strings. Clone,
checkout, JSON, version, network, and subprocess failures are collected as
concise validation errors without Python tracebacks. Temporary checkout cleanup
runs on success and failure.

## Tests

Implementation follows red-green-refactor. Existing tests that assert vendored
layout behavior are replaced with tests for the remote contract. Tests cover:

- acceptance of the exact catalog-only layout;
- rejection of wrong source type, URL, ref, SHA, version, policy, category, and
  fallback metadata;
- rejection when `plugins/web-translator` reappears;
- remote success using a temporary local Git repository and lightweight tag;
- remote failure for a missing tag, mismatched commit, mismatched manifest
  version, and failed upstream version check; and
- malformed JSON and Git failures without tracebacks.

Unit tests never access the public network. The final release verification runs
`--verify-remote` against GitHub only after `v0.4.0` exists. When a compatible
local Codex executable is available, an installation smoke test uses an isolated
temporary `CODEX_HOME` so it does not alter the user's installed marketplaces or
plugins. That smoke test executes the documented marketplace registration and
plugin installation flow; tests do not grep or parse human-facing README prose.
README version, commands, platform setup, and links receive direct maintainer
review plus `git diff --check`.

## Delivery order and failure handling

The upstream release must exist before the marketplace points to it:

```text
verify web-translator 0.4.0
-> push and merge the upstream release
-> push v0.4.0 and create its GitHub release
-> resolve and verify the tag commit
-> update and verify the plugins catalog
-> push and merge the marketplace change
-> smoke-test installation
```

Every commit is pushed immediately, following the repository workflow requested
by the maintainer. A nonzero verification command stops the sequence; later
publication steps do not run on partial evidence.

Rollback never moves or deletes the upstream tag. Reverting the marketplace
migration commit restores the prior vendored snapshot from Git history. A later
fixed external release uses a new version, tag, SHA, and marketplace commit.

## Acceptance criteria

The migration is complete only when:

1. `web-translator` main and tag `v0.4.0` identify the verified release commit.
2. The GitHub release for `v0.4.0` exists.
3. `plugins/main` contains no vendored plugin directory.
4. The marketplace entry pins the exact `v0.4.0` tag and commit SHA.
5. Offline marketplace tests and validation pass.
6. Remote validation against the published upstream tag passes.
7. Upstream version, tests, skill checks, plugin checks, and diff checks pass.
8. Installation smoke testing passes when the local Codex executable supports
   the required plugin commands, or the precise unavailable-command limitation
   is reported without claiming that smoke test passed.

# Starryeye Plugins

This repository is a catalog-only Codex plugin marketplace maintained by
[starryeye](https://github.com/starryeye). Plugin code stays in its upstream
repository and each marketplace release pins an immutable Git tag and commit.

## Available plugins

### supertranslator

`supertranslator` provides separate reviewed Korean translation workflows for one
supported public static HTML page and one local, attached, or public text-selectable
PDF. It supports Windows and macOS with Python 3.11 or newer.

- Upstream: <https://github.com/starryeye/supertranslator>
- Release: [`v0.8.0`](https://github.com/starryeye/supertranslator/releases/tag/v0.8.0)
- Skills: `supertranslator-web` for HTML and `supertranslator-pdf` for PDF.

## Install the marketplace and plugin

```text
codex plugin marketplace add https://github.com/starryeye/plugins.git --ref main --sparse .agents/plugins
codex plugin add supertranslator@starryeye
```

The marketplace install loads the skills but does not install Python, Chromium, or
Poppler. Complete runtime setup in every workspace where translation tasks run.

## Migrating from Web Translator 0.7.0

Version 0.8.0 is an intentional breaking rename, not an in-place upgrade. Remove
the old `web-translator@starryeye` plugin through Codex plugin management, then
install `supertranslator@starryeye` using the command above. This catalog contains
only the new identity; there is no legacy listing or executable alias. GitHub may
continue to redirect the old repository URL as platform behavior.

In each affected workspace, use that workspace's Python interpreter to run
`python -m pip uninstall web-translator`, then install the new `supertranslator`
distribution with the platform-specific setup below. The old module and command
are not provided. If the workspace directory moves, recreate its `.venv` at the
new absolute path instead of reusing old editable-install paths or shebangs.
These steps are explicit user actions; do not edit installed plugin caches or
automatically reinstall plugins in unrelated workspaces.

Use a new workspace/run for 0.8.0. Start a new Codex task after reinstalling so it
loads only `supertranslator-web` and `supertranslator-pdf`. New runs use
`.supertranslator/runs`; historical `.web-translator/runs` data is preserved but
is not discovered or supported for resume by 0.8.0. Do not move its internal files
into the new run root or rewrite embedded paths or digests. Finished HTML and PDF
artifacts remain readable.

## Runtime setup

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install "supertranslator[test] @ git+https://github.com/starryeye/supertranslator.git@v0.8.0"
& .\.venv\Scripts\python.exe -m playwright install chromium
winget install -e --id oschwartz10612.Poppler
```

Open a new PowerShell after Poppler installation.

### macOS POSIX shell

```bash
python3.11 -m venv .venv
./.venv/bin/python -m pip install "supertranslator[test] @ git+https://github.com/starryeye/supertranslator.git@v0.8.0"
./.venv/bin/python -m playwright install chromium
brew install poppler
```

Start a new Codex task from that workspace after setup. Both skills resolve `.venv`
relative to the active task workspace.

## Maintainer release flow

Release and push `starryeye/supertranslator` first. Create an immutable SemVer tag,
copy its exact commit SHA into `.agents/plugins/marketplace.json`, update catalog
fallback metadata, and update the expected release version and listing metadata in
`scripts/validate_marketplace.py` and the matching release fixtures in
`tests/test_validate_marketplace.py` alongside the catalog. Then run:

```bash
python3.11 -m unittest tests/test_validate_marketplace.py -v
python3.11 scripts/validate_marketplace.py
python3.11 scripts/validate_marketplace.py --verify-remote
git diff --check
```

The standard validator is offline. `--verify-remote` accesses the declared Git
source, verifies tag and commit, compares manifest metadata, and runs the upstream
version consistency check.

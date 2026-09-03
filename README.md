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
- Release: [`v0.5.2`](https://github.com/starryeye/web-translator/releases/tag/v0.5.2)

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
& .\.venv\Scripts\python.exe -m pip install "web-translator[test] @ git+https://github.com/starryeye/web-translator.git@v0.5.2"
& .\.venv\Scripts\python.exe -m playwright install chromium
winget install -e --id oschwartz10612.Poppler
```

Open a new PowerShell after Poppler installation.

### macOS POSIX shell

```bash
python3.11 -m venv .venv
./.venv/bin/python -m pip install "web-translator[test] @ git+https://github.com/starryeye/web-translator.git@v0.5.2"
./.venv/bin/python -m playwright install chromium
brew install poppler
```

Start a new Codex task from that workspace after setup. Both skills resolve `.venv`
relative to the active task workspace.

## Maintainer release flow

Release and push `starryeye/web-translator` first. Create an immutable SemVer tag,
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

# Web Translator Marketplace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained `starryeye` Codex marketplace that installs the vendored `web-translator` plugin snapshot.

**Architecture:** The repository-local marketplace catalog points to `./plugins/web-translator`. That directory is a byte-for-byte snapshot of upstream commit `09460540cb3a509b897f8e4d6e86d8439011d0d0`, excluding only nested Git metadata, while the root README records provenance and user/maintainer commands.

**Tech Stack:** Codex plugin JSON, Python 3.11+, Git, the bundled `plugin-creator` validation scripts, Markdown.

## Global Constraints

- Marketplace name is exactly `starryeye`; display name is exactly `Starryeye Plugins`.
- Plugin name and folder name are exactly `web-translator`.
- Marketplace source is local path `./plugins/web-translator`.
- Installation policy is `AVAILABLE`; authentication policy is `ON_INSTALL`; category is `Productivity`.
- Vendor upstream `main` commit `09460540cb3a509b897f8e4d6e86d8439011d0d0` without nested `.git` metadata.
- Do not modify the vendored plugin's behavior.
- Do not run live/network-marked plugin tests as deterministic validation.
- Do not publish or push the marketplace as part of implementation.

---

### Task 1: Marketplace catalog and vendored plugin

**Files:**

- Create: `.agents/plugins/marketplace.json`
- Create: `plugins/web-translator/**`

**Interfaces:**

- Consumes: upstream repository `https://github.com/starryeye/web-translator` at commit `09460540cb3a509b897f8e4d6e86d8439011d0d0`
- Produces: marketplace entry `web-translator@starryeye` resolving to `./plugins/web-translator`

- [ ] **Step 1: Verify the marketplace does not exist yet**

Run:

```bash
python3 -c 'from pathlib import Path; assert Path(".agents/plugins/marketplace.json").is_file()'
```

Expected: FAIL with `AssertionError`, proving the marketplace artifact is not already present.

- [ ] **Step 2: Scaffold the repo-local marketplace entry**

Run:

```bash
python3 /Users/starryeye/.codex/skills/.system/plugin-creator/scripts/create_basic_plugin.py web-translator --path /Users/starryeye/play/plugins/plugins --marketplace-path /Users/starryeye/play/plugins/.agents/plugins/marketplace.json --with-marketplace --marketplace-name starryeye
```

Expected: creates `.agents/plugins/marketplace.json` and a valid temporary `plugins/web-translator` scaffold.

The generated catalog must be equivalent to:

```json
{
  "name": "starryeye",
  "interface": {
    "displayName": "Starryeye Plugins"
  },
  "plugins": [
    {
      "name": "web-translator",
      "source": {
        "source": "local",
        "path": "./plugins/web-translator"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity"
    }
  ]
}
```

If the scaffold uses its default display name or category, update only those generated values to match the JSON above.

- [ ] **Step 3: Fetch the pinned upstream snapshot into a temporary directory**

Run each command separately:

```bash
snapshot_dir=$(mktemp -d)
git clone --no-checkout https://github.com/starryeye/web-translator.git "$snapshot_dir/web-translator"
git -C "$snapshot_dir/web-translator" checkout --detach 09460540cb3a509b897f8e4d6e86d8439011d0d0
git -C "$snapshot_dir/web-translator" rev-parse HEAD
```

Expected final output:

```text
09460540cb3a509b897f8e4d6e86d8439011d0d0
```

- [ ] **Step 4: Replace the temporary scaffold with the upstream working tree**

Run:

```bash
rsync -a --delete --exclude=.git/ "$snapshot_dir/web-translator/" plugins/web-translator/
```

Then verify nested Git metadata was excluded:

```bash
test ! -e plugins/web-translator/.git
```

Expected: exit code 0.

- [ ] **Step 5: Validate the catalog contract and plugin manifest**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path

catalog = json.loads(Path('.agents/plugins/marketplace.json').read_text())
assert catalog['name'] == 'starryeye'
assert catalog['interface']['displayName'] == 'Starryeye Plugins'
assert catalog['plugins'] == [{
    'name': 'web-translator',
    'source': {'source': 'local', 'path': './plugins/web-translator'},
    'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'},
    'category': 'Productivity',
}]

manifest = json.loads(Path('plugins/web-translator/.codex-plugin/plugin.json').read_text())
assert manifest['name'] == 'web-translator'
assert manifest['version'] == '0.1.0'
PY
```

Expected: exit code 0 with no output.

Run:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" plugins/web-translator
```

Expected: plugin validation succeeds with no errors.

- [ ] **Step 6: Commit the marketplace core**

```bash
git add .agents/plugins/marketplace.json plugins/web-translator
git commit -m "Add web translator marketplace plugin"
```

### Task 2: Marketplace usage and provenance documentation

**Files:**

- Modify: `README.md`

**Interfaces:**

- Consumes: `web-translator@starryeye` from Task 1 and pinned upstream SHA `09460540cb3a509b897f8e4d6e86d8439011d0d0`
- Produces: user installation commands and maintainer refresh procedure

- [ ] **Step 1: Verify the existing README lacks the marketplace contract**

Run:

```bash
python3 - <<'PY'
from pathlib import Path

text = Path('README.md').read_text()
assert 'codex plugin marketplace add' in text
assert 'web-translator@starryeye' in text
assert '09460540cb3a509b897f8e4d6e86d8439011d0d0' in text
PY
```

Expected: FAIL with `AssertionError`.

- [ ] **Step 2: Replace the minimal README with marketplace documentation**

Write `README.md` with this exact content:

````markdown
# Starryeye Plugins

A self-contained Codex plugin marketplace maintained by [starryeye](https://github.com/starryeye).

## Available plugins

### Web Translator

`web-translator` translates one public static web page into a reviewed offline Korean HTML bundle while preserving its structure and assets.

- Upstream: <https://github.com/starryeye/web-translator>
- Vendored commit: [`09460540cb3a509b897f8e4d6e86d8439011d0d0`](https://github.com/starryeye/web-translator/commit/09460540cb3a509b897f8e4d6e86d8439011d0d0)
- Runtime: Windows-first, Python 3.11 or newer

## Install

Clone this repository, then register its root as a local marketplace:

```bash
codex plugin marketplace add /absolute/path/to/plugins
codex plugin add web-translator@starryeye
```

Start a new Codex task after installation so the plugin skill is loaded. Before using the translator, follow the [upstream Windows setup](https://github.com/starryeye/web-translator#windows-setup), including the Playwright Chromium installation.

## Update the vendored plugin

Fetch the desired upstream commit into a temporary checkout, replace `plugins/web-translator` while excluding `.git`, and update the vendored commit link above. Then run:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" plugins/web-translator
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
```

The marketplace intentionally pins a snapshot. Installing it never downloads a moving `main` branch.
````

- [ ] **Step 3: Verify README installation and provenance details**

Run:

```bash
python3 - <<'PY'
from pathlib import Path

text = Path('README.md').read_text()
required = (
    '# Starryeye Plugins',
    'codex plugin marketplace add /absolute/path/to/plugins',
    'codex plugin add web-translator@starryeye',
    '09460540cb3a509b897f8e4d6e86d8439011d0d0',
    'Windows-first, Python 3.11 or newer',
    'validate_plugin.py" plugins/web-translator',
)
for item in required:
    assert item in text, item
PY
```

Expected: exit code 0 with no output.

- [ ] **Step 4: Run deterministic plugin tests in an isolated temporary environment**

Run each command separately:

```bash
test_env=$(mktemp -d)
python3 -m venv "$test_env/venv"
"$test_env/venv/bin/python" -m pip install -e './plugins/web-translator[test]'
"$test_env/venv/bin/python" -m playwright install chromium
(
  cd plugins/web-translator
  "$test_env/venv/bin/python" -m pytest tests -q
)
```

Expected: dependency and Chromium installation succeed, and pytest reports zero failures. The upstream `pyproject.toml` excludes `live` tests by default.

- [ ] **Step 5: Run final repository checks**

Run:

```bash
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" plugins/web-translator
git diff --check
git status --short
```

Expected: JSON parsing and plugin validation succeed, `git diff --check` reports nothing, and Git status lists `README.md` plus this implementation plan only when the plan portability correction has not yet been committed.

- [ ] **Step 6: Commit documentation and plan**

```bash
git add README.md docs/superpowers/plans/2026-08-13-web-translator-marketplace.md
git commit -m "Document marketplace installation"
```

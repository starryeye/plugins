# Web Translator Marketplace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained `starryeye` Codex marketplace that installs the vendored `web-translator` plugin snapshot.

**Architecture:** The repository-local marketplace catalog points to `./plugins/web-translator`. That directory is a byte-for-byte snapshot of upstream commit `09460540cb3a509b897f8e4d6e86d8439011d0d0`, excluding only nested Git metadata, while the root README records provenance and user/maintainer commands.

**Tech Stack:** Codex plugin JSON, Python 3.11+, standard-library `unittest`, Git, the bundled `plugin-creator` validation scripts, PyYAML, Playwright Chromium, Markdown.

## Global Constraints

- Marketplace name is exactly `starryeye`; display name is exactly `Starryeye Plugins`.
- Plugin name and folder name are exactly `web-translator`.
- Marketplace source is local path `./plugins/web-translator`.
- Installation policy is `AVAILABLE`; authentication policy is `ON_INSTALL`; category is `Productivity`.
- Vendor upstream `main` commit `09460540cb3a509b897f8e4d6e86d8439011d0d0` without nested `.git` metadata.
- Do not modify the vendored plugin's behavior.
- Do not run live/network-marked plugin tests as deterministic validation.
- Do not publish or push the marketplace as part of implementation.

## Maintainer interpreter invariant

Never run validation with an ambient `python3`. Explicitly select Python 3.11 or newer,
verify its version, and use an isolated environment interpreter for repository tests,
repository validation, bundled plugin validation, and vendored plugin tests. Create this
environment after `plugins/web-translator` exists (Task 1, Step 4).

POSIX shell:

```bash
python3.11 -c 'import sys; assert sys.version_info >= (3, 11), sys.version'
python3.11 -m venv .venv-maintainer
./.venv-maintainer/bin/python -m pip install PyYAML -e './plugins/web-translator[test]'
./.venv-maintainer/bin/python -m playwright install chromium
```

PowerShell:

```powershell
py -3.11 -c "import sys; assert sys.version_info >= (3, 11), sys.version"
py -3.11 -m venv .venv-maintainer
$MaintainerPython = (Resolve-Path ".\.venv-maintainer\Scripts\python.exe").Path
& $MaintainerPython -m pip install PyYAML -e ".\plugins\web-translator[test]"
& $MaintainerPython -m playwright install chromium
```

---

### Task 1: Marketplace catalog and vendored plugin

**Files:**

- Create: `.agents/plugins/marketplace.json`
- Create: `plugins/web-translator/**`
- Create: `scripts/validate_marketplace.py`
- Create: `tests/test_validate_marketplace.py`
- Modify: `.gitignore`

**Interfaces:**

- Consumes: upstream repository `https://github.com/starryeye/web-translator` at commit `09460540cb3a509b897f8e4d6e86d8439011d0d0`
- Produces: marketplace entry `web-translator@starryeye` resolving to `./plugins/web-translator`

- [ ] **Step 1: Verify the marketplace does not exist yet**

Run:

```bash
python3.11 -c 'from pathlib import Path; assert Path(".agents/plugins/marketplace.json").is_file()'
```

Expected: FAIL with `AssertionError`, proving the marketplace artifact is not already present.

- [ ] **Step 2: Scaffold the repo-local marketplace entry**

Run:

```bash
python3.11 /Users/starryeye/.codex/skills/.system/plugin-creator/scripts/create_basic_plugin.py web-translator --path /Users/starryeye/play/plugins/plugins --marketplace-path /Users/starryeye/play/plugins/.agents/plugins/marketplace.json --with-marketplace --marketplace-name starryeye
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

- [ ] **Step 5: Bootstrap the isolated maintainer environment**

Run the POSIX or PowerShell commands in **Maintainer interpreter invariant** above.
Expected: the explicit interpreter reports Python 3.11 or newer; PyYAML, the vendored
test dependencies, and Playwright Chromium install successfully. Add
`.venv-maintainer/` to `.gitignore`.

- [ ] **Step 6: Drive the repository validator with focused tests**

Create `tests/test_validate_marketplace.py` first. Its fixtures must exercise the real
validator CLI and cover valid input plus every required rejection: marketplace identity,
the exact single entry and policy/category/local path, missing source directory, name
alignment, strict semver, declared skills path, nested `.git`, and unreadable JSON.

Run before the implementation exists:

```bash
./.venv-maintainer/bin/python -m unittest tests/test_validate_marketplace.py -v
```

PowerShell equivalent:

```powershell
& $MaintainerPython -m unittest .\tests\test_validate_marketplace.py -v
```

Expected RED: nonzero with the valid-layout test failing because
`scripts/validate_marketplace.py` does not exist. Add the smallest CLI shell, confirm the
valid-layout test passes, add the rejection cases, and run again. Expected contract RED:
the permissive shell returns zero for every invalid fixture.

Implement `scripts/validate_marketplace.py` using only the Python standard library, then
rerun the same focused command. Expected GREEN: all focused tests pass.

- [ ] **Step 7: Validate the real marketplace and bundled plugin**

POSIX shell:

```bash
./.venv-maintainer/bin/python scripts/validate_marketplace.py
./.venv-maintainer/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" plugins/web-translator
```

PowerShell:

```powershell
& $MaintainerPython .\scripts\validate_marketplace.py
$CodexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$PluginValidator = Join-Path $CodexRoot "skills\.system\plugin-creator\scripts\validate_plugin.py"
& $MaintainerPython $PluginValidator .\plugins\web-translator
```

Expected: both validators succeed. The plugin validator imports PyYAML from the isolated
environment rather than from the selected base interpreter.

- [ ] **Step 8: Commit the marketplace core**

```bash
git add .agents/plugins/marketplace.json plugins/web-translator .gitignore scripts tests
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
./.venv-maintainer/bin/python - <<'PY'
from pathlib import Path

text = Path('README.md').read_text()
assert 'codex plugin marketplace add' in text
assert 'web-translator@starryeye' in text
assert '09460540cb3a509b897f8e4d6e86d8439011d0d0' in text
PY
```

Expected: FAIL with `AssertionError`.

- [ ] **Step 2: Replace the minimal README with marketplace documentation**

Write `README.md` with the marketplace identity, pinned upstream SHA, and equivalent
PowerShell/POSIX workflows. Link setup to the local pinned
`plugins/web-translator/README.md`, not to upstream `main`. The preferred runtime workflow
must create `plugins/web-translator/.venv`, install the vendored package and Playwright
Chromium with its environment interpreter, and tell the user to open that directory as
the Codex task workspace. Explain the invariant that the skill resolves `.venv` relative
to the task workspace and provide the alternative of creating `.venv` in another intended
workspace and installing the vendored package there.

The maintainer section must reproduce **Maintainer interpreter invariant** for both shells
and run the focused repository tests, repository validator, bundled plugin validator, and
deterministic vendored suite with the isolated interpreter. Do not use `/dev/null` as the
only documented output handling and do not invoke a validator with ambient `python3`.

- [ ] **Step 3: Verify README installation and provenance details**

Run:

```bash
./.venv-maintainer/bin/python - <<'PY'
from pathlib import Path

text = Path('README.md').read_text()
required = (
    '# Starryeye Plugins',
    'codex plugin marketplace add',
    'codex plugin add web-translator@starryeye',
    '09460540cb3a509b897f8e4d6e86d8439011d0d0',
    'Windows-first, Python 3.11 or newer',
    'scripts/validate_marketplace.py',
    'plugins/web-translator/README.md#windows-setup',
    'PowerShell maintainer environment',
)
for item in required:
    assert item in text, item
PY
```

Expected: exit code 0 with no output.

- [ ] **Step 4: Run deterministic plugin tests from the isolated environment**

POSIX shell:

```bash
(
  cd plugins/web-translator
  ../../.venv-maintainer/bin/python -m pytest tests -q
)
```

PowerShell:

```powershell
Push-Location .\plugins\web-translator
try { & $MaintainerPython -m pytest tests -q } finally { Pop-Location }
```

Expected: pytest reports zero failures. The upstream `pyproject.toml` excludes `live`
tests by default. This full deterministic suite is required when the vendored snapshot
changes; root-only marketplace documentation or validator changes may rely on recorded
evidence plus the focused repository tests.

- [ ] **Step 5: Run final repository checks**

Run:

```bash
./.venv-maintainer/bin/python -m unittest tests/test_validate_marketplace.py -v
./.venv-maintainer/bin/python scripts/validate_marketplace.py
./.venv-maintainer/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" plugins/web-translator
git diff --check
git status --short
```

PowerShell equivalent:

```powershell
& $MaintainerPython -m unittest .\tests\test_validate_marketplace.py -v
& $MaintainerPython .\scripts\validate_marketplace.py
& $MaintainerPython $PluginValidator .\plugins\web-translator
git diff --check
git status --short
```

Expected: focused tests and both validators succeed, `git diff --check` reports nothing,
and Git status lists only the intentional root-owned changes.

- [ ] **Step 6: Commit documentation and plan**

```bash
git add README.md docs/superpowers/plans/2026-08-13-web-translator-marketplace.md
git commit -m "Document marketplace installation"
```

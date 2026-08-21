# Starryeye Plugins

A self-contained Codex plugin marketplace maintained by [starryeye](https://github.com/starryeye).

## Available plugins

### Web Translator

`web-translator` translates one public static web page into a reviewed offline Korean HTML bundle while preserving its structure and assets.

- Upstream: <https://github.com/starryeye/web-translator>
- Version: `0.3.0`
- Vendored commit: [`a868c6b5aa83f5691afe1b710aec031d39952e09`](https://github.com/starryeye/web-translator/commit/a868c6b5aa83f5691afe1b710aec031d39952e09)
- Runtime: Windows and macOS, Python 3.11 or newer

## Install

For a Git marketplace, include both the marketplace manifest and the vendored plugin
in Codex's sparse checkout. Omitting the plugin path lets Codex discover the catalog
entry but installation then fails because `plugins/web-translator` is absent.

PowerShell and POSIX shell:

```text
codex plugin marketplace add https://github.com/starryeye/plugins.git --ref main --sparse .agents/plugins --sparse plugins/web-translator
codex plugin add web-translator@starryeye
```

If `starryeye` was already registered without the plugin sparse path, replace that
registration before installing:

```text
codex plugin marketplace remove starryeye
codex plugin marketplace add https://github.com/starryeye/plugins.git --ref main --sparse .agents/plugins --sparse plugins/web-translator
codex plugin add web-translator@starryeye
```

The translator supports Windows and macOS; its pinned prerequisites are documented in the
[vendored plugin setup](plugins/web-translator/README.md#setup).

### Local clone alternative

You can instead clone this repository, register its root as a local marketplace, and
install the plugin.

PowerShell:

```powershell
git clone https://github.com/starryeye/plugins.git starryeye-plugins
Set-Location .\starryeye-plugins
codex plugin marketplace add (Resolve-Path ".").Path
codex plugin add web-translator@starryeye
Set-Location .\plugins\web-translator
py -3.11 -c "import sys; assert sys.version_info >= (3, 11), sys.version"
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m playwright install chromium
```

POSIX shell:

```bash
git clone https://github.com/starryeye/plugins.git starryeye-plugins
cd starryeye-plugins
codex plugin marketplace add "$PWD"
codex plugin add web-translator@starryeye
cd plugins/web-translator
python3.11 -c 'import sys; assert sys.version_info >= (3, 11), sys.version'
python3.11 -m venv .venv
./.venv/bin/python -m pip install -e '.[test]'
./.venv/bin/python -m playwright install chromium
```

After setup, open `starryeye-plugins/plugins/web-translator` as the Codex task workspace
and start a new task so the installed skill is loaded. This working directory is part of
the runtime contract: the skill resolves `.venv` relative to the task workspace and does
not rely on an activated environment. If you intentionally use a different task
workspace, create `.venv` in that workspace instead, install the vendored package into it
with `<environment-python> -m pip install -e <clone>/plugins/web-translator`, and run
`<environment-python> -m playwright install chromium`. Here, `<environment-python>` is
`<workspace>/.venv/Scripts/python.exe` on Windows or `<workspace>/.venv/bin/python` on
POSIX.

## Update the vendored plugin

Fetch the desired upstream commit into a temporary checkout, replace `plugins/web-translator` while excluding `.git`, and update the version and vendored commit link above. Keep `EXPECTED_PLUGIN_VERSION` in `scripts/validate_marketplace.py` synchronized with the release. The Codex marketplace UI reads the displayed version from the vendored plugin manifest. Then run:

### POSIX maintainer environment

```bash
python3.11 -c 'import sys; assert sys.version_info >= (3, 11), sys.version'
python3.11 -m venv .venv-maintainer
./.venv-maintainer/bin/python -m pip install PyYAML -e './plugins/web-translator[test]'
./.venv-maintainer/bin/python -m playwright install chromium
./.venv-maintainer/bin/python -m unittest tests/test_validate_marketplace.py -v
./.venv-maintainer/bin/python scripts/validate_marketplace.py
./.venv-maintainer/bin/python plugins/web-translator/scripts/version.py --root plugins/web-translator check
./.venv-maintainer/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" plugins/web-translator
(
  cd plugins/web-translator
  ../../.venv-maintainer/bin/python -m pytest tests -q
)
git diff --check
```

### PowerShell maintainer environment

```powershell
py -3.11 -c "import sys; assert sys.version_info >= (3, 11), sys.version"
py -3.11 -m venv .venv-maintainer
$MaintainerPython = (Resolve-Path ".\.venv-maintainer\Scripts\python.exe").Path
& $MaintainerPython -m pip install PyYAML -e ".\plugins\web-translator[test]"
& $MaintainerPython -m playwright install chromium
& $MaintainerPython -m unittest .\tests\test_validate_marketplace.py -v
& $MaintainerPython .\scripts\validate_marketplace.py
& $MaintainerPython .\plugins\web-translator\scripts\version.py --root .\plugins\web-translator check
$CodexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$PluginValidator = Join-Path $CodexRoot "skills\.system\plugin-creator\scripts\validate_plugin.py"
& $MaintainerPython $PluginValidator .\plugins\web-translator
Push-Location .\plugins\web-translator
try { & $MaintainerPython -m pytest tests -q } finally { Pop-Location }
git diff --check
```

The repository-local validator uses only the Python standard library and checks the
marketplace-to-manifest contract. PyYAML is installed because the bundled Codex plugin
validator imports it. The marketplace intentionally pins a snapshot; installing it never
downloads a moving `main` branch.

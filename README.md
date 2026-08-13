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

# Web Translator Marketplace Design

## Goal

Turn the `starryeye/plugins` repository into a Codex repo marketplace that distributes the current released state of `starryeye/web-translator` as a self-contained plugin.

## Scope

The marketplace will contain one plugin, `web-translator`. It will vendor a snapshot of the upstream repository rather than use a Git submodule or download code during installation. The work does not change the plugin's behavior or publish the marketplace remotely.

## Repository layout

```text
.
|-- .agents/plugins/marketplace.json
|-- plugins/
|   `-- web-translator/
|       |-- .codex-plugin/plugin.json
|       |-- skills/
|       |-- src/
|       |-- tests/
|       `-- supporting project files
|-- docs/superpowers/specs/
`-- README.md
```

The vendored plugin directory will contain the upstream `main` working tree captured during implementation, without its nested `.git` metadata. The root README will record the exact upstream commit SHA. This keeps the marketplace clone self-contained and makes the snapshot's provenance reproducible.

## Marketplace metadata

The marketplace file will use:

- Marketplace name: `starryeye`
- Display name: `Starryeye Plugins`
- Plugin name: `web-translator`
- Local source path: `./plugins/web-translator`
- Installation policy: `AVAILABLE`
- Authentication policy: `ON_INSTALL`
- Category: `Productivity`

The plugin name will remain identical to its directory name and to the name in `.codex-plugin/plugin.json`.

## Documentation

The root README will explain:

1. What the marketplace contains.
2. How to add this repository as a non-default local marketplace.
3. How to install `web-translator@starryeye`.
4. The plugin's Windows-first prerequisites.
5. The vendored snapshot's exact upstream commit SHA.
6. How maintainers refresh the snapshot from the upstream repository and validate it.

Commands will use repository-relative paths where practical and will distinguish marketplace registration from plugin installation.

## Update flow

An upstream update will be incorporated intentionally:

1. Obtain a clean snapshot of the desired upstream commit.
2. Replace the contents of `plugins/web-translator` while excluding nested Git metadata.
3. Confirm that the plugin manifest version and marketplace entry still match the plugin name.
4. Run plugin and marketplace validation.
5. Commit the snapshot together with any version or README changes.

No automatic latest-version download will run during user installation.

## Error handling and safety

- Marketplace validation will fail if required policy or category fields are missing.
- Plugin validation will fail if required manifest fields, referenced component paths, or semantic versions are invalid.
- Snapshot replacement will target only `plugins/web-translator`; unrelated repository files will remain untouched.
- Network-dependent upstream tests will not be treated as deterministic marketplace validation.

## Verification

Before delivery:

1. Parse `marketplace.json` as JSON and check its required metadata.
2. Run the bundled plugin validator against `plugins/web-translator`.
3. Run the plugin's deterministic test suite when its documented runtime is available in the current environment.
4. Inspect Git status and the final diff to ensure only marketplace, vendored plugin, documentation, and design files changed.

If platform-specific tests cannot run on macOS because the plugin is Windows-first, report that limitation explicitly rather than claiming those tests passed.

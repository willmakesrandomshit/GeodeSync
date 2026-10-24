# GeodeSync v2.3.0 — companion tools and safer setup

GeodeSync v2.3.0 expands the Geometry Dash companion dashboard with tools for mod maintenance, save insight, customization, and troubleshooting.

## New companion tools

- **Update Mods:** Check installed Geode mods against the Geode index and update selected mods or the available set. A compatibility guard filters a known-broken ImagePlus build for the supported game version.
- **Demon Tracker:** Read local Geometry Dash progress and active level grinds, with an option to copy a shareable summary.
- **Texture Packs:** Back up the original `Resources` folder before installing a selected pack, then restore the saved vanilla textures from the tool.
- **Keybind Doctor:** Inspect readable Geode configuration files for overlapping mod shortcuts.

## Dashboard and reliability

- Keep the player card, game and Geode status, Steam update lock, and primary setup action together on the dashboard.
- Search installed mods and enable or disable them from the mod manager.
- Keep version switching staged, validated, and recoverable, with detected save backups before file changes.
- Complete dashboard startup when Geode is installed but its version cannot be read; show an installed/unknown status instead of treating it as missing.
- Export a local diagnostic report for support. Review the report before sharing it.

Features depend on the platform and the installed GeodeSync build. Back up important saves and review confirmation prompts before changing game, mod, or texture files. Check the [user guide](USER_GUIDE.md) for setup and recovery instructions.

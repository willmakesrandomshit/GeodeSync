# GeodeSync v2.0.0 — safer switches and saved setups

GeodeSync v2 brings the everyday setup flow into one clearer home and makes game-file switching recoverable when Steam or the computer interrupts the process.

## Safer game switching

- Stage the complete Steam depot beside the installed game and validate it before touching the current installation.
- Check free disk space before staging. Existing game entries are moved aside and restored if a replacement fails.
- Write a recovery journal before replacing files. If the app exits or crashes mid-switch, the next launch restores the previous game files before another switch can begin.
- Back up detected Geometry Dash saves before a version change; stop if that backup fails, and ask before proceeding when no saves are found.
- Confirm that Geometry Dash is closed before replacing files.
- Validate supported Windows game builds against their expected executable size and macOS depots as complete app bundles.

## Game profiles and preferences

- Save a local profile containing a supported game version and the selected active Geode mods.
- Apply a profile through the same confirmation and recovery flow as a regular version switch.
- Keep the chosen game folder, backup preference, and selected target version across restarts.

## Better support and recovery

- Export a local support report with app, platform, Steam and game status, and recent activity.
- Keep report contents focused on diagnostics: save contents and mod files are not included, and common paths, emails, and secret-like values are redacted.
- Keep a bounded, rotating activity log and explain when startup recovery needs manual attention.
- Add regression coverage for successful switches, failed validation, partial writes, restart recovery, and committed cleanup.

## Interface

- Use one plum, lime, lilac, and warm-neutral visual system across the main screen and utility dialogs.
- Show Steam, save, game version, Geode, and update-lock status together.
- Put the recommended next action first and keep optional tools grouped out of the main flow.

The Windows and macOS packages are built by the existing release workflow. macOS builds target Apple silicon on macOS 11 or newer and Intel on macOS 10.15 or newer. Signing and notarization are applied only when the repository's Apple signing credentials are configured.

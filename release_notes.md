# GeodeSync v1.1.3 — consolidated stability and macOS hotfix

This release combines the earlier GeodeSync 1.1.3 features with the follow-up fixes for macOS installation, Steam recovery, game bundle validation, and app updates.

## macOS downgrade and recovery

- Prevent overlapping downgrade actions and replace the Geometry Dash app bundle transactionally, preserving the old install if validation or replacement fails.
- Resolve Steam's macOS depot from the canonical Steam.AppBundle location first; ignore stale or invalid cached depots.
- Validate the downloaded game bundle and its `Info.plist` before installing it. A Steam completion log alone is not accepted as proof that files are ready.
- If the depot is malformed or incomplete, leave the installed game untouched and report a recoverable error.
- Verify Steam manifest lock and unlock operations. Do not start Steam file verification when safely unlocking the manifest failed.
- Distinguish a Steam launch request from the game actually starting, and wait for slow launches before reporting failure.
- Report malformed bundle metadata clearly, including trailing or invalid plist content.

## App updater and compatibility

- Compare numeric app versions and never offer or install an older release.
- Verify Mac updater architecture, app bundle structure, and GitHub SHA-256 digest before replacing the app.
- Keep user saves and existing installations intact when an update or recovery step fails.

## Builds

- GitHub Actions builds Windows, Apple silicon, and Intel Mac packages and runs the regression suite.
- Mac builds include Python, Tcl, and Tk. Unsigned builds may require Control-click → Open once in macOS.

This release does not claim to repair a Geometry Dash installation that was already left corrupted. Use Steam's Verify integrity after restoring the game, then try launching from Steam before applying a downgrade again.

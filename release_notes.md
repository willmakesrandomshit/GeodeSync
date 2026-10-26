# GeodeSync v2.3.8 — Automatic verified updates

## Updates apply automatically

When GeodeSync finds a newer stable release, it downloads the official platform package, verifies its SHA-256 metadata and archive contents, then restarts to apply it without an approval dialog. If a Steam game-file download or switch is active, the verified update waits until that operation finishes. Clicking **Update now** also applies the verified package as soon as it is ready.

This behavior is available to installs after they have updated to v2.3.8. Older installed versions still use the updater behavior they shipped with for the first update to v2.3.8.

## Rich Presence

With **Keep in BG on close** enabled, closing the GeodeSync window minimizes it and keeps Discord Rich Presence connected. While Geometry Dash is running, the activity reads **Playing Geometry Dash with GeodeSync**; while the game is closed, it shows GeodeSync as a companion.

## Verification

The regression suite covers automatic update/restart behavior, waiting for active Steam file work, the Rich Presence payload, and background close behavior. The release workflow builds and tests Windows, macOS, and Linux packages.

# GeodeSync v2.3.7 — Discord Rich Presence stays active

## Keep Rich Presence running after closing the window

When **Keep in BG on close** is enabled, closing the GeodeSync window now minimizes the app instead of shutting it down. Discord Rich Presence therefore stays connected. While Geometry Dash is running, the activity reads **Playing Geometry Dash with GeodeSync**; when the game is closed, it shows GeodeSync as a companion.

Turn **Keep in BG on close** off before closing if you want to fully exit GeodeSync and clear its Rich Presence.

## Verification

The regression suite checks background close behavior, normal exit behavior, and the Discord activity payload. Windows, macOS, and Linux packages are built and tested by the release workflow.

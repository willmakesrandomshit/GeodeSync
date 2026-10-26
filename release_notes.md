# GeodeSync v2.3.9 — System tray and verified updates

## Close to the system tray on Windows

With **Close to System Tray** enabled, closing the dashboard hides GeodeSync in the Windows notification area while background monitoring and Discord Rich Presence continue. Right-click the GeodeSync tray icon to reopen the dashboard or exit the app. If tray support cannot start, the app minimizes to the taskbar instead. macOS and Linux retain their existing background behavior.

Windows path-opening now checks that local targets exist before asking the shell to open them, preventing a native missing-path dialog for stale or malformed targets. Steam protocol links remain supported.

## Verified automatic updates

GeodeSync downloads the official platform package, verifies its SHA-256 metadata and archive contents, then restarts to apply it without an approval dialog. If a Steam game-file download or switch is active, the verified update waits until that operation finishes. This behavior first shipped in v2.3.8.

## Verification

The release workflow runs the regression suite and packages Windows, macOS, and Linux builds. Windows packaging includes the tray runtime dependencies.

# GeodeSync v2.3.10 — Responsive dashboard

## Dashboard layout

Setup badges now sit below player stats instead of competing for the same row. The tools grid fills its card cleanly, long tool names wrap to their available column width, and footer status text resizes around the action buttons. This avoids overlaps and clipping at different window sizes and Windows display scaling settings.

## Windows system tray

With **Close to System Tray** enabled, closing the dashboard hides GeodeSync in the Windows notification area while background monitoring and Discord Rich Presence continue. Right-click the tray icon to reopen the dashboard or exit. If tray support cannot start, GeodeSync minimizes to the taskbar. macOS and Linux retain their existing background behavior.

## Verified automatic updates

GeodeSync downloads the official platform package, verifies its SHA-256 metadata and archive contents, then restarts to apply it. If a Steam game-file download or switch is active, the verified update waits until that operation finishes. Automatic updates first shipped in v2.3.8.

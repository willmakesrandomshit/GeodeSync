# GeodeSync v1.1.5 — macOS Depot Validation Hotfix

## Fixes

- Reject incomplete cached macOS game bundles before installing them. Damaged or partial Steam depot folders now go through the download path again instead of being mistaken for a completed download.
- Report malformed Geometry Dash `Info.plist` data as an invalid bundle instead of leaking an uncaught XML parser exception into the overwrite error.
- Preserve the installed game bundle when the downloaded app fails validation.

## Previous v1.1.4 fixes

- Prevent rapid repeated clicks from starting overlapping Geometry Dash downgrades and replacing the game app bundle concurrently.
- Stop the restore flow if GeodeSync cannot verify that Steam's app manifest was unlocked; Steam validation is no longer started after an unlock failure.
- Verify macOS Steam manifest lock/unlock state and roll back a failed lock attempt instead of leaving the manifest read-only.
- Keep the macOS launch monitor waiting for slow Steam launches and report when the process actually starts.

## macOS app and updates

- Download a ready-to-open app for Apple silicon (`arm64`) or Intel (`x86_64`).
- Python, Tcl, and Tk are bundled; no Terminal commands or separate runtime install are needed.
- **Update Now** downloads the build matching the Mac's processor, verifies its SHA-256 digest and app bundle, installs it beside the current app, and reopens GeodeSync.
- Apple silicon requires macOS 11 or newer. Intel requires macOS 10.15 or newer.
- Unsigned community builds require a one-time Control-click → **Open** approval from macOS.

## Windows

- The Windows executable and ZIP remain part of each release.
- The Windows in-app updater remains available.

The release is built from this repository by GitHub Actions. A tag is published only after the Windows, Apple silicon, and Intel build jobs succeed.

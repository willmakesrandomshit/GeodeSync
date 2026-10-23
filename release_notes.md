# GeodeSync v1.1.3

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

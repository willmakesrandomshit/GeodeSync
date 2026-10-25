# GeodeSync v2.3.2 — Windows runtime reliability update

This release changes the Windows package to keep its Python runtime beside the app. It addresses a failure mode reported during launch/update where PyInstaller could not load `python314.dll` from its temporary `_MEI...` extraction directory. The screenshot alone cannot establish whether the missing DLL came from extraction, security software, a damaged download, or another local issue.

## Changes

- Windows now ships as an onedir portable ZIP. Extract the complete ZIP and keep `_internal` beside `GeodeSync.exe`; no per-launch `_MEI...` runtime extraction is needed.
- Windows CI runs the regression suite before packaging.
- The latest release page and website use stable ZIP names, and the release includes SHA-256 checksums.
- The in-app updater continues to open the official Releases page for review. v2.3.0 clients that expect a standalone `GeodeSync.exe` will fall back to that page because new releases no longer publish a one-file executable.
- Existing installations are not silently replaced. Download and extract the latest ZIP, then launch the new executable.

## Compatibility and limits

GeodeSync remains a companion for Steam installations of Geometry Dash. Review confirmations before changing game files and back up important saves. Release builds are produced by GitHub Actions for Windows, macOS (Apple silicon and Intel), and Linux. A build target does not prove compatibility on every operating-system version or device. The Windows onedir package must be built and launched on Windows CI; it has not been tested on the affected user's machine.

This release is not Authenticode-signed or macOS-notarized unless the required publisher credentials are configured in the release workflow. Check the asset checksums and read [SECURITY.md](SECURITY.md) for verification details.

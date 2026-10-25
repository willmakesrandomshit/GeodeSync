# GeodeSync v2.3.3 — Windows game-file validation hotfix

This hotfix strengthens Windows game-version switching after a report of `GeometryDash.exe - Bad Image` for `libcrypto-3-x64.dll` (Windows error `0xc000007b`). The report alone could not identify whether the DLL was damaged, the wrong architecture, or left over from an earlier install.

## Changes

- Validate the staged `GeometryDash.exe` and every staged DLL as Windows PE files before changing the installed game.
- Reject damaged DLL headers and DLLs whose architecture does not match the game executable.
- Validate the assembled game folder before marking a switch successful; roll back the switch if a damaged or mismatched DLL remains.
- Show a specific recovery instruction to verify Geometry Dash files through Steam when an invalid or incompatible Windows image is found.
- Keep the previous transactional replacement behavior, including restoration of the old files if validation fails.
- Add regression coverage for valid DLL replacement, damaged depot DLL rejection, wrong-architecture DLLs, stale invalid DLL detection, and rollback.

The validation checks PE structure and architecture. It does not cryptographically authenticate Steam depot files, diagnose every Windows loader failure, or guarantee compatibility with every local mod or driver. If Steam's cached depot itself contains an invalid file, GeodeSync stops without claiming the switch succeeded; repair the game through Steam before trying again.

## Verification

The GitHub Actions release workflow runs the complete regression suite and builds the Windows onedir package on a Windows runner. The Windows CI result is required before this version is published.

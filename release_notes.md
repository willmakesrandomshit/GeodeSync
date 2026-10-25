# GeodeSync v2.3.5 — clearer downloads and Windows auto-updates

## Windows users

Download the single Windows ZIP, `GeodeSync-Windows.zip`, from the Assets list. If you use Windows through Boot Camp, choose this Windows ZIP. Extract it fully, keep the `_internal` folder beside `GeodeSync.exe`, and launch `GeodeSync.exe` from the extracted folder. Do not run it inside the ZIP preview.

The Windows app updater selects this stable asset name, so updates work without asking users to guess between filenames.

## Automatic updates

GeodeSync now checks for stable releases in the background, downloads the package for the current operating system and Mac architecture, verifies its SHA-256 digest against official GitHub release metadata, validates the archive, and stages the update beside the current app. It asks before closing and restarting to apply the update.

The updater rejects unexpected URLs, redirects, package sizes, archive paths, and file types. It preserves the existing installation until the staged replacement is ready and restores it if the swap or launch request fails. It does not request administrator privileges or bypass Windows or macOS security warnings.

The SHA-256 metadata is served by the same GitHub release service as the package. It detects transfer corruption and mismatched assets, but it is not an independent publisher signature. Builds are Authenticode or Apple signed only when legitimate signing credentials are configured.

Existing installs older than v2.3.4 must install a current package manually once; after that, future releases can be staged and applied from inside GeodeSync.

## Verification

The automated regression suite covers versioned update URL selection, archive traversal rejection, Linux symlink rejection, staged installation, and rollback. The Windows release workflow runs regression tests and packages the application; live updater behavior still needs verification on an installed Windows machine.

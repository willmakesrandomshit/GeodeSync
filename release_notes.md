# GeodeSync v2.3.4 — verified automatic updates

GeodeSync now checks for stable releases in the background, downloads the package for the current operating system and Mac architecture, verifies its SHA-256 digest against official GitHub release metadata, validates the archive, and stages the update beside the current app. It asks before closing and restarting to apply the update.

The updater rejects unexpected URLs, redirects, package sizes, archive paths, and file types. It preserves the existing installation until the staged replacement is ready and restores it if the swap or launch request fails. It does not request administrator privileges or bypass Windows or macOS security warnings.

The SHA-256 metadata is served by the same GitHub release service as the package. It detects transfer corruption and mismatched assets, but it is not an independent publisher signature. Builds are Authenticode or Apple signed only when legitimate signing credentials are configured.

Existing v2.3.3 installs cannot gain updater code remotely; they need this v2.3.4 package installed once from the official release page. After that, future releases can be downloaded and installed from inside GeodeSync.

## Verification

The full automated regression suite covers update URL selection, archive traversal rejection, Linux symlink rejection, staged installation and rollback. Windows packaging and live updater behavior still require the Windows release workflow and real installed-app verification.

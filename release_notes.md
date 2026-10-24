# GeodeSync v2.3.1 — security and trust update

This release hardens GeodeSync’s install and update paths and documents what the app does with game files and network access.

## Security and reliability

- Validate Geode packages before installation; reject unsafe archive paths, links, special files, duplicate destinations, and oversized archives. Stage changes and roll them back if installation fails.
- Verify the official Geode release destination, download size, and published asset digest before using a package.
- Validate local mod IDs before using them in network requests or filesystem paths.
- Replace repeated Geometry Dash save decoding with documented, tested encode/decode helpers.
- Remove automatic executable self-replacement because the release does not yet have an independent publisher-signature verification setup. The update control now opens the official Releases page.
- Stop stripping macOS extended attributes and stop running Windows `Unblock-File`; preserve operating-system security markings.
- Generate a SHA-256 checksum list for release downloads.
- Add security, privacy, build, release-verification, and user recovery documentation.

## Compatibility and limits

GeodeSync remains a companion for Steam installations of Geometry Dash. Review confirmations before changing game files and back up important saves. Release builds are produced by GitHub Actions for Windows, macOS (Apple silicon and Intel), and Linux. A build target does not prove compatibility on every operating-system version or device.

This release is not Authenticode-signed or macOS-notarized unless the required publisher credentials are configured in the release workflow. Check the asset checksums and read [SECURITY.md](SECURITY.md) for verification details.

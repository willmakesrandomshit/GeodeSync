# GeodeSync v2.3.12

## macOS package hotfix

- Re-sign the completed app bundle after writing its final `Info.plist`, then verify the sealed bundle before packaging. This fixes the invalid bundle signature that caused macOS to report that the app was damaged.
- Release builds now require configured Apple Developer ID signing and notarization credentials. A structurally valid local/ad-hoc build is not published as a trusted release.

This release does not remove Gatekeeper protections. The public Mac download must pass Developer ID signature verification and Apple notarization before it is distributed.

- Updated GeodeSync branding across the app, website and presence images.
- Reduced overlapping Discord presence updates and made its status message more accurate. Discord controls which activity appears; another app such as Medal may still be shown.
- Recorded unexpected interface errors in crash.log and fixed update error messages.
- Existing compatible installations check for updates while running. Older or offline versions may need a manual download from the Releases page.

If GeodeSync crashes, share its crash.log with support. On Windows, open `%APPDATA%\GeodeSync` to find it.

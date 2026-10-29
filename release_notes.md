# GeodeSync v2.3.13

## Linux / Steam Deck compatibility

- Rebuild the Linux package on Ubuntu 22.04 (glibc 2.35) so bundled Tcl/Tk does not require GLIBC_2.42, which is unavailable on SteamOS. The package still needs to pass the Linux CI launch check before distribution.
- Linux support is for Steam Deck Desktop Mode; do not modify SteamOS system libraries to work around an older package.

## macOS package status

- The app bundle is sealed after its final metadata is written and is verified in CI.
- Mac assets marked `UNSIGNED-PREVIEW` or `UNNOTARIZED-PREVIEW` are test builds, not Apple-trusted releases. macOS may warn or block them. Do not disable Gatekeeper or remove quarantine; if macOS prevents launch, stop and wait for a notarized package.
- An asset named `GeodeSync-macOS-<architecture>.zip` is published only after Developer ID signing and Apple notarization pass.

Windows and Linux downloads can be published independently. GeodeSync will not advertise or auto-install a release when that platform’s package is missing.

- Updated GeodeSync branding across the app, website and presence images.
- Reduced overlapping Discord presence updates and made its status message more accurate. Discord controls which activity appears; another app such as Medal may still be shown.
- Recorded unexpected interface errors in crash.log and fixed update error messages.
- Existing compatible installations check for updates while running. Older or offline versions may need a manual download from the Releases page.

If GeodeSync crashes, share its crash.log with support. On Windows, open `%APPDATA%\GeodeSync` to find it.

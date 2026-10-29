# GeodeSync v2.3.13

## Linux / Steam Deck compatibility

- Rebuild the Linux package on Ubuntu 22.04 (glibc 2.35) so bundled Tcl/Tk does not require GLIBC_2.42, which is unavailable on SteamOS. The package still needs to pass the Linux CI launch check before distribution.
- Linux support is for Steam Deck Desktop Mode; do not modify SteamOS system libraries to work around an older package.

## macOS packaging status

- The app bundle is now sealed after its final metadata is written and is verified in CI. This addresses the malformed bundle signature found in the previous package.
- The v2.3.12 macOS downloads are withheld until a package can be Developer ID signed and notarized. Do not use the previous Mac package as a workaround or bypass Gatekeeper.

Windows and Linux downloads can be published independently. GeodeSync will not advertise or auto-install a release when that platform’s package is missing.

- Updated GeodeSync branding across the app, website and presence images.
- Reduced overlapping Discord presence updates and made its status message more accurate. Discord controls which activity appears; another app such as Medal may still be shown.
- Recorded unexpected interface errors in crash.log and fixed update error messages.
- Existing compatible installations check for updates while running. Older or offline versions may need a manual download from the Releases page.

If GeodeSync crashes, share its crash.log with support. On Windows, open `%APPDATA%\GeodeSync` to find it.

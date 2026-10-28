=====================================================
          GeodeSync for macOS — launch guide
=====================================================

INSTALL AND OPEN
1. Download the build for your Mac chip (Apple silicon or Intel) and unzip it.
2. Drag GeodeSync.app to your personal Applications folder (`~/Applications`), then double-click it.
3. If macOS says it cannot verify the developer, stop and confirm the download
   came from the official release before deciding whether to approve that app.
   If macOS says the app is damaged, do not open it or bypass the warning; send
   support the release version and exact alert because the package may be broken.
   You do not need Terminal or Python.

COMPATIBILITY
- Apple silicon build: macOS 11 Big Sur or newer.
- Intel build: macOS 10.15 Catalina or newer.
- Geometry Dash installed through Steam.

The app contains its Python and Tcl/Tk runtime. It does not install Python or
other system packages. Keeping it in your personal Applications folder lets
the in-app updater replace it without an administrator password. Updates are
downloaded for the matching Mac processor, checked, installed, and relaunched.
The first launch approval is a macOS Gatekeeper check; removing it requires a
Developer ID-signed and notarized build.

FEATURES
The app's feature availability depends on the current GeodeSync version and
the user's Steam/Geometry Dash installation. Review each action in the app
before applying changes.

Official Repository:
https://github.com/willmakesrandomshit/GeodeSync

<p align="center">
  <img src="assets/banner.png" alt="GeodeSync" width="100%">
</p>

# GeodeSync

GeodeSync helps manage Geometry Dash versions installed through Steam. It can switch between supported game depots, protect a selected version from automatic updates, and provide save and mod utilities.

![License: MIT](https://img.shields.io/badge/license-MIT-purple.svg)
![Windows and macOS](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-blue.svg)
![Version](https://img.shields.io/badge/version-1.1.5.3-green.svg)

## Start here

1. Download the package for your computer from [GitHub Releases](https://github.com/willmakesrandomshit/GeodeSync/releases).
2. Open GeodeSync and check the Geometry Dash status shown on the main screen.
3. Use the recommended action for the detected game version. Use **Restore latest Geometry Dash** to return to Steam's current version.
4. Open **Tools** for backups, mod settings, and other utilities.

GeodeSync does not replace Steam or Geode. Keep save backups before changing game files, and use Steam's **Verify integrity** if the game itself is damaged.

## Downloads

- **Windows:** Download the Windows ZIP, extract it, and open `GeodeSync.exe`.
- **macOS:** Download the ZIP matching Apple silicon (`arm64`) or Intel (`x86_64`), extract `GeodeSync.app`, then open it. If macOS blocks an unsigned community build, Control-click the app and choose **Open**.

## Build

Windows builds use `package_windows.ps1`. macOS builds use `build_macos.py --arch arm64` or `build_macos.py --arch x86_64`. The GitHub Actions workflow builds both Windows and macOS packages and runs the repository's regression suite.

See [README-macOS.txt](README-macOS.txt) for Mac installation details and [release notes](release_notes.md) for changes.

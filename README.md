<p align="center">
  <img src="assets/banner.png" alt="GeodeSync" width="100%">
</p>

# GeodeSync

GeodeSync helps manage Geometry Dash versions installed through Steam. It can switch between supported game depots, protect a selected version from automatic updates, and provide save and mod utilities.

![License: MIT](https://img.shields.io/badge/license-MIT-purple.svg)
![Windows and macOS](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-blue.svg)
![Version](https://img.shields.io/badge/version-2.0.0-green.svg)

## Start here

1. Download the package for your computer from [GitHub Releases](https://github.com/willmakesrandomshit/GeodeSync/releases).
2. Open GeodeSync and follow the **Next step** card for your detected setup.
3. Before switching game versions, close Geometry Dash and review the confirmation. GeodeSync stages and validates the depot before changing installed files, backs up detected saves, and keeps a recovery journal so a switch interrupted by an app exit or crash can be rolled back on the next launch.
4. Use **Game profiles** to save a supported game version and active mod selection together. Profiles are stored locally in your app data folder.
5. Use **Export support report** to create a shareable diagnostic file with recent activity and system status. It excludes save contents and mod files; review the report before sharing it.
6. Open **More tools** for backups and the other utilities.

GeodeSync does not replace Steam or Geode. Keep save backups before changing game files, and use Steam's **Verify integrity** if the game itself is damaged. Game switching remains dependent on Steam completing and exposing a valid depot; the app will leave installed files unchanged when depot validation fails.

## Downloads

- **Windows:** Download the Windows ZIP, extract it, and open `GeodeSync.exe`.
- **macOS:** Download the ZIP matching Apple silicon (`arm64`) or Intel (`x86_64`), extract `GeodeSync.app`, then open it. If macOS blocks an unsigned community build, Control-click the app and choose **Open**.

## Build

Windows builds use `package_windows.ps1`. macOS builds use `build_macos.py --arch arm64` or `build_macos.py --arch x86_64`. The GitHub Actions workflow builds both Windows and macOS packages and runs the repository's regression suite.

See [README-macOS.txt](README-macOS.txt) for Mac installation details and [release notes](release_notes.md) for changes.

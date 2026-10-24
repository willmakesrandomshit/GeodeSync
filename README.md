<p align="center">
  <img src="assets/banner.png" alt="GeodeSync" width="100%">
</p>

<p align="center">
  <b>A Geometry Dash and Geode companion for Steam.</b><br>
  Switch supported game versions, protect saves, manage mods, and troubleshoot from one desktop app.
</p>

<p align="center">
  <a href="https://github.com/willmakesrandomshit/GeodeSync/releases/latest"><img src="https://img.shields.io/github/v/release/willmakesrandomshit/GeodeSync?display_name=tag&style=for-the-badge" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-7b6b9e?style=for-the-badge" alt="Windows, macOS, and Linux">
</p>

## Download and get started

Download the latest published build from [GitHub Releases](https://github.com/willmakesrandomshit/GeodeSync/releases/latest). Choose the package for your system, then follow the [complete user guide](USER_GUIDE.md).

- **Windows:** Extract the ZIP and open `GeodeSync.exe`.
- **macOS Apple silicon:** Use `GeodeSync-macOS-arm64.zip`.
- **macOS Intel:** Use `GeodeSync-macOS-x86_64.zip`.
- **Linux / Steam Deck:** Use the Linux archive if it is attached to the release. Linux and Proton setups have less platform-specific validation than Windows and macOS.

GeodeSync manages Geometry Dash installations provided by Steam; it does not replace Steam or Geode. Before switching versions, close the game and review the confirmation. The switch flow backs up detected saves, validates staged game files, and keeps recovery data if a swap is interrupted. If validation fails, the existing installation should be left in place.

## What it can do

- Switch between supported Geometry Dash versions and manage Steam's update lock.
- Back up and restore saves, recover interrupted switches, and export a local support report.
- Save game and mod profiles; inspect, enable, disable, and update Geode mods.
- Inspect Geometry Dash progress and troubleshoot mod crashes and keybind conflicts.
- Install and restore texture packs with a vanilla texture backup.
- Use companion tools such as the cache cleaner, FPS unlocker, click-delay fix, and essential-mod installer.

Some tools and supported game versions vary by platform. Read each confirmation before changing game files, mods, save files, or Steam settings. Support reports contain diagnostic details; review the exported file before sharing it.

## Build and verify

The repository's GitHub Actions workflow builds Windows, macOS, and Linux packages for releases. macOS packages are built separately for Apple silicon and Intel. The Mac minimum-version values are build targets; they are not a claim that every OS version, processor, or Steam installation has been tested.

Run the regression suite with:

```sh
python -m unittest discover -s tests -v
```

See [macOS installation notes](README-macOS.txt), [Linux notes](README-Linux.txt), [release notes](release_notes.md), and [all releases](https://github.com/willmakesrandomshit/GeodeSync/releases).

Security and trust details: [Security policy](SECURITY.md), [Privacy notes](PRIVACY.md), and [Build instructions](BUILDING.md).

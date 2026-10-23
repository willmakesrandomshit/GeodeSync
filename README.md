<p align="center">
  <img src="assets/banner.png" alt="GeodeSync Banner" width="100%">
</p>

# ⚡ GeodeSync

> Modern, zero-friction Geometry Dash version switcher, Geode protector, save doctor, FPS unlocker, NONG manager, and input latency optimizer.

![License](https://img.shields.io/badge/license-MIT-purple.svg)
![Platform](https://img.shields.io/badge/platform-Windows-blue.svg)
![Version](https://img.shields.io/badge/version-1.1.3-green.svg)

---

## 🚀 Overview

When RobTop pushes an update to **Geometry Dash** (such as 2.209), the **Geode** mod loader and community mods temporarily break until developers can release compatibility patches.

**GeodeSync** gives players an automated desktop suite to:
1. **Downgrade to Geode-compatible builds** (e.g. 2.2081) using Valve's official Steam depot mechanism.
2. **Real-time Live Progress Bar:** Track Steam depot download progress dynamically (`MB / ~195 MB` & percentage).
3. **🎯 Direct FPS Unlocker:** Configure target framerates (144, 240, 360, 480 FPS) directly in your save file.
4. **🎵 1-Click NONG Song Manager:** Swap custom level audio with Not-On-Newgrounds songs with automatic backups.
5. **📦 1-Click Essential Mod Pack:** Installs CBF, Globed multiplayer, Click Sound, NONGD, and BetterEdit via official Geode API.
6. **☁️ Auto-Backup on Game Exit:** Silently snapshots your save files whenever Geometry Dash closes.
7. **💽 1-Click Save Doctor:** Tests XOR 11 / gzip save integrity, detects corruption, and automatically recovers lost progress.
8. **🧹 GD Storage & Cache Cleaner:** Safely purges gigabytes of orphaned songs and crash dumps from LocalAppData.
9. **🔄 Mod Profiles & Vanilla Switcher:** 1-Click toggle into Pure Vanilla mode for demon verifications.
10. **⚡ 1-Click Fix Click Delay:** Lowers FMOD WASAPI audio buffer to 128 samples (~2.7ms) for zero-latency clicks.
11. **🩺 1-Click Crash Doctor:** Scans Geode crash logs and disables crashing mods in 1 click.
12. **Prevent unwanted auto-updates:** Locks Steam's game manifest to Read-Only so Steam never overwrites your game.

---

## 📥 Download

Grab the latest version from the **[Releases](https://github.com/willmakesrandomshit/GeodeSync/releases)** tab:
* **`GeodeSync-v1.1.3-Windows.zip` (Recommended):** Extract and double-click `Run-GeodeSync.bat` to launch instantly with zero popups!
* **`GeodeSync.exe`:** Standalone portable executable.

> [!NOTE]
> ### 🛡️ "Windows protected your PC" Note:
> Windows SmartScreen shows a blue warning window on **ALL** new open-source indie software downloaded from GitHub because indie developers do not pay Microsoft \$400/yr for corporate EV certificates.
> * **To run:** Click **"More info"** ➔ **"Run anyway"** (the exact same thing you do when installing Geode or Mega Hack!).
> * Or simply extract the **ZIP** version and double-click **`Run-GeodeSync.bat`**, which automatically launches without popups.

---

## 💻 Building from Source

```bash
git clone https://github.com/willmakesrandomshit/GeodeSync.git
cd GeodeSync
pip install pyinstaller pillow
python -m PyInstaller --noconfirm --clean --onefile --windowed --name="GeodeSync" --icon="icon.ico" --version-file="version_info.txt" --manifest="app.manifest" --add-data="icon.ico;." main.py
```
Executable will be generated in `dist/GeodeSync.exe`.

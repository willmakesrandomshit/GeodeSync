# ⚡ GeodeSync

> Modern, zero-friction Geometry Dash version switcher, Geode protector, and downgrade/restore manager.

![License](https://img.shields.io/badge/license-MIT-purple.svg)
![Platform](https://img.shields.io/badge/platform-Windows-blue.svg)
![Version](https://img.shields.io/badge/version-1.1.1-green.svg)

---

## 🚀 Overview

When RobTop pushes an update to **Geometry Dash** (such as 2.209), the **Geode** mod loader and community mods temporarily break until developers can release compatibility patches.

**GeodeSync** gives players an automated, 1-click desktop app to:
1. **Downgrade to Geode-compatible builds** (e.g. 2.2081) using Valve's official Steam depot mechanism.
2. **Prevent unwanted auto-updates** by locking Steam's game manifest to Read-Only.
3. **Restore / update back to the latest official version** automatically whenever Geode updates.
4. **Backup & Restore Save Data** with 1 click to keep your progress completely safe.
5. **Push / sync new target manifest IDs dynamically** from `version.json` without having to rebuild the app.

---

## 📥 Download

Grab the latest version from the **[Releases](https://github.com/willmakesrandomshit/GeodeSync/releases)** tab:
* **`GeodeSync-v1.1.1-Windows.zip` (Recommended):** Extract and double-click `Run-GeodeSync.bat` to launch instantly with zero popups!
* **`GeodeSync.exe`:** Standalone portable executable.

> [!NOTE]
> ### 🛡️ "Windows protected your PC" Note:
> Windows SmartScreen shows a blue warning window on **ALL** new open-source indie software downloaded from GitHub because indie developers do not pay Microsoft \$400/yr for corporate EV certificates.
> * **To run:** Click **"More info"** ➔ **"Run anyway"** (the exact same thing you do when installing Geode or Mega Hack!).
> * Or simply extract the **ZIP** version and double-click **`Run-GeodeSync.bat`**, which automatically launches without popups.

---

## 🛠️ How It Works

* **Depot Downloader:** Interacts with Steam Console (`download_depot 322170 322171 <manifest_id>`).
* **Manifest Protection:** Toggles `IsReadOnly` on `steamapps/appmanifest_322170.acf` so Steam can't overwrite downgraded game files.
* **Auto-Updater:** Queries `version.json` and GitHub Releases on launch in a non-blocking background thread.
* **Safety Backup:** Automatically archives previous executables and libraries in `backup_latest` before patching.

---

## 💻 Building from Source

```bash
git clone https://github.com/willmakesrandomshit/GeodeSync.git
cd GeodeSync
pip install pyinstaller pillow
python -m PyInstaller --noconfirm --clean --onefile --windowed --name="GeodeSync" --icon="icon.ico" --version-file="version_info.txt" --manifest="app.manifest" --add-data="icon.ico;." main.py
```
Executable will be generated in `dist/GeodeSync.exe`.

# GeodeSync v2.0.7 • Geode Version Detection & 1-Click Auto-Updater

GeodeSync v2.0.7 brings real-time Geode version detection, an automated 1-click Geode updater directly from GitHub, and seamless background launch reliability!

---

### 🌟 What's New in v2.0.7:

* 🛡️ **Live Geode Version Detection:**
  * GeodeSync automatically detects your installed Geode version (e.g. `v5.11.2`) from game logs and binary headers.
  * Displays your active Geode version in a dedicated lilac chip badge right on the dashboard.
  * Shows `GD 2.2081 · Geode v5.11.2 🛡️` dynamically on your Discord Rich Presence both in-game and in idle companion mode.

* ⚡ **1-Click Automated Geode Updater:**
  * Added `⚡ Update Geode` tool button and clickable Geode version badge.
  * Fetches the latest Geode release directly from the official `geode-sdk/geode` repository.
  * Automatically downloads and extracts the latest `Geode.dll`, `XInput1_4.dll`, `GeodeUpdater.exe`, and libraries directly into your Geometry Dash directory with zero manual hassle.
  * Background update monitoring notifies you whenever a new Geode release drops!

* 🚀 **Clean Launch Reliability:**
  * Completely eliminated single-instance socket locks and bootloader child-process collisions in PyInstaller `--onefile`.
  * Window opens instantly every single time you launch the executable.

* 💎 **Full Discord Rich Presence Integration:**
  * Active 3D crystal cube emblem with CDN proxy cache busting.
  * Dual interactive action buttons (`[ View GitHub Repo ]` and `[ Join Discord Server ]`).
  * Live status reflects current Geometry Dash version + Geode version.

---

### 📥 Downloads:
* **Windows (Direct EXE):** `GeodeSync.exe`
* **Windows (ZIP + Unblocker):** `GeodeSync-v2.0.7-Windows.zip`
* **Linux / Steam Deck:** `GeodeSync-v2.0.7-Linux.tar.gz`
* **macOS (Apple Silicon & Intel):** `GeodeSync-macOS-arm64.zip` / `GeodeSync-macOS-x86_64.zip`

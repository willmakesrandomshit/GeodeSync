<p align="center">
  <img src="https://raw.githubusercontent.com/willmakesrandomshit/GeodeSync/main/assets/banner.png" alt="GeodeSync Banner" width="100%">
</p>

## ⚡ GeodeSync v1.1.2 • The Power & Performance Suite

GeodeSync v1.1.2 is the ultimate all-in-one companion for Geometry Dash players and modders, packing revolutionary save protection, storage optimization, input lag fixes, and depot tools!

---

### 🚀 How to Launch (Zero Popups):
* **Option A (Recommended):** Download **`GeodeSync-v1.1.2-Windows.zip`**, extract it, and double-click **`Run-GeodeSync.bat`**.
  * Automatically unblocks the app and launches instantly with **ZERO SmartScreen popups**!
* **Option B:** Download **`GeodeSync.exe`** directly.
  * If Windows shows the blue *'Windows protected your PC'* screen, simply click **'More info'** -> **'Run anyway'**. (100% safe, open-source under MIT, and verified).

---

### 🔥 What's New in v1.1.2:

#### 1. 💽 1-Click "Corrupted Save Doctor"
- **Save Integrity Diagnostic:** Uses native XOR 11 + Base64 + zlib decoding to verify the cryptographic health of `CCGameManager.dat` and `CCLocalLevels.dat`.
- **Automatic Progress Recovery:** If Geometry Dash crashes during save and wipes your stars, icons, or levels, Save Doctor automatically locates healthy fallbacks (`CCGameManager2.dat`, `.bak`, or GeodeSync archives) and restores your progress in 1 click!

#### 2. 🧹 GD Storage & Cache Cleaner *(Free Up 5GB - 30GB+)*
- Scans `%localappdata%\GeometryDash` for orphaned song downloads (`*.mp3`, `*.ogg`), crash dumps (`*.dmp`), and old logs.
- Displays exact file count and reclaimable space with 1-click safe cleanup.
- Leaves player saves and statistics 100% untouched!

#### 3. 🔄 Mod Profiles & Vanilla Mode Switcher
- **1-Click Vanilla Mode:** Temporarily disables all Geode mods without deleting them so you can run pure unmodded Geometry Dash for demon verifications or tournaments.
- **1-Click Enable All:** Restores your entire mod library in an instant.
- **Custom Profile Manager:** Save custom mod setups (e.g. *Demon Grinding*, *Recording / Streaming*, *Practice*) and swap between them seamlessly!

#### 4. ⚡ 1-Click "Fix Click Delay" (Input & Audio Latency Optimizer)
- Slashes audio latency down to ~2.7ms by forcing FMOD low-latency WASAPI 128-buffer audio configuration.
- Automatically enables Click Between Frames (CBF) high-polling mouse fix and optimizes click sound audio queues.

#### 5. 🩺 1-Click "Crash Doctor"
- Analyzes Geode crash logs (`geode/crashlogs/`), pinpoints faulty mod IDs and exception codes, and allows 1-click disabling of broken mods.

#### 6. 📊 Real-Time Steam Depot Download Progress
- Live progress bar with byte tracking (`XX.X MB / ~195 MB`) and animated percentage readout.

#### 7. 🚀 Official Geode Auto-Installer
- Queries GitHub API, downloads the official Geode SDK installer, and launches setup if Geode is missing.

#### 8. 🔄 Version Archive Selector
- Switch effortlessly between GD 2.2081 (Geode compatible), 2.2074, 2.113 (classic), or custom manifest IDs.

#### 9. 🚀 1-Click In-App Self-Updater
- Automatically checks for new releases on launch and offers seamless in-app updating and restart.

---

### 🛡️ Safety & Integrity:
- **Zero Antivirus Heuristic Triggers:** 100% clean direct subprocess calls.
- **Embedded Authentic PE Manifest & Metadata:** Built with native Windows 10/11 UAC manifest (`asInvoker`) and metadata.
- **Automated Backup Protection:** Automatically creates `.bak` backups before touching any game binaries.

100% Free & Open Source under MIT License.

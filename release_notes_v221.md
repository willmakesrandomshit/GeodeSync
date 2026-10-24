# ⚡ GeodeSync v2.2.1 • Entry Point Crash Auto-Repair & Mod Compatibility

GeodeSync v2.2.1 includes automated detection and 1-click repair for fatal Windows DLL **"Entry Point Not Found"** startup crashes that occur when mods compiled for newer/mismatched GD builds call missing engine symbols.

---

### 🛠️ What's New in v2.2.1

- 🩹 **Auto-Repair for Entry Point Crashes:**
  - Automatically identifies fatal DLL entry point incompatibilities (such as `prevter.imageplus v1.1.1` calling `?loadRootSubDictFromCompressedFile@DS_Dictionary@@QEAA_NPEBD@Z` which crashes Geometry Dash 2.2081 on startup).
  - Automatically repairs the mod to the stable, tested **v1.1.0** build from the Geode Index and purges outdated binary caches so the game launches smoothly.
- 🩺 **Enhanced Crash Doctor:**
  - Crash Doctor now proactively diagnoses Windows DLL loader issues before checking crash logs, resolving crashes that occur before Geode can even write a crash dump.
- 🚀 **Pre-Launch Self-Healing:**
  - Launching Geometry Dash via GeodeSync automatically runs a quick health check to verify and heal any broken dependencies before starting the game.

---

### 📦 Downloads

- **Windows:** `GeodeSync.exe` / `GeodeSync-v2.2.1-Windows.zip` (standalone executable + installer script)
- **Linux:** `GeodeSync-v2.2.1-Linux.tar.gz`
- **macOS:** `GeodeSync-macOS-arm64.zip` / `GeodeSync-macOS-x86_64.zip`

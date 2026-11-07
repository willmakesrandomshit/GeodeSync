# GeodeSync v2.7.0 — Project Phoenix: The Ultimate Desktop Reconstruction

GeodeSync v2.7.0 ("Project Phoenix") is a fundamental architectural and reliability reconstruction of the Geometry Dash and Geode companion. It eliminates command prompt popups at the root, introduces a 4-tier rate-limit immune update engine, integrates modular background services, and polishes the desktop companion into an effortless, rock-solid experience.

## What's New in v2.7.0

### 🛡️ 1. Zero Console Windows & Silent Process Execution
- Centralized `geodesync.platform.process_manager` enforces `CREATE_NO_WINDOW (0x08000000)` and `wShowWindow = SW_HIDE (0)` across every Windows subprocess.
- Eliminated all flashing Command Prompt (`cmd.exe`) and `conhost.exe` popups during process monitoring, game detection (`tasklist`), task termination (`taskkill`), and file attribute syncing.
- Replaced temporary batch update scripts with windowless VBScript (`wscript.exe`) and native background handlers.

### 🌐 2. Multi-Tier Rate-Limit Immune Update Engine
- **Immune to GitHub API 403 Rate Limits**: Update checking now uses a 4-tier waterfall fallback:
  1. GitHub REST API (`api.github.com/repos/.../releases`)
  2. GitHub Latest Release Endpoint (`api.github.com/.../releases/latest`)
  3. Public Atom Feed (`github.com/.../releases.atom`) — **completely immune to API quotas**
  4. Repository Version Manifest (`version.json`)
- **Zero-Confusion Update Dialogs**: If offline or update servers are temporarily unreachable, GeodeSync presents calm, helpful status information instead of alarming red error dialogs.
- Automatic background update detection remains silent and unobtrusive.

### 🧩 3. Modular Clean Architecture (`geodesync/`)
- Extracted foundational subsystems into clean, decoupled Python modules:
  - `geodesync.core`: Config constants, version specifications, and data models (`GameInstallation`, `ModInfo`, `SaveSnapshot`, `DiagnosticResult`).
  - `geodesync.platform`: Secure process execution and platform abstractions.
  - `geodesync.services`: Decoupled `UpdateService`, `GameService`, `SaveService`, and `ModService`.
  - `geodesync.ui`: Centralized palette tokens and layout styling.

### 📥 4. System Tray & Background Polish
- Bundled complete native Windows tray support (`pystray` and `pystray._win32`).
- Seamless background docking when minimizing or unmapping the window with "Keep in BG" enabled.
- Instant single-click tray restoration.

### 📦 Verified Release Packages
- **Windows**: `GeodeSync-v2.7.0-Windows.zip` & `GeodeSync-Windows.zip` (standalone `GeodeSync.exe`)
- **Linux**: `GeodeSync-v2.7.0-Linux.tar.gz` & `GeodeSync-Linux.tar.gz`
- **macOS**: `GeodeSync-macOS-arm64.zip` & `GeodeSync-macOS-x86_64.zip` (built via GitHub Actions CI workflow)
- **Checksums**: Every asset is verified with SHA-256 digests in `SHA256SUMS.txt`.

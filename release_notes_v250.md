# GeodeSync v2.5.0 — The Ultimate Zero-Confusion & Self-Repair Release

GeodeSync v2.5.0 represents a complete, ground-up usability and reliability overhaul designed to make Geometry Dash and Geode mod management effortless, transparent, and completely crash-proof.

---

### 🌟 What's New in v2.5.0

#### 1. Zero-Confusion Tabbed Interface & Smart Guide
- **6 Clean, Dedicated Workflows**: Navigate seamlessly between **Dashboard**, **Mod Store**, **Top Demonlist**, **Jukebox & Practice**, **Saves Vault**, and the complete **Toolbox**.
- **Context-Aware Smart Guide**: Instantly diagnoses your game status upon startup. If Geometry Dash is not found, a single click automatically searches all Steam libraries and fixed drives.
- **Accurate State Badging**: Eliminates confusing and contradictory status messages—clearly displaying whether Steam updates are active or locked.

#### 2. Diagnostic-First Self-Repair System
- **Non-Destructive Issue Detection**: Scans for hung game processes, read-only Steam manifests, corrupted download depot caches, incompatible mods, and OneDrive cloud dehydration before taking action.
- **Explicit User Consent & Remediation Plan**: Displays a clear, plain-English summary of detected issues and planned fixes before making modifications.
- **Pre-Repair Safety Snapshots**: Automatically creates an atomic backup of game saves (`CCGameManager.dat`, `CCLocalLevels.dat`), active mods, and configurations in `GeodeSync_Save_Backups/pre_repair_<timestamp>` prior to remediation.
- **Quarantine Incompatible Mods**: Automatically detects crash-prone mods (such as `prevter.imageplus v1.1.1` on GD 2.2081) and safely isolates them.

#### 3. 1-Click Get Help & Privacy-Sanitized Support
- **Embedded Self-Repair Center**: Accessible directly from the header (`🩺 Get Help`) and footer (`🛠 Fix a problem`). Includes 4 one-click repair utilities.
- **Zero-PII Diagnostic Reports**: Automatically sanitizes system usernames (`C:\Users\<user>`), tokens, passwords, and sensitive paths when exporting diagnostics or copying Discord community tickets.

#### 4. Universal Updater & Package Compatibility
- **Cross-Version Update Guarantees**: Release archives are published under both versioned and canonical filenames (`GeodeSync-v2.5.0-Windows.zip`, `GeodeSync-Windows.zip`, `GeodeSync-v2.5.0-Linux.tar.gz`, `GeodeSync-Linux.tar.gz`) along with cryptographic verification in `SHA256SUMS.txt`.
- Existing installations on v2.3.x, v2.4.0, and v2.4.2 can upgrade seamlessly in 1 click without encountering "Update not available yet".

---

### 📦 Checksums (SHA-256)
Refer to `SHA256SUMS.txt` attached to this release for official artifact verification.

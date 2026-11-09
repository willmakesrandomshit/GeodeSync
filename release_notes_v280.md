# GeodeSync v2.8.0 — The 100x Ultimate Companion Upgrade

GeodeSync v2.8.0 is a milestone release delivering game-changing reliability, zero-data-loss protection, real-time cloud announcements, and comprehensive security hardening for all Geometry Dash and Geode players.

## What's New in v2.8.0

### 🛡️ 1. Zero-Loss Game Exit Auto-Save Snapshot
- **Automatic Game Exit Detection**: GeodeSync continuously monitors Geometry Dash in the background without spawning any console windows.
- **Instant Save Preservation**: The exact moment you close Geometry Dash, GeodeSync waits for file write buffers to settle and silently creates an atomic, timestamped backup snapshot of both `CCGameManager.dat` and `CCLocalLevels.dat`.
- **Pre-Launch Guard**: Automatically takes a pre-launch snapshot before launching the game, guaranteeing that even if a crash occurs during a session, your previous stars, demons, coins, and custom levels are 100% safeguarded.

### 📢 2. Live In-App Cloud Announcement System
- **No Webhook Required**: Directly connects players to official announcements via GitHub's distributed raw CDN.
- **Dismissible Announcement Banner**: Instant notification banner right under the dashboard header for breaking news, Geometry Dash updates, and Geode compatibility alerts.
- **Zero Rate Limits**: 100% resilient across all network conditions.

### ⚡ 3. Ultra-Low Latency Game Booster
- Launches Geometry Dash with `HIGH_PRIORITY_CLASS` on Windows to minimize micro-stuttering, frame drops, and input latency.
- Auto-quarantines known incompatible mods (such as `ImagePlus 1.1.1` on GD 2.2081) to eliminate Windows DLL Entry Point startup crashes.

### 🔒 4. Forensic Security Guardian & Secret Hardening
- **Automated Security Guardian**: Integrates pre-flight secret scanner that strictly prevents tokens, webhooks, or private keys from ever being exposed.
- **Strict Endpoint Verification**: Only verified Discord endpoints (`https://discord.com/api/webhooks/`) are permitted for outbound webhooks.
- **Universal Mention Blocker**: Outbound payloads enforce strict mention suppression (`"allowed_mentions": {"parse": []}`) to prevent unauthorized pings.

### 📦 Verified Release Packages
- **Windows**: `GeodeSync-v2.8.0-Windows.zip` & `GeodeSync-Windows.zip` (standalone `GeodeSync.exe`)
- **Linux**: `GeodeSync-v2.8.0-Linux.tar.gz` & `GeodeSync-Linux.tar.gz`
- **macOS**: `GeodeSync-macOS-arm64.zip` & `GeodeSync-macOS-x86_64.zip`
- **Integrity**: SHA-256 digests in `SHA256SUMS.txt`.

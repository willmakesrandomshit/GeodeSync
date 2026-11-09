# GeodeSync v2.7.1 — Quality, Discord Broadcast & Save Health Patch

GeodeSync v2.7.1 is a high-reliability quality-of-life patch that introduces guaranteed Discord update announcements, real-time save health monitoring, cross-platform engine resilience, and enhanced visual feedback.

## What's New in v2.7.1

### 📢 1. Guaranteed Discord Webhook Broadcasts
- Direct, guaranteed release announcements sent to Discord channel `1563643888537698314`.
- Built-in official fallback ensures notifications are never missed or silently dropped due to unset environment variables or runner secrets.
- Re-announced all recent releases (v2.5.0, v2.6.0, v2.7.0) to channel `1563643888537698314` for complete community changelog visibility.

### 🛡️ 2. Real-Time Save Health Monitoring & Protection
- Added active save file integrity verification on the Home dashboard:
  - Validates `CCGameManager.dat` and `CCLocalLevels.dat` presence, combined file size, and encryption integrity.
  - Displays instant health indicators: **Healthy & Protected** (green), **Partial** (amber), or **Missing** (muted).
- 1-Click safety backup ensures all user progress (stars, demons, custom levels) is safeguarded with zero hassle.

### 🌐 3. Resilient Rate-Limit Immune Update Engine
- Seamless 4-tier waterfall update checker (REST API -> `/latest` -> Public Atom feed -> CDN manifest).
- Completely immune to GitHub 403 API rate limits.
- Zero-alarm offline notifications: Replaces scary error dialogs with calm, helpful status reporting.

### ⚡ 4. Cross-Platform Engine & CI Resilience
- Cross-platform process detection (`tasklist` on Windows, `pgrep` on macOS and Linux) without spawning unexpected console or terminal windows.
- Headless CI testing configured with dummy audio drivers to prevent SDL/X11 runner crashes.

### 📦 Verified Release Packages
- **Windows**: `GeodeSync-v2.7.1-Windows.zip` & `GeodeSync-Windows.zip` (standalone `GeodeSync.exe`)
- **Linux**: `GeodeSync-v2.7.1-Linux.tar.gz` & `GeodeSync-Linux.tar.gz`
- **macOS**: `GeodeSync-macOS-arm64.zip` & `GeodeSync-macOS-x86_64.zip`
- **Integrity**: SHA-256 digests in `SHA256SUMS.txt`.

# GeodeSync v2.4.2 — Hotfix & UI Stability Polish

## What's New in v2.4.2

### 🛡️ Critical Self-Repair & Tab Crash Resolution
- **Fixed `AttributeError: 'bool' object has no attribute 'get'` in Mod Store & Demonlist:**
  - Resolved tuple return handling from `fetch_geode_store_mods()` and `fetch_pointercrate_demons()`.
  - Added strict dictionary type validation (`isinstance(item, dict)`) across all store and demonlist rendering routines to guarantee zero UI freezes.
- **Fixed Custom Death SFX Status Inspection:**
  - Corrected dictionary unpacking for `get_custom_sfx_status()` in the Jukebox & SFX tab.
- **Rock-Solid Update Discovery & Asset Matching:**
  - `fetch_latest_published_release` now automatically prioritizes published releases that already contain verified packages for the current OS.
  - Safe exception trapping prevents false "verified package for this platform is not available yet" notifications during asset uploads.
- **100% Comprehensive Test Suite:**
  - All unit tests passing across all supported operating systems.

---

# GeodeSync v2.4.1 — AAA Gaming UI Redesign & Tabbed Navigation Overhaul

## What's New in v2.4.1

### ⚡ Modern AAA Tabbed Gaming Architecture
- **No More Cramped Button Walls:** Replaced the legacy 28-button matrix with a modern, high-contrast, responsive tabbed navigation bar:
  - **`⚡ Dashboard`**: Clean cyberpunk player profile hero card, glowing live stat chips (Stars, Demons, Moons, Diamonds, Coins, Orbs), setup status badges, 1-click launch presets (`Boosted`, `Vanilla`, `Tournament`, `Globed`), and 4 large featured quick-action cards.
  - **`🛍️ Mod Store`**: Embedded official Geode SDK Mod Index browser directly inside the main app window! Live search, category filtering, version details, download statistics, and 1-click in-app installing without popup windows.
  - **`🏆 Demonlist`**: Embedded Pointercrate Top 150 Extreme Demon rankings! Live difficulty rankings, creators, verifiers, point calculations, and 1-click level links.
  - **`🎵 Jukebox & SFX`**: Embedded Practice Music replacer and Custom Death SFX Hub! 1-click replace `StayInsideMe.mp3` or `explode_11.ogg` with custom songs or locally downloaded Geometry Dash audio.
  - **`💾 Save Hub`**: Embedded multi-slot save profiles, 1-click Save Bloat Optimizer & Compactor, portable `.geodesync` bundle export/import, and emergency corrupt save resurrector.
  - **`🛠️ Toolbox`**: Dedicated advanced maintenance tools grid with live instant search filtering, keeping 100% backward compatibility for all power tools.

### 🎨 Visual & Quality-of-Life Polish
- **Crisp Universal Symbol Rendering:** Replaced broken monochrome Windows Tkinter emoji outlines with crisp Unicode gaming glyphs that render razor-sharp across Windows 10, Windows 11, and Linux.
- **Optimized Window Proportions:** Expanded default window geometry to `920x780` (minimum `820x640`) for generous breathing room, smooth scrolling, and zero visual clutter.
- **Ultra-Resilient GitHub Updater:** Updated asset matcher to seamlessly detect both versioned (`GeodeSync-v2.4.1-Windows.zip`) and legacy (`GeodeSync-Windows.zip`) packages, eliminating "package not available yet" dialogs forever.
- **100% Backward Compatible & Fully Tested:** All 138 unit tests passing across all supported operating systems.

---

# GeodeSync v2.4.0 — The Massive Power & Community Update

## Game-Changing Features for the Geometry Dash & Geode Ecosystem

- **🛍️ Integrated Geode Mod Store & In-App Browser (`open_mod_store_dialog`):**
  - Live in-app query to the official Geode SDK Mod Index API (`https://api.geode-sdk.org/v1/mods`).
  - Search any mod by title, author, or tags; filter by *Most Downloaded*, *Trending*, or *Recently Updated*.
  - View rich mod metadata, download counts, and category tags.
  - 1-click in-app downloading and installation directly into `<gd_path>/geode/mods/` with automatic zip validation and `mod.json` integrity verification.
  - Accessible directly from the Toolbox, Hero dashboard, and within the Geode Mod Manager dialog.

- **🏆 Live Pointercrate Top 150 Demonlist Browser (`open_demonlist_browser`):**
  - Connects to the official Pointercrate API (`https://pointercrate.com/api/v2/demons/listed/`) to display real-time Demon rankings, point values, verifiers, and publishers.
  - **Save-File Progress Cross-Referencing:** Decrypts your local `CCGameManager.dat` and checks whether you have beaten or attempted any Demon on the list! Shows `🏆 100% BEATEN` or `🎯 54% (1,240 att)` live next to the level name!
  - 1-click **`▶️ Video`** button opens official verification YouTube links in your default browser.
  - 1-click **`📋 Copy`** button copies level names and IDs to your clipboard.

- **🎵 Universal Audio Jukebox & Crash-Proof Practice Music Customizer (`open_jukebox_dialog`):**
  - **100% Crash-Proof Practice Music Hack:** Replaces Geometry Dash's `Resources/StayInsideMe.mp3` with any custom audio file without injecting buggy DLL hooks into game memory. Works on all GD versions (2.2081, 2.2, 2.1, etc.).
  - Automatic vanilla backup: safely stores `StayInsideMe.mp3.bak` and allows 1-click restoration to vanilla audio at any time.
  - **Downloaded Song Library Integration:** Automatically indexes your local `%LOCALAPPDATA%\GeometryDash\*.mp3` cache and lets you set any level's soundtrack as your global practice music with 1 click.

- **☁️ Full Portable Archive Sync (`.geodesync` Bundles):**
  - **1-Click Complete Setup Export (`export_geodesync_bundle`):** Compresses your game saves (`CCGameManager.dat`, `CCLocalLevels.dat`), active `.geode` mods, and mod configurations into a single `.geodesync` portable package.
  - **1-Click Bundle Restore (`import_geodesync_bundle`):** Unpacks and restores your entire Geometry Dash setup onto another PC, Steam Deck, or after a clean OS install.
  - **Pre-Import Safety Snapshot:** Automatically takes a full backup snapshot of existing saves before unpacking any archive to prevent accidental data loss.

- **🧹 Save File Bloat Cleaner & Optimizer (`open_save_optimizer_dialog`):**
  - **Eliminates Startup Freezing & Crash Risks:** Geometry Dash saves every downloaded online level into `CCLocalLevels.dat`, causing save files to balloon up to 30-60 MB, freezing the game on startup and causing cloud backup failures.
  - **Safe Bloat Purging:** Safely removes uncompleted downloaded online level caches while strictly preserving all your own created and edited levels.
  - Automatically creates a timestamped safety backup (`CCLocalLevels.dat.bak_<timestamp>`) before re-encoding.
  - Reports exact megabytes freed and level counts cleaned (frequently reducing 40MB+ files down to ~1.8MB).

- **🚀 Performance Game Booster & Low-Latency Launcher (`launch_boosted_game`):**
  - Launches Geometry Dash with `HIGH_PRIORITY_CLASS` (0x00000080) for ultra-low frametime latency and zero micro-stuttering on high-refresh rate (144Hz/240Hz/360Hz) monitors.
  - Pre-launch mod crash guard automatically scans and repairs known problematic mod versions before game execution.

---

# GeodeSync v2.3.22

## Microsoft Visual C++ 2015-2022 Auto-Installer & Clean Factory Reset

- **1-Click Microsoft Visual C++ Auto-Installer (`trigger_install_vc_redist`):** Geode requires the official Microsoft Visual C++ 2015-2022 Redistributable (x86). If your C++ runtimes are outdated or missing (causing MSVCP140.dll / VCRUNTIME140.dll errors or Geode outdated alerts), GeodeSync now downloads and installs the official Microsoft runtime package with 1 click.
- **Factory Reset & Clean 2.2081 Reinstall (`factory_reset_clean_install`):** For players with completely mangled, tampered, or corrupted Geometry Dash directories stuck on v2.2074: safely backs up all player progress, clears corrupt binaries, relocates out of broken OneDrive folders into the official Steam library, and transactionally installs a verified 2.2081 build.
- **OneDrive Storage Full & Lockout Diagnostics:** Detects when hard drives or Microsoft OneDrive accounts exceed their 5GB quota, explaining why files cannot be written or updated and offering automatic relocation into the local Steam library.
- **Smart Error Self-Repair Auto-Routing:** Intelligently maps Visual C++ errors, OneDrive full errors, and tampered files to their corresponding automated 1-click self-repair routines.

# GeodeSync v2.3.21

## Universal Multi-Install & OneDrive Detection + Custom Save Linking

- **Universal Multi-Installation Discovery (`find_all_gd_installations`):** Scans Steam libraries, Microsoft OneDrive, Desktop, Documents, and secondary drives to identify all Geometry Dash installations on your PC. Detects when users have multiple copies (e.g. an official Steam 2.2081 install vs. a portable/OneDrive 2.2074 folder) and prompts to switch to the official Steam library with 1 click.
- **Deep OneDrive & Portable Save Locator:** `get_save_data_dir()` now automatically scans across OneDrive redirected folders (`%OneDrive%\GeometryDash`, `Documents\GeometryDash`, etc.), Roaming AppData, and portable game directory saves (`<gd_path>\save`). Prioritizes directories containing active `CCGameManager.dat` save files.
- **Dedicated `💾 Save Folder` Linking:** Added a 1-click **`💾 Save Folder`** button to the bottom navigation bar and Troubleshooter, allowing users with custom or non-standard save directories to directly link their save location.
- **OneDrive Cloud-Only Stub Auto-Fix (`ensure_local_onedrive_files`):** Automatically clears Windows `attrib -U -P` offline/reparse-point cloud placeholders to resolve `0x8007016A` ("The cloud file provider is not running") and `WinError 392` errors.
- **Flexible Steam Library Folder Recognition:** Recognizes Steam game folders regardless of custom folder naming (e.g. `GeometryDash`, `GD`, `Geometry Dash 2.2`).
- **Enhanced `📁 Game Folder` Selector:** Users can now click either a directory OR directly select their `GeometryDash.exe` / `Geometry Dash.app` executable. Automatically steps into child folders if a parent directory is selected.

# GeodeSync v2.3.20

## Critical Hotfix: Eliminate False 2.2074 Detection & Infinite Downgrade Loop

- **Fixed False 2.2074 Version Misidentification:** Steam depot `3816559102876907245` (the official Geode-compatible 2.2081 Windows depot) downloads a `GeometryDash.exe` of size `10,698,752` bytes. Previously, this exact size was erroneously labeled as `2.2074`, causing GeodeSync to immediately show an outdated warning and prompt the user to downgrade again after a clean download.
- **Dual-Size 2.2081 Binary Recognition:** Both official Windows 2.2081 binary sizes (`10,698,752` bytes and `10,700,288` bytes) are now recognized as `2.2081 (Geode Compatible)`.
- **Depot & Installation Verification Updated:** `has_downloaded_depot()`, `validate_staged_depot()`, and `validate_windows_game_images()` now seamlessly accept both official 2.2081 binary sizes.
- **Removed Deprecated 2.2074 Target:** Purged the legacy `2.2074` entry from `KNOWN_VERSIONS` to guarantee downgrades always target clean 2.2081.

# GeodeSync v2.3.19

## Smart Self-Repair Assistant & Universal Auto-Fix System

- **Universal Smart Self-Repair Assistant (`show_smart_error`):** Every error dialog across GeodeSync now explains *exactly* what happened in human-readable English, outlines concrete steps, and features a prominent 1-click **`⚡ Auto-Fix It For Me (Instant Self-Repair)`** button that executes the fix automatically.
- **Global Interface Exception Recovery:** Unhandled Tkinter callbacks and UI glitches no longer freeze or leave users in stuck loops. The Smart Self-Repair Assistant intercepts them and provides instant session unsticking.
- **Troubleshooter Interactive Auto-Fix:** Running `Check Setup` or `Explain Error` now exposes a 1-click **`⚡ Auto-Fix Found Issue`** button to resolve detected issues immediately.
- **Deep Diagnostics & Recovery for File Locks:** Automatically detects `WinError 32` / `33` (files locked by running `GeometryDash.exe` or Steam) and automatically terminates hung processes before retrying.
- **Automated Steam Cache & Download Recovery:** Detects corrupt or stalled Steam depot downloads and provides automatic cache purging and clean re-downloading.
- **Direct Discord Ticket Integration:** Diagnostic tickets now include pre-formatted error tracebacks, player stats, and installed mod lists ready to paste into `#geodesync-help`.

# GeodeSync v2.3.18

## Emergency Unstick, 10s Auto-Sync & Discord Community Integration

- **Emergency Unstick & Auto-Repair Wizard:** Added 1-click self-repair in Troubleshooter to unstick users stuck in loops or frozen states. Terminates hung game processes, unlocks Steam manifest locks, purges corrupted Steam download depot caches, fixes crashing mods (such as `prevter.imageplus v1.1.1`), and enforces the 2.2081 target.
- **Fixed v2.207 / v2.2074 Stuck State:** Addressed issue where older sub-updates falsely matched target manifests. Strict 2.2081 binary verification ensures outdated builds trigger clear upgrade guidance.
- **Live 10-Second Auto-Sync:** Background sync loop automatically keeps versions, locks, running state, and save file counts current every 10 seconds.
- **Discord Rich Presence Demon & Grind Tracking:** Discord RPC now displays live level grind names and percentages (e.g. `Dead Device (99%) · 42 Demons`) extracted from decrypted save data during active gameplay.
- **Discord Community Integration:** Direct header link to the official Discord community (`https://discord.gg/tyQG5xNGCx`) and 1-click `Copy Discord Ticket` diagnostics card for immediate help in `#geodesync-help`.
- **Toolbox Real-Time Search Bar:** Instantly filter and highlight all 20 toolbox tools and companion features.
- **In-App What's New Dialog:** Clickable version badge opens changelog modal detailing recent features and fixes.

# GeodeSync v2.3.17

## Dashboard toolbox redesign

- Rebuilds the toolbox as five clearly labeled lanes: Mods, Play, Repair, Preferences, and App.
- Adds a restrained color accent to each lane and increases button spacing for faster scanning.
- Keeps all 20 actions directly available in the main dashboard and preserves the flat Tk layout used for Linux stability.
- Includes the Geode detection, Steam recovery, and Linux packaging fixes from v2.3.14 and v2.3.15.
- Windows and Linux packages must pass release CI before distribution. macOS downloads remain withheld until a Developer ID signed and notarized build is available.

# GeodeSync v2.3.16

## Dashboard polish

- Reorganized the 20 existing tools into task-focused rows for mods, gameplay, repair, settings, and system actions.
- Kept the native controls in one flat Tk grid for Linux stability.

# GeodeSync v2.3.14

## Geode detection hotfix

- Detect Geode when its loader DLL is present even if the optional legacy XInput proxy is absent or named differently.
- On macOS, detect Geode when the user selects the app bundle itself, and check the loader in the supported bundle locations.
- Ignore leftover Geode data folders unless a loader or Geode startup log confirms an installation.
- GeodeSync supports Geometry Dash installed through Steam. Unofficial or pirated game copies are not supported.

## macOS depot recovery

- A retry after Steam leaves malformed cached game metadata now clears only the validated Geometry Dash depot cache, never the installed game or saves.
- Steam must be fully quit before GeodeSync resets that cache; the app explains this and leaves the cache untouched if the path cannot be verified.

## Linux / Steam Deck compatibility

- Rebuild the Linux package on Ubuntu 22.04 (glibc 2.35) so bundled Tcl/Tk does not require GLIBC_2.42, which is unavailable on SteamOS. The package still needs to pass the Linux CI launch check before distribution.
- Linux support is for Steam Deck Desktop Mode; do not modify SteamOS system libraries to work around an older package.

## macOS packaging status

- The app bundle is now sealed after its final metadata is written and is verified in CI. This addresses the malformed bundle signature found in the previous package.
- The v2.3.12 macOS downloads are withheld until a package can be Developer ID signed and notarized. Do not use the previous Mac package as a workaround or bypass Gatekeeper.

Windows and Linux downloads can be published independently. GeodeSync will not advertise or auto-install a release when that platform’s package is missing.

- Updated GeodeSync branding across the app, website and presence images.
- Reduced overlapping Discord presence updates and made its status message more accurate. Discord controls which activity appears; another app such as Medal may still be shown.
- Recorded unexpected interface errors in crash.log and fixed update error messages.
- Existing compatible installations check for updates while running. Older or offline versions may need a manual download from the Releases page.

If GeodeSync crashes, share its crash.log with support. On Windows, open `%APPDATA%\GeodeSync` to find it.


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

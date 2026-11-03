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

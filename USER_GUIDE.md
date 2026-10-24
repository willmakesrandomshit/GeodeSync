# GeodeSync User Guide

GeodeSync helps manage a Steam copy of Geometry Dash: it can switch to a supported game version, protect that version from Steam auto-updates, manage saves and mods, and collect diagnostics when something goes wrong. It does not replace Steam or Geode.

This guide describes the v2.0.0 interface. Button names can vary slightly between older releases; update from the official [GeodeSync GitHub Releases page](https://github.com/willmakesrandomshit/GeodeSync/releases) if a control mentioned here is missing.

## Before you start

- Install Geometry Dash through Steam, sign in to the Steam account that owns it, and make sure Steam can download game files.
- Close Geometry Dash before changing its version or replacing game files.
- Back up your Geometry Dash saves before major changes. GeodeSync can make a backup, but keeping a separate copy is sensible.
- Download GeodeSync only from the official GitHub Releases page. Do not share your save files, Steam credentials, or account tokens with support.
- Game switching needs a working internet connection and enough free disk space for Steam to download and stage the depot.

## Install and open GeodeSync

### Windows

1. Download the Windows ZIP from the official Releases page.
2. Extract the ZIP to a normal folder. Do not run the app from inside the ZIP preview.
3. Open `GeodeSync.exe`.
4. If Windows shows a security prompt, check that the download came from the official repository before deciding whether to continue.

The Windows release is packaged as an executable; Python is not required separately.

### macOS

1. Download the ZIP for your Mac: `arm64` for Apple silicon, or `x86_64` for Intel.
2. Extract it and move `GeodeSync.app` into your personal Applications folder (`~/Applications`).
3. Open the app. The release includes its Python and Tk runtime; you do not need Terminal or a separate Python install.
4. If Gatekeeper warns that the community build is not notarized, only proceed if you downloaded it from the official GeodeSync repository and trust that release. Control-click the app, choose **Open**, and confirm once. This is a one-time app-opening decision; do not disable Gatekeeper globally.

The packaged Mac builds target macOS 11 or newer on Apple silicon and macOS 10.15 or newer on Intel. That is the build target, not a claim that every macOS version or Steam setup has been tested. A Mac build cannot repair a Steam or Geometry Dash problem that is outside GeodeSync.

### Linux / Steam Deck

The repository contains a legacy Linux runner, but the current main release and this guide focus on Windows and macOS packages. Linux/Steam Deck behavior depends on the runner, Python/Tk installation, Steam/Proton setup, and current release assets. Do not use the Windows or Mac package on Linux.

## First launch and setup

1. Start Steam and make sure Geometry Dash appears in your Library.
2. Open GeodeSync. It checks for Steam, the game folder, the installed game version, Geode, saves, and the Steam update lock. These status labels are detection results; if a path is wrong, use **Browse GD Folder** in the footer (or the equivalent folder control in your build) and select the Steam Geometry Dash folder. On Mac, you may select the folder containing `Geometry Dash.app` or the app bundle itself.
3. Follow the large **Next step** card. It recommends one action based on the detected setup:
   - **Install Geode**: opens the official Geode installer. Complete that installer, return to GeodeSync, and refresh/reopen if the status has not updated.
   - **Install game version 2.2081**: starts the safe version switch described below.
   - **Launch Geometry Dash**: asks Steam to launch the game. On macOS, GeodeSync checks the app bundle first and then asks Steam to launch it; an accepted request does not guarantee the game process started.
4. Read every confirmation before continuing. A version change replaces game files and changes Steam's update lock.

## Switch to the Geode-compatible game version

The default recommended target in v2.0.0 is Geometry Dash 2.2081. The target is not a promise that every Geode mod works; check the Geode and mod requirements too.

1. Make sure Geometry Dash is closed. If prompted, allow GeodeSync to close it or close it yourself.
2. Click **Backup saves** under **More tools** first if you want a manual backup. The version-switch flow also backs up detected save files and asks before proceeding if it cannot find any.
3. Click the main **Install game version 2.2081** button and review the confirmation.
4. Leave Steam open and let its download finish. GeodeSync stages and validates the downloaded files before replacing the installed game. Do not quit GeodeSync or Steam, launch the game, or click the switch button repeatedly while it is working.
5. Wait for the completion message and check the activity log. A Steam “download complete” message by itself is not proof that the depot is valid or installed.
6. When the status card says the game is ready, use **Launch Geometry Dash**. Confirm the game actually reaches its menu before assuming the switch worked.

After a successful switch, GeodeSync protects the selected version by locking Steam's Geometry Dash app manifest against automatic updates. Steam may be unable to update Geometry Dash while that protection is active. Use **Restore current game** to remove the lock and ask Steam to validate/update the game when you want the latest official version again.

### Choose a different supported version

Open **More tools → Version selector**, choose one of the versions offered for your platform, and select **Set as Target Version**. The Mac build may offer fewer versions than Windows. Selecting a target only changes the chosen version; it does not download it. Follow the main Next step card to install it. Avoid choosing a version unless it is compatible with your Geode build and mods.

### Restore the current/latest Steam version

1. Click **Restore current game** and read the confirmation.
2. GeodeSync unlocks the Geometry Dash Steam manifest and triggers Steam's file validation. Watch the Steam Downloads page and wait for the update/validation to finish.
3. Launch Geometry Dash from Steam once to confirm it works. Geode or mods may need to be reinstalled or updated for the current game version.

Restoring the current game changes game files through Steam; it does not delete your GeodeSync save-backup folders. Do not manually delete or edit Steam manifest files to fix an update problem.

## Saves and profiles

### Back up saves

Choose **More tools → Backup saves**. GeodeSync copies detected `.dat` and `.dat.bak` save files into a timestamped `GeodeSync_Save_Backups` folder under the Geometry Dash save-data folder and shows the destination. Keep another copy outside that folder if the saves are important.

**Auto-Backup: ON/OFF** controls whether GeodeSync snapshots detected saves after it observes Geometry Dash close. It is a convenience, not a substitute for a separate backup. Check the activity log for a successful backup entry.

### Restore a save backup

Choose **More tools → Restore saves**. It offers the newest GeodeSync backup and warns that restoring overwrites matching current save files. Close Geometry Dash first. If possible, make a fresh backup of the current files before restoring.

### Check or repair saves

Choose **More tools → Save Doctor** to check the main save files and look for a usable alternate or GeodeSync backup. Read its proposed repair carefully. If it offers a repair, it preserves the replaced file with a `.corrupted_bak` suffix before copying the selected fallback. If it cannot find a known-good backup, it cannot reconstruct lost progress; check Steam Cloud or another backup before writing over files.

### Game profiles and mod profiles

- **Game profiles** saves the selected supported game version and the currently active Geode mod filenames. Applying a profile may switch game files and enable/disable mods. It cannot download missing profile mods for you.
- **Mod profiles** lets you save or switch mod sets and use vanilla mode. Close Geometry Dash before changing mods. Keep a copy of important mod files; a profile records filenames, not the mod contents.

## Other tools

Open **More tools** to find the additional utilities. Use only the tools you need and read each confirmation:

- **Mods folder** opens the detected Geode mods folder.
- **Cache cleaner** can remove selected crash/log files and downloaded song/audio cache. Selected cached songs may need to download again. Review the selection before confirming.
- **Crash Doctor** inspects recent Geode crash logs and may offer to temporarily disable a suspected mod. A suspected mod is a clue, not proof; re-enable it if disabling it does not resolve the crash.
- **Fix click delay**, **FPS unlocker**, **Essential mods**, and other game utilities change files, settings, or install community content. Back up first, review prompts, and check each tool's result in the activity log. Mod availability and compatibility can change over time.
- **Clear** clears the visible activity panel; it is not a repair action. Prefer exporting a support report before clearing useful troubleshooting history.

## Updates to GeodeSync

If GeodeSync shows an update banner, use **Install update** or open the official Releases page. On Mac, the in-app updater selects the matching processor package and checks the download before replacing the app. If an update cannot be installed, download the correct package from the official Releases page and replace the old app/executable after closing GeodeSync. Do not mix Intel and Apple silicon Mac builds.

## Troubleshooting

### Steam reports “disk write error”

1. Stop retrying the same action repeatedly and close Geometry Dash.
2. If GeodeSync previously changed the game version, choose **Restore current game** and allow Steam validation/update to finish.
3. In Steam, open **Geometry Dash → Properties → Installed Files → Verify integrity of game files**. Watch for a Steam Downloads error; “files validated” only confirms the files Steam checked at that moment.
4. Restart Steam and GeodeSync once. Confirm the Steam library drive has free space and that Steam can write to its own library. Do not delete game files, manually edit `appmanifest_322170.acf`, or change broad folder permissions.
5. If it persists, export and review a GeodeSync support report and include the exact Steam error text. A Steam disk-write error may come from Steam, its library drive, permissions, antivirus/security software, or GeodeSync's update lock; the wording alone does not identify which.

### macOS: “Failed to start process for this game: OS Error 256”

This code alone does not identify the cause. First use **Restore current game**, wait for Steam validation, then try launching Geometry Dash directly from Steam. In GeodeSync, check that the Geometry Dash version and app bundle are detected. If Steam itself still gives OS Error 256, GeodeSync has not proved that it caused the failure; the Steam launch log or macOS Console report is needed to identify the cause. Do not bypass Gatekeeper, remove security checks, or repeatedly downgrade while the game is failing to launch.

### “download complete” but GeodeSync says the cached app is invalid

GeodeSync leaves the installed game unchanged when the downloaded Mac depot fails app-bundle validation. Quit Steam completely, reopen Steam and GeodeSync, then retry the version switch once. If it fails again, stop and send the support report; repeated retries may just reproduce a bad or incomplete cached download.

### Error says “junk after document element” or app metadata is invalid

Stop the game switch. This indicates the downloaded app metadata could not be parsed, so GeodeSync should not replace the installed game. Export a support report and send it with the exact error. Do not try to repair `Info.plist` manually or delete the cached depot unless support gives you a specific, backed-up procedure.

### Game launches without Geode or mods

Confirm Geode is installed for the selected Geometry Dash version. A Steam integrity verification can restore official game files and remove injected/mod-loader files; if you run it, you may need to install Geode again. Check each mod's supported game version and use the Geode interface to update or disable incompatible mods.

### GeodeSync cannot find Steam or Geometry Dash

Make sure Steam is installed and Geometry Dash is installed through Steam. Use the folder chooser to select the correct Steam library's Geometry Dash folder. On Mac, select the folder containing `Geometry Dash.app`, or select the app bundle. If the chosen path is valid but detection still fails, include the platform, processor, GeodeSync version, and support report.

## Export a support report

If something fails, the report is more useful than a photo of only the error dialog:

1. In GeodeSync, open **More tools → Export support report**.
2. Save the `.txt` file somewhere easy to find, such as the Desktop.
3. Open it and review it before sharing. The report includes GeodeSync/platform/game status and recent activity. The app redacts common home-folder paths and email addresses and does not include save-file contents or mod files, but you should still review the whole report.
4. Attach that text file to your support message. Include what button you clicked, what you expected, what happened, the exact error, whether Steam can launch Geometry Dash by itself, your GeodeSync version, macOS/Windows version, and Mac processor type if applicable.

If you cannot open GeodeSync to export the report, take a screenshot of the full window including the activity log. Do not post save files, passwords, Steam credentials, or authentication tokens.

## Data and recovery notes

- Settings and game profiles are stored locally in GeodeSync's app-data folder. GeodeSync does not sync those settings between computers.
- Save backups live alongside the detected Geometry Dash save-data location. They are not a cloud backup.
- Game switching creates recovery data so an interrupted file swap can be recovered on the next start. If GeodeSync says recovery needs attention, do not start another switch; export a support report first.
- The support report is created only when you choose **Export support report**. Review it before sending it to anyone.

## Official links

- [GeodeSync releases](https://github.com/willmakesrandomshit/GeodeSync/releases)
- [GeodeSync source repository](https://github.com/willmakesrandomshit/GeodeSync)
- [Geode project](https://geode-sdk.org/)

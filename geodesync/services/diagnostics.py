"""Installation diagnostics (moved verbatim from v2.8.0 main.py): plain-English error explanations and the install issue scanner. No Tk imports."""

import os
import sys
import shutil
import platform
import struct
from geodesync.platform.process_manager import IS_LINUX, IS_MAC, IS_WIN, safe_run_command
from geodesync.platform.steam import find_macos_game_app, is_steam_library_game_path, validate_macos_game_app

if IS_WIN:
    import winreg
else:
    winreg = None





def ensure_local_onedrive_files(folder_path):
    """Ensures OneDrive cloud-only stub files are downloaded locally to prevent WinError 392 or 0x8007016A."""
    if not IS_WIN or not folder_path or not os.path.isdir(folder_path):
        return True, "Path not applicable"
    try:
        target_pattern = os.path.join(folder_path, "*")
        safe_run_command(
            ["attrib.exe", "-U", "-P", "/s", "/d", target_pattern],
            timeout=10,
        )
        return True, "OneDrive files pinned locally"
    except Exception as e:
        return False, str(e)


def check_vc_redist_installed():
    """Checks if Microsoft Visual C++ 2015-2022 (x86) Redistributable is installed and up to date."""
    if not IS_WIN:
        return True, "Not required on this platform", None
    if not winreg:
        return True, "Registry unavailable", None
    try:
        flags = winreg.KEY_READ
        if hasattr(winreg, "KEY_WOW64_32KEY"):
            flags |= winreg.KEY_WOW64_32KEY
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X86", 0, flags) as key:
            installed, _ = winreg.QueryValueEx(key, "Installed")
            version, _ = winreg.QueryValueEx(key, "Version")
            ver_clean = str(version).lstrip("v").split(".")
            major = int(ver_clean[0]) if len(ver_clean) > 0 and ver_clean[0].isdigit() else 0
            minor = int(ver_clean[1]) if len(ver_clean) > 1 and ver_clean[1].isdigit() else 0
            if installed == 1 and (major > 14 or (major == 14 and minor >= 30)):
                return True, f"Installed ({version})", version
            return False, f"Outdated ({version})", version
    except Exception:
        syswow = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "SysWOW64", "msvcp140.dll")
        sys32 = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "System32", "msvcp140.dll")
        if os.path.exists(syswow) or os.path.exists(sys32):
            return True, "Detected via system DLL", None
        return False, "Not installed or missing", None


def check_folder_writable_and_space(folder_path):
    """Verifies that folder_path is writable and has adequate free space.
    Detects OneDrive quota locks (storage full) and permission blocks.
    """
    if not folder_path or not os.path.isdir(folder_path):
        return False, "Directory does not exist", 0
    try:
        usage = shutil.disk_usage(folder_path)
        free_mb = round(usage.free / (1024 * 1024), 1)

        test_file = os.path.join(folder_path, f".geodesync-write-test-{os.getpid()}.tmp")
        try:
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
        except OSError as exc:
            err_str = str(exc).lower()
            if "112" in err_str or "not enough space" in err_str or "quota" in err_str:
                return False, "Drive or OneDrive storage is completely full! Cannot write files.", free_mb
            if "onedrive" in folder_path.lower():
                return False, f"OneDrive is blocking write access (quota full or locked): {exc}", free_mb
            return False, f"Directory is not writable: {exc}", free_mb

        if free_mb < 500:
            return False, f"Critically low disk space ({free_mb} MB remaining). At least 500 MB is required.", free_mb

        return True, "OK", free_mb
    except Exception as exc:
        return False, str(exc), 0


WINDOWS_PE_MACHINE_NAMES = {
    0x014C: "x86",
    0x8664: "x64",
    0xAA64: "ARM64",
}


def read_windows_pe_machine(path):
    """Read and structurally validate a PE executable/DLL's architecture."""
    try:
        file_size = os.path.getsize(path)
        if file_size < 0x40:
            raise ValueError("file is too small to contain a PE header")
        with open(path, "rb") as stream:
            dos_header = stream.read(0x40)
            if dos_header[:2] != b"MZ":
                raise ValueError("missing DOS MZ signature")
            pe_offset = struct.unpack_from("<I", dos_header, 0x3C)[0]
            if pe_offset < 0x40 or pe_offset > file_size - 24:
                raise ValueError("PE header offset is outside the file")
            stream.seek(pe_offset)
            signature = stream.read(4)
            coff_data = stream.read(20)
            if signature != b"PE\0\0" or len(coff_data) != 20:
                raise ValueError("missing or truncated PE/COFF header")
            machine, section_count, _timestamp, _symbols, _symbol_count, optional_size, _flags = struct.unpack(
                "<HHIIIHH", coff_data
            )
            if machine not in WINDOWS_PE_MACHINE_NAMES:
                raise ValueError(f"unsupported PE machine type 0x{machine:04x}")
            if not 1 <= section_count <= 96:
                raise ValueError("invalid PE section count")
            if optional_size < 2 or pe_offset + 24 + optional_size + section_count * 40 > file_size:
                raise ValueError("truncated PE optional header or section table")
            optional_header = stream.read(optional_size)
            optional_magic = struct.unpack_from("<H", optional_header, 0)[0]
            expected_magic = 0x10B if machine == 0x014C else 0x20B
            if optional_magic != expected_magic:
                raise ValueError("PE machine type does not match its optional-header format")
            for _ in range(section_count):
                section = stream.read(40)
                if len(section) != 40:
                    raise ValueError("truncated PE section table")
                _name, _virtual_size, _virtual_address, raw_size, raw_offset, *_rest = struct.unpack(
                    "<8sIIIIIIHHI", section
                )
                if raw_size and (raw_offset > file_size or raw_size > file_size - raw_offset):
                    raise ValueError("PE section data extends beyond the file")
            return machine
    except OSError as exc:
        raise ValueError(f"file cannot be read ({exc})") from exc


def validate_windows_game_images(game_root, expected_exe_size=None):
    """Reject damaged or wrong-architecture game EXE/DLL files before commit."""
    executable = os.path.join(game_root, "GeometryDash.exe")
    if not os.path.isfile(executable):
        return "GeometryDash.exe is missing."
    try:
        if expected_exe_size is not None:
            actual = os.path.getsize(executable)
            if isinstance(expected_exe_size, (tuple, list, set)):
                if actual not in expected_exe_size:
                    return "GeometryDash.exe size does not match the selected Steam depot."
            elif actual != expected_exe_size:
                return "GeometryDash.exe size does not match the selected Steam depot."
    except OSError as exc:
        return f"GeometryDash.exe cannot be inspected ({exc})."
    try:
        expected_machine = read_windows_pe_machine(executable)
    except ValueError as exc:
        return f"GeometryDash.exe is not a valid Windows executable ({exc})."

    walk_errors = []
    for directory, dirnames, filenames in os.walk(game_root, onerror=walk_errors.append):
        # The active transaction contains backup copies of the old install;
        # those are not part of the candidate game being validated.
        dirnames[:] = [name for name in dirnames if not name.startswith(".geodesync-transaction-")]
        for filename in filenames:
            if not filename.lower().endswith(".dll"):
                continue
            path = os.path.join(directory, filename)
            relative = os.path.relpath(path, game_root)
            try:
                machine = read_windows_pe_machine(path)
            except ValueError as exc:
                return f"DLL {relative!r} is damaged or not a valid Windows library ({exc})."
            if machine != expected_machine:
                actual = WINDOWS_PE_MACHINE_NAMES[machine]
                expected = WINDOWS_PE_MACHINE_NAMES[expected_machine]
                return f"DLL {relative!r} is {actual}, but GeometryDash.exe is {expected}."
    if walk_errors:
        return f"A game folder could not be fully inspected ({walk_errors[0]})."
    return None


def explain_error_text(error_text, platform_name=None):
    """Map common player-facing errors to short, concrete, safe recovery steps."""
    raw = str(error_text or "").strip()
    text = raw.casefold()
    platform_name = (platform_name or platform.system()).casefold()
    if not raw:
        return (
            "Paste the exact error",
            "Copy the full message from the error window and paste it above. Include any code such as 0xc000007b.",
        )
    if "whoopsies" in text and "unhandled exception" in text:
        return (
            "Geode crashed",
            "“Whoopsies! An unhandled exception has occurred” is Geode’s crash report, not the cause by itself. Reinstalling GeodeSync or deleting the old game folder won’t identify the crash.\n\n"
            "Copy the complete report, including Geode Information, Exception Information, Stack Trace, and Installed Mods. If the crash window has a Copy button, use it; otherwise open Crash Doctor or attach a screenshot of the whole report.\n\n"
            "A selected folder ending in `steamapps\\common\\Geometry Dash` and containing `GeometryDash.exe` is the expected Steam layout. We still need the crash report to tell whether a mod, Geode, or another game component failed. Do not delete saves or download replacement DLLs.",
        )
    if platform_name in ("darwin", "mac", "macos") and (
        ("damaged" in text and "can’t be opened" in text)
        or ("damaged" in text and "can't be opened" in text)
        or ("move it to the trash" in text)
    ):
        return (
            "macOS rejected the GeodeSync app",
            "Don’t keep deleting unrelated Trash items, run Terminal commands, or turn off Gatekeeper. This alert can mean the downloaded app bundle is incomplete or its signature cannot be verified. Confirm the exact GeodeSync version and that the download came from the official release. If it still says the app is damaged, stop and send support a screenshot plus the reviewed GeodeSync support report so the package can be checked.\n\n"
            "If macOS instead says it cannot check the app for malicious software, and you have verified that it came from the official release, Apple may offer an Open Anyway choice under System Settings → Privacy & Security. That only records your decision to allow this app; it does not make the app Apple-trusted. If the damaged-app alert remains, do not force it open.",
        )
    if platform_name in ("darwin", "mac", "macos") and (
        "cannot be opened because apple cannot check" in text
        or "apple cannot check this app for malicious software" in text
        or "apple cannot check it for malicious software" in text
        or "unidentified developer" in text
        or "developer cannot be verified" in text
    ):
        return (
            "macOS needs your approval to open this app",
            "First confirm the app came from the official GeodeSync release and that its download completed. If you trust that exact build, try opening it once, then use System Settings → Privacy & Security → Open Anyway if macOS offers that choice. Review the warning before deciding. This does not make the app notarized or Apple-trusted. If macOS says the app is damaged, stop and send support the exact alert instead of overriding it.",
        )
    if "0xc000007b" in text or "bad image" in text:
        return (
            "Windows could not load a game file",
            "1. Close Geometry Dash and Steam.\n"
            "2. In Steam, open Library → Geometry Dash → Properties → Installed Files → Verify integrity of game files.\n"
            "3. Launch Geometry Dash from Steam once.\n"
            "4. If it only fails with Geode installed, disable the most recently added Geode mod and retry.\n\n"
            "Do not download individual DLL files from websites. If the same error remains, export a GeodeSync support report and include this exact message.",
        )
    if any(token in text for token in ("failed to load python dll", "python314.dll", "_mei")):
        return (
            "GeodeSync did not start correctly",
            "Download the latest Windows package from the official GeodeSync Releases page. Extract the whole ZIP to a normal folder, keep `_internal` beside `GeodeSync.exe`, and run the EXE from that folder—not from the ZIP preview.\n\n"
            "If it still fails, export a support report and include the full message. Do not download replacement DLLs from third-party sites.",
        )
    if any(token in text for token in ("winerror 32", "winerror 33", "used by another process", "being used by another", "being used by")):
        return (
            "Game file locked by a background process",
            "Geometry Dash or Steam is currently open and holding onto game files. "
            "Click '⚡ Auto-Fix It For Me' below to terminate any hung processes, unlock the files, and retry automatically.\n\n"
            "If you prefer manual steps: Open Task Manager, end GeometryDash.exe, restart Steam, and try again.",
        )
    if any(token in text for token in ("2.207", "2.2074", "outdated 2.2")):
        return (
            "Outdated Geometry Dash 2.2074 build",
            "Your game is on an older 2.2 sub-update (2.2074) that causes crashes and mod incompatibility with modern Geode. "
            "Click '⚡ Auto-Fix It For Me' to upgrade cleanly to the official Geode-compatible 2.2081 build.",
        )
    if any(token in text for token in ("steam download timed out", "steam download is incomplete", "malformed downloaded depot", "depot cache")):
        return (
            "Steam download cache corrupted or timed out",
            "Steam left an incomplete download chunk in its cache folder. "
            "Click '⚡ Auto-Fix It For Me' to safely clear the corrupt cache, reset the manifest lock, and restart a clean download.",
        )
    if any(token in text for token in ("prevter.imageplus", "entry point not found")):
        return (
            "Incompatible mod causing game launch crash",
            "An incompatible mod (such as an outdated Image+ build) is crashing Geometry Dash on startup. "
            "Click '⚡ Auto-Fix It For Me' to automatically install the patched, compatible version or safely disable it.",
        )
    if any(token in text for token in ("manifest locked", "appmanifest_322170")):
        return (
            "Steam manifest file is locked",
            "The Steam update manifest is set to read-only to protect your mods from being overwritten. "
            "Click '⚡ Auto-Fix It For Me' to unlock it safely so Steam can write files.",
        )
    if any(token in text for token in ("visual c++", "visual c", "vc++", "vcredist", "msvcp140", "vcruntime140")):
        return (
            "Microsoft Visual C++ Redistributable is outdated or missing",
            "Geode and Geometry Dash require the official Microsoft Visual C++ 2015-2022 Redistributable (x86).\n\n"
            "Click '⚡ Auto-Fix It For Me' to download and install the official Microsoft package automatically.",
        )
    if any(token in text for token in ("storage full", "quota", "not enough space on disk", "winerror 112")):
        return (
            "Disk or OneDrive storage quota full",
            "Your hard drive or Microsoft OneDrive cloud storage is completely out of space, which blocks Windows from creating or updating game files.\n\n"
            "Click '⚡ Auto-Fix It For Me' to switch to a drive with free space or relocate out of OneDrive, or free up storage in your OneDrive account.",
        )
    if any(token in text for token in ("tampered", "renamed", "clean install", "factory reset", "mangled")):
        return (
            "Geometry Dash files tampered or damaged",
            "Your game files have been moved, renamed, or corrupted across multiple sub-updates.\n\n"
            "Click '⚡ Auto-Fix It For Me' to run a clean Factory Reset: your saves will be preserved while clean, official 2.2081 game files are installed.",
        )
    if any(token in text for token in ("onedrive", "0x8007016a", "reparse point", "cloud file provider", "cloud-only", "offline attribute", "winerror 392")):
        return (
            "OneDrive cloud sync or placeholder conflict",
            "Geometry Dash game files or save data are stored inside Microsoft OneDrive and are stuck in cloud-only online mode.\n\n"
            "Click '⚡ Auto-Fix It For Me' to force Windows to pin and download all files locally to your computer.\n\n"
            "If issues persist: Right-click your Geometry Dash folder in File Explorer, select 'Always keep on this device', or move your game folder outside of OneDrive into your Steam library.",
        )
    if any(token in text for token in ("cannot find ccgamemanager", "save file corrupted", "ccgamemanager.dat", "no save backup found")):
        return (
            "Geometry Dash save data issue",
            "Geometry Dash could not find or read your player save files (CCGameManager.dat), or your saves are in a custom or OneDrive directory.\n\n"
            "Click '⚡ Auto-Fix It For Me' to auto-discover your saves across OneDrive and local drives, or click '💾 Save Folder' to link your save directory.",
        )
    if "disk write error" in text or ("disk" in text and "write" in text and "error" in text):
        return (
            "Steam could not write game files",
            "1. Close Geometry Dash.\n"
            "2. Check that the Steam library drive has free space.\n"
            "3. Restart Steam, then use Library → Geometry Dash → Properties → Installed Files → Verify integrity of game files.\n"
            "4. If Steam still shows the error, export a GeodeSync support report and include the Steam message.\n\n"
            "Do not delete Steam manifests or game files by hand.",
        )
    if any(token in text for token in ("access is denied", "permission denied", "winerror 5", "permissionerror")):
        return (
            "GeodeSync could not access a file",
            "Close Geometry Dash and Steam, then reopen GeodeSync normally and check that the selected folder is the Steam Geometry Dash folder. If Windows Security shows a block notification, review that notification and allow only the official GeodeSync app if you trust it. Do not turn off Defender or run random repair scripts.\n\n"
            "If it still fails, export a support report and include the exact message.",
        )
    if any(token in text for token in ("urlopen error", "name or service not known", "connection timed out", "network is unreachable", "temporary failure in name resolution")):
        return (
            "GeodeSync could not reach the download service",
            "Check that your internet works, then retry once. If browsing works but GeodeSync still cannot download, check whether a firewall or proxy is blocking GitHub. Include the full error and export a support report if it continues.",
        )
    if "steam" in text and any(token in text for token in ("not running", "not found", "could not locate")):
        return (
            "Steam was not found",
            "Open Steam, sign in, and make sure Geometry Dash is installed through Steam. Then return to GeodeSync and choose Game Folder if it still cannot find the install.",
        )
    if "incompatible with geode" in text or "unsupported game version" in text:
        return (
            "This Geometry Dash version may not work with Geode",
            "In GeodeSync, choose a supported game version and switch it using the main game-version button. Wait for Steam to finish, then launch Geometry Dash from Steam. Check your mods for version compatibility too.",
        )
    return (
        "No matching fix found yet",
        "GeodeSync does not recognize this message, so it will not guess or change your files. Copy the full error, choose Export Report in Activity Log, and send both to support. Include what you clicked just before it appeared.",
    )


def scan_installation_issues(manager, is_windows=None, is_macos=None, recovery_error=None, is_linux=None):
    """Read-only checks for common setup problems; never modifies game or Steam files."""
    is_windows = IS_WIN if is_windows is None else bool(is_windows)
    is_macos = IS_MAC if is_macos is None else bool(is_macos)
    is_linux = IS_LINUX if is_linux is None else bool(is_linux)
    findings = []
    steam_path = getattr(manager, "steam_path", None)
    if not steam_path or not os.path.isdir(steam_path):
        findings.append({
            "title": "Steam was not found",
            "detail": "GeodeSync cannot check or manage the Steam game until it can find Steam.",
            "steps": "Open and sign in to Steam. If it is already open, choose Game Folder in GeodeSync and select the Geometry Dash folder inside your Steam library.",
        })

    game_path = getattr(manager, "gd_path", None)
    if not game_path or not os.path.isdir(game_path):
        findings.append({
            "title": "Geometry Dash folder was not found",
            "detail": "The selected game folder is missing or unavailable.",
            "steps": "Choose Game Folder and select the Steam Geometry Dash folder. On Windows it contains GeometryDash.exe; on Mac it contains Geometry Dash.app.",
        })
    elif is_windows:
        if is_steam_library_game_path(game_path):
            findings.append({
                "title": "Steam Geometry Dash folder confirmed",
                "detail": "The selected folder follows Steam’s `steamapps\\common\\Geometry Dash` layout.",
                "steps": "This is the folder to select in the Geode Installer. It should contain `GeometryDash.exe`; do not put the installer file inside the folder or copy Geode files by hand.",
            })
        else:
            findings.append({
                "title": "This game folder is not clearly inside a Steam library",
                "detail": "GeodeSync found a Geometry Dash folder, but its path does not match Steam’s `steamapps\\common\\Geometry Dash` layout.",
                "steps": "In Steam, open Geometry Dash → Properties → Installed Files → Browse. In GeodeSync choose Game Folder and select that folder—the one containing `GeometryDash.exe`. Do not select the installer or copy Geode files by hand.",
            })
        problem = validate_windows_game_images(game_path)
        if problem:
            findings.append({
                "title": "A Windows game file may be damaged or mismatched",
                "detail": problem,
                "steps": "Close the game, then in Steam open Library → Geometry Dash → Properties → Installed Files → Verify integrity of game files. Do not replace individual DLLs from download sites. Run this check again after Steam finishes.",
            })
        vc_ok, vc_status, _ = check_vc_redist_installed()
        if not vc_ok:
            findings.append({
                "title": "Microsoft Visual C++ Redistributable is outdated or missing",
                "detail": f"Status: {vc_status}\nGeode and Geometry Dash require the official Microsoft Visual C++ 2015-2022 Redistributable (x86). Without it, Geode crashes on launch with MSVCP140.dll / VCRUNTIME140.dll or outdated C++ errors.",
                "steps": "Click '📥 Install Visual C++' in the Troubleshooter to automatically install the official Microsoft package.",
            })
        if game_path and os.path.isdir(game_path):
            writable, write_err, free_mb = check_folder_writable_and_space(game_path)
            if not writable:
                findings.append({
                    "title": "Game folder is locked or out of storage",
                    "detail": f"Path: {game_path}\nStatus: {write_err}\nFree storage: {free_mb} MB",
                    "steps": "If this folder is in OneDrive, your cloud storage quota may be full. Relocate your game into your official Steam library (C:\\Program Files (x86)\\Steam\\steamapps\\common\\Geometry Dash) or free up storage.",
                })
    elif is_macos:
        if is_steam_library_game_path(game_path):
            findings.append({
                "title": "Steam Geometry Dash folder confirmed",
                "detail": "The selected folder follows Steam’s `steamapps/common/Geometry Dash` layout.",
                "steps": "This is the folder to select in the Geode Installer. Do not copy Geode files by hand.",
            })
        else:
            findings.append({
                "title": "This game folder is not clearly inside a Steam library",
                "detail": "GeodeSync found a Geometry Dash app, but its path does not match Steam’s `steamapps/common/Geometry Dash` layout.",
                "steps": "In Steam, open Geometry Dash → Properties → Installed Files → Browse. In GeodeSync choose Game Folder and select the Geometry Dash folder in that Steam library.",
            })
        app_path = find_macos_game_app(game_path)
        problem = validate_macos_game_app(app_path)
        if problem:
            findings.append({
                "title": "Geometry Dash.app looks incomplete",
                "detail": problem,
                "steps": "Quit Steam, reopen it, then use Geometry Dash → Properties → Installed Files → Verify integrity. Run this check again after Steam finishes.",
            })
    elif is_linux:
        if is_steam_library_game_path(game_path):
            findings.append({
                "title": "Steam / Proton Geometry Dash folder confirmed",
                "detail": "This folder follows Steam’s `steamapps/common/Geometry Dash` layout used by the Proton game files.",
                "steps": "Keep using this Steam library folder. GeodeSync manages the Windows Geometry Dash files Steam runs through Proton; it does not install a native Linux build.",
            })
        else:
            findings.append({
                "title": "This game folder is not clearly inside a Steam library",
                "detail": "GeodeSync found a folder, but its path does not match Steam’s `steamapps/common/Geometry Dash` layout.",
                "steps": "In Steam, open Geometry Dash → Properties → Installed Files → Browse. Select that folder in GeodeSync. On Steam Deck, switch to Desktop Mode first.",
            })
        executable = os.path.join(game_path, "GeometryDash.exe")
        if not os.path.isfile(executable):
            findings.append({
                "title": "The Proton game executable is missing",
                "detail": "The selected folder does not contain `GeometryDash.exe`.",
                "steps": "In Steam, open Geometry Dash → Properties → Installed Files → Verify integrity of game files. Wait for Steam to finish, then select the folder containing `GeometryDash.exe` again.",
            })

    # Check OneDrive game path
    if game_path and "onedrive" in game_path.casefold():
        findings.append({
            "title": "Geometry Dash is located inside Microsoft OneDrive",
            "detail": f"Your active game path is:\n{game_path}\n\nOneDrive cloud sync frequently locks game files during updates, reverts modified files, or keeps executables online-only (causing 0x8007016A errors).",
            "steps": "If you installed Geometry Dash through Steam, click '📁 Game Folder' and select your official Steam library folder instead. If keeping it in OneDrive, right-click the folder in File Explorer and select 'Always keep on this device'.",
        })

    # Check OneDrive save path
    save_path = manager.get_save_data_dir() if hasattr(manager, "get_save_data_dir") else None
    if save_path and "onedrive" in save_path.casefold():
        findings.append({
            "title": "Geometry Dash save data is synced by OneDrive",
            "detail": f"Save data found at:\n{save_path}\n\nOneDrive is actively syncing your save files (CCGameManager.dat). Ensure files are set to 'Always keep on this device' so backup operations don't freeze.",
            "steps": "Right-click the GeometryDash save folder in File Explorer and select 'Always keep on this device'.",
        })

    # Check multiple installations
    if hasattr(manager, "find_all_gd_installations"):
        try:
            all_installs = manager.find_all_gd_installations()
            if len(all_installs) > 1:
                install_lines = []
                for inst in all_installs:
                    is_active = (game_path and os.path.abspath(inst["path"]).casefold() == os.path.abspath(game_path).casefold())
                    active_mark = " (ACTIVE IN GEODESYNC)" if is_active else ""
                    install_lines.append(f"• [{inst['source']}] {inst['path']} — GD {inst['version']}{active_mark}")
                findings.append({
                    "title": f"Multiple Geometry Dash installations found ({len(all_installs)} detected)",
                    "detail": "GeodeSync detected multiple copies of Geometry Dash on your PC:\n\n" + "\n".join(install_lines),
                    "steps": "If GeodeSync shows an unexpected version (like v2.2074 or custom build), you may have multiple copies on your drive and GeodeSync is looking at a different one than you play! Click '📁 Game Folder' in GeodeSync to switch to your official Steam installation.",
                })
        except Exception:
            pass

    if recovery_error:
        findings.append({
            "title": "An interrupted game repair needs attention",
            "detail": str(recovery_error),
            "steps": "Stop here—do not start another version switch. Export a support report and send it with this message so the recovery files can be reviewed safely.",
        })
    if findings:
        return findings
    return [{
        "title": "No obvious setup problem found",
        "detail": "The Steam and game folders passed GeodeSync’s basic checks. This does not rule out a problem inside Steam, Geode, or a mod.",
        "steps": "Paste the exact error above and choose Explain Error. If the game fails only with Geode, try disabling the most recently installed mod. Export a support report if you still need help.",
    }]

"""Locating the game install, versions, process control, save/crash directories. (GDManager mixin, moved verbatim from v2.8.0 main.py)."""

import os
import re
import json
import time
import subprocess
import plistlib
from geodesync.core.game_constants import SIZES_22081, SIZE_2209
from geodesync.platform.process_manager import IS_LINUX, IS_MAC, IS_WIN, is_win_process_running, safe_run_command
from geodesync.platform.steam import APP_ID, discover_linux_steam_roots, discover_steam_game_folders, find_macos_game_app, is_steam_library_game_path
from geodesync.platform.system import find_linux_geometry_dash_pids
from geodesync.core.theme import UI



class GameMixin:
    """Locating the game install, versions, process control, save/crash directories."""

    def find_all_gd_installations(self):
        """Discovers all Geometry Dash game folders across Steam, OneDrive, Desktop, and common game drives."""
        results = []
        seen = set()

        def add_candidate(folder, source_type):
            if not folder or not os.path.isdir(folder):
                return
            real_path = os.path.abspath(folder)
            norm_key = real_path.casefold()
            if norm_key in seen:
                return

            exe = os.path.join(real_path, "GeometryDash.exe")
            app = find_macos_game_app(real_path) if IS_MAC else None
            if not os.path.isfile(exe) and not app:
                return

            seen.add(norm_key)
            is_steam = is_steam_library_game_path(real_path)
            is_onedrive = "onedrive" in real_path.casefold()

            ver = "Unknown"
            if IS_WIN and os.path.isfile(exe):
                try:
                    size = os.path.getsize(exe)
                    if size in SIZES_22081:
                        ver = "2.2081"
                    elif size == SIZE_2209:
                        ver = "2.209"
                    elif size == 7578624:
                        ver = "2.113"
                    else:
                        ver = f"Custom ({round(size / (1024*1024), 1)} MB)"
                except Exception:
                    pass

            results.append({
                "path": real_path,
                "name": os.path.basename(real_path),
                "is_steam": is_steam,
                "is_onedrive": is_onedrive,
                "source": "Steam" if is_steam else ("OneDrive" if is_onedrive else source_type),
                "version": ver,
                "exe": exe if os.path.isfile(exe) else (app or "")
            })

        # 1. Steam paths & library folders
        if self.steam_path:
            common_dir = os.path.join(self.steam_path, "steamapps", "common")
            if os.path.isdir(common_dir):
                try:
                    for entry in os.listdir(common_dir):
                        add_candidate(os.path.join(common_dir, entry), "Steam")
                except Exception:
                    pass

            vdf_path = os.path.join(self.steam_path, "steamapps", "libraryfolders.vdf")
            if os.path.exists(vdf_path):
                try:
                    with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
                        matches = re.findall(r'"path"\s+"([^"]+)"', f.read(), re.IGNORECASE)
                    for lib_dir in matches:
                        sub_common = os.path.join(lib_dir.replace(r"\\", "\\"), "steamapps", "common")
                        if os.path.isdir(sub_common):
                            for entry in os.listdir(sub_common):
                                add_candidate(os.path.join(sub_common, entry), "Steam")
                except Exception:
                    pass

        # 2. OneDrive roots
        onedrive_roots = []
        for env_var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
            val = os.environ.get(env_var)
            if val and os.path.isdir(val) and val not in onedrive_roots:
                onedrive_roots.append(val)
        user_home = os.path.expanduser("~")
        for candidate_name in ("OneDrive", "OneDrive - Personal"):
            p = os.path.join(user_home, candidate_name)
            if os.path.isdir(p) and p not in onedrive_roots:
                onedrive_roots.append(p)

        for od in onedrive_roots:
            for sub in ("", "Desktop", "Documents", "Games", "GeometryDash", "Geometry Dash"):
                target = os.path.join(od, sub) if sub else od
                if os.path.isdir(target):
                    add_candidate(target, "OneDrive")
                    try:
                        for entry in os.listdir(target):
                            subpath = os.path.join(target, entry)
                            if os.path.isdir(subpath):
                                add_candidate(subpath, "OneDrive")
                    except Exception:
                        pass

        # 3. Standard user folders
        for folder_name in ("Desktop", "Documents", "Downloads", "Games"):
            base = os.path.join(user_home, folder_name)
            if os.path.isdir(base):
                for name in ("Geometry Dash", "GeometryDash", "GD", "GD 2.2"):
                    add_candidate(os.path.join(base, name), "Local")
                try:
                    for entry in os.listdir(base):
                        if "geometry" in entry.lower() or "gd" in entry.lower():
                            add_candidate(os.path.join(base, entry), "Local")
                except Exception:
                    pass

        # 4. Common root drives
        for drive in ("C:\\", "D:\\", "E:\\"):
            for root_name in ("Games", "GeometryDash", "Geometry Dash", "GD"):
                add_candidate(os.path.join(drive, root_name), "Local")

        return results

    def detect_gd_path(self):
        if IS_LINUX:
            for candidate in discover_steam_game_folders(discover_linux_steam_roots()):
                if os.path.isfile(os.path.join(candidate, "GeometryDash.exe")):
                    return candidate
            return None

        # 1. Check Steam standard path
        if self.steam_path:
            default_gd = os.path.join(self.steam_path, "steamapps", "common", "Geometry Dash")
            if os.path.exists(default_gd):
                return default_gd

            # Scan any folder in steamapps/common that has GeometryDash.exe
            common_dir = os.path.join(self.steam_path, "steamapps", "common")
            if os.path.isdir(common_dir):
                try:
                    for entry in os.listdir(common_dir):
                        full = os.path.join(common_dir, entry)
                        if os.path.isdir(full) and (
                            os.path.isfile(os.path.join(full, "GeometryDash.exe")) or
                            (IS_MAC and find_macos_game_app(full))
                        ):
                            return full
                except Exception:
                    pass

        # 2. Check all libraries in libraryfolders.vdf
        if self.steam_path:
            vdf_path = os.path.join(self.steam_path, "steamapps", "libraryfolders.vdf")
            if os.path.exists(vdf_path):
                try:
                    with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    matches = re.findall(r'"path"\s+"([^"]+)"', content, re.IGNORECASE)
                    for lib_dir in matches:
                        clean_dir = lib_dir.replace(r"\\", "\\")
                        candidate = os.path.join(clean_dir, "steamapps", "common", "Geometry Dash")
                        if os.path.exists(candidate):
                            return candidate
                        sub_common = os.path.join(clean_dir, "steamapps", "common")
                        if os.path.isdir(sub_common):
                            for entry in os.listdir(sub_common):
                                full = os.path.join(sub_common, entry)
                                if os.path.isdir(full) and (
                                    os.path.isfile(os.path.join(full, "GeometryDash.exe")) or
                                    (IS_MAC and find_macos_game_app(full))
                                ):
                                    return full
                except Exception:
                    pass

        # 3. macOS default
        if IS_MAC:
            mac_default = os.path.expanduser("~/Library/Application Support/Steam/steamapps/common/Geometry Dash")
            if os.path.exists(mac_default):
                return mac_default

        # 4. Fallback search: OneDrive, Desktop, Documents, Games
        for inst in self.find_all_gd_installations():
            if inst.get("path") and os.path.isdir(inst["path"]):
                return inst["path"]

        return None

    def get_save_data_dir(self):
        # 1. User manual override from settings
        custom = getattr(self, "custom_save_path", None)
        if custom and os.path.isdir(custom):
            return custom

        if IS_MAC:
            mac_save = os.path.expanduser("~/Library/Application Support/GeometryDash")
            if os.path.exists(mac_save):
                return mac_save
            return mac_save

        if IS_LINUX:
            candidates = []
            if self.gd_path:
                game_steamapps = os.path.dirname(os.path.dirname(os.path.abspath(self.gd_path)))
                candidates.append(os.path.join(game_steamapps, "compatdata", APP_ID, "pfx", "drive_c", "users", "steamuser", "AppData", "Local", "GeometryDash"))
            for root in discover_linux_steam_roots():
                candidates.append(os.path.join(root, "steamapps", "compatdata", APP_ID, "pfx", "drive_c", "users", "steamuser", "AppData", "Local", "GeometryDash"))
            for c in candidates:
                if os.path.exists(c):
                    return c
            return candidates[0] if candidates else None

        # 2. Windows candidate search (AppData, OneDrive, Roaming, Saved Games, Documents, Portable)
        candidates = []

        # Portable saves inside or next to game folder take precedence if game folder is portable
        if self.gd_path and os.path.isdir(self.gd_path):
            candidates.append(os.path.join(self.gd_path, "save"))
            candidates.append(os.path.join(self.gd_path, "saves"))
            candidates.append(os.path.join(self.gd_path, "AppData", "Local", "GeometryDash"))
            if not is_steam_library_game_path(self.gd_path):
                candidates.append(self.gd_path)

        appdata = os.environ.get("LOCALAPPDATA")
        if appdata:
            candidates.append(os.path.join(appdata, "GeometryDash"))

        onedrive_roots = []
        for env_var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
            val = os.environ.get(env_var)
            if val and os.path.isdir(val) and val not in onedrive_roots:
                onedrive_roots.append(val)
        user_home = os.path.expanduser("~")
        for candidate_name in ("OneDrive", "OneDrive - Personal"):
            p = os.path.join(user_home, candidate_name)
            if os.path.isdir(p) and p not in onedrive_roots:
                onedrive_roots.append(p)

        for od in onedrive_roots:
            candidates.append(os.path.join(od, "GeometryDash"))
            candidates.append(os.path.join(od, "Documents", "GeometryDash"))
            candidates.append(os.path.join(od, "AppData", "Local", "GeometryDash"))
            candidates.append(os.path.join(od, "Desktop", "GeometryDash"))

        roaming = os.environ.get("APPDATA")
        if roaming:
            candidates.append(os.path.join(roaming, "GeometryDash"))
        candidates.append(os.path.join(user_home, "Saved Games", "GeometryDash"))
        candidates.append(os.path.join(user_home, "Documents", "GeometryDash"))

        # Prioritize whichever directory actually contains Geometry Dash save files (.dat)
        for c in candidates:
            if os.path.isdir(c):
                try:
                    for f in os.listdir(c):
                        if f.lower().startswith("cc") and f.lower().endswith(".dat"):
                            return c
                except Exception:
                    pass

        # If none contain .dat files yet, return the first directory that exists
        for c in candidates:
            if os.path.isdir(c):
                return c

        if appdata:
            return os.path.join(appdata, "GeometryDash")
        return None

    def get_crashlogs_dir(self):
        candidates = []
        if IS_MAC:
            candidates.append(os.path.expanduser("~/Library/Application Support/GeometryDash/geode/crashlogs"))
        if self.gd_path:
            candidates.append(os.path.join(self.gd_path, "geode", "crashlogs"))
        save_dir = self.get_save_data_dir()
        if save_dir:
            candidates.append(os.path.join(save_dir, "geode", "crashlogs"))
        for c in candidates:
            if os.path.exists(c):
                return c
        return candidates[0] if candidates else None

    def get_gd_version_info(self):
        if not self.gd_path:
            return "Not Installed", UI["red"]

        if IS_MAC:
            app_path = os.path.join(self.gd_path, "Geometry Dash.app")
            if not os.path.exists(app_path):
                app_path = os.path.join(self.gd_path, "GeometryDash.app")
            if not os.path.exists(app_path):
                return "Missing Geometry Dash.app", UI["red"]
            plist_path = os.path.join(app_path, "Contents", "Info.plist")
            if os.path.exists(plist_path):
                try:
                    import plistlib
                    with open(plist_path, "rb") as fp:
                        pl = plistlib.load(fp)
                    ver = str(pl.get("CFBundleShortVersionString") or pl.get("CFBundleVersion") or "")
                    if "2.2081" in ver or ver == "2.2081":
                        return f"{self.target_gd_version} (Geode Compatible)", UI["lime"]
                    elif ver:
                        return f"{ver}", "#60a5fa"
                except Exception:
                    pass
            return f"{self.target_gd_version} (macOS)", UI["lime"]

        exe_path = os.path.join(self.gd_path, "GeometryDash.exe")
        if not os.path.exists(exe_path):
            return "Missing Executable", UI["red"]

        try:
            size = os.path.getsize(exe_path)
        except Exception:
            return "Inaccessible", UI["red"]

        if size in SIZES_22081:
            return "2.2081 (Geode Compatible)", UI["lime"]
        elif size == 7578624:
            return "2.113 (Classic 2.11 Legacy)", UI["lilac"]
        elif size == SIZE_2209:
            return "2.209 (Incompatible with Geode)", UI["red"]
        mb = round(size / (1024 * 1024), 2)
        return f"Custom Build ({mb} MB)", UI["muted"]

    def is_current_gd_22081(self):
        if not self.gd_path:
            return False
        if IS_MAC:
            if self.target_gd_version != "2.2081":
                return False
            app_path = os.path.join(self.gd_path, "Geometry Dash.app")
            if not os.path.exists(app_path):
                app_path = os.path.join(self.gd_path, "GeometryDash.app")
            if not os.path.exists(app_path):
                return False
            plist_path = os.path.join(app_path, "Contents", "Info.plist")
            if os.path.exists(plist_path):
                try:
                    import plistlib
                    with open(plist_path, "rb") as fp:
                        pl = plistlib.load(fp)
                    ver = str(pl.get("CFBundleShortVersionString") or pl.get("CFBundleVersion") or "")
                    if "2.209" in ver:
                        return False
                    if "2.2081" in ver:
                        return True
                except Exception:
                    pass
            return os.path.exists(app_path)

        exe = os.path.join(self.gd_path, "GeometryDash.exe")
        if os.path.exists(exe):
            try:
                return os.path.getsize(exe) in SIZES_22081
            except Exception:
                return False
        return False

    def is_gd_process_running(self):
        if IS_MAC:
            try:
                output = subprocess.check_output(["pgrep", "-f", "Geometry Dash"]).decode()
                return bool(output.strip())
            except subprocess.CalledProcessError:
                return False
            except Exception:
                return False

        if IS_WIN:
            try:
                import ctypes
                hwnd = ctypes.windll.user32.FindWindowW(None, "Geometry Dash")
                if hwnd:
                    return True
            except Exception:
                pass
            return is_win_process_running("geometrydash.exe")

        try:
            return bool(find_linux_geometry_dash_pids())
        except Exception:
            return False

    def close_gd_process(self):
        if IS_MAC:
            try:
                subprocess.run(["killall", "Geometry Dash"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(1)
                return True
            except Exception:
                return False

        if IS_WIN:
            try:
                safe_run_command(["taskkill", "/F", "/IM", "GeometryDash.exe"])
                time.sleep(1)
                return True
            except Exception:
                return False

        if IS_LINUX:
            pids = find_linux_geometry_dash_pids()
            if not pids:
                return True
            for pid in pids:
                try:
                    os.kill(pid, 15)
                except ProcessLookupError:
                    continue
                except OSError:
                    return False
            deadline = time.time() + 8
            while time.time() < deadline:
                if not find_linux_geometry_dash_pids():
                    return True
                time.sleep(0.25)
            return False

        try:
            subprocess.run(["pkill", "-TERM", "-x", "GeometryDash"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)
            return True
        except Exception:
            return False

    def get_keybind_map(self, custom_search_dirs=None):
        """
        Inspects all Geode mod configs and local appdata saved settings to extract
        assigned hotkeys, detecting any potential keybind collisions.
        """
        GLFW_KEYS = {
            32: "Space", 39: "'", 44: ",", 45: "-", 46: ".", 47: "/",
            48: "0", 49: "1", 50: "2", 51: "3", 52: "4", 53: "5", 54: "6", 55: "7", 56: "8", 57: "9",
            59: ";", 61: "=", 65: "A", 66: "B", 67: "C", 68: "D", 69: "E", 70: "F", 71: "G",
            72: "H", 73: "I", 74: "J", 75: "K", 76: "L", 77: "M", 78: "N", 79: "O", 80: "P",
            81: "Q", 82: "R", 83: "S", 84: "T", 85: "U", 86: "V", 87: "W", 88: "X", 89: "Y", 90: "Z",
            256: "Escape", 257: "Enter", 258: "Tab", 259: "Backspace", 260: "Insert", 261: "Delete",
            262: "Right", 263: "Left", 264: "Down", 265: "Up", 290: "F1", 291: "F2", 292: "F3",
            293: "F4", 294: "F5", 295: "F6", 296: "F7", 297: "F8", 298: "F9", 299: "F10", 300: "F11", 301: "F12"
        }

        key_map = {}
        search_dirs = []

        if custom_search_dirs is not None:
            search_dirs = list(custom_search_dirs)
        else:
            local_gd = os.path.expandvars("%LOCALAPPDATA%\\GeometryDash\\geode\\mods") if IS_WIN else None
            if local_gd and os.path.isdir(local_gd):
                search_dirs.append(local_gd)

            if self.gd_path:
                g_cfg = os.path.join(self.gd_path, "geode", "config")
                if os.path.isdir(g_cfg):
                    search_dirs.append(g_cfg)

        for base_dir in search_dirs:
            for root, dirs, files in os.walk(base_dir):
                for f in files:
                    if f in ("settings.json", "saved.json", "config.json"):
                        p = os.path.join(root, f)
                        mod_id = os.path.basename(os.path.dirname(p))
                        try:
                            with open(p, "r", encoding="utf-8", errors="ignore") as fp:
                                data = json.load(fp)

                            def extract(obj, prefix=""):
                                if isinstance(obj, dict):
                                    if "key" in obj and isinstance(obj["key"], int) and obj["key"] > 0:
                                        k_code = obj["key"]
                                        k_name = GLFW_KEYS.get(k_code, f"Key {k_code}")
                                        mods = obj.get("modifiers", 0)
                                        mod_suffix = ""
                                        if mods & 1: mod_suffix += "+Shift"
                                        if mods & 2: mod_suffix += "+Ctrl"
                                        if mods & 4: mod_suffix += "+Alt"
                                        full_k = k_name + mod_suffix
                                        key_map.setdefault(full_k, []).append({"mod": mod_id, "action": prefix})
                                    else:
                                        for k, v in obj.items():
                                            extract(v, f"{prefix}.{k}" if prefix else k)
                                elif isinstance(obj, list):
                                    for item in obj:
                                        extract(item, prefix)

                            extract(data)
                        except Exception:
                            pass

        conflicts = {}
        normal = {}
        for k, v in key_map.items():
            distinct_mods = {item["mod"] for item in v}
            if len(distinct_mods) > 1:
                conflicts[k] = v
            else:
                normal[k] = v

        return {"conflicts": conflicts, "all_keys": key_map}

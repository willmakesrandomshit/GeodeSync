"""Steam discovery, depot/manifest locking and Steam process control. (GDManager mixin, moved verbatim from v2.8.0 main.py)."""

import os
import shutil
import stat
import time
import subprocess
from geodesync.core.config import DEPOT_ID
from geodesync.core.game_constants import KNOWN_VERSIONS, SIZES_22081
from geodesync.platform.process_manager import IS_LINUX, IS_MAC, IS_WIN, is_win_process_running, safe_check_output
from geodesync.platform.steam import APP_ID, discover_linux_steam_roots, find_macos_game_app, validate_macos_game_app
from geodesync.platform.system import open_url_or_path

if IS_WIN:
    import winreg
    import winsound
else:
    winreg = None
    winsound = None


class SteamMixin:
    """Steam discovery, depot/manifest locking and Steam process control."""

    def detect_steam_path(self):
        if IS_MAC:
            candidates = [
                os.path.expanduser("~/Library/Application Support/Steam"),
                "/Applications/Steam.app"
            ]
            for c in candidates:
                if os.path.exists(c):
                    return c
            return os.path.expanduser("~/Library/Application Support/Steam")

        if IS_LINUX:
            roots = discover_linux_steam_roots()
            return roots[0] if roots else None

        if IS_WIN and winreg:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
                    val, _ = winreg.QueryValueEx(key, "SteamPath")
                    if os.path.exists(val):
                        return os.path.abspath(val)
            except Exception:
                pass

        default = r"C:\Program Files (x86)\Steam"
        if os.path.exists(default):
            return default
        return None

    def get_steam_exe(self):
        if IS_MAC:
            candidates = [
                "/Applications/Steam.app/Contents/MacOS/steam_osx",
                os.path.expanduser("~/Applications/Steam.app/Contents/MacOS/steam_osx"),
                "/Applications/Steam.app"
            ]
            for c in candidates:
                if os.path.exists(c):
                    return c
            return "/Applications/Steam.app"

        if IS_LINUX:
            candidates = [
                shutil.which("steam"),
                "/usr/bin/steam",
                os.path.expanduser("~/.local/share/Steam/steam.sh"),
            ]
            for c in candidates:
                if c and os.path.exists(c):
                    return c
            if shutil.which("flatpak") and os.path.exists(os.path.expanduser("~/.var/app/com.valvesoftware.Steam")):
                return "flatpak:com.valvesoftware.Steam"
            return "steam"

        if self.steam_path:
            exe = os.path.join(self.steam_path, "steam.exe")
            if os.path.exists(exe):
                return exe
        return None

    def is_steam_running(self):
        if IS_MAC:
            try:
                output = subprocess.check_output(["pgrep", "-xi", "steam"]).decode()
                return bool(output.strip())
            except subprocess.CalledProcessError:
                return False
            except Exception:
                return True

        if IS_WIN:
            try:
                output = safe_check_output(["tasklist", "/FI", "IMAGENAME eq steam.exe", "/NH"])
                return "steam.exe" in output.lower()
            except Exception:
                return True

        try:
            output = subprocess.check_output(["pgrep", "-xi", "steam"]).decode()
            return bool(output.strip())
        except Exception:
            return True

    def get_manifest_path(self):
        if self.gd_path:
            parent = os.path.dirname(os.path.dirname(self.gd_path))
            m_path = os.path.join(parent, f"appmanifest_{APP_ID}.acf")
            if os.path.exists(m_path):
                return m_path

        if self.steam_path:
            m_path = os.path.join(self.steam_path, "steamapps", f"appmanifest_{APP_ID}.acf")
            if os.path.exists(m_path):
                return m_path
        return None

    def get_depot_path(self):
        if self.steam_path:
            if IS_MAC:
                # Modern macOS Steam keeps console-downloaded depots inside
                # Steam.AppBundle. A stale directory under the outer Steam
                # support folder must not shadow the location Steam actually
                # writes to.
                steam_root = os.path.expanduser("~/Library/Application Support/Steam")
                mac_depot = "322172"
                candidates = [
                    os.path.join(steam_root, "Steam.AppBundle", "Steam", "Contents", "MacOS", "steamapps", "content", f"app_{APP_ID}", f"depot_{mac_depot}"),
                    os.path.join(steam_root, "steamapps", "content", f"app_{APP_ID}", f"depot_{mac_depot}"),
                ]
                if self.steam_path != "/Applications/Steam.app":
                    candidates.append(os.path.join(self.steam_path, "steamapps", "content", f"app_{APP_ID}", f"depot_{mac_depot}"))
                candidates = list(dict.fromkeys(os.path.abspath(path) for path in candidates))
                # Reuse a cache only when its app bundle validates. If every
                # existing candidate is damaged, return Steam's canonical
                # destination so the next download is checked at the path
                # Steam actually uses.
                for candidate in candidates:
                    app_path = find_macos_game_app(candidate)
                    if app_path and validate_macos_game_app(app_path) is None:
                        return candidate
                return candidates[0]
            d_path = os.path.join(self.steam_path, "steamapps", "content", f"app_{APP_ID}", f"depot_{DEPOT_ID}")
            return d_path
        return None

    def get_depot_current_size(self):
        d_path = self.get_depot_path()
        if not d_path or not os.path.exists(d_path):
            return 0
        total = 0
        try:
            for root, dirs, files in os.walk(d_path):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        total += os.path.getsize(fp)
                    except Exception:
                        pass
        except Exception:
            pass
        return total

    def get_steam_console_log(self):
        if self.steam_path:
            log_p = os.path.join(self.steam_path, "logs", "console_log.txt")
            if os.path.exists(log_p):
                return log_p
        return None

    def is_steam_running(self):
        if IS_WIN:
            return is_win_process_running("steam.exe")
        if IS_MAC:
            try:
                out = subprocess.check_output(["pgrep", "-f", "Steam"]).decode()
                return bool(out.strip())
            except Exception:
                return False
        try:
            out = subprocess.check_output(["pgrep", "-x", "steam"]).decode()
            return bool(out.strip())
        except Exception:
            return False

    def get_steam_exe_path(self):
        if not IS_WIN:
            return None
        try:
            import winreg
            for subkey, val_name in [
                (r"Software\Valve\Steam", "SteamExe"),
                (r"Software\Valve\Steam", "SteamPath"),
            ]:
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey) as key:
                        val, _ = winreg.QueryValueEx(key, val_name)
                        if val:
                            val = val.replace("/", "\\")
                            if val.lower().endswith(".exe") and os.path.isfile(val):
                                return val
                            cand = os.path.join(val, "steam.exe")
                            if os.path.isfile(cand):
                                return cand
                except Exception:
                    pass
        except Exception:
            pass
        for cand in [r"C:\Program Files (x86)\Steam\steam.exe", r"C:\Program Files\Steam\steam.exe"]:
            if os.path.isfile(cand):
                return cand
        return None

    def ensure_steam_running(self, timeout=14):
        """Ensure Steam is running before launching GD; starts Steam if closed and waits for initialization."""
        if self.is_steam_running():
            return True
        steam_exe = self.get_steam_exe_path()
        if steam_exe and os.path.isfile(steam_exe):
            try:
                subprocess.Popen([steam_exe, "-silent"])
            except Exception:
                open_url_or_path("steam://")
        else:
            open_url_or_path("steam://")

        t0 = time.time()
        while time.time() - t0 < timeout:
            time.sleep(0.4)
            if self.is_steam_running():
                time.sleep(1.2)  # Allow Steam IPC pipes to spin up
                return True
        return False

    def is_manifest_locked(self):
        if not self.manifest_path or not os.path.exists(self.manifest_path):
            return False
        try:
            if IS_MAC:
                st = os.stat(self.manifest_path)
                if hasattr(st, "st_flags") and (st.st_flags & stat.UF_IMMUTABLE):
                    return True
                return not bool(st.st_mode & stat.S_IWRITE)
            mode = os.stat(self.manifest_path).st_mode
            return not bool(mode & stat.S_IWRITE)
        except Exception:
            return False

    def set_manifest_locked(self, lock: bool):
        if not self.manifest_path or not os.path.exists(self.manifest_path):
            raise FileNotFoundError("appmanifest_322170.acf not found!")

        for attempt in range(5):
            try:
                if IS_MAC:
                    if lock:
                        os.chmod(self.manifest_path, stat.S_IREAD)
                        try:
                            subprocess.run(
                                ["chflags", "uchg", self.manifest_path],
                                check=True,
                                capture_output=True,
                                text=True,
                                timeout=10,
                            )
                        except Exception:
                            # Do not leave the manifest read-only if the immutable
                            # flag could not be applied successfully.
                            os.chmod(self.manifest_path, stat.S_IREAD | stat.S_IWRITE)
                            raise
                    else:
                        subprocess.run(
                            ["chflags", "nouchg", self.manifest_path],
                            check=True,
                            capture_output=True,
                            text=True,
                            timeout=10,
                        )
                        os.chmod(self.manifest_path, stat.S_IWRITE | stat.S_IREAD)
                    if self.is_manifest_locked() is not lock:
                        raise OSError("Steam appmanifest lock state did not change as requested.")
                    return
                else:
                    if lock:
                        os.chmod(self.manifest_path, stat.S_IREAD)
                    else:
                        os.chmod(self.manifest_path, stat.S_IWRITE | stat.S_IREAD)
                    return
            except PermissionError:
                time.sleep(0.3)
            except Exception as e:
                if attempt == 4:
                    raise e
                time.sleep(0.3)

    def has_downloaded_depot(self):
        d_path = self.get_depot_path()
        if d_path and os.path.exists(d_path):
            if IS_MAC:
                app_path = find_macos_game_app(d_path)
                # Steam can leave an app-bundle-shaped directory behind after
                # an interrupted depot download. Existence alone is not proof
                # that the cached depot is safe to install. In particular,
                # plistlib raises ExpatError for truncated or concatenated
                # Info.plist data; validate it here so a bad cache is retried
                # through Steam instead of reaching the replacement step.
                return app_path is not None and validate_macos_game_app(app_path) is None
            exe = os.path.join(d_path, "GeometryDash.exe")
            try:
                target_meta = next(
                    (meta for meta in KNOWN_VERSIONS.values()
                     if str(meta.get("manifest")) == str(self.target_manifest)),
                    {},
                )
                expected_size = target_meta.get("sizes") or target_meta.get("size")
                if str(self.target_manifest) == "3816559102876907245":
                    expected_size = SIZES_22081

                if not os.path.exists(exe):
                    return False
                actual_size = os.path.getsize(exe)
                if expected_size is not None:
                    if isinstance(expected_size, (tuple, list, set)):
                        if actual_size not in expected_size:
                            return False
                    elif actual_size != expected_size:
                        return False
                resources_dir = os.path.join(d_path, "Resources")
                if not os.path.isdir(resources_dir):
                    return False
                for kf in ("Dash.mp3", "GJ_GameSheet-hd.png"):
                    kf_path = os.path.join(resources_dir, kf)
                    if not os.path.isfile(kf_path) or os.path.getsize(kf_path) == 0:
                        return False
                if self.get_depot_current_size() < 150 * 1024 * 1024:
                    return False
                return True
            except Exception:
                return False
        return False

    def is_depot_locked(self):
        d_path = self.get_depot_path()
        if not d_path or not os.path.isdir(d_path):
            return False
        test_files = [os.path.join(d_path, "GeometryDash.exe")]
        res_dir = os.path.join(d_path, "Resources")
        if os.path.isdir(res_dir):
            for f in ("Dash.mp3", "Deadlocked.mp3", "GJ_GameSheet-hd.png"):
                p = os.path.join(res_dir, f)
                if os.path.isfile(p):
                    test_files.append(p)
        for p in test_files:
            try:
                with open(p, "rb") as f:
                    f.read(1024)
            except OSError as e:
                if getattr(e, "winerror", None) in (32, 33, 5):
                    return True
            except Exception:
                pass
        return False

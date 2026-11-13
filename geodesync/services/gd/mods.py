"""Geode and mod management: install detection, mods, incompatibilities, updates, the Geode store. (GDManager mixin, moved verbatim from v2.8.0 main.py)."""

import os
import re
import json
import shutil
import urllib.request
import zipfile
from geodesync.core.config import APP_VERSION
from geodesync.platform.process_manager import IS_MAC, IS_WIN
from geodesync.platform.steam import find_macos_game_app
from geodesync.services.geode_install import is_safe_geode_mod_id



class ModsMixin:
    """Geode and mod management: install detection, mods, incompatibilities, updates, the Geode store."""

    def is_geode_installed(self):
        if not self.gd_path or not os.path.exists(self.gd_path):
            return False
        if IS_MAC:
            app_dir = find_macos_game_app(self.gd_path)
            mac_geode_dir = os.path.expanduser("~/Library/Application Support/GeometryDash/geode")
            if app_dir:
                bundle = os.path.join(app_dir, "Contents")
                loader_candidates = (
                    os.path.join(bundle, "Frameworks", "Geode.dylib"),
                    os.path.join(bundle, "MacOS", "Geode.dylib"),
                    os.path.join(bundle, "Frameworks", "Geode.framework", "Geode"),
                )
                if any(os.path.isfile(path) for path in loader_candidates):
                    return True
            # A data directory alone can survive an uninstall, so require
            # evidence that Geode has actually started before treating it as
            # an installed loader.
            return self._has_geode_startup_log(mac_geode_dir)

        # Geode's loader DLL is the authoritative Windows/Proton marker. Some
        # valid installs do not have the legacy XInput proxy (or use a
        # different proxy name), so requiring that second file caused false
        # negatives. Ignore a leftover data folder unless it has a Geode log.
        game_path = os.path.abspath(self.gd_path)
        loader_candidates = (
            os.path.join(game_path, "Geode.dll"),
            os.path.join(game_path, "geode", "Geode.dll"),
        )
        if any(os.path.isfile(path) for path in loader_candidates):
            return True
        return self._has_geode_startup_log(os.path.join(game_path, "geode"))

    @staticmethod
    def _has_geode_startup_log(geode_dir):
        log_dir = os.path.join(geode_dir, "logs")
        if not os.path.isdir(log_dir):
            return False
        try:
            files = [
                os.path.join(log_dir, name)
                for name in os.listdir(log_dir)
                if name.lower().endswith(".log") and os.path.isfile(os.path.join(log_dir, name))
            ]
            if not files:
                return False
            latest = max(files, key=os.path.getmtime)
            with open(latest, "r", encoding="utf-8", errors="ignore") as stream:
                return any(re.search(r"\bRunning Geode\s+v?\d+\.\d+\.\d+", line, re.IGNORECASE) for line in stream)
        except OSError:
            return False

    def get_installed_geode_version(self):
        if not self.gd_path or not os.path.isdir(self.gd_path):
            return None

        # 1. Parse latest Geode log in geode/logs/
        log_dir = os.path.join(self.gd_path, "geode", "logs")
        if os.path.isdir(log_dir):
            try:
                files = [f for f in os.listdir(log_dir) if f.endswith(".log")]
                if files:
                    files.sort(key=lambda f: os.path.getmtime(os.path.join(log_dir, f)), reverse=True)
                    latest_log = os.path.join(log_dir, files[0])
                    with open(latest_log, "r", encoding="utf-8", errors="ignore") as stream:
                        for _ in range(35):
                            line = stream.readline()
                            if not line:
                                break
                            m = re.search(r"Running Geode (v\d+\.\d+\.\d+(?:-[\w.]+)?|[0-9]+\.[0-9]+\.[0-9]+)", line, re.IGNORECASE)
                            if m:
                                ver = m.group(1)
                                if not ver.startswith("v"):
                                    ver = f"v{ver}"
                                return ver
            except Exception:
                pass

        # 2. Check PE version info on Windows (Geode.dll)
        if IS_WIN:
            geode_dll = os.path.join(self.gd_path, "Geode.dll")
            if os.path.isfile(geode_dll):
                try:
                    import ctypes
                    from ctypes import wintypes
                    size = ctypes.windll.version.GetFileVersionInfoSizeW(geode_dll, None)
                    if size > 0:
                        res = ctypes.create_string_buffer(size)
                        ctypes.windll.version.GetFileVersionInfoW(geode_dll, None, size, res)
                        p_val = wintypes.LPVOID()
                        u_len = wintypes.UINT()
                        if ctypes.windll.version.VerQueryValueW(res, r"\\", ctypes.byref(p_val), ctypes.byref(u_len)):
                            buf = ctypes.cast(p_val, ctypes.POINTER(wintypes.DWORD))
                            ms, ls = buf[2], buf[3]
                            major, minor, build = ms >> 16, ms & 0xFFFF, ls >> 16
                            if major > 0:
                                return f"v{major}.{minor}.{build}"
                except Exception:
                    pass

        # 3. Fallback: if Geode.dll / Geode.dylib / geode folder exists
        if self.is_geode_installed():
            return "v5.x"
        return None

    def get_installed_mods(self):
        if not self.gd_path:
            return []
        mods_dir = os.path.join(self.gd_path, "geode", "mods")
        if not os.path.isdir(mods_dir):
            return []
        results = []
        try:
            for item in sorted(os.listdir(mods_dir)):
                if item.endswith((".geode", ".disabled")):
                    is_enabled = item.endswith(".geode")
                    full = os.path.join(mods_dir, item)
                    name = item
                    version = "v1.0"
                    developer = "Unknown"
                    mod_id = item.replace(".geode.disabled", "").replace(".geode", "")
                    try:
                        with zipfile.ZipFile(full, "r") as zf:
                            if "mod.json" in zf.namelist():
                                try:
                                    meta = json.loads(zf.read("mod.json").decode("utf-8", errors="ignore"))
                                except Exception:
                                    meta = {}
                                if isinstance(meta, dict):
                                    name = meta.get("name", meta.get("id", mod_id))
                                    version = meta.get("version", "v1.0")
                                    dev = meta.get("developer") or meta.get("developers")
                                    if isinstance(dev, list):
                                        developer = ", ".join(dev)
                                    elif isinstance(dev, str):
                                        developer = str(dev)
                    except Exception:
                        pass
                    results.append({
                        "filename": item,
                        "mod_id": mod_id,
                        "id": mod_id,
                        "name": name,
                        "version": version,
                        "developer": developer,
                        "enabled": is_enabled,
                        "is_enabled": is_enabled,
                        "path": full,
                    })
        except Exception:
            pass
        return results

    def toggle_mod(self, filename, enable=None):
        if not self.gd_path:
            return False, "GD path not found"
        mods_dir = os.path.join(self.gd_path, "geode", "mods")
        src = os.path.join(mods_dir, filename)
        if not os.path.exists(src):
            return False, "Mod file not found"
        if filename.endswith(".geode") and enable in (False, None):
            dst = os.path.join(mods_dir, filename + ".disabled")
        elif filename.endswith(".disabled") and enable in (True, None):
            dst = os.path.join(mods_dir, filename[:-9])
        else:
            return False, "Invalid state"
        try:
            os.replace(src, dst)
            return True, os.path.basename(dst)
        except Exception as e:
            return False, str(e)

    def check_incompatible_mods(self):
        """
        Scans for known incompatible or broken mods that cause Windows DLL Loader
        'Entry Point Not Found' crashes (e.g. prevter.imageplus v1.1.1 calling
        loadRootSubDictFromCompressedFile which is missing in GD 2.2081).
        """
        if not self.gd_path:
            return []
        mods_dir = os.path.join(self.gd_path, "geode", "mods")
        if not os.path.isdir(mods_dir):
            return []

        issues = []
        ip_path = os.path.join(mods_dir, "prevter.imageplus.geode")
        if os.path.exists(ip_path):
            try:
                with zipfile.ZipFile(ip_path, "r") as zf:
                    if "mod.json" in zf.namelist():
                        try:
                            meta = json.loads(zf.read("mod.json").decode("utf-8", errors="ignore"))
                        except Exception:
                            meta = {}
                        if isinstance(meta, dict):
                            ver = str(meta.get("version", "")).lstrip("v")
                            # 1.1.1 calls loadRootSubDictFromCompressedFile which crashes GD 2.2081
                            if ver == "1.1.1":
                                issues.append({
                                    "id": "prevter.imageplus",
                                    "name": "ImagePlus",
                                    "version": "v" + ver,
                                    "issue": "Missing DLL Entry Point (?loadRootSubDictFromCompressedFile@DS_Dictionary@@QEAA_NPEBD@Z)",
                                    "recommended_version": "v1.1.0",
                                    "download_url": "https://api.geode-sdk.org/v1/mods/prevter.imageplus/versions/1.1.0/download",
                                    "file_path": ip_path
                                })
            except Exception:
                pass

        return issues

    def fix_incompatible_mod(self, issue):
        """
        Downloads the recommended stable release of a mod, replaces the broken .geode file,
        and purges the stale unzipped cache.
        """
        if not self.gd_path or not issue.get("download_url"):
            return False, "Invalid issue or missing download URL."
        if not is_safe_geode_mod_id(issue.get("id")):
            return False, "Invalid Geode mod identifier."
        try:
            req = urllib.request.Request(issue["download_url"], headers={"User-Agent": "GeodeSync-Client"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()

            file_path = issue["file_path"]
            with open(file_path, "wb") as f:
                f.write(data)

            # Purge unzipped cached DLL to ensure Windows loads the fresh binary
            unzipped_dir = os.path.join(self.gd_path, "geode", "unzipped", issue["id"])
            if os.path.exists(unzipped_dir):
                shutil.rmtree(unzipped_dir, ignore_errors=True)

            return True, f"Successfully installed tested {issue['recommended_version']} for {issue['name']}!"
        except Exception as e:
            return False, str(e)

    def check_outdated_mods(self, progress_callback=None):
        """
        Scans all installed .geode mods and checks for updates against the Geode SDK Index API
        (api.geode-sdk.org) using concurrent requests. Skips known broken versions (e.g. prevter.imageplus v1.1.1).
        """
        if not self.gd_path:
            return []
        mods_dir = os.path.join(self.gd_path, "geode", "mods")
        if not os.path.isdir(mods_dir):
            return []

        installed = []
        for f in os.listdir(mods_dir):
            if f.endswith(".geode"):
                fp = os.path.join(mods_dir, f)
                try:
                    with zipfile.ZipFile(fp, "r") as zf:
                        if "mod.json" in zf.namelist():
                            try:
                                meta = json.loads(zf.read("mod.json").decode("utf-8", errors="ignore"))
                            except Exception:
                                meta = {}
                            if isinstance(meta, dict):
                                mid = meta.get("id")
                                mver = str(meta.get("version", "")).lstrip("v")
                                mname = meta.get("name", mid)
                                if is_safe_geode_mod_id(mid) and mver:
                                    installed.append({
                                        "id": mid,
                                        "name": mname,
                                        "current_version": mver,
                                        "file_path": fp
                                    })
                except Exception:
                    pass

        if not installed:
            return []

        def parse_v(v_str):
            nums = []
            for part in str(v_str).lstrip("v").split("."):
                m = re.match(r"^(\d+)", part)
                nums.append(int(m.group(1)) if m else 0)
            while len(nums) < 3:
                nums.append(0)
            return tuple(nums[:3])

        outdated = []
        total = len(installed)
        completed = [0]

        def query_mod(item):
            mid = item["id"]
            if not is_safe_geode_mod_id(mid):
                completed[0] += 1
                if progress_callback:
                    try:
                        progress_callback(completed[0], total)
                    except Exception:
                        pass
                return None
            url = f"https://api.geode-sdk.org/v1/mods/{mid}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "GeodeSync-Client"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                payload = data.get("payload", {})
                versions = payload.get("versions", [])
                if versions:
                    for v_entry in versions:
                        v_str = str(v_entry.get("version", "")).lstrip("v")
                        # CRITICAL SAFEGUARD: Avoid imageplus 1.1.1 crash on GD 2.2081
                        if mid == "prevter.imageplus" and v_str == "1.1.1":
                            continue
                        cur_tuple = parse_v(item["current_version"])
                        latest_tuple = parse_v(v_str)
                        if latest_tuple > cur_tuple:
                            dl_url = v_entry.get("download", {}).get("url") or f"https://api.geode-sdk.org/v1/mods/{mid}/versions/{v_str}/download"
                            return {
                                "id": mid,
                                "name": item["name"],
                                "current_version": item["current_version"],
                                "latest_version": v_str,
                                "download_url": dl_url,
                                "file_path": item["file_path"],
                                "summary": payload.get("about", "") or payload.get("description", "")
                            }
                        break
            except Exception:
                pass
            finally:
                completed[0] += 1
                if progress_callback:
                    try:
                        progress_callback(completed[0], total)
                    except Exception:
                        pass
            return None

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            results = ex.map(query_mod, installed)
            for r in results:
                if r:
                    outdated.append(r)

        return outdated

    def update_single_mod(self, item):
        """
        Downloads the updated .geode file for a mod, writes it to geode/mods/,
        and purges its stale unzipped cache.
        """
        if not self.gd_path or not item.get("download_url"):
            return False, "Missing download URL."
        if not is_safe_geode_mod_id(item.get("id")):
            return False, "Invalid Geode mod identifier."
        try:
            req = urllib.request.Request(item["download_url"], headers={"User-Agent": "GeodeSync-Client"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = resp.read()

            file_path = item["file_path"]
            with open(file_path, "wb") as f:
                f.write(data)

            unzipped_dir = os.path.join(self.gd_path, "geode", "unzipped", item["id"])
            if os.path.exists(unzipped_dir):
                shutil.rmtree(unzipped_dir, ignore_errors=True)

            return True, f"Updated {item['name']} to v{item['latest_version']}!"
        except Exception as e:
            return False, str(e)

    def fetch_geode_store_mods(self, query="", page=1, per_page=20, sort="downloads"):
        """
        Fetches official Geode mods from https://api.geode-sdk.org/v1/mods.
        Returns (success: bool, mods_or_error: list|str).
        """
        import urllib.request
        import urllib.parse
        params = {"page": page, "per_page": per_page, "sort": sort}
        if query:
            params["query"] = query
        url = f"https://api.geode-sdk.org/v1/mods?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": f"GeodeSync/{APP_VERSION}"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            raw_mods = data.get("payload", {}).get("data", [])
            mods = []
            for item in raw_mods:
                v0 = item.get("versions", [{}])[0] if item.get("versions") else {}
                devs = item.get("developers", [])
                dev_names = ", ".join(d.get("display_name", d.get("username", "Unknown")) for d in devs) if devs else "Unknown"
                mods.append({
                    "id": item.get("id"),
                    "name": v0.get("name") or item.get("id"),
                    "version": v0.get("version", "v1.0.0"),
                    "description": v0.get("description") or item.get("about", ""),
                    "developer": dev_names,
                    "downloads": item.get("download_count", 0),
                    "tags": item.get("tags", []),
                    "download_link": v0.get("download_link", ""),
                })
            return True, mods
        except Exception as e:
            return False, str(e)

    def install_mod_from_store(self, mod_id, download_url=None, progress_callback=None):
        """
        Downloads and installs a .geode mod package from the Geode Mod Store into geode/mods.
        Validates zip integrity and mod.json.
        """
        if not self.gd_path:
            return False, "Could not locate Geometry Dash folder."
        mods_dir = os.path.join(self.gd_path, "geode", "mods")
        os.makedirs(mods_dir, exist_ok=True)

        if not download_url:
            ok, mods = self.fetch_geode_store_mods(query=mod_id, per_page=5)
            if not ok or not mods:
                return False, f"Could not find download URL for {mod_id}"
            matched = next((m for m in mods if m["id"].lower() == mod_id.lower()), mods[0])
            download_url = matched.get("download_link")
            if not download_url:
                return False, f"No download link found for {mod_id}"

        target_file = os.path.join(mods_dir, f"{mod_id}.geode")
        temp_file = target_file + ".part"

        import urllib.request
        req = urllib.request.Request(download_url, headers={"User-Agent": f"GeodeSync/{APP_VERSION}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp, open(temp_file, "wb") as f:
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 16384
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        try:
                            progress_callback(downloaded, total_size)
                        except Exception:
                            pass

            with zipfile.ZipFile(temp_file, "r") as zf:
                if "mod.json" not in zf.namelist():
                    os.remove(temp_file)
                    return False, "Downloaded file is corrupted or not a valid Geode mod (missing mod.json)."

            if os.path.exists(target_file):
                os.remove(target_file)
            os.rename(temp_file, target_file)
            return True, f"Installed {mod_id}.geode successfully!"
        except Exception as e:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
            return False, f"Failed to download/install {mod_id}: {e}"

    def apply_mod_preset(self, preset_type):
        """
        Applies a curated mod configuration:
        'tournament': enables FPS unlockers / trackers, disables visual clutter
        'globed': enables multiplayer
        'vanilla': disables all mods
        """
        if not self.gd_path:
            return False, "Could not locate Geometry Dash folder."
        mods_dir = os.path.join(self.gd_path, "geode", "mods")
        if not os.path.isdir(mods_dir):
            return False, "Geode mods directory not found."

        all_mods = self.get_installed_mods()
        if not all_mods:
            return True, "No mods installed to configure."

        updated = 0
        for m in all_mods:
            mod_id = m.get("mod_id") or m.get("id") or ""
            m_id = mod_id.lower()
            is_enabled = m.get("is_enabled", True)

            should_enable = True
            if preset_type == "vanilla":
                should_enable = False
            elif preset_type == "tournament":
                if "globed" in m_id or "imageplus" in m_id:
                    should_enable = False
            elif preset_type == "globed":
                if "globed" in m_id or "node-ids" in m_id:
                    should_enable = True

            if should_enable != is_enabled:
                curr_file = os.path.join(mods_dir, m.get("filename", f"{mod_id}.geode" if is_enabled else f"{mod_id}.geode.disabled"))
                new_file = os.path.join(mods_dir, f"{mod_id}.geode" if should_enable else f"{mod_id}.geode.disabled")
                if os.path.exists(curr_file):
                    try:
                        os.rename(curr_file, new_file)
                        updated += 1
                    except Exception:
                        pass

        return True, f"Preset '{preset_type}' applied ({updated} mods adjusted)."

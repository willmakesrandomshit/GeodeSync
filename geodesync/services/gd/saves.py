"""Backups, safety snapshots, bundles, save slots, bloat cleaning and salvage. (GDManager mixin, moved verbatim from v2.8.0 main.py)."""

import os
import re
import json
import shutil
import time
import tempfile
import zipfile
from datetime import datetime
from geodesync.core.compat import decode_geometry_dash_save, encode_geometry_dash_save
from geodesync.core.config import APP_VERSION
from geodesync.services.install_transaction import safe_copy_item



class SavesMixin:
    """Backups, safety snapshots, bundles, save slots, bloat cleaning and salvage."""

    def perform_silent_backup(self, prefix="Auto"):
        save_dir = self.get_save_data_dir()
        if not save_dir or not os.path.exists(save_dir):
            return 0
        backup_root = os.path.join(save_dir, "GeodeSync_Save_Backups")
        os.makedirs(backup_root, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
        target_folder = os.path.join(backup_root, f"{prefix}_{timestamp}")
        staging_folder = tempfile.mkdtemp(prefix=".geodesync-save-stage-", dir=backup_root)
        copied = 0
        try:
            for filename in os.listdir(save_dir):
                if filename.endswith((".dat", ".dat.bak")):
                    src_f = os.path.join(save_dir, filename)
                    dst_f = os.path.join(staging_folder, filename)
                    try:
                        safe_copy_item(src_f, dst_f)
                        copied += 1
                    except Exception:
                        try:
                            shutil.copy2(src_f, dst_f)
                            copied += 1
                        except Exception:
                            pass
            if copied:
                try:
                    os.replace(staging_folder, target_folder)
                except Exception:
                    shutil.copytree(staging_folder, target_folder, dirs_exist_ok=True)
                    shutil.rmtree(staging_folder, ignore_errors=True)
            else:
                shutil.rmtree(staging_folder, ignore_errors=True)
        except Exception:
            shutil.rmtree(staging_folder, ignore_errors=True)
            raise

        # Keep ten routine snapshots and five explicit pre-switch snapshots.
        retention = 5 if prefix == "BeforeSwitch" else 10
        matching = [os.path.join(backup_root, d) for d in os.listdir(backup_root) if d.startswith(f"{prefix}_")]
        matching.sort(key=os.path.getmtime, reverse=True)
        for old in matching[retention:]:
            try:
                shutil.rmtree(old)
            except Exception:
                pass
        return copied

    def get_player_stats(self):
        save_dir = self.get_save_data_dir()
        if not save_dir:
            return None
        gm_path = os.path.join(save_dir, "CCGameManager.dat")
        if not os.path.exists(gm_path):
            return None
        try:
            mtime = os.path.getmtime(gm_path)
            size = os.path.getsize(gm_path)
            if getattr(self, "_cached_player_stats", None) is not None and getattr(self, "_cached_stats_mtime", 0) == mtime and getattr(self, "_cached_stats_size", 0) == size:
                return self._cached_player_stats

            with open(gm_path, "rb") as f:
                raw = f.read()
            dec = decode_geometry_dash_save(raw).decode("utf-8", errors="ignore")

            name_m = re.search(r"<k>playerName</k><s>([^<]+)</s>", dec)
            player_name = name_m.group(1) if name_m else "Player"

            gs_idx = dec.find("GS_value")
            stats = {}
            if gs_idx != -1:
                chunk = dec[gs_idx : gs_idx + 4000]
                for m in re.finditer(r"<k>([0-9]+)</k><s>([0-9]+)</s>", chunk):
                    stats[int(m.group(1))] = int(m.group(2))

            result = {
                "name": player_name,
                "jumps": stats.get(1, 0),
                "attempts": stats.get(2, 0),
                "demons": stats.get(5, 0),
                "stars": stats.get(6, 0),
                "coins": stats.get(8, 0),
                "user_coins": stats.get(12, 0),
                "diamonds": stats.get(13, 0),
                "orbs": stats.get(14, 0),
                "moons": stats.get(28, 0),
            }
            self._cached_player_stats = result
            self._cached_stats_mtime = mtime
            self._cached_stats_size = size
            return result
        except Exception:
            return None

    def export_geodesync_bundle(self, dest_path, include_saves=True, include_mods=True, include_configs=True):
        """
        Packages saves, geode mods, configs into a compressed .geodesync portable archive.
        """
        try:
            save_dir = self.get_save_data_dir()
            mods_dir = os.path.join(self.gd_path, "geode", "mods") if self.gd_path else None
            config_dir = os.path.join(self.gd_path, "geode", "config") if self.gd_path else None

            stats = self.get_player_stats() or {}
            manifest = {
                "format_version": "1.0",
                "created_at": time.time(),
                "geodesync_version": APP_VERSION,
                "player_name": stats.get("name", "Player"),
                "stars": stats.get("stars", 0),
                "demons": stats.get("demons", 0),
                "contents": []
            }

            temp_dest = dest_path + ".tmp"
            with zipfile.ZipFile(temp_dest, "w", zipfile.ZIP_DEFLATED) as zf:
                if include_saves and save_dir and os.path.isdir(save_dir):
                    for save_name in ("CCGameManager.dat", "CCLocalLevels.dat", "CCGameManager2.dat", "CCLocalLevels2.dat"):
                        sp = os.path.join(save_dir, save_name)
                        if os.path.exists(sp):
                            zf.write(sp, arcname=f"saves/{save_name}")
                            manifest["contents"].append(f"saves/{save_name}")

                if include_mods and mods_dir and os.path.isdir(mods_dir):
                    for m in os.listdir(mods_dir):
                        if m.endswith((".geode", ".geode.disabled")):
                            mp = os.path.join(mods_dir, m)
                            if os.path.isfile(mp):
                                zf.write(mp, arcname=f"mods/{m}")
                                manifest["contents"].append(f"mods/{m}")

                if include_configs and config_dir and os.path.isdir(config_dir):
                    for root, _, files in os.walk(config_dir):
                        for file in files:
                            cfg_path = os.path.join(root, file)
                            rel_p = os.path.relpath(cfg_path, config_dir).replace("\\", "/")
                            zf.write(cfg_path, arcname=f"configs/{rel_p}")
                            manifest["contents"].append(f"configs/{rel_p}")

                zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            if os.path.exists(dest_path):
                os.remove(dest_path)
            os.rename(temp_dest, dest_path)
            size_mb = round(os.path.getsize(dest_path) / (1024 * 1024), 2)
            return True, f"Created {os.path.basename(dest_path)} ({size_mb} MB, {len(manifest['contents'])} items bundled)"
        except Exception as e:
            if os.path.exists(dest_path + ".tmp"):
                try:
                    os.remove(dest_path + ".tmp")
                except Exception:
                    pass
            return False, f"Failed to export bundle: {e}"

    def backup_save_files_snapshot(self, tag="auto"):
        """
        Creates an atomic timestamped snapshot of all *.dat and *.dat.bak save files.
        """
        save_dir = self.get_save_data_dir()
        if not save_dir or not os.path.isdir(save_dir):
            return False, "No save directory found"
        bak_dir = os.path.join(save_dir, "GeodeSync_Save_Backups", f"{tag}_{int(time.time())}")
        try:
            os.makedirs(bak_dir, exist_ok=True)
            copied = 0
            for f in os.listdir(save_dir):
                if f.endswith((".dat", ".dat.bak")):
                    src = os.path.join(save_dir, f)
                    if os.path.isfile(src):
                        shutil.copy2(src, os.path.join(bak_dir, f))
                        copied += 1
            return True, f"Backed up {copied} save files."
        except Exception as e:
            return False, str(e)

    def create_safety_snapshot(self, tag="pre_repair"):
        """Creates a timestamped pre-repair safety snapshot of save files, active mods, and configurations.
        Returns the snapshot directory path on success, or None on failure.
        """
        save_dir = self.get_save_data_dir()
        if not save_dir or not os.path.isdir(save_dir):
            return None
        snapshot_root = os.path.join(save_dir, "GeodeSync_Save_Backups")
        os.makedirs(snapshot_root, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        snapshot_dir = os.path.join(snapshot_root, f"{tag}_{timestamp}")
        os.makedirs(snapshot_dir, exist_ok=True)

        # 1. Backup save files (*.dat, *.dat.bak)
        try:
            for f in os.listdir(save_dir):
                if f.endswith((".dat", ".dat.bak")):
                    src = os.path.join(save_dir, f)
                    if os.path.isfile(src):
                        shutil.copy2(src, os.path.join(snapshot_dir, f))
        except Exception:
            pass

        # 2. Backup active mods and configurations
        if self.gd_path and os.path.isdir(self.gd_path):
            mods_dir = os.path.join(self.gd_path, "geode", "mods")
            if os.path.isdir(mods_dir):
                mods_snapshot = os.path.join(snapshot_dir, "mods")
                os.makedirs(mods_snapshot, exist_ok=True)
                for mf in os.listdir(mods_dir):
                    if mf.endswith((".geode", ".disabled")):
                        src_m = os.path.join(mods_dir, mf)
                        if os.path.isfile(src_m):
                            try:
                                shutil.copy2(src_m, os.path.join(mods_snapshot, mf))
                            except Exception:
                                pass
            cfg_dir = os.path.join(self.gd_path, "geode", "config")
            if os.path.isdir(cfg_dir):
                cfg_snapshot = os.path.join(snapshot_dir, "config")
                try:
                    shutil.copytree(cfg_dir, cfg_snapshot, dirs_exist_ok=True)
                except Exception:
                    pass

        return snapshot_dir

    def import_geodesync_bundle(self, bundle_path, overwrite_saves=True, overwrite_mods=True):
        """
        Unpacks and restores saves, mods, and configs from a .geodesync bundle.
        Always takes a pre-import safety backup of current saves first!
        """
        if not os.path.isfile(bundle_path):
            return False, "Bundle file not found."
        try:
            self.backup_save_files_snapshot(tag="pre_bundle_import")

            save_dir = self.get_save_data_dir()
            mods_dir = os.path.join(self.gd_path, "geode", "mods") if self.gd_path else None
            config_dir = os.path.join(self.gd_path, "geode", "config") if self.gd_path else None

            restored_saves = 0
            restored_mods = 0
            restored_configs = 0

            with zipfile.ZipFile(bundle_path, "r") as zf:
                names = zf.namelist()
                for name in names:
                    if name.startswith("saves/") and overwrite_saves and save_dir:
                        dest_f = os.path.join(save_dir, os.path.basename(name))
                        with zf.open(name) as src, open(dest_f, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        restored_saves += 1
                    elif name.startswith("mods/") and overwrite_mods and mods_dir:
                        os.makedirs(mods_dir, exist_ok=True)
                        dest_f = os.path.join(mods_dir, os.path.basename(name))
                        with zf.open(name) as src, open(dest_f, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        restored_mods += 1
                    elif name.startswith("configs/") and config_dir:
                        rel = name[len("configs/"):]
                        dest_f = os.path.join(config_dir, rel)
                        os.makedirs(os.path.dirname(dest_f), exist_ok=True)
                        with zf.open(name) as src, open(dest_f, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        restored_configs += 1

            return True, f"Successfully imported bundle! Restored {restored_saves} saves, {restored_mods} mods, and {restored_configs} configs."
        except Exception as e:
            return False, f"Failed to import bundle: {e}"

    def analyze_save_bloat(self):
        """
        Analyzes CCLocalLevels.dat to inspect total size, level count, and downloaded online levels bloat.
        """
        save_dir = self.get_save_data_dir()
        if not save_dir:
            return False, "Save directory not found"
        ll_path = os.path.join(save_dir, "CCLocalLevels.dat")
        if not os.path.exists(ll_path):
            return False, "CCLocalLevels.dat does not exist"
        try:
            raw_size = os.path.getsize(ll_path)
            with open(ll_path, "rb") as f:
                raw_bytes = f.read()
            dec = decode_geometry_dash_save(raw_bytes).decode("utf-8", errors="ignore")

            online_cached = len(re.findall(r"<k>k1</k><i>[0-9]+</i>", dec))
            total_levels = len(re.findall(r"<k>k2</k><s>", dec))

            return True, {
                "file_size_mb": round(raw_size / (1024 * 1024), 2),
                "total_levels": total_levels,
                "online_cached": online_cached,
                "user_created": max(0, total_levels - online_cached),
            }
        except Exception as e:
            return False, str(e)

    def clean_save_bloat(self, remove_online_cache=True):
        """
        Cleans downloaded online level caches from CCLocalLevels.dat while preserving user-created levels.
        Creates a timestamped backup before writing changes.
        """
        save_dir = self.get_save_data_dir()
        if not save_dir:
            return False, "Save directory not found"
        ll_path = os.path.join(save_dir, "CCLocalLevels.dat")
        if not os.path.exists(ll_path):
            return False, "CCLocalLevels.dat does not exist"
        try:
            bak_path = ll_path + f".bak_{int(time.time())}"
            shutil.copy2(ll_path, bak_path)

            old_size = os.path.getsize(ll_path)
            with open(ll_path, "rb") as f:
                raw_bytes = f.read()
            dec = decode_geometry_dash_save(raw_bytes).decode("utf-8", errors="ignore")

            llm_m = re.search(r"(<k>LLM_01</k><d>)(.*?)(</d><k>LLM_02</k>)", dec, re.DOTALL)
            if not llm_m:
                return False, "Could not locate local level map (LLM_01) in save data."

            prefix, body, suffix = llm_m.group(1), llm_m.group(2), llm_m.group(3)
            entries = re.findall(r"(<k>k_\d+</k><d>.*?</d>)", body, re.DOTALL)
            cleaned_entries = []
            removed_count = 0
            for idx, entry in enumerate(entries):
                is_online_cache = ("<k>k1</k><i>" in entry) and ("<k>k21</k><i>1</i>" in entry or "<k>k21</k>" not in entry)
                if remove_online_cache and is_online_cache:
                    removed_count += 1
                else:
                    renumbered = re.sub(r"^<k>k_\d+</k>", f"<k>k_{len(cleaned_entries)}</k>", entry)
                    cleaned_entries.append(renumbered)

            new_body = "".join(cleaned_entries)
            if not new_body.startswith("<k>_isArr</k><t/>"):
                new_body = "<k>_isArr</k><t/>" + new_body

            new_dec = dec[:llm_m.start(2)] + new_body + dec[llm_m.end(2):]
            encoded_bytes = encode_geometry_dash_save(new_dec.encode("utf-8"))

            with open(ll_path, "wb") as f:
                f.write(encoded_bytes)

            new_size = os.path.getsize(ll_path)
            saved_mb = round((old_size - new_size) / (1024 * 1024), 2)
            return True, {
                "removed_levels": removed_count,
                "old_size_bytes": old_size,
                "new_size_bytes": new_size,
                "saved_bytes": max(0, old_size - new_size),
                "old_size_mb": round(old_size / (1024 * 1024), 2),
                "new_size_mb": round(new_size / (1024 * 1024), 2),
                "saved_mb": max(0.0, saved_mb),
            }
        except Exception as e:
            return False, f"Optimization failed: {e}"

    def get_save_slots_dir(self):
        save_dir = self.get_save_data_dir()
        if not save_dir:
            return None
        slots_dir = os.path.join(save_dir, "GeodeSync_Save_Slots")
        os.makedirs(slots_dir, exist_ok=True)
        return slots_dir

    def get_save_slots(self):
        slots_dir = self.get_save_slots_dir()
        if not slots_dir:
            return []
        slots = []
        try:
            for item in sorted(os.listdir(slots_dir)):
                slot_path = os.path.join(slots_dir, item)
                if os.path.isdir(slot_path):
                    gm = os.path.join(slot_path, "CCGameManager.dat")
                    info = {"name": item, "path": slot_path, "has_saves": os.path.exists(gm)}
                    if os.path.exists(gm):
                        try:
                            with open(gm, "rb") as f:
                                dec = decode_geometry_dash_save(f.read()).decode("utf-8", errors="ignore")
                            m = re.search(r"<k>playerName</k><s>([^<]+)</s>", dec)
                            info["player_name"] = m.group(1) if m else "Player"
                            stars_m = re.search(r"<k>6</k><s>([0-9]+)</s>", dec)
                            info["stars"] = int(stars_m.group(1)) if stars_m else 0
                        except Exception:
                            info["player_name"] = "Player"
                            info["stars"] = 0
                    slots.append(info)
        except Exception:
            pass
        return slots

    def create_save_slot(self, slot_name):
        slots_dir = self.get_save_slots_dir()
        if not slots_dir:
            return False, "Save directory not found"
        safe_name = re.sub(r'[^a-zA-Z0-9_\- ]', '', slot_name).strip()
        if not safe_name:
            return False, "Invalid slot name"
        target = os.path.join(slots_dir, safe_name)
        if os.path.exists(target):
            return False, "A slot with this name already exists"
        os.makedirs(target, exist_ok=True)
        save_dir = self.get_save_data_dir()
        for f in os.listdir(save_dir):
            if f.endswith((".dat", ".dat.bak")):
                shutil.copy2(os.path.join(save_dir, f), os.path.join(target, f))
        return True, f"Created save slot '{safe_name}'"

    def switch_save_slot(self, slot_name):
        slots_dir = self.get_save_slots_dir()
        if not slots_dir:
            return False, "Save directory not found"
        target = os.path.join(slots_dir, slot_name)
        if not os.path.isdir(target):
            return False, "Slot directory does not exist"
        self.backup_save_files_snapshot(tag="pre_slot_switch")
        save_dir = self.get_save_data_dir()
        for f in os.listdir(target):
            if f.endswith((".dat", ".dat.bak")):
                shutil.copy2(os.path.join(target, f), os.path.join(save_dir, f))
        return True, f"Switched to save slot '{slot_name}'"

    def find_salvageable_saves(self):
        save_dir = self.get_save_data_dir()
        if not save_dir:
            return []
        candidates = []
        for root, _, files in os.walk(save_dir):
            for file in files:
                if file.startswith("CCGameManager") and (file.endswith(".dat") or ".bak" in file):
                    full_p = os.path.join(root, file)
                    try:
                        sz = os.path.getsize(full_p)
                        if sz > 100:
                            with open(full_p, "rb") as f:
                                dec = decode_geometry_dash_save(f.read()).decode("utf-8", errors="ignore")
                            if "<k>playerName</k>" in dec:
                                name_m = re.search(r"<k>playerName</k><s>([^<]+)</s>", dec)
                                stars_m = re.search(r"<k>6</k><s>([0-9]+)</s>", dec)
                                demons_m = re.search(r"<k>GS_value</k>.*?<k>14</k><s>([0-9]+)</s>", dec, re.DOTALL)
                                mtime = os.path.getmtime(full_p)
                                rel_name = os.path.relpath(full_p, save_dir).replace("\\", "/")
                                candidates.append({
                                    "path": full_p,
                                    "relative_path": rel_name,
                                    "size_kb": round(sz / 1024, 1),
                                    "player_name": name_m.group(1) if name_m else "Player",
                                    "stars": int(stars_m.group(1)) if stars_m else 0,
                                    "demons": int(demons_m.group(1)) if demons_m else 0,
                                    "mtime": mtime,
                                    "date_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
                                })
                    except Exception:
                        pass
        return sorted(candidates, key=lambda c: c["mtime"], reverse=True)

    def resurrect_save(self, candidate_gm_path):
        save_dir = self.get_save_data_dir()
        if not save_dir:
            return False, "Save directory not found"
        if not os.path.isfile(candidate_gm_path):
            return False, "Target save file does not exist"
        self.backup_save_files_snapshot(tag="pre_resurrect")
        target_gm = os.path.join(save_dir, "CCGameManager.dat")
        shutil.copy2(candidate_gm_path, target_gm)

        cand_dir = os.path.dirname(candidate_gm_path)
        for cand_ll in ("CCLocalLevels.dat", "CCLocalLevels.dat.bak"):
            ll_cand_p = os.path.join(cand_dir, cand_ll)
            if os.path.isfile(ll_cand_p):
                shutil.copy2(ll_cand_p, os.path.join(save_dir, "CCLocalLevels.dat"))
                break

        return True, "Save file successfully resurrected and restored!"

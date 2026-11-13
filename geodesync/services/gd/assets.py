"""Texture packs, practice music, custom death SFX and local audio. (GDManager mixin, moved verbatim from v2.8.0 main.py)."""

import os
import json
import shutil
import time
import zipfile

from geodesync.services.diagnostics import inspect_png_resource



class AssetsMixin:
    """Texture packs, practice music, custom death SFX and local audio."""

    def get_texture_pack_status(self):
        """
        Returns info about current texture pack and vanilla backup state.
        """
        if not self.gd_path:
            return {"active_pack": "Unknown", "has_backup": False, "vanilla_files": 0}
        bak_dir = os.path.join(self.gd_path, "Resources_Vanilla_Backup")
        has_bak = os.path.isdir(bak_dir)
        bak_count = len(os.listdir(bak_dir)) if has_bak else 0

        info_file = os.path.join(self.gd_path, "geode", "active_texture_pack.json")
        active_pack = "Vanilla (Default)"
        if os.path.exists(info_file):
            try:
                with open(info_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    active_pack = data.get("name", "Custom Pack")
            except Exception:
                pass

        return {
            "active_pack": active_pack,
            "has_backup": has_bak,
            "vanilla_files": bak_count
        }

    def backup_vanilla_textures(self, progress_callback=None):
        """
        Creates a pristine copy of Resources/ into Resources_Vanilla_Backup/ if not already present.
        """
        if not self.gd_path:
            return False, "Geometry Dash path not set."
        res_dir = os.path.join(self.gd_path, "Resources")
        if not os.path.isdir(res_dir):
            return False, "Resources directory not found."
        bak_dir = os.path.join(self.gd_path, "Resources_Vanilla_Backup")
        if os.path.isdir(bak_dir) and os.listdir(bak_dir):
            return True, "Vanilla backup is already safe and up to date."

        try:
            os.makedirs(bak_dir, exist_ok=True)
            files = [f for f in os.listdir(res_dir) if os.path.isfile(os.path.join(res_dir, f))]
            total = len(files)
            for i, f in enumerate(files):
                shutil.copy2(os.path.join(res_dir, f), os.path.join(bak_dir, f))
                if progress_callback and i % 50 == 0:
                    try:
                        progress_callback(i + 1, total)
                    except Exception:
                        pass
            if progress_callback:
                try:
                    progress_callback(total, total)
                except Exception:
                    pass
            return True, f"Successfully backed up {total} vanilla assets!"
        except Exception as e:
            return False, str(e)

    def install_texture_pack(self, source_path, pack_name=None, progress_callback=None):
        """
        Installs a custom texture pack (from a .zip or folder), ensuring vanilla textures
        are securely backed up first.
        """
        if not self.gd_path:
            return False, "Geometry Dash path not set."
        if not os.path.exists(source_path):
            return False, "Texture pack source not found."

        ok, msg = self.backup_vanilla_textures(progress_callback=None)
        if not ok:
            return False, f"Failed to protect vanilla textures: {msg}"

        res_dir = os.path.join(self.gd_path, "Resources")
        display_name = pack_name or os.path.splitext(os.path.basename(source_path))[0]
        installed_count = 0

        try:
            if zipfile.is_zipfile(source_path):
                with zipfile.ZipFile(source_path, "r") as zf:
                    entries = zf.namelist()
                    valid_exts = (".png", ".plist", ".fnt", ".ogg", ".mp3", ".wav")
                    asset_entries = [e for e in entries if e.lower().endswith(valid_exts)]
                    total = len(asset_entries)
                    for i, entry in enumerate(asset_entries):
                        filename = os.path.basename(entry)
                        if not filename:
                            continue
                        data = zf.read(entry)
                        dest_path = os.path.join(res_dir, filename)
                        with open(dest_path, "wb") as out:
                            out.write(data)
                        installed_count += 1
                        if progress_callback and i % 25 == 0:
                            try:
                                progress_callback(i + 1, total)
                            except Exception:
                                pass
            elif os.path.isdir(source_path):
                valid_exts = (".png", ".plist", ".fnt", ".ogg", ".mp3", ".wav")
                matched = []
                for root, dirs, files in os.walk(source_path):
                    for f in files:
                        if f.lower().endswith(valid_exts):
                            matched.append((os.path.join(root, f), f))
                total = len(matched)
                for i, (src, fname) in enumerate(matched):
                    shutil.copy2(src, os.path.join(res_dir, fname))
                    installed_count += 1
                    if progress_callback and i % 25 == 0:
                        try:
                            progress_callback(i + 1, total)
                        except Exception:
                            pass
            else:
                return False, "Invalid texture pack format (must be .zip or directory)."

            meta_dir = os.path.join(self.gd_path, "geode")
            os.makedirs(meta_dir, exist_ok=True)
            with open(os.path.join(meta_dir, "active_texture_pack.json"), "w", encoding="utf-8") as f:
                json.dump({"name": display_name, "files": installed_count, "installed_at": time.time()}, f, indent=2)

            return True, f"Successfully applied texture pack '{display_name}' ({installed_count} textures updated)!"
        except Exception as e:
            return False, str(e)

    def restore_vanilla_textures(self, progress_callback=None):
        """
        Restores 100% vanilla textures from Resources_Vanilla_Backup into Resources.
        """
        if not self.gd_path:
            return False, "Geometry Dash path not set."
        process_check = getattr(self, "is_gd_process_running", None)
        if callable(process_check) and process_check():
            return False, "Close Geometry Dash before restoring textures. No files were changed."
        bak_dir = os.path.join(self.gd_path, "Resources_Vanilla_Backup")
        if not os.path.isdir(bak_dir) or not os.listdir(bak_dir):
            return False, "Vanilla backup does not exist yet. Launch with vanilla textures to create one."
        res_dir = os.path.join(self.gd_path, "Resources")

        try:
            files = [f for f in os.listdir(bak_dir)
                     if os.path.isfile(os.path.join(bak_dir, f)) and not os.path.islink(os.path.join(bak_dir, f))]
            if not files:
                return False, "Vanilla backup contains no usable files. No files were changed."
            # Validate the entire image backup before writing any of it so a bad backup
            # cannot leave the live Resources directory half-restored.
            for filename in files:
                if filename.casefold().endswith(".png"):
                    problem = inspect_png_resource(os.path.join(bak_dir, filename))
                    if problem:
                        return False, f"Vanilla backup texture {filename!r} failed its integrity check ({problem}). No files were changed."
            os.makedirs(res_dir, exist_ok=True)
            total = len(files)
            for i, f in enumerate(files):
                shutil.copy2(os.path.join(bak_dir, f), os.path.join(res_dir, f))
                if progress_callback and i % 50 == 0:
                    try:
                        progress_callback(i + 1, total)
                    except Exception:
                        pass

            info_file = os.path.join(self.gd_path, "geode", "active_texture_pack.json")
            if os.path.exists(info_file):
                try:
                    os.remove(info_file)
                except Exception:
                    pass

            return True, f"Successfully restored {total} vanilla textures!"
        except Exception as e:
            return False, str(e)

    def get_practice_music_status(self):
        """
        Checks whether custom practice music is active by checking Resources/StayInsideMe.mp3.bak.
        """
        if not self.gd_path:
            return False, "No GD folder set"
        res_dir = os.path.join(self.gd_path, "Resources")
        bak_file = os.path.join(res_dir, "StayInsideMe.mp3.bak")
        curr_file = os.path.join(res_dir, "StayInsideMe.mp3")
        if not os.path.exists(curr_file):
            return False, "StayInsideMe.mp3 not found"
        if os.path.exists(bak_file):
            return True, "Custom Practice Music Active"
        return False, "Vanilla StayInsideMe.mp3"

    def set_custom_practice_music(self, source_audio_path):
        """
        Replaces StayInsideMe.mp3 with a custom audio file, backing up the original.
        """
        if not self.gd_path:
            return False, "Could not locate Geometry Dash folder."
        if not os.path.isfile(source_audio_path):
            return False, f"Source audio file not found: {source_audio_path}"
        res_dir = os.path.join(self.gd_path, "Resources")
        if not os.path.isdir(res_dir):
            return False, "Resources directory not found in GD folder."

        orig_file = os.path.join(res_dir, "StayInsideMe.mp3")
        bak_file = os.path.join(res_dir, "StayInsideMe.mp3.bak")

        try:
            if os.path.exists(orig_file) and not os.path.exists(bak_file):
                shutil.copy2(orig_file, bak_file)
            shutil.copy2(source_audio_path, orig_file)
            return True, "Successfully set custom practice music!"
        except Exception as e:
            return False, f"Failed to swap practice music: {e}"

    def restore_vanilla_practice_music(self):
        """
        Restores StayInsideMe.mp3 from StayInsideMe.mp3.bak.
        """
        if not self.gd_path:
            return False, "Could not locate Geometry Dash folder."
        res_dir = os.path.join(self.gd_path, "Resources")
        orig_file = os.path.join(res_dir, "StayInsideMe.mp3")
        bak_file = os.path.join(res_dir, "StayInsideMe.mp3.bak")

        if not os.path.exists(bak_file):
            return True, "Already using vanilla practice music."
        try:
            shutil.copy2(bak_file, orig_file)
            os.remove(bak_file)
            return True, "Restored original vanilla practice music."
        except Exception as e:
            return False, f"Failed to restore vanilla music: {e}"

    def get_local_audio_tracks(self):
        """
        Scans save directory for downloaded custom songs (*.mp3).
        Returns list of dicts: [{'song_id': '12345', 'path': '...', 'size_mb': 4.2}]
        """
        save_dir = self.get_save_data_dir()
        if not save_dir or not os.path.isdir(save_dir):
            return []
        songs = []
        try:
            for f in os.listdir(save_dir):
                if f.endswith(".mp3"):
                    full_p = os.path.join(save_dir, f)
                    if os.path.isfile(full_p):
                        song_id = os.path.splitext(f)[0]
                        size_mb = round(os.path.getsize(full_p) / (1024 * 1024), 2)
                        songs.append({"song_id": song_id, "path": full_p, "size_mb": size_mb})
        except Exception:
            pass
        return sorted(songs, key=lambda s: s["song_id"])

    def get_custom_sfx_status(self):
        if not self.gd_path:
            return {}
        res_dir = os.path.join(self.gd_path, "Resources")
        death_bak = os.path.join(res_dir, "explode_11.ogg.bak")
        return {
            "death_sfx_custom": os.path.exists(death_bak),
            "res_dir_exists": os.path.isdir(res_dir)
        }

    def set_custom_death_sfx(self, source_audio_path):
        if not self.gd_path:
            return False, "Could not locate Geometry Dash folder."
        if not os.path.isfile(source_audio_path):
            return False, "Source audio file not found."
        res_dir = os.path.join(self.gd_path, "Resources")
        if not os.path.isdir(res_dir):
            return False, "Resources directory not found in GD folder."
        orig_sfx = os.path.join(res_dir, "explode_11.ogg")
        bak_sfx = os.path.join(res_dir, "explode_11.ogg.bak")
        try:
            if os.path.exists(orig_sfx) and not os.path.exists(bak_sfx):
                shutil.copy2(orig_sfx, bak_sfx)
            shutil.copy2(source_audio_path, orig_sfx)
            return True, "Successfully installed custom death sound!"
        except Exception as e:
            return False, f"Failed to swap death sound: {e}"

    def restore_vanilla_death_sfx(self):
        if not self.gd_path:
            return False, "Could not locate Geometry Dash folder."
        res_dir = os.path.join(self.gd_path, "Resources")
        orig_sfx = os.path.join(res_dir, "explode_11.ogg")
        bak_sfx = os.path.join(res_dir, "explode_11.ogg.bak")
        if not os.path.exists(bak_sfx):
            return True, "Already using vanilla death sound."
        try:
            shutil.copy2(bak_sfx, orig_sfx)
            os.remove(bak_sfx)
            return True, "Restored original vanilla death sound."
        except Exception as e:
            return False, f"Failed to restore vanilla sound: {e}"

"""Geode mod discovery, inspection, and safe toggle operations."""

import json
import os
import zipfile
from typing import List, Optional
from geodesync.core.models import ModInfo


class ModService:
    """Manages .geode mods within a game directory."""

    @staticmethod
    def get_mods_dir(game_path: str) -> str:
        return os.path.join(game_path, "geode", "mods")

    @classmethod
    def list_mods(cls, game_path: str) -> List[ModInfo]:
        """Scan geode/mods directory for installed and disabled mods."""
        mods_dir = cls.get_mods_dir(game_path)
        if not os.path.isdir(mods_dir):
            return []

        results: List[ModInfo] = []
        for filename in os.listdir(mods_dir):
            full_path = os.path.join(mods_dir, filename)
            if not os.path.isfile(full_path):
                continue

            enabled = filename.endswith(".geode")
            disabled = filename.endswith(".geode.disabled")
            if not (enabled or disabled):
                continue

            mod_id = filename.replace(".geode.disabled", "").replace(".geode", "")
            name = mod_id
            version = "unknown"
            developer = "unknown"

            # Try reading mod.json inside the zip
            try:
                with zipfile.ZipFile(full_path, "r") as zf:
                    if "mod.json" in zf.namelist():
                        with zf.open("mod.json") as mj:
                            data = json.loads(mj.read().decode("utf-8", errors="ignore"))
                            mod_id = data.get("id", mod_id)
                            name = data.get("name", name)
                            version = data.get("version", version)
                            developer = data.get("developer", developer)
            except Exception:
                pass

            results.append(ModInfo(
                id=mod_id,
                name=name,
                version=version,
                developer=developer,
                enabled=enabled,
                file_path=full_path,
            ))
        return results

    @classmethod
    def toggle_mod(cls, mod: ModInfo) -> bool:
        """Enable or disable a mod by renaming its file."""
        if not os.path.isfile(mod.file_path):
            return False
        try:
            if mod.enabled:
                new_path = mod.file_path + ".disabled"
            else:
                new_path = mod.file_path[:-9]  # remove .disabled
            os.rename(mod.file_path, new_path)
            mod.file_path = new_path
            mod.enabled = not mod.enabled
            return True
        except OSError:
            return False

"""Game detection, state checks, and process inspection."""

import os
import sys
from typing import Optional, List
from geodesync.platform.process_manager import safe_run_command
from geodesync.core.models import GameInstallation


class GameService:
    """Detects and monitors Geometry Dash installations."""

    COMMON_STEAM_PATHS = [
        r"C:\Program Files (x86)\Steam\steamapps\common\Geometry Dash",
        r"C:\Program Files\Steam\steamapps\common\Geometry Dash",
        r"D:\Steam\steamapps\common\Geometry Dash",
        r"D:\SteamLibrary\steamapps\common\Geometry Dash",
        r"E:\SteamLibrary\steamapps\common\Geometry Dash",
    ]

    @classmethod
    def is_game_running(cls) -> bool:
        """Check if GeometryDash.exe is actively running without popping windows."""
        if sys.platform != "win32":
            return False
        try:
            res = safe_run_command(["tasklist", "/fi", "imagename eq GeometryDash.exe", "/nh"])
            return "GeometryDash.exe" in (res.stdout or "")
        except Exception:
            return False

    @classmethod
    def auto_detect(cls) -> Optional[GameInstallation]:
        """Find the local Geometry Dash directory."""
        for path in cls.COMMON_STEAM_PATHS:
            if os.path.isdir(path):
                exe = os.path.join(path, "GeometryDash.exe")
                if os.path.isfile(exe):
                    geode_dir = os.path.join(path, "geode")
                    return GameInstallation(
                        path=path,
                        exe_path=exe,
                        geode_installed=os.path.isdir(geode_dir),
                        geode_dir=geode_dir if os.path.isdir(geode_dir) else None,
                    )
        return None

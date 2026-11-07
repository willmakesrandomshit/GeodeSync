"""Geometry Dash save file decode, validate, and safe snapshot creation."""

import base64
import os
import shutil
import zlib
from datetime import datetime
from typing import Optional, Tuple


def decode_gd_save(raw: bytes) -> bytes:
    """Decode Geometry Dash XOR 0x0B, base64 URL-safe, zlib compressed save data."""
    xored = bytes(b ^ 11 for b in raw)
    b64_str = xored.decode("ascii", errors="ignore").replace("-", "+").replace("_", "/")
    padded = b64_str + "=" * ((4 - len(b64_str) % 4) % 4)
    compressed = base64.b64decode(padded)
    return zlib.decompress(compressed, 15 | 32)


def encode_gd_save(data: bytes) -> bytes:
    """Encode raw XML save into Geometry Dash's zlib + base64 + XOR 0x0B format."""
    compressed = zlib.compress(data)
    b64 = base64.b64encode(compressed).decode("ascii").replace("+", "-").replace("/", "_")
    return bytes(b ^ 11 for b in b64.encode("ascii"))


class SaveService:
    """Inspect and snapshot local Geometry Dash save data."""

    @staticmethod
    def get_save_dir() -> str:
        """Get standard Geometry Dash local AppData save path."""
        local_app = os.environ.get("LOCALAPPDATA", "")
        return os.path.join(local_app, "GeometryDash")

    @classmethod
    def create_snapshot(cls, backup_dir: str, tag: str = "manual") -> Tuple[bool, str]:
        """Create a timestamped copy of save files."""
        save_dir = cls.get_save_dir()
        if not os.path.isdir(save_dir):
            return False, "Geometry Dash save directory not found."

        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_dir = os.path.join(backup_dir, f"snapshot_{ts}_{tag}")
        os.makedirs(target_dir, exist_ok=True)

        copied = 0
        for f in ["CCGameManager.dat", "CCGameManager2.dat", "CCLocalLevels.dat", "CCLocalLevels2.dat"]:
            src = os.path.join(save_dir, f)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(target_dir, f))
                copied += 1

        if copied == 0:
            return False, "No save files found to snapshot."
        return True, target_dir

"""Centralized configuration, versioning, and environment constants."""

import os
import sys

from geodesync.platform.process_manager import IS_WIN, IS_MAC, IS_LINUX

APP_VERSION = "3.0.0"
APP_NAME = "GeodeSync"
GITHUB_REPO = "willmakesrandomshit/GeodeSync"
CONFIG_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.json"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases?per_page=100"
GEODE_REPO = "geode-sdk/geode"
GEODE_API = f"https://api.github.com/repos/{GEODE_REPO}/releases/latest"

APP_ID = "322170"
DEPOT_ID = "322172" if IS_MAC else "322171"
DEFAULT_MANIFEST = "8780295549609362522" if IS_MAC else "3816559102876907245"
DEFAULT_TARGET_GD = "2.2081"

# Geometry Dash baseline executable sizes (2.2081)
SIZES_22081 = {
    11516928,  # Windows vanilla x86
    11520000,
    11521536,
    11522048,
    11522560,
    11523072,
    11524096,
}


def get_app_data_dir():
    """Return platform-standard persistent application directory."""
    if IS_WIN:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = os.path.join(base, "GeodeSync")
    elif IS_MAC:
        path = os.path.expanduser("~/Library/Application Support/GeodeSync")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        path = os.path.join(base, "geodesync")
    os.makedirs(path, exist_ok=True)
    return path


def _crash_log_path():
    """Return platform-standard crash log path."""
    if IS_WIN:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "GeodeSync", "crash.log")
    if IS_MAC:
        return os.path.expanduser("~/Library/Logs/GeodeSync/crash.log")
    state_home = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return os.path.join(state_home, "geodesync", "crash.log")


def _application_root():
    """Return base execution root (handling PyInstaller bundle directory)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

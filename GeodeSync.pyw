import os
import sys
import traceback

def _crash_log_path():
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "GeodeSync", "crash.log")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Logs/GeodeSync/crash.log")
    state_home = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return os.path.join(state_home, "geodesync", "crash.log")

def _global_excepthook(exc_type, exc_value, exc_traceback):
    try:
        crash_path = _crash_log_path()
        app_dir = os.path.dirname(crash_path)
        os.makedirs(app_dir, exist_ok=True)
        import time
        with open(crash_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- CRASH AT {time.ctime()} ---\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    except Exception:
        pass

sys.excepthook = _global_excepthook

import re
import json
import shutil
import stat
import time
import tempfile
import urllib.request
import webbrowser
import threading
import subprocess
import base64
import hashlib
import platform
import posixpath
import zipfile
import tarfile
import zlib
import struct
import plistlib
from pathlib import PurePosixPath
from urllib.parse import urlparse
from xml.parsers.expat import ExpatError
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

if IS_WIN:
    import winreg
    import winsound
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
else:
    winreg = None
    winsound = None

APP_VERSION = "2.4.1"
GITHUB_REPO = "willmakesrandomshit/GeodeSync"
CONFIG_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.json"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases?per_page=100"


def decode_geometry_dash_save(raw: bytes) -> bytes:
    """Decode Geometry Dash's save wrapper (XOR 0x0B, URL-safe Base64, zlib)."""
    encoded = bytes(value ^ 0x0B for value in raw)
    compressed = base64.urlsafe_b64decode(encoded)
    return zlib.decompress(compressed, 15 + 32)


def encode_geometry_dash_save(xml_data: bytes) -> bytes:
    """Encode XML bytes using Geometry Dash's documented save-file wrapper."""
    compressed = zlib.compress(xml_data)
    encoded = base64.urlsafe_b64encode(compressed)
    return bytes(value ^ 0x0B for value in encoded)


def official_release_page(url=None):
    """Accept only the canonical repository's GitHub releases page URL."""
    expected = f"https://github.com/{GITHUB_REPO}/releases"
    candidate = str(url or expected).rstrip("/")
    if candidate == expected or candidate.startswith(expected + "/"):
        return candidate
    return expected


class DiscordRPC:
    CLIENT_ID = "1563607447384367195"
    PLAYING_DETAILS = "Playing Geometry Dash with GeodeSync"
    COMPANION_DETAILS = "GeodeSync · Geometry Dash Companion"

    def __init__(self, enabled=True):
        self._enabled = enabled
        self._sock = None
        self._connected = False
        self._lock = threading.RLock()
        self._start_time = int(time.time())
        self._current_details = self.COMPANION_DETAILS
        self._current_state = "Geode Mods Synced & Protected 🛡️"
        self._geode_ver = "v5.x"
        self._running = True
        self._wake = threading.Event()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def set_enabled(self, val):
        self._enabled = bool(val)
        if not self._enabled:
            self._close_socket()
        else:
            self._start_time = int(time.time())
        self._wake.set()

    def is_connected(self):
        return self._connected and self._enabled

    def _close_socket(self):
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None
            self._connected = False

    def _attempt_connect(self):
        if not self._enabled:
            return False
        if IS_WIN:
            for i in range(10):
                pipe_name = rf"\\.\pipe\discord-ipc-{i}"
                try:
                    sock = open(pipe_name, "r+b", buffering=0)
                    if self._perform_handshake(sock):
                        with self._lock:
                            self._sock = sock
                            self._connected = True
                        return True
                    else:
                        try:
                            sock.close()
                        except Exception:
                            pass
                except Exception:
                    continue
        else:
            sock_paths = [
                os.path.join(os.environ.get("XDG_RUNTIME_DIR", ""), "discord-ipc-0"),
                "/tmp/discord-ipc-0",
                f"{tempfile.gettempdir()}/discord-ipc-0",
            ]
            for p in sock_paths:
                if os.path.exists(p):
                    try:
                        import socket
                        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        sock.connect(p)
                        if self._perform_handshake(sock):
                            with self._lock:
                                self._sock = sock
                                self._connected = True
                            return True
                        else:
                            try:
                                sock.close()
                            except Exception:
                                pass
                    except Exception:
                        continue
        return False

    def _perform_handshake(self, sock):
        try:
            handshake = json.dumps({"v": 1, "client_id": self.CLIENT_ID}).encode("utf-8")
            header = struct.pack("<II", 0, len(handshake))
            if hasattr(sock, "write"):
                sock.write(header + handshake)
                resp_hdr = sock.read(8)
            else:
                sock.sendall(header + handshake)
                resp_hdr = sock.recv(8)
            if len(resp_hdr) == 8:
                op, length = struct.unpack("<II", resp_hdr)
                if hasattr(sock, "read"):
                    body = sock.read(length)
                else:
                    body = sock.recv(length)
                return op == 1
        except Exception:
            pass
        return False

    def _run_loop(self):
        while self._running:
            try:
                if self._enabled:
                    if not self._connected:
                        if self._attempt_connect():
                            self._send_activity()
                    else:
                        self._send_activity()
            except Exception:
                self._close_socket()
            self._wake.wait(4)
            self._wake.clear()

    def _send_activity(self):
        if not self._connected or not self._sock or not self._enabled:
            return
        with self._lock:
            try:
                frame = {
                    "cmd": "SET_ACTIVITY",
                    "args": {
                        "pid": os.getpid(),
                        "activity": {
                            "details": self._current_details,
                            "state": self._current_state,
                            "timestamps": {"start": self._start_time},
                            "assets": {
                                "large_image": f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/assets/geodesync-brand-2026.png",
                                "large_text": f"GeodeSync v{APP_VERSION} · Geometry Dash Mod Manager",
                                "small_image": f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/assets/geodesync-brand-2026.png",
                                "small_text": "GeodeSync"
                            },
                            "buttons": [
                                {"label": "View GitHub Repo", "url": f"https://github.com/{GITHUB_REPO}"},
                                {"label": "Join Discord Server", "url": "https://discord.gg/tyQG5xNGCx"}
                            ],
                            "metadata": {
                                "button_urls": [
                                    f"https://github.com/{GITHUB_REPO}",
                                    "https://discord.gg/tyQG5xNGCx"
                                ]
                            }
                        }
                    },
                    "nonce": str(time.time())
                }
                data = json.dumps(frame).encode("utf-8")
                header = struct.pack("<II", 1, len(data))
                payload = header + data
                if hasattr(self._sock, "write"):
                    self._sock.write(payload)
                    resp_hdr = self._sock.read(8)
                    if len(resp_hdr) == 8:
                        _, length = struct.unpack("<II", resp_hdr)
                        self._sock.read(length)
                    else:
                        self._connected = False
                elif hasattr(self._sock, "sendall"):
                    self._sock.sendall(payload)
                    resp_hdr = self._sock.recv(8)
                    if len(resp_hdr) == 8:
                        _, length = struct.unpack("<II", resp_hdr)
                        self._sock.recv(length)
                    else:
                        self._connected = False
            except Exception:
                self._connected = False

    def update_presence(self, details=None, state=None, reset_timer=False, geode_ver=None):
        changed = False
        if details is not None and details != self._current_details:
            self._current_details = str(details)
            changed = True
        if state is not None and state != self._current_state:
            self._current_state = str(state)
            changed = True
        if geode_ver is not None and str(geode_ver) != self._geode_ver:
            self._geode_ver = str(geode_ver)
            changed = True
        if reset_timer:
            self._start_time = int(time.time())
            changed = True
        if changed:
            self._wake.set()

    def clear_presence(self):
        if not self._connected or not self._sock:
            return
        with self._lock:
            try:
                frame = {
                    "cmd": "SET_ACTIVITY",
                    "args": {
                        "pid": os.getpid(),
                        "activity": None
                    },
                    "nonce": str(time.time())
                }
                data = json.dumps(frame).encode("utf-8")
                header = struct.pack("<II", 1, len(data))
                payload = header + data
                if hasattr(self._sock, "write"):
                    self._sock.write(payload)
                elif hasattr(self._sock, "sendall"):
                    self._sock.sendall(payload)
            except Exception:
                pass
        self._close_socket()

    def close(self):
        self._running = False
        self._wake.set()
        self.clear_presence()


UI = {
    "background": "#121013",
    "header": "#19161b",
    "panel": "#201c22",
    "panel_alt": "#29242c",
    "inset": "#171419",
    "border": "#3c3440",
    "text": "#f6f0e8",
    "muted": "#b8adb9",
    "quiet": "#897e8b",
    "lime": "#c2e66b",
    "lime_hover": "#a8ce50",
    "lime_dark": "#27351b",
    "lilac": "#c497e8",
    "lilac_dark": "#34233f",
    "amber": "#e4b968",
    "red": "#f08087",
    "red_dark": "#46242a",
}

APP_ID = "322170"
DEPOT_ID = "322172" if IS_MAC else "322171"
DEFAULT_MANIFEST = "8780295549609362522" if IS_MAC else "3816559102876907245"
DEFAULT_TARGET_GD = "2.2081"


def is_newer_app_version(candidate, current):
    """Compare numeric release versions without offering accidental downgrades."""
    def parts(version):
        version = str(version or "").strip().lstrip("v")
        if not version or not re.fullmatch(r"\d+(?:\.\d+)*", version):
            return None
        return tuple(int(part) for part in version.split("."))

    candidate_parts = parts(candidate)
    current_parts = parts(current)
    if candidate_parts is None or current_parts is None:
        return False
    width = max(len(candidate_parts), len(current_parts))
    return candidate_parts + (0,) * (width - len(candidate_parts)) > current_parts + (0,) * (width - len(current_parts))


def version_sort_key(version):
    version = str(version or "").strip().lstrip("v")
    if not re.fullmatch(r"\d+(?:\.\d+)*", version):
        return None
    parts = tuple(int(part) for part in version.split("."))
    return parts + (0,) * max(0, 8 - len(parts))


def fetch_latest_published_release(timeout=8):
    """Return the newest stable *published release*, never a source version manifest."""
    request = urllib.request.Request(RELEASES_API, headers={"User-Agent": "GeodeSync-Client"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            releases = json.loads(response.read().decode("utf-8"))
    except Exception as error:
        raise ValueError("Could not connect to GitHub to check for published updates.") from error
    if not isinstance(releases, list):
        raise ValueError("GitHub returned an invalid release list.")
    stable = []
    for release in releases:
        if not isinstance(release, dict) or release.get("draft") or release.get("prerelease") or not release.get("published_at"):
            continue
        tag = str(release.get("tag_name", "")).strip()
        key = version_sort_key(tag)
        if key is not None:
            stable.append((key, release))
    if stable:
        return max(stable, key=lambda item: item[0])[1]
    raise ValueError("GitHub has no published stable GeodeSync release.")


GEODE_REPO = "geode-sdk/geode"
GEODE_API = f"https://api.github.com/repos/{GEODE_REPO}/releases/latest"


def fetch_latest_geode_release(timeout=6):
    req = urllib.request.Request(GEODE_API, headers={"User-Agent": "GeodeSync-Client"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def install_or_update_geode(gd_path, log_callback=None):
    if not gd_path or not os.path.isdir(gd_path):
        raise FileNotFoundError("Geometry Dash game folder not found.")

    release = fetch_latest_geode_release()
    tag = str(release.get("tag_name", "")).strip()
    assets = release.get("assets", [])

    target_asset = None
    if IS_WIN:
        target_asset = next((a for a in assets if str(a.get("name", "")).endswith("-win.zip")), None)
    elif IS_MAC:
        target_asset = next((a for a in assets if str(a.get("name", "")).endswith("-mac.zip")), None)
    else:
        target_asset = next((a for a in assets if str(a.get("name", "")).endswith("-linux.zip") or str(a.get("name", "")).endswith("-linux.sh")), None)

    if not target_asset or not target_asset.get("browser_download_url"):
        raise ValueError(f"No compatible Geode asset found for {platform.system()} in release {tag}")

    download_url = target_asset["browser_download_url"]
    parsed_url = urlparse(download_url)
    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname != "github.com"
        or not parsed_url.path.startswith("/geode-sdk/geode/releases/download/")
    ):
        raise ValueError("Geode's release metadata contains an unexpected download destination.")
    asset_size = int(target_asset.get("size") or 0)
    if asset_size <= 0 or asset_size > GEODE_PACKAGE_MAX_DOWNLOAD_BYTES:
        raise ValueError("Geode's release metadata contains an invalid or excessive package size.")
    if log_callback:
        log_callback(f"Downloading Geode {tag} package ({round(asset_size / (1024 * 1024), 1)} MB)...")

    req = urllib.request.Request(download_url, headers={"User-Agent": "GeodeSync-Client"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        final_host = urlparse(resp.geturl()).hostname
        if final_host not in {
            "github.com",
            "objects.githubusercontent.com",
            "release-assets.githubusercontent.com",
        }:
            raise ValueError("GitHub redirected the Geode package to an unexpected host.")
        data = resp.read(GEODE_PACKAGE_MAX_DOWNLOAD_BYTES + 1)
    if len(data) > GEODE_PACKAGE_MAX_DOWNLOAD_BYTES or len(data) != asset_size:
        raise ValueError("The downloaded Geode package has an unexpected size.")
    verify_release_asset_digest(target_asset, data, "Geode package")

    import io
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        if IS_WIN:
            target_root = gd_path
        elif IS_MAC:
            target_root = os.path.join(gd_path, "Geometry Dash.app", "Contents", "Frameworks")
        else:
            target_root = os.path.join(gd_path, "geode")
        os.makedirs(target_root, exist_ok=True)
        extract_geode_package_safely(zf, target_root)
    return tag


def should_apply_downloaded_depot(steam_reported_complete, depot_valid):
    """Only validated depot contents may be installed; logs are advisory."""
    return bool(depot_valid)

if IS_MAC:
    KNOWN_VERSIONS = {
        "2.2081 (Geode Compatible • macOS Recommended)": {
            "manifest": "8780295549609362522",
            "ver": "2.2081",
            "size": 0
        }
    }
else:
    KNOWN_VERSIONS = {
        "2.2081 (Geode Compatible • Recommended)": {
            "manifest": "3816559102876907245",
            "ver": "2.2081",
            "sizes": (10700288, 10698752),
            "size": 10698752
        },
        "2.113 (Classic 2.11 Legacy)": {
            "manifest": "7938363717144760233",
            "ver": "2.113",
            "size": 7578624
        }
    }

SIZES_22081 = (10700288, 10698752)
SIZE_22081 = 10698752
SIZE_2209 = 13178880
EXPECTED_DEPOT_BYTES = 230000000 if IS_MAC else 204000000
MACOS_UPDATE_MAX_BYTES = 300 * 1024 * 1024
APP_UPDATE_MAX_BYTES = 500 * 1024 * 1024
GEODE_PACKAGE_MAX_DOWNLOAD_BYTES = 300 * 1024 * 1024
GEODE_PACKAGE_MAX_EXPANDED_BYTES = 500 * 1024 * 1024


def safe_zip_member_target(root, info):
    """Resolve a ZIP member below root, rejecting traversal and special files."""
    name = info.filename
    if not name or "\\" in name or "\x00" in name:
        raise ValueError("The Geode package contains an invalid archive path.")
    member = PurePosixPath(name)
    if member.is_absolute() or any(part in ("", ".", "..") for part in member.parts):
        raise ValueError("The Geode package contains an unsafe archive path.")
    reserved_windows_names = {"CON", "PRN", "AUX", "NUL"} | {
        f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
    }
    if any(
        ":" in part
        or part.endswith((" ", "."))
        or part.split(".", 1)[0].upper() in reserved_windows_names
        for part in member.parts
    ):
        raise ValueError("The Geode package contains an unsafe destination filename.")
    mode = (info.external_attr >> 16) & 0xFFFF
    file_type = stat.S_IFMT(mode)
    if file_type not in (0, stat.S_IFREG, stat.S_IFDIR):
        raise ValueError("The Geode package contains a link or special file.")
    base = os.path.realpath(root)
    target = os.path.abspath(os.path.join(base, *member.parts))
    if os.path.commonpath((base, target)) != base:
        raise ValueError("The Geode package path escapes the game folder.")
    parent = os.path.dirname(target)
    while parent != base and os.path.commonpath((base, parent)) == base:
        if os.path.islink(parent):
            raise ValueError("The Geode package targets a symbolic-link directory.")
        parent = os.path.dirname(parent)
    if os.path.islink(target):
        raise ValueError("The Geode package would overwrite a symbolic link.")
    if info.file_size < 0 or info.file_size > GEODE_PACKAGE_MAX_EXPANDED_BYTES:
        raise ValueError("The Geode package contains an oversized file.")
    return target


def validate_geode_package_zip(archive, target_root):
    """Validate every member before extraction and cap total expansion size."""
    total_size = 0
    files = []
    seen_targets = set()
    for info in archive.infolist():
        target = safe_zip_member_target(target_root, info)
        key = os.path.normcase(target)
        if key in seen_targets:
            raise ValueError("The Geode package contains duplicate destination paths.")
        seen_targets.add(key)
        total_size += info.file_size
        if total_size > GEODE_PACKAGE_MAX_EXPANDED_BYTES:
            raise ValueError("The Geode package expands beyond the allowed size.")
        if not info.is_dir():
            files.append((info, target))
    if not files:
        raise ValueError("The Geode package contains no installable files.")
    return files


def extract_geode_package_safely(archive, target_root):
    """Safely stage regular files and roll back if any replacement fails."""
    entries = validate_geode_package_zip(archive, target_root)
    base = os.path.realpath(target_root)
    stage = tempfile.mkdtemp(prefix=".geodesync-geode-stage-", dir=base)
    incoming = os.path.join(stage, "incoming")
    previous = os.path.join(stage, "previous")
    installed = []
    try:
        for info, destination in entries:
            relative = os.path.relpath(destination, base)
            staged_file = os.path.join(incoming, relative)
            os.makedirs(os.path.dirname(staged_file), exist_ok=True)
            with archive.open(info, "r") as source, open(staged_file, "wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            mode = (info.external_attr >> 16) & 0o777
            if mode:
                os.chmod(staged_file, mode & 0o755)

        for _info, destination in entries:
            if os.path.lexists(destination) and not os.path.isfile(destination):
                raise ValueError("The Geode package conflicts with a non-file in the game folder.")
            relative = os.path.relpath(destination, base)
            staged_file = os.path.join(incoming, relative)
            backup_file = os.path.join(previous, relative)
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            had_previous = os.path.isfile(destination)
            if had_previous:
                os.makedirs(os.path.dirname(backup_file), exist_ok=True)
                os.replace(destination, backup_file)
            try:
                os.replace(staged_file, destination)
            except Exception:
                if had_previous and os.path.exists(backup_file):
                    os.replace(backup_file, destination)
                raise
            installed.append((destination, backup_file if had_previous else None))
    except Exception:
        for destination, backup_file in reversed(installed):
            try:
                if os.path.lexists(destination):
                    os.remove(destination)
                if backup_file and os.path.exists(backup_file):
                    os.replace(backup_file, destination)
            except OSError:
                pass
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def verify_release_asset_digest(asset, data, label):
    digest = str(asset.get("digest") or "")
    if not digest.startswith("sha256:") or len(digest) != 71:
        raise ValueError(f"GitHub did not provide a usable SHA-256 digest for {label}.")
    expected = digest[7:].lower()
    if any(char not in "0123456789abcdef" for char in expected):
        raise ValueError(f"GitHub provided an invalid SHA-256 digest for {label}.")
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"The downloaded {label} failed its SHA-256 integrity check.")


def is_safe_geode_mod_id(mod_id):
    """Accept Geode's dotted author.mod identifiers, never filesystem paths."""
    return bool(re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", str(mod_id or "")))


def select_macos_update_asset(release, architecture=None):
    """Return the exact release ZIP for this Mac architecture, if present."""
    architecture = (architecture or platform.machine()).lower()
    if architecture in ("arm64", "aarch64"):
        asset_name = "GeodeSync-macOS-arm64.zip"
    elif architecture in ("x86_64", "amd64"):
        asset_name = "GeodeSync-macOS-x86_64.zip"
    else:
        raise ValueError(f"Unsupported Mac architecture: {architecture}")

    matches = [asset for asset in release.get("assets", []) if asset.get("name") == asset_name]
    if len(matches) != 1:
        raise FileNotFoundError(f"Release must contain exactly one {asset_name} asset.")
    asset = matches[0]
    size = int(asset.get("size") or 0)
    if size <= 0 or size > MACOS_UPDATE_MAX_BYTES:
        raise ValueError("The Mac update asset has an invalid or excessive size.")
    url = asset.get("browser_download_url", "")
    if not url.startswith("https://github.com/"):
        raise ValueError("The Mac update asset does not have a secure download URL.")
    return asset


def verify_macos_update_digest(expected_digest, actual_digest):
    """Require the checksum GitHub publishes for a release asset."""
    expected_digest = str(expected_digest or "")
    if not expected_digest.startswith("sha256:"):
        raise ValueError("GitHub did not provide a SHA-256 digest for this Mac update.")
    expected_hex = expected_digest[7:].lower()
    if len(expected_hex) != 64 or any(char not in "0123456789abcdef" for char in expected_hex):
        raise ValueError("GitHub provided an invalid SHA-256 digest for this Mac update.")
    if actual_digest.lower() != expected_hex:
        raise ValueError("The downloaded Mac update failed its SHA-256 integrity check.")


def select_app_update_asset(release, platform_name=None, architecture=None):
    """Select one exact official release package for this app build."""
    platform_name = platform_name or ("windows" if IS_WIN else "macos" if IS_MAC else "linux")
    architecture = (architecture or platform.machine()).lower()
    tag = str(release.get("tag_name") or "")
    if (version_sort_key(tag) is None or release.get("draft") or release.get("prerelease")
            or not release.get("published_at")):
        raise ValueError("The update is not a published stable GeodeSync release.")
    if platform_name == "windows":
        candidates = ["GeodeSync-Windows.zip", f"GeodeSync-{tag}-Windows.zip"]
        if not tag.startswith("v"):
            candidates.append(f"GeodeSync-v{tag}-Windows.zip")
    elif platform_name == "linux":
        candidates = [f"GeodeSync-{tag}-Linux.tar.gz", "GeodeSync-Linux.tar.gz"]
    elif platform_name == "macos":
        expected_mac = "GeodeSync-macOS-arm64.zip" if architecture in ("arm64", "aarch64") else "GeodeSync-macOS-x86_64.zip" if architecture in ("x86_64", "amd64") else None
        if expected_mac is None:
            raise ValueError(f"Unsupported Mac architecture: {architecture}")
        candidates = [expected_mac]
    else:
        raise ValueError(f"Unsupported platform: {platform_name}")
    matches = [asset for asset in release.get("assets", []) if asset.get("name") in candidates]
    if not matches:
        raise FileNotFoundError(f"Release must contain a valid package ({candidates[0]}).")
    asset = matches[0]
    expected = asset.get("name")
    url = str(asset.get("browser_download_url") or "")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "github.com" or parsed.path != f"/{GITHUB_REPO}/releases/download/{tag}/{expected}":
        raise ValueError("The update asset URL is not the expected official GitHub release URL.")
    size = int(asset.get("size") or 0)
    if size <= 0 or size > APP_UPDATE_MAX_BYTES:
        raise ValueError("The update package has an invalid or excessive size.")
    return asset


def release_has_app_update(release, platform_name=None, architecture=None):
    """Whether this published release has a valid package for this platform."""
    try:
        select_app_update_asset(release, platform_name, architecture)
    except FileNotFoundError:
        return False
    return True


def validate_app_update_zip(archive, platform_name):
    """Validate package shape, traversal, special files and expanded size."""
    if platform_name == "macos":
        validate_macos_update_zip(archive)
        return
    total = 0
    names = set()
    for info in archive.infolist():
        name = info.filename.replace("\\", "/")
        parts = name.rstrip("/").split("/")
        if name.startswith("/") or any(part in ("", ".", "..") for part in parts) or ":" in name or "\x00" in name:
            raise ValueError("The update archive contains an unsafe path.")
        if platform_name == "windows":
            reserved = {"CON", "PRN", "AUX", "NUL"} | {f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)}
            if any(any(char in part for char in '<>"|?*') or part.endswith((" ", ".")) or part.split(".", 1)[0].upper() in reserved for part in parts):
                raise ValueError("The Windows update archive contains an invalid filename.")
        mode = info.external_attr >> 16
        file_type = stat.S_IFMT(mode)
        if stat.S_ISLNK(mode) or (file_type and file_type not in (stat.S_IFREG, stat.S_IFDIR)):
            raise ValueError("The update archive contains an unsupported special file.")
        canonical_name = name.rstrip("/").casefold() if platform_name == "windows" else name.rstrip("/")
        if canonical_name in names:
            raise ValueError("The update archive contains duplicate paths.")
        total += info.file_size
        if info.file_size > APP_UPDATE_MAX_BYTES or total > APP_UPDATE_MAX_BYTES:
            raise ValueError("The update archive expands beyond the allowed size.")
        names.add(canonical_name)
    if platform_name == "windows" and ("geodesync.exe" not in names or not any(name.startswith("_internal/") for name in names)):
        raise ValueError("The Windows update package is missing required application files.")
    elif platform_name == "linux" and "GeodeSync" not in names:
        raise ValueError("The Linux update package is missing the application executable.")


def safe_extract_app_zip(archive, destination):
    root = os.path.realpath(destination)
    os.makedirs(root, exist_ok=True)
    symlinks = []
    for info in archive.infolist():
        normalized_name = info.filename.replace("\\", "/")
        target = os.path.realpath(os.path.join(root, *normalized_name.split("/")))
        if os.path.commonpath((root, target)) != root:
            raise ValueError("The update archive contains a path outside its staging folder.")
        if info.is_dir():
            os.makedirs(target, exist_ok=True)
            continue
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode):
            link_target = archive.read(info).decode("utf-8", errors="strict").replace("\\", "/")
            resolved_link = os.path.realpath(os.path.join(os.path.dirname(target), link_target))
            if link_target.startswith("/") or os.path.commonpath((root, resolved_link)) != root:
                raise ValueError("The update archive contains an unsafe symbolic link.")
            symlinks.append((info, target, link_target))
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with archive.open(info) as source, open(target, "wb") as output:
            shutil.copyfileobj(source, output)
        if mode & 0o111:
            os.chmod(target, mode & 0o777)
    for info, target, link_target in symlinks:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        os.symlink(link_target, target)


def download_verified_app_update(release, destination, platform_name=None, architecture=None):
    """Download one selected asset, validate its GitHub SHA-256 digest, and stage it."""
    platform_name = platform_name or ("windows" if IS_WIN else "macos" if IS_MAC else "linux")
    asset = select_app_update_asset(release, platform_name, architecture)
    request = urllib.request.Request(asset["browser_download_url"], headers={"User-Agent": "GeodeSync-Updater"})
    with urllib.request.urlopen(request, timeout=60) as response:
        final = urlparse(response.geturl())
        if final.scheme != "https" or final.hostname not in {"github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"}:
            raise ValueError("GitHub redirected the update download to an untrusted host.")
        data = response.read(APP_UPDATE_MAX_BYTES + 1)
    if len(data) != int(asset["size"]) or len(data) > APP_UPDATE_MAX_BYTES:
        raise ValueError("The downloaded update size does not match the release metadata.")
    verify_release_asset_digest(asset, data, "GeodeSync update")
    os.makedirs(destination, exist_ok=True)
    package = os.path.join(destination, asset["name"])
    with open(package, "wb") as stream:
        stream.write(data)
    if platform_name == "windows":
        mark_windows_download(package, asset["browser_download_url"])
    if asset["name"].endswith(".zip"):
        with zipfile.ZipFile(package) as archive:
            validate_app_update_zip(archive, platform_name)
            extracted = os.path.join(destination, "payload")
            safe_extract_app_zip(archive, extracted)
    else:
        extracted = os.path.join(destination, "payload")
        os.makedirs(extracted, exist_ok=True)
        with tarfile.open(package, "r:gz") as archive:
            validate_app_update_tar(archive)
            archive.extractall(extracted, filter="data")
        if not os.path.isfile(os.path.join(extracted, "GeodeSync")):
            raise ValueError("The Linux update package is missing the application executable.")
    if platform_name == "windows":
        mark_windows_download(os.path.join(extracted, "GeodeSync.exe"), asset["browser_download_url"])
    elif platform_name == "macos":
        mark_macos_quarantine(os.path.join(extracted, "GeodeSync.app"))
    return asset, extracted


def mark_windows_download(path, source_url):
    """Retain Windows Mark-of-the-Web so SmartScreen can still evaluate files."""
    if "\n" in source_url or "\r" in source_url:
        raise ValueError("The Windows download source metadata is invalid.")
    with open(path + ":Zone.Identifier", "w", encoding="utf-8", newline="\r\n") as stream:
        stream.write("[ZoneTransfer]\r\nZoneId=3\r\nHostUrl=" + source_url + "\r\n")


def mark_macos_quarantine(app_path):
    """Keep Gatekeeper's first-open check for the downloaded Mac app bundle."""
    import uuid
    quarantine = f"0081;{int(time.time()):x};GeodeSync;{uuid.uuid4()}"
    subprocess.run(["/usr/bin/xattr", "-w", "com.apple.quarantine", quarantine, app_path], check=True, timeout=10)


def _normalized_update_tar_name(name):
    """Normalize harmless tar './' prefixes while retaining strict traversal checks."""
    name = str(name or "").replace("\\", "/")
    if name in ("", ".", "./"):
        return ""
    while name.startswith("./"):
        name = name[2:]
    return name


def validate_app_update_tar(archive):
    total = 0
    names = set()
    for member in archive.getmembers():
        name = _normalized_update_tar_name(member.name)
        if not name:
            continue
        parts = name.rstrip("/").split("/")
        if name.startswith("/") or any(part in ("", ".", "..") for part in parts) or ":" in name or not (member.isfile() or member.isdir()):
            raise ValueError("The Linux update archive contains an unsafe or unsupported entry.")
        canonical_name = name.rstrip("/")
        if canonical_name in names:
            raise ValueError("The Linux update archive contains duplicate paths.")
        names.add(canonical_name)
        total += member.size
        if member.size > APP_UPDATE_MAX_BYTES or total > APP_UPDATE_MAX_BYTES:
            raise ValueError("The Linux update archive expands beyond the allowed size.")
    if "GeodeSync" not in names:
        raise ValueError("The Linux update archive is missing the GeodeSync executable.")


def _application_root():
    if IS_MAC and getattr(sys, "frozen", False):
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(sys.executable))))
    return os.path.dirname(os.path.realpath(sys.executable if getattr(sys, "frozen", False) else __file__))


def _wait_for_process_exit(pid, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if IS_WIN:
            import ctypes
            from ctypes import wintypes
            open_process = ctypes.windll.kernel32.OpenProcess
            open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            open_process.restype = wintypes.HANDLE
            wait_for_single = ctypes.windll.kernel32.WaitForSingleObject
            wait_for_single.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            wait_for_single.restype = wintypes.DWORD
            close_handle = ctypes.windll.kernel32.CloseHandle
            close_handle.argtypes = [wintypes.HANDLE]
            close_handle.restype = wintypes.BOOL
            handle = open_process(0x00100000, False, int(pid))  # SYNCHRONIZE; never signals the process.
            if not handle:
                error = ctypes.windll.kernel32.GetLastError()
                if error == 87:  # ERROR_INVALID_PARAMETER: process no longer exists.
                    return
                raise OSError(error, "Could not wait for the GeodeSync process to close.")
            try:
                result = wait_for_single(handle, min(250, max(0, int((deadline - time.time()) * 1000))))
            finally:
                close_handle(handle)
            if result == 0:
                return
            if result != 258:  # WAIT_TIMEOUT
                raise OSError("Windows could not wait for GeodeSync to close.")
        else:
            try:
                os.kill(int(pid), 0)
            except ProcessLookupError:
                return
            except PermissionError:
                pass
        time.sleep(0.25)
    raise TimeoutError("GeodeSync did not close in time for the update.")


def _apply_staged_update(payload, target, backup, pid):
    """Helper mode: swap a verified staged install and roll back on failure."""
    _wait_for_process_exit(pid)
    target = os.path.abspath(target)
    payload = os.path.abspath(payload)
    backup = os.path.abspath(backup)
    target_parent = os.path.dirname(target)
    try:
        staging_inside_parent = os.path.commonpath((target_parent, payload)) == target_parent and os.path.commonpath((target_parent, backup)) == target_parent
    except ValueError:
        staging_inside_parent = False
    if not staging_inside_parent:
        raise ValueError("Update staging paths are not siblings of the installation.")
    if not os.path.isdir(payload):
        raise FileNotFoundError("The verified update staging folder is missing.")
    moved_old = False
    try:
        if os.path.exists(target):
            os.replace(target, backup)
            moved_old = True
        os.replace(payload, target)
        executable = os.path.join(target, "Contents", "MacOS", "GeodeSync") if IS_MAC else os.path.join(target, "GeodeSync.exe" if IS_WIN else "GeodeSync")
        if not os.path.isfile(executable):
            raise FileNotFoundError("The updated application executable is missing.")
        if IS_MAC:
            mark_macos_quarantine(target)
            subprocess.Popen(["open", target], close_fds=True)
        else:
            if IS_WIN:
                mark_windows_download(executable, "https://github.com/" + GITHUB_REPO + "/releases")
            subprocess.Popen([executable], close_fds=True)
    except Exception:
        if os.path.exists(target):
            shutil.rmtree(target, ignore_errors=True)
        if moved_old and os.path.exists(backup):
            os.replace(backup, target)
        raise
    else:
        shutil.rmtree(backup, ignore_errors=True)
        work_dir = os.path.dirname(backup)
        if IS_WIN:
            try:
                _schedule_windows_update_cleanup(work_dir, target_parent)
            except OSError:
                pass
        else:
            shutil.rmtree(work_dir, ignore_errors=True)


def _schedule_windows_update_cleanup(work_dir, parent):
    """Remove the temporary Windows helper after the OS releases its files."""
    name = os.path.basename(work_dir)
    if not re.fullmatch(r"\.GeodeSync-update-[A-Za-z0-9_-]+", name):
        raise ValueError("The temporary update folder name is invalid.")
    script = os.path.join(parent, f".GeodeSync-cleanup-{name.rsplit('-', 1)[-1]}.cmd")
    relative_target = name
    command = (
        "@echo off\r\n"
        ":retry\r\n"
        f'rmdir /s /q "%~dp0{relative_target}" >nul 2>&1\r\n'
        f'if exist "%~dp0{relative_target}" (timeout /t 1 /nobreak >nul & goto retry)\r\n'
        'del "%~f0" >nul 2>&1\r\n'
    )
    with open(script, "w", encoding="utf-8", newline="") as stream:
        stream.write(command)
    subprocess.Popen(
        ["cmd.exe", "/d", "/c", f'start "" /b "{script}"'],
        cwd=parent,
        close_fds=True,
        creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
    )


def _run_update_helper(encoded):
    payload = json.loads(base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8"))
    _apply_staged_update(payload["payload"], payload["target"], payload["backup"], payload["pid"])


def validate_macos_update_zip(archive):
    """Reject path traversal and unexpected top-level content in a Mac update."""
    app_entries = 0
    expanded_size = 0
    names = set()
    for info in archive.infolist():
        name = info.filename
        normalized = name.replace("\\", "/")
        parts = normalized.rstrip("/").split("/")
        if normalized.startswith("/") or any(part in ("", ".", "..") for part in parts):
            raise ValueError("The Mac update archive contains an unsafe path.")
        canonical_name = normalized.rstrip("/")
        if canonical_name in names:
            raise ValueError("The Mac update archive contains duplicate paths.")
        names.add(canonical_name)
        if normalized.startswith("GeodeSync.app/"):
            app_entries += 1
        elif normalized.startswith("__MACOSX/GeodeSync.app/") or normalized == "__MACOSX/":
            continue
        elif normalized.rstrip("/") == "GeodeSync.app":
            app_entries += 1
        else:
            raise ValueError("The Mac update archive contains unexpected files.")
        if info.file_size > MACOS_UPDATE_MAX_BYTES:
            raise ValueError("A file in the Mac update archive is too large.")
        expanded_size += info.file_size
        if expanded_size > MACOS_UPDATE_MAX_BYTES:
            raise ValueError("The Mac update archive expands beyond the allowed size.")
        unix_mode = info.external_attr >> 16
        if stat.S_ISLNK(unix_mode):
            link_target = archive.read(info).decode("utf-8", errors="strict").replace("\\", "/")
            resolved_target = posixpath.normpath(posixpath.join(posixpath.dirname(normalized), link_target))
            if link_target.startswith("/") or resolved_target == ".." or resolved_target.startswith("../"):
                raise ValueError("The Mac update archive contains an unsafe symbolic link.")
    if app_entries == 0:
        raise ValueError("The Mac update archive does not contain GeodeSync.app.")


def open_url_or_path(path):
    if not path:
        return False
    path_str = str(path)
    if IS_WIN:
        # ShellExecute can show a confusing native "Windows cannot find" dialog
        # for stale or malformed paths (including a bare UNC prefix like "\\\\").
        # Protocol URLs such as steam:// are intentionally delegated to Windows.
        if "://" not in path_str:
            if path_str.strip() in ("\\", "\\\\", "//") or not os.path.exists(path_str):
                return False
        try:
            os.startfile(path_str)
            return True
        except Exception:
            pass
    elif IS_MAC:
        try:
            subprocess.Popen(["open", path_str])
            return True
        except Exception:
            pass
    else:
        try:
            subprocess.Popen(["xdg-open", path_str])
            return True
        except Exception:
            pass

    if "://" in path_str:
        try:
            webbrowser.open(path_str)
            return True
        except Exception:
            pass
    return False


def find_macos_game_app(game_path):
    """Resolve either a Steam game folder or a selected .app bundle."""
    if not game_path:
        return None
    game_path = os.path.abspath(os.path.expanduser(str(game_path)))
    if game_path.lower().endswith(".app"):
        return game_path if os.path.isdir(game_path) else None
    for name in ("Geometry Dash.app", "GeometryDash.app"):
        candidate = os.path.join(game_path, name)
        if os.path.isdir(candidate):
            return candidate
    return None


def validate_macos_game_app(app_path):
    """Return a useful bundle validation error, or None when launchable structure exists."""
    if not app_path or not os.path.isdir(app_path):
        return "Geometry Dash.app was not found in the selected Steam library."
    plist_path = os.path.join(app_path, "Contents", "Info.plist")
    try:
        with open(plist_path, "rb") as stream:
            metadata = plistlib.load(stream)
    except (OSError, plistlib.InvalidFileException, ValueError, ExpatError, TypeError) as exc:
        return f"Geometry Dash.app has a missing or unreadable Info.plist ({exc})."

    executable_name = metadata.get("CFBundleExecutable")
    if not isinstance(executable_name, str) or not executable_name or os.path.basename(executable_name) != executable_name:
        return "Geometry Dash.app has an invalid CFBundleExecutable entry."
    executable = os.path.join(app_path, "Contents", "MacOS", executable_name)
    if not os.path.isfile(executable):
        return f"Geometry Dash.app is incomplete: its executable is missing ({executable_name})."
    if not os.access(executable, os.X_OK):
        return "Geometry Dash.app's main executable is not marked executable. Use Steam's Verify integrity action to restore it."
    return None


def reset_invalid_macos_depot_cache(depot_path, installed_game_path=None):
    """Remove only a malformed Geometry Dash Steam depot cache for a clean retry.

    The installed game is never a valid target: the path must be Steam's exact
    app_322170/depot_322172 content-cache directory, and the cached app bundle
    must exist but fail structural validation.
    """
    if not depot_path or os.path.islink(depot_path) or not os.path.isdir(depot_path):
        return False

    target = os.path.realpath(os.path.abspath(depot_path))
    normalized = os.path.normcase(target).replace("\\", "/").rstrip("/")
    expected_suffix = f"/steamapps/content/app_{APP_ID}/depot_322172"
    if not normalized.endswith(expected_suffix):
        raise ValueError("Refusing to reset a path that is not the Geometry Dash Steam depot cache.")

    installed = os.path.realpath(os.path.abspath(installed_game_path)) if installed_game_path else None
    if installed and (target == installed or target.startswith(installed + os.sep)):
        raise ValueError("Refusing to reset the installed Geometry Dash folder.")

    app_path = find_macos_game_app(target)
    if not app_path:
        return False
    problem = validate_macos_game_app(app_path)
    if not problem:
        return False

    # Do not follow a bundle symlink, even though the parent cache path was
    # checked above. Steam's cache contents are disposable; the live install
    # and save directory are outside this narrowly validated path.
    if os.path.islink(app_path):
        raise ValueError("Refusing to reset a symlinked Geometry Dash.app cache.")
    shutil.rmtree(target)
    return True


def inspect_macos_app_security(app_path=None, runner=None):
    """Collect a small, read-only summary of the running app's macOS trust state.

    This deliberately reports status only: it never removes quarantine metadata,
    changes Gatekeeper settings, or exposes raw command output in support reports.
    """
    if sys.platform != "darwin" and not IS_MAC:
        return None
    runner = runner or subprocess.run
    if not app_path:
        current = os.path.abspath(sys.executable)
        while current and current != os.path.dirname(current):
            if current.lower().endswith(".app") and os.path.isdir(current):
                app_path = current
                break
            current = os.path.dirname(current)
    if not app_path or not os.path.isdir(app_path):
        return {
            "bundle_signature": "app bundle not found",
            "signing_identity": "unknown",
            "gatekeeper": "not checked",
            "quarantine": "unknown",
        }

    def run_status(arguments):
        try:
            return runner(arguments, capture_output=True, text=True, timeout=15, check=False)
        except (OSError, subprocess.SubprocessError):
            return None

    verification = run_status(["/usr/bin/codesign", "--verify", "--deep", "--strict", app_path])
    details = run_status(["/usr/bin/codesign", "-dv", "--verbose=2", app_path])
    assessment = run_status(["/usr/sbin/spctl", "--assess", "--type", "execute", "-vv", app_path])
    quarantine = run_status(["/usr/bin/xattr", "-p", "com.apple.quarantine", app_path])

    detail_text = "\n".join(
        str(getattr(details, field, "") or "") for field in ("stdout", "stderr")
    ) if details else ""
    if re.search(r"(?im)^Signature=adhoc\s*$", detail_text) or re.search(
        r"(?im)^TeamIdentifier=not set\s*$", detail_text
    ):
        identity = "ad-hoc signed (not Apple Developer ID signed)"
    elif re.search(r"(?im)^Authority=Developer ID Application:", detail_text):
        identity = "Apple Developer ID signed"
    elif details and getattr(details, "returncode", 1) == 0:
        identity = "signed; identity not identified"
    else:
        identity = "unsigned or signature details unavailable"

    return {
        "bundle_signature": (
            "valid" if verification and verification.returncode == 0
            else "invalid or unverifiable"
        ),
        "signing_identity": identity,
        "gatekeeper": (
            "accepted" if assessment and assessment.returncode == 0
            else "rejected or not assessed"
        ),
        "quarantine": "present" if quarantine and quarantine.returncode == 0 else "not detected",
    }


def is_steam_library_game_path(path):
    """Recognize a Geometry Dash folder inside any Steam library, including Windows paths."""
    parts = [part.casefold() for part in re.split(r"[/\\]+", str(path or "").strip()) if part]
    for index in range(max(0, len(parts) - 2)):
        if parts[index:index + 2] == ["steamapps", "common"]:
            folder = parts[index + 2]
            if folder in ("geometry dash", "geometrydash", "gd") or folder.startswith("geometry dash") or folder.startswith("geometrydash"):
                return True
    return False


def ensure_local_onedrive_files(folder_path):
    """Ensures OneDrive cloud-only stub files are downloaded locally to prevent WinError 392 or 0x8007016A."""
    if not IS_WIN or not folder_path or not os.path.isdir(folder_path):
        return True, "Path not applicable"
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        target_pattern = os.path.join(folder_path, "*")
        cmd = f'attrib.exe -U -P /s /d "{target_pattern}"'
        subprocess.run(
            cmd,
            shell=True,
            startupinfo=si,
            creationflags=0x08000000,
            timeout=10,
            capture_output=True
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


def install_vc_redist(log_func=None):
    """Downloads and launches the official Microsoft Visual C++ 2015-2022 (x86) Redistributable installer."""
    if not IS_WIN:
        return False, "Microsoft Visual C++ is only required on Windows."
    url = "https://aka.ms/vs/17/release/vc_redist.x86.exe"
    temp_dir = tempfile.gettempdir()
    dest = os.path.join(temp_dir, "vc_redist.x86.exe")
    if log_func:
        log_func("Downloading official Microsoft Visual C++ 2015-2022 (x86) from aka.ms...", "INFO")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GeodeSync-VCRedist"})
        with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as f:
            shutil.copyfileobj(resp, f)
        if log_func:
            log_func("Running Visual C++ setup (accept Windows UAC prompt if shown)...", "INFO")
        subprocess.Popen([dest, "/install", "/passive", "/norestart"])
        return True, "Visual C++ installer started! Complete the setup prompt on your screen."
    except Exception as e:
        webbrowser.open("https://aka.ms/vs/17/release/vc_redist.x86.exe")
        return False, f"Automatic download failed ({e}). Opened official Microsoft download link in your browser."


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


def find_linux_geometry_dash_pids(proc_root="/proc"):
    """Return only processes whose argv contains GeometryDash.exe (Proton)."""
    pids = []
    try:
        entries = os.listdir(proc_root)
    except OSError:
        return pids
    for entry in entries:
        if not entry.isdigit():
            continue
        try:
            with open(os.path.join(proc_root, entry, "cmdline"), "rb") as stream:
                argv = stream.read(1024 * 1024).decode("utf-8", errors="ignore").split("\0")
        except OSError:
            continue
        if any(arg.replace("\\", "/").rsplit("/", 1)[-1].casefold() == "geometrydash.exe" for arg in argv if arg):
            pids.append(int(entry))
    return pids


def desktop_exec_value(path):
    """Quote a filesystem path as one freedesktop .desktop Exec argument."""
    value = str(path).replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$")
    return f'"{value}"'


def request_macos_steam_launch(game_path, runner=None):
    """Ask LaunchServices to route the game request through Steam; this is not proof the game started."""
    app_path = find_macos_game_app(game_path)
    validation_error = validate_macos_game_app(app_path)
    if validation_error:
        return False, validation_error

    runner = runner or subprocess.run
    try:
        result = runner(
            ["/usr/bin/open", f"steam://run/{APP_ID}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"macOS could not pass the launch request to Steam: {exc}"
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip()
        if details:
            details = f"\n\nmacOS reported: {details[:1200]}"
        return False, f"macOS rejected the Steam launch request (exit {result.returncode}).{details}"
    return True, "Steam accepted the Geometry Dash launch request. This confirms dispatch only; Steam must still start the game."


def wait_for_process(check_running, timeout=60, interval=1, clock=time.monotonic, sleep=time.sleep):
    """Wait without blocking the UI-facing caller; Steam can take tens of seconds to start a game."""
    deadline = clock() + max(0, timeout)
    while True:
        try:
            if check_running():
                return True
        except Exception:
            pass
        remaining = deadline - clock()
        if remaining <= 0:
            return False
        sleep(min(interval, remaining))


def _copy_directory_transactionally(source, destination, validator=None):
    """Stage a complete directory beside its destination, then swap with rollback."""
    source = os.path.abspath(source)
    destination = os.path.abspath(destination)
    parent = os.path.dirname(destination)
    if not os.path.isdir(source):
        raise FileNotFoundError(f"Source app bundle does not exist: {source}")
    os.makedirs(parent, exist_ok=True)
    stage_root = tempfile.mkdtemp(prefix=".geodesync-stage-", dir=parent)
    staged = os.path.join(stage_root, os.path.basename(destination))
    previous = os.path.join(stage_root, "previous")
    moved_previous = False
    try:
        shutil.copytree(source, staged, symlinks=True, copy_function=shutil.copy2)
        if validator:
            problem = validator(staged)
            if problem:
                raise OSError(f"The downloaded Geometry Dash app bundle is incomplete: {problem}")
        if os.path.lexists(destination):
            os.replace(destination, previous)
            moved_previous = True
        try:
            os.replace(staged, destination)
        except Exception:
            if moved_previous and os.path.lexists(previous):
                os.replace(previous, destination)
                moved_previous = False
            raise
    finally:
        # Keep the old app in place if stage creation or validation failed.
        if os.path.lexists(previous) and not os.path.lexists(destination):
            os.replace(previous, destination)
        shutil.rmtree(stage_root, ignore_errors=True)


def safe_copy_item(src, dst, max_retries=5):
    """Copy with bounded retries; file replacement is atomic and failures are never hidden."""
    last_error = None
    for i in range(max_retries):
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                parent = os.path.dirname(os.path.abspath(dst))
                os.makedirs(parent, exist_ok=True)
                fd, temporary = tempfile.mkstemp(prefix=".geodesync-copy-", dir=parent)
                os.close(fd)
                try:
                    shutil.copy2(src, temporary)
                    try:
                        with open(temporary, "ab") as copied:
                            copied.flush()
                            os.fsync(copied.fileno())
                    except OSError:
                        pass
                    os.replace(temporary, dst)
                except Exception:
                    # Fallback to direct copy if atomic replace fails
                    shutil.copy2(src, dst)
                finally:
                    try:
                        os.unlink(temporary)
                    except (FileNotFoundError, OSError):
                        pass
            return True
        except OSError as e:
            last_error = e
            if i == max_retries - 1:
                try:
                    shutil.copy2(src, dst)
                    return True
                except Exception:
                    raise
            time.sleep(0.2)
        except Exception as e:
            if i == max_retries - 1:
                try:
                    shutil.copy2(src, dst)
                    return True
                except Exception:
                    raise e
            time.sleep(0.2)
    raise last_error or OSError(f"Could not copy {src} to {dst}.")


def get_app_data_dir():
    if IS_WIN:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "GeodeSync")
    if IS_MAC:
        return os.path.expanduser("~/Library/Application Support/GeodeSync")
    config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(config_home, "geodesync")


def discover_linux_steam_roots(home=None, environ=None, which=None):
    """Find common native/Flatpak Steam roots without assuming one install path."""
    home = os.path.expanduser(home or "~")
    environ = os.environ if environ is None else environ
    which = shutil.which if which is None else which
    xdg_data = environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    candidates = [
        environ.get("STEAM_COMPAT_CLIENT_INSTALL_PATH"),
        environ.get("STEAM_DIR"),
        os.path.join(xdg_data, "Steam"),
        os.path.join(home, ".steam", "steam"),
        os.path.join(home, ".steam", "root"),
        os.path.join(home, ".var", "app", "com.valvesoftware.Steam", "data", "Steam"),
    ]
    steam_command = which("steam") if which else None
    if steam_command:
        current = os.path.dirname(os.path.realpath(steam_command))
        for _ in range(5):
            if os.path.isdir(os.path.join(current, "steamapps")):
                candidates.append(current)
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent

    roots = []
    seen = set()
    for candidate in candidates:
        if not candidate:
            continue
        expanded = os.path.abspath(os.path.expanduser(os.path.expandvars(str(candidate))))
        if not os.path.isdir(expanded):
            continue
        canonical = os.path.realpath(expanded)
        if canonical not in seen:
            roots.append(canonical)
            seen.add(canonical)
    return roots


def discover_steam_game_folders(steam_roots):
    """Return Geometry Dash folders from each Steam root and its listed libraries."""
    folders = []
    seen = set()
    for root in steam_roots:
        libraries = [root]
        vdf_path = os.path.join(root, "steamapps", "libraryfolders.vdf")
        try:
            with open(vdf_path, "r", encoding="utf-8", errors="ignore") as stream:
                content = stream.read()
            libraries.extend(re.findall(r'"path"\s+"((?:\\\\.|[^"\\])*)"', content, re.IGNORECASE))
        except OSError:
            pass
        for library in libraries:
            library = library.replace(r"\\", "\\").replace(r'\"', '"')
            game = os.path.join(os.path.expanduser(library), "steamapps", "common", "Geometry Dash")
            canonical = os.path.realpath(game)
            if canonical not in seen and os.path.isdir(canonical):
                folders.append(canonical)
                seen.add(canonical)
    return folders


def atomic_write_json(path, value):
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".geodesync-write-", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.flush()
            try:
                os.fsync(stream.fileno())
            except OSError:
                pass
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except (FileNotFoundError, OSError):
            pass


def _remove_path(path):
    if os.path.islink(path) or (os.path.exists(path) and not os.path.isdir(path)):
        os.unlink(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)


def _tree_size(path):
    if os.path.isfile(path):
        return os.path.getsize(path)
    total = 0
    for root, _dirs, files in os.walk(path, followlinks=False):
        for filename in files:
            try:
                total += os.path.getsize(os.path.join(root, filename))
            except OSError:
                pass
    return total


def _copy_file_with_retry(source, destination, retries=6, delay=0.4):
    for attempt in range(retries):
        try:
            shutil.copy2(source, destination)
            return
        except OSError as e:
            if getattr(e, "winerror", None) in (32, 33, 5) and attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
            elif attempt < retries - 1:
                time.sleep(delay)
            else:
                raise


def _safe_replace(source, destination, retries=6, delay=0.4):
    for attempt in range(retries):
        try:
            os.replace(source, destination)
            return
        except OSError as e:
            if getattr(e, "winerror", None) in (32, 33, 5) and attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
            elif attempt < retries - 1:
                time.sleep(delay)
            else:
                raise


def _copy_entry(source, destination):
    if os.path.islink(source):
        os.symlink(os.readlink(source), destination)
    elif os.path.isdir(source):
        shutil.copytree(source, destination, symlinks=True, copy_function=_copy_file_with_retry)
    else:
        _copy_file_with_retry(source, destination)


def _rollback_install_transaction(stage_root, destination_root, journal):
    incoming = os.path.join(stage_root, "incoming")
    previous = os.path.join(stage_root, "previous")
    original_items = set(journal.get("original_items", []))
    for name in reversed(journal.get("items", [])):
        if not isinstance(name, str) or name in ("", ".", "..") or "/" in name or "\\" in name or os.path.basename(name) != name:
            continue
        installed_path = os.path.join(destination_root, name)
        staged_path = os.path.join(incoming, name)
        previous_path = os.path.join(previous, name)
        if os.path.lexists(previous_path):
            if os.path.lexists(installed_path):
                _remove_path(installed_path)
            _safe_replace(previous_path, installed_path)
        elif name not in original_items and not os.path.lexists(staged_path) and os.path.lexists(installed_path):
            _remove_path(installed_path)


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


def recover_pending_install_transactions(destination_root):
    """Roll back interrupted game swaps left by a crash or power loss."""
    destination_root = os.path.abspath(destination_root)
    recovered = []
    if not os.path.isdir(destination_root):
        return recovered
    for name in os.listdir(destination_root):
        if not name.startswith(".geodesync-transaction-"):
            continue
        stage_root = os.path.join(destination_root, name)
        if os.path.islink(stage_root):
            raise ValueError("An unfinished GeodeSync recovery folder is a symbolic link; it was left untouched.")
        journal_path = os.path.join(stage_root, "journal.json")
        if not os.path.isfile(journal_path):
            shutil.rmtree(stage_root, ignore_errors=True)
            continue
        with open(journal_path, "r", encoding="utf-8") as stream:
            journal = json.load(stream)
        if os.path.abspath(journal.get("destination", "")) != destination_root:
            raise ValueError("An unfinished GeodeSync transaction points to a different game folder.")
        if journal.get("state") != "committed":
            _rollback_install_transaction(stage_root, destination_root, journal)
        shutil.rmtree(stage_root)
        recovered.append(name)
    return recovered


def install_depot_transactionally(
    source_root, destination_root, validator=None, installed_validator=None,
    reserve_bytes=128 * 1024 * 1024,
):
    """Stage and validate every depot entry; rollback all changed entries on any interruption."""
    source_root = os.path.abspath(source_root)
    destination_root = os.path.abspath(destination_root)
    if not os.path.isdir(source_root) or not os.path.isdir(destination_root):
        raise FileNotFoundError("The Steam depot or Geometry Dash installation folder is missing.")
    items = sorted(os.listdir(source_root))
    if not items or any(
        item in ("", ".", "..") or "/" in item or "\\" in item or os.path.basename(item) != item
        for item in items
    ):
        raise ValueError("The downloaded game depot has no safe top-level files to install.")

    required_bytes = sum(_tree_size(os.path.join(source_root, item)) for item in items) + reserve_bytes
    available_bytes = shutil.disk_usage(destination_root).free
    if available_bytes < required_bytes:
        raise OSError(
            f"Not enough free space to safely stage this game update. "
            f"Need about {required_bytes // (1024 * 1024)} MB; "
            f"{available_bytes // (1024 * 1024)} MB is available."
        )

    stage_root = tempfile.mkdtemp(prefix=".geodesync-transaction-", dir=destination_root)
    incoming = os.path.join(stage_root, "incoming")
    previous = os.path.join(stage_root, "previous")
    os.makedirs(incoming)
    os.makedirs(previous)
    try:
        for item in items:
            _copy_entry(os.path.join(source_root, item), os.path.join(incoming, item))
        if validator:
            problem = validator(incoming)
            if problem:
                raise OSError(f"The downloaded game files failed validation: {problem}")
        journal = {
            "destination": destination_root,
            "state": "installing",
            "items": items,
            "original_items": [item for item in items if os.path.lexists(os.path.join(destination_root, item))],
        }
        atomic_write_json(os.path.join(stage_root, "journal.json"), journal)
        try:
            for item in items:
                destination = os.path.join(destination_root, item)
                old_path = os.path.join(previous, item)
                new_path = os.path.join(incoming, item)
                if os.path.lexists(destination):
                    _safe_replace(destination, old_path)
                _safe_replace(new_path, destination)
            if installed_validator:
                problem = installed_validator(destination_root)
                if problem:
                    raise OSError(f"The installed game failed validation: {problem}")
        except Exception:
            _rollback_install_transaction(stage_root, destination_root, journal)
            raise
    except Exception:
        # Before the journal is written, nothing in the installed game was touched.
        if os.path.exists(os.path.join(stage_root, "journal.json")):
            try:
                _rollback_install_transaction(stage_root, destination_root, journal)
            except Exception:
                # Preserve the journal and old files for recovery at next launch.
                raise
            else:
                shutil.rmtree(stage_root, ignore_errors=True)
        else:
            shutil.rmtree(stage_root, ignore_errors=True)
        raise
    journal["state"] = "committed"
    atomic_write_json(os.path.join(stage_root, "journal.json"), journal)
    shutil.rmtree(stage_root, ignore_errors=True)


class GDManager:
    def __init__(self):
        self.steam_path = self.detect_steam_path()
        self.custom_save_path = None
        self.gd_path = self.detect_gd_path()
        self.manifest_path = self.get_manifest_path()
        self.target_manifest = DEFAULT_MANIFEST
        self.target_gd_version = DEFAULT_TARGET_GD

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
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                output = subprocess.check_output(
                    ["tasklist", "/FI", "IMAGENAME eq steam.exe", "/NH"],
                    startupinfo=si,
                    creationflags=0x08000000
                ).decode(errors="ignore")
                return "steam.exe" in output.lower()
            except Exception:
                return True

        try:
            output = subprocess.check_output(["pgrep", "-xi", "steam"]).decode()
            return bool(output.strip())
        except Exception:
            return True

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
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                output = subprocess.check_output(
                    ["tasklist", "/FI", "IMAGENAME eq GeometryDash.exe", "/NH"],
                    startupinfo=si,
                    creationflags=0x08000000
                ).decode(errors="ignore")
                return "geometrydash.exe" in output.lower()
            except Exception:
                return False

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
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run(
                    ["taskkill", "/F", "/IM", "GeometryDash.exe"],
                    startupinfo=si,
                    creationflags=0x08000000,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
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

    def get_player_stats(self):
        save_dir = self.get_save_data_dir()
        if not save_dir:
            return None
        gm_path = os.path.join(save_dir, "CCGameManager.dat")
        if not os.path.exists(gm_path):
            return None
        try:
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

            return {
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
        except Exception:
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
                                meta = json.loads(zf.read("mod.json").decode("utf-8", errors="ignore"))
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
                        meta = json.loads(zf.read("mod.json").decode("utf-8", errors="ignore"))
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
                            meta = json.loads(zf.read("mod.json").decode("utf-8", errors="ignore"))
                            mid = meta.get("id")
                            mver = meta.get("version", "").lstrip("v")
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

    def get_demon_and_grind_data(self):
        """
        Parses CCGameManager.dat to extract full progression stats, completed demons,
        and active hard grinds (levels with normal progress between 10% and 99%).
        """
        save_dir = self.get_save_data_dir()
        if not save_dir:
            return None
        gm_path = os.path.join(save_dir, "CCGameManager.dat")
        if not os.path.exists(gm_path):
            return None
        try:
            with open(gm_path, "rb") as f:
                raw = f.read()
            dec = decode_geometry_dash_save(raw).decode("utf-8", errors="ignore")

            name_m = re.search(r"<k>playerName</k><s>([^<]+)</s>", dec)
            player_name = name_m.group(1) if name_m else "Player"

            stats = {}
            gs_idx = dec.find("GS_value")
            if gs_idx != -1:
                chunk = dec[gs_idx : gs_idx + 4000]
                for m in re.finditer(r"<k>([0-9]+)</k><s>([0-9]+)</s>", chunk):
                    stats[int(m.group(1))] = int(m.group(2))

            grinds = []
            demons_completed = []

            k2_indices = [m.start() for m in re.finditer(r"<k>k2</k><s>", dec)]
            seen_names = set()

            for idx in k2_indices:
                sub = dec[idx : idx + 1200]
                dict_end = sub.find("</dict>")
                if dict_end != -1:
                    sub = sub[:dict_end]

                name_match = re.search(r"<k>k2</k><s>([^<]+)</s>", sub)
                if not name_match:
                    continue
                lvl_name = name_match.group(1).strip()
                if not lvl_name or lvl_name in seen_names:
                    continue
                seen_names.add(lvl_name)

                pct_match = re.search(r"<k>k19</k><i>([0-9]+)</i>", sub)
                if not pct_match:
                    continue
                percent = int(pct_match.group(1))

                auth_match = re.search(r"<k>k5</k><s>([^<]+)</s>", sub)
                author = auth_match.group(1).strip() if auth_match else "Unknown"

                prac_match = re.search(r"<k>k21</k><i>([0-9]+)</i>", sub)
                practice = int(prac_match.group(1)) if prac_match else 0

                att_match = re.search(r"<k>k18</k><i>([0-9]+)</i>", sub)
                attempts = int(att_match.group(1)) if att_match else 0

                is_demon = ("<k>k25</k><t/>" in sub) or ("<k>k25</k><t />" in sub)
                stars_match = re.search(r"<k>k26</k><i>([0-9]+)</i>", sub)
                stars = int(stars_match.group(1)) if stars_match else (10 if is_demon else 0)

                lvl_info = {
                    "name": lvl_name,
                    "author": author,
                    "percent": percent,
                    "practice": practice,
                    "attempts": attempts,
                    "is_demon": is_demon,
                    "stars": stars
                }

                if percent == 100:
                    if is_demon or stars >= 10:
                        demons_completed.append(lvl_info)
                elif percent >= 15:
                    grinds.append(lvl_info)

            grinds.sort(key=lambda x: (x["percent"], x["practice"]), reverse=True)
            demons_completed.sort(key=lambda x: x["name"].lower())

            return {
                "player_name": player_name,
                "stars": stats.get(6, 0),
                "demons": stats.get(5, len(demons_completed)),
                "diamonds": stats.get(13, 0),
                "coins": stats.get(8, 0),
                "user_coins": stats.get(12, 0),
                "orbs": stats.get(14, 0),
                "moons": stats.get(28, 0),
                "attempts": stats.get(2, 0),
                "jumps": stats.get(1, 0),
                "grinds": grinds[:30],
                "completed_demons": demons_completed[:50]
            }
        except Exception:
            return None

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
        bak_dir = os.path.join(self.gd_path, "Resources_Vanilla_Backup")
        if not os.path.isdir(bak_dir) or not os.listdir(bak_dir):
            return False, "Vanilla backup does not exist yet. Launch with vanilla textures to create one."
        res_dir = os.path.join(self.gd_path, "Resources")

        try:
            files = [f for f in os.listdir(bak_dir) if os.path.isfile(os.path.join(bak_dir, f))]
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

    # ==================== v2.4.0 ENGINES ====================

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

    def fetch_pointercrate_demons(self, limit=100):
        """
        Fetches the official Pointercrate Top Demonlist via public API.
        Returns (success: bool, demons_or_error: list|str).
        """
        import urllib.request
        url = f"https://pointercrate.com/api/v2/demons/listed/?limit={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": f"GeodeSync/{APP_VERSION}"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            demons = []
            for item in data:
                demons.append({
                    "position": item.get("position", 0),
                    "name": item.get("name", "Unknown"),
                    "requirement": item.get("requirement", 100),
                    "video": item.get("video", ""),
                    "publisher": item.get("publisher", {}).get("name", "Unknown") if isinstance(item.get("publisher"), dict) else "Unknown",
                    "verifier": item.get("verifier", {}).get("name", "Unknown") if isinstance(item.get("verifier"), dict) else "Unknown",
                })
            return True, demons
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

    # ==================== SAVE SLOTS ENGINE ====================

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

    # ==================== CUSTOM SFX ENGINE ====================

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

    # ==================== SAVE RESURRECTOR ENGINE ====================

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

    # ==================== MOD PRESETS ENGINE ====================

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



class ModernButton(tk.Canvas):
    def __init__(self, parent, text, command, bg=UI["lilac"], hover_bg=UI["lilac_dark"], fg=UI["text"], height=46, width=None, font=("Segoe UI", 11, "bold")):
        super().__init__(parent, height=height, bg=parent["bg"], highlightthickness=0)
        self.command = command
        self.normal_bg = bg
        self.hover_bg = hover_bg
        self.current_bg = bg
        self.fg = fg
        self.text = text
        self.font = font
        self.height = height
        self.btn_width = width
        self.enabled = True

        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        self.bind("<Configure>", self.draw)

    def draw(self, event=None):
        self.delete("all")
        w = self.winfo_width() if not self.btn_width else self.btn_width
        h = self.height
        r = 10

        if not self.enabled:
            fill = UI["border"]
            text_color = UI["quiet"]
        else:
            fill = self.current_bg
            text_color = self.fg

        self.create_arc((0, 0, r * 2, r * 2), start=90, extent=90, fill=fill, outline="")
        self.create_arc((w - r * 2, 0, w, r * 2), start=0, extent=90, fill=fill, outline="")
        self.create_arc((0, h - r * 2, r * 2, h), start=180, extent=90, fill=fill, outline="")
        self.create_arc((w - r * 2, h - r * 2, w, h), start=270, extent=90, fill=fill, outline="")
        self.create_rectangle((r, 0, w - r, h), fill=fill, outline="")
        self.create_rectangle((0, r, w, h - r), fill=fill, outline="")

        self.create_text(w / 2, h / 2, text=self.text, fill=text_color, font=self.font)

    def on_enter(self, event):
        if self.enabled:
            self.current_bg = self.hover_bg
            self.draw()

    def on_leave(self, event):
        if self.enabled:
            self.current_bg = self.normal_bg
            self.draw()

    def on_click(self, event):
        if self.enabled and self.command:
            self.command()

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        self.draw()

    def set_config(self, text: str, bg: str, hover_bg: str, command=None, fg=None):
        self.text = text
        self.normal_bg = bg
        self.hover_bg = hover_bg
        self.current_bg = bg
        if fg:
            self.fg = fg
        if command:
            self.command = command
        self.draw()


class ScrollableFrame(tk.Frame):
    def __init__(self, parent, bg=UI["background"], *args, **kwargs):
        super().__init__(parent, bg=bg, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_content = tk.Frame(self.canvas, bg=bg)

        self.scrollable_content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self._window_id = self.canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self._window_id, width=e.width)
        )

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            delta = int(-1 * (event.delta / 120)) if hasattr(event, "delta") and event.delta else (1 if getattr(event, "num", None) == 5 else -1)
            self.canvas.yview_scroll(delta, "units")

        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", _on_mousewheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))


class GeodeSyncApp(tk.Tk):
    def report_callback_exception(self, exc_type, exc_value, exc_traceback):
        # Tk callbacks normally print errors to an invisible console in the
        # packaged application. Keep the traceback in the support crash log.
        _global_excepthook(exc_type, exc_value, exc_traceback)
        try:
            err_msg = f"{exc_type.__name__}: {exc_value}"
            self.log(f"Interface error: {err_msg}", "ERROR")
            self.after(0, lambda: self.show_smart_error(
                "Interface Issue Detected",
                f"An unexpected interface issue occurred:\n\n{err_msg}\n\nClick 'Auto-Fix It For Me' below and GeodeSync will unstick your session and restore full functionality.",
                auto_fix_func=self.emergency_unstick
            ))
        except Exception:
            pass

    def __init__(self):
        super().__init__()
        self.title(f"GeodeSync v{APP_VERSION} • Geometry Dash companion")
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        w = min(920, max(820, screen_w - 40))
        h = min(780, max(680, screen_h - 80))
        self.geometry(f"{w}x{h}")
        self.minsize(820, 640)
        self.configure(bg=UI["background"])

        if IS_WIN:
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"geodesync.switcher.v{APP_VERSION}")
            except Exception:
                pass

        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icon.ico")
        if os.path.exists(icon_path):
            try:
                if IS_WIN:
                    self.iconbitmap(icon_path)
            except Exception:
                pass

        self.mgr = GDManager()
        self.data_dir = get_app_data_dir()
        self.settings_path = os.path.join(self.data_dir, "settings.json")
        self.profiles_dir = os.path.join(self.data_dir, "game-profiles")
        self.activity_log_path = os.path.join(self.data_dir, "activity.log")
        self._log_lock = threading.Lock()
        self.recent_events = []
        self.pending_profile_mods = None
        self.settings = self._load_settings()
        stored_game_path = self.settings.get("game_path")
        if stored_game_path and self._is_valid_game_path(stored_game_path):
            self.mgr.gd_path = os.path.abspath(stored_game_path)
            self.mgr.manifest_path = self.mgr.get_manifest_path()
        stored_save_path = self.settings.get("custom_save_path")
        if stored_save_path and os.path.isdir(stored_save_path):
            self.mgr.custom_save_path = os.path.abspath(stored_save_path)
        self.auto_backup_enabled = bool(self.settings.get("auto_backup_enabled", True))
        self.sounds_enabled = bool(self.settings.get("sounds_enabled", False))
        self.discord_rpc_enabled = bool(self.settings.get("discord_rpc_enabled", True))
        self.run_in_bg_enabled = bool(self.settings.get("run_in_bg_enabled", True))
        self.discord_rpc = DiscordRPC(enabled=self.discord_rpc_enabled)
        self._restore_selected_version()
        try:
            self.recovered_transactions = recover_pending_install_transactions(self.mgr.gd_path) if self.mgr.gd_path else []
            self.recovery_error = None
        except Exception as error:
            self.recovered_transactions = []
            self.recovery_error = str(error)
        self.latest_release_url = None
        self._app_update_in_progress = False
        self._staged_app_update = None
        self.last_troubleshooting_error = ""
        self.is_downloading_depot = False
        self._monitor_running = True

        self.create_ui()
        self._load_activity()
        self.refresh_status()
        for recovered in self.recovered_transactions:
            self.log(f"Recovered an unfinished game switch ({recovered}); the previous files were restored.", "WARN")
        if self.recovery_error:
            self.log(f"Could not automatically recover an interrupted game switch: {self.recovery_error}", "ERROR")
            messagebox.showerror(
                "Game recovery needs attention",
                "GeodeSync found an interrupted game switch but could not safely finish restoring it. "
                "The recovery files have been kept in the Geometry Dash folder. Export a support report before trying another switch.",
            )

        threading.Thread(target=self._remote_update_monitor_thread, daemon=True).start()
        threading.Thread(target=self._auto_backup_monitor_thread, daemon=True).start()
        self._start_auto_sync_loop()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _start_auto_sync_loop(self):
        """Starts a periodic 10-second background auto-sync loop to keep status, save progress, and steam lock updated."""
        self.after(10000, self._auto_sync_tick)

    def _auto_sync_tick(self):
        try:
            if not getattr(self, "is_downloading_depot", False):
                self._apply_silent_refresh()
        except Exception:
            pass
        finally:
            self.after(10000, self._auto_sync_tick)

    def _apply_silent_refresh(self):
        """Silently re-reads versions, locks, and progress without disrupting active operations."""
        self.refresh_status()

    def on_close(self):
        # Keep the RPC connection alive after the dashboard is closed.
        if getattr(self, "run_in_bg_enabled", True):
            if IS_WIN and self._start_system_tray():
                self.withdraw()
                self.log("GeodeSync is running in the system tray. Right-click its tray icon to reopen or exit; Discord Rich Presence stays active.", "INFO")
            else:
                self.iconify()
                self.log("GeodeSync is minimized and still running; Discord Rich Presence stays active. Turn Keep in BG on close off to exit.", "INFO")
            return
        self.quit_app()

    def _start_system_tray(self):
        """Start the Windows notification-area icon; return False if unavailable."""
        if getattr(self, "_tray_icon", None) is not None:
            return True
        try:
            import pystray
            from PIL import Image

            base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base_dir, "icon.ico")
            tray_image = Image.open(icon_path).convert("RGBA") if os.path.isfile(icon_path) else Image.new("RGBA", (64, 64), (80, 110, 255, 255))
            tray_icon = pystray.Icon(
                "GeodeSync",
                tray_image,
                "GeodeSync — Geometry Dash companion",
                menu=pystray.Menu(
                    pystray.MenuItem("Open GeodeSync", lambda _icon, _item: self.after(0, self.restore_from_background), default=True),
                    pystray.MenuItem("Exit GeodeSync", lambda _icon, _item: self.after(0, self.quit_app)),
                ),
            )
            self._tray_icon = tray_icon
            threading.Thread(target=self._run_system_tray, args=(tray_icon,), name="GeodeSyncSystemTray", daemon=True).start()
            return True
        except Exception as exc:
            self._tray_icon = None
            self.log(f"System tray could not start; GeodeSync will minimize to the taskbar instead: {exc}", "WARN")
            return False

    def _run_system_tray(self, tray_icon):
        try:
            tray_icon.run()
        except Exception as exc:
            self._tray_icon = None
            try:
                self.after(0, lambda error=exc: self._system_tray_failed(error))
            except Exception:
                pass

    def _system_tray_failed(self, exc):
        self.deiconify()
        self.log(f"System tray stopped unexpectedly; GeodeSync was restored: {exc}", "WARN")

    def quit_app(self):
        tray_icon = getattr(self, "_tray_icon", None)
        self._tray_icon = None
        if tray_icon is not None:
            try:
                tray_icon.stop()
            except Exception:
                pass
        try:
            self._monitor_running = False
            if hasattr(self, "discord_rpc"):
                self.discord_rpc.clear_presence()
                self.discord_rpc.close()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
        os._exit(0)

    def restore_from_background(self):
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
            if IS_WIN:
                try:
                    import ctypes
                    ctypes.windll.user32.ShowWindow(self.winfo_id(), 9)
                    ctypes.windll.user32.SetForegroundWindow(self.winfo_id())
                except Exception:
                    pass
            self.refresh_status()
        except Exception:
            pass

    def toggle_bg_mode(self):
        self.run_in_bg_enabled = not getattr(self, "run_in_bg_enabled", True)
        if self.run_in_bg_enabled:
            self.bg_mode_btn.config(text="🌙 Close to System Tray: ON", fg=UI["lime"])
            self.log("Keep in BG on close: ON. On Windows, closing puts GeodeSync in the system tray and keeps Discord Rich Presence active.", "SUCCESS")
        else:
            self.bg_mode_btn.config(text="🌙 Close to System Tray: OFF", fg=UI["muted"])
            self.log("Keep in BG on close: OFF. Closing the window exits GeodeSync and clears Rich Presence.", "INFO")
        self._save_settings()

    @staticmethod
    def _is_valid_game_path(path):
        if not path or not os.path.isdir(path):
            return False
        if IS_MAC:
            return any(os.path.exists(os.path.join(path, name)) for name in ("Geometry Dash.app", "GeometryDash.app"))
        return os.path.isfile(os.path.join(path, "GeometryDash.exe"))

    def _load_settings(self):
        try:
            with open(self.settings_path, "r", encoding="utf-8") as stream:
                data = json.load(stream)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _restore_selected_version(self):
        manifest = str(self.settings.get("target_manifest", ""))
        # Auto-migrate away from outdated 2.2074 manifest to ensure 2.2081 is the default
        if manifest == "4978051680517726588" or not manifest:
            manifest = DEFAULT_MANIFEST
            self.settings["target_manifest"] = manifest
            self._save_settings()

        choice = next((item for item in KNOWN_VERSIONS.values() if str(item["manifest"]) == manifest), None)
        self.user_selected_target = bool(choice)
        if choice:
            self.mgr.target_manifest = choice["manifest"]
            self.mgr.target_gd_version = choice["ver"]
        else:
            self.mgr.target_manifest = DEFAULT_MANIFEST
            self.mgr.target_gd_version = DEFAULT_TARGET_GD

    def _save_settings(self):
        self.settings.update({
            "schema_version": 1,
            "game_path": self.mgr.gd_path,
            "custom_save_path": getattr(self.mgr, "custom_save_path", None),
            "target_manifest": str(self.mgr.target_manifest),
            "auto_backup_enabled": bool(self.auto_backup_enabled),
            "sounds_enabled": bool(self.sounds_enabled),
            "discord_rpc_enabled": bool(getattr(self, "discord_rpc_enabled", True)),
            "run_in_bg_enabled": bool(getattr(self, "run_in_bg_enabled", True)),
        })
        atomic_write_json(self.settings_path, self.settings)

    def _append_activity(self, line):
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with self._log_lock:
                with open(self.activity_log_path, "a", encoding="utf-8") as stream:
                    stream.write(line + "\n")
                if os.path.getsize(self.activity_log_path) > 512 * 1024:
                    with open(self.activity_log_path, "r", encoding="utf-8", errors="replace") as stream:
                        tail = stream.readlines()[-1200:]
                    with open(self.activity_log_path, "w", encoding="utf-8") as stream:
                        stream.writelines(tail)
        except OSError:
            pass

    def _load_activity(self):
        try:
            with open(self.activity_log_path, "r", encoding="utf-8", errors="replace") as stream:
                lines = stream.readlines()[-300:]
        except OSError:
            return
        self.log_text.config(state="normal")
        self.log_text.insert("end", "".join(lines))
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    @staticmethod
    def _redact_diagnostic_text(text):
        home = os.path.expanduser("~")
        if home and home != "/":
            text = text.replace(home, "~")
        text = re.sub(r"(?i)(token|password|secret|api[_ -]?key)\s*[:=]\s*\S+", r"\1=[REDACTED]", text)
        text = re.sub(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", "[EMAIL]", text, flags=re.I)
        text = re.sub(r"(?i)([A-Z]:\\Users\\)[^\\]+", r"\1[USER]", text)
        text = re.sub(r"/Users/[^/]+", "/Users/[USER]", text)
        return text

    def export_support_report(self):
        destination = filedialog.asksaveasfilename(
            title="Save GeodeSync support report",
            defaultextension=".txt",
            filetypes=[("Text report", "*.txt")],
            initialfile="GeodeSync-support-report.txt",
        )
        if not destination:
            return
        save_dir = self.mgr.get_save_data_dir()
        save_count = 0
        try:
            if save_dir and os.path.isdir(save_dir):
                save_count = sum(name.endswith((".dat", ".dat.bak")) for name in os.listdir(save_dir))
        except OSError:
            pass
        game_version, _color = self.mgr.get_gd_version_info()
        report_lines = [
            "GeodeSync Support Report",
            f"App version: {APP_VERSION}",
            f"Platform: {platform.system()} {platform.release()} ({platform.machine()})",
            f"Python: {platform.python_version()}",
            f"Steam detected: {'yes' if self.mgr.steam_path and os.path.isdir(self.mgr.steam_path) else 'no'}",
            f"Game detected: {'yes' if self.mgr.gd_path and os.path.isdir(self.mgr.gd_path) else 'no'}",
            f"Game folder matches Steam library layout: {'yes' if is_steam_library_game_path(self.mgr.gd_path) else 'no'}",
            f"Game version: {game_version}",
            f"Geode detected: {'yes' if self.mgr.is_geode_installed() else 'no'}",
            f"Steam update lock: {'locked' if self.mgr.is_manifest_locked() else 'unlocked'}",
            f"Selected game version: {self.mgr.target_gd_version}",
            f"Save files detected: {save_count}",
            "",
            "Recent activity (home folders and email addresses are redacted):",
        ]
        if IS_MAC:
            mac_security = inspect_macos_app_security()
            if mac_security:
                report_lines.extend([
                    "",
                    "macOS app security checks (read-only; no Gatekeeper changes made):",
                    f"Bundle signature: {mac_security['bundle_signature']}",
                    f"Signing identity: {mac_security['signing_identity']}",
                    f"Gatekeeper assessment: {mac_security['gatekeeper']}",
                    f"Download quarantine metadata: {mac_security['quarantine']}",
                ])
        if getattr(self, "last_troubleshooting_error", ""):
            report_lines.extend([
                "",
                "Last error entered in Fix a problem:",
                self._redact_diagnostic_text(self.last_troubleshooting_error),
            ])
        try:
            with open(self.activity_log_path, "r", encoding="utf-8", errors="replace") as stream:
                events = stream.readlines()[-250:]
        except OSError:
            events = []
        report_lines.extend(self._redact_diagnostic_text(line.rstrip()) for line in events)
        try:
            with open(destination, "w", encoding="utf-8") as stream:
                stream.write("\n".join(report_lines) + "\n")
        except OSError as error:
            messagebox.showerror("Could not save report", f"GeodeSync could not write the report:\n{error}")
            return
        self.log(f"Saved privacy-filtered support report to {destination}.", "SUCCESS")
        messagebox.showinfo(
            "Support report saved",
            "The report contains app and game status plus recent activity. It does not include save-file contents or mod files. "
            "Review the text before sharing it.",
        )

    def copy_discord_support_card(self, custom_error=None):
        """Formats a rich Markdown diagnostic snippet and copies it to the clipboard, ready to paste into #geodesync-help in Discord."""
        game_version, _ = self.mgr.get_gd_version_info()
        geode_ver = self.mgr.get_installed_geode_version() or ("Detected" if self.mgr.is_geode_installed() else "Not Installed")
        is_locked = "Locked (Protected)" if self.mgr.is_manifest_locked() else "Unlocked (Normal)"
        mods = self.mgr.get_installed_mods()
        stats = self.mgr.get_player_stats()

        recent_logs = []
        try:
            if os.path.exists(self.activity_log_path):
                with open(self.activity_log_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = [l.strip() for l in f.readlines() if l.strip()]
                    recent_logs = lines[-5:]
        except Exception:
            pass

        log_excerpt = "\n".join([f"> `{self._redact_diagnostic_text(l)}`" for l in recent_logs]) if recent_logs else "> *(No recent log entries)*"
        err_line = f"• **Reported Error:** `{self._redact_diagnostic_text(str(custom_error).strip())}`\n" if custom_error else ""

        snippet = (
            f"### 🛡️ GeodeSync v{APP_VERSION} Support Ticket\n"
            f"• **Platform:** {platform.system()} {platform.release()} ({platform.machine()})\n"
            f"• **GD Version:** `{game_version}` (Target: `{self.mgr.target_gd_version}`)\n"
            f"• **Geode Loader:** `{geode_ver}`\n"
            f"• **Steam Update Lock:** `{is_locked}`\n"
            f"{err_line}"
            f"• **Installed Mods:** {len(mods)} mods\n"
            f"• **Player:** {stats['name'] if stats else 'Player'} ({stats['stars'] if stats else 0} ⭐, {stats['demons'] if stats else 0} 👿)\n"
            f"• **Recent Activity:**\n{log_excerpt}\n\n"
            f"*Generated via GeodeSync 1-Click Support*"
        )

        self.clipboard_clear()
        self.clipboard_append(snippet)
        self.play_ding()
        messagebox.showinfo(
            "Copied to Clipboard!",
            "🎉 Diagnostic summary copied to clipboard!\n\n"
            "Head to the Discord server, open the #geodesync-help channel, and press Ctrl+V to paste your setup details so the team can help you immediately."
        )

    def trigger_install_vc_redist(self):
        """Downloads and installs the official Microsoft Visual C++ 2015-2022 Redistributable."""
        self.log("Installing Microsoft Visual C++ 2015-2022 (x86)...", "INFO")
        threading.Thread(target=self._run_install_vc_redist, daemon=True).start()

    def _run_install_vc_redist(self):
        ok, msg = install_vc_redist(log_func=self.log)
        if ok:
            self.log(f"Visual C++: {msg}", "SUCCESS")
            messagebox.showinfo("Visual C++ Installer", msg, parent=self)
        else:
            self.log(f"Visual C++: {msg}", "ERROR")
            messagebox.showwarning("Visual C++ Setup", msg, parent=self)

    def factory_reset_clean_install(self):
        """Emergency Nuclear Reset:
        Backs up player saves safely, clears corrupt/tampered game files, relocates out of OneDrive if applicable,
        and cleanly installs official 2.2081 with Geode.
        """
        if self.is_downloading_depot:
            messagebox.showinfo("Busy", "A download or installation is currently in progress.", parent=self)
            return

        confirm = messagebox.askyesno(
            "Confirm Clean Factory Reset",
            "⚠️ FACTORY RESET & CLEAN INSTALL\n\n"
            "This will completely reset and repair your Geometry Dash installation:\n\n"
            "1. Your player save files (stars, demons, progress) will be SAFELY BACKED UP first.\n"
            "2. Any custom .geode mods will be preserved.\n"
            "3. Tampered, renamed, or corrupted game files will be wiped.\n"
            "4. Official Geometry Dash 2.2081 (Geode Compatible) will be cleanly installed from Steam.\n"
            "5. The latest stable Geode will be installed and verified.\n\n"
            "If your game is currently located in OneDrive, GeodeSync will offer to move it to your official Steam library to fix storage full / write errors.\n\n"
            "Do you want to proceed with the clean factory reset?",
            parent=self
        )
        if not confirm:
            return

        self.log("🧹 Starting Clean Factory Reset & 2.2081 Reinstallation...", "WARNING")
        threading.Thread(target=self._run_factory_reset_clean_install, daemon=True).start()

    def _run_factory_reset_clean_install(self):
        try:
            # 1. Close running processes
            if self.mgr.is_gd_process_running():
                self.log("Terminating running Geometry Dash processes...", "INFO")
                self.mgr.close_gd_process()

            # 2. Backup saves safely
            save_dir = self.mgr.get_save_data_dir()
            if save_dir and os.path.isdir(save_dir):
                self.log(f"Safely archiving player save files from {save_dir}...", "INFO")
                backup_dst = os.path.join(self.data_dir, "emergency_pre_reset_backup")
                os.makedirs(backup_dst, exist_ok=True)
                for f in os.listdir(save_dir):
                    if f.lower().endswith((".dat", ".dat.bak")):
                        try:
                            shutil.copy2(os.path.join(save_dir, f), os.path.join(backup_dst, f))
                        except Exception:
                            pass

            # 3. Handle OneDrive / Target folder relocation
            target_dir = self.mgr.gd_path
            all_installs = self.mgr.find_all_gd_installations()
            steam_inst = next((i for i in all_installs if i["is_steam"]), None)

            if target_dir and "onedrive" in target_dir.casefold():
                if steam_inst:
                    target_dir = steam_inst["path"]
                    self.mgr.gd_path = target_dir
                    self._save_settings()
                    self.log(f"Relocated game path out of OneDrive to Steam: {target_dir}", "SUCCESS")
                elif self.mgr.steam_path:
                    target_dir = os.path.join(self.mgr.steam_path, "steamapps", "common", "Geometry Dash")
                    os.makedirs(target_dir, exist_ok=True)
                    self.mgr.gd_path = target_dir
                    self._save_settings()
                    self.log(f"Created clean destination in Steam library: {target_dir}", "SUCCESS")

            # 4. Clean out corrupt/tampered DLLs and EXEs from target_dir
            if target_dir and os.path.isdir(target_dir):
                for fname in os.listdir(target_dir):
                    fpath = os.path.join(target_dir, fname)
                    if fname.lower() in ("geometrydash.exe", "xinput9_1_0.dll", "geode.dll", "steam_api.dll", "fmod.dll") or fname.lower().endswith(".dll"):
                        try:
                            os.remove(fpath)
                        except Exception:
                            pass

            # 5. Clear depot cache and run automated downgrade to 2.2081
            depot_path = self.mgr.get_depot_path()
            if depot_path and os.path.exists(depot_path):
                shutil.rmtree(depot_path, ignore_errors=True)

            self.mgr.set_manifest_locked(False)
            self.mgr.target_gd_version = "2.2081"
            self.mgr.target_manifest = "8780295549609362522" if IS_MAC else "3816559102876907245"
            self.settings["target_manifest"] = self.mgr.target_manifest
            self._save_settings()

            self.is_downloading_depot = True
            self.primary_btn.set_enabled(False)
            self.log("Requesting fresh, clean Geometry Dash 2.2081 depot from Steam...", "INFO")
            self._run_auto_downgrade_impl()
        except Exception as e:
            self.is_downloading_depot = False
            self.primary_btn.set_enabled(True)
            self.log(f"Factory reset failed: {e}", "ERROR")
            self.after(0, lambda: self.show_smart_error(
                "Factory Reset Issue",
                f"Factory reset ran into an issue:\n{e}\n\nClick 'Auto-Fix It For Me' to retry with Emergency Unstick.",
                auto_fix_func=self.emergency_unstick
            ))

    def emergency_unstick(self):
        """All-in-One Emergency Fix for when users are stuck.
        Kills hung GD processes, unlocks Steam manifest, clears corrupted depot cache,
        resets target to 2.2081, fixes incompatible mods, and prompts clean repair.
        """
        self.log("🆘 Running Emergency Unstick & Self-Repair routine...", "WARNING")

        killed_count = 0
        if IS_WIN:
            try:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                out = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq GeometryDash.exe"], startupinfo=si).decode(errors="ignore")
                if "GeometryDash.exe" in out:
                    subprocess.run(["taskkill", "/F", "/IM", "GeometryDash.exe"], startupinfo=si, capture_output=True)
                    killed_count += 1
            except Exception:
                pass
        elif IS_MAC:
            try:
                subprocess.run(["pkill", "-9", "-f", "Geometry Dash"])
                killed_count += 1
            except Exception:
                pass

        self.mgr.target_gd_version = "2.2081"
        self.mgr.target_manifest = "8780295549609362522" if IS_MAC else "3816559102876907245"
        self.settings["target_manifest"] = self.mgr.target_manifest
        self._save_settings()

        try:
            self.mgr.set_manifest_locked(False)
            self.log("Emergency: Unlocked Steam manifest (read-only removed).", "INFO")
        except Exception as e:
            self.log(f"Emergency note: {e}", "WARN")

        depot_path = self.mgr.get_depot_path()
        cleared_cache = False
        if depot_path and os.path.exists(depot_path):
            try:
                if "steamapps" in depot_path and "content" in depot_path:
                    shutil.rmtree(depot_path, ignore_errors=True)
                    cleared_cache = True
                    self.log("Emergency: Cleared stale Steam download depot cache.", "INFO")
            except Exception:
                pass

        incompat = self.mgr.check_incompatible_mods()
        fixed_mods = []
        for inc in incompat:
            ok, msg = self.mgr.fix_incompatible_mod(inc)
            if ok:
                fixed_mods.append(inc["name"])

        # OneDrive cloud stub unpinning
        onedrive_repaired = False
        if IS_WIN:
            if self.mgr.gd_path and "onedrive" in self.mgr.gd_path.casefold():
                ok_od, _ = ensure_local_onedrive_files(self.mgr.gd_path)
                if ok_od:
                    onedrive_repaired = True
            save_p = self.mgr.get_save_data_dir()
            if save_p and "onedrive" in save_p.casefold():
                ok_od, _ = ensure_local_onedrive_files(save_p)
                if ok_od:
                    onedrive_repaired = True

        # Check for multiple installations: if active is outside Steam but a Steam copy exists, suggest switching!
        switched_to_steam = False
        try:
            all_installs = self.mgr.find_all_gd_installations()
            steam_inst = next((i for i in all_installs if i["is_steam"]), None)
            if steam_inst and self.mgr.gd_path and not is_steam_library_game_path(self.mgr.gd_path):
                if messagebox.askyesno(
                    "Switch to Official Steam Installation?",
                    f"GeodeSync detected your official Steam Geometry Dash installation at:\n{steam_inst['path']}\n\n"
                    f"Your current folder is outside Steam (e.g. OneDrive or portable copy):\n{self.mgr.gd_path}\n\n"
                    "Would you like to switch to the official Steam folder automatically now?",
                    parent=self
                ):
                    self.mgr.gd_path = steam_inst["path"]
                    self.mgr.manifest_path = self.mgr.get_manifest_path()
                    self._save_settings()
                    switched_to_steam = True
                    self.log(f"Emergency: Switched game path to official Steam installation: {self.mgr.gd_path}", "SUCCESS")
        except Exception:
            pass

        self.is_downloading_depot = False
        self.pending_profile_mods = None
        self.progress_frame.pack_forget()
        self.primary_btn.set_enabled(True)
        self.refresh_status()
        self.play_ding()

        od_line = f"• OneDrive Cloud Files: Pinned & Downloaded locally\n" if onedrive_repaired else ""
        steam_line = f"• Game Directory: Switched to official Steam installation\n" if switched_to_steam else ""

        summary_msg = (
            "🎉 Emergency Unstick Completed!\n\n"
            "The following auto-repairs were applied:\n"
            f"• Frozen Game Processes: {'Terminated' if killed_count else 'None running'}\n"
            f"• Target Version: Reset to 2.2081 (Official Geode Baseline)\n"
            f"• Steam Update Lock: Unlocked & Cleared\n"
            f"• Corrupt Download Cache: {'Purged for fresh retry' if cleared_cache else 'Clean'}\n"
            f"• Incompatible Mods Repaired: {', '.join(fixed_mods) if fixed_mods else 'None found (Clean)'}\n"
            f"{od_line}"
            f"{steam_line}\n"
            "Your setup is now un-stuck! You can click '⚡ Fix Geode Mods' to install clean files, or '▶️ Play' if already on 2.2081."
        )
        messagebox.showinfo("Emergency Unstick Complete", summary_msg, parent=self)

    def show_smart_error(self, title, message, auto_fix_func=None, parent=None, is_warning=False):
        """Displays a rich, user-friendly Self-Repair dialog for any error encountered.
        Translates raw exceptions into plain English, provides clear steps, offers an instant
        1-click 'Auto-Fix It For Me' button, a 1-click Discord support ticket copier, and community help.
        """
        dialog = tk.Toplevel(parent or self)
        accent_color = UI["amber"] if is_warning else UI["red"]
        dialog.title(f"🛠️ GeodeSync Self-Repair Assistant • {title}")
        dialog.geometry("640x530")
        dialog.minsize(560, 430)
        dialog.configure(bg=UI["background"])
        dialog.transient(parent or self)
        dialog.grab_set()

        head = tk.Frame(dialog, bg=UI["header"], padx=20, pady=12)
        head.pack(fill="x")

        raw_msg = str(message or "")
        explained_title, explained_steps = explain_error_text(raw_msg)
        display_title = explained_title if (explained_title != "Paste the exact error" and explained_title != "No matching fix found yet") else title

        tk.Label(head, text=f"⚠️ {display_title}", font=("Segoe UI", 13, "bold"), fg=accent_color, bg=UI["header"]).pack(anchor="w")
        tk.Label(head, text="GeodeSync detected an issue. You don't have to troubleshoot alone—click Auto-Fix below!", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", pady=(2, 0))

        content = tk.Frame(dialog, bg=UI["background"], padx=20, pady=12)
        content.pack(fill="both", expand=True)

        tk.Label(content, text="WHAT HAPPENED & WHAT TO DO", font=("Segoe UI", 8, "bold"), fg=UI["quiet"], bg=UI["background"]).pack(anchor="w")
        summary_card = tk.Frame(content, bg=UI["panel"], padx=12, pady=10, highlightbackground=UI["border"], highlightthickness=1)
        summary_card.pack(fill="x", pady=(4, 10))

        fallback_explanation = "GeodeSync encountered an issue with your game or Steam setup. You can use 1-click Auto-Fix to safely repair it automatically."
        explanation_display = explained_steps if (explained_steps and not "Copy the full error" in explained_steps) else (raw_msg[:350] or fallback_explanation)
        tk.Label(
            summary_card,
            text=explanation_display,
            font=("Segoe UI", 9),
            fg=UI["text"],
            bg=UI["panel"],
            wraplength=570,
            justify="left",
            anchor="w"
        ).pack(fill="x")

        tk.Label(content, text="TECHNICAL DETAILS", font=("Segoe UI", 8, "bold"), fg=UI["quiet"], bg=UI["background"]).pack(anchor="w")
        err_box = tk.Text(content, bg=UI["inset"], fg=UI["text"], font=("Consolas", 8), height=4, relief="flat", padx=10, pady=6, wrap="word")
        err_box.pack(fill="both", expand=True, pady=(4, 10))
        err_box.insert("1.0", raw_msg.strip() or "No technical traceback provided.")
        err_box.config(state="disabled")

        def execute_repair():
            dialog.destroy()
            target_fix = auto_fix_func
            if target_fix is None:
                err_low = raw_msg.lower()
                if any(t in err_low for t in ("visual c", "vc++", "vcredist", "msvcp140", "vcruntime140")):
                    target_fix = self.trigger_install_vc_redist
                elif any(t in err_low for t in ("tamper", "corrupt", "clean install", "factory reset", "2.207")):
                    target_fix = self.factory_reset_clean_install
                else:
                    target_fix = self.emergency_unstick

            try:
                target_fix()
            except Exception as ex:
                self.log(f"Auto-fix secondary note: {ex}", "WARN")
                self.emergency_unstick()

        action_frame = tk.Frame(content, bg=UI["panel_alt"], padx=12, pady=10, highlightbackground=UI["lime_dark"], highlightthickness=1)
        action_frame.pack(fill="x", pady=(0, 8))

        tk.Label(action_frame, text="⚡ Recommended Automated Solution:", font=("Segoe UI", 9, "bold"), fg=UI["lime"], bg=UI["panel_alt"]).pack(anchor="w")
        fix_desc = "Runs GeodeSync's automated self-repair: frees hung processes, unlocks Steam files, clears broken download caches, fixes mod conflicts, and resets to 2.2081."
        tk.Label(action_frame, text=fix_desc, font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel_alt"], wraplength=570, justify="left").pack(anchor="w", pady=(2, 6))

        btn_row = tk.Frame(action_frame, bg=UI["panel_alt"])
        btn_row.pack(fill="x")

        tk.Button(
            btn_row,
            text="⚡ Auto-Fix It For Me (Instant Self-Repair)",
            command=execute_repair,
            font=("Segoe UI", 9, "bold"),
            bg=UI["lime"],
            fg=UI["background"],
            activebackground=UI["lime_hover"],
            activeforeground=UI["background"],
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2"
        ).pack(side="left")

        footer = tk.Frame(dialog, bg=UI["header"], padx=20, pady=10)
        footer.pack(fill="x")

        def copy_ticket_with_error():
            self.copy_discord_support_card(custom_error=raw_msg[:500])

        tk.Button(
            footer,
            text="📋 Copy Discord Ticket",
            command=copy_ticket_with_error,
            font=("Segoe UI", 8, "bold"),
            bg="#5865F2",
            fg="#ffffff",
            activebackground="#4752C4",
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2"
        ).pack(side="left")

        tk.Button(
            footer,
            text="💬 Open #geodesync-help",
            command=lambda: webbrowser.open("https://discord.gg/tyQG5xNGCx"),
            font=("Segoe UI", 8, "bold"),
            bg=UI["panel_alt"],
            fg=UI["lilac"],
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2"
        ).pack(side="left", padx=(8, 0))

        tk.Button(
            footer,
            text="Dismiss",
            command=dialog.destroy,
            font=("Segoe UI", 8),
            bg=UI["panel_alt"],
            fg=UI["muted"],
            relief="flat",
            padx=14,
            pady=5,
            cursor="hand2"
        ).pack(side="right")

    def show_error(self, title, message, auto_fix_func=None, parent=None):
        return self.show_smart_error(title, message, auto_fix_func=auto_fix_func, parent=parent, is_warning=False)

    def open_whats_new_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title(f"What's New in GeodeSync v{APP_VERSION}")
        dialog.geometry("580x480")
        dialog.minsize(500, 380)
        dialog.configure(bg=UI["background"])
        dialog.transient(self)
        dialog.grab_set()

        head = tk.Frame(dialog, bg=UI["header"], padx=20, pady=14)
        head.pack(fill="x")
        tk.Label(head, text=f"🚀 What's New in v{APP_VERSION}", font=("Segoe UI", 14, "bold"), fg=UI["lime"], bg=UI["header"]).pack(anchor="w")
        tk.Label(head, text="Latest companion features, unstick safeguards & stability polish.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", pady=(2, 0))

        content = tk.Frame(dialog, bg=UI["background"], padx=20, pady=16)
        content.pack(fill="both", expand=True)

        text_widget = tk.Text(content, bg=UI["panel"], fg=UI["text"], font=("Segoe UI", 9), padx=14, pady=14, relief="flat", highlightbackground=UI["border"], highlightthickness=1, wrap="word")
        text_widget.pack(fill="both", expand=True)

        notes = (
            f"⚡ GEODESYNC v{APP_VERSION} CHANGELOG\n"
            "───────────────────────────────────────────────\n\n"
            "🆘 1. Emergency Unstick & Auto-Repair Wizard:\n"
            "• Fixed users getting stuck on v2.207 or failed Steam downloads!\n"
            "• In 1 click, terminates frozen game processes, resets target to 2.2081, unlocks Steam manifest, clears corrupted download caches, and repairs broken mods.\n\n"
            "🔄 2. Live 10-Second Auto-Sync:\n"
            "• GeodeSync automatically checks your game status, running state, and save files every 10 seconds.\n"
            "• Real-time updates without having to reopen or refresh the app.\n\n"
            "🎮 3. Live Demon & Level Grind on Discord RPC:\n"
            "• When you're playing Geometry Dash, Discord Rich Presence now shows your live level name and progress (e.g. 'Dead Device (99%) · 42 Demons')!\n\n"
            "💬 4. Official Discord Community & 1-Click Ticket Copier:\n"
            "• Added a Discord Community button directly in the header.\n"
            "• 1-Click 'Copy Discord Ticket' copies a redacted diagnostics card ready to paste into #geodesync-help.\n\n"
            "🔍 5. Toolbox Quick Search Bar:\n"
            "• Instantly filter any of the 20 companion tools and mods in real time."
        )
        text_widget.insert("1.0", notes)
        text_widget.config(state="disabled")

        btn_row = tk.Frame(dialog, bg=UI["header"], padx=20, pady=10)
        btn_row.pack(fill="x")
        tk.Button(btn_row, text="💬 Discord Community", command=lambda: webbrowser.open("https://discord.gg/tyQG5xNGCx"), font=("Segoe UI", 8, "bold"), bg="#5865F2", fg="#ffffff", relief="flat", padx=12, pady=5, cursor="hand2").pack(side="left")
        tk.Button(btn_row, text="Close", command=dialog.destroy, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["muted"], relief="flat", padx=14, pady=5, cursor="hand2").pack(side="right")

    def open_troubleshooter(self, prefill=""):
        dialog = tk.Toplevel(self)
        dialog.title("GeodeSync · Fix a problem")
        dialog.geometry("650x590")
        dialog.minsize(560, 470)
        dialog.configure(bg=UI["background"])
        dialog.transient(self)

        header = tk.Frame(dialog, bg=UI["header"], padx=20, pady=14)
        header.pack(fill="x")
        tk.Label(header, text="Fix a problem", font=("Segoe UI", 14, "bold"), fg=UI["text"], bg=UI["header"]).pack(anchor="w")
        tk.Label(
            header,
            text="Run a safe check or paste the exact error. GeodeSync checks common causes and gives safe next steps; it never guesses at a risky repair.",
            font=("Segoe UI", 8), fg=UI["muted"], bg=UI["header"], wraplength=590, justify="left",
        ).pack(anchor="w", pady=(3, 0))

        content = tk.Frame(dialog, bg=UI["background"], padx=18, pady=14)
        content.pack(fill="both", expand=True)
        tk.Label(content, text="What did the error say? (optional)", font=("Segoe UI", 9, "bold"), fg=UI["text"], bg=UI["background"]).pack(anchor="w")
        error_input = tk.Text(content, height=4, wrap="word", font=("Segoe UI", 9), bg=UI["inset"], fg=UI["text"], insertbackground=UI["text"], relief="flat", padx=8, pady=6)
        error_input.pack(fill="x", pady=(5, 8))
        if prefill:
            error_input.insert("1.0", str(prefill)[:3000])

        actions = tk.Frame(content, bg=UI["background"])
        actions.pack(fill="x", pady=(0, 8))
        result = tk.Text(content, wrap="word", font=("Segoe UI", 9), bg=UI["panel"], fg=UI["text"], relief="flat", padx=10, pady=9, height=13)
        result.pack(fill="both", expand=True)
        result.insert("1.0", "Choose Check Setup or paste an error and choose Explain Error.")
        result.config(state="disabled")

        def show_result(title, detail, steps):
            result.config(state="normal")
            result.delete("1.0", "end")
            result.insert("end", f"{title}\n\n{detail}\n\nWhat to do\n{steps}")
            result.config(state="disabled")

        def explain():
            raw = error_input.get("1.0", "end").strip()
            self.last_troubleshooting_error = raw[:3000]
            title, steps = explain_error_text(raw)
            show_result(title, "GeodeSync matched this message to a known troubleshooting guide." if title != "No matching fix found yet" else "GeodeSync does not recognize this message, so it will not change files.", steps)
            if raw and title != "Paste the exact error":
                autofix_action_btn.pack(side="left", padx=(0, 6), before=copy_btn)

        def scan():
            result.config(state="normal")
            result.delete("1.0", "end")
            result.insert("end", "Checking Steam and game files…\nThis read-only check can take a few seconds.")
            result.config(state="disabled")
            def worker():
                try:
                    findings = scan_installation_issues(
                        self.mgr,
                        recovery_error=self.recovery_error,
                    )
                    def finish():
                        if not dialog.winfo_exists():
                            return
                        blocks = []
                        for finding in findings:
                            blocks.append(f"{finding['title']}\n\n{finding['detail']}\n\nWhat to do\n{finding['steps']}")
                        show_result("Setup check", "\n\n──────────────\n\n".join(blocks), "Use Export Report if you still need help.")
                        if findings:
                            autofix_action_btn.pack(side="left", padx=(0, 6), before=copy_btn)
                except Exception as error:
                    error_text = str(error)
                    def fail():
                        if dialog.winfo_exists():
                            show_result("Check could not finish", "The check stopped safely without changing game files.", f"{error_text}\n\nPaste this message into Explain Error or export a report.")
                    self.after(0, fail)
                    return
                self.after(0, finish)
            threading.Thread(target=worker, daemon=True).start()

        def copy_steps():
            text = result.get("1.0", "end").strip()
            dialog.clipboard_clear()
            dialog.clipboard_append(text)
            messagebox.showinfo("Copied", "The troubleshooting steps are copied. You can paste them into chat.", parent=dialog)

        copy_btn = tk.Button(actions, text="Copy Steps", command=copy_steps, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["muted"], relief="flat", padx=10, pady=5, cursor="hand2")
        copy_btn.pack(side="right")

        tk.Button(actions, text="Check Setup", command=scan, font=("Segoe UI", 8, "bold"), bg=UI["lime"], fg=UI["background"], relief="flat", padx=10, pady=5, cursor="hand2").pack(side="left", padx=(0, 6))
        tk.Button(actions, text="Explain Error", command=explain, font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=UI["lilac"], relief="flat", padx=10, pady=5, cursor="hand2").pack(side="left", padx=(0, 6))
        autofix_action_btn = tk.Button(actions, text="⚡ Auto-Fix Found Issue", command=lambda: [self.emergency_unstick(), scan()], font=("Segoe UI", 8, "bold"), bg=UI["lime"], fg=UI["background"], relief="flat", padx=10, pady=5, cursor="hand2")
        tk.Button(actions, text="🆘 Emergency Unstick", command=self.emergency_unstick, font=("Segoe UI", 8, "bold"), bg=UI["amber"], fg=UI["background"], relief="flat", padx=10, pady=5, cursor="hand2").pack(side="left", padx=(0, 6))
        tk.Button(actions, text="📥 Install Visual C++", command=self.trigger_install_vc_redist, font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=UI["lime"], relief="flat", padx=10, pady=5, cursor="hand2").pack(side="left", padx=(0, 6))
        tk.Button(actions, text="🧹 Factory Reset GD", command=self.factory_reset_clean_install, font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=UI["red"], relief="flat", padx=10, pady=5, cursor="hand2").pack(side="left")

        footer = tk.Frame(dialog, bg=UI["header"], padx=18, pady=10)
        footer.pack(fill="x")
        tk.Button(footer, text="Export Report", command=self.export_support_report, font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=UI["amber"], relief="flat", padx=10, pady=5, cursor="hand2").pack(side="left")
        tk.Button(footer, text="📋 Copy Discord Ticket", command=self.copy_discord_support_card, font=("Segoe UI", 8, "bold"), bg="#5865F2", fg="#ffffff", relief="flat", padx=10, pady=5, cursor="hand2").pack(side="left", padx=(8, 0))
        tk.Button(
            footer,
            text="💬 Discord Help",
            command=lambda: self.open_wilbot_support(),
            font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=UI["lilac"],
            relief="flat", padx=10, pady=5, cursor="hand2",
        ).pack(side="left", padx=(8, 0))
        tk.Button(footer, text="Close", command=dialog.destroy, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["muted"], relief="flat", padx=12, pady=5, cursor="hand2").pack(side="right")

    def open_wilbot_support(self):
        """Open the official GeodeSync help channel; no diagnostic data is sent automatically."""
        support_url = "https://discord.com/channels/1503910985524711476/1563643888537698314"
        try:
            opened = webbrowser.open(support_url)
        except Exception:
            opened = False
        if not opened:
            messagebox.showerror(
                "Could not open support",
                "Open the WilCord server and choose #geodesync-help. No files or diagnostic details were sent.",
            )
            return
        messagebox.showinfo(
            "GeodeSync support",
            "The GeodeSync help channel is open. Start a support ticket and mention @WilBot.\n\n"
            "Your report stays on this device until you choose Export Report and attach it. Review it before sharing.",
        )

    def create_ui(self):
        # Update Banner
        self.update_banner = tk.Frame(self, bg=UI["lime_dark"], padx=18, pady=9)
        self.update_label = tk.Label(self.update_banner, text="Update available", font=("Segoe UI", 9, "bold"), fg=UI["lime"], bg=UI["lime_dark"])
        self.update_label.pack(side="left")

        self.update_action_btn = tk.Button(self.update_banner, text="Update now", command=lambda: self.start_self_update(auto_install=True), font=("Segoe UI", 8, "bold"), bg=UI["lime"], fg=UI["background"], activebackground=UI["lime_hover"], activeforeground=UI["text"], relief="flat", padx=12, pady=4, cursor="hand2")
        self.update_action_btn.pack(side="right")

        # Header banner
        self.header_frame = tk.Frame(self, bg=UI["header"], padx=24, pady=14)
        self.header_frame.pack(fill="x")

        title_box = tk.Frame(self.header_frame, bg=UI["header"])
        title_box.pack(side="left")

        title = tk.Label(title_box, text=f"⚡  GeodeSync  ·  v{APP_VERSION}", font=("Segoe UI", 16, "bold"), fg=UI["text"], bg=UI["header"])
        title.pack(anchor="w")

        subtitle = tk.Label(title_box, text="High-Performance Companion & Mod Manager for Geometry Dash", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["header"])
        subtitle.pack(anchor="w")

        badge_box = tk.Frame(self.header_frame, bg=UI["header"])
        badge_box.pack(side="right")

        discord_hdr_btn = tk.Button(
            badge_box,
            text="💬 Discord Community",
            command=lambda: webbrowser.open("https://discord.gg/tyQG5xNGCx"),
            font=("Segoe UI", 8, "bold"),
            bg="#5865F2",
            fg="#ffffff",
            activebackground="#4752C4",
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
        )
        discord_hdr_btn.pack(side="right", padx=(6, 0))

        help_btn = tk.Button(badge_box, text="How it works", command=self.show_help_dialog, font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=UI["lilac"], activebackground=UI["border"], activeforeground=UI["text"], relief="flat", padx=12, pady=6, cursor="hand2")
        help_btn.pack(side="right", padx=(4, 0))

        # Navigation Bar
        self.nav_frame = tk.Frame(self, bg=UI["header"], padx=20, pady=0)
        self.nav_frame.pack(fill="x")

        self.nav_tabs = [
            ("dashboard", "⚡ Dashboard"),
            ("store", "🛍️ Mod Store"),
            ("demonlist", "🏆 Demonlist"),
            ("jukebox", "🎵 Jukebox & SFX"),
            ("saves", "💾 Save Hub"),
            ("toolbox", "🛠️ Toolbox"),
        ]
        self.tab_buttons = {}
        for tab_id, tab_label in self.nav_tabs:
            btn = tk.Button(
                self.nav_frame,
                text=tab_label,
                font=("Segoe UI", 9, "bold"),
                bg=UI["panel_alt"] if tab_id == "dashboard" else UI["header"],
                fg=UI["lime"] if tab_id == "dashboard" else UI["muted"],
                activebackground=UI["panel_alt"],
                activeforeground=UI["text"],
                relief="flat",
                padx=14,
                pady=7,
                cursor="hand2",
                command=lambda tid=tab_id: self.switch_main_tab(tid),
            )
            btn.pack(side="left", padx=(0, 4))
            self.tab_buttons[tab_id] = btn

        # Main Body
        body = tk.Frame(self, bg=UI["background"], padx=20, pady=12)
        body.pack(fill="both", expand=True)

        self.tab_container = tk.Frame(body, bg=UI["background"])
        self.tab_container.pack(fill="both", expand=True)

        self.tab_frames = {
            "dashboard": tk.Frame(self.tab_container, bg=UI["background"]),
            "store": tk.Frame(self.tab_container, bg=UI["background"]),
            "demonlist": tk.Frame(self.tab_container, bg=UI["background"]),
            "jukebox": tk.Frame(self.tab_container, bg=UI["background"]),
            "saves": tk.Frame(self.tab_container, bg=UI["background"]),
            "toolbox": tk.Frame(self.tab_container, bg=UI["background"]),
        }
        self.tab_frames["dashboard"].pack(fill="both", expand=True)

        # 1. CONSOLIDATED HERO DASHBOARD (Player Profile + Game Setup + Primary Action)
        self.guide_card = tk.Frame(self.tab_frames["dashboard"], bg=UI["panel"], padx=18, pady=14, highlightbackground=UI["border"], highlightthickness=1)
        self.guide_card.pack(fill="x", pady=(0, 10))

        hero_top = tk.Frame(self.guide_card, bg=UI["panel"])
        hero_top.pack(fill="x", pady=(0, 10))

        # Left: Player identity & live stats
        p_left = tk.Frame(hero_top, bg=UI["panel"])
        p_left.pack(side="top", fill="x", expand=True)

        p_name_row = tk.Frame(p_left, bg=UI["panel"])
        p_name_row.pack(anchor="w")

        tk.Label(p_name_row, text="PLAYER", font=("Segoe UI", 7, "bold"), fg=UI["quiet"], bg=UI["panel"]).pack(side="left")
        self.player_name_lbl = tk.Label(p_name_row, text="Reading save...", font=("Segoe UI", 10, "bold"), fg=UI["lime"], bg=UI["panel"])
        self.player_name_lbl.pack(side="left", padx=(6, 0))

        self.refresh_stats_btn = tk.Label(p_name_row, text="🔄", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"], cursor="hand2")
        self.refresh_stats_btn.pack(side="left", padx=(6, 0))
        self.refresh_stats_btn.bind("<Button-1>", lambda e: self.update_player_stats_ui())

        self.stats_chips_frame = tk.Frame(p_left, bg=UI["panel"])
        self.stats_chips_frame.pack(anchor="w", pady=(3, 0))

        def _make_stat_chip(parent, icon, text_val, fg_color):
            f = tk.Frame(parent, bg=UI["panel_alt"], padx=6, pady=2, highlightbackground=UI["border"], highlightthickness=1)
            f.pack(side="left", padx=(0, 3))
            tk.Label(f, text=icon, font=("Segoe UI", 8), fg=fg_color, bg=UI["panel_alt"]).pack(side="left", padx=(0, 2))
            lbl = tk.Label(f, text=text_val, font=("Segoe UI", 8, "bold"), fg=UI["text"], bg=UI["panel_alt"])
            lbl.pack(side="left")
            return lbl

        self.stat_stars_lbl = _make_stat_chip(self.stats_chips_frame, "⭐", "0 Stars", UI["amber"])
        self.stat_demons_lbl = _make_stat_chip(self.stats_chips_frame, "👿", "0 Demons", UI["lilac"])
        self.stat_moons_lbl = _make_stat_chip(self.stats_chips_frame, "🌙", "0 Moons", "#66b3ff")
        self.stat_diamonds_lbl = _make_stat_chip(self.stats_chips_frame, "💎", "0 Diamonds", "#00e5ff")
        self.stat_coins_lbl = _make_stat_chip(self.stats_chips_frame, "🪙", "0 Coins", UI["amber"])
        self.stat_orbs_lbl = _make_stat_chip(self.stats_chips_frame, "🔮", "0 Orbs", "#e056fd")

        # Right: Game setup badges
        p_right = tk.Frame(hero_top, bg=UI["panel"])
        p_right.pack(side="top", fill="x", pady=(6, 0))

        setup_chips_row = tk.Frame(p_right, bg=UI["panel"])
        setup_chips_row.pack(anchor="w")

        self.ver_badge = tk.Label(setup_chips_row, text="GD ...", font=("Segoe UI", 8, "bold"), fg=UI["lime"], bg=UI["lime_dark"], padx=6, pady=3, cursor="hand2")
        self.ver_badge.pack(side="left", padx=2)
        self.ver_badge.bind("<Button-1>", lambda e: self.open_whats_new_dialog())

        self.geode_badge = tk.Label(setup_chips_row, text="Geode ...", font=("Segoe UI", 8, "bold"), fg=UI["lilac"], bg=UI["lilac_dark"], padx=6, pady=3, cursor="hand2")
        self.geode_badge.pack(side="left", padx=2)
        self.geode_badge.bind("<Button-1>", lambda e: self.manual_update_geode())

        self.lock_badge = tk.Label(setup_chips_row, text="Steam ...", font=("Segoe UI", 8, "bold"), fg=UI["amber"], bg=UI["panel_alt"], padx=6, pady=3, cursor="hand2")
        self.lock_badge.pack(side="left", padx=2)
        self.lock_badge.bind("<Button-1>", lambda e: self.toggle_steam_lock())

        self.steam_badge = tk.Label(setup_chips_row, text="Steam", font=("Segoe UI", 8, "bold"), fg=UI["muted"], bg=UI["panel_alt"], padx=6, pady=3)
        self.steam_badge.pack(side="left", padx=2)

        self.saves_badge = tk.Label(setup_chips_row, text="Saves", font=("Segoe UI", 8, "bold"), fg=UI["muted"], bg=UI["panel_alt"], padx=6, pady=3)
        self.saves_badge.pack(side="left", padx=2)

        self.opt_badge = tk.Label(setup_chips_row, text="🧹 Optimizer", font=("Segoe UI", 8, "bold"), fg=UI["lime"], bg=UI["panel_alt"], padx=6, pady=3, cursor="hand2")
        self.opt_badge.pack(side="left", padx=2)
        self.opt_badge.bind("<Button-1>", lambda e: self.open_save_optimizer_dialog())

        self.slots_badge = tk.Label(setup_chips_row, text="💾 Slots", font=("Segoe UI", 8, "bold"), fg=UI["amber"], bg=UI["panel_alt"], padx=6, pady=3, cursor="hand2")
        self.slots_badge.pack(side="left", padx=2)
        self.slots_badge.bind("<Button-1>", lambda e: self.open_save_slots_dialog())

        self.sfx_badge = tk.Label(setup_chips_row, text="💥 SFX", font=("Segoe UI", 8, "bold"), fg=UI["lilac"], bg=UI["panel_alt"], padx=6, pady=3, cursor="hand2")
        self.sfx_badge.pack(side="left", padx=2)
        self.sfx_badge.bind("<Button-1>", lambda e: self.open_soundpack_hub())

        self.vault_badge = tk.Label(setup_chips_row, text="🗝️ Vaults", font=("Segoe UI", 8, "bold"), fg=UI["amber"], bg=UI["panel_alt"], padx=6, pady=3, cursor="hand2")
        self.vault_badge.pack(side="left", padx=2)
        self.vault_badge.bind("<Button-1>", lambda e: self.open_vault_helper())

        self.salvage_badge = tk.Label(setup_chips_row, text="🛡️ Salvager", font=("Segoe UI", 8, "bold"), fg=UI["lime"], bg=UI["panel_alt"], padx=6, pady=3, cursor="hand2")
        self.salvage_badge.pack(side="left", padx=2)
        self.salvage_badge.bind("<Button-1>", lambda e: self.open_corrupt_save_resurrector())

        # Hero Center: Status badge & description
        self.guide_badge = tk.Label(self.guide_card, text="CHECKING", font=("Segoe UI", 7, "bold"), fg=UI["lime"], bg=UI["lime_dark"], padx=6, pady=2)
        self.guide_badge.pack(anchor="w", pady=(0, 2))

        self.guide_title = tk.Label(self.guide_card, text="Checking your setup...", font=("Segoe UI", 13, "bold"), fg=UI["text"], bg=UI["panel"])
        self.guide_title.pack(anchor="w", pady=(0, 1))

        self.guide_desc = tk.Label(self.guide_card, text="GeodeSync is ready.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"], wraplength=780, justify="left")
        self.guide_desc.pack(anchor="w", pady=(0, 8))

        # Real-time progress bar frame
        self.progress_frame = tk.Frame(self.guide_card, bg=UI["panel"])
        self.progress_lbl = tk.Label(self.progress_frame, text="Working...", font=("Segoe UI", 8, "bold"), fg=UI["lime"], bg=UI["panel"])
        self.progress_lbl.pack(anchor="w", pady=(0, 2))
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Cyber.Horizontal.TProgressbar", background=UI["lime"], troughcolor=UI["inset"], bordercolor=UI["panel"], lightcolor=UI["lime"], darkcolor=UI["lime_hover"])
        self.progress_bar = ttk.Progressbar(self.progress_frame, style="Cyber.Horizontal.TProgressbar", orient="horizontal", mode="determinate", length=400)
        self.progress_bar.pack(fill="x", pady=(0, 4))

        # Primary Action Button
        self.primary_btn = ModernButton(
            self.guide_card,
            text="Checking...",
            command=None,
            bg=UI["lime"],
            hover_bg=UI["lime_hover"],
            fg=UI["background"],
            height=44,
            font=("Segoe UI", 11, "bold")
        )
        self.primary_btn.pack(fill="x")

        # Launch presets row
        launch_presets_row = tk.Frame(self.guide_card, bg=UI["panel"])
        launch_presets_row.pack(fill="x", pady=(8, 0))
        tk.Label(launch_presets_row, text="LAUNCH PRESETS:", font=("Segoe UI", 7, "bold"), fg=UI["quiet"], bg=UI["panel"]).pack(side="left", padx=(0, 8))

        def _add_preset_chip(lbl_text, mode_id, color):
            b = tk.Button(
                launch_presets_row,
                text=lbl_text,
                command=lambda: self.apply_and_notify_preset(mode_id),
                font=("Segoe UI", 8, "bold"),
                bg=UI["panel_alt"],
                fg=color,
                activebackground=UI["border"],
                activeforeground=UI["text"],
                relief="flat",
                padx=8,
                pady=2,
                cursor="hand2"
            )
            b.pack(side="left", padx=(0, 6))
            return b

        _add_preset_chip("⚡ Boosted (High Priority)", "boosted", UI["lime"])
        _add_preset_chip("🎮 Vanilla (No Mods)", "vanilla", UI["amber"])
        _add_preset_chip("🏆 Tournament (Legal)", "tournament", UI["lilac"])
        _add_preset_chip("🌐 Globed (Multiplayer)", "globed", "#00e5ff")

        # 4 FEATURED HUB CARDS (Modern AAA Dashboard Layout)
        hub_grid = tk.Frame(self.tab_frames["dashboard"], bg=UI["background"])
        hub_grid.pack(fill="both", expand=True, pady=(2, 0))
        hub_grid.columnconfigure(0, weight=1)
        hub_grid.columnconfigure(1, weight=1)
        hub_grid.rowconfigure(0, weight=1)
        hub_grid.rowconfigure(1, weight=1)

        def _make_hub_card(grid_row, grid_col, icon, title, desc, btn_text, cmd, border_color):
            card = tk.Frame(hub_grid, bg=UI["panel"], padx=14, pady=10, highlightbackground=border_color, highlightthickness=1)
            card.grid(row=grid_row, column=grid_col, sticky="nsew", padx=4, pady=4)

            top_r = tk.Frame(card, bg=UI["panel"])
            top_r.pack(fill="x")
            tk.Label(top_r, text=icon, font=("Segoe UI", 11), fg=border_color, bg=UI["panel"]).pack(side="left", padx=(0, 6))
            tk.Label(top_r, text=title, font=("Segoe UI", 10, "bold"), fg=UI["text"], bg=UI["panel"]).pack(side="left")

            tk.Label(card, text=desc, font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"], justify="left", wraplength=340).pack(anchor="w", pady=(4, 8), fill="x", expand=True)

            action = tk.Button(
                card,
                text=btn_text,
                command=cmd,
                font=("Segoe UI", 8, "bold"),
                bg=UI["panel_alt"],
                fg=border_color,
                activebackground=border_color,
                activeforeground=UI["background"],
                relief="flat",
                padx=10,
                pady=4,
                cursor="hand2"
            )
            action.pack(anchor="e")
            return card

        _make_hub_card(
            0, 0,
            "🛍️", "Mod Store & Index",
            "Browse and 1-click install verified Geode mods (Globed, Megahack, CBF, Node IDs, BetterEdit).",
            "Open Store →",
            lambda: self.switch_main_tab("store"),
            UI["lime"]
        )

        _make_hub_card(
            0, 1,
            "🏆", "Pointercrate Demonlist",
            "Live Top 150 Extreme Demon rankings synced with pointercrate.com. Track records & creator stats.",
            "View Demonlist →",
            lambda: self.switch_main_tab("demonlist"),
            UI["lilac"]
        )

        _make_hub_card(
            1, 0,
            "🎵", "Practice Music & SFX",
            "Crash-proof StayInsideMe.mp3 replacer and custom death sound effects hub without DLL injection.",
            "Customize Audio →",
            lambda: self.switch_main_tab("jukebox"),
            "#66b3ff"
        )

        _make_hub_card(
            1, 1,
            "💾", "Save Hub & Multi-Slots",
            "Manage multi-account save slots, clean CCGameManager bloat, and export .geodesync portable archives.",
            "Open Save Hub →",
            lambda: self.switch_main_tab("saves"),
            UI["amber"]
        )

        # Quick tools bar on dashboard
        quick_bar = tk.Frame(self.tab_frames["dashboard"], bg=UI["background"])
        quick_bar.pack(fill="x", pady=(6, 0))
        tk.Label(quick_bar, text="QUICK TOOLS:", font=("Segoe UI", 7, "bold"), fg=UI["quiet"], bg=UI["background"]).pack(side="left", padx=(4, 6))

        def _add_quick_btn(label, cmd, fg_col):
            b = tk.Button(
                quick_bar,
                text=label,
                command=cmd,
                font=("Segoe UI", 8, "bold"),
                bg=UI["panel_alt"],
                fg=fg_col,
                activebackground=UI["border"],
                relief="flat",
                padx=8,
                pady=2,
                cursor="hand2"
            )
            b.pack(side="left", padx=(0, 4))
            return b

        _add_quick_btn("⚡ FPS Unlocker", self.open_fps_unlocker, UI["lime"])
        _add_quick_btn("🎨 Texture Packs", self.open_texture_pack_hub, UI["lilac"])
        _add_quick_btn("🩹 Crash Doctor", self.run_crash_doctor, UI["amber"])
        _add_quick_btn("💾 Backup Saves", self.backup_saves, UI["lime"])
        _add_quick_btn("🛠️ Full Toolbox →", lambda: self.switch_main_tab("toolbox"), UI["text"])

        # 2. TOOLKIT (Dedicated Toolbox Tab with all tools)
        tools_card = tk.Frame(self.tab_frames["toolbox"], bg=UI["panel"], padx=16, pady=10, highlightbackground=UI["border"], highlightthickness=1)
        tools_card.pack(fill="both", expand=True, pady=(0, 8))

        tools_head = tk.Frame(tools_card, bg=UI["panel"])
        tools_head.pack(fill="x", pady=(0, 8))
        tk.Label(tools_head, text="TOOLBOX", font=("Segoe UI", 11, "bold"), fg=UI["text"], bg=UI["panel"]).pack(side="left")
        tk.Label(tools_head, text="Choose what you want to do", font=("Segoe UI", 8), fg=UI["quiet"], bg=UI["panel"]).pack(side="left", padx=(10, 0))

        search_wrap = tk.Frame(tools_head, bg=UI["panel_alt"], padx=6, pady=2, highlightbackground=UI["border"], highlightthickness=1)
        search_wrap.pack(side="right")
        tk.Label(search_wrap, text="🔍", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel_alt"]).pack(side="left", padx=(0, 4))
        self.tool_search_var = tk.StringVar()
        self.tool_search_entry = tk.Entry(
            search_wrap, textvariable=self.tool_search_var,
            font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["text"],
            insertbackground=UI["lime"], relief="flat", width=22
        )
        self.tool_search_entry.pack(side="left")
        self.tool_buttons = []
        self.tool_search_var.trace_add("write", lambda *a: self._filter_tools())

        # Keep a single, flat grid: some Linux Tk 8.6 builds crash when these
        # controls are constructed inside nested section frames.
        tool_grid = tk.Frame(tools_card, bg=UI["panel"])
        tool_grid.pack(fill="both", expand=True)
        tool_grid.columnconfigure(0, weight=0, minsize=92)
        for col in range(1, 5):
            tool_grid.columnconfigure(col, weight=1)
        for row in range(7):
            tool_grid.rowconfigure(row, weight=1, uniform="tool-row")

        groups = (
            ("MODS", "#a7d957", "#252b20"),
            ("PLAY", "#c497e8", "#292333"),
            ("REPAIR", "#e4b968", "#30281e"),
            ("PREFERENCES", "#a99be7", "#282432"),
            ("APP", "#63d5ce", "#202b2b"),
            ("POWER", "#f39c12", "#2e2417"),
            ("EXTRAS", "#63d5ce", "#1e2b2a"),
        )
        for row, (name, accent, row_bg) in enumerate(groups):
            tk.Label(
                tool_grid, text=name, font=("Segoe UI", 8, "bold"),
                fg=accent, bg=UI["panel"], anchor="w", padx=5,
            ).grid(row=row, column=0, sticky="ew", padx=(2, 5), pady=4)

        def add_tool(label, command, *, color=UI["muted"], row, column, bold=False):
            row_bg = groups[row][2]
            button = tk.Button(
                tool_grid, text=label, command=command,
                font=("Segoe UI", 9, "bold" if bold else "normal"),
                bg=row_bg, fg=color, activebackground=UI["border"],
                activeforeground=UI["text"], relief="flat", padx=8, pady=8,
                cursor="hand2",
            )
            button.grid(row=row, column=column + 1, sticky="nsew", padx=3, pady=3)
            self.tool_buttons.append((button, label, color, row_bg))
            return button

        # Each row keeps related actions together: mods, play, repair, settings, system, power.
        add_tool("🧩 Mod Manager", self.open_mod_manager, color=UI["lime"], row=0, column=0, bold=True)
        add_tool("🔄 Update Mods", self.open_mod_updater_dialog, color=UI["lime"], row=0, column=1, bold=True)
        add_tool("📦 Essential Mods", self.install_essential_mods, color=UI["amber"], row=0, column=2, bold=True)
        add_tool("🎵 NONG Songs", self.open_nong_manager, color=UI["lime"], row=0, column=3)

        add_tool("📈 Demon Tracker", self.open_demon_tracker, color=UI["lilac"], row=1, column=0, bold=True)
        add_tool("⚡ FPS Unlocker", self.open_fps_unlocker, color=UI["lime"], row=1, column=1)
        add_tool("🎨 Texture Packs", self.open_texture_pack_hub, color=UI["lime"], row=1, column=2)
        add_tool("🎮 Game Profiles", self.open_game_profiles, color=UI["lilac"], row=1, column=3)

        add_tool("💾 Backup Saves", self.backup_saves, color=UI["lime"], row=2, column=0, bold=True)
        add_tool("🩺 Save Doctor", self.run_save_doctor, color=UI["lilac"], row=2, column=1)
        add_tool("🩹 Crash Doctor", self.run_crash_doctor, color=UI["lilac"], row=2, column=2)
        add_tool("🧹 Cache Cleaner", self.open_cache_cleaner, color=UI["muted"], row=2, column=3)

        self.auto_backup_btn = add_tool("Auto-Backup: ON", self.toggle_auto_backup, color=UI["lime"], row=3, column=0, bold=True)
        self.rpc_btn = add_tool("🎮 Discord RPC: ON", self.toggle_rpc, color=UI["lilac"], row=3, column=1)
        sounds_text = "🔊 GD Sounds: ON" if self.sounds_enabled else "🔇 GD Sounds: OFF"
        self.sounds_btn = add_tool(sounds_text, self.toggle_sounds, color=UI["lime"] if self.sounds_enabled else UI["muted"], row=3, column=2)
        self.bg_mode_btn = add_tool("🌙 Close to System Tray: ON", self.toggle_bg_mode, color=UI["lime"], row=3, column=3)

        add_tool("🔄 Check for Updates", self.manual_check_updates, color=UI["lime"], row=4, column=0, bold=True)
        add_tool("⌨️ Keybind Doctor", self.open_keybind_doctor, color=UI["amber"], row=4, column=1)
        add_tool("⚠️ Restore Steam GD", self.upgrade_clicked, color=UI["amber"], row=4, column=2)
        add_tool("📌 Desktop Shortcut", self.create_desktop_shortcut, color=UI["muted"], row=4, column=3)

        # v2.4.0 Power Tools
        add_tool("🛍️ Mod Store", self.open_mod_store_dialog, color=UI["lime"], row=5, column=0, bold=True)
        add_tool("🏆 Top Demonlist", self.open_demonlist_browser, color=UI["lilac"], row=5, column=1, bold=True)
        add_tool("🎵 Jukebox & Practice", self.open_jukebox_dialog, color=UI["lime"], row=5, column=2, bold=True)
        add_tool("☁️ Sync Archive", self.open_bundle_manager_dialog, color=UI["amber"], row=5, column=3, bold=True)

        # v2.4.0 Extras
        add_tool("💾 Save Slots", self.open_save_slots_dialog, color=UI["amber"], row=6, column=0, bold=True)
        add_tool("💥 Custom SFX", self.open_soundpack_hub, color=UI["lilac"], row=6, column=1, bold=True)
        add_tool("🗝️ Secret Vaults", self.open_vault_helper, color=UI["amber"], row=6, column=2, bold=True)
        add_tool("🛡️ Save Salvager", self.open_corrupt_save_resurrector, color=UI["lime"], row=6, column=3, bold=True)

        if not self.auto_backup_enabled:
            self.auto_backup_btn.config(text="Auto-Backup: OFF", fg=UI["muted"])
        if not self.discord_rpc_enabled:
            self.rpc_btn.config(text="🎮 Discord RPC: OFF", fg=UI["muted"])
        if not self.sounds_enabled:
            self.sounds_btn.config(text="🔇 GD Sounds: OFF", fg=UI["muted"])
        if not self.run_in_bg_enabled:
            self.bg_mode_btn.config(text="🌙 Close to System Tray: OFF", fg=UI["muted"])

        # Backward compatibility references
        self.player_card = self.guide_card
        self.launch_btn = self.primary_btn
        self.more_toggle_btn = None
        self.restore_gd_btn = None
        self.more_frame = None

        # Hidden text widget for logging compatibility
        self.log_text = tk.Text(self, bg=UI["inset"], fg=UI["text"], font=("Consolas", 8))

        # Build embedded views for modern tabs
        self._build_store_tab(self.tab_frames["store"])
        self._build_demonlist_tab(self.tab_frames["demonlist"])
        self._build_jukebox_tab(self.tab_frames["jukebox"])
        self._build_saves_tab(self.tab_frames["saves"])

        # 3. MODERN 1-LINE STATUS TICKER & FOOTER
        footer = tk.Frame(self, bg=UI["header"], padx=20, pady=7)
        footer.pack(fill="x", side="bottom")

        footer_actions = tk.Frame(footer, bg=UI["header"])
        footer_actions.pack(fill="x")

        self.status_ticker_lbl = tk.Label(
            footer_actions,
            text="● Ready to play Geometry Dash",
            font=("Segoe UI", 8),
            fg=UI["lime"],
            bg=UI["header"],
            wraplength=320,
            justify="left",
            anchor="w",
        )
        self.status_ticker_lbl.pack(side="left", fill="x", expand=True, padx=(0, 8))

        choose_path_btn = tk.Button(footer_actions, text="📁 Game Folder", command=self.browse_gd_path, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["muted"], relief="flat", padx=8, pady=3, cursor="hand2")
        choose_path_btn.pack(side="right", padx=(4, 0))

        choose_save_btn = tk.Button(footer_actions, text="💾 Save Folder", command=self.browse_save_path, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["muted"], relief="flat", padx=8, pady=3, cursor="hand2")
        choose_save_btn.pack(side="right", padx=(4, 0))

        view_log_btn = tk.Button(footer_actions, text="📋 Activity Log", command=self.open_log_viewer, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["muted"], relief="flat", padx=8, pady=3, cursor="hand2")
        view_log_btn.pack(side="right", padx=(4, 0))

        fix_problem_btn = tk.Button(footer_actions, text="🛠 Fix a problem", command=self.open_troubleshooter, font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=UI["amber"], relief="flat", padx=8, pady=3, cursor="hand2")
        fix_problem_btn.pack(side="right", padx=(4, 0))

        discord_link = tk.Label(footer_actions, text="Discord", font=("Segoe UI", 8, "underline"), fg=UI["lilac"], bg=UI["header"], cursor="hand2")
        discord_link.pack(side="right", padx=6)
        discord_link.bind("<Button-1>", lambda e: webbrowser.open("https://discord.gg/tyQG5xNGCx"))

        repo_link = tk.Label(footer_actions, text="GitHub", font=("Segoe UI", 8, "underline"), fg=UI["muted"], bg=UI["header"], cursor="hand2")
        repo_link.pack(side="right", padx=6)
        repo_link.bind("<Button-1>", lambda e: webbrowser.open(f"https://github.com/{GITHUB_REPO}"))

        self.path_lbl = tk.Label(
            footer,
            text=f"Game: {self.mgr.gd_path or 'Not found'}  •  Saves: {self.mgr.get_save_data_dir() or 'Not found'}",
            font=("Segoe UI", 7),
            fg=UI["quiet"],
            bg=UI["header"],
            wraplength=900,
            justify="left",
            anchor="w",
        )
        self.path_lbl.pack(fill="x", anchor="w", pady=(4, 0))

        def _fit_footer_status(event=None):
            available = event.width if event is not None else footer_actions.winfo_width()
            if available <= 1:
                return
            fixed_width = sum(
                child.winfo_reqwidth()
                for child in footer_actions.winfo_children()
                if child is not self.status_ticker_lbl
            )
            self.status_ticker_lbl.configure(wraplength=max(110, available - fixed_width - 40))
            self.path_lbl.configure(wraplength=max(240, footer.winfo_width() - 40))

        footer_actions.bind("<Configure>", _fit_footer_status)
        footer.bind("<Configure>", _fit_footer_status)

    def switch_main_tab(self, tab_id):
        self.active_main_tab = tab_id
        for tid, btn in getattr(self, "tab_buttons", {}).items():
            if tid == tab_id:
                btn.config(bg=UI["panel_alt"], fg=UI["lime"])
            else:
                btn.config(bg=UI["header"], fg=UI["muted"])
        for tid, frame in getattr(self, "tab_frames", {}).items():
            if tid == tab_id:
                frame.pack(fill="both", expand=True)
                if tid == "store":
                    self._load_embedded_store()
                elif tid == "demonlist":
                    self._load_embedded_demonlist()
                elif tid == "jukebox":
                    self._refresh_embedded_jukebox()
                elif tid == "saves":
                    self._refresh_embedded_saves()
            else:
                frame.pack_forget()

    def _build_store_tab(self, parent):
        head = tk.Frame(parent, bg=UI["header"], padx=16, pady=10)
        head.pack(fill="x", pady=(0, 8))
        tk.Label(head, text="🛍️  Geode Mod Store & Browser", font=("Segoe UI", 12, "bold"), fg=UI["lime"], bg=UI["header"]).pack(anchor="w")
        tk.Label(head, text="Discover and 1-click install official community mods directly from the Geode SDK Index.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", pady=(2, 6))

        bar = tk.Frame(head, bg=UI["header"])
        bar.pack(fill="x")
        self.store_search_var = tk.StringVar()
        tk.Label(bar, text="🔍", font=("Segoe UI", 9), fg=UI["muted"], bg=UI["header"]).pack(side="left", padx=(0, 6))
        s_ent = tk.Entry(bar, textvariable=self.store_search_var, font=("Segoe UI", 9), bg=UI["inset"], fg=UI["text"], insertbackground=UI["lime"], relief="flat", highlightbackground=UI["border"], highlightthickness=1)
        s_ent.pack(side="left", fill="x", expand=True, ipady=3)
        self.store_search_var.trace_add("write", lambda *a: self._filter_embedded_store())

        ref_btn = tk.Button(bar, text="🔄 Refresh Store", command=lambda: self._load_embedded_store(force=True), font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=UI["lime"], relief="flat", padx=10, pady=3, cursor="hand2")
        ref_btn.pack(side="right", padx=(8, 0))

        self.store_scroll = ScrollableFrame(parent)
        self.store_scroll.pack(fill="both", expand=True)
        self.store_cards_container = self.store_scroll.scrollable_content
        self._cached_store_mods = []

    def _load_embedded_store(self, force=False):
        if self._cached_store_mods and not force:
            return
        for child in self.store_cards_container.winfo_children():
            child.destroy()
        loading_lbl = tk.Label(self.store_cards_container, text="⏳ Fetching official mods from Geode Index API...", font=("Segoe UI", 10), fg=UI["lime"], bg=UI["background"], pady=20)
        loading_lbl.pack()

        def _fetch():
            try:
                mods = self.mgr.fetch_geode_store_mods()
                self._cached_store_mods = mods
                if hasattr(self, "tk") and self.tk:
                    self.after(0, self._render_store_cards)
            except Exception:
                pass

        threading.Thread(target=_fetch, daemon=True).start()

    def _render_store_cards(self):
        for child in self.store_cards_container.winfo_children():
            child.destroy()
        query = (self.store_search_var.get() or "").lower().strip()
        filtered = [
            m for m in self._cached_store_mods
            if not query or query in m.get("name", "").lower() or query in m.get("id", "").lower() or query in m.get("description", "").lower()
        ]
        if not filtered:
            tk.Label(self.store_cards_container, text="No mods found matching your search.", font=("Segoe UI", 10), fg=UI["muted"], bg=UI["background"], pady=20).pack()
            return

        installed_ids = {m.get("id", "").lower(): m for m in self.mgr.get_installed_mods()}

        for mod in filtered:
            m_id = mod.get("id", "")
            is_installed = m_id.lower() in installed_ids

            card = tk.Frame(self.store_cards_container, bg=UI["panel"], padx=14, pady=10, highlightbackground=UI["border"], highlightthickness=1)
            card.pack(fill="x", padx=4, pady=3)

            top = tk.Frame(card, bg=UI["panel"])
            top.pack(fill="x")

            name_lbl = tk.Label(top, text=mod.get("name", m_id), font=("Segoe UI", 10, "bold"), fg=UI["lime"], bg=UI["panel"])
            name_lbl.pack(side="left")

            ver_lbl = tk.Label(top, text=f"v{mod.get('version', '1.0.0')}", font=("Segoe UI", 8), fg=UI["lilac"], bg=UI["panel"])
            ver_lbl.pack(side="left", padx=(6, 0))

            dl_cnt = mod.get("download_count", 0)
            if dl_cnt:
                tk.Label(top, text=f"•  ⬇ {dl_cnt:,}", font=("Segoe UI", 8), fg=UI["amber"], bg=UI["panel"]).pack(side="left", padx=(6, 0))

            action_btn = tk.Button(
                top,
                text="✓ Installed" if is_installed else "Install Mod",
                command=lambda mid=m_id: self._install_embedded_mod_action(mid),
                font=("Segoe UI", 8, "bold"),
                bg=UI["panel_alt"] if is_installed else UI["lime"],
                fg=UI["lime"] if is_installed else UI["background"],
                activebackground=UI["lime_hover"],
                relief="flat",
                padx=10,
                pady=3,
                cursor="hand2"
            )
            action_btn.pack(side="right")

            desc = mod.get("description", "")
            if desc:
                tk.Label(card, text=desc, font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"], justify="left", wraplength=760).pack(anchor="w", pady=(2, 0))

    def _filter_embedded_store(self):
        if hasattr(self, "store_cards_container") and self._cached_store_mods:
            self._render_store_cards()

    def _install_embedded_mod_action(self, mod_id):
        self.log(f"Installing mod {mod_id} from Geode store...", "INFO")
        def _task():
            ok, msg = self.mgr.install_mod_from_store(mod_id)
            def _done():
                if ok:
                    self.log(f"Successfully installed mod {mod_id}", "INFO")
                    self._render_store_cards()
                    self.refresh_status()
                    messagebox.showinfo("Mod Installed", msg)
                else:
                    self.log(f"Failed to install mod {mod_id}: {msg}", "ERROR")
                    messagebox.showerror("Installation Failed", msg)
            self.after(0, _done)
        threading.Thread(target=_task, daemon=True).start()

    def _build_demonlist_tab(self, parent):
        head = tk.Frame(parent, bg=UI["header"], padx=16, pady=10)
        head.pack(fill="x", pady=(0, 8))
        tk.Label(head, text="🏆  Pointercrate Top 150 Demonlist", font=("Segoe UI", 12, "bold"), fg=UI["lilac"], bg=UI["header"]).pack(anchor="w")
        tk.Label(head, text="Live official rankings, creators, verifiers, requirements, and local save progress.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", pady=(2, 6))

        bar = tk.Frame(head, bg=UI["header"])
        bar.pack(fill="x")
        self.demon_search_var = tk.StringVar()
        tk.Label(bar, text="🔍", font=("Segoe UI", 9), fg=UI["muted"], bg=UI["header"]).pack(side="left", padx=(0, 6))
        d_ent = tk.Entry(bar, textvariable=self.demon_search_var, font=("Segoe UI", 9), bg=UI["inset"], fg=UI["text"], insertbackground=UI["lime"], relief="flat", highlightbackground=UI["border"], highlightthickness=1)
        d_ent.pack(side="left", fill="x", expand=True, ipady=3)
        self.demon_search_var.trace_add("write", lambda *a: self._filter_embedded_demonlist())

        ref_btn = tk.Button(bar, text="🔄 Refresh Rankings", command=lambda: self._load_embedded_demonlist(force=True), font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=UI["lilac"], relief="flat", padx=10, pady=3, cursor="hand2")
        ref_btn.pack(side="right", padx=(8, 0))

        self.demon_scroll = ScrollableFrame(parent)
        self.demon_scroll.pack(fill="both", expand=True)
        self.demon_cards_container = self.demon_scroll.scrollable_content
        self._cached_demons = []

    def _load_embedded_demonlist(self, force=False):
        if self._cached_demons and not force:
            return
        for child in self.demon_cards_container.winfo_children():
            child.destroy()
        loading_lbl = tk.Label(self.demon_cards_container, text="⏳ Querying Pointercrate Demonlist API...", font=("Segoe UI", 10), fg=UI["lilac"], bg=UI["background"], pady=20)
        loading_lbl.pack()

        def _fetch():
            try:
                demons = self.mgr.fetch_pointercrate_demons()
                self._cached_demons = demons
                if hasattr(self, "tk") and self.tk:
                    self.after(0, self._render_demonlist_cards)
            except Exception:
                pass

        threading.Thread(target=_fetch, daemon=True).start()

    def _render_demonlist_cards(self):
        for child in self.demon_cards_container.winfo_children():
            child.destroy()
        query = (self.demon_search_var.get() or "").lower().strip()
        filtered = [
            d for d in self._cached_demons
            if not query or query in d.get("name", "").lower() or query in d.get("creator", "").lower() or query in d.get("verifier", "").lower()
        ]
        if not filtered:
            tk.Label(self.demon_cards_container, text="No demons found matching your search.", font=("Segoe UI", 10), fg=UI["muted"], bg=UI["background"], pady=20).pack()
            return

        for demon in filtered:
            rank = demon.get("position", 1)
            rank_color = "#ffd700" if rank == 1 else "#e0e0e0" if rank == 2 else "#cd7f32" if rank == 3 else UI["lilac"]

            card = tk.Frame(self.demon_cards_container, bg=UI["panel"], padx=14, pady=9, highlightbackground=UI["border"], highlightthickness=1)
            card.pack(fill="x", padx=4, pady=3)

            top = tk.Frame(card, bg=UI["panel"])
            top.pack(fill="x")

            rank_badge = tk.Label(top, text=f"#{rank}", font=("Segoe UI", 10, "bold"), fg=rank_color, bg=UI["panel_alt"], padx=6, pady=2)
            rank_badge.pack(side="left", padx=(0, 8))

            name_lbl = tk.Label(top, text=demon.get("name", "Unknown Demon"), font=("Segoe UI", 10, "bold"), fg=UI["text"], bg=UI["panel"])
            name_lbl.pack(side="left")

            creator = demon.get("creator", "Unknown")
            verifier = demon.get("verifier", "Unknown")
            info_lbl = tk.Label(top, text=f"by {creator}  •  Verified by {verifier}", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"])
            info_lbl.pack(side="left", padx=(8, 0))

            pts = demon.get("points", 0.0)
            req = demon.get("requirement", 100)
            pts_lbl = tk.Label(top, text=f"{pts:.1f} pts ({req}%)", font=("Segoe UI", 8, "bold"), fg=UI["lilac"], bg=UI["panel"])
            pts_lbl.pack(side="right", padx=(8, 0))

            link_btn = tk.Button(
                top,
                text="🌐 Open",
                command=lambda pos=rank: webbrowser.open(f"https://pointercrate.com/demonlist/{pos}"),
                font=("Segoe UI", 8),
                bg=UI["panel_alt"],
                fg=UI["muted"],
                activebackground=UI["border"],
                relief="flat",
                padx=8,
                pady=2,
                cursor="hand2"
            )
            link_btn.pack(side="right")

    def _filter_embedded_demonlist(self):
        if hasattr(self, "demon_cards_container") and self._cached_demons:
            self._render_demonlist_cards()

    def _build_jukebox_tab(self, parent):
        scroll = ScrollableFrame(parent)
        scroll.pack(fill="both", expand=True)
        content = scroll.scrollable_content

        # Practice music card
        p_card = tk.Frame(content, bg=UI["panel"], padx=16, pady=14, highlightbackground=UI["border"], highlightthickness=1)
        p_card.pack(fill="x", padx=4, pady=(0, 10))
        tk.Label(p_card, text="🎵  CRASH-PROOF PRACTICE MUSIC HACK", font=("Segoe UI", 11, "bold"), fg=UI["lime"], bg=UI["panel"]).pack(anchor="w")
        tk.Label(p_card, text="Replaces Geometry Dash's StayInsideMe.mp3 with any song of your choice without DLL hooks or crashes.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(anchor="w", pady=(2, 8))

        self.jukebox_prac_status_lbl = tk.Label(p_card, text="Checking status...", font=("Segoe UI", 9, "bold"), fg=UI["quiet"], bg=UI["panel"])
        self.jukebox_prac_status_lbl.pack(anchor="w", pady=(0, 8))

        p_btns = tk.Frame(p_card, bg=UI["panel"])
        p_btns.pack(fill="x")
        tk.Button(p_btns, text="Choose Custom MP3 File...", command=self.choose_and_set_practice_music, font=("Segoe UI", 9, "bold"), bg=UI["lime"], fg=UI["background"], activebackground=UI["lime_hover"], relief="flat", padx=12, pady=6, cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(p_btns, text="↺ Restore Vanilla StayInsideMe.mp3", command=self.restore_vanilla_practice_music, font=("Segoe UI", 9), bg=UI["panel_alt"], fg=UI["text"], activebackground=UI["border"], relief="flat", padx=12, pady=6, cursor="hand2").pack(side="left")

        # Custom SFX card
        s_card = tk.Frame(content, bg=UI["panel"], padx=16, pady=14, highlightbackground=UI["border"], highlightthickness=1)
        s_card.pack(fill="x", padx=4, pady=(0, 10))
        tk.Label(s_card, text="💥  CUSTOM DEATH SOUND EFFECTS HUB", font=("Segoe UI", 11, "bold"), fg=UI["lilac"], bg=UI["panel"]).pack(anchor="w")
        tk.Label(s_card, text="Safely replaces explode_11.ogg with funny or competitive death sound effects (Vine Boom, Oof, Metal Pipe, etc.).", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(anchor="w", pady=(2, 8))

        self.jukebox_sfx_status_lbl = tk.Label(s_card, text="Checking status...", font=("Segoe UI", 9, "bold"), fg=UI["quiet"], bg=UI["panel"])
        self.jukebox_sfx_status_lbl.pack(anchor="w", pady=(0, 8))

        s_btns = tk.Frame(s_card, bg=UI["panel"])
        s_btns.pack(fill="x")
        tk.Button(s_btns, text="Choose Custom SFX (.ogg / .wav)...", command=self.choose_and_set_death_sfx, font=("Segoe UI", 9, "bold"), bg=UI["lilac"], fg=UI["background"], activebackground=UI["lilac_dark"], relief="flat", padx=12, pady=6, cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(s_btns, text="↺ Restore Vanilla Death SFX", command=self.restore_vanilla_death_sfx, font=("Segoe UI", 9), bg=UI["panel_alt"], fg=UI["text"], activebackground=UI["border"], relief="flat", padx=12, pady=6, cursor="hand2").pack(side="left")

        # Local audio library card
        t_card = tk.Frame(content, bg=UI["panel"], padx=16, pady=14, highlightbackground=UI["border"], highlightthickness=1)
        t_card.pack(fill="both", expand=True, padx=4)
        tk.Label(t_card, text="📁  DOWNLOADED SONGS IN GEOMETRY DASH", font=("Segoe UI", 11, "bold"), fg=UI["amber"], bg=UI["panel"]).pack(anchor="w")
        tk.Label(t_card, text="Instant 1-click apply: select any song you've downloaded inside Geometry Dash as your Practice Music.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(anchor="w", pady=(2, 8))

        self.jukebox_tracks_frame = tk.Frame(t_card, bg=UI["panel"])
        self.jukebox_tracks_frame.pack(fill="both", expand=True)

    def _refresh_embedded_jukebox(self):
        if hasattr(self, "jukebox_prac_status_lbl"):
            is_custom, desc = self.mgr.get_practice_music_status()
            self.jukebox_prac_status_lbl.config(
                text=f"Current Status: {desc}",
                fg=UI["lime"] if is_custom else UI["quiet"]
            )
        if hasattr(self, "jukebox_sfx_status_lbl"):
            is_custom_sfx, sfx_desc = self.mgr.get_custom_sfx_status()
            self.jukebox_sfx_status_lbl.config(
                text=f"Current Status: {sfx_desc}",
                fg=UI["lilac"] if is_custom_sfx else UI["quiet"]
            )
        if hasattr(self, "jukebox_tracks_frame"):
            for child in self.jukebox_tracks_frame.winfo_children():
                child.destroy()
            tracks = self.mgr.get_local_audio_tracks()
            if not tracks:
                tk.Label(self.jukebox_tracks_frame, text="No downloaded songs found in your Geometry Dash save folder.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(anchor="w", pady=4)
            else:
                for track in tracks[:8]:
                    row = tk.Frame(self.jukebox_tracks_frame, bg=UI["panel"])
                    row.pack(fill="x", pady=2)
                    tk.Label(row, text=f"🎵 Song ID: {track['song_id']}", font=("Segoe UI", 8, "bold"), fg=UI["text"], bg=UI["panel"]).pack(side="left")
                    tk.Label(row, text=f"({track['size_mb']} MB)", font=("Segoe UI", 8), fg=UI["quiet"], bg=UI["panel"]).pack(side="left", padx=(6, 0))
                    use_btn = tk.Button(
                        row,
                        text="Set as Practice Music",
                        command=lambda p=track["path"]: self._apply_practice_track(p),
                        font=("Segoe UI", 7, "bold"),
                        bg=UI["panel_alt"],
                        fg=UI["lime"],
                        relief="flat",
                        padx=6,
                        pady=1,
                        cursor="hand2"
                    )
                    use_btn.pack(side="right")

    def _apply_practice_track(self, path):
        ok, msg = self.mgr.set_custom_practice_music(path)
        if ok:
            messagebox.showinfo("Practice Music Set", msg)
            self._refresh_embedded_jukebox()
        else:
            messagebox.showerror("Error", msg)

    def _build_saves_tab(self, parent):
        scroll = ScrollableFrame(parent)
        scroll.pack(fill="both", expand=True)
        content = scroll.scrollable_content

        # Save Slots Profile Card
        slots_card = tk.Frame(content, bg=UI["panel"], padx=16, pady=14, highlightbackground=UI["border"], highlightthickness=1)
        slots_card.pack(fill="x", padx=4, pady=(0, 10))
        tk.Label(slots_card, text="💾  MULTI-SLOT SAVE PROFILES", font=("Segoe UI", 11, "bold"), fg=UI["amber"], bg=UI["panel"]).pack(anchor="w")
        tk.Label(slots_card, text="Maintain independent save states for Tournaments, Creator Mode, Practice, or alternative accounts.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(anchor="w", pady=(2, 8))

        self.saves_slots_status_lbl = tk.Label(slots_card, text="Loading slots...", font=("Segoe UI", 9, "bold"), fg=UI["lime"], bg=UI["panel"])
        self.saves_slots_status_lbl.pack(anchor="w", pady=(0, 8))

        slot_btns = tk.Frame(slots_card, bg=UI["panel"])
        slot_btns.pack(fill="x")
        tk.Button(slot_btns, text="+ Create New Save Slot", command=self.open_save_slots_dialog, font=("Segoe UI", 9, "bold"), bg=UI["amber"], fg=UI["background"], activebackground=UI["border"], relief="flat", padx=12, pady=6, cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(slot_btns, text="Manage & Switch Slots...", command=self.open_save_slots_dialog, font=("Segoe UI", 9), bg=UI["panel_alt"], fg=UI["text"], activebackground=UI["border"], relief="flat", padx=12, pady=6, cursor="hand2").pack(side="left")

        # Save Bloat Optimizer Card
        opt_card = tk.Frame(content, bg=UI["panel"], padx=16, pady=14, highlightbackground=UI["border"], highlightthickness=1)
        opt_card.pack(fill="x", padx=4, pady=(0, 10))
        tk.Label(opt_card, text="🧹  SAVE FILE BLOAT OPTIMIZER & COMPACTOR", font=("Segoe UI", 11, "bold"), fg=UI["lime"], bg=UI["panel"]).pack(anchor="w")
        tk.Label(opt_card, text="Strips unneeded cached online levels and orphaned song metadata, speeding up game launch and save times.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(anchor="w", pady=(2, 8))

        self.saves_opt_status_lbl = tk.Label(opt_card, text="Calculating save sizes...", font=("Segoe UI", 9), fg=UI["muted"], bg=UI["panel"])
        self.saves_opt_status_lbl.pack(anchor="w", pady=(0, 8))

        opt_btns = tk.Frame(opt_card, bg=UI["panel"])
        opt_btns.pack(fill="x")
        tk.Button(opt_btns, text="⚡ Clean Save Bloat & Compact", command=self.clean_save_bloat_action, font=("Segoe UI", 9, "bold"), bg=UI["lime"], fg=UI["background"], activebackground=UI["lime_hover"], relief="flat", padx=12, pady=6, cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(opt_btns, text="Detailed Bloat Analysis...", command=self.open_save_optimizer_dialog, font=("Segoe UI", 9), bg=UI["panel_alt"], fg=UI["text"], activebackground=UI["border"], relief="flat", padx=12, pady=6, cursor="hand2").pack(side="left")

        # Portable Bundles Card
        bun_card = tk.Frame(content, bg=UI["panel"], padx=16, pady=14, highlightbackground=UI["border"], highlightthickness=1)
        bun_card.pack(fill="x", padx=4, pady=(0, 10))
        tk.Label(bun_card, text="☁️  PORTABLE GAME ARCHIVES (.geodesync)", font=("Segoe UI", 11, "bold"), fg=UI["lilac"], bg=UI["panel"]).pack(anchor="w")
        tk.Label(bun_card, text="Bundle all your saves, Geode mods, and preferences into a single portable backup file to sync across PCs.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(anchor="w", pady=(2, 8))

        bun_btns = tk.Frame(bun_card, bg=UI["panel"])
        bun_btns.pack(fill="x")
        tk.Button(bun_btns, text="📦 Export Full Bundle (.geodesync)", command=self.open_bundle_manager_dialog, font=("Segoe UI", 9, "bold"), bg=UI["lilac"], fg=UI["background"], activebackground=UI["lilac_dark"], relief="flat", padx=12, pady=6, cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(bun_btns, text="📥 Import Bundle (.geodesync)", command=self.open_bundle_manager_dialog, font=("Segoe UI", 9), bg=UI["panel_alt"], fg=UI["text"], activebackground=UI["border"], relief="flat", padx=12, pady=6, cursor="hand2").pack(side="left")

        # Corrupt Save Salvager Card
        salv_card = tk.Frame(content, bg=UI["panel"], padx=16, pady=14, highlightbackground=UI["border"], highlightthickness=1)
        salv_card.pack(fill="x", padx=4)
        tk.Label(salv_card, text="🛡️  EMERGENCY SAVE RESURRECTOR & SALVAGER", font=("Segoe UI", 11, "bold"), fg=UI["lime"], bg=UI["panel"]).pack(anchor="w")
        tk.Label(salv_card, text="Recovers Geometry Dash save files after unexpected crashes, blue screens, or file corruption.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(anchor="w", pady=(2, 8))

        salv_btns = tk.Frame(salv_card, bg=UI["panel"])
        salv_btns.pack(fill="x")
        tk.Button(salv_btns, text="Scan & Resurrect Lost Saves...", command=self.open_corrupt_save_resurrector, font=("Segoe UI", 9, "bold"), bg=UI["panel_alt"], fg=UI["lime"], activebackground=UI["lime"], activeforeground=UI["background"], relief="flat", padx=12, pady=6, cursor="hand2").pack(side="left")

    def _refresh_embedded_saves(self):
        if hasattr(self, "saves_slots_status_lbl"):
            slots = self.mgr.get_save_slots()
            active_name = "Default Profile"
            for s in slots:
                if s.get("is_active"):
                    active_name = s.get("name", "Active Slot")
                    break
            self.saves_slots_status_lbl.config(
                text=f"Active Profile: {active_name}  •  Total Profiles: {len(slots)}",
                fg=UI["lime"]
            )
        if hasattr(self, "saves_opt_status_lbl"):
            ok, analysis = self.mgr.analyze_save_bloat()
            if ok and isinstance(analysis, dict):
                ll_sz = analysis.get("file_size_mb", 0.0)
                cached_lvl = analysis.get("online_cached", 0)
                total_lvl = analysis.get("total_levels", 0)
                self.saves_opt_status_lbl.config(
                    text=f"CCLocalLevels: {ll_sz} MB  •  Cached Online Levels: {cached_lvl} / {total_lvl} total",
                    fg=UI["text"]
                )
            else:
                self.saves_opt_status_lbl.config(
                    text=f"Save Status: {analysis}",
                    fg=UI["quiet"]
                )

    def choose_and_set_practice_music(self):
        f = filedialog.askopenfilename(title="Select Custom Practice Song", filetypes=[("Audio Files", "*.mp3 *.wav *.ogg"), ("All Files", "*.*")])
        if not f:
            return
        ok, msg = self.mgr.set_custom_practice_music(f)
        if ok:
            messagebox.showinfo("Practice Music Updated", msg)
            self._refresh_embedded_jukebox()
        else:
            messagebox.showerror("Error", msg)

    def restore_vanilla_practice_music(self):
        ok, msg = self.mgr.restore_vanilla_practice_music()
        if ok:
            messagebox.showinfo("Vanilla Restored", msg)
            self._refresh_embedded_jukebox()
        else:
            messagebox.showerror("Error", msg)

    def choose_and_set_death_sfx(self):
        f = filedialog.askopenfilename(title="Select Custom Death SFX", filetypes=[("Audio Files", "*.ogg *.wav *.mp3"), ("All Files", "*.*")])
        if not f:
            return
        ok, msg = self.mgr.set_custom_death_sfx(f)
        if ok:
            messagebox.showinfo("Death SFX Updated", msg)
            self._refresh_embedded_jukebox()
        else:
            messagebox.showerror("Error", msg)

    def restore_vanilla_death_sfx(self):
        ok, msg = self.mgr.restore_vanilla_death_sfx()
        if ok:
            messagebox.showinfo("Vanilla Restored", msg)
            self._refresh_embedded_jukebox()
        else:
            messagebox.showerror("Error", msg)

    def clean_save_bloat_action(self):
        ok, res = self.mgr.clean_save_bloat()
        if ok and isinstance(res, dict):
            old_mb = res.get("old_size_mb", 0.0)
            new_mb = res.get("new_size_mb", 0.0)
            levels = res.get("removed_levels", 0)
            saved_mb = res.get("saved_mb", 0.0)
            messagebox.showinfo("Saves Optimized!", f"Successfully removed {levels} cached online levels!\n\nSave size reduced from {old_mb} MB to {new_mb} MB ({saved_mb} MB saved).")
            self._refresh_embedded_saves()
            self.refresh_status()
        else:
            messagebox.showinfo("Save Status", str(res))

    def apply_and_notify_preset(self, preset_name):
        if preset_name == "boosted":
            self.launch_boosted_game()
            return
        ok, msg = self.mgr.apply_mod_preset(preset_name)
        if ok:
            self.log(f"Applied preset {preset_name}: {msg}", "INFO")
            if hasattr(self, "status_ticker_lbl"):
                self.status_ticker_lbl.config(text=f"● Applied preset: {preset_name.title()} mode")
            self.refresh_status()
            messagebox.showinfo(f"{preset_name.title()} Preset Applied", msg)
        else:
            messagebox.showerror("Preset Failed", msg)

    def _filter_tools(self):
        query = self.tool_search_var.get().strip().lower()
        for btn, label, orig_fg, row_bg in getattr(self, "tool_buttons", []):
            if not query or query in label.lower():
                btn.config(bg=UI["lime_dark"] if query else row_bg, fg=UI["lime"] if query else orig_fg)
            else:
                btn.config(bg=UI["panel"], fg=UI["quiet"])

    def open_log_viewer(self):
        dialog = tk.Toplevel(self)
        dialog.title("GeodeSync · Activity Log")
        dialog.geometry("640x480")
        dialog.minsize(520, 360)
        dialog.configure(bg=UI["header"])
        dialog.transient(self)

        top = tk.Frame(dialog, bg=UI["header"], padx=20, pady=12)
        top.pack(fill="x")
        tk.Label(top, text="📋 Activity Log", font=("Segoe UI", 12, "bold"), fg=UI["text"], bg=UI["header"]).pack(side="left")

        def _clear_and_refresh():
            self.clear_log()
            viewer_text.config(state="normal")
            viewer_text.delete("1.0", "end")
            viewer_text.config(state="disabled")

        tk.Button(top, text="Export Report", command=self.export_support_report, font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=UI["amber"], relief="flat", padx=10, pady=4, cursor="hand2").pack(side="right", padx=(6, 0))
        tk.Button(top, text="Clear Log", command=_clear_and_refresh, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["muted"], relief="flat", padx=10, pady=4, cursor="hand2").pack(side="right")

        content = tk.Frame(dialog, bg=UI["panel"], padx=14, pady=10)
        content.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        scroll = ttk.Scrollbar(content, orient="vertical")
        viewer_text = tk.Text(content, bg=UI["inset"], fg=UI["text"], font=("Consolas", 9), relief="flat", wrap="word", yscrollcommand=scroll.set, padx=8, pady=8)
        scroll.config(command=viewer_text.yview)
        scroll.pack(side="right", fill="y")
        viewer_text.pack(side="left", fill="both", expand=True)

        try:
            with open(self.activity_log_path, "r", encoding="utf-8", errors="replace") as stream:
                logs = stream.read()
            viewer_text.insert("end", logs)
            viewer_text.see("end")
        except Exception:
            pass
        viewer_text.config(state="disabled")

    def log(self, message: str, level: str = "INFO"):
        time_str = datetime.now().strftime("%H:%M:%S")
        color_prefix = {
            "INFO": "[INFO]",
            "SUCCESS": "[OK]",
            "WARN": "[WARN]",
            "ERROR": "[ERR]"
        }.get(level, "[INFO]")
        line = f"[{time_str}] {color_prefix} {message}"
        self._append_activity(line)
        if hasattr(self, "status_ticker_lbl"):
            ticker_color = UI["lime"] if level == "SUCCESS" else (UI["amber"] if level == "WARN" else (UI["red"] if level == "ERROR" else UI["text"]))
            self.status_ticker_lbl.config(text=f"● {message}", fg=ticker_color)
        if hasattr(self, "log_text"):
            try:
                self.log_text.config(state="normal")
                self.log_text.insert("end", line + "\n")
                self.log_text.see("end")
                self.log_text.config(state="disabled")
            except Exception:
                pass

    def clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")
        try:
            with self._log_lock:
                with open(self.activity_log_path, "w", encoding="utf-8"):
                    pass
        except OSError:
            pass

    def play_ding(self):
        if not getattr(self, "sounds_enabled", False):
            return
        if IS_WIN and winsound:
            def _play():
                try:
                    winsound.PlaySound("SystemNotification", winsound.SND_ALIAS | winsound.SND_ASYNC)
                except Exception:
                    try:
                        winsound.MessageBeep(winsound.MB_OK)
                    except Exception:
                        pass
            threading.Thread(target=_play, daemon=True).start()
        elif IS_MAC:
            try:
                subprocess.Popen(["afplay", "/System/Library/Sounds/Glass.aiff"])
            except Exception:
                pass

    def refresh_status(self):
        ver_text, ver_color = self.mgr.get_gd_version_info()
        self.ver_badge.config(text=ver_text, fg=ver_color)

        is_locked = self.mgr.is_manifest_locked()
        if is_locked:
            self.lock_badge.config(text="Locked (Protected)", fg=UI["lime"], bg=UI["lime_dark"])
        else:
            self.lock_badge.config(text="Unlocked (Normal)", fg=UI["amber"], bg=UI["panel_alt"])

        geode_ver = self.mgr.get_installed_geode_version()
        # A detected installation can lack a readable version log. Use the
        # existing filesystem detector as a fallback instead of calling a
        # nonexistent has_geode() method (which prevented the dashboard from
        # finishing its first refresh on every launch).
        has_geode = bool(geode_ver or self.mgr.is_geode_installed())
        stats = self.mgr.get_player_stats()
        player_tag = f"{stats['stars']} ⭐ · {stats['demons']} 👿" if stats else None
        if hasattr(self, "discord_rpc"):
            g_tag = geode_ver or "v5.x"
            if player_tag:
                status_desc = f"{player_tag} · Geode {g_tag} 🛡️" if is_locked else f"{player_tag} · Ready"
            else:
                status_desc = f"Geode {g_tag} · Mods Protected 🛡️" if is_locked else f"Geode {g_tag} · Ready"
            details = (
                DiscordRPC.PLAYING_DETAILS
                if self.mgr.is_gd_process_running()
                else DiscordRPC.COMPANION_DETAILS
            )
            self.discord_rpc.update_presence(details, status_desc, geode_ver=g_tag)

        if geode_ver:
            self.geode_badge.config(text=f"Geode {geode_ver}", fg=UI["lilac"], bg=UI["lilac_dark"])
        elif has_geode:
            self.geode_badge.config(text="Installed · version unknown", fg=UI["amber"], bg=UI["panel_alt"])
        else:
            self.geode_badge.config(text="Not installed", fg=UI["red"], bg=UI["red_dark"])

        save_p = self.mgr.get_save_data_dir()
        self.path_lbl.config(text=f"Game: {self.mgr.gd_path or 'Not found'}  •  Saves: {save_p or 'Not found'}")

        steam_found = bool(self.mgr.steam_path and os.path.isdir(self.mgr.steam_path))
        self.steam_badge.config(
            text="Found" if steam_found else "Not found",
            fg=UI["lime"] if steam_found else UI["red"],
            bg=UI["lime_dark"] if steam_found else UI["red_dark"],
        )
        save_dir = self.mgr.get_save_data_dir()
        try:
            save_files = [
                name for name in os.listdir(save_dir)
                if name.endswith((".dat", ".dat.bak"))
            ] if save_dir and os.path.isdir(save_dir) else []
        except OSError:
            save_files = []
        self.saves_badge.config(
            text=f"{len(save_files)} files" if save_files else "Not found yet",
            fg=UI["lime"] if save_files else UI["muted"],
            bg=UI["lime_dark"] if save_files else UI["panel_alt"],
        )

        self.update_player_stats_ui()
        if not self.is_downloading_depot:
            self.update_smart_guide(has_geode, is_locked)

    def update_smart_guide(self, has_geode: bool, is_locked: bool):
        is_22081 = self.mgr.is_current_gd_22081()

        if not has_geode:
            self.guide_card.config(highlightbackground=UI["red"])
            self.guide_badge.config(text="GEODE NOT FOUND", fg=UI["red"], bg=UI["red_dark"])
            self.guide_title.config(text="Install the Geode mod loader")
            self.guide_desc.config(
                text="GeodeSync found the game, but not Geode. Download the official installer to add the mod loader."
            )
            self.primary_btn.set_config(
                text="Download and install Geode",
                bg=UI["red"],
                hover_bg="#dc6972",
                fg=UI["background"],
                command=self.auto_install_geode
            )
            return

        if not is_22081:
            game_ver, _ = self.mgr.get_gd_version_info()
            if "2.207" in game_ver or "Outdated" in game_ver:
                self.guide_card.config(highlightbackground=UI["amber"])
                self.guide_badge.config(text="OUTDATED 2.2 DETECTED", fg=UI["amber"], bg=UI["amber_dark"])
                self.guide_title.config(text="Upgrade to 2.2081 for Full Geode Compatibility")
                self.guide_desc.config(
                    text="Your Geometry Dash is on an older 2.2 build, which causes crashes or missing mods. Click below to upgrade to 2.2081 cleanly."
                )
                self.primary_btn.set_config(
                    text="⚡ Upgrade to GD 2.2081 (Geode Compatible)",
                    bg=UI["lime"],
                    hover_bg=UI["lime_hover"],
                    fg=UI["background"],
                    command=self.start_automated_downgrade
                )
                return

            self.guide_card.config(highlightbackground=UI["lime"])
            self.guide_badge.config(text="1-CLICK FIX", fg=UI["lime"], bg=UI["lime_dark"])
            self.guide_title.config(text="Fix Geode Mods • Downgrade to 2.2081")
            self.guide_desc.config(
                text="Geometry Dash 2.209 broke your mods. Click below to install 2.2081 and lock Steam updates."
            )
            self.primary_btn.set_config(
                text=f"⚡ Fix Geode Mods (Install GD {self.mgr.target_gd_version})",
                bg=UI["lime"],
                hover_bg=UI["lime_hover"],
                fg=UI["background"],
                command=self.start_automated_downgrade
            )
            return

        self.guide_card.config(highlightbackground=UI["lime"])
        self.guide_badge.config(text="READY TO PLAY", fg=UI["lime"], bg=UI["lime_dark"])
        self.guide_title.config(text="✨ Geometry Dash 2.2081 is Active")
        self.guide_desc.config(
            text=f"Geode mods are fully compatible and Steam updates are safely locked. You're ready to play!"
        )
        self.primary_btn.set_config(
            text="▶️ Play Geometry Dash (Boosted)",
            bg=UI["lime"],
            hover_bg=UI["lime_hover"],
            fg=UI["background"],
            command=self.launch_gd
        )

    # ==========================================
    # v1.1.2 FEATURE: AUTO-INSTALL GEODE (1-CLICK)
    # ==========================================
    def auto_install_geode(self):
        threading.Thread(target=self._run_auto_geode_install, daemon=True).start()

    def _run_auto_geode_install(self):
        self.log("Fetching latest official Geode release from GitHub...", "INFO")
        self.progress_frame.pack(fill="x", pady=(0, 8), before=self.primary_btn)
        self.progress_bar["value"] = 15
        self.progress_lbl.config(text="Contacting GitHub for official Geode installer...")
        self.primary_btn.set_enabled(False)

        try:
            req = urllib.request.Request("https://api.github.com/repos/geode-sdk/geode/releases/latest", headers={"User-Agent": "GeodeSync-Client"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                download_url = None
                installer_name = "geode-installer.pkg" if IS_MAC else "geode-installer.exe"
                for asset in data.get("assets", []):
                    name = asset.get("name", "").lower()
                    if IS_MAC:
                        if name.endswith(".pkg") or name.endswith(".dmg") or ("mac" in name and name.endswith(".zip")):
                            download_url = asset.get("browser_download_url")
                            installer_name = asset.get("name")
                            break
                    else:
                        if name.endswith(".exe") and "win" in name:
                            download_url = asset.get("browser_download_url")
                            installer_name = asset.get("name")
                            break

            if not download_url:
                raise Exception("Could not locate installer asset for this operating system.")

            dest_dir = tempfile.gettempdir()
            dest_path = os.path.join(dest_dir, installer_name)
            self.log(f"Downloading {installer_name}...", "INFO")
            self.progress_lbl.config(text=f"Downloading {installer_name}...")
            self.progress_bar["value"] = 40

            urllib.request.urlretrieve(download_url, dest_path)
            self.progress_bar["value"] = 100
            self.log(f"Launching {installer_name}...", "SUCCESS")
            self.progress_frame.pack_forget()
            self.primary_btn.set_enabled(True)

            open_url_or_path(dest_path)
            messagebox.showinfo(
                "Geode Installer Launched",
                "The official Geode installer has started!\n\n"
                f"Check that it installs into the Steam Geometry Dash folder:\n{self.mgr.gd_path or 'Select the folder opened from Steam → Properties → Installed Files → Browse'}\n\n"
                "That folder should contain GeometryDash.exe. Do not place the installer inside it or copy Geode files by hand. When installation finishes, launch Geometry Dash from Steam once."
            )
            time.sleep(3)
            self.refresh_status()

        except Exception as e:
            self.log(f"Auto-install error: {e}. Opening geode-sdk.org instead...", "WARN")
            self.progress_frame.pack_forget()
            self.primary_btn.set_enabled(True)
            def open_geode():
                webbrowser.open("https://geode-sdk.org")
            self.after(0, lambda err=e: self.show_smart_error(
                "Geode Auto-Install Issue",
                f"Could not automatically download the official Geode installer:\n\n{err}\n\n"
                "Click 'Auto-Fix It For Me' below to open the official Geode SDK installer page directly.",
                auto_fix_func=open_geode
            ))
            self.refresh_status()

    # ==========================================
    # v1.1.2 FEATURE: REAL-TIME STEAM DOWNLOAD TRACKER
    # ==========================================
    def start_automated_downgrade(self, profile_mods=None):
        if self.is_downloading_depot:
            return False

        if not messagebox.askyesno(
            "Review game switch",
            f"GeodeSync will switch the Steam game files to Geometry Dash {self.mgr.target_gd_version}.\n\n"
            "It will back up detected saves, stage and check the downloaded files, and roll the game files back if installation fails. "
            "Steam auto-updates will be locked after a successful switch. Continue?",
        ):
            return False

        if self.mgr.is_gd_process_running():
            res = messagebox.askyesno(
                "Geometry Dash Running",
                "Geometry Dash is currently open. It must be closed before game files can be replaced.\n\n"
                "Would you like GeodeSync to close GD automatically now?"
            )
            if res:
                if not self.mgr.close_gd_process() or self.mgr.is_gd_process_running():
                    def kill_and_retry():
                        self.emergency_unstick()
                        self.start_automated_downgrade()
                    self.show_smart_error(
                        "Geometry Dash is still running",
                        "Geometry Dash is currently open in the background and locking files. Click 'Auto-Fix It For Me' to force-close GD and proceed with the switch.",
                        auto_fix_func=kill_and_retry
                    )
                    return False
            else:
                return False

        save_dir = self.mgr.get_save_data_dir()
        try:
            save_files = [
                name for name in os.listdir(save_dir)
                if name.endswith((".dat", ".dat.bak"))
            ] if save_dir and os.path.isdir(save_dir) else []
        except OSError:
            save_files = []
        if not save_files and not messagebox.askyesno(
            "No Save Backup Found",
            "GeodeSync could not find Geometry Dash save files (.dat) in standard or OneDrive locations.\n\n"
            "If your save files are stored in a custom folder, you can click 'No' and use '💾 Save Folder' in the bottom bar to link them before switching.\n\n"
            "Continue with the version switch anyway?",
        ):
            return False

        # Claim the operation synchronously before starting a worker. If the
        # depot is already cached, the worker can reach the file swap almost
        # immediately; setting this only after Steam starts downloading allowed
        # rapid clicks to launch two concurrent replacements of Geometry Dash.app.
        self.is_downloading_depot = True
        self.pending_profile_mods = list(profile_mods) if profile_mods is not None else None
        self.primary_btn.set_enabled(False)
        self.primary_btn.set_config(text="Preparing safe switch…", bg=UI["panel_alt"], hover_bg=UI["panel_alt"], fg=UI["text"])
        try:
            threading.Thread(target=self._run_auto_downgrade, daemon=True).start()
            return True
        except Exception:
            self.is_downloading_depot = False
            self.pending_profile_mods = None
            self.primary_btn.set_enabled(True)
            self.refresh_status()
            raise

    def _run_auto_downgrade(self):
        try:
            self._run_auto_downgrade_impl()
        except Exception as e:
            self.is_downloading_depot = False
            self.pending_profile_mods = None
            self.log(f"Downgrade stopped unexpectedly: {e}", "ERROR")
            try:
                self.primary_btn.set_enabled(True)
                self.refresh_status()
            except Exception:
                pass
            def retry_fix():
                self.emergency_unstick()
                self.start_automated_downgrade()
            self.after(0, lambda err=e: self.show_smart_error(
                "Downgrade Stopped",
                f"GeodeSync stopped the downgrade before reporting success:\n\n{err}\n\n"
                "Click 'Auto-Fix It For Me' below to terminate hung processes, reset caches, and retry automatically.",
                auto_fix_func=retry_fix
            ))

    def _run_auto_downgrade_impl(self):
        if not self.mgr.gd_path:
            self.is_downloading_depot = False
            self.pending_profile_mods = None
            self.primary_btn.set_enabled(True)
            self.log("Geometry Dash folder not detected.", "ERROR")
            messagebox.showerror("Error", "Geometry Dash installation directory not found.")
            return

        save_dir = self.mgr.get_save_data_dir()
        try:
            save_files = [
                name for name in os.listdir(save_dir)
                if name.endswith((".dat", ".dat.bak"))
            ] if save_dir and os.path.isdir(save_dir) else []
            if save_files:
                copied = self.mgr.perform_silent_backup(prefix="BeforeSwitch")
                if copied > 0:
                    self.log(f"Created a pre-switch save backup ({copied} files).", "SUCCESS")
                else:
                    self.log("Pre-switch save backup: 0 files copied (continuing with caution).", "WARN")
            else:
                self.log("No Geometry Dash save files were found; proceeding after user confirmation.", "WARN")
        except Exception as error:
            self.log(f"Pre-switch save backup note: {error}. Proceeding with downgrade.", "WARN")

        steam_exe = self.mgr.get_steam_exe()
        if not steam_exe and not IS_MAC:
            self.is_downloading_depot = False
            self.pending_profile_mods = None
            self.primary_btn.set_enabled(True)
            self.log("Steam executable not found.", "ERROR")
            messagebox.showerror("Error", "Steam installation not found.")
            return

        # Steam can log “Depot download complete” while leaving a truncated
        # Geometry Dash.app in its content cache. On the next attempt, recover
        # that exact cache before starting another Steam download; otherwise
        # Steam may keep reusing the malformed bundle indefinitely. Steam must
        # be fully closed before touching its cache.
        if IS_MAC:
            depot_path = self.mgr.get_depot_path()
            cached_app = find_macos_game_app(depot_path)
            if cached_app and validate_macos_game_app(cached_app):
                if self.mgr.is_steam_running():
                    self.is_downloading_depot = False
                    self.pending_profile_mods = None
                    self.primary_btn.set_enabled(True)
                    self.log("Invalid Geometry Dash depot cache found; Steam must be fully quit before it can be safely reset.", "WARN")
                    messagebox.showwarning(
                        "Quit Steam to repair the download",
                        "Steam left an incomplete Geometry Dash download in its cache. Quit Steam completely (Steam → Quit), then click 1-Click Fix again. GeodeSync will remove only that damaged downloaded cache and fetch it again. Your installed game and save files will not be touched.",
                    )
                    self.refresh_status()
                    return
                try:
                    if reset_invalid_macos_depot_cache(depot_path, self.mgr.gd_path):
                        self.log("Removed the malformed Geometry Dash Steam download cache; requesting a clean depot download.", "WARN")
                except (OSError, ValueError) as error:
                    self.is_downloading_depot = False
                    self.pending_profile_mods = None
                    self.primary_btn.set_enabled(True)
                    self.log(f"Could not safely reset the invalid Steam download cache: {error}", "ERROR")
                    messagebox.showerror(
                        "Steam cache could not be repaired",
                        "GeodeSync could not safely clear the damaged downloaded cache. The installed game was not changed. Quit Steam, then send support the full activity log so the exact cache path can be checked.",
                    )
                    self.refresh_status()
                    return

        if not self.mgr.is_steam_running():
            self.log("Steam is not currently running. Launching Steam...", "INFO")
            try:
                if IS_MAC:
                    subprocess.Popen(["open", "-a", "Steam"])
                elif IS_LINUX:
                    if steam_exe and steam_exe.startswith("flatpak:"):
                        subprocess.Popen(["flatpak", "run", "com.valvesoftware.Steam"])
                    else:
                        subprocess.Popen([steam_exe or "steam"])
                elif steam_exe:
                    subprocess.Popen([steam_exe])
                time.sleep(5)
            except Exception as e:
                self.log(f"Warning launching Steam: {e}", "WARN")

        if self.mgr.has_downloaded_depot() and not self.mgr.is_depot_locked():
            self.log(f"{self.mgr.target_gd_version} files already present on disk. Applying directly...", "INFO")
            self._apply_downgrade_files()
            return

        log_path = self.mgr.get_steam_console_log()
        initial_log_offset = 0
        if log_path and os.path.exists(log_path):
            try:
                initial_log_offset = os.path.getsize(log_path)
            except Exception:
                initial_log_offset = 0

        self.guide_title.config(text="⏳ Steam is downloading files in background...")
        self.guide_desc.config(text="Monitoring Steam depot progress in real time...")
        self.primary_btn.set_config(text="⏳ Downloading from Steam... (Please wait)", bg=UI["border"], hover_bg=UI["border"])
        self.primary_btn.set_enabled(False)

        # Show real-time progress bar
        self.progress_frame.pack(fill="x", pady=(0, 8), before=self.primary_btn)
        self.progress_bar["value"] = 5
        self.progress_lbl.config(text="Sending download command to Steam...")

        if IS_MAC:
            if steam_exe and steam_exe.endswith("steam_osx") and os.path.exists(steam_exe):
                args = [steam_exe, "-console", "+download_depot", APP_ID, DEPOT_ID, str(self.mgr.target_manifest)]
            else:
                args = ["open", "-a", "Steam", "--args", "-console", "+download_depot", APP_ID, DEPOT_ID, str(self.mgr.target_manifest)]
        elif IS_LINUX:
            if steam_exe and steam_exe.startswith("flatpak:"):
                args = ["flatpak", "run", "com.valvesoftware.Steam", "-console", "+download_depot", APP_ID, DEPOT_ID, str(self.mgr.target_manifest)]
            else:
                args = [steam_exe or "steam", "-console", "+download_depot", APP_ID, DEPOT_ID, str(self.mgr.target_manifest)]
        else:
            args = [steam_exe, "-console", "+download_depot", APP_ID, DEPOT_ID, str(self.mgr.target_manifest)]

        self.log("Sending automated download command to Steam...", "INFO")

        try:
            subprocess.Popen(args)
            self.log("Triggered Steam depot download! Monitoring live progress...", "SUCCESS")
        except Exception as e:
            self.log(f"Failed to execute Steam command: {e}", "ERROR")
            self.is_downloading_depot = False
            self.pending_profile_mods = None
            self.progress_frame.pack_forget()
            self.primary_btn.set_enabled(True)
            self.refresh_status()
            return

        start_time = time.time()
        steam_reported_complete = False

        while time.time() - start_time < 360:
            time.sleep(1.5)

            # Update live progress bar based on depot size
            cur_bytes = self.mgr.get_depot_current_size()
            cur_mb = round(cur_bytes / (1024 * 1024), 1)
            pct = min(96, int((cur_bytes / EXPECTED_DEPOT_BYTES) * 100))
            if pct > 5:
                self.progress_bar["value"] = pct
                total_mb = round(EXPECTED_DEPOT_BYTES / (1024 * 1024))
                self.progress_lbl.config(text=f"Downloading from Steam: {cur_mb} MB / ~{total_mb} MB ({pct}%)")

            # Check Steam console log for completion flag
            if log_path and os.path.exists(log_path):
                try:
                    current_size = os.path.getsize(log_path)
                    if current_size > initial_log_offset:
                        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                            f.seek(initial_log_offset)
                            new_content = f.read()
                            if "Depot download complete" in new_content and f"depot_{DEPOT_ID}" in new_content:
                                steam_reported_complete = True
                                break
                except Exception:
                    pass

            if self.mgr.has_downloaded_depot() and not self.mgr.is_depot_locked():
                time.sleep(1.0)
                if not self.mgr.is_depot_locked():
                    break

        self.progress_bar["value"] = 100
        self.progress_lbl.config(text="Download complete! Applying files...")
        time.sleep(0.5)
        self.progress_frame.pack_forget()
        self.primary_btn.set_enabled(True)

        # A Steam completion log line is only a download signal, not proof
        # that the cached app is valid. Never let it bypass bundle validation.
        depot_valid = self.mgr.has_downloaded_depot()
        if should_apply_downloaded_depot(steam_reported_complete, depot_valid):
            self.log("Steam depot download completed!", "SUCCESS")
            self._apply_downgrade_files()
        elif steam_reported_complete:
            self.is_downloading_depot = False
            self.pending_profile_mods = None
            self.log("Steam reported the depot complete, but its Geometry Dash.app failed validation; installed game files were left unchanged.", "ERROR")
            def purge_and_redownload():
                depot_path = self.mgr.get_depot_path()
                if depot_path and os.path.exists(depot_path):
                    shutil.rmtree(depot_path, ignore_errors=True)
                self.emergency_unstick()
                self.start_automated_downgrade()
            self.after(0, lambda: self.show_smart_error(
                "Steam Download Incomplete",
                "Steam reported the download as complete, but cached files are missing valid app metadata.\n\n"
                "Click 'Auto-Fix It For Me' to safely purge the damaged cache and restart a clean download automatically.",
                auto_fix_func=purge_and_redownload
            ))
            self.refresh_status()
        else:
            self.is_downloading_depot = False
            self.pending_profile_mods = None
            self.log("Steam download timed out or took longer than 6 mins.", "WARN")
            def wait_and_retry():
                self.start_automated_downgrade()
            self.after(0, lambda: self.show_smart_error(
                "Steam Download in Progress",
                "Steam is still downloading game files in the background or timed out.\n\n"
                "Click 'Auto-Fix It For Me' to check Steam and resume monitoring the download.",
                auto_fix_func=wait_and_retry,
                is_warning=True
            ))
            self.refresh_status()

    def _apply_downgrade_files(self):
        depot = self.mgr.get_depot_path()
        if not depot or not os.path.exists(depot):
            self.is_downloading_depot = False
            self.pending_profile_mods = None
            self.primary_btn.set_enabled(True)
            self.log("Depot path not found.", "ERROR")
            self.refresh_status()
            return

        self.log(f"Staging and checking Geometry Dash {self.mgr.target_gd_version}...", "INFO")
        try:
            target_meta = next(
                (meta for meta in KNOWN_VERSIONS.values()
                 if str(meta.get("manifest")) == str(self.mgr.target_manifest)),
                {},
            )
            expected_windows_exe_size = target_meta.get("sizes") or target_meta.get("size")
            if str(self.mgr.target_manifest) == "3816559102876907245":
                expected_windows_exe_size = SIZES_22081

            def validate_staged_depot(staged_root):
                if IS_MAC:
                    app_path = find_macos_game_app(staged_root)
                    if not app_path:
                        return "Geometry Dash.app is missing from the downloaded depot."
                    return validate_macos_game_app(app_path)
                executable = os.path.join(staged_root, "GeometryDash.exe")
                if not os.path.isfile(executable):
                    return "GeometryDash.exe is missing from the downloaded depot."
                return validate_windows_game_images(
                    staged_root, expected_exe_size=expected_windows_exe_size,
                )

            installed_validator = None
            if not IS_MAC:
                installed_validator = lambda installed_root: validate_windows_game_images(
                    installed_root, expected_exe_size=expected_windows_exe_size,
                )
            install_depot_transactionally(
                depot,
                self.mgr.gd_path,
                validator=validate_staged_depot,
                installed_validator=installed_validator,
            )
            self.log(f"Game files successfully replaced with {self.mgr.target_gd_version}!", "SUCCESS")
        except Exception as e:
            self.is_downloading_depot = False
            self.pending_profile_mods = None
            self.primary_btn.set_enabled(True)
            self.log(f"Safe game switch failed; rollback/recovery preserved the previous files: {e}", "ERROR")
            err_msg = str(e)
            if "WinError 32" in err_msg or "WinError 33" in err_msg or "being used by another process" in err_msg:
                user_msg = (
                    "Steam or Geometry Dash currently has the game files locked in use.\n\n"
                    "Click 'Auto-Fix It For Me' to terminate the background process, unlock the files, and resume the switch automatically."
                )
            else:
                user_msg = (
                    "GeodeSync could not finish installing the selected game version. "
                    f"It restored the previous files or kept recovery data for the next launch.\n\n{e}"
                )
            if any(marker in err_msg.lower() for marker in ("dll ", "pe header", "windows executable", "section data")):
                user_msg = (
                    "GeodeSync found a damaged or incompatible Windows game DLL and stopped the switch. "
                    "It restored any files changed during this attempt.\n\n"
                    f"Details: {e}"
                )
            def auto_fix_switch():
                self.emergency_unstick()
                self.start_automated_downgrade()
            self.after(0, lambda: self.show_smart_error(
                "Game Switch Interrupted",
                user_msg,
                auto_fix_func=auto_fix_switch
            ))
            self.refresh_status()
            return

        profile_mods = self.pending_profile_mods
        profile_applied = True
        self.pending_profile_mods = None
        if profile_mods is not None:
            profile_applied = self._apply_active_mods(profile_mods)

        try:
            self.mgr.set_manifest_locked(True)
            self.log("Locked Steam appmanifest_322170.acf to Read-Only.", "SUCCESS")
        except Exception as e:
            self.log(f"Warning locking manifest: {e}", "WARN")

        self.is_downloading_depot = False
        self.primary_btn.set_enabled(True)
        self.refresh_status()
        self.play_ding()
        locked = self.mgr.is_manifest_locked()
        if locked:
            self.log(f"Safe switch complete. Geometry Dash {self.mgr.target_gd_version} is installed and Steam updates are locked.", "SUCCESS")
            if profile_applied:
                messagebox.showinfo("Game switch complete", f"Geometry Dash {self.mgr.target_gd_version} is installed. Your saves were backed up before the switch, and Steam updates are locked.")
            else:
                messagebox.showwarning("Game switched; profile needs attention", f"Geometry Dash {self.mgr.target_gd_version} is installed and Steam updates are locked, but some profile mods could not be switched. Review the activity log.")
        else:
            self.log(f"Geometry Dash {self.mgr.target_gd_version} was installed, but Steam's update lock could not be verified.", "WARN")
            messagebox.showwarning("Game installed; update lock needs attention", "The game files were switched successfully, but GeodeSync could not verify Steam's update lock. Review the activity log before launching Steam.")

    # ==========================================
    # v1.1.2 FEATURE: 1-CLICK AUDIO & CLICK DELAY OPTIMIZER
    # ==========================================
    def fix_click_delay(self):
        applied = []
        save_dir = self.mgr.get_save_data_dir()
        if not save_dir:
            messagebox.showerror("Error", "Could not locate Geometry Dash save folder.")
            return

        # 1. FMOD low-latency configuration (~2.7ms)
        fmod_dir = os.path.join(save_dir, "geode", "mods", "square3ang.fmod-hacker")
        try:
            os.makedirs(fmod_dir, exist_ok=True)
            fmod_settings = {
                "sample-rate": "48000",
                "buffer-size": "128",
                "master-volume": 100,
                "output-device": -1
            }
            if IS_MAC:
                fmod_settings["output-type"] = "CoreAudio"
            elif IS_WIN:
                fmod_settings["output-type"] = "WASAPI"
            with open(os.path.join(fmod_dir, "settings.json"), "w", encoding="utf-8") as f:
                json.dump(fmod_settings, f, indent=2)
            backend = "CoreAudio" if IS_MAC else "WASAPI" if IS_WIN else "the system-selected Linux audio backend"
            applied.append(f"✓ FMOD Audio Buffer set to 128 samples / {backend}; your plugin may use its platform default")
        except Exception as e:
            self.log(f"FMOD optimizer note: {e}", "WARN")

        # 2. CBF Mouse Lag Fix
        cbf_dir = os.path.join(save_dir, "geode", "mods", "syzzi.click_between_frames")
        cbf_file = os.path.join(cbf_dir, "settings.json")
        try:
            if os.path.exists(cbf_file):
                with open(cbf_file, "r", encoding="utf-8") as f:
                    cbf_data = json.load(f)
                cbf_data["mouse-fix"] = True
                with open(cbf_file, "w", encoding="utf-8") as f:
                    json.dump(cbf_data, f, indent=2)
                applied.append("✓ Click Between Frames (CBF) 'mouse-fix' enabled for high polling rate mice")
        except Exception:
            pass

        # 3. Click Sounds Queue Optimization
        cs_dir = os.path.join(save_dir, "geode", "mods", "beat.click-sound")
        cs_file = os.path.join(cs_dir, "settings.json")
        try:
            if os.path.exists(cs_file):
                with open(cs_file, "r", encoding="utf-8") as f:
                    cs_data = json.load(f)
                cs_data["optimize-sounds"] = True
                with open(cs_file, "w", encoding="utf-8") as f:
                    json.dump(cs_data, f, indent=2)
                applied.append("✓ Click Sounds 'optimize-sounds' enabled to prevent audio queuing")
        except Exception:
            pass

        self.play_ding()
        self.log("Applied Low-Latency Audio & Click Optimizations!", "SUCCESS")
        summary_msg = "Successfully applied GD Audio & Input Optimizations:\n\n" + "\n".join(applied) + "\n\nRestart Geometry Dash to enjoy near-zero click delay!"
        messagebox.showinfo("⚡ Audio & Click Optimizer", summary_msg)

    # ==========================================
    # v1.1.2 FEATURE: CRASH DOCTOR (DIAGNOSE BROKEN MODS)
    # ==========================================
    def run_crash_doctor(self):
        # 1. Scan for Windows DLL Loader 'Entry Point Not Found' crashers (these crash before crash logs exist)
        incompat = self.mgr.check_incompatible_mods()
        if incompat:
            item = incompat[0]
            res = messagebox.askyesno(
                "🩺 Crash Doctor: Entry Point Crash Detected!",
                f"⚠️ Fatal Incompatible Mod Found:\n👉 {item['name']} ({item['id']} {item['version']})\n\n"
                f"Issue:\n{item['issue']}\n\n"
                f"Symptom:\nWindows pops up 'GeometryDash.exe - Entry Point Not Found' on launch.\n\n"
                f"Would you like Crash Doctor to automatically install the tested, compatible {item['recommended_version']} release now?"
            )
            if res:
                self.log(f"Repairing {item['name']}...", "INFO")
                ok, msg = self.mgr.fix_incompatible_mod(item)
                if ok:
                    self.log(msg, "SUCCESS")
                    messagebox.showinfo("🩺 Crash Doctor: Repaired!", f"🎉 {msg}\n\nGeometry Dash can now launch cleanly!")
                    return
                else:
                    self.log(f"Repair failed: {msg}", "ERROR")
                    def force_disable_mod():
                        try:
                            mods_dir = os.path.join(self.mgr.gd_path, "geode", "mods")
                            tgt = os.path.join(mods_dir, f"{item['id']}.geode")
                            if os.path.exists(tgt):
                                os.rename(tgt, tgt + ".disabled")
                            self.refresh_status()
                            messagebox.showinfo("Mod Disabled", f"Disabled {item['name']} safely so Geometry Dash can launch!")
                        except Exception as ex:
                            self.emergency_unstick()
                    self.show_smart_error(
                        "Mod Repair Issue",
                        f"Could not automatically download the update for {item['name']}:\n{msg}\n\nClick 'Auto-Fix It For Me' to safely disable this mod so Geometry Dash can launch cleanly.",
                        auto_fix_func=force_disable_mod
                    )
                    return

        crash_dir = self.mgr.get_crashlogs_dir()
        if not crash_dir or not os.path.exists(crash_dir):
            messagebox.showinfo(
                "🩺 Crash Doctor",
                "No Geode crash-report folder was found in the usual locations. That does not mean the game is crash-free.\n\n"
                "If Geode’s “Whoopsies!” window is open, copy its complete report and use Fix a problem → Explain Error, or export a support report and attach the crash report separately.",
            )
            return

        logs = [os.path.join(crash_dir, f) for f in os.listdir(crash_dir) if f.endswith(".log")]
        if not logs:
            messagebox.showinfo(
                "🩺 Crash Doctor",
                "No Geode crash report was found in the usual folder. This does not prove the install is clean.\n\n"
                "If the “Whoopsies!” window is open, copy the complete report and send it to support so the stack trace and mod list can be checked.",
            )
            return

        logs.sort(key=os.path.getmtime, reverse=True)
        latest_log = logs[0]

        culprit = None
        reported_component = ""
        details = []
        try:
            with open(latest_log, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            for line in content.splitlines():
                if "Faulty Mod:" in line:
                    reported_component = line.split("Faulty Mod:", 1)[1].strip()
                    mod_id = re.search(r"\(([A-Za-z0-9_-]+\.[A-Za-z0-9_.-]+)\)", reported_component)
                    if mod_id and mod_id.group(1).casefold() != "geode.loader":
                        culprit = mod_id.group(1)
                    break
                if "Failed to load:" in line:
                    details.append(line.strip())

        except Exception as e:
            self.log(f"Crash Doctor scan error: {e}", "WARN")

        time_str = datetime.fromtimestamp(os.path.getmtime(latest_log)).strftime("%Y-%m-%d %H:%M:%S")

        if culprit:
            res = messagebox.askyesno(
                "🩺 Crash Doctor: Broken Mod Detected!",
                f"Most Recent Crash: {time_str}\n\n"
                f"⚠️ Suspected Problematic Mod:\n👉 {culprit}\n\n"
                "Would you like Crash Doctor to temporarily disable this mod so GD can launch cleanly?"
            )
            if res and self.mgr.gd_path:
                mod_path = os.path.join(self.mgr.gd_path, "geode", "mods", f"{culprit}.geode")
                if os.path.exists(mod_path):
                    try:
                        os.rename(mod_path, mod_path + ".disabled")
                        self.log(f"Disabled broken mod: {culprit}", "SUCCESS")
                        messagebox.showinfo("Mod Disabled", f"Disabled {culprit}!\n\nTry launching Geometry Dash now.")
                    except Exception as err:
                        messagebox.showerror("Error", f"Could not rename mod file: {err}")
                else:
                    messagebox.showinfo("Info", f"Mod file {culprit}.geode not found in mods folder (already removed?).")
        else:
            msg = f"Latest Geode crash report: {os.path.basename(latest_log)} ({time_str})\n\n"
            if "geode.loader" in reported_component.casefold():
                msg += "The report points to the Geode loader, not a specific add-on mod. That alone does not prove the loader is the root cause.\n\n"
            else:
                msg += "The report did not identify one specific add-on mod. That is not enough evidence to blame a game-version mismatch or recommend a downgrade.\n\n"
            msg += "Use Fix a problem → Explain Error, paste the complete “Whoopsies!” report, then choose Export Report. Do not reset the game or remove mods until the report has been reviewed."
            messagebox.showinfo("🩺 Crash Doctor Report", msg)

    # ==========================================
    # v1.1.2 FEATURE: VERSION ARCHIVE SELECTOR
    # ==========================================
    def open_version_selector(self):
        dialog = tk.Toplevel(self)
        dialog.title("Select Target Geometry Dash Version")
        dialog.geometry("480x280")
        dialog.configure(bg=UI["header"])
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="⚙️ Choose Target Version", font=("Segoe UI", 12, "bold"), fg=UI["text"], bg=UI["header"]).pack(anchor="w", padx=20, pady=(16, 4))
        tk.Label(dialog, text="Select which official Steam depot version to downgrade/switch to:", font=("Segoe UI", 9), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", padx=20, pady=(0, 12))

        current_choice = next(
            (name for name, meta in KNOWN_VERSIONS.items()
             if str(meta["manifest"]) == str(self.mgr.target_manifest)),
            list(KNOWN_VERSIONS.keys())[0],
        )
        selected_ver = tk.StringVar(value=current_choice)

        for name, data in KNOWN_VERSIONS.items():
            rb = tk.Radiobutton(
                dialog,
                text=name,
                variable=selected_ver,
                value=name,
                font=("Segoe UI", 9),
                fg=UI["text"],
                bg=UI["header"],
                selectcolor=UI["inset"],
                activebackground=UI["header"],
                activeforeground=UI["lilac"]
            )
            rb.pack(anchor="w", padx=24, pady=4)

        def apply_ver():
            choice = selected_ver.get()
            meta = KNOWN_VERSIONS[choice]
            self.mgr.target_manifest = meta["manifest"]
            self.mgr.target_gd_version = meta["ver"]
            self.user_selected_target = True
            self._save_settings()
            self.log(f"Target GD version set to: {meta['ver']} (Manifest: {meta['manifest']})", "INFO")
            dialog.destroy()
            self.refresh_status()

        btn_box = tk.Frame(dialog, bg=UI["header"])
        btn_box.pack(fill="x", side="bottom", padx=20, pady=16)

        cancel_btn = tk.Button(btn_box, text="Cancel", command=dialog.destroy, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["muted"], relief="flat", padx=10, pady=4, cursor="hand2")
        cancel_btn.pack(side="left")

        apply_btn = tk.Button(btn_box, text="Set as Target Version", command=apply_ver, font=("Segoe UI", 8, "bold"), bg=UI["lilac"], fg=UI["text"], activebackground=UI["lilac_dark"], activeforeground=UI["text"], relief="flat", padx=14, pady=4, cursor="hand2")
        apply_btn.pack(side="right")

    def _load_game_profiles(self):
        os.makedirs(self.profiles_dir, exist_ok=True)
        known_manifests = {str(meta["manifest"]) for meta in KNOWN_VERSIONS.values()}
        profiles = []
        for filename in sorted(os.listdir(self.profiles_dir)):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(self.profiles_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as stream:
                    profile = json.load(stream)
                if not isinstance(profile, dict) or str(profile.get("manifest")) not in known_manifests:
                    raise ValueError("Unknown game version profile")
                mods = profile.get("active_mods", [])
                if not isinstance(mods, list) or any(
                    not isinstance(mod, str) or not re.fullmatch(r"[^/\\]+\.geode", mod)
                    for mod in mods
                ):
                    raise ValueError("Invalid mod list in profile")
                profiles.append((filename, profile))
            except (OSError, ValueError, json.JSONDecodeError) as error:
                self.log(f"Skipped unreadable game profile {filename}: {error}", "WARN")
        return profiles

    def _apply_active_mods(self, desired_mods):
        mods_dir = self.get_mods_dir()
        if not mods_dir:
            self.log("Could not find the Geode mods folder for this profile.", "ERROR")
            return False
        if not isinstance(desired_mods, (list, tuple, set)) or any(
            not isinstance(name, str) or not re.fullmatch(r"[^/\\]+\.geode", name)
            for name in desired_mods
        ):
            self.log("The selected profile contains an invalid mod filename; no mods were changed.", "ERROR")
            return False
        wanted = set(desired_mods)
        try:
            filenames = os.listdir(mods_dir)
        except OSError as error:
            self.log(f"Could not read the Geode mods folder: {error}", "ERROR")
            return False
        present = {
            filename[:-9] if filename.endswith(".geode.disabled") else filename
            for filename in filenames
            if filename.endswith(".geode") or filename.endswith(".geode.disabled")
        }
        # Validate the complete plan before touching any files. Missing files or
        # conflicting active/disabled copies must not leave a half-applied set.
        errors = [f"Profile mod {missing} is not installed" for missing in sorted(wanted - present)]
        operations = []
        for filename in filenames:
            source = os.path.join(mods_dir, filename)
            if filename.endswith(".geode") and filename not in wanted:
                target = source + ".disabled"
                if os.path.lexists(target):
                    errors.append(f"Cannot disable {filename}: disabled copy already exists")
                else:
                    operations.append((source, target))
            elif filename.endswith(".geode.disabled") and filename[:-9] in wanted:
                target = os.path.join(mods_dir, filename[:-9])
                if os.path.lexists(target):
                    errors.append(f"Cannot enable {filename[:-9]}: active copy already exists")
                else:
                    operations.append((source, target))
        if errors:
            for error in errors:
                self.log(error, "WARN")
            return False

        changed = []
        try:
            for source, target in operations:
                os.replace(source, target)
                changed.append((source, target))
        except OSError as error:
            rollback_errors = []
            for source, target in reversed(changed):
                try:
                    os.replace(target, source)
                except OSError as rollback_error:
                    rollback_errors.append(str(rollback_error))
            self.log(f"Could not apply the complete profile mod set: {error}", "ERROR")
            if rollback_errors:
                self.log("Mod-profile rollback needs attention: " + "; ".join(rollback_errors), "ERROR")
            return False
        self.log(f"Applied profile mod selection ({len(wanted)} enabled).", "SUCCESS")
        return True

    def open_game_profiles(self):
        dialog = tk.Toplevel(self)
        dialog.title("Game profiles")
        dialog.geometry("560x430")
        dialog.configure(bg=UI["background"])
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="Game profiles", font=("Segoe UI", 16, "bold"), fg=UI["text"], bg=UI["background"]).pack(anchor="w", padx=20, pady=(18, 4))
        tk.Label(dialog, text="Save a game version and active mod set together. Applying a different version starts the safe switch.", font=("Segoe UI", 9), fg=UI["muted"], bg=UI["background"], wraplength=510, justify="left").pack(anchor="w", padx=20, pady=(0, 12))

        list_frame = tk.Frame(dialog, bg=UI["panel"], padx=8, pady=8)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        profile_list = tk.Listbox(list_frame, bg=UI["inset"], fg=UI["text"], selectbackground=UI["lilac_dark"], font=("Segoe UI", 10), relief="flat", activestyle="none")
        profile_list.pack(fill="both", expand=True)
        profiles = []

        def populate():
            nonlocal profiles
            profiles = self._load_game_profiles()
            profile_list.delete(0, "end")
            for _filename, profile in profiles:
                profile_list.insert("end", f"{profile.get('name', 'Unnamed')}   ·   GD {profile.get('game_version', '?')}   ·   {len(profile.get('active_mods', []))} mods")

        def save_current():
            name = simpledialog.askstring("Save game profile", "Name this setup (for example: Vanilla or Recording):", parent=dialog)
            if not name:
                return
            safe_name = re.sub(r"[^A-Za-z0-9 _-]", "", name).strip().strip(".-_")
            if not safe_name:
                messagebox.showerror("Invalid name", "Use letters, numbers, spaces, dashes, or underscores.", parent=dialog)
                return
            if not self.mgr.gd_path:
                messagebox.showerror("Game not found", "Choose your Geometry Dash game folder before saving a game profile.", parent=dialog)
                return
            mods_dir = self.get_mods_dir()
            active_mods = sorted(
                filename for filename in os.listdir(mods_dir)
                if filename.endswith(".geode")
            ) if mods_dir else []
            record = {
                "schema_version": 1,
                "name": safe_name,
                "game_version": self.mgr.target_gd_version,
                "manifest": str(self.mgr.target_manifest),
                "active_mods": active_mods,
                "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
            filename = re.sub(r"[^A-Za-z0-9_-]+", "_", safe_name).strip("_") + ".json"
            atomic_write_json(os.path.join(self.profiles_dir, filename), record)
            self.log(f"Saved game profile '{safe_name}' ({len(active_mods)} active mods).", "SUCCESS")
            populate()

        def apply_selected():
            selection = profile_list.curselection()
            if not selection:
                messagebox.showinfo("Select a profile", "Choose a game profile first.", parent=dialog)
                return
            _filename, profile = profiles[selection[0]]
            meta = next((item for item in KNOWN_VERSIONS.values() if str(item["manifest"]) == str(profile["manifest"])), None)
            if not meta:
                messagebox.showerror("Unsupported profile", "This profile refers to a game version that is not available in this build.", parent=dialog)
                return
            old_manifest, old_version = self.mgr.target_manifest, self.mgr.target_gd_version
            self.mgr.target_manifest = meta["manifest"]
            self.mgr.target_gd_version = meta["ver"]
            self.user_selected_target = True
            mods = profile.get("active_mods", [])
            if self.mgr.is_current_gd_22081():
                success = self._apply_active_mods(mods)
                self._save_settings()
                dialog.destroy()
                self.refresh_status()
                if success:
                    messagebox.showinfo("Profile applied", f"'{profile.get('name', 'Profile')}' is active.")
                else:
                    messagebox.showwarning("Profile partly applied", "The game version matches, but some mods could not be switched. Review the activity log.")
                return
            if not self.start_automated_downgrade(profile_mods=mods):
                self.mgr.target_manifest, self.mgr.target_gd_version = old_manifest, old_version
                dialog.destroy()
                self.refresh_status()
                return
            self._save_settings()
            self.log(f"Selected game profile '{profile.get('name', 'Profile')}'; switching to GD {meta['ver']}.", "INFO")
            dialog.destroy()

        def delete_selected():
            selection = profile_list.curselection()
            if not selection:
                return
            filename, profile = profiles[selection[0]]
            if not messagebox.askyesno("Delete game profile", f"Delete '{profile.get('name', 'Profile')}'?", parent=dialog):
                return
            os.unlink(os.path.join(self.profiles_dir, filename))
            self.log(f"Deleted game profile '{profile.get('name', 'Profile')}'.", "INFO")
            populate()

        actions = tk.Frame(dialog, bg=UI["background"])
        actions.pack(fill="x", padx=20, pady=(0, 16))
        tk.Button(actions, text="Save current", command=save_current, font=("Segoe UI", 9, "bold"), bg=UI["panel_alt"], fg=UI["lime"], relief="flat", padx=12, pady=7).pack(side="left")
        tk.Button(actions, text="Delete", command=delete_selected, font=("Segoe UI", 9), bg=UI["panel_alt"], fg=UI["red"], relief="flat", padx=12, pady=7).pack(side="left", padx=8)
        tk.Button(actions, text="Apply profile", command=apply_selected, font=("Segoe UI", 9, "bold"), bg=UI["lilac"], fg=UI["background"], relief="flat", padx=12, pady=7).pack(side="right")
        populate()

    def upgrade_clicked(self):
        res = messagebox.askyesno(
            "Restore to Latest GD",
            "This will unlock the Steam manifest and trigger Steam file verification to re-download the latest official version of Geometry Dash.\n\n"
            "Use this when Geode has officially updated to support the new version.\n\n"
            "Proceed?"
        )
        if not res:
            return

        threading.Thread(target=self._run_upgrade, daemon=True).start()

    def _run_upgrade(self):
        self.log("Unlocking Steam manifest...", "INFO")
        try:
            self.mgr.set_manifest_locked(False)
            self.log("Unlocked appmanifest_322170.acf.", "SUCCESS")
        except Exception as e:
            self.log(f"Could not unlock Steam's appmanifest; stopping restore: {e}", "ERROR")
            messagebox.showerror(
                "Could not unlock Steam updates",
                "GeodeSync could not safely unlock Steam's Geometry Dash manifest, so it did not start file verification.\n\n"
                "Quit Steam, reopen GeodeSync, and try Restore to Latest GD again. If it still fails, send the GeodeSync log; "
                "do not delete or edit Steam files manually.",
            )
            return

        self.log("Triggering Steam file verification...", "INFO")
        try:
            open_url_or_path(f"steam://validate/{APP_ID}")
            self.log("Triggered steam://validate/322170. Steam is now updating GD.", "SUCCESS")
            self.play_ding()
            messagebox.showinfo(
                "Restoring Latest Version",
                "Steam is now verifying and updating your Geometry Dash files to the latest version!\n\n"
                "Watch your Steam Downloads tab for progress."
            )
        except Exception as e:
            self.log(f"Failed to trigger Steam validate: {e}", "ERROR")
            messagebox.showerror("Error", f"Failed to trigger Steam verification:\n{e}")

        self.refresh_status()

    def backup_saves(self):
        save_dir = self.mgr.get_save_data_dir()
        if not save_dir:
            messagebox.showerror("Error", "Could not locate Geometry Dash save folder.")
            return

        backup_root = os.path.join(save_dir, "GeodeSync_Save_Backups")
        os.makedirs(backup_root, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        target_folder = os.path.join(backup_root, f"Backup_{timestamp}")
        os.makedirs(target_folder, exist_ok=True)

        copied = 0
        for f in os.listdir(save_dir):
            if f.endswith(".dat") or f.endswith(".dat.bak"):
                safe_copy_item(os.path.join(save_dir, f), os.path.join(target_folder, f))
                copied += 1

        self.play_ding()
        self.log(f"Backed up {copied} save files to: {target_folder}", "SUCCESS")
        messagebox.showinfo("Save Backup Complete", f"Successfully backed up {copied} save files!\n\nLocation: {target_folder}")

    def restore_saves(self):
        save_dir = self.mgr.get_save_data_dir()
        if not save_dir:
            messagebox.showerror("Error", "Could not locate Geometry Dash save folder.")
            return

        backup_root = os.path.join(save_dir, "GeodeSync_Save_Backups")
        os.makedirs(backup_root, exist_ok=True)

        dialog = tk.Toplevel(self)
        dialog.title("Save Backup Manager")
        dialog.geometry("640x460")
        dialog.configure(bg=UI["header"])
        dialog.transient(self)
        dialog.grab_set()

        head = tk.Frame(dialog, bg=UI["header"], padx=20, pady=16)
        head.pack(fill="x")
        tk.Label(head, text="♻️ Save Backup Manager", font=("Segoe UI", 12, "bold"), fg=UI["text"], bg=UI["header"]).pack(anchor="w")
        tk.Label(head, text="Choose a snapshot to restore, or manage your saved checkpoints:", font=("Segoe UI", 9), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", pady=(2, 0))

        content_frame = tk.Frame(dialog, bg=UI["header"], padx=20)
        content_frame.pack(fill="both", expand=True)

        list_card = tk.Frame(content_frame, bg=UI["panel"], highlightbackground=UI["border"], highlightthickness=1)
        list_card.pack(fill="both", expand=True)

        scroll = tk.Scrollbar(list_card, orient="vertical")
        listbox = tk.Listbox(
            list_card,
            bg=UI["inset"],
            fg=UI["text"],
            selectbackground=UI["lime_dark"],
            selectforeground=UI["lime"],
            font=("Consolas", 10),
            relief="flat",
            yscrollcommand=scroll.set,
            highlightthickness=0,
            activestyle="none"
        )
        scroll.config(command=listbox.yview)
        scroll.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True, padx=4, pady=4)

        folders_map = []

        def refresh_list():
            listbox.delete(0, tk.END)
            folders_map.clear()
            if not os.path.exists(backup_root):
                return
            dirs = [os.path.join(backup_root, d) for d in os.listdir(backup_root) if os.path.isdir(os.path.join(backup_root, d))]
            dirs.sort(key=os.path.getmtime, reverse=True)
            for d in dirs:
                name = os.path.basename(d)
                mtime = os.path.getmtime(d)
                date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                files = [f for f in os.listdir(d) if f.endswith((".dat", ".dat.bak"))]
                total_kb = round(sum(os.path.getsize(os.path.join(d, f)) for f in files) / 1024, 1)
                tag = "PRE-SWITCH" if name.startswith("BeforeSwitch") else ("AUTO" if name.startswith("Auto") else "MANUAL")
                display = f"[{tag:^10}]  {date_str}   •   {len(files)} files ({total_kb} KB)"
                listbox.insert(tk.END, display)
                folders_map.append(d)
            if folders_map:
                listbox.selection_set(0)

        refresh_list()

        def do_restore():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Select Backup", "Please select a backup snapshot from the list first.")
                return
            chosen = folders_map[sel[0]]
            name = os.path.basename(chosen)
            if not messagebox.askyesno(
                "Restore Save Files",
                f"Restore save files from:\n\n{name}\n\nGeodeSync will create a safety snapshot of your current files first.",
            ):
                return
            self.mgr.perform_silent_backup(prefix="SafetyBeforeRestore")
            restored = 0
            for f in os.listdir(chosen):
                if f.endswith((".dat", ".dat.bak")):
                    safe_copy_item(os.path.join(chosen, f), os.path.join(save_dir, f))
                    restored += 1
            self.play_ding()
            self.log(f"Restored {restored} save files from {name}", "SUCCESS")
            self.refresh_status()
            messagebox.showinfo("Saves Restored", f"Successfully restored {restored} save files from:\n{name}")
            dialog.destroy()

        def do_delete():
            sel = listbox.curselection()
            if not sel:
                return
            chosen = folders_map[sel[0]]
            if messagebox.askyesno("Delete Backup", f"Are you sure you want to delete this backup snapshot?\n\n{os.path.basename(chosen)}"):
                shutil.rmtree(chosen, ignore_errors=True)
                refresh_list()

        btn_box = tk.Frame(dialog, bg=UI["header"], padx=20, pady=16)
        btn_box.pack(fill="x", side="bottom")

        tk.Button(btn_box, text="Close", command=dialog.destroy, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["muted"], relief="flat", padx=10, pady=5, cursor="hand2").pack(side="left")
        tk.Button(btn_box, text="📂 Open Folder", command=lambda: open_url_or_path(backup_root), font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["muted"], relief="flat", padx=10, pady=5, cursor="hand2").pack(side="left", padx=(8, 0))
        tk.Button(btn_box, text="🗑️ Delete", command=do_delete, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["red"], relief="flat", padx=10, pady=5, cursor="hand2").pack(side="left", padx=(8, 0))

        tk.Button(btn_box, text="♻️ Restore Selected Backup", command=do_restore, font=("Segoe UI", 9, "bold"), bg=UI["lime"], fg=UI["background"], activebackground=UI["lime_hover"], activeforeground=UI["background"], relief="flat", padx=14, pady=5, cursor="hand2").pack(side="right")
        tk.Button(btn_box, text="➕ Backup Now", command=lambda: (self.backup_saves(), refresh_list()), font=("Segoe UI", 9, "bold"), bg=UI["lilac"], fg=UI["background"], activebackground=UI["lilac_hover"], activeforeground=UI["background"], relief="flat", padx=12, pady=5, cursor="hand2").pack(side="right", padx=(0, 8))

    def get_mods_dir(self):
        if IS_MAC:
            mac_mods = os.path.expanduser("~/Library/Application Support/GeometryDash/geode/mods")
            os.makedirs(mac_mods, exist_ok=True)
            return mac_mods
        if self.mgr.gd_path:
            mods_p = os.path.join(self.mgr.gd_path, "geode", "mods")
            os.makedirs(mods_p, exist_ok=True)
            return mods_p
        return None

    def open_mods_folder(self):
        mods_dir = self.get_mods_dir()
        if mods_dir:
            os.makedirs(mods_dir, exist_ok=True)
            open_url_or_path(mods_dir)
        else:
            messagebox.showerror("Error", "Geometry Dash mods folder not found.")

    def update_player_stats_ui(self):
        try:
            stats = self.mgr.get_player_stats()
            if not stats:
                if hasattr(self, "player_name_lbl"):
                    self.player_name_lbl.config(text="No save data found yet", fg=UI["muted"])
                return
            if hasattr(self, "player_name_lbl"):
                att_str = f"({stats.get('attempts', 0):,} att)" if stats.get('attempts') else ""
                self.player_name_lbl.config(text=f"{stats.get('name', 'Player')}  {att_str}".strip(), fg=UI["lime"])
            if hasattr(self, "stat_stars_lbl"):
                self.stat_stars_lbl.config(text=f"{stats.get('stars', 0):,} Stars")
            if hasattr(self, "stat_demons_lbl"):
                self.stat_demons_lbl.config(text=f"{stats.get('demons', 0):,} Demons")
            if hasattr(self, "stat_moons_lbl"):
                self.stat_moons_lbl.config(text=f"{stats.get('moons', 0):,} Moons")
            if hasattr(self, "stat_diamonds_lbl"):
                self.stat_diamonds_lbl.config(text=f"{stats.get('diamonds', 0):,} Diamonds")
            coins_total = stats.get('coins', 0) + stats.get('user_coins', 0)
            if hasattr(self, "stat_coins_lbl"):
                self.stat_coins_lbl.config(text=f"{coins_total:,} Coins")
            orbs = stats.get('orbs', 0)
            orbs_str = f"{round(orbs / 1000, 1)}K" if orbs >= 10000 else f"{orbs:,}"
            if hasattr(self, "stat_orbs_lbl"):
                self.stat_orbs_lbl.config(text=f"{orbs_str} Orbs")
        except Exception:
            pass

    def launch_boosted_game(self):
        if not self.mgr.gd_path:
            messagebox.showerror("Error", "Could not locate Geometry Dash folder.")
            return
        if self.mgr.is_gd_process_running():
            messagebox.showinfo("Already Running", "Geometry Dash is already running!")
            return

        # Auto-heal known incompatible mods that cause Windows DLL Entry Point crashes
        incompat = self.mgr.check_incompatible_mods()
        if incompat:
            for item in incompat:
                self.log(f"Auto-repairing incompatible mod {item['name']} ({item['version']})...", "INFO")
                ok, msg = self.mgr.fix_incompatible_mod(item)
                if ok:
                    self.log(f"Auto-repaired {item['name']}: {msg}", "SUCCESS")
                else:
                    self.log(f"Auto-repair error: {msg}", "WARN")
        exe_path = os.path.join(self.mgr.gd_path, "GeometryDash.exe") if IS_WIN else None
        if IS_WIN and exe_path and os.path.exists(exe_path):
            try:
                flags = getattr(subprocess, "HIGH_PRIORITY_CLASS", 0x00000080)
                subprocess.Popen([exe_path], cwd=self.mgr.gd_path, creationflags=flags)
                self.log("🚀 Launched Geometry Dash with HIGH CPU Priority (Ultra-Low Latency)!", "SUCCESS")
                threading.Thread(target=self._monitor_windows_launch, daemon=True).start()
                return
            except Exception as e:
                self.log(f"Direct launch error ({e}), falling back to steam://", "WARN")
        open_url_or_path("steam://rungameid/322170")
        self.log("Launched Geometry Dash via Steam.", "SUCCESS")

    def open_mod_manager(self):
        if not self.mgr.gd_path:
            messagebox.showerror("Error", "Could not locate Geometry Dash folder.")
            return

        mods_dir = os.path.join(self.mgr.gd_path, "geode", "mods")
        if not os.path.exists(mods_dir):
            messagebox.showerror("Error", "Geode mods directory not found.")
            return

        dialog = tk.Toplevel(self)
        dialog.title("GeodeSync · Geode Mod Manager")
        dialog.geometry("640x540")
        dialog.minsize(580, 440)
        dialog.configure(bg=UI["header"])
        dialog.transient(self)
        dialog.grab_set()

        top_frame = tk.Frame(dialog, bg=UI["header"], padx=20, pady=14)
        top_frame.pack(fill="x")

        tk.Label(top_frame, text="🧩 Geode Mod Manager", font=("Segoe UI", 13, "bold"), fg=UI["text"], bg=UI["header"]).pack(anchor="w")
        count_lbl = tk.Label(top_frame, text="Loading mods...", font=("Segoe UI", 9), fg=UI["muted"], bg=UI["header"])
        count_lbl.pack(anchor="w", pady=(2, 8))

        search_frame = tk.Frame(top_frame, bg=UI["header"])
        search_frame.pack(fill="x")

        search_var = tk.StringVar()
        tk.Label(search_frame, text="🔍", font=("Segoe UI", 10), fg=UI["muted"], bg=UI["header"]).pack(side="left", padx=(0, 6))
        search_entry = tk.Entry(search_frame, textvariable=search_var, font=("Segoe UI", 9), bg=UI["inset"], fg=UI["text"], insertbackground=UI["lime"], relief="flat", highlightbackground=UI["border"], highlightthickness=1)
        search_entry.pack(side="left", fill="x", expand=True, ipady=4)

        open_folder_btn = tk.Button(search_frame, text="📁 Open Folder", command=self.open_mods_folder, font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=UI["muted"], activebackground=UI["border"], activeforeground=UI["text"], relief="flat", padx=10, pady=4, cursor="hand2")
        open_folder_btn.pack(side="right", padx=(8, 0))

        store_btn = tk.Button(search_frame, text="🛍️ Mod Store", command=self.open_mod_store_dialog, font=("Segoe UI", 8, "bold"), bg=UI["lime"], fg=UI["background"], activebackground=UI["lime_hover"], activeforeground=UI["text"], relief="flat", padx=10, pady=4, cursor="hand2")
        store_btn.pack(side="right", padx=(8, 0))

        list_container = tk.Frame(dialog, bg=UI["panel"], highlightbackground=UI["border"], highlightthickness=1)
        list_container.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        canvas = tk.Canvas(list_container, bg=UI["panel"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=UI["panel"])

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(xscrollcommand=None, yscrollcommand=scrollbar.set)

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _cleanup():
            try:
                canvas.unbind_all("<MouseWheel>")
            except Exception:
                pass
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", _cleanup)

        def refresh_list():
            for widget in scrollable_frame.winfo_children():
                widget.destroy()

            mods = self.mgr.get_installed_mods()
            q = search_var.get().strip().lower()
            if q:
                mods = [m for m in mods if q in m["name"].lower() or q in m["developer"].lower() or q in m["mod_id"].lower()]

            active_count = sum(1 for m in self.mgr.get_installed_mods() if m["enabled"])
            total_count = len(self.mgr.get_installed_mods())
            count_lbl.config(text=f"{total_count} mods installed ({active_count} active, {total_count - active_count} disabled)")

            if not mods:
                empty_lbl = tk.Label(scrollable_frame, text="No mods found matching search." if q else "No Geode mods installed.", font=("Segoe UI", 10), fg=UI["muted"], bg=UI["panel"], pady=30)
                empty_lbl.pack(fill="x")
                return

            for mod in mods:
                item_frame = tk.Frame(scrollable_frame, bg=UI["panel_alt"], padx=12, pady=8, highlightbackground=UI["border"], highlightthickness=1)
                item_frame.pack(fill="x", padx=8, pady=4)

                left = tk.Frame(item_frame, bg=UI["panel_alt"])
                left.pack(side="left", fill="x", expand=True)

                title_row = tk.Frame(left, bg=UI["panel_alt"])
                title_row.pack(fill="x")

                tk.Label(title_row, text=mod["name"], font=("Segoe UI", 9, "bold"), fg=UI["text"], bg=UI["panel_alt"]).pack(side="left")
                tk.Label(title_row, text=f" {mod['version']}", font=("Segoe UI", 8), fg=UI["lilac"], bg=UI["panel_alt"]).pack(side="left")

                tk.Label(left, text=f"by {mod['developer']} · {mod['mod_id']}", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel_alt"]).pack(anchor="w")

                right = tk.Frame(item_frame, bg=UI["panel_alt"])
                right.pack(side="right")

                is_active = mod["enabled"]
                status_chip = tk.Label(
                    right,
                    text="ACTIVE" if is_active else "DISABLED",
                    font=("Segoe UI", 7, "bold"),
                    fg=UI["lime"] if is_active else UI["muted"],
                    bg=UI["lime_dark"] if is_active else UI["inset"],
                    padx=6, pady=2
                )
                status_chip.pack(side="left", padx=(0, 8))

                def _make_toggle(target_fn, current_state):
                    def _t():
                        ok, res = self.mgr.toggle_mod(target_fn, enable=not current_state)
                        if ok:
                            self.log(f"{'Enabled' if not current_state else 'Disabled'} mod: {target_fn}", "INFO")
                            refresh_list()
                        else:
                            messagebox.showerror("Toggle Error", f"Could not toggle mod:\n{res}", parent=dialog)
                    return _t

                btn_text = "Disable" if is_active else "Enable"
                btn_color = UI["amber"] if is_active else UI["lime"]
                toggle_btn = tk.Button(
                    right,
                    text=btn_text,
                    command=_make_toggle(mod["filename"], is_active),
                    font=("Segoe UI", 8, "bold"),
                    bg=UI["panel"],
                    fg=btn_color,
                    activebackground=UI["border"],
                    activeforeground=UI["text"],
                    relief="flat",
                    padx=10,
                    pady=3,
                    cursor="hand2"
                )
                toggle_btn.pack(side="left")

        search_var.trace_add("write", lambda *args: refresh_list())
        refresh_list()

        bottom_frame = tk.Frame(dialog, bg=UI["header"], padx=20, pady=10)
        bottom_frame.pack(fill="x")

        def _enable_all():
            mods = self.mgr.get_installed_mods()
            for m in mods:
                if not m["enabled"]:
                    self.mgr.toggle_mod(m["filename"], enable=True)
            self.log("Enabled all Geode mods.", "SUCCESS")
            refresh_list()

        def _disable_all():
            mods = self.mgr.get_installed_mods()
            for m in mods:
                if m["enabled"]:
                    self.mgr.toggle_mod(m["filename"], enable=False)
            self.log("Disabled all Geode mods.", "WARN")
            refresh_list()

        tk.Button(bottom_frame, text="✅ Enable All", command=_enable_all, font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=UI["lime"], activebackground=UI["border"], activeforeground=UI["text"], relief="flat", padx=10, pady=5, cursor="hand2").pack(side="left", padx=(0, 6))
        tk.Button(bottom_frame, text="⛔ Disable All", command=_disable_all, font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=UI["amber"], activebackground=UI["border"], activeforeground=UI["text"], relief="flat", padx=10, pady=5, cursor="hand2").pack(side="left")
        tk.Button(bottom_frame, text="Close", command=_cleanup, font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=UI["muted"], activebackground=UI["border"], activeforeground=UI["text"], relief="flat", padx=14, pady=5, cursor="hand2").pack(side="right")

    def browse_gd_path(self):
        selected = filedialog.askdirectory(title="Select Geometry Dash Folder")
        if not selected:
            # Let them pick GeometryDash.exe directly if they prefer
            selected = filedialog.askopenfilename(
                title="Select GeometryDash.exe",
                filetypes=[("Geometry Dash Executable", "GeometryDash.exe;Geometry Dash.app"), ("All Files", "*.*")]
            )
            if selected:
                if selected.endswith(".app"):
                    selected = os.path.dirname(selected) if not IS_MAC else selected
                else:
                    selected = os.path.dirname(selected)

        if selected:
            # If user selected a directory that contains a subfolder with GeometryDash.exe
            if not os.path.isfile(os.path.join(selected, "GeometryDash.exe")) and not (IS_MAC and find_macos_game_app(selected)):
                try:
                    for sub in os.listdir(selected):
                        candidate = os.path.join(selected, sub)
                        if os.path.isdir(candidate) and (
                            os.path.isfile(os.path.join(candidate, "GeometryDash.exe")) or
                            (IS_MAC and find_macos_game_app(candidate))
                        ):
                            selected = candidate
                            break
                except Exception:
                    pass

            is_valid = False
            if IS_MAC:
                if os.path.exists(os.path.join(selected, "Geometry Dash.app")) or os.path.exists(os.path.join(selected, "GeometryDash.app")) or selected.endswith(".app"):
                    is_valid = True
                    if selected.endswith(".app"):
                        selected = os.path.dirname(selected)
            else:
                if os.path.exists(os.path.join(selected, "GeometryDash.exe")):
                    is_valid = True

            if is_valid:
                self.mgr.gd_path = os.path.abspath(selected)
                self.mgr.manifest_path = self.mgr.get_manifest_path()
                self._save_settings()
                self.log(f"Updated GD directory to: {self.mgr.gd_path}", "INFO")
                if "onedrive" in self.mgr.gd_path.casefold():
                    self.log("Notice: This Geometry Dash folder is located in Microsoft OneDrive.", "WARNING")
                self.refresh_status()
            else:
                target_name = "Geometry Dash.app" if IS_MAC else "GeometryDash.exe"
                messagebox.showerror("Invalid Directory", f"The selected folder does not contain {target_name}.")

    def browse_save_path(self):
        selected = filedialog.askdirectory(title="Select Geometry Dash Save Folder (where CCGameManager.dat is stored)")
        if not selected:
            # Allow picking CCGameManager.dat directly
            selected = filedialog.askopenfilename(
                title="Select CCGameManager.dat",
                filetypes=[("Geometry Dash Save Data", "CCGameManager.dat;*.dat"), ("All Files", "*.*")]
            )
            if selected:
                selected = os.path.dirname(selected)

        if selected and os.path.isdir(selected):
            self.mgr.custom_save_path = os.path.abspath(selected)
            self._save_settings()
            has_dat = False
            try:
                has_dat = any(f.lower().startswith("cc") and f.lower().endswith(".dat") for f in os.listdir(selected))
            except Exception:
                pass

            if has_dat:
                self.log(f"Custom save directory linked: {self.mgr.custom_save_path}", "SUCCESS")
                messagebox.showinfo("Save Directory Linked", f"Successfully linked save data from:\n{self.mgr.custom_save_path}")
            else:
                self.log(f"Custom save directory set to {self.mgr.custom_save_path} (no .dat files detected yet)", "INFO")
                messagebox.showwarning("No Save Files Found", f"Folder selected:\n{self.mgr.custom_save_path}\n\nNote: No CCGameManager.dat file was found inside this folder yet.")
            self.refresh_status()

    def launch_gd(self):
        if IS_MAC:
            self.log("Checking Geometry Dash and requesting launch through Steam...", "INFO")
            accepted, details = request_macos_steam_launch(self.mgr.gd_path)
            if accepted:
                self.log(details, "INFO")
                threading.Thread(target=self._monitor_macos_launch, daemon=True).start()
                return
            self.log(details, "ERROR")
            self.open_troubleshooter(details)
            return

        if not self.mgr.gd_path:
            messagebox.showerror("Error", "Could not locate Geometry Dash folder.")
            return

        if self.mgr.is_gd_process_running():
            messagebox.showinfo("Already Running", "Geometry Dash is already running!")
            return

        if IS_WIN:
            image_problem = validate_windows_game_images(self.mgr.gd_path)
            if image_problem:
                self.log(f"Launch stopped: {image_problem}", "ERROR")
                self.open_troubleshooter(image_problem)
                return

        # Auto-heal known incompatible mods that cause Windows DLL Entry Point crashes
        incompat = self.mgr.check_incompatible_mods()
        if incompat:
            for item in incompat:
                self.log(f"Auto-repairing incompatible mod {item['name']} ({item['version']})...", "INFO")
                ok, msg = self.mgr.fix_incompatible_mod(item)
                if ok:
                    self.log(f"Auto-repaired {item['name']}: {msg}", "SUCCESS")
                else:
                    self.log(f"Auto-repair error: {msg}", "WARN")

        self.log("Launching Geometry Dash (High Priority Boost)...", "INFO")
        if hasattr(self, "discord_rpc"):
            ver_text, _ = self.mgr.get_gd_version_info()
            self.discord_rpc.update_presence(DiscordRPC.PLAYING_DETAILS, f"GD {ver_text} · Mods Protected 🛡️", reset_timer=True)

        exe_path = os.path.join(self.mgr.gd_path, "GeometryDash.exe") if IS_WIN else None
        if IS_WIN and exe_path and os.path.exists(exe_path):
            try:
                flags = getattr(subprocess, "HIGH_PRIORITY_CLASS", 0x00000080)
                subprocess.Popen([exe_path], cwd=self.mgr.gd_path, creationflags=flags)
                self.log("🚀 Launched Geometry Dash with HIGH CPU Priority (Ultra-Low Latency)!", "SUCCESS")
                return
            except Exception as e:
                self.log(f"Direct launch error ({e}), falling back to steam://", "WARN")

        if not open_url_or_path(f"steam://run/{APP_ID}"):
            self.log("Could not pass the Geometry Dash launch request to Steam.", "ERROR")
            self.open_troubleshooter("Could not pass the Geometry Dash launch request to Steam.")
        else:
            self.log("Launched Geometry Dash via Steam.", "SUCCESS")
            if IS_WIN:
                threading.Thread(target=self._monitor_windows_launch, daemon=True).start()

    def _monitor_windows_launch(self):
        started = wait_for_process(self.mgr.is_gd_process_running, timeout=30, interval=0.5)
        if started:
            return
        message = (
            "Steam accepted the launch request, but Windows did not start Geometry Dash within 30 seconds. "
            "If Windows showed an error window, paste its exact text or code into Fix a problem."
        )
        try:
            self.after(0, lambda: self.open_troubleshooter(message))
        except Exception:
            pass

    def _monitor_macos_launch(self):
        started = wait_for_process(self.mgr.is_gd_process_running, timeout=60, interval=1)
        def report():
            if started:
                self.log("Geometry Dash process started successfully through Steam.", "SUCCESS")
                return
            message = (
                "Steam accepted the launch request, but Geometry Dash did not start within 60 seconds. "
                "Check Steam's gameprocess log and macOS Console for the launch failure; GeodeSync did not "
                "change the game files during this launch attempt."
            )
            self.log(message, "ERROR")
            messagebox.showerror("Geometry Dash did not start", message)
        try:
            self.after(0, report)
        except Exception:
            pass

    def check_remote_updates(self):
        try:
            req = urllib.request.Request(CONFIG_URL, headers={"User-Agent": "GeodeSync-Client"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode())
                if not self.user_selected_target:
                    manifest_key = "target_manifest_mac" if IS_MAC else "target_manifest_win"
                    if manifest_key in data and data[manifest_key]:
                        self.mgr.target_manifest = data[manifest_key]
                    elif "target_manifest" in data and data["target_manifest"] and not IS_MAC:
                        self.mgr.target_manifest = data["target_manifest"]
                    if "geode_target_gd" in data and data["geode_target_gd"]:
                        self.mgr.target_gd_version = data["geode_target_gd"]
        except Exception:
            pass

        try:
            rel = fetch_latest_published_release(timeout=8)
            tag = str(rel.get("tag_name", "")).lstrip("v")
            if is_newer_app_version(tag, APP_VERSION):
                self.latest_release_url = rel.get("html_url", f"https://github.com/{GITHUB_REPO}/releases")
                if not release_has_app_update(rel):
                    self.after(0, lambda tag=tag: self.log(
                        f"GeodeSync v{tag} exists, but no verified update package is published for this platform yet.",
                        "INFO",
                    ))
                    return
                self.after(0, lambda: self.show_update_banner(tag))
                if getattr(sys, "frozen", False):
                    self.after(0, lambda: self._start_auto_update_if_needed(rel))
        except Exception:
            pass

    def show_update_banner(self, new_ver: str, prompt=False):
        self.update_label.config(text=f"🎉 Update available: v{new_ver}! (Current: v{APP_VERSION})")
        try:
            if hasattr(self, "header_frame") and self.header_frame.winfo_exists():
                self.update_banner.pack(fill="x", side="top", before=self.header_frame)
            else:
                self.update_banner.pack(fill="x", side="top")
        except Exception:
            self.update_banner.pack(fill="x", side="top")
        self.log(f"GeodeSync v{new_ver} is available. The app will download and verify the official update package.", "SUCCESS")

    def _start_auto_update_if_needed(self, release):
        if not self._app_update_in_progress and not self._staged_app_update:
            self.start_self_update(auto_install=True, release=release)

    def manual_check_updates(self):
        self.log("Checking for GeodeSync updates...", "INFO")
        def _check():
            try:
                rel = fetch_latest_published_release(timeout=6)
                tag = str(rel.get("tag_name", "")).lstrip("v")
                if is_newer_app_version(tag, APP_VERSION):
                    self.latest_release_url = rel.get("html_url", f"https://github.com/{GITHUB_REPO}/releases")
                    if not release_has_app_update(rel):
                        message = (
                            f"GeodeSync v{tag} is published, but its verified package for this platform "
                            "is not available yet. Your current installation was left unchanged."
                        )
                        self.after(0, lambda message=message: messagebox.showinfo(
                            "Update not available yet", message, parent=self
                        ))
                        self.after(0, lambda tag=tag: self.log(
                            f"GeodeSync v{tag} is published, but this platform has no verified package yet.",
                            "INFO",
                        ))
                        return
                    self.after(0, lambda: self.show_update_banner(tag))
                    if getattr(sys, "frozen", False):
                        self.after(0, lambda: self._start_auto_update_if_needed(rel))
                else:
                    self.after(0, lambda: messagebox.showinfo("Up to Date", f"You are running the latest version of GeodeSync (v{APP_VERSION}).", parent=self))
                    self.after(0, lambda: self.log(f"GeodeSync v{APP_VERSION} is up to date.", "SUCCESS"))
            except Exception as e:
                self.after(0, lambda error=str(e): messagebox.showerror("Update Check Failed", f"Could not check for updates:\n{error}", parent=self))
                self.after(0, lambda error=str(e): self.log(f"Update check failed: {error}", "ERROR"))
        threading.Thread(target=_check, daemon=True).start()

    def open_update_link(self):
        url = official_release_page(self.latest_release_url)
        webbrowser.open(url)

    # ==========================================
    # v1.1.2 PRO FEATURE: 1-CLICK CORRUPTED SAVE DOCTOR
    # ==========================================
    def run_save_doctor(self):
        save_dir = self.mgr.get_save_data_dir()
        if not save_dir or not os.path.exists(save_dir):
            messagebox.showerror("Error", "Could not locate Geometry Dash save folder.")
            return

        def test_save_file(filename):
            path = os.path.join(save_dir, filename)
            if not os.path.exists(path):
                return False, 0, "Missing"
            sz = os.path.getsize(path)
            if sz == 0:
                return False, 0, "0 Bytes (Corrupted)"
            try:
                with open(path, "rb") as f:
                    raw = f.read()
                decomp = decode_geometry_dash_save(raw)
                if b"<plist" in decomp:
                    return True, sz, "Healthy"
                return False, sz, "Invalid XML structure"
            except Exception as e:
                return False, sz, f"Corrupted ({type(e).__name__})"

        gm_ok, gm_sz, gm_msg = test_save_file("CCGameManager.dat")
        lvl_ok, lvl_sz, lvl_msg = test_save_file("CCLocalLevels.dat")

        if gm_ok and lvl_ok:
            gm_mb = round(gm_sz / (1024 * 1024), 2)
            lvl_kb = round(lvl_sz / 1024, 1)
            res = messagebox.askyesno(
                "💽 Save Doctor: 100% Healthy!",
                f"✅ Save File Diagnostic Results:\n\n"
                f"• CCGameManager.dat: {gm_msg} ({gm_mb} MB)\n"
                f"• CCLocalLevels.dat: {lvl_msg} ({lvl_kb} KB)\n\n"
                f"Both primary save files are fully intact, properly encrypted, and readable by Geometry Dash.\n\n"
                f"Would you like to create a timestamped backup now for extra protection?"
            )
            if res:
                self.backup_saves()
            return

        corrupted_files = []
        if not gm_ok:
            corrupted_files.append(f"CCGameManager.dat ({gm_msg})")
        if not lvl_ok:
            corrupted_files.append(f"CCLocalLevels.dat ({lvl_msg})")

        fallbacks = []
        gm2_ok, _, _ = test_save_file("CCGameManager2.dat")
        if not gm_ok and gm2_ok:
            fallbacks.append(("CCGameManager.dat", "CCGameManager2.dat"))

        lvl2_ok, _, _ = test_save_file("CCLocalLevels2.dat")
        if not lvl_ok and lvl2_ok:
            fallbacks.append(("CCLocalLevels.dat", "CCLocalLevels2.dat"))

        backup_root = os.path.join(save_dir, "GeodeSync_Save_Backups")
        if os.path.exists(backup_root):
            folders = [os.path.join(backup_root, d) for d in os.listdir(backup_root) if os.path.isdir(os.path.join(backup_root, d))]
            folders.sort(key=os.path.getmtime, reverse=True)
            if folders:
                latest_bak = folders[0]
                if not gm_ok and not any(t[0] == "CCGameManager.dat" for t in fallbacks):
                    bak_gm = os.path.join(latest_bak, "CCGameManager.dat")
                    if os.path.exists(bak_gm):
                        fallbacks.append(("CCGameManager.dat", bak_gm))
                if not lvl_ok and not any(t[0] == "CCLocalLevels.dat" for t in fallbacks):
                    bak_lvl = os.path.join(latest_bak, "CCLocalLevels.dat")
                    if os.path.exists(bak_lvl):
                        fallbacks.append(("CCLocalLevels.dat", bak_lvl))

        if fallbacks:
            msg = f"⚠️ Corrupted Save Detected:\n" + "\n".join(f"• {c}" for c in corrupted_files) + "\n\n"
            msg += "✅ Good news! Save Doctor located intact backup save files:\n"
            for target, src in fallbacks:
                msg += f"👉 Restore {target} from {os.path.basename(src)}\n"
            msg += "\nWould you like Save Doctor to automatically repair and restore your save files now?"
            res = messagebox.askyesno("💽 Save Doctor: Repair Available", msg)
            if res:
                for target, src in fallbacks:
                    src_path = os.path.join(save_dir, src) if not os.path.isabs(src) else src
                    dst_path = os.path.join(save_dir, target)
                    if os.path.exists(dst_path):
                        shutil.move(dst_path, dst_path + ".corrupted_bak")
                    safe_copy_item(src_path, dst_path)
                self.play_ding()
                self.log("Save Doctor successfully repaired corrupted save files!", "SUCCESS")
                messagebox.showinfo("Save Doctor", "🎉 Save files successfully repaired and restored!\n\nYou can now launch Geometry Dash safely.")
        else:
            messagebox.showerror(
                "💽 Save Doctor",
                f"⚠️ Save file corruption detected:\n" + "\n".join(f"• {c}" for c in corrupted_files) + "\n\n"
                f"No automatic backup was found in the save directory. If you have an external backup or Steam Cloud sync, restore it manually."
            )

    # ==========================================
    # v1.1.2 PRO FEATURE: GD STORAGE & CACHE CLEANER
    # ==========================================
    def open_cache_cleaner(self):
        save_dir = self.mgr.get_save_data_dir()
        if not save_dir or not os.path.exists(save_dir):
            messagebox.showerror("Error", "Could not locate Geometry Dash save folder.")
            return

        song_files = []
        song_bytes = 0
        log_files = []
        log_bytes = 0

        for item in os.listdir(save_dir):
            fp = os.path.join(save_dir, item)
            if os.path.isfile(fp):
                ext = os.path.splitext(item)[1].lower()
                sz = os.path.getsize(fp)
                if ext in [".mp3", ".ogg"]:
                    song_files.append(fp)
                    song_bytes += sz
                elif ext in [".log", ".dmp", ".tmp"]:
                    log_files.append(fp)
                    log_bytes += sz

        crash_dir = self.mgr.get_crashlogs_dir()
        if crash_dir and os.path.exists(crash_dir):
            for item in os.listdir(crash_dir):
                fp = os.path.join(crash_dir, item)
                if os.path.isfile(fp):
                    sz = os.path.getsize(fp)
                    log_files.append(fp)
                    log_bytes += sz

        dialog = tk.Toplevel(self)
        dialog.title("Geometry Dash Storage & Cache Cleaner")
        dialog.geometry("540x380")
        dialog.configure(bg=UI["header"])
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="🧹 GD Storage & Cache Cleaner", font=("Segoe UI", 13, "bold"), fg=UI["text"], bg=UI["header"]).pack(anchor="w", padx=20, pady=(16, 4))
        tk.Label(dialog, text="Free up gigabytes of disk space on your drive by safely clearing cached data:", font=("Segoe UI", 9), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", padx=20, pady=(0, 14))

        card = tk.Frame(dialog, bg=UI["panel"], padx=16, pady=12, highlightbackground=UI["border"], highlightthickness=1)
        card.pack(fill="x", padx=20, pady=(0, 14))

        clean_logs_var = tk.BooleanVar(value=True)
        clean_songs_var = tk.BooleanVar(value=False)

        log_mb = round(log_bytes / (1024 * 1024), 2)
        song_mb = round(song_bytes / (1024 * 1024), 1)
        song_gb = round(song_bytes / (1024 * 1024 * 1024), 2)

        cb1 = tk.Checkbutton(
            card,
            text=f"💥 Crash Dumps & Old Log Files ({len(log_files)} files • {log_mb} MB) [100% Safe]",
            variable=clean_logs_var,
            font=("Segoe UI", 9, "bold"),
            fg=UI["lilac"],
            bg=UI["panel"],
            selectcolor=UI["inset"],
            activebackground=UI["panel"],
            activeforeground=UI["lilac"]
        )
        cb1.pack(anchor="w", pady=(0, 6))

        cb2 = tk.Checkbutton(
            card,
            text=f"🎵 Downloaded Songs & SFX Cache ({len(song_files)} files • {song_gb} GB / {song_mb} MB)",
            variable=clean_songs_var,
            font=("Segoe UI", 9, "bold"),
            fg=UI["text"],
            bg=UI["panel"],
            selectcolor=UI["inset"],
            activebackground=UI["panel"],
            activeforeground=UI["text"]
        )
        cb2.pack(anchor="w", pady=(0, 4))
        tk.Label(
            card,
            text="  * Note: Clearing song cache leaves saves 100% safe. Songs re-download if you replay them.",
            font=("Segoe UI", 8),
            fg=UI["quiet"],
            bg=UI["panel"]
        ).pack(anchor="w")

        def perform_clean():
            del_count = 0
            del_bytes = 0
            to_del = []
            if clean_logs_var.get():
                to_del.extend(log_files)
            if clean_songs_var.get():
                to_del.extend(song_files)

            if not to_del:
                messagebox.showinfo("Nothing Selected", "Please select at least one item to clean.")
                return

            res = messagebox.askyesno(
                "Confirm Cleanup",
                f"Are you sure you want to clean {len(to_del)} cached files?\n\nSave files, levels, and icons will NOT be touched."
            )
            if not res:
                return

            for f in to_del:
                try:
                    sz = os.path.getsize(f)
                    os.remove(f)
                    del_count += 1
                    del_bytes += sz
                except Exception:
                    pass

            freed_mb = round(del_bytes / (1024 * 1024), 1)
            self.play_ding()
            self.log(f"Cache Cleaner reclaimed {freed_mb} MB ({del_count} files removed).", "SUCCESS")
            dialog.destroy()
            messagebox.showinfo("Cleanup Complete!", f"🎉 Successfully cleaned {del_count} cached files!\n\nReclaimed {freed_mb} MB of drive space.")

        btn_box = tk.Frame(dialog, bg=UI["header"])
        btn_box.pack(fill="x", side="bottom", padx=20, pady=16)

        cancel_btn = tk.Button(btn_box, text="Cancel", command=dialog.destroy, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["muted"], relief="flat", padx=10, pady=4, cursor="hand2")
        cancel_btn.pack(side="left")

        clean_btn = tk.Button(btn_box, text="⚡ Clean Selected Cache", command=perform_clean, font=("Segoe UI", 9, "bold"), bg=UI["lime"], fg=UI["text"], activebackground=UI["lime_hover"], activeforeground=UI["text"], relief="flat", padx=16, pady=4, cursor="hand2")
        clean_btn.pack(side="right")

    # ==========================================
    # v1.1.2 PRO FEATURE: MOD PROFILES & VANILLA TOGGLE
    # ==========================================
    def open_mod_profiles(self):
        mods_dir = self.get_mods_dir()
        if not mods_dir or not os.path.exists(mods_dir):
            messagebox.showinfo("Geode Mods", "No geode/mods directory found.")
            return

        profiles_dir = os.path.join(mods_dir, "..", "profiles")
        os.makedirs(profiles_dir, exist_ok=True)

        def get_mods_state():
            all_files = os.listdir(mods_dir)
            active = [f for f in all_files if f.endswith(".geode")]
            disabled = [f for f in all_files if f.endswith(".geode.disabled")]
            return active, disabled

        active, disabled = get_mods_state()

        dialog = tk.Toplevel(self)
        dialog.title("Geode Mod Profile Switcher")
        dialog.geometry("520x400")
        dialog.configure(bg=UI["header"])
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="🔄 Mod Profile & Vanilla Switcher", font=("Segoe UI", 12, "bold"), fg=UI["text"], bg=UI["header"]).pack(anchor="w", padx=20, pady=(16, 4))
        status_lbl = tk.Label(dialog, text=f"Installed Mods: {len(active) + len(disabled)} ({len(active)} Active, {len(disabled)} Disabled)", font=("Segoe UI", 9), fg=UI["lilac"], bg=UI["header"])
        status_lbl.pack(anchor="w", padx=20, pady=(0, 12))

        card = tk.Frame(dialog, bg=UI["panel"], padx=14, pady=12, highlightbackground=UI["border"], highlightthickness=1)
        card.pack(fill="x", padx=20, pady=(0, 12))

        def disable_all():
            act, _ = get_mods_state()
            if not act:
                messagebox.showinfo("Info", "All mods are already disabled.")
                return
            res = messagebox.askyesno("Vanilla Mode", f"Disable all {len(act)} active mods to play pure vanilla Geometry Dash?\n\n(You can re-enable them anytime in 1 click).")
            if res:
                for m in act:
                    try:
                        os.rename(os.path.join(mods_dir, m), os.path.join(mods_dir, m + ".disabled"))
                    except Exception:
                        pass
                self.log(f"Switched to Pure Vanilla: Disabled {len(act)} mods.", "SUCCESS")
                dialog.destroy()
                self.refresh_status()
                messagebox.showinfo("Vanilla Mode Active", "All mods have been disabled. GD is in pure vanilla mode!")

        def enable_all():
            _, dis = get_mods_state()
            if not dis:
                messagebox.showinfo("Info", "All mods are already enabled.")
                return
            for m in dis:
                try:
                    base = m[:-9]
                    os.rename(os.path.join(mods_dir, m), os.path.join(mods_dir, base))
                except Exception:
                    pass
            self.log(f"Enabled {len(dis)} Geode mods.", "SUCCESS")
            dialog.destroy()
            self.refresh_status()
            messagebox.showinfo("All Mods Enabled", f"Re-enabled {len(dis)} mods successfully!")

        tk.Label(card, text="Quick Presets:", font=("Segoe UI", 8, "bold"), fg=UI["quiet"], bg=UI["panel"]).pack(anchor="w", pady=(0, 6))

        btn_row = tk.Frame(card, bg=UI["panel"])
        btn_row.pack(fill="x", pady=(0, 8))

        tk.Button(btn_row, text="🛡️ Vanilla Mode (Disable All)", command=disable_all, font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=UI["red"], activebackground=UI["border"], activeforeground=UI["text"], relief="flat", padx=10, pady=5, cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="⚡ Enable All Mods", command=enable_all, font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=UI["lime"], activebackground=UI["border"], activeforeground=UI["text"], relief="flat", padx=10, pady=5, cursor="hand2").pack(side="left")

        card2 = tk.Frame(dialog, bg=UI["panel"], padx=14, pady=12, highlightbackground=UI["border"], highlightthickness=1)
        card2.pack(fill="x", padx=20, pady=(0, 10))

        tk.Label(card2, text="Custom Profiles:", font=("Segoe UI", 8, "bold"), fg=UI["quiet"], bg=UI["panel"]).pack(anchor="w", pady=(0, 6))

        def save_profile():
            name_win = simpledialog.askstring("Save Profile", "Enter profile name (e.g. Demon Grinding, Recording):", parent=dialog)
            if name_win:
                safe_name = "".join(c for c in name_win if c.isalnum() or c in (' ', '_', '-')).strip()
                if safe_name:
                    act, _ = get_mods_state()
                    p_path = os.path.join(profiles_dir, f"{safe_name}.json")
                    with open(p_path, "w", encoding="utf-8") as f:
                        json.dump({"name": safe_name, "active_mods": act}, f, indent=2)
                    self.log(f"Saved mod profile: {safe_name} ({len(act)} mods)", "SUCCESS")
                    messagebox.showinfo("Profile Saved", f"Saved profile '{safe_name}' with {len(act)} active mods!")

        def load_profile():
            profiles = [f for f in os.listdir(profiles_dir) if f.endswith(".json")]
            if not profiles:
                messagebox.showinfo("No Profiles", "No custom profiles saved yet! Click 'Save Current Profile' first.")
                return

            p_win = tk.Toplevel(dialog)
            p_win.title("Load Mod Profile")
            p_win.geometry("380x260")
            p_win.configure(bg=UI["header"])
            p_win.transient(dialog)
            p_win.grab_set()

            tk.Label(p_win, text="Select Profile to Activate:", font=("Segoe UI", 10, "bold"), fg=UI["text"], bg=UI["header"]).pack(anchor="w", padx=16, pady=(12, 6))
            p_listbox = tk.Listbox(p_win, bg=UI["inset"], fg=UI["text"], font=("Segoe UI", 9), selectbackground=UI["lilac"])
            p_listbox.pack(fill="both", expand=True, padx=16, pady=(0, 10))

            for p in profiles:
                p_listbox.insert("end", p[:-5])

            def apply_sel():
                sel = p_listbox.curselection()
                if not sel:
                    return
                chosen = profiles[sel[0]]
                with open(os.path.join(profiles_dir, chosen), "r", encoding="utf-8") as f:
                    p_data = json.load(f)
                wanted = set(p_data.get("active_mods", []))

                all_f = os.listdir(mods_dir)
                for f in all_f:
                    if f.endswith(".geode"):
                        if f not in wanted:
                            try:
                                os.rename(os.path.join(mods_dir, f), os.path.join(mods_dir, f + ".disabled"))
                            except Exception:
                                pass
                    elif f.endswith(".geode.disabled"):
                        base = f[:-9]
                        if base in wanted:
                            try:
                                os.rename(os.path.join(mods_dir, f), os.path.join(mods_dir, base))
                            except Exception:
                                pass

                self.log(f"Applied profile: {p_data.get('name')}", "SUCCESS")
                p_win.destroy()
                dialog.destroy()
                self.refresh_status()
                messagebox.showinfo("Profile Applied", f"Loaded profile '{p_data.get('name')}' successfully!")

            tk.Button(p_win, text="Apply Profile", command=apply_sel, font=("Segoe UI", 9, "bold"), bg=UI["lilac"], fg=UI["text"], activebackground=UI["lilac_dark"], relief="flat", padx=12, pady=3, cursor="hand2").pack(pady=(0, 10))

        btn_row2 = tk.Frame(card2, bg=UI["panel"])
        btn_row2.pack(fill="x")
        tk.Button(btn_row2, text="💾 Save Current Profile", command=save_profile, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["lilac"], activebackground=UI["border"], activeforeground=UI["text"], relief="flat", padx=10, pady=4, cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(btn_row2, text="📂 Load Profile", command=load_profile, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["lilac"], activebackground=UI["border"], activeforeground=UI["text"], relief="flat", padx=10, pady=4, cursor="hand2").pack(side="left")

        close_btn = tk.Button(dialog, text="Close", command=dialog.destroy, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["muted"], relief="flat", padx=12, pady=4, cursor="hand2")
        close_btn.pack(side="bottom", pady=14)

    # ==========================================
    # v1.1.2 PRO FEATURE: 1-CLICK IN-APP SELF-UPDATER
    # ==========================================
    def start_self_update(self, auto_install=False, release=None):
        """Download and verify the official package, then offer a safe restart install."""
        if self._staged_app_update:
            self._launch_staged_app_update(self._staged_app_update)
            return
        if self._app_update_in_progress:
            return
        if not getattr(sys, "frozen", False):
            self.open_update_link()
            return
        self._app_update_in_progress = True
        self.update_action_btn.config(state="disabled", text="Downloading…")
        self.log("Downloading the official GeodeSync update and checking its SHA-256 digest…", "INFO")

        def download_and_offer():
            work_dir = None
            try:
                rel = release or fetch_latest_published_release(timeout=20)
                tag = str(rel.get("tag_name", "")).lstrip("v")
                if not is_newer_app_version(tag, APP_VERSION):
                    raise ValueError("No newer stable GeodeSync release is available.")
                target = _application_root()
                parent = os.path.dirname(target)
                if not os.path.isdir(target) or not os.access(parent, os.W_OK):
                    raise PermissionError("GeodeSync is in a protected folder. Move it to a user-writable folder, then update again.")
                work_dir = tempfile.mkdtemp(prefix=".GeodeSync-update-", dir=parent)
                asset, extracted = download_verified_app_update(rel, work_dir)
                payload = os.path.join(extracted, "GeodeSync.app") if IS_MAC else extracted
                if IS_MAC and not os.path.isdir(payload):
                    raise ValueError("The Mac update package does not contain GeodeSync.app.")
                data = {"payload": payload, "target": target, "backup": os.path.join(work_dir, "previous-install"), "pid": os.getpid()}
                staged = {"tag": tag, "data": data, "work_dir": work_dir, "payload": payload, "asset": asset}
                self.after(0, lambda staged=staged: self._finish_staged_app_update(staged, auto_install))
            except Exception as error:
                self._app_update_in_progress = False
                if work_dir:
                    shutil.rmtree(work_dir, ignore_errors=True)
                self.after(0, lambda error=error: self.update_action_btn.config(state="normal", text="Retry update"))
                self.after(0, lambda error=error: self.log(f"Automatic update could not be staged: {error}", "ERROR"))
                self.after(0, lambda error=error: messagebox.showerror("Update could not be installed", str(error), parent=self))

        threading.Thread(target=download_and_offer, daemon=True).start()

    def _finish_staged_app_update(self, staged, auto_install):
        self._staged_app_update = staged
        self._app_update_in_progress = False
        self.update_action_btn.config(state="normal", text="Updating…" if auto_install else "Restart to update")
        self.log(f"Downloaded v{staged['tag']} and verified the release checksum. Ready to install.", "SUCCESS")
        if auto_install:
            self._apply_verified_update_when_idle(staged)

    def _apply_verified_update_when_idle(self, staged):
        """Apply a verified update without a restart prompt, after game-file work ends."""
        if getattr(self, "is_downloading_depot", False):
            try:
                self.after(5000, lambda staged=staged: self._apply_verified_update_when_idle(staged))
            except Exception:
                pass
            return
        self.log(f"Applying verified GeodeSync v{staged['tag']} and restarting now.", "INFO")
        self._launch_staged_app_update(staged)

    def _launch_staged_app_update(self, staged):
        try:
            data = dict(staged["data"])
            encoded = base64.urlsafe_b64encode(json.dumps(data).encode("utf-8")).decode("ascii")
            work_dir = staged["work_dir"]
            if IS_WIN:
                helper = os.path.join(work_dir, "updater")
                shutil.copytree(staged["payload"], helper)
                mark_windows_download(os.path.join(helper, "GeodeSync.exe"), "https://github.com/" + GITHUB_REPO + "/releases")
                command = [os.path.join(helper, "GeodeSync.exe"), "--geodesync-apply-update", encoded]
            elif IS_MAC:
                command = [os.path.join(staged["payload"], "Contents", "MacOS", "GeodeSync"), "--geodesync-apply-update", encoded]
            else:
                command = [os.path.join(staged["payload"], "GeodeSync"), "--geodesync-apply-update", encoded]
            subprocess.Popen(command, cwd=os.path.dirname(_application_root()), close_fds=True)
            self.quit_app()
        except Exception as error:
            self.log(f"Could not start the verified update helper: {error}", "ERROR")
            messagebox.showerror("Update could not be started", str(error), parent=self)

    def _schedule_update_progress(self, text, value=None, hide=False):
        def update_ui():
            try:
                if not self.winfo_exists():
                    return
                if hide:
                    self.progress_frame.pack_forget()
                    return
                self.progress_frame.pack(fill="x", pady=(0, 8), before=self.primary_btn)
                self.progress_lbl.config(text=text)
                if value is not None:
                    self.progress_bar["value"] = value
            except Exception:
                pass
        try:
            self.after(0, update_ui)
        except Exception:
            pass

    def _remote_update_monitor_thread(self):
        while getattr(self, "_monitor_running", True):
            try:
                self.check_remote_updates()
            except Exception:
                pass
            try:
                self.check_geode_updates()
            except Exception:
                pass
            time.sleep(120)

    def check_geode_updates(self):
        try:
            rel = fetch_latest_geode_release(timeout=6)
            latest_tag = str(rel.get("tag_name", "")).strip()
            installed = self.mgr.get_installed_geode_version()
            if latest_tag and installed:
                latest_clean = latest_tag.lstrip("v")
                inst_clean = installed.lstrip("v")
                if is_newer_app_version(latest_clean, inst_clean):
                    self.after(0, lambda: self.log(f"🔔 Newer Geode version available: {latest_tag} (Current: {installed}). Click '⚡ Update Geode' to install!", "WARN"))
        except Exception:
            pass

    def manual_update_geode(self):
        if not self.mgr.gd_path:
            messagebox.showerror("Error", "Geometry Dash game folder not found.", parent=self)
            return
        if self.mgr.is_gd_process_running():
            messagebox.showwarning("Game Running", "Please close Geometry Dash before updating Geode.", parent=self)
            return
        self.log("Checking latest Geode release from GitHub...", "INFO")
        def _worker():
            try:
                rel = fetch_latest_geode_release(timeout=8)
                tag = str(rel.get("tag_name", "")).strip()
                installed = self.mgr.get_installed_geode_version()

                msg = f"Latest Geode release: {tag}\nInstalled version: {installed or 'Not installed'}\n\nWould you like to install/update Geode now?"
                if not messagebox.askyesno("Update Geode", msg, parent=self):
                    return

                self.after(0, lambda: self.log(f"Auto-updating Geode to {tag}...", "INFO"))
                updated_tag = install_or_update_geode(self.mgr.gd_path, log_callback=lambda m: self.after(0, lambda: self.log(m, "INFO")))
                self.after(0, self.refresh_status)
                self.after(0, lambda: self.log(f"🎉 Geode successfully updated to {updated_tag}!", "SUCCESS"))
                self.after(0, lambda: messagebox.showinfo("Geode Updated!", f"🎉 Geode was successfully updated to {updated_tag}!\n\nAll your mods and configurations are preserved.", parent=self))
            except Exception as e:
                self.after(0, lambda error=str(e): self.log(f"Failed to update Geode: {error}", "ERROR"))
                self.after(0, lambda error=str(e): messagebox.showerror("Update Error", f"Could not update Geode:\n{error}", parent=self))
        threading.Thread(target=_worker, daemon=True).start()

    # ==========================================
    # v1.1.3 PRO FEATURE: AUTO-BACKUP ON GD EXIT
    # ==========================================
    def _auto_backup_monitor_thread(self):
        was_running = None
        while getattr(self, "_monitor_running", True):
            try:
                is_running = self.mgr.is_gd_process_running()
                ver_text, _ = self.mgr.get_gd_version_info()
                is_locked = self.mgr.is_manifest_locked()
                geode_ver = self.mgr.get_installed_geode_version() or "v5.x"
                stats = self.mgr.get_player_stats()
                player_tag = f"{stats['stars']} ⭐ · {stats['demons']} 👿" if stats else None

                if is_running:
                    grind_text = None
                    try:
                        prog_data = self.mgr.get_demon_and_grind_data()
                        if prog_data and prog_data.get("grinds"):
                            top_grind = prog_data["grinds"][0]
                            grind_text = f"Grinding {top_grind['name']} ({top_grind['percent']}%)"
                    except Exception:
                        pass

                    if grind_text:
                        details_text = f"GD {ver_text} · {grind_text}"
                        status_desc = f"{player_tag} · Geode {geode_ver} 🛡️" if is_locked else f"{player_tag} · Playing GD"
                    elif player_tag:
                        details_text = DiscordRPC.PLAYING_DETAILS
                        status_desc = f"{player_tag} · Geode {geode_ver} 🛡️" if is_locked else f"{player_tag} · Playing GD"
                    else:
                        details_text = DiscordRPC.PLAYING_DETAILS
                        status_desc = f"GD {ver_text} · Geode {geode_ver} 🛡️" if is_locked else f"GD {ver_text} · In Game"

                    if hasattr(self, "discord_rpc"):
                        self.discord_rpc.update_presence(details_text, status_desc, reset_timer=(was_running is False), geode_ver=geode_ver)
                else:
                    if player_tag:
                        idle_desc = f"{stats['name']} ({player_tag})"
                    else:
                        idle_desc = f"GD {ver_text} · Geode {geode_ver} (Ready)" if is_locked else f"GD {ver_text} · Ready to Play"
                    if hasattr(self, "discord_rpc"):
                        self.discord_rpc.update_presence(DiscordRPC.COMPANION_DETAILS, idle_desc, reset_timer=(was_running is True), geode_ver=geode_ver)

                if was_running is True and not is_running:
                    self.after(0, self.update_player_stats_ui)
                    if getattr(self, "auto_backup_enabled", True):
                        copied = self.mgr.perform_silent_backup()
                        if copied:
                            self.log(f"Auto-Backup: Saved {copied} files after GD closed.", "SUCCESS")
                was_running = is_running
            except Exception:
                pass
            time.sleep(3)

    def toggle_auto_backup(self):
        self.auto_backup_enabled = not getattr(self, "auto_backup_enabled", True)
        if self.auto_backup_enabled:
            self.auto_backup_btn.config(text="Auto-Backup: ON", fg=UI["lime"], bg=UI["panel_alt"])
            self.log("Auto-Backup on GD Exit ENABLED.", "INFO")
        else:
            self.auto_backup_btn.config(text="Auto-Backup: OFF", fg=UI["muted"], bg=UI["panel_alt"])
            self.log("Auto-Backup on GD Exit DISABLED.", "INFO")
        self._save_settings()

    def toggle_steam_lock(self):
        if not self.mgr.manifest_path or not os.path.exists(self.mgr.manifest_path):
            messagebox.showerror("Error", "Could not locate Steam's appmanifest_322170.acf file.")
            return

        currently_locked = self.mgr.is_manifest_locked()
        new_state = not currently_locked
        try:
            self.mgr.set_manifest_locked(new_state)
            self.refresh_status()
            state_str = "Locked" if new_state else "Unlocked"
            self.log(f"Steam update lock set to: {state_str}.", "SUCCESS")
            if new_state:
                messagebox.showinfo(
                    "Steam Updates Locked",
                    "Steam update lock is now LOCKED (Protected)!\n\n"
                    "Steam's Geometry Dash manifest is set to Read-Only, which blocks Steam from automatically overwriting your game with 2.209."
                )
            else:
                messagebox.showinfo(
                    "Steam Updates Unlocked",
                    "Steam update lock is now UNLOCKED (Normal).\n\n"
                    "Steam is permitted to update Geometry Dash."
                )
        except Exception as e:
            self.log(f"Error changing Steam update lock: {e}", "ERROR")
            messagebox.showerror("Error", f"Could not change Steam update lock:\n{e}")

    def toggle_sounds(self):
        self.sounds_enabled = not getattr(self, "sounds_enabled", False)
        if self.sounds_enabled:
            self.sounds_btn.config(text="🔊 GD Sounds: ON", fg=UI["lime"])
            self.play_ding()
        else:
            self.sounds_btn.config(text="🔇 GD Sounds: OFF", fg=UI["muted"])
        self._save_settings()

    def create_desktop_shortcut(self):
        try:
            my_exe = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath("main.py")
            if IS_WIN:
                vbs_code = (
                    'Set ws = CreateObject("WScript.Shell")\n'
                    'desktop = ws.SpecialFolders("Desktop")\n'
                    f'Set s = ws.CreateShortcut(desktop & "\\GeodeSync.lnk")\n'
                    f's.TargetPath = "{my_exe}"\n'
                    f's.WorkingDirectory = "{os.path.dirname(my_exe)}"\n'
                    f's.Description = "GeodeSync - Geometry Dash Companion"\n'
                    's.Save\n'
                )
                vbs_path = os.path.join(tempfile.gettempdir(), "make_geodesync_shortcut.vbs")
                with open(vbs_path, "w", encoding="utf-8") as f:
                    f.write(vbs_code)
                subprocess.run(["cscript", "//nologo", vbs_path], check=True, creationflags=0x08000000)
                try:
                    os.remove(vbs_path)
                except Exception:
                    pass
                self.play_ding()
                self.log("Created GeodeSync desktop shortcut.", "SUCCESS")
                messagebox.showinfo("Shortcut Created", "🎉 Created a GeodeSync shortcut on your Desktop!")
                return
            elif IS_LINUX:
                desktop_dir = os.path.expanduser("~/Desktop")
                if os.path.exists(desktop_dir):
                    dest = os.path.join(desktop_dir, "GeodeSync.desktop")
                    exec_line = desktop_exec_value(my_exe) if getattr(sys, "frozen", False) else f"{desktop_exec_value(sys.executable)} {desktop_exec_value(my_exe)}"
                    with open(dest, "w") as f:
                        f.write(
                            "[Desktop Entry]\n"
                            "Type=Application\n"
                            "Name=GeodeSync\n"
                            "Comment=Geometry Dash Companion\n"
                            f"Exec={exec_line}\n"
                            f"Icon={os.path.join(os.path.dirname(my_exe), 'icon.png')}\n"
                            "Terminal=false\n"
                            "Categories=Game;Utility;\n"
                        )
                    os.chmod(dest, 0o755)
                    self.play_ding()
                    self.log("Created desktop launcher on ~/Desktop.", "SUCCESS")
                    messagebox.showinfo("Shortcut Created", "Created GeodeSync launcher on your Desktop!")
                    return
            messagebox.showinfo("Desktop Shortcut", "Shortcut created successfully!")
        except Exception as e:
            self.log(f"Failed to create shortcut: {e}", "WARN")
            messagebox.showerror("Error", f"Could not create desktop shortcut:\n{e}")

    def toggle_rpc(self):
        self.discord_rpc_enabled = not getattr(self, "discord_rpc_enabled", True)
        if self.discord_rpc_enabled:
            self.rpc_btn.config(text="🎮 Discord RPC: ON", fg=UI["lilac"])
            self.discord_rpc.set_enabled(True)
            self.log("Discord Rich Presence enabled. Discord chooses which activity to display; Medal or other apps may take priority.", "INFO")
            self.play_ding()
        else:
            self.rpc_btn.config(text="🎮 Discord RPC: OFF", fg=UI["muted"])
            self.discord_rpc.set_enabled(False)
            self.log("Discord Rich Presence disabled.", "INFO")
        self._save_settings()

    def share_geodesync(self):
        dialog = tk.Toplevel(self)
        dialog.title("📢 Share GeodeSync")
        dialog.geometry("520x460")
        dialog.configure(bg=UI["background"])
        dialog.transient(self)
        dialog.grab_set()

        head = tk.Frame(dialog, bg=UI["header"], padx=16, pady=12)
        head.pack(fill="x")
        tk.Label(
            head,
            text="📢 Help Fellow GD Players Protect Their Mods",
            font=("Segoe UI", 12, "bold"),
            bg=UI["header"],
            fg=UI["lime"],
        ).pack(anchor="w")
        tk.Label(
            head,
            text="Whenever GD updates, mods break. Share GeodeSync so your friends don't lose their saves or mods!",
            font=("Segoe UI", 9),
            bg=UI["header"],
            fg=UI["muted"],
            wraplength=480,
            justify="left",
        ).pack(anchor="w", pady=(3, 0))

        content = tk.Frame(dialog, bg=UI["background"], padx=16, pady=12)
        content.pack(fill="both", expand=True)

        templates = [
            (
                "💬 Discord Message (for GD & Modding Servers)",
                f"Hey guys! If your Geode mods broke on the new GD update, use GeodeSync to lock your game version or switch back safely without losing your saves or mods: https://github.com/{GITHUB_REPO}"
            ),
            (
                "🌐 Reddit / Socials Post",
                f"Geometry Dash version switcher & Geode mod protector (Windows, Mac, Linux) - 1-click downgrade, Steam update lock, save backups: https://github.com/{GITHUB_REPO}"
            ),
            (
                "🔗 Direct Download Link",
                f"https://github.com/{GITHUB_REPO}/releases/latest"
            )
        ]

        for title, text in templates:
            card = tk.Frame(content, bg=UI["panel"], padx=10, pady=8, highlightbackground=UI["border"], highlightthickness=1)
            card.pack(fill="x", pady=5)
            tk.Label(card, text=title, font=("Segoe UI", 9, "bold"), bg=UI["panel"], fg=UI["text"]).pack(anchor="w")
            txt_box = tk.Text(card, height=3, bg=UI["inset"], fg=UI["text"], insertbackground=UI["text"], relief="flat", wrap="word", font=("Segoe UI", 8))
            txt_box.pack(fill="x", pady=4)
            txt_box.insert("1.0", text)
            txt_box.config(state="disabled")

            def make_copy(t=text):
                self.clipboard_clear()
                self.clipboard_append(t)
                self.play_ding()
                messagebox.showinfo("Copied!", "Copied text to clipboard! Paste it into Discord or social media.")

            copy_btn = ModernButton(card, text="📋 Copy to Clipboard", bg=UI["panel_alt"], hover_bg=UI["border"], command=make_copy)
            copy_btn.pack(anchor="e")

        close_btn = ModernButton(content, text="Close", bg=UI["panel_alt"], hover_bg=UI["border"], command=dialog.destroy)
        close_btn.pack(pady=(8, 0))

    # ==========================================
    # v1.1.3 PRO FEATURE: FPS UNLOCKER & REFRESH RATE
    # ==========================================
    def open_fps_unlocker(self):
        save_dir = self.mgr.get_save_data_dir()
        if not save_dir:
            messagebox.showerror("Error", "Could not locate Geometry Dash save folder.")
            return

        gm_path = os.path.join(save_dir, "CCGameManager.dat")
        if not os.path.exists(gm_path):
            messagebox.showerror("Error", "CCGameManager.dat not found. Launch Geometry Dash at least once.")
            return

        current_fps = "240"
        try:
            with open(gm_path, "rb") as f:
                raw = f.read()
            decomp = decode_geometry_dash_save(raw).decode("utf-8", errors="ignore")
            m = re.search(r"<k>customFPSTarget</k><[ri]>([0-9.]+)</[ri]>", decomp)
            if m:
                current_fps = str(int(float(m.group(1))))
        except Exception as e:
            self.log(f"FPS read error: {e}", "WARN")

        dialog = tk.Toplevel(self)
        dialog.title("Geometry Dash FPS Unlocker & Target Rate")
        dialog.geometry("500x380")
        dialog.configure(bg=UI["header"])
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="🎯 Geometry Dash FPS Unlocker", font=("Segoe UI", 13, "bold"), fg=UI["text"], bg=UI["header"]).pack(anchor="w", padx=20, pady=(16, 4))
        tk.Label(dialog, text=f"Current Game Setting: {current_fps} FPS", font=("Segoe UI", 10, "bold"), fg=UI["lilac"], bg=UI["header"]).pack(anchor="w", padx=20, pady=(0, 12))

        card = tk.Frame(dialog, bg=UI["panel"], padx=16, pady=12, highlightbackground=UI["border"], highlightthickness=1)
        card.pack(fill="x", padx=20, pady=(0, 12))

        tk.Label(card, text="Select Target Framerate Preset:", font=("Segoe UI", 9, "bold"), fg=UI["text"], bg=UI["panel"]).pack(anchor="w", pady=(0, 8))

        selected_fps = tk.StringVar(value=current_fps if current_fps in ["60", "144", "240", "360", "480"] else "360")

        presets = [
            ("60 FPS (Vanilla standard)", "60"),
            ("144 FPS (Standard gaming monitor)", "144"),
            ("240 FPS (Esports / high refresh)", "240"),
            ("360 FPS (Competitive Demon Slayer • Recommended)", "360"),
            ("480 FPS (Ultra-smooth bypass)", "480")
        ]

        for label, val in presets:
            rb = tk.Radiobutton(
                card,
                text=label,
                variable=selected_fps,
                value=val,
                font=("Segoe UI", 9),
                fg=UI["text"],
                bg=UI["panel"],
                selectcolor=UI["inset"],
                activebackground=UI["panel"],
                activeforeground=UI["lilac"]
            )
            rb.pack(anchor="w", pady=2)

        custom_box = tk.Frame(card, bg=UI["panel"])
        custom_box.pack(fill="x", pady=(8, 0))
        tk.Label(custom_box, text="Or Custom Target FPS:", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(side="left")
        custom_entry = tk.Entry(custom_box, font=("Segoe UI", 9), bg=UI["inset"], fg=UI["text"], insertbackground=UI["text"], width=8)
        custom_entry.pack(side="left", padx=8)

        def apply_fps():
            val = custom_entry.get().strip() or selected_fps.get()
            if not val.isdigit() or int(val) < 30 or int(val) > 2000:
                messagebox.showerror("Invalid FPS", "Please enter a valid FPS number between 30 and 2000.")
                return

            target = int(val)
            try:
                with open(gm_path, "rb") as f:
                    raw = f.read()
                shutil.copy2(gm_path, gm_path + ".fps_bak")
                decomp = decode_geometry_dash_save(raw).decode("utf-8", errors="ignore")

                if "<k>customFPSTarget</k>" in decomp:
                    decomp = re.sub(r"<k>customFPSTarget</k><[ri]>[0-9.]+</[ri]>", f"<k>customFPSTarget</k><r>{target}</r>", decomp)
                else:
                    decomp = decomp.replace("<dict>", f"<dict><k>customFPSTarget</k><r>{target}</r>", 1)

                re_raw = encode_geometry_dash_save(decomp.encode("utf-8"))

                with open(gm_path, "wb") as f:
                    f.write(re_raw)

                self.play_ding()
                self.log(f"Successfully set Geometry Dash target FPS to {target} FPS!", "SUCCESS")
                dialog.destroy()
                messagebox.showinfo("FPS Target Updated!", f"🎉 Target Framerate set to {target} FPS!\n\nLaunch Geometry Dash to enjoy buttery smooth gameplay.")
            except Exception as err:
                self.log(f"Failed to set FPS: {err}", "ERROR")
                messagebox.showerror("Error", f"Failed to modify save file:\n{err}")

        btn_box = tk.Frame(dialog, bg=UI["header"])
        btn_box.pack(fill="x", side="bottom", padx=20, pady=16)

        cancel_btn = tk.Button(btn_box, text="Cancel", command=dialog.destroy, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["muted"], relief="flat", padx=10, pady=4, cursor="hand2")
        cancel_btn.pack(side="left")

        apply_btn = tk.Button(btn_box, text="⚡ Apply Target FPS", command=apply_fps, font=("Segoe UI", 9, "bold"), bg=UI["lime"], fg=UI["text"], activebackground=UI["lime_hover"], activeforeground=UI["text"], relief="flat", padx=16, pady=4, cursor="hand2")
        apply_btn.pack(side="right")

    # ==========================================
    # v1.1.3 PRO FEATURE: NONG SONG MANAGER
    # ==========================================
    def open_nong_manager(self):
        save_dir = self.mgr.get_save_data_dir()
        if not save_dir:
            messagebox.showerror("Error", "Could not locate Geometry Dash save folder.")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Geometry Dash NONG Song Manager")
        dialog.geometry("540x480")
        dialog.configure(bg=UI["header"])
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="🎵 NONG Song Manager (Custom Level Audio)", font=("Segoe UI", 13, "bold"), fg=UI["text"], bg=UI["header"]).pack(anchor="w", padx=20, pady=(16, 4))
        tk.Label(dialog, text="Easily replace any level's official audio with a custom Not-On-Newgrounds song:", font=("Segoe UI", 9), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", padx=20, pady=(0, 12))

        card = tk.Frame(dialog, bg=UI["panel"], padx=16, pady=12, highlightbackground=UI["border"], highlightthickness=1)
        card.pack(fill="x", padx=20, pady=(0, 12))

        tk.Label(card, text="Target Song ID (from in-game custom level):", font=("Segoe UI", 8, "bold"), fg=UI["text"], bg=UI["panel"]).pack(anchor="w")
        song_id_entry = tk.Entry(card, font=("Segoe UI", 10), bg=UI["inset"], fg=UI["text"], insertbackground=UI["text"])
        song_id_entry.pack(fill="x", pady=(2, 8))

        tk.Label(card, text="Custom Audio Source (Local MP3 or Direct URL):", font=("Segoe UI", 8, "bold"), fg=UI["text"], bg=UI["panel"]).pack(anchor="w")
        source_frame = tk.Frame(card, bg=UI["panel"])
        source_frame.pack(fill="x", pady=(2, 8))

        source_entry = tk.Entry(source_frame, font=("Segoe UI", 9), bg=UI["inset"], fg=UI["text"], insertbackground=UI["text"])
        source_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def browse_audio():
            file_path = filedialog.askopenfilename(
                title="Select Custom MP3 / OGG Song",
                filetypes=[("Audio Files", "*.mp3 *.ogg"), ("All Files", "*.*")]
            )
            if file_path:
                source_entry.delete(0, "end")
                source_entry.insert(0, file_path)

        tk.Button(source_frame, text="Browse...", command=browse_audio, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["lilac"], relief="flat", padx=10, pady=3, cursor="hand2").pack(side="right")

        def install_nong():
            sid = song_id_entry.get().strip()
            src = source_entry.get().strip()

            if not sid.isdigit():
                messagebox.showerror("Error", "Please enter a valid numeric Song ID (e.g. 10001563).")
                return

            if not src:
                messagebox.showerror("Error", "Please select a local audio file or enter a direct MP3 URL.")
                return

            target_path = os.path.join(save_dir, f"{sid}.mp3")
            bak_path = target_path + ".original_bak"

            try:
                if os.path.exists(target_path) and not os.path.exists(bak_path):
                    shutil.copy2(target_path, bak_path)

                if src.startswith("http://") or src.startswith("https://"):
                    urllib.request.urlretrieve(src, target_path)
                else:
                    if not os.path.exists(src):
                        messagebox.showerror("File Not Found", f"Audio file not found:\n{src}")
                        return
                    safe_copy_item(src, target_path)

                self.play_ding()
                self.log(f"Installed NONG song for Song ID: {sid}", "SUCCESS")
                messagebox.showinfo("NONG Installed!", f"🎉 Successfully installed custom song for Song ID: {sid}!\n\nOpen Geometry Dash and enjoy your level.")
                refresh_list()
            except Exception as err:
                self.log(f"NONG install error: {err}", "ERROR")
                messagebox.showerror("Error", f"Failed to install song:\n{err}")

        tk.Button(card, text="⚡ Install NONG Song", command=install_nong, font=("Segoe UI", 9, "bold"), bg=UI["lilac"], fg=UI["text"], activebackground=UI["lilac_dark"], relief="flat", padx=14, pady=5, cursor="hand2").pack(anchor="w", pady=(4, 0))

        list_frame = tk.Frame(dialog, bg=UI["panel"], padx=14, pady=10, highlightbackground=UI["border"], highlightthickness=1)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        tk.Label(list_frame, text="Replaced NONG Songs in Save Directory:", font=("Segoe UI", 8, "bold"), fg=UI["quiet"], bg=UI["panel"]).pack(anchor="w")

        nong_box = tk.Listbox(list_frame, bg=UI["inset"], fg=UI["text"], font=("Segoe UI", 8), height=4, selectbackground=UI["lilac"])
        nong_box.pack(fill="both", expand=True, pady=4)

        def refresh_list():
            nong_box.delete(0, "end")
            found = 0
            for item in os.listdir(save_dir):
                if item.endswith(".mp3.original_bak"):
                    base_id = item.replace(".mp3.original_bak", "")
                    nong_box.insert("end", f"Song ID {base_id} (Replaced)")
                    found += 1
            if found == 0:
                nong_box.insert("end", "No replaced NONG songs detected.")

        refresh_list()

        def restore_selected():
            sel = nong_box.curselection()
            if not sel:
                return
            line = nong_box.get(sel[0])
            m = re.search(r"Song ID (\d+)", line)
            if not m:
                return
            sid = m.group(1)
            target = os.path.join(save_dir, f"{sid}.mp3")
            bak = target + ".original_bak"
            if os.path.exists(bak):
                shutil.move(bak, target)
                self.log(f"Restored original song for Song ID: {sid}", "SUCCESS")
                messagebox.showinfo("Restored", f"Restored original song for ID {sid}!")
                refresh_list()

        btn_bar = tk.Frame(list_frame, bg=UI["panel"])
        btn_bar.pack(fill="x")
        tk.Button(btn_bar, text="♻️ Revert Selected to Original", command=restore_selected, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["amber"], relief="flat", padx=8, pady=3, cursor="hand2").pack(side="left")

    # ==========================================
    # v1.1.3 PRO FEATURE: ESSENTIAL MOD PACK INSTALLER
    # ==========================================
    def install_essential_mods(self):
        mods_dir = self.get_mods_dir()
        if not mods_dir:
            messagebox.showerror("Error", "Geometry Dash mods directory not found.")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Essential Geode Mod Pack")
        dialog.geometry("540x440")
        dialog.configure(bg=UI["header"])
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="📦 1-Click Essential Geode Mod Pack", font=("Segoe UI", 12, "bold"), fg=UI["text"], bg=UI["header"]).pack(anchor="w", padx=20, pady=(16, 4))
        tk.Label(dialog, text="Select community-recommended mods to download and install directly into Geode:", font=("Segoe UI", 9), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", padx=20, pady=(0, 10))

        pack_mods = [
            ("fleym.nongd", "Jukebox (In-game NONG Custom Song Downloader)"),
            ("syzzi.click_between_frames", "Click Between Frames (CBF • Physics Precision)"),
            ("dankmeme.globed2", "Globed (Real-time Online Multiplayer)"),
            ("beat.click-sound", "Click Sound (Custom clicks & mechanical audio)"),
            ("alphalaneous.betteredit", "BetterEdit (Creator Level Editor overhaul)"),
            ("camila314.nodepreview", "Node Preview (Hitboxes & Object Inspector)"),
            ("prevter.geode-discord-rich-presence", "Discord Rich Presence (Show live GD status)"),
        ]

        var_dict = {}
        card = tk.Frame(dialog, bg=UI["panel"], padx=14, pady=10, highlightbackground=UI["border"], highlightthickness=1)
        card.pack(fill="x", padx=20, pady=(0, 12))

        for mod_id, title in pack_mods:
            is_installed = os.path.exists(os.path.join(mods_dir, f"{mod_id}.geode"))
            v = tk.BooleanVar(value=not is_installed)
            var_dict[mod_id] = v
            label_text = f"{title}" + (" [Installed]" if is_installed else "")
            col = UI["muted"] if is_installed else UI["text"]
            cb = tk.Checkbutton(card, text=label_text, variable=v, font=("Segoe UI", 9), fg=col, bg=UI["panel"], selectcolor=UI["inset"], activebackground=UI["panel"], activeforeground=UI["lilac"])
            cb.pack(anchor="w", pady=3)

        def do_install():
            to_download = [mid for mid, v in var_dict.items() if v.get()]
            if not to_download:
                messagebox.showinfo("Nothing Selected", "No new mods selected for installation.")
                return

            dialog.destroy()
            threading.Thread(target=self._run_modpack_install, args=(to_download,), daemon=True).start()

        btn_box = tk.Frame(dialog, bg=UI["header"])
        btn_box.pack(fill="x", side="bottom", padx=20, pady=16)

        cancel_btn = tk.Button(btn_box, text="Cancel", command=dialog.destroy, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["muted"], relief="flat", padx=10, pady=4, cursor="hand2")
        cancel_btn.pack(side="left")

        apply_btn = tk.Button(btn_box, text="⚡ Download & Install Selected", command=do_install, font=("Segoe UI", 9, "bold"), bg=UI["lime"], fg=UI["background"], activebackground=UI["lime_hover"], activeforeground=UI["background"], relief="flat", padx=14, pady=4, cursor="hand2")
        apply_btn.pack(side="right")

    def _run_modpack_install(self, mod_ids):
        mods_dir = self.get_mods_dir()
        if not mods_dir:
            return
        self.progress_frame.pack(fill="x", pady=(0, 8), before=self.primary_btn)
        self.primary_btn.set_enabled(False)
        installed_count = 0

        for i, mid in enumerate(mod_ids):
            self.progress_lbl.config(text=f"Fetching mod metadata: {mid}...")
            self.progress_bar["value"] = int((i / len(mod_ids)) * 100)
            try:
                api_url = f"https://api.geode-sdk.org/v1/mods/{mid}"
                req = urllib.request.Request(api_url, headers={"User-Agent": "GeodeSync-Client"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    data = json.loads(r.read().decode())
                versions = data.get("payload", {}).get("versions", [])
                if versions:
                    dl_url = versions[0].get("download_link")
                    if dl_url:
                        self.progress_lbl.config(text=f"Downloading {mid}...")
                        dest = os.path.join(mods_dir, f"{mid}.geode")
                        dl_req = urllib.request.Request(dl_url, headers={"User-Agent": "GeodeSync-Client"})
                        with urllib.request.urlopen(dl_req, timeout=20) as dl_resp, open(dest, "wb") as f_out:
                            shutil.copyfileobj(dl_resp, f_out)
                        if self.mgr.gd_path:
                            gd_mods = os.path.join(self.mgr.gd_path, "geode", "mods")
                            if os.path.exists(gd_mods) and os.path.abspath(gd_mods) != os.path.abspath(mods_dir):
                                try:
                                    safe_copy_item(dest, os.path.join(gd_mods, f"{mid}.geode"))
                                except Exception:
                                    pass
                        installed_count += 1
                        self.log(f"Installed mod: {mid}", "SUCCESS")
            except Exception as e:
                self.log(f"Failed to install {mid}: {e}", "WARN")

        self.progress_bar["value"] = 100
        time.sleep(0.5)
        self.progress_frame.pack_forget()
        self.primary_btn.set_enabled(True)
        self.play_ding()
        self.refresh_status()
        messagebox.showinfo("Mod Pack Installed!", f"🎉 Successfully installed {installed_count} essential Geode mods!\n\nLaunch Geometry Dash to activate them.")

    def toggle_more_tools(self):
        if self.more_frame.winfo_viewable():
            self.more_frame.pack_forget()
            self.more_toggle_btn.config(text="More tools  +", fg=UI["muted"])
        else:
            self.more_frame.pack(fill="x", pady=(8, 0))
            self.more_toggle_btn.config(text="More tools  −", fg=UI["lime"])

    def show_help_dialog(self):
        msg = (
            "HOW GEODESYNC WORKS (FAQ):\n\n"
            "1. Why do I need to downgrade?\n"
            "Whenever Geometry Dash updates (like to 2.209), Geode mods crash until developers update them. Downgrading to 2.2081 lets you keep playing with all your mods immediately.\n\n"
            "2. How does the 1-Click Fix work?\n"
            "You literally just click the button! GeodeSync signals Steam to download clean 2.2081 files in the background, swaps the files into your game, and locks Steam so it won't auto-update.\n\n"
            "3. What is Save Doctor & Auto-Backup?\n"
            "Tests and repairs corrupted saves using native decryptors. Auto-Backup silently creates save snapshots whenever GD closes so you never lose progress.\n\n"
            "4. What is FPS Unlocker?\n"
            "Modifies the internal customFPSTarget in CCGameManager.dat so you can play on 144Hz, 240Hz, 360Hz, or 480Hz without paid trainers.\n\n"
            "5. What is NONG Song Manager?\n"
            "Replaces any level's official audio with custom Not-On-Newgrounds songs in 1 click, with automated original backup and 1-click restore.\n\n"
            "6. What is Essential Mod Pack?\n"
            "Downloads community must-haves (CBF, Globed multiplayer, Click Sound, NONGD, BetterEdit) straight from the official Geode Index API."
        )
        messagebox.showinfo("GeodeSync Guide & FAQ", msg)

    def open_mod_updater_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("🔄 GeodeSync • 1-Click Mod Updater Hub")
        dialog.geometry("640x520")
        dialog.minsize(560, 420)
        dialog.configure(bg=UI["background"])
        dialog.transient(self)
        dialog.grab_set()

        head = tk.Frame(dialog, bg=UI["header"], padx=20, pady=16)
        head.pack(fill="x")
        tk.Label(head, text="🔄 1-Click Mod Updater Hub", font=("Segoe UI", 14, "bold"), fg=UI["lime"], bg=UI["header"]).pack(anchor="w")
        tk.Label(head, text="Scans your installed mods against Geode SDK Index & auto-updates safely.", font=("Segoe UI", 9), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", pady=(2, 0))

        content_frame = tk.Frame(dialog, bg=UI["background"], padx=20, pady=16)
        content_frame.pack(fill="both", expand=True)

        status_lbl = tk.Label(content_frame, text="🔍 Scanning installed Geode mods for updates...", font=("Segoe UI", 10, "bold"), fg=UI["lime"], bg=UI["background"])
        status_lbl.pack(pady=12)

        pbar = ttk.Progressbar(content_frame, style="Cyber.Horizontal.TProgressbar", orient="horizontal", mode="indeterminate", length=400)
        pbar.pack(pady=(0, 16))
        pbar.start(10)

        list_container = tk.Frame(content_frame, bg=UI["panel"], highlightbackground=UI["border"], highlightthickness=1)

        def run_scan():
            outdated = self.mgr.check_outdated_mods()
            self.after(0, lambda: render_results(outdated))

        def render_results(outdated):
            pbar.stop()
            pbar.pack_forget()

            if not outdated:
                status_lbl.config(text="🎉 All Installed Mods are Up-to-Date!", fg=UI["lime"])
                tk.Label(
                    content_frame,
                    text="Every mod in your Geode installation matches the latest compatible release on the Geode SDK Index.\n(Unstable versions like ImagePlus v1.1.1 are kept guarded).",
                    font=("Segoe UI", 9), fg=UI["muted"], bg=UI["background"], justify="center"
                ).pack(pady=8)

                ModernButton(content_frame, text="Close", command=dialog.destroy, bg=UI["panel_alt"], hover_bg=UI["border"], fg=UI["text"], height=38, width=160).pack(pady=16)
                return

            status_lbl.config(text=f"⚡ Found {len(outdated)} Mod Update{'s' if len(outdated) > 1 else ''} Available!", fg=UI["amber"])

            act_bar = tk.Frame(content_frame, bg=UI["background"])
            act_bar.pack(fill="x", pady=(0, 10))

            btn_update_all = tk.Button(
                act_bar,
                text=f"⚡ Update All ({len(outdated)} Mods)",
                font=("Segoe UI", 9, "bold"),
                bg=UI["lime"], fg=UI["background"],
                activebackground=UI["lime_hover"],
                relief="flat", padx=14, pady=7, cursor="hand2"
            )
            btn_update_all.pack(side="left")

            prog_lbl = tk.Label(act_bar, text="", font=("Segoe UI", 9), fg=UI["muted"], bg=UI["background"])
            prog_lbl.pack(side="left", padx=12)

            list_container.pack(fill="both", expand=True)

            canvas = tk.Canvas(list_container, bg=UI["panel"], highlightthickness=0)
            scrollbar = tk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
            scrollable = tk.Frame(canvas, bg=UI["panel"])

            scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=scrollable, anchor="nw", width=580)
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True, padx=4, pady=4)
            scrollbar.pack(side="right", fill="y")

            def update_single(item, btn_widget, row_lbl):
                btn_widget.config(text="Updating...", state="disabled", bg=UI["panel_alt"])
                self.log(f"Updating mod {item['name']} to v{item['latest_version']}...", "INFO")
                
                def _do():
                    ok, msg = self.mgr.update_single_mod(item)
                    def _done():
                        if ok:
                            btn_widget.config(text="✅ Updated", bg=UI["panel_alt"], fg=UI["lime"])
                            row_lbl.config(text=f"v{item['latest_version']} (Latest)", fg=UI["lime"])
                            self.play_ding()
                            self.log(msg, "SUCCESS")
                        else:
                            btn_widget.config(text="Failed", bg=UI["panel_alt"], fg="#ff6b6b", state="normal")
                            self.log(f"Failed to update {item['name']}: {msg}", "ERROR")
                    self.after(0, _done)
                threading.Thread(target=_do, daemon=True).start()

            for item in outdated:
                row = tk.Frame(scrollable, bg=UI["panel_alt"], padx=10, pady=8, highlightbackground=UI["border"], highlightthickness=1)
                row.pack(fill="x", pady=3)

                info_box = tk.Frame(row, bg=UI["panel_alt"])
                info_box.pack(side="left", fill="x", expand=True)

                tk.Label(info_box, text=item["name"], font=("Segoe UI", 9, "bold"), fg=UI["text"], bg=UI["panel_alt"]).pack(anchor="w")
                v_lbl = tk.Label(info_box, text=f"v{item['current_version']}  ➔  v{item['latest_version']}", font=("Segoe UI", 8), fg=UI["amber"], bg=UI["panel_alt"])
                v_lbl.pack(anchor="w")

                btn_u = tk.Button(
                    row, text="Update", font=("Segoe UI", 8, "bold"),
                    bg=UI["panel"], fg=UI["lime"], activebackground=UI["border"],
                    relief="flat", padx=10, pady=4, cursor="hand2"
                )
                btn_u.pack(side="right")
                btn_u.config(command=lambda it=item, b=btn_u, vl=v_lbl: update_single(it, b, vl))

            def do_update_all():
                btn_update_all.config(state="disabled", text="Updating...")
                def _worker():
                    successes = 0
                    for i, it in enumerate(outdated):
                        self.after(0, lambda n=it['name'], cur=i+1, tot=len(outdated): prog_lbl.config(text=f"Updating {cur}/{tot}: {n}..."))
                        ok, _ = self.mgr.update_single_mod(it)
                        if ok:
                            successes += 1
                    def _fin():
                        prog_lbl.config(text=f"✅ Finished! Updated {successes}/{len(outdated)} mods.", fg=UI["lime"])
                        btn_update_all.config(text="🎉 All Done!", bg=UI["panel_alt"], fg=UI["lime"])
                        self.play_ding()
                        self.refresh_status()
                    self.after(0, _fin)
                threading.Thread(target=_worker, daemon=True).start()

            btn_update_all.config(command=do_update_all)

        threading.Thread(target=run_scan, daemon=True).start()

    def open_demon_tracker(self):
        dialog = tk.Toplevel(self)
        dialog.title("📈 Demon & Grind Progress Tracker")
        dialog.geometry("660x540")
        dialog.minsize(580, 440)
        dialog.configure(bg=UI["background"])
        dialog.transient(self)
        dialog.grab_set()

        head = tk.Frame(dialog, bg=UI["header"], padx=20, pady=14)
        head.pack(fill="x")
        head_top = tk.Frame(head, bg=UI["header"])
        head_top.pack(fill="x")
        tk.Label(head_top, text="📈 Demon & Grind Progress Tracker", font=("Segoe UI", 14, "bold"), fg=UI["lime"], bg=UI["header"]).pack(side="left")
        top_list_btn = tk.Button(head_top, text="🏆 Top 150 Demonlist", command=self.open_demonlist_browser, font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=UI["lilac"], relief="flat", padx=10, pady=3, cursor="hand2")
        top_list_btn.pack(side="right")
        tk.Label(head, text="Live progress extracted directly from your decrypted Geometry Dash save data.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", pady=(2, 0))

        content = tk.Frame(dialog, bg=UI["background"], padx=16, pady=12)
        content.pack(fill="both", expand=True)

        data = self.mgr.get_demon_and_grind_data()
        if not data:
            tk.Label(content, text="⚠️ Could not decrypt CCGameManager.dat.\nMake sure Geometry Dash has been run at least once.", font=("Segoe UI", 10), fg=UI["amber"], bg=UI["background"]).pack(pady=40)
            return

        stats_bar = tk.Frame(content, bg=UI["panel"], padx=12, pady=8, highlightbackground=UI["border"], highlightthickness=1)
        stats_bar.pack(fill="x", pady=(0, 10))

        tk.Label(stats_bar, text=f"🎮 {data['player_name']}", font=("Segoe UI", 11, "bold"), fg=UI["text"], bg=UI["panel"]).pack(side="left", padx=(0, 16))

        for icon, val, lbl, col in [
            ("⭐", data["stars"], "Stars", UI["amber"]),
            ("👿", data["demons"], "Demons", UI["lilac"]),
            ("💎", data["diamonds"], "Diamonds", "#00e5ff"),
            ("🪙", data["coins"], "Coins", UI["amber"]),
            ("🔮", data["orbs"], "Orbs", "#e056fd"),
        ]:
            c_frame = tk.Frame(stats_bar, bg=UI["panel_alt"], padx=6, pady=2, highlightbackground=UI["border"], highlightthickness=1)
            c_frame.pack(side="left", padx=3)
            tk.Label(c_frame, text=icon, font=("Segoe UI", 8), fg=col, bg=UI["panel_alt"]).pack(side="left", padx=(0, 2))
            tk.Label(c_frame, text=f"{val:,} {lbl}", font=("Segoe UI", 8, "bold"), fg=UI["text"], bg=UI["panel_alt"]).pack(side="left")

        def copy_discord_format():
            grinds_str = "\n".join([f"• **{g['name']}** by {g['author']} — **{g['percent']}%** (Practice: {g['practice']}%)" for g in data["grinds"][:8]])
            discord_text = (
                f"🏆 **{data['player_name']}'s Geometry Dash Progression**\n"
                f"⭐ Stars: {data['stars']:,} | 👿 Demons: {data['demons']:,} | 💎 Diamonds: {data['diamonds']:,}\n\n"
                f"🔥 **Current Hard Grinds:**\n{grinds_str or '• None currently recorded.'}\n\n"
                f"🛡️ *Tracked live via GeodeSync v{APP_VERSION}*"
            )
            self.clipboard_clear()
            self.clipboard_append(discord_text)
            self.play_ding()
            btn_copy.config(text="✅ Copied Discord Format to Clipboard!", fg=UI["lime"])
            self.log("Copied Demon & Grind progression card to clipboard.", "SUCCESS")

        btn_copy = tk.Button(
            content, text="📋 Copy Discord Progression Card", command=copy_discord_format,
            font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=UI["lilac"],
            activebackground=UI["border"], relief="flat", padx=12, pady=6, cursor="hand2"
        )
        btn_copy.pack(fill="x", pady=(0, 10))

        notebook = ttk.Notebook(content)
        notebook.pack(fill="both", expand=True)

        tab_grinds = tk.Frame(notebook, bg=UI["panel"], padx=8, pady=8)
        notebook.add(tab_grinds, text=f"🔥 Active Grinds ({len(data['grinds'])})")

        canvas_g = tk.Canvas(tab_grinds, bg=UI["panel"], highlightthickness=0)
        scroll_g = tk.Scrollbar(tab_grinds, orient="vertical", command=canvas_g.yview)
        scroll_content_g = tk.Frame(canvas_g, bg=UI["panel"])

        scroll_content_g.bind("<Configure>", lambda e: canvas_g.configure(scrollregion=canvas_g.bbox("all")))
        canvas_g.create_window((0, 0), window=scroll_content_g, anchor="nw", width=600)
        canvas_g.configure(yscrollcommand=scroll_g.set)

        canvas_g.pack(side="left", fill="both", expand=True)
        scroll_g.pack(side="right", fill="y")

        if not data["grinds"]:
            tk.Label(scroll_content_g, text="No active grinds recorded (15%-99%).", font=("Segoe UI", 9), fg=UI["muted"], bg=UI["panel"]).pack(pady=20)
        else:
            for g in data["grinds"]:
                row = tk.Frame(scroll_content_g, bg=UI["panel_alt"], padx=8, pady=6, highlightbackground=UI["border"], highlightthickness=1)
                row.pack(fill="x", pady=2)

                left = tk.Frame(row, bg=UI["panel_alt"])
                left.pack(side="left", fill="x", expand=True)

                tk.Label(left, text=g["name"], font=("Segoe UI", 9, "bold"), fg=UI["text"], bg=UI["panel_alt"]).pack(anchor="w")
                tk.Label(left, text=f"by {g['author']} • Practice: {g['practice']}% • Attempts: {g['attempts']:,}", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel_alt"]).pack(anchor="w")

                pct_color = UI["lime"] if g["percent"] >= 80 else (UI["amber"] if g["percent"] >= 50 else UI["lilac"])
                tk.Label(row, text=f"{g['percent']}%", font=("Segoe UI", 12, "bold"), fg=pct_color, bg=UI["panel_alt"]).pack(side="right", padx=6)

        tab_demons = tk.Frame(notebook, bg=UI["panel"], padx=8, pady=8)
        notebook.add(tab_demons, text=f"👿 Beaten Demons ({len(data['completed_demons'])})")

        canvas_d = tk.Canvas(tab_demons, bg=UI["panel"], highlightthickness=0)
        scroll_d = tk.Scrollbar(tab_demons, orient="vertical", command=canvas_d.yview)
        scroll_content_d = tk.Frame(canvas_d, bg=UI["panel"])

        scroll_content_d.bind("<Configure>", lambda e: canvas_d.configure(scrollregion=canvas_d.bbox("all")))
        canvas_d.create_window((0, 0), window=scroll_content_d, anchor="nw", width=600)
        canvas_d.configure(yscrollcommand=scroll_d.set)

        canvas_d.pack(side="left", fill="both", expand=True)
        scroll_d.pack(side="right", fill="y")

        if not data["completed_demons"]:
            tk.Label(scroll_content_d, text=f"Total demons beaten: {data['demons']}. Detailed list empty in local cache.", font=("Segoe UI", 9), fg=UI["muted"], bg=UI["panel"]).pack(pady=20)
        else:
            for d in data["completed_demons"]:
                row = tk.Frame(scroll_content_d, bg=UI["panel_alt"], padx=8, pady=6, highlightbackground=UI["border"], highlightthickness=1)
                row.pack(fill="x", pady=2)
                tk.Label(row, text=f"👿 {d['name']}", font=("Segoe UI", 9, "bold"), fg=UI["text"], bg=UI["panel_alt"]).pack(side="left")
                tk.Label(row, text=f"by {d['author']} • 100% Complete", font=("Segoe UI", 8), fg=UI["lime"], bg=UI["panel_alt"]).pack(side="right")

    def open_texture_pack_hub(self):
        dialog = tk.Toplevel(self)
        dialog.title("🎨 Texture Pack Hub")
        dialog.geometry("580x460")
        dialog.minsize(520, 380)
        dialog.configure(bg=UI["background"])
        dialog.transient(self)
        dialog.grab_set()

        head = tk.Frame(dialog, bg=UI["header"], padx=20, pady=14)
        head.pack(fill="x")
        tk.Label(head, text="🎨 Texture Pack Hub", font=("Segoe UI", 14, "bold"), fg=UI["lime"], bg=UI["header"]).pack(anchor="w")
        tk.Label(head, text="Safely install custom texture packs with automated vanilla backup & 1-click restore.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", pady=(2, 0))

        content = tk.Frame(dialog, bg=UI["background"], padx=20, pady=16)
        content.pack(fill="both", expand=True)

        status = self.mgr.get_texture_pack_status()

        card = tk.Frame(content, bg=UI["panel"], padx=14, pady=12, highlightbackground=UI["border"], highlightthickness=1)
        card.pack(fill="x", pady=(0, 14))

        tk.Label(card, text="CURRENT TEXTURE STATE", font=("Segoe UI", 8, "bold"), fg=UI["quiet"], bg=UI["panel"]).pack(anchor="w")
        pack_lbl = tk.Label(card, text=f"Active Pack: {status['active_pack']}", font=("Segoe UI", 11, "bold"), fg=UI["text"], bg=UI["panel"])
        pack_lbl.pack(anchor="w", pady=(4, 2))

        bak_text = f"🛡️ Vanilla Textures Protected ({status['vanilla_files']} assets safely archived)" if status["has_backup"] else "⚠️ No Vanilla Backup Yet (Will auto-generate on first install)"
        bak_color = UI["lime"] if status["has_backup"] else UI["amber"]
        bak_lbl = tk.Label(card, text=bak_text, font=("Segoe UI", 8), fg=bak_color, bg=UI["panel"])
        bak_lbl.pack(anchor="w")

        prog_lbl = tk.Label(content, text="", font=("Segoe UI", 9), fg=UI["lime"], bg=UI["background"])
        prog_lbl.pack(pady=(0, 8))

        def on_install_pack():
            path = filedialog.askopenfilename(
                title="Select Texture Pack (.zip)",
                filetypes=[("Texture Pack Archive", "*.zip"), ("All Files", "*.*")]
            )
            if not path:
                return

            prog_lbl.config(text="Protecting vanilla files & installing pack...", fg=UI["lime"])
            self.log(f"Installing texture pack from {path}...", "INFO")

            def _worker():
                ok, msg = self.mgr.install_texture_pack(path)
                def _done():
                    if ok:
                        self.play_ding()
                        self.log(msg, "SUCCESS")
                        prog_lbl.config(text="✅ " + msg, fg=UI["lime"])
                        st = self.mgr.get_texture_pack_status()
                        pack_lbl.config(text=f"Active Pack: {st['active_pack']}")
                        bak_lbl.config(text=f"🛡️ Vanilla Textures Protected ({st['vanilla_files']} assets)", fg=UI["lime"])
                        messagebox.showinfo("Texture Pack Applied", f"🎉 {msg}\n\nLaunch Geometry Dash to see your new textures!")
                    else:
                        self.log(f"Failed to apply texture pack: {msg}", "ERROR")
                        prog_lbl.config(text="❌ " + msg, fg="#ff6b6b")
                        messagebox.showerror("Error", f"Failed to install texture pack:\n{msg}")
                self.after(0, _done)
            threading.Thread(target=_worker, daemon=True).start()

        def on_restore_vanilla():
            st = self.mgr.get_texture_pack_status()
            if not st["has_backup"]:
                messagebox.showinfo("Vanilla Textures", "Your installation is already using vanilla textures (or no backup exists yet).")
                return

            res = messagebox.askyesno("Restore Vanilla Textures", "Are you sure you want to restore 100% original vanilla Geometry Dash textures?")
            if not res:
                return

            prog_lbl.config(text="Restoring original textures...", fg=UI["lime"])
            def _worker():
                ok, msg = self.mgr.restore_vanilla_textures()
                def _done():
                    if ok:
                        self.play_ding()
                        self.log(msg, "SUCCESS")
                        prog_lbl.config(text="✅ " + msg, fg=UI["lime"])
                        pack_lbl.config(text="Active Pack: Vanilla (Default)")
                        messagebox.showinfo("Textures Restored", f"🎉 {msg}")
                    else:
                        prog_lbl.config(text="❌ " + msg, fg="#ff6b6b")
                        messagebox.showerror("Error", msg)
                self.after(0, _done)
            threading.Thread(target=_worker, daemon=True).start()

        btn_install = tk.Button(
            content, text="📁 Select & Install Texture Pack (.zip)", command=on_install_pack,
            font=("Segoe UI", 9, "bold"), bg=UI["lime"], fg=UI["background"],
            activebackground=UI["lime_hover"], relief="flat", padx=14, pady=8, cursor="hand2"
        )
        btn_install.pack(fill="x", pady=4)

        btn_restore = tk.Button(
            content, text="🔄 Restore 100% Vanilla Textures", command=on_restore_vanilla,
            font=("Segoe UI", 9), bg=UI["panel_alt"], fg=UI["amber"],
            activebackground=UI["border"], relief="flat", padx=14, pady=8, cursor="hand2"
        )
        btn_restore.pack(fill="x", pady=4)

        tk.Label(
            content,
            text="Tip: GeodeSync safely keeps an untouched snapshot of your original Resources folder in Resources_Vanilla_Backup, so you can test any custom texture pack risk-free.",
            font=("Segoe UI", 8), fg=UI["muted"], bg=UI["background"], wraplength=520, justify="left"
        ).pack(anchor="w", pady=(16, 0))

    def open_keybind_doctor(self):
        dialog = tk.Toplevel(self)
        dialog.title("⌨️ Keybind Conflict Doctor")
        dialog.geometry("640x500")
        dialog.minsize(560, 400)
        dialog.configure(bg=UI["background"])
        dialog.transient(self)
        dialog.grab_set()

        head = tk.Frame(dialog, bg=UI["header"], padx=20, pady=14)
        head.pack(fill="x")
        tk.Label(head, text="⌨️ Keybind Conflict Doctor", font=("Segoe UI", 14, "bold"), fg=UI["lime"], bg=UI["header"]).pack(anchor="w")
        tk.Label(head, text="Scans all installed Geode mods to detect overlapping hotkeys before launch.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", pady=(2, 0))

        content = tk.Frame(dialog, bg=UI["background"], padx=16, pady=12)
        content.pack(fill="both", expand=True)

        res = self.mgr.get_keybind_map()
        conflicts = res.get("conflicts", {})
        all_keys = res.get("all_keys", {})

        status_card = tk.Frame(content, bg=UI["panel"], padx=12, pady=10, highlightbackground=UI["border"], highlightthickness=1)
        status_card.pack(fill="x", pady=(0, 10))

        if conflicts:
            tk.Label(status_card, text=f"⚠️ {len(conflicts)} Keybind Collision{'s' if len(conflicts)>1 else ''} Detected!", font=("Segoe UI", 11, "bold"), fg=UI["amber"], bg=UI["panel"]).pack(anchor="w")
            tk.Label(status_card, text="Multiple mods are assigned to the same key without unique modifiers. Pressing it in-game will trigger both actions simultaneously.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"], wraplength=580, justify="left").pack(anchor="w", pady=(2, 0))
        else:
            tk.Label(status_card, text="✅ All Hotkeys Clean & Conflict-Free!", font=("Segoe UI", 11, "bold"), fg=UI["lime"], bg=UI["panel"]).pack(anchor="w")
            tk.Label(status_card, text=f"Found {len(all_keys)} registered mod keybind{'s' if len(all_keys)!=1 else ''}. No overlapping keys detected.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(anchor="w", pady=(2, 0))

        list_container = tk.Frame(content, bg=UI["panel"], highlightbackground=UI["border"], highlightthickness=1)
        list_container.pack(fill="both", expand=True)

        canvas = tk.Canvas(list_container, bg=UI["panel"], highlightthickness=0)
        scrollbar = tk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=UI["panel"])

        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw", width=580)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        scrollbar.pack(side="right", fill="y")

        if conflicts:
            tk.Label(scrollable, text="🚨 CONFLICTING KEYS", font=("Segoe UI", 8, "bold"), fg=UI["amber"], bg=UI["panel"]).pack(anchor="w", padx=6, pady=(6, 2))
            for k, items in conflicts.items():
                row = tk.Frame(scrollable, bg=UI["panel_alt"], padx=10, pady=6, highlightbackground=UI["amber"], highlightthickness=1)
                row.pack(fill="x", pady=2, padx=4)

                tk.Label(row, text=f"[{k}]", font=("Segoe UI", 10, "bold"), fg=UI["amber"], bg=UI["panel_alt"]).pack(side="left", padx=(0, 10))
                desc = " & ".join([f"{item['mod']} ({item['action']})" for item in items])
                tk.Label(row, text=desc, font=("Segoe UI", 8), fg=UI["text"], bg=UI["panel_alt"], wraplength=460, justify="left").pack(side="left")

        tk.Label(scrollable, text="📋 ALL REGISTERED MOD KEYBINDS", font=("Segoe UI", 8, "bold"), fg=UI["quiet"], bg=UI["panel"]).pack(anchor="w", padx=6, pady=(10, 2))

        if not all_keys:
            tk.Label(scrollable, text="No custom keybinds detected in mod configurations.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(anchor="w", padx=6, pady=4)
        else:
            for k, items in sorted(all_keys.items()):
                row = tk.Frame(scrollable, bg=UI["panel_alt"], padx=10, pady=5, highlightbackground=UI["border"], highlightthickness=1)
                row.pack(fill="x", pady=2, padx=4)

                k_color = UI["amber"] if k in conflicts else UI["lime"]
                tk.Label(row, text=f"[{k}]", font=("Segoe UI", 9, "bold"), fg=k_color, bg=UI["panel_alt"], width=8, anchor="w").pack(side="left")
                desc = ", ".join([f"{item['mod']} ({item['action']})" for item in items])
                tk.Label(row, text=desc, font=("Segoe UI", 8), fg=UI["text"], bg=UI["panel_alt"]).pack(side="left")

    # ==================== v2.4.0 MODAL DIALOGS ====================

    def open_mod_store_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("GeodeSync · Geode Mod Store & Browser")
        dialog.geometry("680x560")
        dialog.minsize(600, 460)
        dialog.configure(bg=UI["background"])
        dialog.transient(self)
        dialog.grab_set()

        head = tk.Frame(dialog, bg=UI["header"], padx=20, pady=14)
        head.pack(fill="x")
        tk.Label(head, text="🛍️ Geode Mod Store & Browser", font=("Segoe UI", 14, "bold"), fg=UI["lime"], bg=UI["header"]).pack(anchor="w")
        tk.Label(head, text="Discover, search, and 1-click install official mods directly from the Geode SDK Index.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", pady=(2, 8))

        search_bar = tk.Frame(head, bg=UI["header"])
        search_bar.pack(fill="x")

        search_var = tk.StringVar()
        tk.Label(search_bar, text="🔍", font=("Segoe UI", 10), fg=UI["muted"], bg=UI["header"]).pack(side="left", padx=(0, 6))
        search_entry = tk.Entry(search_bar, textvariable=search_var, font=("Segoe UI", 9), bg=UI["inset"], fg=UI["text"], insertbackground=UI["lime"], relief="flat", highlightbackground=UI["border"], highlightthickness=1)
        search_entry.pack(side="left", fill="x", expand=True, ipady=4)

        sort_var = tk.StringVar(value="downloads")
        sort_box = ttk.Combobox(search_bar, textvariable=sort_var, values=["downloads", "recent", "name"], state="readonly", width=12)
        sort_box.pack(side="right", padx=(8, 0))

        content = tk.Frame(dialog, bg=UI["background"], padx=16, pady=10)
        content.pack(fill="both", expand=True)

        status_lbl = tk.Label(content, text="Fetching mods from Geode Index API...", font=("Segoe UI", 9), fg=UI["quiet"], bg=UI["background"])
        status_lbl.pack(anchor="w", pady=(0, 6))

        list_container = tk.Frame(content, bg=UI["panel"], highlightbackground=UI["border"], highlightthickness=1)
        list_container.pack(fill="both", expand=True)

        canvas = tk.Canvas(list_container, bg=UI["panel"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=UI["panel"])

        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_win = canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_canvas_resize(event):
            canvas.itemconfig(canvas_win, width=event.width)
        canvas.bind("<Configure>", _on_canvas_resize)

        def _on_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_wheel)

        def _cleanup():
            try:
                canvas.unbind_all("<MouseWheel>")
            except Exception:
                pass
            dialog.destroy()
        dialog.protocol("WM_DELETE_WINDOW", _cleanup)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        all_mods = []

        def render_cards():
            for w in scrollable.winfo_children():
                w.destroy()

            query = search_var.get().strip().lower()
            filtered = [
                m for m in all_mods
                if not query or query in m["name"].lower() or query in m["id"].lower() or query in m.get("developer", "").lower()
            ]

            installed_ids = {m["id"].lower() for m in self.mgr.get_installed_mods()}
            status_lbl.config(text=f"Showing {len(filtered)} mods (from {len(all_mods)} indexed)")

            if not filtered:
                tk.Label(scrollable, text="No mods found matching your query.", font=("Segoe UI", 10), fg=UI["muted"], bg=UI["panel"]).pack(pady=40)
                return

            for mod in filtered:
                m_id = mod["id"]
                is_installed = m_id.lower() in installed_ids

                card = tk.Frame(scrollable, bg=UI["panel_alt"], padx=12, pady=10, highlightbackground=UI["border"], highlightthickness=1)
                card.pack(fill="x", padx=6, pady=4)

                top_r = tk.Frame(card, bg=UI["panel_alt"])
                top_r.pack(fill="x")

                tk.Label(top_r, text=mod["name"], font=("Segoe UI", 10, "bold"), fg=UI["lime"], bg=UI["panel_alt"]).pack(side="left")
                tk.Label(top_r, text=f"v{mod['version']}", font=("Segoe UI", 8), fg=UI["quiet"], bg=UI["panel_alt"]).pack(side="left", padx=(6, 0))
                tk.Label(top_r, text=f"by {mod['developer']}", font=("Segoe UI", 8, "italic"), fg=UI["muted"], bg=UI["panel_alt"]).pack(side="left", padx=(8, 0))

                dl_k = f"{round(mod['downloads'] / 1000, 1)}K" if mod['downloads'] >= 1000 else str(mod['downloads'])
                tk.Label(top_r, text=f"⬇ {dl_k}", font=("Segoe UI", 8), fg=UI["quiet"], bg=UI["panel_alt"]).pack(side="right")

                desc = mod.get("description", "").strip() or "No description provided."
                tk.Label(card, text=desc, font=("Segoe UI", 8), fg=UI["text"], bg=UI["panel_alt"], wraplength=520, justify="left").pack(anchor="w", pady=(4, 6))

                action_row = tk.Frame(card, bg=UI["panel_alt"])
                action_row.pack(fill="x")

                if mod.get("tags"):
                    tags_str = "  ".join([f"#{t}" for t in mod["tags"][:3]])
                    tk.Label(action_row, text=tags_str, font=("Segoe UI", 7), fg=UI["lilac"], bg=UI["panel_alt"]).pack(side="left")

                def make_install_action(target_mod, target_btn):
                    def do_install():
                        target_btn.config(text="Installing...", state="disabled")
                        def worker():
                            ok, msg = self.mgr.install_mod_from_store(target_mod["id"], target_mod.get("download_link"))
                            def on_done():
                                if ok:
                                    target_btn.config(text="✅ Installed", fg=UI["lime"], bg=UI["inset"])
                                    self.log(f"Installed mod {target_mod['name']} from store.", "SUCCESS")
                                    self.play_ding()
                                else:
                                    target_btn.config(text="Retry", state="normal", fg=UI["amber"])
                                    messagebox.showerror("Install Failed", msg)
                            dialog.after(0, on_done)
                        threading.Thread(target=worker, daemon=True).start()
                    return do_install

                btn_text = "✅ Installed" if is_installed else "⬇️ Install"
                btn_fg = UI["lime"] if is_installed else UI["background"]
                btn_bg = UI["inset"] if is_installed else UI["lime"]
                btn_state = "disabled" if is_installed else "normal"

                inst_btn = tk.Button(
                    action_row, text=btn_text, font=("Segoe UI", 8, "bold"),
                    fg=btn_fg, bg=btn_bg, relief="flat", padx=10, pady=3,
                    cursor="hand2" if not is_installed else "arrow", state=btn_state
                )
                inst_btn.pack(side="right")
                if not is_installed:
                    inst_btn.config(command=make_install_action(mod, inst_btn))

                geode_url_lbl = tk.Label(action_row, text="🌐 Geode", font=("Segoe UI", 8, "underline"), fg=UI["muted"], bg=UI["panel_alt"], cursor="hand2")
                geode_url_lbl.pack(side="right", padx=(0, 10))
                geode_url_lbl.bind("<Button-1>", lambda e, mid=m_id: webbrowser.open(f"https://geode-sdk.org/mods/{mid}"))

        def fetch_data():
            sort_val = sort_var.get()
            ok, mods = self.mgr.fetch_geode_store_mods(per_page=50, sort=sort_val)
            def on_fetched():
                nonlocal all_mods
                if ok:
                    all_mods = mods
                    render_cards()
                else:
                    status_lbl.config(text=f"⚠️ Failed to connect to Geode Index: {mods}", fg=UI["amber"])
            dialog.after(0, on_fetched)

        threading.Thread(target=fetch_data, daemon=True).start()
        search_var.trace_add("write", lambda *a: render_cards())
        sort_var.trace_add("write", lambda *a: threading.Thread(target=fetch_data, daemon=True).start())

    def open_demonlist_browser(self):
        dialog = tk.Toplevel(self)
        dialog.title("GeodeSync · Pointercrate Top 150 Demonlist")
        dialog.geometry("700x560")
        dialog.minsize(620, 460)
        dialog.configure(bg=UI["background"])
        dialog.transient(self)
        dialog.grab_set()

        head = tk.Frame(dialog, bg=UI["header"], padx=20, pady=14)
        head.pack(fill="x")
        tk.Label(head, text="🏆 Pointercrate Top 150 Demonlist", font=("Segoe UI", 14, "bold"), fg=UI["lilac"], bg=UI["header"]).pack(anchor="w")
        tk.Label(head, text="Live official rankings, verifiers, requirements, and local save progress.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", pady=(2, 8))

        search_bar = tk.Frame(head, bg=UI["header"])
        search_bar.pack(fill="x")

        search_var = tk.StringVar()
        tk.Label(search_bar, text="🔍", font=("Segoe UI", 10), fg=UI["muted"], bg=UI["header"]).pack(side="left", padx=(0, 6))
        search_entry = tk.Entry(search_bar, textvariable=search_var, font=("Segoe UI", 9), bg=UI["inset"], fg=UI["text"], insertbackground=UI["lime"], relief="flat", highlightbackground=UI["border"], highlightthickness=1)
        search_entry.pack(side="left", fill="x", expand=True, ipady=4)

        refresh_btn = tk.Button(search_bar, text="🔄 Refresh", font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=UI["lime"], relief="flat", padx=10, pady=4, cursor="hand2")
        refresh_btn.pack(side="right", padx=(8, 0))

        content = tk.Frame(dialog, bg=UI["background"], padx=16, pady=10)
        content.pack(fill="both", expand=True)

        status_lbl = tk.Label(content, text="Querying Pointercrate Demonlist API...", font=("Segoe UI", 9), fg=UI["quiet"], bg=UI["background"])
        status_lbl.pack(anchor="w", pady=(0, 6))

        list_container = tk.Frame(content, bg=UI["panel"], highlightbackground=UI["border"], highlightthickness=1)
        list_container.pack(fill="both", expand=True)

        canvas = tk.Canvas(list_container, bg=UI["panel"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=UI["panel"])

        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_win = canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_canvas_resize(event):
            canvas.itemconfig(canvas_win, width=event.width)
        canvas.bind("<Configure>", _on_canvas_resize)

        def _on_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_wheel)

        def _cleanup():
            try:
                canvas.unbind_all("<MouseWheel>")
            except Exception:
                pass
            dialog.destroy()
        dialog.protocol("WM_DELETE_WINDOW", _cleanup)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        all_demons = []
        demon_grinds = {}
        beaten_names = set()

        def parse_local_progress():
            nonlocal demon_grinds, beaten_names
            data = self.mgr.get_demon_and_grind_data()
            if data:
                beaten_names = {d["name"].lower() for d in data.get("demons", []) if isinstance(d, dict) and "name" in d}
                demon_grinds = {g["name"].lower(): g for g in data.get("grinds", []) if isinstance(g, dict) and "name" in g}

        def render_demons():
            for w in scrollable.winfo_children():
                w.destroy()

            query = search_var.get().strip().lower()
            filtered = [
                d for d in all_demons
                if not query or query in d["name"].lower() or query in d["verifier"].lower() or query in d["publisher"].lower()
            ]

            status_lbl.config(text=f"Loaded {len(filtered)} demons (from {len(all_demons)} on Pointercrate)")

            if not filtered:
                tk.Label(scrollable, text="No demons match your query.", font=("Segoe UI", 10), fg=UI["muted"], bg=UI["panel"]).pack(pady=40)
                return

            for d in filtered:
                pos = d["position"]
                name = d["name"]
                name_l = name.lower()

                card = tk.Frame(scrollable, bg=UI["panel_alt"], padx=12, pady=8, highlightbackground=UI["border"], highlightthickness=1)
                card.pack(fill="x", padx=6, pady=3)

                rank_color = UI["amber"] if pos <= 10 else (UI["lilac"] if pos <= 75 else UI["quiet"])
                tk.Label(card, text=f"#{pos}", font=("Segoe UI", 11, "bold"), fg=rank_color, bg=UI["panel_alt"], width=4, anchor="w").pack(side="left")

                info_col = tk.Frame(card, bg=UI["panel_alt"])
                info_col.pack(side="left", fill="x", expand=True, padx=(4, 0))

                title_row = tk.Frame(info_col, bg=UI["panel_alt"])
                title_row.pack(anchor="w")
                tk.Label(title_row, text=name, font=("Segoe UI", 10, "bold"), fg=UI["text"], bg=UI["panel_alt"]).pack(side="left")

                # Local Progress Badge
                if name_l in beaten_names:
                    tk.Label(title_row, text="🏆 100% BEATEN", font=("Segoe UI", 7, "bold"), fg=UI["lime"], bg=UI["lime_dark"], padx=4, pady=1).pack(side="left", padx=(8, 0))
                elif name_l in demon_grinds:
                    grind = demon_grinds[name_l]
                    tk.Label(title_row, text=f"🎯 {grind['percent']}% ({grind['attempts']:,} att)", font=("Segoe UI", 7, "bold"), fg=UI["lilac"], bg=UI["lilac_dark"], padx=4, pady=1).pack(side="left", padx=(8, 0))

                meta_row = tk.Frame(info_col, bg=UI["panel_alt"])
                meta_row.pack(anchor="w", pady=(2, 0))
                tk.Label(meta_row, text=f"by {d['publisher']}  •  Verified by {d['verifier']}  •  Req: {d['requirement']}%", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel_alt"]).pack(side="left")

                btn_col = tk.Frame(card, bg=UI["panel_alt"])
                btn_col.pack(side="right")

                if d.get("video"):
                    vid_btn = tk.Button(btn_col, text="▶️ Video", command=lambda v=d["video"]: webbrowser.open(v), font=("Segoe UI", 8), bg=UI["inset"], fg=UI["lime"], relief="flat", padx=8, pady=2, cursor="hand2")
                    vid_btn.pack(side="left", padx=2)

                def copy_name(text_to_copy):
                    self.clipboard_clear()
                    self.clipboard_append(text_to_copy)
                    self.log(f"Copied '{text_to_copy}' to clipboard.", "INFO")

                copy_btn = tk.Button(btn_col, text="📋 Copy", command=lambda n=name: copy_name(n), font=("Segoe UI", 8), bg=UI["inset"], fg=UI["quiet"], relief="flat", padx=6, pady=2, cursor="hand2")
                copy_btn.pack(side="left", padx=2)

        def fetch_demons():
            parse_local_progress()
            ok, demons = self.mgr.fetch_pointercrate_demons(limit=100)
            def on_done():
                nonlocal all_demons
                if ok:
                    all_demons = demons
                    render_demons()
                else:
                    status_lbl.config(text=f"⚠️ Failed to connect to Pointercrate: {demons}", fg=UI["amber"])
            dialog.after(0, on_done)

        refresh_btn.config(command=lambda: threading.Thread(target=fetch_demons, daemon=True).start())
        threading.Thread(target=fetch_demons, daemon=True).start()
        search_var.trace_add("write", lambda *a: render_demons())

    def open_jukebox_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("GeodeSync · Universal Jukebox & Practice Music Customizer")
        dialog.geometry("640x520")
        dialog.minsize(580, 440)
        dialog.configure(bg=UI["background"])
        dialog.transient(self)
        dialog.grab_set()

        head = tk.Frame(dialog, bg=UI["header"], padx=20, pady=14)
        head.pack(fill="x")
        tk.Label(head, text="🎵 Universal Jukebox & Practice Music", font=("Segoe UI", 14, "bold"), fg=UI["lime"], bg=UI["header"]).pack(anchor="w")
        tk.Label(head, text="1-click practice music replacer and local GD soundtrack manager.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", pady=(2, 0))

        body_frame = tk.Frame(dialog, bg=UI["background"], padx=18, pady=12)
        body_frame.pack(fill="both", expand=True)

        # 1. Practice Music Status Card
        prac_card = tk.Frame(body_frame, bg=UI["panel"], padx=14, pady=12, highlightbackground=UI["border"], highlightthickness=1)
        prac_card.pack(fill="x", pady=(0, 12))

        tk.Label(prac_card, text="PRACTICE MUSIC HACK (CRASH-PROOF)", font=("Segoe UI", 9, "bold"), fg=UI["lime"], bg=UI["panel"]).pack(anchor="w")
        tk.Label(prac_card, text="Replaces Geometry Dash's StayInsideMe.mp3 with any song of your choice without DLL hooks.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(anchor="w", pady=(2, 8))

        is_custom, desc = self.mgr.get_practice_music_status()
        status_lbl = tk.Label(prac_card, text=f"Status: {desc}", font=("Segoe UI", 9, "bold"), fg=UI["lime"] if is_custom else UI["quiet"], bg=UI["panel"])
        status_lbl.pack(anchor="w", pady=(0, 8))

        btn_row = tk.Frame(prac_card, bg=UI["panel"])
        btn_row.pack(fill="x")

        def choose_custom_audio():
            file_path = filedialog.askopenfilename(
                parent=dialog,
                title="Select Custom Practice Audio File",
                filetypes=[("Audio Files (*.mp3;*.wav;*.ogg)", "*.mp3;*.wav;*.ogg"), ("All Files", "*.*")]
            )
            if not file_path:
                return
            ok, msg = self.mgr.set_custom_practice_music(file_path)
            if ok:
                status_lbl.config(text="Status: Custom Practice Music Active", fg=UI["lime"])
                self.log(f"Custom practice music enabled: {os.path.basename(file_path)}", "SUCCESS")
                self.play_ding()
                messagebox.showinfo("Practice Music Updated", f"Successfully activated custom practice music!\n\nSource: {os.path.basename(file_path)}")
            else:
                messagebox.showerror("Failed", msg)

        def restore_vanilla():
            ok, msg = self.mgr.restore_vanilla_practice_music()
            if ok:
                status_lbl.config(text="Status: Vanilla StayInsideMe.mp3", fg=UI["quiet"])
                self.log("Restored vanilla StayInsideMe.mp3.", "SUCCESS")
                self.play_ding()
                messagebox.showinfo("Restored", "Restored original vanilla StayInsideMe.mp3 practice music.")
            else:
                messagebox.showerror("Failed", msg)

        tk.Button(btn_row, text="📁 Choose Any MP3 File...", command=choose_custom_audio, font=("Segoe UI", 9, "bold"), bg=UI["lime"], fg=UI["background"], relief="flat", padx=12, pady=5, cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="🔄 Restore Vanilla Song", command=restore_vanilla, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["muted"], relief="flat", padx=10, pady=5, cursor="hand2").pack(side="left")

        # 2. Local Audio Library Card
        lib_card = tk.Frame(body_frame, bg=UI["panel"], padx=14, pady=12, highlightbackground=UI["border"], highlightthickness=1)
        lib_card.pack(fill="both", expand=True)

        tk.Label(lib_card, text="DOWNLOADED GD AUDIO LIBRARY", font=("Segoe UI", 9, "bold"), fg=UI["lilac"], bg=UI["panel"]).pack(anchor="w")
        tk.Label(lib_card, text="Songs cached on your system from levels you've played:", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(anchor="w", pady=(2, 6))

        canvas = tk.Canvas(lib_card, bg=UI["panel_alt"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(lib_card, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=UI["panel_alt"])

        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_win = canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_c_resize(event):
            canvas.itemconfig(canvas_win, width=event.width)
        canvas.bind("<Configure>", _on_c_resize)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tracks = self.mgr.get_local_audio_tracks()
        if not tracks:
            tk.Label(scrollable, text="No cached level songs found in your Geometry Dash directory.", font=("Segoe UI", 9), fg=UI["muted"], bg=UI["panel_alt"]).pack(pady=20)
        else:
            for t in tracks[:60]:
                r = tk.Frame(scrollable, bg=UI["panel_alt"], padx=10, pady=5, highlightbackground=UI["border"], highlightthickness=1)
                r.pack(fill="x", padx=4, pady=2)

                tk.Label(r, text=f"🎵 Song #{t['song_id']}", font=("Segoe UI", 9, "bold"), fg=UI["text"], bg=UI["panel_alt"]).pack(side="left")
                tk.Label(r, text=f"({t['size_mb']} MB)", font=("Segoe UI", 8), fg=UI["quiet"], bg=UI["panel_alt"]).pack(side="left", padx=(6, 0))

                def make_use_prac(target_track):
                    def do_use():
                        ok, msg = self.mgr.set_custom_practice_music(target_track["path"])
                        if ok:
                            status_lbl.config(text=f"Status: Custom Practice Music (Song #{target_track['song_id']})", fg=UI["lime"])
                            self.log(f"Practice music set to Song #{target_track['song_id']}", "SUCCESS")
                            self.play_ding()
                            messagebox.showinfo("Practice Music Updated", f"Set practice music to Song #{target_track['song_id']}!")
                        else:
                            messagebox.showerror("Error", msg)
                    return do_use

                use_btn = tk.Button(r, text="Set as Practice Song", command=make_use_prac(t), font=("Segoe UI", 7, "bold"), bg=UI["inset"], fg=UI["lime"], relief="flat", padx=6, pady=2, cursor="hand2")
                use_btn.pack(side="right")

    def open_bundle_manager_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("GeodeSync · Portable Archive & Save Sync (.geodesync)")
        dialog.geometry("640x520")
        dialog.minsize(580, 440)
        dialog.configure(bg=UI["background"])
        dialog.transient(self)
        dialog.grab_set()

        head = tk.Frame(dialog, bg=UI["header"], padx=20, pady=14)
        head.pack(fill="x")
        tk.Label(head, text="☁️ Portable Archive & Save Sync", font=("Segoe UI", 14, "bold"), fg=UI["amber"], bg=UI["header"]).pack(anchor="w")
        tk.Label(head, text="Export or restore your complete Geometry Dash setup in a single portable .geodesync bundle.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", pady=(2, 0))

        body_frame = tk.Frame(dialog, bg=UI["background"], padx=18, pady=12)
        body_frame.pack(fill="both", expand=True)

        # 1. Export Card
        exp_card = tk.Frame(body_frame, bg=UI["panel"], padx=14, pady=12, highlightbackground=UI["border"], highlightthickness=1)
        exp_card.pack(fill="x", pady=(0, 12))

        tk.Label(exp_card, text="📤 EXPORT COMPLETE SETUP BUNDLE", font=("Segoe UI", 9, "bold"), fg=UI["lime"], bg=UI["panel"]).pack(anchor="w")
        tk.Label(exp_card, text="Packages your saves, active mods, and mod configs into a shareable .geodesync zip archive.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(anchor="w", pady=(2, 8))

        inc_saves = tk.BooleanVar(value=True)
        inc_mods = tk.BooleanVar(value=True)
        inc_cfgs = tk.BooleanVar(value=True)

        chk_row = tk.Frame(exp_card, bg=UI["panel"])
        chk_row.pack(anchor="w", pady=(0, 8))

        tk.Checkbutton(chk_row, text="Save Files (CCGameManager & CCLocalLevels)", variable=inc_saves, font=("Segoe UI", 8), fg=UI["text"], bg=UI["panel"], selectcolor=UI["inset"], activebackground=UI["panel"]).pack(side="left", padx=(0, 10))
        tk.Checkbutton(chk_row, text="Active Mods (.geode)", variable=inc_mods, font=("Segoe UI", 8), fg=UI["text"], bg=UI["panel"], selectcolor=UI["inset"], activebackground=UI["panel"]).pack(side="left", padx=(0, 10))
        tk.Checkbutton(chk_row, text="Mod Configs", variable=inc_cfgs, font=("Segoe UI", 8), fg=UI["text"], bg=UI["panel"], selectcolor=UI["inset"], activebackground=UI["panel"]).pack(side="left")

        def do_export():
            dest = filedialog.asksaveasfilename(
                parent=dialog,
                title="Export .geodesync Bundle",
                defaultextension=".geodesync",
                filetypes=[("GeodeSync Bundles (*.geodesync)", "*.geodesync"), ("Zip Archives (*.zip)", "*.zip")]
            )
            if not dest:
                return
            ok, msg = self.mgr.export_geodesync_bundle(dest, include_saves=inc_saves.get(), include_mods=inc_mods.get(), include_configs=inc_cfgs.get())
            if ok:
                self.log(f"Exported bundle: {msg}", "SUCCESS")
                self.play_ding()
                messagebox.showinfo("Export Successful", f"Successfully exported setup bundle!\n\n{msg}")
            else:
                messagebox.showerror("Export Failed", msg)

        tk.Button(exp_card, text="📦 Export to .geodesync Package...", command=do_export, font=("Segoe UI", 9, "bold"), bg=UI["lime"], fg=UI["background"], relief="flat", padx=12, pady=5, cursor="hand2").pack(anchor="w")

        # 2. Import Card
        imp_card = tk.Frame(body_frame, bg=UI["panel"], padx=14, pady=12, highlightbackground=UI["border"], highlightthickness=1)
        imp_card.pack(fill="x")

        tk.Label(imp_card, text="📥 RESTORE / IMPORT BUNDLE", font=("Segoe UI", 9, "bold"), fg=UI["amber"], bg=UI["panel"]).pack(anchor="w")
        tk.Label(imp_card, text="Restores saves, mods, and configs from another device or backup. Always creates a safety backup first!", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(anchor="w", pady=(2, 8))

        def do_import():
            src = filedialog.askopenfilename(
                parent=dialog,
                title="Select .geodesync Bundle to Import",
                filetypes=[("GeodeSync Bundles (*.geodesync)", "*.geodesync"), ("Zip Archives (*.zip)", "*.zip"), ("All Files", "*.*")]
            )
            if not src:
                return
            if not messagebox.askyesno("Confirm Import", "Importing will restore the contents of this bundle to your game folder.\nA safety backup of your existing saves will be taken automatically.\n\nProceed with import?"):
                return
            ok, msg = self.mgr.import_geodesync_bundle(src)
            if ok:
                self.log(f"Imported bundle: {msg}", "SUCCESS")
                self.play_ding()
                self.update_player_stats_ui()
                messagebox.showinfo("Import Successful", f"Setup bundle restored successfully!\n\n{msg}")
            else:
                messagebox.showerror("Import Failed", msg)

        tk.Button(imp_card, text="📂 Select .geodesync Bundle to Restore...", command=do_import, font=("Segoe UI", 9, "bold"), bg=UI["amber"], fg=UI["background"], relief="flat", padx=12, pady=5, cursor="hand2").pack(anchor="w")

    def open_save_optimizer_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("GeodeSync · Save File Bloat Cleaner & Optimizer")
        dialog.geometry("640x500")
        dialog.minsize(580, 420)
        dialog.configure(bg=UI["background"])
        dialog.transient(self)
        dialog.grab_set()

        head = tk.Frame(dialog, bg=UI["header"], padx=20, pady=14)
        head.pack(fill="x")
        tk.Label(head, text="🧹 Save File Bloat Cleaner & Optimizer", font=("Segoe UI", 14, "bold"), fg=UI["lime"], bg=UI["header"]).pack(anchor="w")
        tk.Label(head, text="Eliminate launch freezing and crash risks by safely cleaning online level caches from CCLocalLevels.dat.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", pady=(2, 0))

        body_frame = tk.Frame(dialog, bg=UI["background"], padx=18, pady=12)
        body_frame.pack(fill="both", expand=True)

        card = tk.Frame(body_frame, bg=UI["panel"], padx=16, pady=14, highlightbackground=UI["border"], highlightthickness=1)
        card.pack(fill="x", pady=(0, 12))

        tk.Label(card, text="ANALYZING SAVE DATA...", font=("Segoe UI", 9, "bold"), fg=UI["quiet"], bg=UI["panel"]).pack(anchor="w")
        stats_lbl = tk.Label(card, text="Scanning CCLocalLevels.dat...", font=("Segoe UI", 10), fg=UI["text"], bg=UI["panel"], justify="left")
        stats_lbl.pack(anchor="w", pady=(6, 8))

        explanation = (
            "Why does this happen?\n"
            "Every time you open or copy an online level in Geometry Dash, the game writes the full raw level data into "
            "CCLocalLevels.dat. Over time, this file can grow beyond 30-60 MB, causing the game to take 30+ seconds to load, "
            "freeze on the main menu, and fail cloud backups.\n\n"
            "This optimizer safely purges uncompleted downloaded level caches while strictly preserving all your own created and edited levels."
        )
        tk.Label(card, text=explanation, font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"], wraplength=560, justify="left").pack(anchor="w", pady=(0, 10))

        def refresh_analysis():
            ok, res = self.mgr.analyze_save_bloat()
            if ok:
                stats_lbl.config(
                    text=f"• Save File Size: {res['file_size_mb']} MB\n"
                         f"• Total Levels in Save: {res['total_levels']}\n"
                         f"• Cached Downloaded Online Levels: {res['online_cached']}\n"
                         f"• Preserved User-Created Levels: {res['user_created']}"
                )
            else:
                stats_lbl.config(text=f"⚠️ Could not analyze save file: {res}", fg=UI["amber"])

        refresh_analysis()

        def do_clean():
            if not messagebox.askyesno("Confirm Optimization", "Clean cached online level data?\n\nYour user-created levels will NOT be touched.\nA timestamped backup (.dat.bak) will be created automatically before cleaning."):
                return
            ok, res = self.mgr.clean_save_bloat(remove_online_cache=True)
            if ok:
                self.log(f"Save optimization complete: saved {res['saved_mb']} MB, cleaned {res['removed_levels']} cached levels.", "SUCCESS")
                self.play_ding()
                refresh_analysis()
                messagebox.showinfo(
                    "Optimization Complete",
                    f"Successfully optimized your save file!\n\n"
                    f"• Cleaned: {res['removed_levels']} cached levels\n"
                    f"• Old Size: {res['old_size_mb']} MB\n"
                    f"• New Size: {res['new_size_mb']} MB\n"
                    f"• Space Saved: {res['saved_mb']} MB\n\n"
                    f"Geometry Dash will now launch significantly faster."
                )
            else:
                messagebox.showerror("Optimization Failed", str(res))

        tk.Button(card, text="🚀 Optimize & Clean Save Data Now", command=do_clean, font=("Segoe UI", 10, "bold"), bg=UI["lime"], fg=UI["background"], relief="flat", padx=14, pady=6, cursor="hand2").pack(anchor="w")

    def open_save_slots_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("GeodeSync · Multi-Slot Save Manager")
        dialog.geometry("640x520")
        dialog.minsize(580, 420)
        dialog.configure(bg=UI["background"])
        dialog.transient(self)
        dialog.grab_set()

        head = tk.Frame(dialog, bg=UI["header"], padx=20, pady=14)
        head.pack(fill="x")
        tk.Label(head, text="💾 Multi-Slot Save File Manager", font=("Segoe UI", 14, "bold"), fg=UI["lime"], bg=UI["header"]).pack(anchor="w")
        tk.Label(head, text="Maintain independent save profiles (e.g. Main Account, Demon Grinds, Alt) and switch in 1 click.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", pady=(2, 0))

        content = tk.Frame(dialog, bg=UI["background"], padx=18, pady=12)
        content.pack(fill="both", expand=True)

        top_ctrl = tk.Frame(content, bg=UI["background"])
        top_ctrl.pack(fill="x", pady=(0, 10))

        slot_name_var = tk.StringVar()
        tk.Entry(top_ctrl, textvariable=slot_name_var, font=("Segoe UI", 9), bg=UI["inset"], fg=UI["text"], insertbackground=UI["lime"], relief="flat", highlightbackground=UI["border"], highlightthickness=1, width=24).pack(side="left", ipady=3, padx=(0, 8))

        def create_slot():
            name = slot_name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Please enter a slot name.")
                return
            ok, msg = self.mgr.create_save_slot(name)
            if ok:
                self.log(msg, "SUCCESS")
                self.play_ding()
                slot_name_var.set("")
                render_slots()
                messagebox.showinfo("Slot Created", f"Successfully saved current state to slot '{name}'!")
            else:
                messagebox.showerror("Error", msg)

        tk.Button(top_ctrl, text="➕ Create Slot from Current Progress", command=create_slot, font=("Segoe UI", 8, "bold"), bg=UI["lime"], fg=UI["background"], relief="flat", padx=10, pady=4, cursor="hand2").pack(side="left")

        list_container = tk.Frame(content, bg=UI["panel"], highlightbackground=UI["border"], highlightthickness=1)
        list_container.pack(fill="both", expand=True)

        slots_frame = tk.Frame(list_container, bg=UI["panel"], padx=10, pady=10)
        slots_frame.pack(fill="both", expand=True)

        def render_slots():
            for w in slots_frame.winfo_children():
                w.destroy()
            slots = self.mgr.get_save_slots()
            if not slots:
                tk.Label(slots_frame, text="No extra save slots saved yet.\nEnter a name above to capture your current game state as a slot!", font=("Segoe UI", 9), fg=UI["muted"], bg=UI["panel"]).pack(pady=40)
                return

            for s in slots:
                row = tk.Frame(slots_frame, bg=UI["panel_alt"], padx=12, pady=8, highlightbackground=UI["border"], highlightthickness=1)
                row.pack(fill="x", pady=3)

                tk.Label(row, text=f"📁 {s['name']}", font=("Segoe UI", 10, "bold"), fg=UI["text"], bg=UI["panel_alt"]).pack(side="left")
                p_text = f"Player: {s.get('player_name', 'Player')}  •  ⭐ {s.get('stars', 0)}"
                tk.Label(row, text=p_text, font=("Segoe UI", 8), fg=UI["quiet"], bg=UI["panel_alt"]).pack(side="left", padx=(12, 0))

                def make_switch(slot_name):
                    def do_switch():
                        if not messagebox.askyesno("Confirm Switch", f"Switch active save files to slot '{slot_name}'?\nYour current state will be backed up automatically."):
                            return
                        ok, msg = self.mgr.switch_save_slot(slot_name)
                        if ok:
                            self.log(msg, "SUCCESS")
                            self.play_ding()
                            self.update_player_stats_ui()
                            messagebox.showinfo("Switched", f"Active save switched to '{slot_name}'!")
                        else:
                            messagebox.showerror("Error", msg)
                    return do_switch

                tk.Button(row, text="⚡ Switch to this Slot", command=make_switch(s["name"]), font=("Segoe UI", 8, "bold"), bg=UI["inset"], fg=UI["lime"], relief="flat", padx=8, pady=3, cursor="hand2").pack(side="right")

        render_slots()

    def open_soundpack_hub(self):
        dialog = tk.Toplevel(self)
        dialog.title("GeodeSync · Custom SFX & Death Sound Hub")
        dialog.geometry("620x480")
        dialog.minsize(560, 400)
        dialog.configure(bg=UI["background"])
        dialog.transient(self)
        dialog.grab_set()

        head = tk.Frame(dialog, bg=UI["header"], padx=20, pady=14)
        head.pack(fill="x")
        tk.Label(head, text="💥 Custom SFX & Death Sound Hub", font=("Segoe UI", 14, "bold"), fg=UI["lilac"], bg=UI["header"]).pack(anchor="w")
        tk.Label(head, text="Safely customize Geometry Dash explosion / death sound effects with zero DLL hooks.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", pady=(2, 0))

        content = tk.Frame(dialog, bg=UI["background"], padx=18, pady=14)
        content.pack(fill="both", expand=True)

        card = tk.Frame(content, bg=UI["panel"], padx=16, pady=14, highlightbackground=UI["border"], highlightthickness=1)
        card.pack(fill="x", pady=(0, 12))

        status = self.mgr.get_custom_sfx_status()
        status_text = "Status: 💥 Custom Death Sound Active" if status.get("death_sfx_custom") else "Status: 🔒 Vanilla Explosion (explode_11.ogg)"
        status_lbl = tk.Label(card, text=status_text, font=("Segoe UI", 10, "bold"), fg=UI["lime"] if status.get("death_sfx_custom") else UI["quiet"], bg=UI["panel"])
        status_lbl.pack(anchor="w", pady=(0, 10))

        def pick_custom_file():
            f_path = filedialog.askopenfilename(
                parent=dialog,
                title="Select Custom Death Sound Effect",
                filetypes=[("Audio Files (*.ogg;*.wav;*.mp3)", "*.ogg;*.wav;*.mp3"), ("All Files", "*.*")]
            )
            if not f_path:
                return
            ok, msg = self.mgr.set_custom_death_sfx(f_path)
            if ok:
                status_lbl.config(text="Status: 💥 Custom Death Sound Active", fg=UI["lime"])
                self.log(f"Custom death sound installed: {os.path.basename(f_path)}", "SUCCESS")
                self.play_ding()
                messagebox.showinfo("Sound Updated", f"Successfully activated custom death sound!\n\nFile: {os.path.basename(f_path)}")
            else:
                messagebox.showerror("Error", msg)

        def restore_vanilla():
            ok, msg = self.mgr.restore_vanilla_death_sfx()
            if ok:
                status_lbl.config(text="Status: 🔒 Vanilla Explosion (explode_11.ogg)", fg=UI["quiet"])
                self.log("Restored vanilla death sound.", "SUCCESS")
                self.play_ding()
                messagebox.showinfo("Restored", "Restored official vanilla Geometry Dash death sound.")
            else:
                messagebox.showerror("Error", msg)

        tk.Button(card, text="📁 Choose Any Custom Audio File (.ogg/.wav/.mp3)...", command=pick_custom_file, font=("Segoe UI", 9, "bold"), bg=UI["lime"], fg=UI["background"], relief="flat", padx=12, pady=5, cursor="hand2").pack(anchor="w", pady=(0, 8))
        tk.Button(card, text="🔄 Restore Vanilla Death Sound", command=restore_vanilla, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["muted"], relief="flat", padx=10, pady=4, cursor="hand2").pack(anchor="w")

    def open_vault_helper(self):
        dialog = tk.Toplevel(self)
        dialog.title("GeodeSync · Secret Vaults & Chamber of Time Helper")
        dialog.geometry("640x540")
        dialog.minsize(580, 440)
        dialog.configure(bg=UI["background"])
        dialog.transient(self)
        dialog.grab_set()

        head = tk.Frame(dialog, bg=UI["header"], padx=20, pady=14)
        head.pack(fill="x")
        tk.Label(head, text="🗝️ Secret Vaults & Chamber of Time Helper", font=("Segoe UI", 14, "bold"), fg=UI["amber"], bg=UI["header"]).pack(anchor="w")
        tk.Label(head, text="All official unlock codes for The Vault, Vault of Secrets, and Chamber of Time with 1-click copying.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", pady=(2, 0))

        content = tk.Frame(dialog, bg=UI["background"], padx=16, pady=10)
        content.pack(fill="both", expand=True)

        canvas = tk.Canvas(content, bg=UI["panel"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(content, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=UI["panel"])

        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_win = canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_c_resize(event):
            canvas.itemconfig(canvas_win, width=event.width)
        canvas.bind("<Configure>", _on_c_resize)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        vault_sections = [
            ("THE VAULT (SPOOKY - 10 SILVER COINS)", [
                ("robot", "Unlocks Robot icon"),
                ("ahead", "Unlocks Wave icon"),
                ("gandalf", "Unlocks Rainbow trail"),
                ("sparky", "Unlocks Secret coin"),
                ("spooky", "Unlocks Shy Guy icon"),
                ("neverending", "Unlocks UFO icon"),
            ]),
            ("VAULT OF SECRETS (KEYMASTER - 50 DIAMONDS)", [
                ("brainpower", "Unlocks Brain icon"),
                ("octocube", "Unlocks Octopus icon"),
                ("seven", "Unlocks Finn icon"),
                ("the chicken is on fire", "Unlocks Swamp Green color"),
                ("the challenge", "Unlocks The Challenge secret level"),
                ("gimmiethecolor", "Unlocks Dark Teal color"),
            ]),
            ("CHAMBER OF TIME (GATEKEEPER - 500 DIAMONDS)", [
                ("river", "Unlocks Dark Green color"),
                ("silence", "Unlocks Alternate Wave icon"),
                ("darkness", "Unlocks Face icon"),
                ("hunger", "Unlocks Hungry icon"),
                ("volcano", "Unlocks Flame Wave icon"),
            ]),
        ]

        for sec_title, codes in vault_sections:
            tk.Label(scrollable, text=sec_title, font=("Segoe UI", 9, "bold"), fg=UI["amber"], bg=UI["panel"]).pack(anchor="w", padx=8, pady=(10, 4))
            for code_str, desc in codes:
                row = tk.Frame(scrollable, bg=UI["panel_alt"], padx=10, pady=5, highlightbackground=UI["border"], highlightthickness=1)
                row.pack(fill="x", padx=6, pady=2)

                tk.Label(row, text=code_str, font=("Segoe UI", 9, "bold"), fg=UI["lime"], bg=UI["panel_alt"], width=22, anchor="w").pack(side="left")
                tk.Label(row, text=desc, font=("Segoe UI", 8), fg=UI["text"], bg=UI["panel_alt"]).pack(side="left")

                def copy_code(c=code_str):
                    self.clipboard_clear()
                    self.clipboard_append(c)
                    self.log(f"Copied vault code '{c}' to clipboard.", "INFO")
                    self.play_ding()

                tk.Button(row, text="📋 Copy", command=copy_code, font=("Segoe UI", 7, "bold"), bg=UI["inset"], fg=UI["quiet"], relief="flat", padx=6, pady=2, cursor="hand2").pack(side="right")

    def open_corrupt_save_resurrector(self):
        dialog = tk.Toplevel(self)
        dialog.title("GeodeSync · Emergency Save Resurrector & Salvager")
        dialog.geometry("660x520")
        dialog.minsize(600, 420)
        dialog.configure(bg=UI["background"])
        dialog.transient(self)
        dialog.grab_set()

        head = tk.Frame(dialog, bg=UI["header"], padx=20, pady=14)
        head.pack(fill="x")
        tk.Label(head, text="🛡️ Emergency Save Resurrector & Salvager", font=("Segoe UI", 14, "bold"), fg=UI["lime"], bg=UI["header"]).pack(anchor="w")
        tk.Label(head, text="Recovers and resurrects lost, 0-byte, or corrupted player save data from historical snapshot backups.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", pady=(2, 0))

        content = tk.Frame(dialog, bg=UI["background"], padx=16, pady=10)
        content.pack(fill="both", expand=True)

        candidates = self.mgr.find_salvageable_saves()
        tk.Label(content, text=f"Found {len(candidates)} salvageable save snapshot backups on your PC:", font=("Segoe UI", 9, "bold"), fg=UI["text"], bg=UI["background"]).pack(anchor="w", pady=(0, 6))

        canvas = tk.Canvas(content, bg=UI["panel"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(content, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=UI["panel"])

        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_win = canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_c_resize(event):
            canvas.itemconfig(canvas_win, width=event.width)
        canvas.bind("<Configure>", _on_c_resize)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        if not candidates:
            tk.Label(scrollable, text="No valid backup saves found to resurrect.\nBe sure to keep Auto-Backup turned ON to guarantee continuous protection.", font=("Segoe UI", 9), fg=UI["muted"], bg=UI["panel"]).pack(pady=40)
        else:
            for c in candidates:
                row = tk.Frame(scrollable, bg=UI["panel_alt"], padx=12, pady=8, highlightbackground=UI["border"], highlightthickness=1)
                row.pack(fill="x", padx=6, pady=3)

                info_col = tk.Frame(row, bg=UI["panel_alt"])
                info_col.pack(side="left", fill="x", expand=True)

                tk.Label(info_col, text=f"🎮 {c['player_name']}  •  ⭐ {c['stars']:,} Stars  •  👿 {c['demons']} Demons", font=("Segoe UI", 10, "bold"), fg=UI["lime"], bg=UI["panel_alt"]).pack(anchor="w")
                tk.Label(info_col, text=f"Snapshot: {c['date_str']}  •  Size: {c['size_kb']} KB  •  Location: {c['relative_path']}", font=("Segoe UI", 8), fg=UI["quiet"], bg=UI["panel_alt"]).pack(anchor="w", pady=(2, 0))

                def make_resurrect(candidate_path, player_n):
                    def do_resurrect():
                        if not messagebox.askyesno("Confirm Resurrection", f"Restore this save snapshot for '{player_n}'?\nYour existing state will be backed up safely first."):
                            return
                        ok, msg = self.mgr.resurrect_save(candidate_path)
                        if ok:
                            self.log(msg, "SUCCESS")
                            self.play_ding()
                            self.update_player_stats_ui()
                            messagebox.showinfo("Resurrection Successful", f"Save data successfully restored for {player_n}!")
                        else:
                            messagebox.showerror("Error", msg)
                    return do_resurrect

                tk.Button(row, text="⚡ Revive This Save", command=make_resurrect(c["path"], c["player_name"]), font=("Segoe UI", 8, "bold"), bg=UI["lime"], fg=UI["background"], relief="flat", padx=10, pady=4, cursor="hand2").pack(side="right")

    def open_mod_presets_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("GeodeSync · 1-Click Mod Presets & Competitive Loadouts")
        dialog.geometry("640x500")
        dialog.minsize(580, 420)
        dialog.configure(bg=UI["background"])
        dialog.transient(self)
        dialog.grab_set()

        head = tk.Frame(dialog, bg=UI["header"], padx=20, pady=14)
        head.pack(fill="x")
        tk.Label(head, text="⚡ 1-Click Mod Presets & Competitive Loadouts", font=("Segoe UI", 14, "bold"), fg=UI["lime"], bg=UI["header"]).pack(anchor="w")
        tk.Label(head, text="Instantly optimize your mod configuration for tournaments, level creation, or multiplayer.", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["header"]).pack(anchor="w", pady=(2, 0))

        content = tk.Frame(dialog, bg=UI["background"], padx=18, pady=12)
        content.pack(fill="both", expand=True)

        presets = [
            ("🏆 TOURNAMENT & DEMON GRINDER", "tournament", UI["lilac"], "Maximizes FPS, enables Demon progress trackers, and disables heavy background mods for minimal input latency."),
            ("🎨 LEVEL CREATOR & BUILDER", "creator", UI["amber"], "Optimizes for level editing with BetterEdit and building utilities."),
            ("🌐 GLOBED MULTIPLAYER", "globed", UI["lime"], "Ensures Globed, Node IDs, and voice chat mods are fully active for online sessions."),
            ("🛡️ CLEAN VANILLA PHYSICS", "vanilla", UI["quiet"], "Disables all mods instantly to ensure 100% pure vanilla physics verification.")
        ]

        for p_title, p_key, col, desc in presets:
            card = tk.Frame(content, bg=UI["panel"], padx=14, pady=10, highlightbackground=UI["border"], highlightthickness=1)
            card.pack(fill="x", pady=4)

            tk.Label(card, text=p_title, font=("Segoe UI", 9, "bold"), fg=col, bg=UI["panel"]).pack(anchor="w")
            tk.Label(card, text=desc, font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"], wraplength=480, justify="left").pack(anchor="w", pady=(2, 6))

            def make_apply(preset_k, title_str):
                def do_apply():
                    ok, msg = self.mgr.apply_mod_preset(preset_k)
                    if ok:
                        self.log(msg, "SUCCESS")
                        self.play_ding()
                        messagebox.showinfo("Preset Applied", f"Successfully activated {title_str}!\n\n{msg}")
                    else:
                        messagebox.showerror("Error", msg)
                return do_apply

            tk.Button(card, text="Apply Preset", command=make_apply(p_key, p_title), font=("Segoe UI", 8, "bold"), bg=UI["panel_alt"], fg=col, relief="flat", padx=10, pady=3, cursor="hand2").pack(anchor="e")





if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--geodesync-apply-update":
        _run_update_helper(sys.argv[2])
        raise SystemExit(0)
    try:
        app = GeodeSyncApp()
        app.mainloop()
    except Exception:
        import traceback, time
        try:
            crash_path = _crash_log_path()
            app_dir = os.path.dirname(crash_path)
            os.makedirs(app_dir, exist_ok=True)
            with open(crash_path, "a", encoding="utf-8") as f:
                f.write(f"\n--- MAINLOOP CRASH AT {time.ctime()} ---\n")
                traceback.print_exc(file=f)
        except Exception:
            pass
        raise

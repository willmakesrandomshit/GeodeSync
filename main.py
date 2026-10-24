import os
import sys
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
import shlex
import zipfile
import zlib
import struct
import plistlib
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

APP_VERSION = "2.0.2"
GITHUB_REPO = "willmakesrandomshit/GeodeSync"
CONFIG_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.json"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases?per_page=100"


class DiscordRPC:
    CLIENT_ID = "1178492879627366472"

    def __init__(self, enabled=True):
        self._enabled = enabled
        self._sock = None
        self._connected = False
        self._lock = threading.Lock()
        self._start_time = int(time.time())
        self._current_details = "Geometry Dash Companion"
        self._current_state = "Geode Mods Protected 🛡️"
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def set_enabled(self, val):
        self._enabled = bool(val)
        if not self._enabled:
            self._close_socket()
        else:
            self._start_time = int(time.time())

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
            time.sleep(4)

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
                                "large_image": "gd_large",
                                "large_text": f"GeodeSync v{APP_VERSION}"
                            },
                            "buttons": [
                                {"label": "Get GeodeSync", "url": f"https://github.com/{GITHUB_REPO}"}
                            ]
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

    def update_presence(self, details=None, state=None):
        if details is not None:
            self._current_details = str(details)
        if state is not None:
            self._current_state = str(state)
        if self._connected:
            threading.Thread(target=self._send_activity, daemon=True).start()

    def close(self):
        self._running = False
        self._close_socket()


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
    """Choose the greatest stable published version with instant CDN fallback."""
    try:
        request = urllib.request.Request(RELEASES_API, headers={"User-Agent": "GeodeSync-Client"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            releases = json.loads(response.read().decode("utf-8"))
        if isinstance(releases, list):
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
    except Exception:
        pass

    # Instant fallback to raw version.json (zero rate limits, 50ms response)
    try:
        req = urllib.request.Request(CONFIG_URL, headers={"User-Agent": "GeodeSync-Client"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            cfg = json.loads(resp.read().decode("utf-8"))
            tag = cfg.get("app_version")
            if tag:
                return {
                    "tag_name": f"v{tag}",
                    "html_url": f"https://github.com/{GITHUB_REPO}/releases/tag/v{tag}",
                    "assets": [
                        {
                            "name": "GeodeSync.exe",
                            "browser_download_url": f"https://github.com/{GITHUB_REPO}/releases/download/v{tag}/GeodeSync.exe"
                        },
                        {
                            "name": f"GeodeSync-v{tag}-Windows.zip",
                            "browser_download_url": f"https://github.com/{GITHUB_REPO}/releases/download/v{tag}/GeodeSync-v{tag}-Windows.zip"
                        }
                    ]
                }
    except Exception:
        pass
    raise ValueError("Could not connect to GitHub to check for updates.")


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
            "size": 10700288
        },
        "2.2074 (Previous 2.2 Sub-update)": {
            "manifest": "4978051680517726588",
            "ver": "2.2074",
            "size": 10698752
        },
        "2.113 (Classic 2.11 Legacy)": {
            "manifest": "7938363717144760233",
            "ver": "2.113",
            "size": 7578624
        }
    }

SIZE_22081 = 10700288
SIZE_2209 = 13178880
EXPECTED_DEPOT_BYTES = 230000000 if IS_MAC else 204000000
MACOS_UPDATE_MAX_BYTES = 300 * 1024 * 1024


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


def validate_macos_update_zip(archive):
    """Reject path traversal and unexpected top-level content in a Mac update."""
    app_entries = 0
    expanded_size = 0
    for info in archive.infolist():
        name = info.filename
        normalized = name.replace("\\", "/")
        parts = normalized.split("/")
        if normalized.startswith("/") or ".." in parts:
            raise ValueError("The Mac update archive contains an unsafe path.")
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
    return os.path.expanduser("~/.config/geodesync")


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


def _copy_entry(source, destination):
    if os.path.islink(source):
        os.symlink(os.readlink(source), destination)
    elif os.path.isdir(source):
        shutil.copytree(source, destination, symlinks=True, copy_function=shutil.copy2)
    else:
        shutil.copy2(source, destination)


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
            os.replace(previous_path, installed_path)
        elif name not in original_items and not os.path.lexists(staged_path) and os.path.lexists(installed_path):
            _remove_path(installed_path)


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


def install_depot_transactionally(source_root, destination_root, validator=None, reserve_bytes=128 * 1024 * 1024):
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
                    os.replace(destination, old_path)
                os.replace(new_path, destination)
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
            candidates = [
                os.path.expanduser("~/.local/share/Steam"),
                os.path.expanduser("~/.steam/steam"),
                os.path.expanduser("~/.var/app/com.valvesoftware.Steam/data/Steam"),
                os.path.expanduser("~/.steam/root")
            ]
            for c in candidates:
                if os.path.exists(c):
                    return c
            return os.path.expanduser("~/.local/share/Steam")

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

    def detect_gd_path(self):
        if not self.steam_path:
            return None

        default_gd = os.path.join(self.steam_path, "steamapps", "common", "Geometry Dash")
        if os.path.exists(default_gd):
            return default_gd

        if IS_MAC:
            mac_default = os.path.expanduser("~/Library/Application Support/Steam/steamapps/common/Geometry Dash")
            if os.path.exists(mac_default):
                return mac_default

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
            except Exception:
                pass

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
        if IS_MAC:
            mac_save = os.path.expanduser("~/Library/Application Support/GeometryDash")
            if os.path.exists(mac_save):
                return mac_save
            return mac_save

        if IS_LINUX:
            candidates = []
            if self.steam_path:
                candidates.append(os.path.join(self.steam_path, "steamapps", "compatdata", APP_ID, "pfx", "drive_c", "users", "steamuser", "AppData", "Local", "GeometryDash"))
            candidates.extend([
                os.path.expanduser(f"~/.local/share/Steam/steamapps/compatdata/{APP_ID}/pfx/drive_c/users/steamuser/AppData/Local/GeometryDash"),
                os.path.expanduser(f"~/.steam/steam/steamapps/compatdata/{APP_ID}/pfx/drive_c/users/steamuser/AppData/Local/GeometryDash"),
                os.path.expanduser(f"~/.var/app/com.valvesoftware.Steam/data/Steam/steamapps/compatdata/{APP_ID}/pfx/drive_c/users/steamuser/AppData/Local/GeometryDash")
            ])
            for c in candidates:
                if os.path.exists(c):
                    return c
            return candidates[0] if candidates else None

        appdata = os.environ.get("LOCALAPPDATA")
        if appdata:
            gd_save = os.path.join(appdata, "GeometryDash")
            if os.path.exists(gd_save):
                return gd_save
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

        for meta in KNOWN_VERSIONS.values():
            if meta.get("size") and size == meta["size"]:
                return f"{meta['ver']} (supported depot)", UI["lime"]
        if size == SIZE_2209:
            return "2.209 (Incompatible with Geode)", UI["amber"]
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
                expected_size = next(
                    (meta.get("size") for meta in KNOWN_VERSIONS.values()
                     if str(meta.get("manifest")) == str(self.target_manifest)),
                    None,
                )
                return os.path.getsize(exe) == (expected_size or SIZE_22081)
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
            output = subprocess.check_output(["pgrep", "-f", "GeometryDash"]).decode()
            return bool(output.strip())
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

        try:
            subprocess.run(["pkill", "-9", "-f", "GeometryDash"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
                expected_size = next(
                    (meta.get("size") for meta in KNOWN_VERSIONS.values()
                     if str(meta.get("manifest")) == str(self.target_manifest)),
                    None,
                )
                if not os.path.exists(exe):
                    return False
                actual_size = os.path.getsize(exe)
                return actual_size == expected_size if expected_size else actual_size == SIZE_22081
            except Exception:
                return False
        return False

    def is_geode_installed(self):
        if not self.gd_path:
            return False
        if IS_MAC:
            app_dir = os.path.join(self.gd_path, "Geometry Dash.app")
            mac_geode_dir = os.path.expanduser("~/Library/Application Support/GeometryDash/geode")
            in_app_geode = os.path.join(app_dir, "Contents", "Frameworks", "Geode.dylib")
            return os.path.exists(mac_geode_dir) or os.path.exists(in_app_geode)
        dll = os.path.join(self.gd_path, "Geode.dll")
        proxy = os.path.join(self.gd_path, "XInput1_4.dll")
        geode_dir = os.path.join(self.gd_path, "geode")
        return (os.path.exists(dll) and os.path.exists(proxy)) or os.path.exists(geode_dir)


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


class GeodeSyncApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"GeodeSync v{APP_VERSION} • Geometry Dash companion")
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        w = min(860, max(720, screen_w - 40))
        h = min(820, max(600, screen_h - 80))
        self.geometry(f"{w}x{h}")
        self.minsize(680, 580)
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
        self.auto_backup_enabled = bool(self.settings.get("auto_backup_enabled", True))
        self.sounds_enabled = bool(self.settings.get("sounds_enabled", True))
        self.discord_rpc_enabled = bool(self.settings.get("discord_rpc_enabled", True))
        self.discord_rpc = DiscordRPC(enabled=self.discord_rpc_enabled)
        self._restore_selected_version()
        try:
            self.recovered_transactions = recover_pending_install_transactions(self.mgr.gd_path) if self.mgr.gd_path else []
            self.recovery_error = None
        except Exception as error:
            self.recovered_transactions = []
            self.recovery_error = str(error)
        self.latest_release_url = None
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
        choice = next((item for item in KNOWN_VERSIONS.values() if str(item["manifest"]) == manifest), None)
        self.user_selected_target = bool(choice)
        if choice:
            self.mgr.target_manifest = choice["manifest"]
            self.mgr.target_gd_version = choice["ver"]

    def _save_settings(self):
        self.settings.update({
            "schema_version": 1,
            "game_path": self.mgr.gd_path,
            "target_manifest": str(self.mgr.target_manifest),
            "auto_backup_enabled": bool(self.auto_backup_enabled),
            "sounds_enabled": bool(self.sounds_enabled),
            "discord_rpc_enabled": bool(getattr(self, "discord_rpc_enabled", True)),
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
            f"Game version: {game_version}",
            f"Geode detected: {'yes' if self.mgr.is_geode_installed() else 'no'}",
            f"Steam update lock: {'locked' if self.mgr.is_manifest_locked() else 'unlocked'}",
            f"Selected game version: {self.mgr.target_gd_version}",
            f"Save files detected: {save_count}",
            "",
            "Recent activity (home folders and email addresses are redacted):",
        ]
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

    def create_ui(self):
        # Update Banner
        self.update_banner = tk.Frame(self, bg=UI["lime_dark"], padx=18, pady=9)
        self.update_label = tk.Label(self.update_banner, text="Update available", font=("Segoe UI", 9, "bold"), fg=UI["lime"], bg=UI["lime_dark"])
        self.update_label.pack(side="left")

        self.update_action_btn = tk.Button(self.update_banner, text="Install update", command=self.start_self_update, font=("Segoe UI", 8, "bold"), bg=UI["lime"], fg=UI["background"], activebackground=UI["lime_hover"], activeforeground=UI["background"], relief="flat", padx=12, pady=4, cursor="hand2")
        self.update_action_btn.pack(side="right")

        # Header banner
        self.header_frame = tk.Frame(self, bg=UI["header"], padx=26, pady=18)
        self.header_frame.pack(fill="x")

        title_box = tk.Frame(self.header_frame, bg=UI["header"])
        title_box.pack(side="left")

        title = tk.Label(title_box, text=f"⚡  GeodeSync  ·  v{APP_VERSION}", font=("Segoe UI", 18, "bold"), fg=UI["text"], bg=UI["header"])
        title.pack(anchor="w")

        subtitle = tk.Label(title_box, text="A simple home for your Geometry Dash setup", font=("Segoe UI", 9), fg=UI["muted"], bg=UI["header"])
        subtitle.pack(anchor="w")

        badge_box = tk.Frame(self.header_frame, bg=UI["header"])
        badge_box.pack(side="right")

        help_btn = tk.Button(badge_box, text="How it works", command=self.show_help_dialog, font=("Segoe UI", 9, "bold"), bg=UI["panel_alt"], fg=UI["lilac"], activebackground=UI["border"], activeforeground=UI["text"], relief="flat", padx=12, pady=7, cursor="hand2")
        help_btn.pack(side="right", padx=6)

        # Main Body
        body = tk.Frame(self, bg=UI["background"], padx=26, pady=16)
        body.pack(fill="both", expand=True)

        # 1. SMART GUIDED NEXT STEP
        self.guide_card = tk.Frame(body, bg=UI["panel"], padx=22, pady=18, highlightbackground=UI["border"], highlightthickness=1)
        self.guide_card.pack(fill="x", pady=(0, 12))

        guide_top = tk.Frame(self.guide_card, bg=UI["panel"])
        guide_top.pack(fill="x")

        self.guide_badge = tk.Label(guide_top, text="NEXT STEP", font=("Segoe UI", 8, "bold"), fg=UI["lime"], bg=UI["lime_dark"], padx=9, pady=4)
        self.guide_badge.pack(side="left")

        self.guide_title = tk.Label(self.guide_card, text="Checking your installation…", font=("Segoe UI", 16, "bold"), fg=UI["text"], bg=UI["panel"])
        self.guide_title.pack(anchor="w", pady=(10, 4))

        self.guide_desc = tk.Label(self.guide_card, text="GeodeSync is checking the game and mod loader.", font=("Segoe UI", 9), fg=UI["muted"], bg=UI["panel"], wraplength=740, justify="left")
        self.guide_desc.pack(anchor="w", pady=(0, 12))

        # Real-Time Progress Bar Frame (Hidden by default, shown during downloads/tasks)
        self.progress_frame = tk.Frame(self.guide_card, bg=UI["panel"])
        self.progress_lbl = tk.Label(self.progress_frame, text="Working…", font=("Segoe UI", 8, "bold"), fg=UI["lime"], bg=UI["panel"])
        self.progress_lbl.pack(anchor="w", pady=(0, 3))
        
        # Style ttk Progressbar
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Cyber.Horizontal.TProgressbar", background=UI["lime"], troughcolor=UI["inset"], bordercolor=UI["panel"], lightcolor=UI["lime"], darkcolor=UI["lime_hover"])
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, style="Cyber.Horizontal.TProgressbar", orient="horizontal", mode="determinate", length=400)
        self.progress_bar.pack(fill="x", pady=(0, 6))

        # The One Primary Action Button
        self.primary_btn = ModernButton(
            self.guide_card,
            text="Checking...",
            command=None,
            bg=UI["lime"],
            hover_bg=UI["lime_hover"],
            fg=UI["background"],
            height=48,
            font=("Segoe UI", 11, "bold")
        )
        self.primary_btn.pack(fill="x")

        # 2. STATUS SUMMARY CHIPS
        status_card = tk.Frame(body, bg=UI["panel"], padx=18, pady=12, highlightbackground=UI["border"], highlightthickness=1)
        status_card.pack(fill="x", pady=(0, 12))

        st_title = tk.Label(status_card, text="YOUR SETUP", font=("Segoe UI", 8, "bold"), fg=UI["quiet"], bg=UI["panel"])
        st_title.pack(anchor="w", pady=(0, 4))

        grid_chips = tk.Frame(status_card, bg=UI["panel"])
        grid_chips.pack(fill="x")

        f_v = tk.Frame(grid_chips, bg=UI["panel"])
        f_v.pack(side="left", expand=True, fill="x", padx=3)
        tk.Label(f_v, text="Geometry Dash", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(anchor="w")
        self.ver_badge = tk.Label(f_v, text="Checking…", font=("Segoe UI", 9, "bold"), fg=UI["lime"], bg=UI["lime_dark"], padx=8, pady=4)
        self.ver_badge.pack(anchor="w", pady=(2, 0))

        f_g = tk.Frame(grid_chips, bg=UI["panel"])
        f_g.pack(side="left", expand=True, fill="x", padx=3)
        tk.Label(f_g, text="Geode Mod Loader", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(anchor="w")
        self.geode_badge = tk.Label(f_g, text="Checking…", font=("Segoe UI", 9, "bold"), fg=UI["lilac"], bg=UI["lilac_dark"], padx=8, pady=4)
        self.geode_badge.pack(anchor="w", pady=(2, 0))

        f_l = tk.Frame(grid_chips, bg=UI["panel"])
        f_l.pack(side="left", expand=True, fill="x", padx=3)
        tk.Label(f_l, text="Steam update lock", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(anchor="w")
        self.lock_badge = tk.Label(f_l, text="Checking…", font=("Segoe UI", 9, "bold"), fg=UI["amber"], bg=UI["panel_alt"], padx=8, pady=4, cursor="hand2")
        self.lock_badge.pack(anchor="w", pady=(2, 0))
        self.lock_badge.bind("<Button-1>", lambda e: self.toggle_steam_lock())

        f_steam = tk.Frame(grid_chips, bg=UI["panel"])
        f_steam.pack(side="left", expand=True, fill="x", padx=3)
        tk.Label(f_steam, text="Steam", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(anchor="w")
        self.steam_badge = tk.Label(f_steam, text="Checking…", font=("Segoe UI", 9, "bold"), fg=UI["muted"], bg=UI["panel_alt"], padx=8, pady=4)
        self.steam_badge.pack(anchor="w", pady=(2, 0))

        f_saves = tk.Frame(grid_chips, bg=UI["panel"])
        f_saves.pack(side="left", expand=True, fill="x", padx=3)
        tk.Label(f_saves, text="Saves", font=("Segoe UI", 8), fg=UI["muted"], bg=UI["panel"]).pack(anchor="w")
        self.saves_badge = tk.Label(f_saves, text="Checking…", font=("Segoe UI", 9, "bold"), fg=UI["muted"], bg=UI["panel_alt"], padx=8, pady=4)
        self.saves_badge.pack(anchor="w", pady=(2, 0))

        # 3. Keep the first screen focused on the recommended action. Utilities
        # stay available in a compact drawer instead of competing with it.
        tools_card = tk.Frame(body, bg=UI["header"], padx=14, pady=10, highlightbackground=UI["border"], highlightthickness=1)
        tools_card.pack(fill="x", pady=(0, 12))

        row_main = tk.Frame(tools_card, bg=UI["header"])
        row_main.pack(fill="x")

        self.more_toggle_btn = tk.Button(row_main, text="More tools  +", command=self.toggle_more_tools, font=("Segoe UI", 9, "bold"), bg=UI["panel_alt"], fg=UI["muted"], activebackground=UI["border"], activeforeground=UI["text"], relief="flat", padx=12, pady=7, cursor="hand2")
        self.more_toggle_btn.pack(side="left")

        self.restore_gd_btn = tk.Button(row_main, text="Restore current game", command=self.upgrade_clicked, font=("Segoe UI", 9, "bold"), bg=UI["panel_alt"], fg=UI["amber"], activebackground=UI["border"], activeforeground=UI["text"], relief="flat", padx=12, pady=7, cursor="hand2")
        self.restore_gd_btn.pack(side="right")

        # The drawer is collapsed by default. A three-column grid stays usable
        # at narrower window sizes and keeps every existing tool reachable.
        self.more_frame = tk.Frame(tools_card, bg=UI["inset"], padx=8, pady=8, highlightbackground=UI["border"], highlightthickness=1)
        tool_grid = tk.Frame(self.more_frame, bg=UI["inset"])
        tool_grid.pack(fill="x")
        for column in range(3):
            tool_grid.columnconfigure(column, weight=1)

        def add_tool(label, command, *, color=UI["muted"], row, column, bold=False):
            button = tk.Button(
                tool_grid, text=label, command=command,
                font=("Segoe UI", 8, "bold" if bold else "normal"),
                bg=UI["panel_alt"], fg=color, activebackground=UI["border"],
                activeforeground=UI["text"], relief="flat", padx=7, pady=7,
                cursor="hand2",
            )
            button.grid(row=row, column=column, sticky="ew", padx=3, pady=3)
            return button

        add_tool("💾 Backup saves", self.backup_saves, color=UI["lime"], row=0, column=0, bold=True)
        add_tool("♻️ Save Manager", self.restore_saves, color=UI["lime"], row=0, column=1)
        add_tool("🩺 Save Doctor", self.run_save_doctor, color=UI["lilac"], row=0, column=2)
        add_tool("📦 Essential mods", self.install_essential_mods, color=UI["amber"], row=1, column=0, bold=True)
        add_tool("📁 Mods folder", self.open_mods_folder, row=1, column=1)
        add_tool("🎯 Mod profiles", self.open_mod_profiles, row=1, column=2)
        add_tool("⚡ FPS unlocker", self.open_fps_unlocker, color=UI["lime"], row=2, column=0)
        add_tool("🧹 Cache cleaner", self.open_cache_cleaner, color=UI["muted"], row=2, column=1)
        add_tool("🩹 Crash Doctor", self.run_crash_doctor, color=UI["lilac"], row=2, column=2)
        add_tool("🎮 Game profiles", self.open_game_profiles, color=UI["lilac"], row=3, column=0)
        self.auto_backup_btn = add_tool("Auto-Backup: ON", self.toggle_auto_backup, color=UI["lime"], row=3, column=1, bold=True)
        add_tool("📌 Desktop shortcut", self.create_desktop_shortcut, color=UI["lime"], row=3, column=2)
        add_tool("🔄 Check updates", self.manual_check_updates, color=UI["lime"], row=4, column=0, bold=True)
        add_tool("📋 Export report", self.export_support_report, color=UI["amber"], row=4, column=1)
        self.sounds_btn = add_tool("🔊 GD Sounds: ON", self.toggle_sounds, color=UI["lime"], row=4, column=2)
        self.rpc_btn = add_tool("🎮 Discord RPC: ON", self.toggle_rpc, color=UI["lilac"], row=5, column=0)
        add_tool("📢 Share GeodeSync", self.share_geodesync, color=UI["lime"], row=5, column=1, bold=True)
        add_tool("⭐ Star on GitHub", lambda: open_url_or_path(f"https://github.com/{GITHUB_REPO}"), color=UI["amber"], row=5, column=2)
        if not self.auto_backup_enabled:
            self.auto_backup_btn.config(text="Auto-Backup: OFF", fg=UI["muted"])
        if not self.sounds_enabled:
            self.sounds_btn.config(text="🔇 GD Sounds: OFF", fg=UI["muted"])
        if not self.discord_rpc_enabled:
            self.rpc_btn.config(text="🎮 Discord RPC: OFF", fg=UI["muted"])

        # 4. ACTIVITY LOG
        log_card = tk.Frame(body, bg=UI["header"], padx=14, pady=10, highlightbackground=UI["border"], highlightthickness=1)
        log_card.pack(fill="both", expand=True)

        log_head = tk.Frame(log_card, bg=UI["header"])
        log_head.pack(fill="x", pady=(0, 3))

        log_title = tk.Label(log_head, text="Activity", font=("Segoe UI", 9, "bold"), fg=UI["muted"], bg=UI["header"])
        log_title.pack(side="left")

        clear_btn = tk.Button(log_head, text="Clear", command=self.clear_log, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["muted"], relief="flat", padx=9, pady=3, cursor="hand2")
        clear_btn.pack(side="right")

        self.log_text = tk.Text(log_card, bg=UI["inset"], fg=UI["text"], font=("Consolas", 9), relief="flat", wrap="word", height=5, padx=10, pady=9, insertbackground=UI["lime"])
        self.log_text.pack(fill="both", expand=True)
        self.log_text.config(state="disabled")

        # Footer
        footer = tk.Frame(self, bg=UI["background"], padx=26, pady=8)
        footer.pack(fill="x", side="bottom")

        self.path_lbl = tk.Label(footer, text=f"Game folder: {self.mgr.gd_path or 'Not found'}", font=("Segoe UI", 8), fg=UI["quiet"], bg=UI["background"])
        self.path_lbl.pack(side="left")

        repo_link = tk.Label(footer, text="GitHub", font=("Segoe UI", 8, "underline"), fg=UI["lilac"], bg=UI["background"], cursor="hand2")
        repo_link.pack(side="left", padx=16)
        repo_link.bind("<Button-1>", lambda e: webbrowser.open(f"https://github.com/{GITHUB_REPO}"))

        choose_path_btn = tk.Button(footer, text="Choose game folder", command=self.browse_gd_path, font=("Segoe UI", 8), bg=UI["panel_alt"], fg=UI["muted"], relief="flat", padx=9, pady=4, cursor="hand2")
        choose_path_btn.pack(side="right")

    def log(self, message: str, level: str = "INFO"):
        self.log_text.config(state="normal")
        time_str = datetime.now().strftime("%H:%M:%S")
        color_prefix = {
            "INFO": "[INFO]",
            "SUCCESS": "[OK]",
            "WARN": "[WARN]",
            "ERROR": "[ERR]"
        }.get(level, "[INFO]")
        line = f"[{time_str}] {color_prefix} {message}"
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self._append_activity(line)

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
        if not getattr(self, "sounds_enabled", True):
            return
        if IS_WIN and winsound:
            def _play():
                try:
                    notes = [(523, 70), (659, 70), (784, 90), (1046, 200)]
                    for freq, dur in notes:
                        winsound.Beep(freq, dur)
                except Exception:
                    try:
                        winsound.MessageBeep(winsound.MB_ICONASTERISK)
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

        if hasattr(self, "discord_rpc"):
            status_desc = "Geode Mods Protected 🛡️" if is_locked else "Ready to Switch"
            self.discord_rpc.update_presence(f"GD {ver_text}", status_desc)

        has_geode = self.mgr.is_geode_installed()
        if has_geode:
            self.geode_badge.config(text="Installed", fg=UI["lilac"], bg=UI["lilac_dark"])
        else:
            self.geode_badge.config(text="Not installed", fg=UI["red"], bg=UI["red_dark"])

        self.path_lbl.config(text=f"Game folder: {self.mgr.gd_path or 'Not found'}")

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
            text="▶️ Launch Geometry Dash",
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
                "Follow the on-screen steps to complete installation, then return to GeodeSync."
            )
            time.sleep(3)
            self.refresh_status()

        except Exception as e:
            self.log(f"Auto-install error: {e}. Opening geode-sdk.org instead...", "WARN")
            self.progress_frame.pack_forget()
            self.primary_btn.set_enabled(True)
            webbrowser.open("https://geode-sdk.org")
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
                    messagebox.showerror("Geometry Dash is still running", "Close Geometry Dash before changing its game files.")
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
            "No save backup found",
            "GeodeSync could not find Geometry Dash save files to back up. Continue with the version switch anyway?",
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
            messagebox.showerror(
                "Downgrade stopped",
                f"GeodeSync stopped the downgrade before reporting success:\n\n{e}\n\n"
                "Check the activity log before trying again.",
            )

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

        if self.mgr.has_downloaded_depot():
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

            if self.mgr.has_downloaded_depot():
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
            messagebox.showerror(
                "Steam download is incomplete",
                "Steam reported the download as complete, but its cached Geometry Dash.app is still missing valid app metadata. "
                "GeodeSync did not replace your installed game. Quit Steam fully, reopen it, and retry 1-Click Fix once. "
                "If it still fails, send the full GeodeSync activity log so the depot path and Steam result can be checked.",
            )
            self.refresh_status()
        else:
            self.is_downloading_depot = False
            self.pending_profile_mods = None
            self.log("Steam download timed out or took longer than 6 mins.", "WARN")
            messagebox.showwarning("Download in Progress", "Steam is still downloading in the background. Check your Steam client and click again when ready!")
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
            def validate_staged_depot(staged_root):
                if IS_MAC:
                    app_path = find_macos_game_app(staged_root)
                    if not app_path:
                        return "Geometry Dash.app is missing from the downloaded depot."
                    return validate_macos_game_app(app_path)
                expected_size = next(
                    (meta.get("size") for meta in KNOWN_VERSIONS.values()
                     if str(meta.get("manifest")) == str(self.mgr.target_manifest)),
                    None,
                )
                executable = os.path.join(staged_root, "GeometryDash.exe")
                if not os.path.isfile(executable):
                    return "GeometryDash.exe is missing from the downloaded depot."
                if expected_size and os.path.getsize(executable) != expected_size:
                    return f"GeometryDash.exe size does not match the selected {self.mgr.target_gd_version} depot."
                return None

            install_depot_transactionally(depot, self.mgr.gd_path, validator=validate_staged_depot)
            self.log(f"Game files successfully replaced with {self.mgr.target_gd_version}!", "SUCCESS")
        except Exception as e:
            self.is_downloading_depot = False
            self.pending_profile_mods = None
            self.primary_btn.set_enabled(True)
            self.log(f"Safe game switch failed; rollback/recovery preserved the previous files: {e}", "ERROR")
            messagebox.showerror(
                "Game switch was not completed",
                f"GeodeSync could not finish installing the selected game version. It restored the previous files or kept recovery data for the next launch.\n\n{e}",
            )
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
                "output-type": "CoreAudio" if IS_MAC else "WASAPI",
                "sample-rate": "48000",
                "buffer-size": "128",
                "master-volume": 100,
                "output-device": -1
            }
            with open(os.path.join(fmod_dir, "settings.json"), "w", encoding="utf-8") as f:
                json.dump(fmod_settings, f, indent=2)
            applied.append(f"✓ FMOD Audio Buffer set to 128 samples / {'CoreAudio' if IS_MAC else 'WASAPI'} (slashes audio delay to ~2.7ms)")
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
        crash_dir = self.mgr.get_crashlogs_dir()
        if not crash_dir or not os.path.exists(crash_dir):
            messagebox.showinfo("🩺 Crash Doctor", "No crash logs folder found! Your Geometry Dash installation looks clean.")
            return

        logs = [os.path.join(crash_dir, f) for f in os.listdir(crash_dir) if f.endswith(".log")]
        if not logs:
            messagebox.showinfo("🩺 Crash Doctor", "Great news! Zero crash logs were detected. No broken mods found!")
            return

        logs.sort(key=os.path.getmtime, reverse=True)
        latest_log = logs[0]

        culprit = None
        details = []
        try:
            with open(latest_log, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            for line in content.splitlines():
                if "Faulty Mod:" in line and "<Unknown>" not in line:
                    culprit = line.split("Faulty Mod:")[1].strip()
                    break
                if "Failed to load:" in line:
                    details.append(line.strip())

            if not culprit:
                # Scan stack trace for known mod id patterns
                matches = re.findall(r"([a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+)\.dll", content)
                if matches:
                    culprit = matches[0]

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
            msg = f"Latest Crash Log: {os.path.basename(latest_log)} ({time_str})\n\n"
            msg += "No single specific mod was flagged as the culprit. This usually means a game version mismatch (e.g. 2.209 vs 2.2081).\n\n"
            msg += "Clicking '⚡ 1-Click Fix' to downgrade to 2.2081 will resolve most startup crashes!"
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

    def browse_gd_path(self):
        selected = filedialog.askdirectory(title="Select Geometry Dash Folder")
        if selected:
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
                self.refresh_status()
            else:
                target_name = "Geometry Dash.app" if IS_MAC else "GeometryDash.exe"
                messagebox.showerror("Invalid Directory", f"The selected folder does not contain {target_name}.")

    def launch_gd(self):
        if IS_MAC:
            self.log("Checking Geometry Dash and requesting launch through Steam...", "INFO")
            accepted, details = request_macos_steam_launch(self.mgr.gd_path)
            if accepted:
                self.log(details, "INFO")
                threading.Thread(target=self._monitor_macos_launch, daemon=True).start()
                return
            self.log(details, "ERROR")
            messagebox.showerror(
                "Geometry Dash could not be launched",
                f"{details}\n\nGeodeSync did not modify the game or bypass macOS security. "
                "If the app bundle is complete, use Steam → Geometry Dash → Properties → Installed Files → "
                "Verify integrity, then try launching from Steam. If Steam still reports OS Error 256, "
                "the Steam launch log or macOS Console report is needed to identify the cause.",
            )
            return

        self.log("Launching Geometry Dash...", "INFO")
        if hasattr(self, "discord_rpc"):
            self.discord_rpc.update_presence("Playing Geometry Dash", "Geode Mods Protected 🛡️")
        if not open_url_or_path(f"steam://run/{APP_ID}"):
            self.log("Could not pass the Geometry Dash launch request to Steam.", "ERROR")
            messagebox.showerror("Launch failed", "Could not pass the Geometry Dash launch request to Steam.")

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
                self.after(0, lambda: self.show_update_banner(tag, prompt=True))
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
        self.log(f"New update detected: v{new_ver}! Click 'Install update' to update automatically.", "SUCCESS")
        if prompt:
            def ask():
                try:
                    if messagebox.askyesno(
                        "GeodeSync Update Available",
                        f"A new version of GeodeSync (v{new_ver}) is available!\n\nWould you like to install the update automatically now?",
                        parent=self,
                    ):
                        self.start_self_update()
                except Exception as e:
                    self.log(f"Update prompt error: {e}", "WARN")
            self.after(50, ask)

    def manual_check_updates(self):
        self.log("Checking for GeodeSync updates...", "INFO")
        def _check():
            try:
                rel = fetch_latest_published_release(timeout=6)
                tag = str(rel.get("tag_name", "")).lstrip("v")
                if is_newer_app_version(tag, APP_VERSION):
                    self.latest_release_url = rel.get("html_url", f"https://github.com/{GITHUB_REPO}/releases")
                    self.after(0, lambda: self.show_update_banner(tag, prompt=True))
                else:
                    self.after(0, lambda: messagebox.showinfo("Up to Date", f"You are running the latest version of GeodeSync (v{APP_VERSION}).", parent=self))
                    self.after(0, lambda: self.log(f"GeodeSync v{APP_VERSION} is up to date.", "SUCCESS"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Update Check Failed", f"Could not check for updates:\n{e}", parent=self))
                self.after(0, lambda: self.log(f"Update check failed: {e}", "ERROR"))
        threading.Thread(target=_check, daemon=True).start()

    def open_update_link(self):
        url = self.latest_release_url or f"https://github.com/{GITHUB_REPO}/releases"
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
                xored = bytes(b ^ 11 for b in raw)
                decoded = base64.b64decode(xored.replace(b'-', b'+').replace(b'_', b'/'))
                decomp = zlib.decompress(decoded, 15 + 32)
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
    def start_self_update(self):
        if not self.latest_release_url:
            messagebox.showinfo("Update Check", "GeodeSync is currently up to date!")
            return

        threading.Thread(target=self._run_self_update, daemon=True).start()

    def _run_self_update(self):
        if IS_MAC:
            self._run_macos_self_update()
            return

        self.log("Downloading latest GeodeSync update from GitHub...", "INFO")
        self._schedule_update_progress("Contacting GitHub for new release binary...", 20)

        try:
            data = fetch_latest_published_release(timeout=12)
            tag = str(data.get("tag_name", "")).strip()
            if not is_newer_app_version(tag, APP_VERSION):
                raise ValueError("GitHub did not report a newer GeodeSync release.")
            self.latest_release_url = data.get("html_url", self.latest_release_url)
            asset_url = None
            for asset in data.get("assets", []):
                if asset.get("name") == "GeodeSync.exe":
                    asset_url = asset.get("browser_download_url")
                    break

            if not asset_url:
                raise Exception("GeodeSync.exe asset not found in release.")

            my_exe = sys.executable if getattr(sys, 'frozen', False) else None
            if not my_exe or not os.path.exists(my_exe):
                webbrowser.open(self.latest_release_url)
                self._schedule_update_progress("", hide=True)
                return

            exe_dir = os.path.dirname(my_exe)
            temp_exe = os.path.join(exe_dir, "GeodeSync_update.exe")

            self._schedule_update_progress("Downloading new GeodeSync executable...", 35)
            req = urllib.request.Request(asset_url, headers={"User-Agent": "GeodeSync-Client"})
            with urllib.request.urlopen(req) as resp, open(temp_exe, "wb") as out_file:
                total_bytes = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    if total_bytes > 0:
                        pct = 35 + int((downloaded / total_bytes) * 55)
                        mb = round(downloaded / (1024 * 1024), 1)
                        total_mb = round(total_bytes / (1024 * 1024), 1)
                        self._schedule_update_progress(f"Downloading update: {mb} / {total_mb} MB ({pct}%)", pct)

            self._schedule_update_progress("Restarting into updated version...", 100)

            bat_path = os.path.join(exe_dir, "_geodesync_swap.bat")
            with open(bat_path, "w") as f:
                f.write(
                    f"@echo off\r\n"
                    f"timeout /t 1 /nobreak >nul\r\n"
                    f":retry\r\n"
                    f"move /y \"{temp_exe}\" \"{my_exe}\" >nul 2>&1\r\n"
                    f"if errorlevel 1 (\r\n"
                    f"    timeout /t 1 /nobreak >nul\r\n"
                    f"    goto retry\r\n"
                    f")\r\n"
                    f"powershell -NoProfile -Command \"Unblock-File -Path '{my_exe}' -ErrorAction SilentlyContinue\"\r\n"
                    f"start \"\" \"{my_exe}\"\r\n"
                    f"del \"%~f0\"\r\n"
                )

            subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=0x08000000)
            self.after(200, lambda: (self.destroy(), sys.exit(0)))

        except Exception as e:
            self.log(f"Self-update error: {e}. Opening GitHub release...", "WARN")
            self._schedule_update_progress("", hide=True)
            webbrowser.open(self.latest_release_url)

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

    def _run_macos_self_update(self):
        """Download, verify and atomically replace this installed .app."""
        workspace = None
        release_url = self.latest_release_url or f"https://github.com/{GITHUB_REPO}/releases/latest"
        try:
            if not getattr(sys, "frozen", False):
                self._schedule_update_progress("Open GitHub to install the packaged Mac app…", hide=True)
                self.after(0, lambda: webbrowser.open(release_url))
                return

            self._schedule_update_progress("Checking the Mac update…", 5)
            release = fetch_latest_published_release(timeout=15)

            tag = str(release.get("tag_name", "")).strip()
            release_url = release.get("html_url", release_url)
            self.latest_release_url = release_url
            version = tag.lstrip("v")
            if not is_newer_app_version(version, APP_VERSION):
                raise ValueError("GitHub did not report a newer GeodeSync release.")

            asset = select_macos_update_asset(release)
            asset_size = int(asset["size"])
            workspace = tempfile.mkdtemp(prefix="geodesync-update-")
            archive_path = os.path.join(workspace, asset["name"])
            self._schedule_update_progress("Downloading the matching Mac app…", 15)
            request = urllib.request.Request(asset["browser_download_url"], headers={"User-Agent": "GeodeSync-Client"})
            digest = hashlib.sha256()
            received = 0
            with urllib.request.urlopen(request, timeout=45) as response, open(archive_path, "wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > MACOS_UPDATE_MAX_BYTES:
                        raise ValueError("The Mac update download exceeded the allowed size.")
                    output.write(chunk)
                    digest.update(chunk)
                    progress = min(65, 15 + int(50 * received / max(asset_size, 1)))
                    self._schedule_update_progress("Downloading the matching Mac app…", progress)

            verify_macos_update_digest(asset.get("digest"), digest.hexdigest())

            self._schedule_update_progress("Checking the app bundle…", 72)
            with zipfile.ZipFile(archive_path) as archive:
                validate_macos_update_zip(archive)
            extracted = os.path.join(workspace, "extracted")
            os.makedirs(extracted, exist_ok=True)
            subprocess.run(
                ["/usr/bin/ditto", "-x", "-k", "--sequesterRsrc", archive_path, extracted],
                check=True,
                timeout=180,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            staged_app = os.path.join(extracted, "GeodeSync.app")
            new_executable = os.path.join(staged_app, "Contents", "MacOS", "GeodeSync")
            new_plist = os.path.join(staged_app, "Contents", "Info.plist")
            if not os.path.isfile(new_executable) or not os.path.isfile(new_plist):
                raise ValueError("The downloaded ZIP does not contain a complete GeodeSync app.")
            with open(new_plist, "rb") as plist_file:
                new_metadata = plistlib.load(plist_file)
            if new_metadata.get("CFBundleIdentifier") != "com.willmakesrandomshit.geodesync":
                raise ValueError("The downloaded app has the wrong bundle identity.")
            if str(new_metadata.get("CFBundleShortVersionString", "")) != version:
                raise ValueError("The downloaded app version does not match its GitHub release tag.")
            try:
                subprocess.run(
                    ["/usr/bin/codesign", "--verify", "--deep", "--strict", staged_app],
                    check=True,
                    timeout=60,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

            executable = os.path.abspath(sys.executable)
            app_path = None
            parent = os.path.dirname(executable)
            while parent and parent != os.path.dirname(parent):
                if parent.endswith(".app") and os.path.isdir(parent):
                    app_path = parent
                    break
                parent = os.path.dirname(parent)
            if not app_path:
                app_path = os.path.dirname(os.path.dirname(os.path.dirname(executable)))
            app_path = os.path.abspath(app_path)
            if not app_path.endswith(".app") or not os.path.isdir(app_path):
                raise ValueError("Could not locate the installed GeodeSync.app to update it.")
            parent_dir = os.path.dirname(app_path)
            if not os.access(parent_dir, os.W_OK):
                raise PermissionError(
                    "This app is installed in a protected folder. Move GeodeSync.app to your personal "
                    "Applications folder, then use Update Now again."
                )

            app_parent = os.path.expanduser("~/Library/Application Support/GeodeSync")
            os.makedirs(app_parent, exist_ok=True)
            helper_path = os.path.join(app_parent, "apply-update.sh")
            incoming_path = os.path.join(parent_dir, ".GeodeSync.app.update")
            backup_path = os.path.join(parent_dir, ".GeodeSync.app.previous")
            log_path = os.path.expanduser("~/Library/Logs/GeodeSync-updater.log")
            app_path_q = shlex.quote(app_path)
            incoming_q = shlex.quote(incoming_path)
            backup_q = shlex.quote(backup_path)
            staged_q = shlex.quote(staged_app)
            workspace_q = shlex.quote(workspace)
            helper_q = shlex.quote(helper_path)
            log_q = shlex.quote(log_path)
            helper = f"""#!/bin/sh
set -u
TARGET={app_path_q}
INCOMING={incoming_q}
BACKUP={backup_q}
STAGED={staged_q}
WORKSPACE={workspace_q}
HELPER={helper_q}
LOG={log_q}
PID={os.getpid()}
while /bin/kill -0 "$PID" 2>/dev/null; do /bin/sleep 0.25; done
if ! /usr/bin/ditto "$STAGED" "$INCOMING" >>"$LOG" 2>&1; then
  /bin/rm -rf "$INCOMING" "$WORKSPACE"
  exit 1
fi
/bin/rm -rf "$BACKUP"
if [ -e "$TARGET" ]; then /bin/mv "$TARGET" "$BACKUP"; fi
if ! /bin/mv "$INCOMING" "$TARGET"; then
  if [ -e "$BACKUP" ]; then /bin/mv "$BACKUP" "$TARGET"; fi
  /bin/rm -rf "$INCOMING" "$WORKSPACE"
  exit 1
fi
/usr/bin/xattr -cr "$TARGET" 2>/dev/null || true
if ! /usr/bin/open "$TARGET" >>"$LOG" 2>&1; then
  /bin/mv "$TARGET" "$INCOMING"
  if [ -e "$BACKUP" ]; then /bin/mv "$BACKUP" "$TARGET"; fi
  /bin/rm -rf "$INCOMING" "$WORKSPACE"
  exit 1
fi
/bin/rm -rf "$BACKUP" "$WORKSPACE"
/bin/rm -f "$HELPER"
"""
            with open(helper_path, "w", encoding="utf-8") as helper_file:
                helper_file.write(helper)
            os.chmod(helper_path, 0o700)
            self._schedule_update_progress("Installing update and reopening GeodeSync…", 95)
            subprocess.Popen(
                ["/bin/sh", helper_path],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self.after(0, self.destroy)
        except Exception as exc:
            if workspace:
                shutil.rmtree(workspace, ignore_errors=True)
            message = str(exc)
            def report_failure():
                try:
                    self.progress_frame.pack_forget()
                    messagebox.showerror(
                        "Mac update not installed",
                        f"{message}\n\nYour current app was left in place. Open GitHub Releases to download manually?",
                    )
                    webbrowser.open(release_url)
                except Exception:
                    pass
            try:
                self.after(0, report_failure)
            except Exception:
                pass

    def _remote_update_monitor_thread(self):
        while getattr(self, "_monitor_running", True):
            try:
                self.check_remote_updates()
            except Exception:
                pass
            time.sleep(120)

    # ==========================================
    # v1.1.3 PRO FEATURE: AUTO-BACKUP ON GD EXIT
    # ==========================================
    def _auto_backup_monitor_thread(self):
        was_running = False
        while getattr(self, "_monitor_running", True):
            try:
                is_running = self.mgr.is_gd_process_running()
                if was_running and not is_running:
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
        self.sounds_enabled = not getattr(self, "sounds_enabled", True)
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
                    with open(dest, "w") as f:
                        f.write(
                            "[Desktop Entry]\n"
                            "Type=Application\n"
                            "Name=GeodeSync\n"
                            "Comment=Geometry Dash Companion\n"
                            f"Exec={my_exe}\n"
                            "Icon=utilities-system-monitor\n"
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
            self.log("Discord Rich Presence enabled. Status showing on Discord profile.", "SUCCESS")
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
            xored = bytes(b ^ 11 for b in raw)
            decoded = base64.b64decode(xored.replace(b'-', b'+').replace(b'_', b'/'))
            decomp = zlib.decompress(decoded, 15 + 32).decode("utf-8", errors="ignore")
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
                xored = bytes(b ^ 11 for b in raw)
                decoded = base64.b64decode(xored.replace(b'-', b'+').replace(b'_', b'/'))
                decomp = zlib.decompress(decoded, 15 + 32).decode("utf-8", errors="ignore")

                if "<k>customFPSTarget</k>" in decomp:
                    decomp = re.sub(r"<k>customFPSTarget</k><[ri]>[0-9.]+</[ri]>", f"<k>customFPSTarget</k><r>{target}</r>", decomp)
                else:
                    decomp = decomp.replace("<dict>", f"<dict><k>customFPSTarget</k><r>{target}</r>", 1)

                re_comp = zlib.compress(decomp.encode("utf-8"))
                re_b64 = base64.b64encode(re_comp).replace(b'+', b'-').replace(b'/', b'_')
                re_raw = bytes(b ^ 11 for b in re_b64)

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


if __name__ == "__main__":
    app = GeodeSyncApp()
    app.mainloop()

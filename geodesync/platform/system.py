"""OS helpers (moved verbatim from v2.8.0 main.py): open URLs/paths, macOS app security, VC++ redistributable, Linux process lookup, desktop entries, process waits, app-data dir."""

import os
import sys
import re
import shutil
import time
import tempfile
import urllib.request
import webbrowser
import subprocess
from geodesync.platform.process_manager import IS_MAC, IS_WIN



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


def get_app_data_dir():
    if IS_WIN:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "GeodeSync")
    if IS_MAC:
        return os.path.expanduser("~/Library/Application Support/GeodeSync")
    config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(config_home, "geodesync")

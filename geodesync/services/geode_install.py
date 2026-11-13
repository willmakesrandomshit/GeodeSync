"""Geode loader download, package validation and safe extraction (moved verbatim from v2.8.0 main.py)."""

import os
import re
import json
import shutil
import stat
import tempfile
import urllib.request
import platform
import zipfile
from pathlib import PurePosixPath
from urllib.parse import urlparse
from geodesync.core.config import GEODE_API
from geodesync.platform.process_manager import IS_MAC, IS_WIN
from geodesync.services.app_update import verify_release_asset_digest



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


def is_safe_geode_mod_id(mod_id):
    """Accept Geode's dotted author.mod identifiers, never filesystem paths."""
    return bool(re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", str(mod_id or "")))

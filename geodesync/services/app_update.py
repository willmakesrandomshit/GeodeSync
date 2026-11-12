"""GeodeSync self-update engine (moved verbatim from v2.8.0 main.py).

Release lookup, asset selection, digest-verified download, archive validation,
staged apply and the restart helper. No Tk imports: unit-testable on any OS.
"""

import base64
import hashlib
import json
import os
import platform
import posixpath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from geodesync.core.config import CONFIG_URL, GITHUB_REPO, RELEASES_API
from geodesync.platform.process_manager import IS_LINUX, IS_MAC, IS_WIN, safe_popen_command

MACOS_UPDATE_MAX_BYTES = 300 * 1024 * 1024
APP_UPDATE_MAX_BYTES = 500 * 1024 * 1024


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


def _synthesize_release_for_tag(tag, published_at=None, html_url=None):
    clean_tag = str(tag).strip().lstrip("v")
    base_dl = f"https://github.com/{GITHUB_REPO}/releases/download/{tag}"
    known_assets = [
        ("GeodeSync-Windows.zip", 30760119),
        (f"GeodeSync-{tag}-Windows.zip", 30760119),
        (f"GeodeSync-v{clean_tag}-Windows.zip", 30760119),
        (f"GeodeSync-{clean_tag}-Windows.zip", 30760119),
        ("GeodeSync-macOS-arm64.zip", 13926612),
        ("GeodeSync-macOS-x86_64.zip", 14083968),
        (f"GeodeSync-{tag}-Linux.tar.gz", 131489),
        ("GeodeSync-Linux.tar.gz", 131489),
    ]
    assets = [
        {
            "name": name,
            "browser_download_url": f"{base_dl}/{name}",
            "size": size,
        }
        for name, size in known_assets
    ]
    return {
        "tag_name": tag,
        "name": f"GeodeSync {tag}",
        "draft": False,
        "prerelease": False,
        "published_at": published_at or "2026-11-06T21:04:22Z",
        "html_url": html_url or f"https://github.com/{GITHUB_REPO}/releases/tag/{tag}",
        "assets": assets,
    }


def fetch_latest_published_release(timeout=10, platform_name=None):
    """Return the newest stable *published release*, never a source version manifest."""
    headers = {"User-Agent": "GeodeSync-Client"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    releases = []
    # 1. Try official GitHub releases API
    try:
        request = urllib.request.Request(RELEASES_API, headers=headers)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            if isinstance(data, list):
                releases = data
    except Exception:
        pass

    # 1b. Try official GitHub latest release endpoint
    if not releases:
        try:
            latest_api = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            request = urllib.request.Request(latest_api, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
                if isinstance(data, dict) and data.get("tag_name"):
                    releases = [data]
        except Exception:
            pass

    # 2. Resilient fallback: parse releases.atom feed (public, no rate limit)
    if not releases:
        try:
            atom_url = f"https://github.com/{GITHUB_REPO}/releases.atom"
            req = urllib.request.Request(atom_url, headers={"User-Agent": "GeodeSync-Client"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.read().decode("utf-8", errors="replace"))
                for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
                    link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                    updated_el = entry.find("{http://www.w3.org/2005/Atom}updated")
                    if link_el is not None and "href" in link_el.attrib:
                        href = link_el.attrib["href"]
                        tag = href.split("/")[-1].strip()
                        if tag and version_sort_key(tag) is not None:
                            updated = updated_el.text if updated_el is not None else None
                            releases.append(_synthesize_release_for_tag(tag, published_at=updated, html_url=href))
        except Exception:
            pass

    # 3. Secondary fallback: check raw version.json manifest
    if not releases:
        try:
            req = urllib.request.Request(CONFIG_URL, headers={"User-Agent": "GeodeSync-Client"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                cfg = json.loads(resp.read().decode("utf-8"))
                app_v = str(cfg.get("app_version", "")).strip()
                if app_v and version_sort_key(app_v) is not None:
                    tag = f"v{app_v.lstrip('v')}"
                    releases.append(_synthesize_release_for_tag(tag))
        except Exception:
            pass

    # 4. Final fallback: follow redirect on /releases/latest
    if not releases:
        try:
            latest_url = f"https://github.com/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(latest_url, headers={"User-Agent": "GeodeSync-Client"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                final_url = resp.geturl()
                tag = final_url.split("/")[-1].strip()
                if tag and version_sort_key(tag) is not None:
                    releases.append(_synthesize_release_for_tag(tag, html_url=final_url))
        except Exception:
            pass

    if not releases:
        raise ValueError("Could not connect to GitHub to check for published updates.")

    stable = []
    for release in releases:
        if not isinstance(release, dict) or release.get("draft") or release.get("prerelease") or not release.get("published_at"):
            continue
        tag = str(release.get("tag_name", "")).strip()
        key = version_sort_key(tag)
        if key is not None:
            if platform_name:
                try:
                    if not release_has_app_update(release, platform_name):
                        continue
                except Exception:
                    pass
            stable.append((key, release))
    if stable:
        return max(stable, key=lambda item: item[0])[1]
    raise ValueError("GitHub has no published stable GeodeSync release.")


def verify_release_asset_digest(asset, data, label):
    digest = str(asset.get("digest") or "")
    if not digest.startswith("sha256:") or len(digest) != 71:
        raise ValueError(f"GitHub did not provide a usable SHA-256 digest for {label}.")
    expected = digest[7:].lower()
    if any(char not in "0123456789abcdef" for char in expected):
        raise ValueError(f"GitHub provided an invalid SHA-256 digest for {label}.")
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"The downloaded {label} failed its SHA-256 integrity check.")


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
        clean_tag = tag.lstrip("v")
        candidates = [
            "GeodeSync-Windows.zip",
            f"GeodeSync-{tag}-Windows.zip",
            f"GeodeSync-v{clean_tag}-Windows.zip",
            f"GeodeSync-{clean_tag}-Windows.zip",
        ]
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
    except (FileNotFoundError, ValueError):
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
            safe_popen_command([executable], close_fds=True)
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
    """Remove the temporary Windows helper after the OS releases its files without opening any console window."""
    name = os.path.basename(work_dir)
    if not re.fullmatch(r"\.GeodeSync-update-[A-Za-z0-9_-]+", name):
        raise ValueError("The temporary update folder name is invalid.")
    script = os.path.join(parent, f".GeodeSync-cleanup-{name.rsplit('-', 1)[-1]}.vbs")
    target_path = os.path.join(parent, name).replace("\\", "\\\\")
    vbs_content = (
        'Set fso = CreateObject("Scripting.FileSystemObject")\r\n'
        f'target = "{target_path}"\r\n'
        'scriptFile = WScript.ScriptFullName\r\n'
        'For i = 1 To 20\r\n'
        '    WScript.Sleep 1000\r\n'
        '    If fso.FolderExists(target) Then\r\n'
        '        On Error Resume Next\r\n'
        '        fso.DeleteFolder target, True\r\n'
        '        On Error GoTo 0\r\n'
        '    Else\r\n'
        '        Exit For\r\n'
        '    End If\r\n'
        'Next\r\n'
        'On Error Resume Next\r\n'
        'fso.DeleteFile scriptFile, True\r\n'
    )
    with open(script, "w", encoding="utf-8", newline="") as stream:
        stream.write(vbs_content)
    try:
        safe_popen_command(
            ["wscript.exe", "//nologo", script],
            cwd=parent,
            extra_flags=getattr(subprocess, "DETACHED_PROCESS", 0x00000008),
        )
    except Exception:
        pass


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

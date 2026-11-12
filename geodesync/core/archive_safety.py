"""Safe ZIP handling for Geode packages: reject traversal, links, device names and zip bombs; install transactionally."""
from __future__ import annotations

import os
import re
import shutil
import stat
import tempfile
from pathlib import PurePosixPath

MAX_EXPANDED_BYTES = 500 * 1024 * 1024
_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"{p}{n}" for p in ("COM", "LPT") for n in range(1, 10)}


def is_safe_mod_id(mod_id) -> bool:
    """Geode's dotted `author.mod` identifiers only, never filesystem paths."""
    return bool(re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", str(mod_id or "")))


def member_target(root: str, info) -> str:
    name = info.filename
    if not name or "\\" in name or "\x00" in name:
        raise ValueError("The Geode package contains an invalid archive path.")
    member = PurePosixPath(name)
    if member.is_absolute() or any(part in ("", ".", "..") for part in member.parts):
        raise ValueError("The Geode package contains an unsafe archive path.")
    if any(":" in part or part.endswith((" ", ".")) or part.split(".", 1)[0].upper() in _RESERVED for part in member.parts):
        raise ValueError("The Geode package contains an unsafe destination filename.")
    kind = stat.S_IFMT((info.external_attr >> 16) & 0xFFFF)
    if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
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
    if info.file_size < 0 or info.file_size > MAX_EXPANDED_BYTES:
        raise ValueError("The Geode package contains an oversized file.")
    return target


def validate_package(archive, root: str):
    """Validate every member up front and cap total expansion. Returns [(info, target)] for regular files."""
    total, files, seen = 0, [], set()
    for info in archive.infolist():
        target = member_target(root, info)
        key = os.path.normcase(target)
        if key in seen:
            raise ValueError("The Geode package contains duplicate destination paths.")
        seen.add(key)
        total += info.file_size
        if total > MAX_EXPANDED_BYTES:
            raise ValueError("The Geode package expands beyond the allowed size.")
        if not info.is_dir():
            files.append((info, target))
    if not files:
        raise ValueError("The Geode package contains no installable files.")
    return files


def extract_transactionally(archive, root: str) -> None:
    """Stage every file first, then swap in with per-file backups; any failure rolls everything back."""
    entries = validate_package(archive, root)
    base = os.path.realpath(root)
    stage = tempfile.mkdtemp(prefix=".geodesync-geode-stage-", dir=base)
    incoming, previous, installed = os.path.join(stage, "incoming"), os.path.join(stage, "previous"), []
    try:
        for info, dest in entries:
            rel = os.path.relpath(dest, base)
            staged = os.path.join(incoming, rel)
            os.makedirs(os.path.dirname(staged), exist_ok=True)
            with archive.open(info, "r") as src, open(staged, "wb") as out:
                shutil.copyfileobj(src, out, length=1024 * 1024)
            mode = (info.external_attr >> 16) & 0o777
            if mode:
                os.chmod(staged, mode & 0o755)
        for _info, dest in entries:
            if os.path.lexists(dest) and not os.path.isfile(dest):
                raise ValueError("The Geode package conflicts with a non-file in the game folder.")
            rel = os.path.relpath(dest, base)
            staged, backup = os.path.join(incoming, rel), os.path.join(previous, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            had = os.path.isfile(dest)
            if had:
                os.makedirs(os.path.dirname(backup), exist_ok=True)
                os.replace(dest, backup)
            try:
                os.replace(staged, dest)
            except Exception:
                if had and os.path.exists(backup):
                    os.replace(backup, dest)
                raise
            installed.append((dest, backup if had else None))
    except Exception:
        for dest, backup in reversed(installed):
            try:
                if os.path.lexists(dest):
                    os.remove(dest)
                if backup and os.path.exists(backup):
                    os.replace(backup, dest)
            except OSError:
                pass
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)

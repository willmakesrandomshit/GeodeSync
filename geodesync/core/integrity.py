"""Integrity helpers: release digests and crash-safe JSON writes."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile


def verify_release_asset_digest(asset: dict, data: bytes, label: str) -> None:
    """Check bytes against the sha256 digest GitHub publishes for a release asset."""
    digest = str(asset.get("digest") or "")
    if not digest.startswith("sha256:") or len(digest) != 71:
        raise ValueError(f"GitHub did not provide a usable SHA-256 digest for {label}.")
    expected = digest[7:].lower()
    if any(c not in "0123456789abcdef" for c in expected):
        raise ValueError(f"GitHub provided an invalid SHA-256 digest for {label}.")
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"The downloaded {label} failed its SHA-256 integrity check.")


def atomic_write_json(path: str, value) -> None:
    """Write JSON so a crash or power loss can never leave a half-written file."""
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".geodesync-write-", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.flush()
            try:
                os.fsync(stream.fileno())
            except OSError:
                pass
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass

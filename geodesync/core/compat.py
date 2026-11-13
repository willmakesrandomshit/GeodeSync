"""v2.8.0 public helpers kept for compatibility: save wrapper codec and the official release page check."""

import base64
import zlib
from geodesync.core.config import GITHUB_REPO



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

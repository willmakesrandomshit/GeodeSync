"""Geometry Dash save-file wrapper: XOR 0x0B -> URL-safe Base64 -> zlib."""
from __future__ import annotations

import base64
import zlib

_XOR = 0x0B


def decode(raw: bytes) -> bytes:
    encoded = bytes(b ^ _XOR for b in raw)
    return zlib.decompress(base64.urlsafe_b64decode(encoded), 15 + 32)


def encode(xml_data: bytes) -> bytes:
    return bytes(b ^ _XOR for b in base64.urlsafe_b64encode(zlib.compress(xml_data)))

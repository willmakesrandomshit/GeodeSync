"""Release-version comparison. Strict numeric versions only; anything else never counts as newer."""
from __future__ import annotations

import re

_VERSION = re.compile(r"\d+(?:\.\d+)*")


def parse_version(version) -> tuple[int, ...] | None:
    v = str(version or "").strip().lstrip("v")
    if not _VERSION.fullmatch(v):
        return None
    return tuple(int(p) for p in v.split("."))


def is_newer(candidate, current) -> bool:
    """True only when `candidate` is strictly newer; missing or malformed versions never offer an update."""
    a, b = parse_version(candidate), parse_version(current)
    if a is None or b is None:
        return False
    width = max(len(a), len(b))
    pad = lambda t: t + (0,) * (width - len(t))
    return pad(a) > pad(b)


def sort_key(version) -> tuple[int, ...] | None:
    parts = parse_version(version)
    return None if parts is None else parts + (0,) * max(0, 8 - len(parts))

"""Linux-only guard: some colour-emoji glyphs crash Tk 8.6 (Xft) with a segmentation fault.

On Linux, text options passed to any Tk widget have astral-plane characters (emoji such as U+1F3B5) and
joiner/variation selectors removed. Other platforms are untouched.
"""
import re
import sys
import tkinter as tk

_ASTRAL = re.compile("[\U00010000-\U0010ffff‍️]")
_installed = False


def sanitize_text(value):
    if not isinstance(value, str):
        return value
    cleaned = _ASTRAL.sub("", value)
    return cleaned.lstrip(" ") if cleaned != value else value


def install():
    """Wrap tkinter's option builder once. Returns True if the guard was installed."""
    global _installed
    if _installed or not sys.platform.startswith("linux"):
        return False
    original = tk.Misc._options

    def _options(self, cnf, kw=None):
        res = original(self, cnf, kw)
        if not res:
            return res
        items = list(res)
        for i in range(0, len(items) - 1, 2):
            if items[i] in ("-text", "-label"):
                items[i + 1] = sanitize_text(items[i + 1])
        return tuple(items)

    tk.Misc._options = _options
    _installed = True
    return True

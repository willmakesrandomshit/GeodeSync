"""Test helper: platform flags (IS_WIN/IS_MAC/IS_LINUX) are module globals, and v3 spreads code over several modules.

patch_flag patches the flag everywhere it exists (main plus every geodesync module) so a test can say
"pretend this is Windows" once, the way it could when everything lived in main.py.
"""
import contextlib
import sys
from unittest import mock


@contextlib.contextmanager
def patch_flag(name, value):
    with contextlib.ExitStack() as stack:
        for key, module in list(sys.modules.items()):
            if module is None or not (key == "main" or key.startswith("geodesync")):
                continue
            if name in getattr(module, "__dict__", {}):
                stack.enter_context(mock.patch.object(module, name, value))
        yield

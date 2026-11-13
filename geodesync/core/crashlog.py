"""Crash log location and the global excepthook (moved verbatim from v2.8.0 main.py)."""

import os
import sys
import traceback
import time



def _crash_log_path():
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "GeodeSync", "crash.log")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Logs/GeodeSync/crash.log")
    state_home = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return os.path.join(state_home, "geodesync", "crash.log")


def _global_excepthook(exc_type, exc_value, exc_traceback):
    try:
        crash_path = _crash_log_path()
        app_dir = os.path.dirname(crash_path)
        os.makedirs(app_dir, exist_ok=True)
        import time
        with open(crash_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- CRASH AT {time.ctime()} ---\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    except Exception:
        pass

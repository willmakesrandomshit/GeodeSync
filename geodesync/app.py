"""Application entry point: update-helper mode or the Tk app, with crash logging."""
import os
import sys
import time
import traceback


def run(argv=None):
    argv = sys.argv if argv is None else argv
    from geodesync.services.app_update import _run_update_helper

    if len(argv) == 3 and argv[1] == "--geodesync-apply-update":
        _run_update_helper(argv[2])
        raise SystemExit(0)
    from geodesync.core.crashlog import _crash_log_path
    from geodesync.ui.app import GeodeSyncApp

    try:
        app = GeodeSyncApp()
        app.mainloop()
    except Exception:
        try:
            crash_path = _crash_log_path()
            os.makedirs(os.path.dirname(crash_path), exist_ok=True)
            with open(crash_path, "a", encoding="utf-8") as f:
                f.write(f"\n--- MAINLOOP CRASH AT {time.ctime()} ---\n")
                traceback.print_exc(file=f)
        except Exception:
            pass
        raise

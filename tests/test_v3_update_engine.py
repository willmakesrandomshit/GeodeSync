"""v3 migration step 2: the self-update engine and process helpers live in the package.

main.py re-exports them, so these tests pin that there is exactly one
implementation (no drift between copies) and that the engine has no UI imports.
"""
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import main  # noqa: E402
from geodesync.core import config  # noqa: E402
from geodesync.platform import process_manager  # noqa: E402
from geodesync.services import app_update  # noqa: E402

UPDATE_NAMES = [
    "is_newer_app_version", "version_sort_key", "fetch_latest_published_release", "verify_release_asset_digest",
    "select_macos_update_asset", "verify_macos_update_digest", "select_app_update_asset", "release_has_app_update",
    "validate_app_update_zip", "safe_extract_app_zip", "download_verified_app_update", "mark_windows_download",
    "mark_macos_quarantine", "validate_app_update_tar", "validate_macos_update_zip", "_apply_staged_update",
    "_run_update_helper", "_wait_for_process_exit", "_application_root",
    "MACOS_UPDATE_MAX_BYTES", "APP_UPDATE_MAX_BYTES",
]
PROCESS_NAMES = [
    "get_silent_startupinfo", "get_silent_creationflags", "safe_run_command", "safe_check_output",
    "safe_popen_command", "is_win_process_running",
]


class SingleImplementationTests(unittest.TestCase):
    def test_main_reexports_the_package_update_engine(self):
        for name in UPDATE_NAMES:
            with self.subTest(name=name):
                self.assertIs(getattr(main, name), getattr(app_update, name))

    def test_main_reexports_the_package_process_helpers(self):
        for name in PROCESS_NAMES:
            with self.subTest(name=name):
                self.assertIs(getattr(main, name), getattr(process_manager, name))

    def test_main_no_longer_defines_moved_functions(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        for name in UPDATE_NAMES + PROCESS_NAMES:
            with self.subTest(name=name):
                self.assertNotIn(f"\ndef {name}(", source)

    def test_release_constants_match_between_main_and_package(self):
        # Builds read APP_VERSION from main.py; the package must not drift from it.
        for name in ("APP_VERSION", "GITHUB_REPO", "CONFIG_URL", "RELEASES_API"):
            with self.subTest(name=name):
                self.assertEqual(getattr(main, name), getattr(config, name))

    def test_platform_flags_agree(self):
        for name in ("IS_WIN", "IS_MAC", "IS_LINUX"):
            with self.subTest(name=name):
                self.assertEqual(getattr(main, name), getattr(process_manager, name))


class NoUiDependencyTests(unittest.TestCase):
    def test_update_engine_imports_without_tkinter(self):
        code = (
            "import sys, builtins\n"
            "real = builtins.__import__\n"
            "def guard(name, *a, **k):\n"
            "    if name == 'tkinter' or name.startswith('tkinter.'):\n"
            "        raise ImportError('tkinter blocked')\n"
            "    return real(name, *a, **k)\n"
            "builtins.__import__ = guard\n"
            "import geodesync.services.app_update as u\n"
            "assert u.is_newer_app_version('3.0.0', '2.8.0')\n"
            "print('ok')\n"
        )
        result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=60,
                                env={**os.environ, "PYTHONPATH": str(ROOT)})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok", result.stdout)


if __name__ == "__main__":
    unittest.main()

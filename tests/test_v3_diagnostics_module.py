"""v3 migration step 5: diagnostics live in the package, no UI imports; main re-exports them."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import main  # noqa: E402
from geodesync.services import diagnostics  # noqa: E402

NAMES = ["explain_error_text", "scan_installation_issues", "read_windows_pe_machine",
         "validate_windows_game_images", "check_folder_writable_and_space", "check_vc_redist_installed",
         "ensure_local_onedrive_files", "WINDOWS_PE_MACHINE_NAMES"]


class DiagnosticsModuleTests(unittest.TestCase):
    def test_main_reexports_package_objects(self):
        for name in NAMES:
            with self.subTest(name=name):
                self.assertIs(getattr(main, name), getattr(diagnostics, name))

    def test_main_no_longer_defines_them(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        for name in NAMES[:-1]:
            with self.subTest(name=name):
                self.assertNotIn(f"\ndef {name}(", source)

    def test_explain_error_text_gives_a_plain_answer(self):
        result = diagnostics.explain_error_text("[WinError 5] Access is denied", platform_name="win32")
        self.assertTrue(result)

    def test_imports_without_tkinter(self):
        code = ("import builtins\nreal=builtins.__import__\n"
                "def g(n,*a,**k):\n"
                "    if n=='tkinter' or n.startswith('tkinter.'): raise ImportError('blocked')\n"
                "    return real(n,*a,**k)\n"
                "builtins.__import__=g\nimport geodesync.services.diagnostics\nprint('ok')\n")
        r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()

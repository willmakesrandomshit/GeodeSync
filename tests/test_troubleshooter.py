import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import explain_error_text, scan_installation_issues


class TroubleshooterTests(unittest.TestCase):
    def test_bad_image_error_gives_exact_steam_verification_path(self):
        title, steps = explain_error_text("GeometryDash.exe - Bad Image, status 0xc000007b", "Windows")
        self.assertIn("Windows", title)
        self.assertIn("Properties → Installed Files → Verify integrity", steps)
        self.assertIn("Do not download individual DLL", steps)

    def test_onefile_python_runtime_error_points_to_complete_zip_extraction(self):
        title, steps = explain_error_text("Failed to load Python DLL from _MEI", "Windows")
        self.assertIn("did not start", title)
        self.assertIn("keep `_internal` beside `GeodeSync.exe`", steps)
        self.assertIn("not from the ZIP preview", steps)

    def test_unknown_error_does_not_invent_a_fix(self):
        title, steps = explain_error_text("A strange vendor error 927")
        self.assertEqual(title, "No matching fix found yet")
        self.assertIn("will not guess", steps)
        self.assertIn("Export Report", steps)

    def test_empty_error_asks_for_full_message(self):
        title, steps = explain_error_text("")
        self.assertEqual(title, "Paste the exact error")
        self.assertIn("code such as 0xc000007b", steps)

    def test_setup_scan_reports_missing_steam_and_game_folder(self):
        manager = SimpleNamespace(steam_path=None, gd_path=None)
        findings = scan_installation_issues(manager, is_windows=True, is_macos=False)
        titles = [finding["title"] for finding in findings]
        self.assertIn("Steam was not found", titles)
        self.assertIn("Geometry Dash folder was not found", titles)

    def test_setup_scan_keeps_recovery_warning_actionable(self):
        with tempfile.TemporaryDirectory() as temp:
            manager = SimpleNamespace(steam_path=temp, gd_path=temp)
            findings = scan_installation_issues(
                manager, is_windows=False, is_macos=False,
                recovery_error="recovery journal unreadable",
            )
        self.assertEqual(findings[-1]["title"], "An interrupted game repair needs attention")
        self.assertIn("do not start another version switch", findings[-1]["steps"])

    def test_windows_scan_reports_damaged_game_dll_with_safe_fix(self):
        with tempfile.TemporaryDirectory() as temp:
            manager = SimpleNamespace(steam_path=temp, gd_path=temp)
            with patch("main.validate_windows_game_images", return_value="DLL 'libcrypto-3-x64.dll' is damaged"):
                findings = scan_installation_issues(manager, is_windows=True, is_macos=False)
        finding = next(item for item in findings if "Windows game file" in item["title"])
        self.assertIn("libcrypto-3-x64.dll", finding["detail"])
        self.assertIn("Verify integrity of game files", finding["steps"])


if __name__ == "__main__":
    unittest.main()

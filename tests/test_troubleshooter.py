import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import (
    explain_error_text,
    inspect_macos_app_security,
    is_steam_library_game_path,
    scan_installation_issues,
)


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

    def test_macos_damaged_app_warning_does_not_recommend_bypassing_gatekeeper(self):
        title, steps = explain_error_text(
            "GeodeSync-8.app is damaged and can't be opened. You should move it to the Trash.",
            "macOS",
        )
        self.assertEqual(title, "macOS rejected the GeodeSync app")
        self.assertIn("Don’t keep deleting unrelated Trash items", steps)
        self.assertIn("If macOS instead says it cannot check", steps)
        self.assertIn("do not force it open", steps)

    def test_macos_unverified_developer_warning_points_to_user_approved_settings(self):
        title, steps = explain_error_text(
            "Apple cannot check this app for malicious software", "macOS"
        )
        self.assertEqual(title, "macOS needs your approval to open this app")
        self.assertIn("System Settings → Privacy & Security → Open Anyway", steps)
        self.assertIn("does not make the app notarized", steps)

    def test_macos_support_security_check_reports_only_summary(self):
        with tempfile.TemporaryDirectory(suffix=".app") as app:
            responses = [
                SimpleNamespace(returncode=0, stdout="", stderr=""),
                SimpleNamespace(returncode=0, stdout="", stderr="Signature=adhoc\nTeamIdentifier=not set\n"),
                SimpleNamespace(returncode=3, stdout="", stderr="rejected"),
                SimpleNamespace(returncode=0, stdout="", stderr="secret-quarantine-value"),
            ]
            with patch("main.IS_MAC", True):
                result = inspect_macos_app_security(
                    app,
                    runner=lambda *args, **kwargs: responses.pop(0),
                )
        self.assertEqual(result["bundle_signature"], "valid")
        self.assertEqual(result["signing_identity"], "ad-hoc signed (not Apple Developer ID signed)")
        self.assertEqual(result["gatekeeper"], "rejected or not assessed")
        self.assertEqual(result["quarantine"], "present")
        self.assertNotIn("secret-quarantine-value", repr(result))

    def test_geode_whoopsies_error_asks_for_full_crash_report_not_a_reset(self):
        title, steps = explain_error_text(
            "Whoopsies! An unhandled exception has occurred.", "Windows"
        )
        self.assertEqual(title, "Geode crashed")
        self.assertIn("complete report", steps)
        self.assertIn("Stack Trace", steps)
        self.assertIn("expected Steam layout", steps)
        self.assertIn("won’t identify the crash", steps)

    def test_steam_game_folder_detection_accepts_custom_windows_library_path(self):
        self.assertTrue(is_steam_library_game_path(
            r"C:\Program Files (x86)\Steam\steamapps\common\Geometry Dash" + "\\"
        ))
        self.assertTrue(is_steam_library_game_path(
            r"D:\Games\SteamLibrary\steamapps\common\Geometry Dash"
        ))
        self.assertFalse(is_steam_library_game_path(r"C:\Games\Geometry Dash"))

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

    def test_setup_scan_warns_when_game_folder_is_outside_steam_library(self):
        with tempfile.TemporaryDirectory() as steam, tempfile.TemporaryDirectory() as game:
            findings = scan_installation_issues(
                SimpleNamespace(steam_path=steam, gd_path=game),
                is_windows=True, is_macos=False,
            )
        finding = next(item for item in findings if "not clearly inside" in item["title"])
        self.assertIn("Steam", finding["steps"])
        self.assertIn("GeometryDash.exe", finding["steps"])

    def test_setup_scan_confirms_valid_steam_library_path(self):
        with tempfile.TemporaryDirectory() as temp:
            game = os.path.join(temp, "steamapps", "common", "Geometry Dash")
            os.makedirs(game)
            findings = scan_installation_issues(
                SimpleNamespace(steam_path=temp, gd_path=game),
                is_windows=True, is_macos=False,
            )
        finding = next(item for item in findings if item["title"] == "Steam Geometry Dash folder confirmed")
        self.assertIn("Geode Installer", finding["steps"])

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

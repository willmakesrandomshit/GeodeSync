import os
import sys
import json
import zipfile
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import GDManager, APP_VERSION, SIZES_22081, validate_windows_game_images, check_vc_redist_installed, check_folder_writable_and_space


class TestV230Features(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.gd_path = os.path.join(self.test_dir, "GeometryDash")
        os.makedirs(self.gd_path)
        self.mgr = GDManager()
        self.mgr.gd_path = self.gd_path

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_version_bumped(self):
        self.assertEqual(APP_VERSION, "2.6.0")

    def test_check_vc_redist_installed(self):
        ok, status, ver = check_vc_redist_installed()
        self.assertIsInstance(ok, bool)
        self.assertIsInstance(status, str)

    def test_check_folder_writable_and_space(self):
        writable, status, free_mb = check_folder_writable_and_space(self.test_dir)
        self.assertTrue(writable)
        self.assertEqual(status, "OK")
        self.assertGreater(free_mb, 0)

    def test_custom_save_path_override(self):
        custom_save = os.path.join(self.test_dir, "CustomSaves")
        os.makedirs(custom_save, exist_ok=True)
        self.mgr.custom_save_path = custom_save
        self.assertEqual(self.mgr.get_save_data_dir(), custom_save)

    def test_portable_save_discovery(self):
        self.mgr.custom_save_path = None
        portable_save = os.path.join(self.gd_path, "save")
        os.makedirs(portable_save, exist_ok=True)
        with open(os.path.join(portable_save, "CCGameManager.dat"), "wb") as f:
            f.write(b"MOCK_SAVE")
        with patch("main.IS_MAC", False), patch("main.IS_WIN", True), patch.dict(os.environ, {"LOCALAPPDATA": os.path.join(self.test_dir, "EmptyAppData")}):
            found = self.mgr.get_save_data_dir()
            self.assertEqual(found, portable_save)

    def test_find_all_gd_installations(self):
        # Create a mock secondary GD installation
        alt_root = os.path.join(self.test_dir, "OneDrive", "Games", "GD")
        os.makedirs(alt_root, exist_ok=True)
        with open(os.path.join(alt_root, "GeometryDash.exe"), "wb") as f:
            f.truncate(10698752)

        with patch("main.IS_WIN", True), patch.dict(os.environ, {"OneDrive": os.path.join(self.test_dir, "OneDrive")}):
            installs = self.mgr.find_all_gd_installations()
            paths = [i["path"].lower() for i in installs]
            self.assertTrue(any("gd" in p for p in paths))

    def test_gd_22081_binary_size_recognition(self):
        """Ensures both 10698752 and 10700288 byte executables are recognized as 2.2081."""
        exe_path = os.path.join(self.gd_path, "GeometryDash.exe")
        with patch("main.IS_WIN", True):
            for valid_size in (10698752, 10700288):
                with open(exe_path, "wb") as f:
                    f.truncate(valid_size)
                self.assertTrue(self.mgr.is_current_gd_22081(), f"Size {valid_size} should be recognized as 2.2081")
                ver_text, color = self.mgr.get_gd_version_info()
                self.assertIn("2.2081", ver_text)
                self.assertNotIn("2.207", ver_text)

            # Invalid size (e.g. 2.209 or corrupted)
            with open(exe_path, "wb") as f:
                f.truncate(13178880)
            self.assertFalse(self.mgr.is_current_gd_22081())
            ver_text, color = self.mgr.get_gd_version_info()
            self.assertIn("2.209", ver_text)

    def test_gd_22081_depot_size_verification(self):
        """Ensures has_downloaded_depot and validate_windows_game_images accept both 2.2081 sizes."""
        depot_dir = os.path.join(self.test_dir, "depot")
        res_dir = os.path.join(depot_dir, "Resources")
        os.makedirs(res_dir, exist_ok=True)
        depot_exe = os.path.join(depot_dir, "GeometryDash.exe")
        with open(os.path.join(res_dir, "Dash.mp3"), "wb") as f:
            f.write(b"MOCK_AUDIO" * 100)
        with open(os.path.join(res_dir, "GJ_GameSheet-hd.png"), "wb") as f:
            f.write(b"MOCK_TEXTURE" * 100)
        # Pad depot total size above 150MB threshold
        with open(os.path.join(depot_dir, "large_padding.dat"), "wb") as f:
            f.truncate(160 * 1024 * 1024)

        with patch("main.IS_WIN", True), patch.object(self.mgr, "get_depot_path", return_value=depot_dir):
            for valid_size in SIZES_22081:
                with open(depot_exe, "wb") as f:
                    f.truncate(valid_size)
                self.assertTrue(self.mgr.has_downloaded_depot(), f"Depot with size {valid_size} should be valid")

    def test_check_outdated_mods(self):
        mods_dir = os.path.join(self.gd_path, "geode", "mods")
        os.makedirs(mods_dir, exist_ok=True)

        # 1. Create a mock outdated mod
        mod_zip = os.path.join(mods_dir, "test.samplemod.geode")
        with zipfile.ZipFile(mod_zip, "w") as zf:
            zf.writestr("mod.json", json.dumps({"id": "test.samplemod", "name": "Sample Mod", "version": "1.0.0"}))

        # 2. Mock API call
        fake_api_response = {
            "payload": {
                "versions": [
                    {"version": "1.2.0", "download": {"url": "https://api.geode-sdk.org/v1/mods/test.samplemod/download"}}
                ],
                "about": "A cool sample mod"
            }
        }

        with patch("urllib.request.urlopen") as mock_url:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(fake_api_response).encode("utf-8")
            mock_url.return_value.__enter__.return_value = mock_resp

            outdated = self.mgr.check_outdated_mods()
            self.assertEqual(len(outdated), 1)
            self.assertEqual(outdated[0]["id"], "test.samplemod")
            self.assertEqual(outdated[0]["current_version"], "1.0.0")
            self.assertEqual(outdated[0]["latest_version"], "1.2.0")

    def test_imageplus_crash_guard_in_updater(self):
        """Ensures imageplus 1.1.1 is never recommended by mod updater to prevent entry point crash."""
        mods_dir = os.path.join(self.gd_path, "geode", "mods")
        os.makedirs(mods_dir, exist_ok=True)

        ip_path = os.path.join(mods_dir, "prevter.imageplus.geode")
        with zipfile.ZipFile(ip_path, "w") as zf:
            zf.writestr("mod.json", json.dumps({"id": "prevter.imageplus", "name": "ImagePlus", "version": "1.1.0"}))

        fake_api_response = {
            "payload": {
                "versions": [
                    {"version": "1.1.1", "download": {"url": "https://api.geode-sdk.org/download/1.1.1"}}
                ]
            }
        }

        with patch("urllib.request.urlopen") as mock_url:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(fake_api_response).encode("utf-8")
            mock_url.return_value.__enter__.return_value = mock_resp

            outdated = self.mgr.check_outdated_mods()
            # Must be empty because 1.1.1 is blacklisted as unstable on GD 2.2081
            self.assertEqual(len(outdated), 0)

    def test_keybind_doctor_conflict_detection(self):
        cfg_dir = os.path.join(self.gd_path, "geode", "config")
        mod_a = os.path.join(cfg_dir, "mod.alpha")
        mod_b = os.path.join(cfg_dir, "mod.beta")
        os.makedirs(mod_a, exist_ok=True)
        os.makedirs(mod_b, exist_ok=True)

        # Both mods bind to Q (GLFW keycode 81)
        with open(os.path.join(mod_a, "settings.json"), "w", encoding="utf-8") as f:
            json.dump({"toggleKey": {"key": 81, "modifiers": 0}}, f)

        with open(os.path.join(mod_b, "settings.json"), "w", encoding="utf-8") as f:
            json.dump({"jumpKey": {"key": 81, "modifiers": 0}}, f)

        res = self.mgr.get_keybind_map(custom_search_dirs=[cfg_dir])
        conflicts = res.get("conflicts", {})
        self.assertIn("Q", conflicts)
        self.assertEqual(len(conflicts["Q"]), 2)

    def test_texture_pack_backup_and_restore(self):
        res_dir = os.path.join(self.gd_path, "Resources")
        os.makedirs(res_dir, exist_ok=True)

        # Vanilla textures
        vanilla_sheet = os.path.join(res_dir, "GJ_GameSheet.png")
        with open(vanilla_sheet, "wb") as f:
            f.write(b"VANILLA_TEXTURE_DATA")

        # 1. Install custom texture pack from zip
        pack_zip = os.path.join(self.test_dir, "CustomPack.zip")
        with zipfile.ZipFile(pack_zip, "w") as zf:
            zf.writestr("GJ_GameSheet.png", b"CUSTOM_TEXTURE_DATA")

        ok, msg = self.mgr.install_texture_pack(pack_zip, "CustomPack")
        self.assertTrue(ok)
        self.assertIn("CustomPack", msg)

        # Check Resources has custom texture
        with open(vanilla_sheet, "rb") as f:
            self.assertEqual(f.read(), b"CUSTOM_TEXTURE_DATA")

        # Check backup was created
        bak_sheet = os.path.join(self.gd_path, "Resources_Vanilla_Backup", "GJ_GameSheet.png")
        self.assertTrue(os.path.exists(bak_sheet))
        with open(bak_sheet, "rb") as f:
            self.assertEqual(f.read(), b"VANILLA_TEXTURE_DATA")

        # Check active status
        status = self.mgr.get_texture_pack_status()
        self.assertEqual(status["active_pack"], "CustomPack")
        self.assertTrue(status["has_backup"])

        # 2. Restore vanilla textures
        ok_res, res_msg = self.mgr.restore_vanilla_textures()
        self.assertTrue(ok_res)

        with open(vanilla_sheet, "rb") as f:
            self.assertEqual(f.read(), b"VANILLA_TEXTURE_DATA")

        status_after = self.mgr.get_texture_pack_status()
        self.assertEqual(status_after["active_pack"], "Vanilla (Default)")


if __name__ == "__main__":
    unittest.main()

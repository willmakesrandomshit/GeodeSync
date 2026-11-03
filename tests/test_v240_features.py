import os
import sys
import json
import zipfile
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import (
    GDManager,
    APP_VERSION,
    GeodeSyncApp,
    encode_geometry_dash_save,
    decode_geometry_dash_save,
)


class TestV240Features(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.gd_path = os.path.join(self.test_dir, "GeometryDash")
        os.makedirs(self.gd_path)
        self.resources_dir = os.path.join(self.gd_path, "Resources")
        os.makedirs(self.resources_dir)
        self.mods_dir = os.path.join(self.gd_path, "geode", "mods")
        os.makedirs(self.mods_dir)
        self.config_dir = os.path.join(self.gd_path, "geode", "config")
        os.makedirs(self.config_dir)
        self.save_dir = os.path.join(self.test_dir, "Saves")
        os.makedirs(self.save_dir)

        self.mgr = GDManager()
        self.mgr.gd_path = self.gd_path
        self.mgr.custom_save_path = self.save_dir

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_version_bumped_to_2_4_0(self):
        self.assertEqual(APP_VERSION, "2.4.0")

    def test_practice_music_swap_and_restore(self):
        # Create a mock StayInsideMe.mp3
        stay_inside = os.path.join(self.resources_dir, "StayInsideMe.mp3")
        with open(stay_inside, "wb") as f:
            f.write(b"ORIGINAL_VANILLA_STAY_INSIDE_ME")

        is_custom, desc = self.mgr.get_practice_music_status()
        self.assertFalse(is_custom)
        self.assertIn("Vanilla", desc)

        # Create a mock custom song
        custom_song = os.path.join(self.test_dir, "at_the_speed_of_light.mp3")
        with open(custom_song, "wb") as f:
            f.write(b"CUSTOM_PRACTICE_SONG_AT_THE_SPEED_OF_LIGHT")

        # Set custom practice music
        ok, msg = self.mgr.set_custom_practice_music(custom_song)
        self.assertTrue(ok)

        # Verify StayInsideMe.mp3.bak was created and StayInsideMe.mp3 was replaced
        bak_file = os.path.join(self.resources_dir, "StayInsideMe.mp3.bak")
        self.assertTrue(os.path.exists(bak_file))
        with open(bak_file, "rb") as f:
            self.assertEqual(f.read(), b"ORIGINAL_VANILLA_STAY_INSIDE_ME")
        with open(stay_inside, "rb") as f:
            self.assertEqual(f.read(), b"CUSTOM_PRACTICE_SONG_AT_THE_SPEED_OF_LIGHT")

        is_custom, desc = self.mgr.get_practice_music_status()
        self.assertTrue(is_custom)
        self.assertIn("Custom", desc)

        # Restore vanilla
        ok, msg = self.mgr.restore_vanilla_practice_music()
        self.assertTrue(ok)
        self.assertFalse(os.path.exists(bak_file))
        with open(stay_inside, "rb") as f:
            self.assertEqual(f.read(), b"ORIGINAL_VANILLA_STAY_INSIDE_ME")

    def test_get_local_audio_tracks(self):
        # Create some simulated downloaded mp3s in save_dir
        song1 = os.path.join(self.save_dir, "10002148.mp3")
        with open(song1, "wb") as f:
            f.write(b"x" * 1024 * 500) # 0.49MB
        song2 = os.path.join(self.save_dir, "845947.mp3")
        with open(song2, "wb") as f:
            f.write(b"x" * 1024 * 1024) # 1.0MB

        tracks = self.mgr.get_local_audio_tracks()
        self.assertEqual(len(tracks), 2)
        ids = [t["song_id"] for t in tracks]
        self.assertIn("10002148", ids)
        self.assertIn("845947", ids)

    def test_export_and_import_geodesync_bundle(self):
        # Create mock saves
        gm_path = os.path.join(self.save_dir, "CCGameManager.dat")
        ll_path = os.path.join(self.save_dir, "CCLocalLevels.dat")
        raw_xml = b'<?xml version="1.0"?><plist version="1.0" gjver="2.0"><dict><k>playerName</k><s>TestPlayer</s><k>LLM_01</k><d><k>_isArr</k><t/><k>k_0</k><d><k>k2</k><s>MyLevel</s></d></d><k>LLM_02</k><i>1</i></dict></plist>'
        enc_data = encode_geometry_dash_save(raw_xml)
        with open(gm_path, "wb") as f:
            f.write(enc_data)
        with open(ll_path, "wb") as f:
            f.write(enc_data)

        # Create mock mod
        mod_file = os.path.join(self.mods_dir, "geode.node-ids.geode")
        with zipfile.ZipFile(mod_file, "w") as zf:
            zf.writestr("mod.json", json.dumps({"id": "geode.node-ids", "version": "1.0.0"}))

        # Create mock config
        cfg_file = os.path.join(self.config_dir, "settings.json")
        with open(cfg_file, "w") as f:
            f.write('{"fps": 240}')

        # Export bundle
        bundle_dest = os.path.join(self.test_dir, "backup.geodesync")
        ok, msg = self.mgr.export_geodesync_bundle(bundle_dest)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(bundle_dest))

        # Verify bundle manifest
        with zipfile.ZipFile(bundle_dest, "r") as zf:
            self.assertIn("manifest.json", zf.namelist())
            self.assertIn("saves/CCGameManager.dat", zf.namelist())
            self.assertIn("saves/CCLocalLevels.dat", zf.namelist())
            self.assertIn("mods/geode.node-ids.geode", zf.namelist())
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            self.assertEqual(manifest["format_version"], "1.0")
            self.assertEqual(manifest["geodesync_version"], APP_VERSION)

        # Clear active directories and test import
        os.remove(gm_path)
        os.remove(ll_path)
        os.remove(mod_file)
        self.assertFalse(os.path.exists(gm_path))

        ok, msg = self.mgr.import_geodesync_bundle(bundle_dest)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(gm_path))
        self.assertTrue(os.path.exists(ll_path))
        self.assertTrue(os.path.exists(mod_file))

    def test_save_bloat_analysis_and_cleaner(self):
        # Build a CCLocalLevels.dat with 1 player-created level and 2 online downloaded cache levels
        xml = (
            '<?xml version="1.0"?><plist version="1.0" gjver="2.0"><dict>'
            '<k>LLM_01</k><d><k>_isArr</k><t/>'
            '<k>k_0</k><d><k>k2</k><s>Player Created Level</s><k>k21</k><i>2</i><k>k4</k><s>MY_CREATION_DATA</s></d>'
            '<k>k_1</k><d><k>k1</k><i>123456</i><k>k2</k><s>Cached Online Level 1</s><k>k21</k><i>1</i><k>k4</k><s>' + ('X' * 50000) + '</s></d>'
            '<k>k_2</k><d><k>k1</k><i>789012</i><k>k2</k><s>Cached Online Level 2</s><k>k21</k><i>1</i><k>k4</k><s>' + ('Y' * 50000) + '</s></d>'
            '</d><k>LLM_02</k><i>3</i></dict></plist>'
        )
        ll_path = os.path.join(self.save_dir, "CCLocalLevels.dat")
        with open(ll_path, "wb") as f:
            f.write(encode_geometry_dash_save(xml.encode("utf-8")))

        # Test Analysis
        ok, res = self.mgr.analyze_save_bloat()
        self.assertTrue(ok)
        self.assertEqual(res["total_levels"], 3)
        self.assertEqual(res["online_cached"], 2)
        self.assertEqual(res["user_created"], 1)

        # Test Cleaning
        ok, clean_res = self.mgr.clean_save_bloat(remove_online_cache=True)
        self.assertTrue(ok)
        self.assertEqual(clean_res["removed_levels"], 2)
        self.assertGreater(clean_res["old_size_bytes"], clean_res["new_size_bytes"])

        # Verify decoded result preserves user created level
        with open(ll_path, "rb") as f:
            cleaned_dec = decode_geometry_dash_save(f.read()).decode("utf-8", errors="ignore")
        self.assertIn("Player Created Level", cleaned_dec)
        self.assertNotIn("Cached Online Level 1", cleaned_dec)
        self.assertNotIn("Cached Online Level 2", cleaned_dec)

    @patch("urllib.request.urlopen")
    def test_fetch_geode_store_mods(self, mock_urlopen):
        mock_response = MagicMock()
        mock_payload = {
            "payload": {
                "data": [
                    {
                        "id": "test.cool-mod",
                        "download_count": 52000,
                        "developers": [{"display_name": "TestDev"}],
                        "tags": ["gameplay"],
                        "about": "A super cool mod",
                        "versions": [
                            {
                                "name": "Cool Mod",
                                "version": "2.1.0",
                                "description": "A super cool mod for GD",
                                "download_link": "https://example.com/test.cool-mod.geode"
                            }
                        ]
                    }
                ]
            }
        }
        mock_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        ok, mods = self.mgr.fetch_geode_store_mods(query="cool")
        self.assertTrue(ok)
        self.assertEqual(len(mods), 1)
        self.assertEqual(mods[0]["id"], "test.cool-mod")
        self.assertEqual(mods[0]["name"], "Cool Mod")
        self.assertEqual(mods[0]["version"], "2.1.0")
        self.assertEqual(mods[0]["downloads"], 52000)

    @patch("urllib.request.urlopen")
    def test_fetch_pointercrate_demons(self, mock_urlopen):
        mock_response = MagicMock()
        mock_demons = [
            {
                "position": 1,
                "name": "Tidal Wave",
                "requirement": 100,
                "video": "https://youtu.be/test",
                "publisher": {"name": "Onilink"},
                "verifier": {"name": "Zoink"}
            }
        ]
        mock_response.read.return_value = json.dumps(mock_demons).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        ok, demons = self.mgr.fetch_pointercrate_demons(limit=10)
        self.assertTrue(ok)
        self.assertEqual(len(demons), 1)
        self.assertEqual(demons[0]["position"], 1)
        self.assertEqual(demons[0]["name"], "Tidal Wave")
        self.assertEqual(demons[0]["verifier"], "Zoink")

    def test_save_slots_creation_and_switching(self):
        # Create a mock save in save_dir
        gm_path = os.path.join(self.save_dir, "CCGameManager.dat")
        raw_xml = b'<?xml version="1.0"?><plist version="1.0" gjver="2.0"><dict><k>playerName</k><s>SlotPlayer1</s><k>6</k><s>500</s></dict></plist>'
        with open(gm_path, "wb") as f:
            f.write(encode_geometry_dash_save(raw_xml))

        # Create slot
        ok, msg = self.mgr.create_save_slot("DemonGrindSlot")
        self.assertTrue(ok)
        slots = self.mgr.get_save_slots()
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["name"], "DemonGrindSlot")
        self.assertEqual(slots[0]["player_name"], "SlotPlayer1")

        # Now change the active save to simulate progress in main
        new_xml = b'<?xml version="1.0"?><plist version="1.0" gjver="2.0"><dict><k>playerName</k><s>MainPlayer2</s><k>6</k><s>1200</s></dict></plist>'
        with open(gm_path, "wb") as f:
            f.write(encode_geometry_dash_save(new_xml))

        # Switch back to DemonGrindSlot
        ok, msg = self.mgr.switch_save_slot("DemonGrindSlot")
        self.assertTrue(ok)
        with open(gm_path, "rb") as f:
            restored_dec = decode_geometry_dash_save(f.read()).decode("utf-8")
        self.assertIn("SlotPlayer1", restored_dec)

    def test_custom_sfx_swap_and_restore(self):
        explode_file = os.path.join(self.resources_dir, "explode_11.ogg")
        with open(explode_file, "wb") as f:
            f.write(b"VANILLA_EXPLOSION")

        status = self.mgr.get_custom_sfx_status()
        self.assertFalse(status["death_sfx_custom"])

        custom_sfx = os.path.join(self.test_dir, "vine_boom.ogg")
        with open(custom_sfx, "wb") as f:
            f.write(b"VINE_BOOM_DEATH_SFX")

        ok, msg = self.mgr.set_custom_death_sfx(custom_sfx)
        self.assertTrue(ok)
        status = self.mgr.get_custom_sfx_status()
        self.assertTrue(status["death_sfx_custom"])
        with open(explode_file, "rb") as f:
            self.assertEqual(f.read(), b"VINE_BOOM_DEATH_SFX")

        ok, msg = self.mgr.restore_vanilla_death_sfx()
        self.assertTrue(ok)
        with open(explode_file, "rb") as f:
            self.assertEqual(f.read(), b"VANILLA_EXPLOSION")

    def test_salvage_and_resurrect_save(self):
        # Create a historical backup directory
        bak_dir = os.path.join(self.save_dir, "GeodeSync_Save_Backups", "auto_123456")
        os.makedirs(bak_dir)
        old_gm = os.path.join(bak_dir, "CCGameManager.dat")
        raw_xml = b'<?xml version="1.0"?><plist version="1.0" gjver="2.0"><dict><k>playerName</k><s>ResurrectedHero</s><k>6</k><s>2500</s></dict></plist>'
        with open(old_gm, "wb") as f:
            f.write(encode_geometry_dash_save(raw_xml))

        candidates = self.mgr.find_salvageable_saves()
        self.assertGreaterEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["player_name"], "ResurrectedHero")

        # Corrupt the main save (write 0 bytes)
        main_gm = os.path.join(self.save_dir, "CCGameManager.dat")
        with open(main_gm, "wb") as f:
            f.write(b"")

        # Resurrect!
        ok, msg = self.mgr.resurrect_save(old_gm)
        self.assertTrue(ok)
        with open(main_gm, "rb") as f:
            resurrected_dec = decode_geometry_dash_save(f.read()).decode("utf-8")
        self.assertIn("ResurrectedHero", resurrected_dec)

    def test_apply_mod_preset(self):
        # Create 2 mods: one globed, one normal
        m1 = os.path.join(self.mods_dir, "dankmeme.globed2.geode")
        with zipfile.ZipFile(m1, "w") as zf:
            zf.writestr("mod.json", json.dumps({"id": "dankmeme.globed2", "version": "1.0.0"}))
        m2 = os.path.join(self.mods_dir, "geode.node-ids.geode")
        with zipfile.ZipFile(m2, "w") as zf:
            zf.writestr("mod.json", json.dumps({"id": "geode.node-ids", "version": "1.0.0"}))

        # Apply vanilla preset (disables all mods)
        ok, msg = self.mgr.apply_mod_preset("vanilla")
        self.assertTrue(ok)
        installed = self.mgr.get_installed_mods()
        self.assertTrue(all(not m["is_enabled"] for m in installed))

    def test_gui_dialogs_initialized(self):
        app = GeodeSyncApp()
        try:
            self.assertTrue(hasattr(app, "open_mod_store_dialog"))
            self.assertTrue(hasattr(app, "open_demonlist_browser"))
            self.assertTrue(hasattr(app, "open_jukebox_dialog"))
            self.assertTrue(hasattr(app, "open_bundle_manager_dialog"))
            self.assertTrue(hasattr(app, "open_save_optimizer_dialog"))
            self.assertTrue(hasattr(app, "open_save_slots_dialog"))
            self.assertTrue(hasattr(app, "open_soundpack_hub"))
            self.assertTrue(hasattr(app, "open_vault_helper"))
            self.assertTrue(hasattr(app, "open_corrupt_save_resurrector"))
            self.assertTrue(hasattr(app, "open_mod_presets_dialog"))
            self.assertTrue(hasattr(app, "launch_boosted_game"))
            self.assertTrue(hasattr(app, "opt_badge"))
            self.assertTrue(hasattr(app, "slots_badge"))
            self.assertTrue(hasattr(app, "sfx_badge"))
            self.assertTrue(hasattr(app, "vault_badge"))
            self.assertTrue(hasattr(app, "salvage_badge"))
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()

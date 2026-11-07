import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import GeodeSyncApp, APP_VERSION


class TestV241TabbedUI(unittest.TestCase):
    def test_version_bumped_to_2_4_2(self):
        self.assertEqual(APP_VERSION, "2.7.0")

    def test_embedded_store_safe_unpacking(self):
        app = GeodeSyncApp()
        try:
            # Simulate what caused the crash: bool or tuple in cached_store_mods
            app._cached_store_mods = [True, {"id": "test.mod", "name": "Test Mod", "version": "1.0.0"}]
            # Should not raise AttributeError: 'bool' object has no attribute 'get'
            app._render_store_cards()
            self.assertIsNotNone(app.store_cards_container)
        finally:
            app.destroy()

    def test_embedded_demonlist_safe_unpacking(self):
        app = GeodeSyncApp()
        try:
            # Simulate bool or tuple in cached_demons
            app._cached_demons = [True, {"position": 1, "name": "Acheron", "creator": "Riot", "verifier": "Zoink"}]
            # Should not raise AttributeError: 'bool' object has no attribute 'get'
            app._render_demonlist_cards()
            self.assertIsNotNone(app.demon_cards_container)
        finally:
            app.destroy()

    def test_embedded_jukebox_safe_sfx(self):
        app = GeodeSyncApp()
        try:
            # Should safely refresh without ValueError: too many values to unpack
            app._refresh_embedded_jukebox()
            self.assertTrue(hasattr(app, "jukebox_sfx_status_lbl"))
        finally:
            app.destroy()

    def test_store_category_filters(self):
        app = GeodeSyncApp()
        try:
            app._cached_store_mods = [
                {"id": "geode.node-ids", "name": "Node IDs", "version": "1.0.0", "description": "QoL tool for developers", "tags": ["qol"]},
                {"id": "dankmeme.globed", "name": "Globed", "version": "1.0.0", "description": "Online multiplayer mod", "tags": ["multiplayer"]},
                {"id": "test.custom-icons", "name": "Custom Icons", "version": "1.0.0", "description": "Cosmetic theme", "tags": ["texture"]},
            ]
            self.assertTrue(hasattr(app, "store_category_var"))
            app.store_category_var.set("multiplayer")
            app._render_store_cards()
            self.assertIsNotNone(app.store_cards_container)

            app.store_category_var.set("qol")
            app._render_store_cards()
            self.assertIsNotNone(app.store_cards_container)
        finally:
            app.destroy()

    def test_demonlist_copy_and_progress(self):
        app = GeodeSyncApp()
        try:
            app._copy_demon_info("Tidal Wave", 1)
            # Test copy did not raise
            app._cached_demons = [
                {"position": 1, "name": "Tidal Wave", "creator": "Onilink", "verifier": "Zoink", "points": 100.0, "requirement": 100, "video": "https://youtube.com/watch?v=123"}
            ]
            app._render_demonlist_cards()
            self.assertIsNotNone(app.demon_cards_container)
        finally:
            app.destroy()

    def test_health_check_runner(self):
        app = GeodeSyncApp()
        try:
            self.assertTrue(hasattr(app, "run_health_check"))
            self.assertTrue(hasattr(app, "health_badge"))
            app.run_health_check()
        finally:
            app.destroy()

    def test_tabbed_navigation_system(self):
        app = GeodeSyncApp()
        try:
            self.assertIsNotNone(app.nav_frame)
            self.assertIsNotNone(app.tab_frames)
            primary_tabs = {"home", "mods", "library", "tools"}
            self.assertTrue(primary_tabs.issubset(set(app.tab_frames.keys())))
            self.assertTrue(primary_tabs.issubset(set(app.tab_buttons.keys())))

            # Test primary tab switching
            for tab_id in primary_tabs:
                app.switch_main_tab(tab_id)
                self.assertEqual(app.active_main_tab, tab_id)

            # Test backward-compatible alias navigation
            legacy_tabs = ["dashboard", "store", "demonlist", "jukebox", "saves", "toolbox"]
            for tab_id in legacy_tabs:
                app.switch_main_tab(tab_id)
                self.assertEqual(app.active_main_tab, tab_id)

            # Switch back to home
            app.switch_main_tab("home")
            self.assertEqual(app.active_main_tab, "home")

            # Verify embedded components exist
            self.assertTrue(hasattr(app, "store_scroll"))
            self.assertTrue(hasattr(app, "demon_scroll"))
            self.assertTrue(hasattr(app, "jukebox_prac_status_lbl"))
            self.assertTrue(hasattr(app, "saves_slots_status_lbl"))
        finally:
            app.destroy()

    def test_help_center_and_auto_find_gd(self):
        app = GeodeSyncApp()
        try:
            self.assertTrue(hasattr(app, "open_get_help_center"))
            self.assertTrue(hasattr(app, "auto_find_and_set_gd"))
        finally:
            app.destroy()

    def test_smart_guide_states(self):
        import tempfile
        import shutil
        app = GeodeSyncApp()
        temp_gd = tempfile.mkdtemp()
        try:
            # Case 1: GD missing
            app.mgr.gd_path = None
            app.update_smart_guide(has_geode=False, is_locked=False)
            self.assertIn("couldn't find", app.guide_title.cget("text").lower())
            self.assertIn("Find Geometry Dash Automatically", app.primary_btn.text)

            # Case 2: GD found, Geode missing
            app.mgr.gd_path = temp_gd
            app.update_smart_guide(has_geode=False, is_locked=False)
            self.assertIn("Install the Geode", app.guide_title.cget("text"))

            # Case 3: Ready, unlocked
            app.mgr.is_current_gd_22081 = lambda: True
            app.update_smart_guide(has_geode=True, is_locked=False)
            self.assertIn("Tip", app.guide_desc.cget("text"))

            # Case 4: Ready, locked
            app.update_smart_guide(has_geode=True, is_locked=True)
            self.assertIn("safely locked", app.guide_desc.cget("text"))
        finally:
            app.destroy()
            shutil.rmtree(temp_gd, ignore_errors=True)

    def test_diagnostic_self_repair_and_snapshot(self):
        import tempfile
        import shutil
        app = GeodeSyncApp()
        td = tempfile.mkdtemp()
        try:
            save_d = os.path.join(td, "SaveDir")
            os.makedirs(save_d, exist_ok=True)
            with open(os.path.join(save_d, "CCGameManager.dat"), "wb") as f:
                f.write(b"mock_save_data")
            app.mgr.get_save_data_dir = lambda: save_d

            # Test safety snapshot
            snap_dir = app.mgr.create_safety_snapshot("test_snap")
            self.assertIsNotNone(snap_dir)
            self.assertTrue(os.path.exists(os.path.join(snap_dir, "CCGameManager.dat")))

            # Test non-interactive safe emergency_unstick
            app.emergency_unstick(interactive=False)
            self.assertEqual(app.mgr.target_gd_version, "2.2081")
        finally:
            app.destroy()
            shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

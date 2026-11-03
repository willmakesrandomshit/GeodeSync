import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import GeodeSyncApp, APP_VERSION


class TestV241TabbedUI(unittest.TestCase):
    def test_version_bumped_to_2_4_1(self):
        self.assertEqual(APP_VERSION, "2.4.1")

    def test_tabbed_navigation_system(self):
        app = GeodeSyncApp()
        try:
            self.assertIsNotNone(app.nav_frame)
            self.assertIsNotNone(app.tab_frames)
            expected_tabs = {"dashboard", "store", "demonlist", "jukebox", "saves", "toolbox"}
            self.assertEqual(set(app.tab_frames.keys()), expected_tabs)
            self.assertEqual(set(app.tab_buttons.keys()), expected_tabs)

            # Test tab switching
            for tab_id in expected_tabs:
                app.switch_main_tab(tab_id)
                self.assertEqual(app.active_main_tab, tab_id)

            # Switch back to dashboard
            app.switch_main_tab("dashboard")
            self.assertEqual(app.active_main_tab, "dashboard")

            # Verify embedded components exist
            self.assertTrue(hasattr(app, "store_scroll"))
            self.assertTrue(hasattr(app, "demon_scroll"))
            self.assertTrue(hasattr(app, "jukebox_prac_status_lbl"))
            self.assertTrue(hasattr(app, "saves_slots_status_lbl"))
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()

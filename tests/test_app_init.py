import unittest
from main import GeodeSyncApp


class TestAppInit(unittest.TestCase):
    def test_app_init_and_refresh_status(self):
        # Verify that GeodeSyncApp initializes, sets up widgets, and runs refresh_status without error
        app = GeodeSyncApp()
        try:
            self.assertIsNotNone(app.mgr)
            self.assertIsNotNone(app.geode_badge)
            self.assertIsNotNone(app.player_card)
            self.assertIsNotNone(app.launch_btn)
            app.refresh_status()
            stats = app.mgr.get_player_stats()
            # If user has GD saves, verify dict structure
            if stats:
                self.assertIn("name", stats)
                self.assertIn("stars", stats)
                self.assertIn("demons", stats)
            mods = app.mgr.get_installed_mods()
            self.assertIsInstance(mods, list)
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()

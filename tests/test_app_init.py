import unittest
from main import GeodeSyncApp


class TestAppInit(unittest.TestCase):
    def test_app_init_and_refresh_status(self):
        # Verify that GeodeSyncApp initializes, sets up widgets, and runs refresh_status without error
        app = GeodeSyncApp()
        try:
            self.assertIsNotNone(app.mgr)
            self.assertIsNotNone(app.geode_badge)
            app.refresh_status()
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()

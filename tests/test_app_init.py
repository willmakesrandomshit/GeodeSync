import unittest
import tkinter as tk
from main import GeodeSyncApp


class TestAppInit(unittest.TestCase):
    @staticmethod
    def _all_widgets(widget):
        yield widget
        for child in widget.winfo_children():
            yield from TestAppInit._all_widgets(child)

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

    def test_tool_categories_switch_without_losing_actions(self):
        app = GeodeSyncApp()
        try:
            def button_named(name):
                return next(
                    widget for widget in self._all_widgets(app)
                    if isinstance(widget, tk.Button) and widget.cget("text") == name
                )

            button_named("Mods & play").invoke()
            visible_text = {widget.cget("text") for widget in self._all_widgets(app) if isinstance(widget, tk.Button)}
            self.assertIn("🧩 Mod Manager", visible_text)
            self.assertNotIn("💾 Backup Saves", visible_text)

            button_named("Repair & saves").invoke()
            visible_text = {widget.cget("text") for widget in self._all_widgets(app) if isinstance(widget, tk.Button)}
            self.assertIn("💾 Backup Saves", visible_text)
            self.assertIn("🩹 Crash Doctor", visible_text)
            self.assertNotIn("🧩 Mod Manager", visible_text)

            button_named("Settings & updates").invoke()
            visible_text = {widget.cget("text") for widget in self._all_widgets(app) if isinstance(widget, tk.Button)}
            self.assertIn("Auto-Backup: ON", visible_text)
            self.assertIn("🔄 Check for Updates", visible_text)
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()

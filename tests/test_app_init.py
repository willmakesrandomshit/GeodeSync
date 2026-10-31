import unittest
import tkinter as tk
import faulthandler
from main import GeodeSyncApp

faulthandler.enable(all_threads=True)


class TestAppInit(unittest.TestCase):
    @staticmethod
    def _all_widgets(widget):
        yield widget
        for child in widget.winfo_children():
            yield from TestAppInit._all_widgets(child)

    def test_app_init_and_refresh_status(self):
        # Verify that GeodeSyncApp initializes, sets up widgets, and runs refresh_status without error
        print("GUI init: constructing app", flush=True)
        app = GeodeSyncApp()
        try:
            print("GUI init: app constructed", flush=True)
            self.assertIsNotNone(app.mgr)
            self.assertIsNotNone(app.geode_badge)
            self.assertIsNotNone(app.player_card)
            self.assertIsNotNone(app.launch_btn)
            print("GUI init: refreshing status", flush=True)
            app.refresh_status()
            print("GUI init: status refreshed", flush=True)
            stats = app.mgr.get_player_stats()
            # If user has GD saves, verify dict structure
            if stats:
                self.assertIn("name", stats)
                self.assertIn("stars", stats)
                self.assertIn("demons", stats)
            mods = app.mgr.get_installed_mods()
            self.assertIsInstance(mods, list)
        finally:
            print("GUI init: destroying app", flush=True)
            app.destroy()
            print("GUI init: app destroyed", flush=True)

    def test_tool_sections_keep_all_actions_visible(self):
        app = GeodeSyncApp()
        try:
            widgets = list(self._all_widgets(app))
            labels = {widget.cget("text") for widget in widgets if isinstance(widget, tk.Label)}
            buttons = {widget.cget("text") for widget in widgets if isinstance(widget, tk.Button)}

            self.assertTrue({"MODS & PLAY", "REPAIR & SAVES", "SETTINGS & UPDATES"}.issubset(labels))
            self.assertTrue({"🧩 Mod Manager", "💾 Backup Saves", "🩹 Crash Doctor", "Auto-Backup: ON"}.issubset(buttons))
            self.assertEqual(sum(1 for widget in widgets if isinstance(widget, tk.Button) and widget.cget("text") in {
                "🧩 Mod Manager", "🔄 Update Mods", "📦 Essential Mods", "🎵 NONG Songs",
                "🎨 Texture Packs", "⚡ FPS Unlocker", "📈 Demon Tracker", "🎮 Game Profiles",
                "💾 Backup Saves", "🩺 Save Doctor", "🩹 Crash Doctor", "🧹 Cache Cleaner",
                "⚠️ Restore Steam GD", "📁 Choose Game Folder", "Auto-Backup: ON",
                "🎮 Discord RPC: ON", "🔇 GD Sounds: OFF", "🌙 Close to System Tray: ON",
                "🔄 Check for Updates", "📌 Desktop Shortcut",
            }), 20)
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()

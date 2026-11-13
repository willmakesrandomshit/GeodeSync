import sys
import unittest
import tkinter as tk
from main import GeodeSyncApp
from geodesync.ui.linux_text import sanitize_text


def _shown(names):
    """Button text as the user sees it: on Linux emoji are stripped (see geodesync/ui/linux_text.py)."""
    if sys.platform.startswith("linux"):
        return {sanitize_text(n) for n in names}
    return set(names)


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

    def test_tool_grid_groups_all_actions_by_task(self):
        app = GeodeSyncApp()
        try:
            widgets = list(self._all_widgets(app))
            labels = {widget.cget("text") for widget in widgets if isinstance(widget, tk.Label)}
            buttons = {widget.cget("text") for widget in widgets if isinstance(widget, tk.Button)}

            self.assertTrue({"TOOLBOX", "Choose what you want to do", "MODS", "PLAY", "REPAIR", "PREFERENCES", "APP"}.issubset(labels))
            self.assertTrue(_shown({"🧩 Mod Manager", "💾 Backup Saves", "🩹 Crash Doctor"}).issubset(buttons))
            self.assertTrue("Auto-Backup: ON" in buttons or "Auto-Backup: OFF" in buttons)
            tool_names = _shown({
                "🧩 Mod Manager", "🔄 Update Mods", "📦 Essential Mods", "🎵 NONG Songs",
                "📈 Demon Tracker", "⚡ FPS Unlocker", "🎨 Texture Packs", "🎮 Game Profiles",
                "💾 Backup Saves", "🩺 Save Doctor", "🩹 Crash Doctor", "🧹 Cache Cleaner",
                "Auto-Backup: ON" if app.auto_backup_enabled else "Auto-Backup: OFF", "🎮 Discord RPC: ON", "🔊 GD Sounds: ON" if app.sounds_enabled else "🔇 GD Sounds: OFF",
                "🌙 Close to System Tray: ON", "🔄 Check for Updates", "⌨️ Keybind Doctor",
                "⚠️ Restore Steam GD", "📌 Desktop Shortcut",
            })
            self.assertEqual(len(buttons.intersection(tool_names)), 20)
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()

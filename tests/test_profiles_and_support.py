import os
import tempfile
import unittest
from unittest import mock

from main import GeodeSyncApp


class GameProfileSafetyTests(unittest.TestCase):
    def make_app(self, mods_dir):
        app = GeodeSyncApp.__new__(GeodeSyncApp)
        app.get_mods_dir = lambda: mods_dir
        app.log = mock.Mock()
        return app

    def test_missing_profile_mod_does_not_partially_change_installed_mods(self):
        with tempfile.TemporaryDirectory() as mods_dir:
            active_path = os.path.join(mods_dir, "current.geode")
            with open(active_path, "w") as stream:
                stream.write("test mod")
            app = self.make_app(mods_dir)

            self.assertFalse(app._apply_active_mods(["missing.geode"]))
            self.assertTrue(os.path.exists(active_path))
            self.assertFalse(os.path.exists(active_path + ".disabled"))

    def test_failed_profile_change_rolls_earlier_mod_renames_back(self):
        with tempfile.TemporaryDirectory() as mods_dir:
            active_path = os.path.join(mods_dir, "old.geode")
            disabled_path = os.path.join(mods_dir, "wanted.geode.disabled")
            with open(active_path, "w") as stream:
                stream.write("old")
            with open(disabled_path, "w") as stream:
                stream.write("wanted")
            app = self.make_app(mods_dir)
            real_replace = os.replace
            calls = 0

            def fail_once(source, target):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated write failure")
                return real_replace(source, target)

            with mock.patch("main.os.replace", side_effect=fail_once):
                self.assertFalse(app._apply_active_mods(["wanted.geode"]))

            self.assertTrue(os.path.exists(active_path))
            self.assertFalse(os.path.exists(active_path + ".disabled"))
            self.assertTrue(os.path.exists(disabled_path))
            self.assertFalse(os.path.exists(os.path.join(mods_dir, "wanted.geode")))

    def test_support_report_redacts_private_paths_emails_and_secrets(self):
        text = (
            "/Users/alex/Library/Steam alex@example.com "
            "api_key=abc123 password: hunter2"
        )
        redacted = GeodeSyncApp._redact_diagnostic_text(text)
        self.assertNotIn("/Users/alex", redacted)
        self.assertNotIn("alex@example.com", redacted)
        self.assertNotIn("abc123", redacted)
        self.assertNotIn("hunter2", redacted)
        self.assertIn("[REDACTED]", redacted)


if __name__ == "__main__":
    unittest.main()

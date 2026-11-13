import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from geodesync.ui import linux_text  # noqa: E402


class LinuxTextGuardTests(unittest.TestCase):
    def test_sanitize_removes_emoji_and_joiners_only(self):
        self.assertEqual(linux_text.sanitize_text("\U0001f3b5 NONG Songs"), "NONG Songs")
        self.assertEqual(linux_text.sanitize_text("Update ✓ ok"), "Update ✓ ok")  # BMP symbols are kept
        self.assertEqual(linux_text.sanitize_text("\U0001f468‍\U0001f4bb Dev"), "Dev")
        self.assertEqual(linux_text.sanitize_text("plain"), "plain")
        self.assertEqual(linux_text.sanitize_text(5), 5)

    def test_install_is_a_no_op_off_linux(self):
        import unittest.mock as mock
        with mock.patch.object(linux_text, "_installed", False), mock.patch.object(sys, "platform", "darwin"):
            self.assertFalse(linux_text.install())


if __name__ == "__main__":
    unittest.main()

"""v3 migration step 3: Steam helpers and the transactional installer live in the package; main re-exports them."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import main  # noqa: E402
from geodesync.platform import steam  # noqa: E402
from geodesync.services import install_transaction as tx  # noqa: E402

STEAM_NAMES = ["should_apply_downloaded_depot", "is_steam_library_game_path", "discover_linux_steam_roots",
               "discover_steam_game_folders", "find_macos_game_app", "validate_macos_game_app",
               "reset_invalid_macos_depot_cache", "request_macos_steam_launch", "APP_ID"]
TX_NAMES = ["install_depot_transactionally", "recover_pending_install_transactions", "safe_copy_item",
            "atomic_write_json"]


class SingleImplementationTests(unittest.TestCase):
    def test_main_reexports_package_objects(self):
        for mod, names in ((steam, STEAM_NAMES), (tx, TX_NAMES)):
            for name in names:
                with self.subTest(name=name):
                    self.assertIs(getattr(main, name), getattr(mod, name))

    def test_main_no_longer_defines_moved_functions(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        for name in STEAM_NAMES + TX_NAMES:
            with self.subTest(name=name):
                self.assertNotIn(f"\ndef {name}(", source)


class BehaviourTests(unittest.TestCase):
    def test_depot_gate_ignores_logs(self):
        self.assertFalse(steam.should_apply_downloaded_depot(True, False))
        self.assertTrue(steam.should_apply_downloaded_depot(False, True))

    def test_atomic_write_json_round_trips_and_leaves_no_temp_files(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "state.json"
            tx.atomic_write_json(str(p), {"a": 1})
            self.assertEqual(json.loads(p.read_text()), {"a": 1})
            self.assertEqual([x.name for x in Path(d).iterdir()], ["state.json"])

    def test_install_replaces_destination_and_recovery_is_clean(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d) / "depot", Path(d) / "game"
            (src / "sub").mkdir(parents=True)
            (src / "a.txt").write_text("new")
            (src / "sub" / "b.txt").write_text("b")
            dst.mkdir()
            (dst / "a.txt").write_text("old")
            tx.install_depot_transactionally(str(src), str(dst))
            self.assertEqual((dst / "a.txt").read_text(), "new")
            self.assertEqual((dst / "sub" / "b.txt").read_text(), "b")
            tx.recover_pending_install_transactions(str(dst))
            self.assertEqual((dst / "a.txt").read_text(), "new")

    def test_no_tkinter_dependency(self):
        for mod in (steam, tx):
            self.assertNotIn("tkinter", Path(mod.__file__).read_text())


if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import unittest
from unittest import mock

from main import (
    atomic_write_json,
    install_depot_transactionally,
    recover_pending_install_transactions,
)


class SafeGameSwitchTests(unittest.TestCase):
    def write(self, path, contents):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as stream:
            stream.write(contents)

    def read(self, path):
        with open(path, "r", encoding="utf-8") as stream:
            return stream.read()

    def test_successfully_stages_and_replaces_depot_entries(self):
        with tempfile.TemporaryDirectory() as root:
            source = os.path.join(root, "depot")
            destination = os.path.join(root, "game")
            os.makedirs(source)
            os.makedirs(destination)
            self.write(os.path.join(source, "GeometryDash.exe"), "new game")
            self.write(os.path.join(source, "Resources", "data.bin"), "new resources")
            self.write(os.path.join(destination, "GeometryDash.exe"), "old game")
            self.write(os.path.join(destination, "Resources", "old.bin"), "preserved other file")

            install_depot_transactionally(source, destination)

            self.assertEqual(self.read(os.path.join(destination, "GeometryDash.exe")), "new game")
            self.assertEqual(self.read(os.path.join(destination, "Resources", "data.bin")), "new resources")
            self.assertFalse(os.path.exists(os.path.join(destination, "Resources", "old.bin")))
            self.assertFalse(any(name.startswith(".geodesync-transaction-") for name in os.listdir(destination)))

    def test_validation_failure_leaves_installed_game_unchanged(self):
        with tempfile.TemporaryDirectory() as root:
            source = os.path.join(root, "depot")
            destination = os.path.join(root, "game")
            os.makedirs(source)
            os.makedirs(destination)
            self.write(os.path.join(source, "game.bin"), "bad depot")
            self.write(os.path.join(destination, "game.bin"), "working game")

            with self.assertRaisesRegex(OSError, "failed validation"):
                install_depot_transactionally(source, destination, validator=lambda _path: "invalid fixture")

            self.assertEqual(self.read(os.path.join(destination, "game.bin")), "working game")

    def test_failed_mid_switch_rolls_all_entries_back(self):
        with tempfile.TemporaryDirectory() as root:
            source = os.path.join(root, "depot")
            destination = os.path.join(root, "game")
            os.makedirs(source)
            os.makedirs(destination)
            self.write(os.path.join(source, "a.bin"), "new a")
            self.write(os.path.join(source, "b.bin"), "new b")
            self.write(os.path.join(destination, "a.bin"), "old a")
            self.write(os.path.join(destination, "b.bin"), "old b")
            real_replace = os.replace

            def fail_b_install(src, dst):
                if "/incoming/b.bin" in src.replace("\\", "/") and dst == os.path.join(destination, "b.bin"):
                    raise OSError("simulated write failure")
                return real_replace(src, dst)

            with mock.patch("main.os.replace", side_effect=fail_b_install):
                with self.assertRaisesRegex(OSError, "simulated write failure"):
                    install_depot_transactionally(source, destination)

            self.assertEqual(self.read(os.path.join(destination, "a.bin")), "old a")
            self.assertEqual(self.read(os.path.join(destination, "b.bin")), "old b")
            self.assertFalse(any(name.startswith(".geodesync-transaction-") for name in os.listdir(destination)))

    def test_startup_recovery_restores_old_files_and_removes_new_files(self):
        with tempfile.TemporaryDirectory() as destination:
            stage = os.path.join(destination, ".geodesync-transaction-crash")
            previous = os.path.join(stage, "previous")
            incoming = os.path.join(stage, "incoming")
            os.makedirs(previous)
            os.makedirs(incoming)
            self.write(os.path.join(previous, "old.bin"), "previous content")
            self.write(os.path.join(destination, "old.bin"), "partially installed content")
            self.write(os.path.join(destination, "new.bin"), "newly installed content")
            atomic_write_json(os.path.join(stage, "journal.json"), {
                "destination": os.path.abspath(destination),
                "state": "installing",
                "items": ["old.bin", "new.bin"],
                "original_items": ["old.bin"],
            })

            recovered = recover_pending_install_transactions(destination)

            self.assertEqual(recovered, [".geodesync-transaction-crash"])
            self.assertEqual(self.read(os.path.join(destination, "old.bin")), "previous content")
            self.assertFalse(os.path.exists(os.path.join(destination, "new.bin")))

    def test_committed_transaction_is_cleaned_without_rollback(self):
        with tempfile.TemporaryDirectory() as destination:
            stage = os.path.join(destination, ".geodesync-transaction-committed")
            previous = os.path.join(stage, "previous")
            incoming = os.path.join(stage, "incoming")
            os.makedirs(previous)
            os.makedirs(incoming)
            self.write(os.path.join(previous, "game.bin"), "old")
            self.write(os.path.join(destination, "game.bin"), "new")
            atomic_write_json(os.path.join(stage, "journal.json"), {
                "destination": os.path.abspath(destination),
                "state": "committed",
                "items": ["game.bin"],
                "original_items": ["game.bin"],
            })

            recover_pending_install_transactions(destination)

            self.assertEqual(self.read(os.path.join(destination, "game.bin")), "new")
            self.assertFalse(os.path.exists(stage))

    def test_safe_copy_item_copies_file_atomically_without_bad_descriptor(self):
        with tempfile.TemporaryDirectory() as root:
            src = os.path.join(root, "source.dat")
            dst = os.path.join(root, "destination.dat")
            self.write(src, "important data")
            from main import safe_copy_item
            safe_copy_item(src, dst)
            self.assertEqual(self.read(dst), "important data")


if __name__ == "__main__":
    unittest.main()

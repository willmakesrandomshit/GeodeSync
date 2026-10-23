import io
import os
import plistlib
import stat
import subprocess
import tempfile
import unittest
import zipfile
from unittest import mock

from main import (
    GDManager,
    GeodeSyncApp,
    _copy_directory_transactionally,
    find_macos_game_app,
    request_macos_steam_launch,
    select_macos_update_asset,
    safe_copy_item,
    validate_macos_update_zip,
    validate_macos_game_app,
    verify_macos_update_digest,
    wait_for_process,
)


def release_asset(name, url="https://github.com/releases/download/v1.1.3/app.zip", size=1024):
    return {"name": name, "browser_download_url": url, "size": size}


class MacUpdateValidationTests(unittest.TestCase):
    def test_requires_matching_sha256_asset_digest(self):
        digest = "a" * 64
        verify_macos_update_digest(f"sha256:{digest}", digest)
        for expected in (None, "", "md5:" + digest, "sha256:xyz"):
            with self.subTest(expected=expected), self.assertRaises(ValueError):
                verify_macos_update_digest(expected, digest)
        with self.assertRaises(ValueError):
            verify_macos_update_digest("sha256:" + "b" * 64, digest)

    def test_selects_asset_for_each_supported_architecture(self):
        release = {"assets": [
            release_asset("GeodeSync-macOS-arm64.zip"),
            release_asset("GeodeSync-macOS-x86_64.zip"),
        ]}
        self.assertEqual(
            select_macos_update_asset(release, "arm64")["name"],
            "GeodeSync-macOS-arm64.zip",
        )
        self.assertEqual(
            select_macos_update_asset(release, "x86_64")["name"],
            "GeodeSync-macOS-x86_64.zip",
        )

    def test_rejects_missing_or_insecure_asset(self):
        with self.assertRaises(FileNotFoundError):
            select_macos_update_asset({"assets": []}, "arm64")
        with self.assertRaises(ValueError):
            select_macos_update_asset({"assets": [
                release_asset("GeodeSync-macOS-arm64.zip", "http://example.com/app.zip")
            ]}, "arm64")

    def test_rejects_duplicate_assets_and_unsupported_architecture(self):
        release = {"assets": [release_asset("GeodeSync-macOS-arm64.zip")] * 2}
        with self.assertRaises(FileNotFoundError):
            select_macos_update_asset(release, "arm64")
        with self.assertRaises(ValueError):
            select_macos_update_asset({"assets": []}, "powerpc")

    def test_accepts_expected_app_and_macos_metadata_entries(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            archive.writestr("GeodeSync.app/Contents/Info.plist", b"plist")
            archive.writestr("__MACOSX/GeodeSync.app/._Contents", b"metadata")
        with zipfile.ZipFile(data) as archive:
            validate_macos_update_zip(archive)

    def test_rejects_path_traversal_and_unexpected_files(self):
        for name in ("GeodeSync.app/../../outside", "elsewhere/payload"):
            data = io.BytesIO()
            with zipfile.ZipFile(data, "w") as archive:
                archive.writestr(name, b"bad")
            with zipfile.ZipFile(data) as archive:
                with self.assertRaises(ValueError):
                    validate_macos_update_zip(archive)


class MacGameLaunchTests(unittest.TestCase):
    def make_app(self, root, name="Geometry Dash.app", executable=True):
        app = os.path.join(root, name)
        contents = os.path.join(app, "Contents")
        macos = os.path.join(contents, "MacOS")
        os.makedirs(macos)
        with open(os.path.join(contents, "Info.plist"), "wb") as stream:
            plistlib.dump({"CFBundleExecutable": "Geometry Dash"}, stream)
        binary = os.path.join(macos, "Geometry Dash")
        with open(binary, "wb") as stream:
            stream.write(b"test executable")
        if executable:
            os.chmod(binary, 0o755)
        return app

    def test_resolves_steam_folder_and_direct_bundle_path(self):
        with tempfile.TemporaryDirectory() as root:
            app = self.make_app(root)
            self.assertEqual(find_macos_game_app(root), app)
            self.assertEqual(find_macos_game_app(app), app)
            self.assertIsNone(find_macos_game_app(os.path.join(root, "missing.app")))

    def test_rejects_incomplete_or_non_executable_bundle(self):
        with tempfile.TemporaryDirectory() as root:
            app = self.make_app(root, executable=False)
            self.assertIn("not marked executable", validate_macos_game_app(app))
            os.unlink(os.path.join(app, "Contents", "MacOS", "Geometry Dash"))
            self.assertIn("executable is missing", validate_macos_game_app(app))

    def test_launch_checks_bundle_and_reports_steam_dispatch_separately(self):
        runner = mock.Mock(return_value=mock.Mock(returncode=0, stdout="", stderr=""))
        with tempfile.TemporaryDirectory() as root:
            app = self.make_app(root)
            accepted, message = request_macos_steam_launch(root, runner)
            self.assertTrue(accepted)
            self.assertIn("dispatch only", message)
            self.assertEqual(runner.call_args.args[0], ["/usr/bin/open", "steam://run/322170"])

            failed = mock.Mock(return_value=mock.Mock(returncode=1, stdout="", stderr="launch denied"))
            accepted, message = request_macos_steam_launch(app, failed)
            self.assertFalse(accepted)
            self.assertIn("launch denied", message)

            missing = mock.Mock()
            accepted, message = request_macos_steam_launch(os.path.join(root, "missing"), missing)
            self.assertFalse(accepted)
            self.assertIn("not found", message)
            missing.assert_not_called()

    def test_process_monitor_waits_for_slow_steam_launch_and_times_out_cleanly(self):
        checks = iter((False, False, True))
        waits = []
        now = [0]
        self.assertTrue(wait_for_process(
            lambda: next(checks),
            timeout=5,
            interval=1,
            clock=lambda: now[0],
            sleep=lambda duration: (waits.append(duration), now.__setitem__(0, now[0] + duration)),
        ))
        self.assertEqual(waits, [1, 1])

        waits = []
        now = [0]
        self.assertFalse(wait_for_process(
            lambda: False,
            timeout=5,
            interval=2,
            clock=lambda: now[0],
            sleep=lambda duration: (waits.append(duration), now.__setitem__(0, now[0] + duration)),
        ))
        self.assertEqual(waits, [2, 2, 1])

    def test_transactional_bundle_swap_replaces_old_tree(self):
        with tempfile.TemporaryDirectory() as root:
            source = self.make_app(root, "new.app")
            destination = self.make_app(root, "Geometry Dash.app")
            with open(os.path.join(destination, "old-file"), "w") as stream:
                stream.write("old")
            _copy_directory_transactionally(source, destination, validate_macos_game_app)
            self.assertIsNone(validate_macos_game_app(destination))
            self.assertFalse(os.path.exists(os.path.join(destination, "old-file")))

    def test_transactional_bundle_validation_failure_preserves_old_install(self):
        with tempfile.TemporaryDirectory() as root:
            source = self.make_app(root, "new.app")
            destination = self.make_app(root, "Geometry Dash.app")
            with open(os.path.join(destination, "old-file"), "w") as stream:
                stream.write("preserve")
            with self.assertRaisesRegex(OSError, "incomplete"):
                _copy_directory_transactionally(source, destination, lambda _path: "bad bundle")
            with open(os.path.join(destination, "old-file")) as stream:
                self.assertEqual(stream.read(), "preserve")

    def test_transactional_bundle_swap_failure_rolls_back_old_install(self):
        with tempfile.TemporaryDirectory() as root:
            source = self.make_app(root, "new.app")
            destination = self.make_app(root, "Geometry Dash.app")
            with open(os.path.join(destination, "old-file"), "w") as stream:
                stream.write("preserve")
            real_replace = os.replace
            calls = 0

            def fail_install_once(src, dst):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated rename failure")
                return real_replace(src, dst)

            with mock.patch("main.os.replace", side_effect=fail_install_once):
                with self.assertRaisesRegex(OSError, "simulated rename failure"):
                    _copy_directory_transactionally(source, destination, validate_macos_game_app)
            with open(os.path.join(destination, "old-file")) as stream:
                self.assertEqual(stream.read(), "preserve")

    def test_atomic_file_copy_does_not_hide_write_failures_or_damage_existing_file(self):
        with tempfile.TemporaryDirectory() as root:
            source = os.path.join(root, "source")
            destination = os.path.join(root, "destination")
            with open(source, "w") as stream:
                stream.write("new contents")
            with open(destination, "w") as stream:
                stream.write("old contents")
            with mock.patch("main.shutil.copy2", side_effect=PermissionError("disk write denied")), \
                 mock.patch("main.time.sleep"):
                with self.assertRaisesRegex(PermissionError, "disk write denied"):
                    safe_copy_item(source, destination, max_retries=2)
            with open(destination) as stream:
                self.assertEqual(stream.read(), "old contents")


class SteamManifestRecoveryTests(unittest.TestCase):
    def make_manager(self, manifest):
        manager = GDManager.__new__(GDManager)
        manager.manifest_path = manifest
        return manager

    def test_macos_manifest_lock_and_unlock_are_verified(self):
        with tempfile.TemporaryDirectory() as root:
            manifest = os.path.join(root, "appmanifest_322170.acf")
            with open(manifest, "w") as stream:
                stream.write("manifest")
            manager = self.make_manager(manifest)

            with mock.patch("main.IS_MAC", True), mock.patch("main.subprocess.run") as run:
                manager.set_manifest_locked(True)
                self.assertTrue(manager.is_manifest_locked())
                manager.set_manifest_locked(False)
                self.assertFalse(manager.is_manifest_locked())

            self.assertEqual(run.call_count, 2)
            self.assertEqual(run.call_args_list[0].args[0][0:2], ["chflags", "uchg"])
            self.assertEqual(run.call_args_list[1].args[0][0:2], ["chflags", "nouchg"])

    def test_macos_failed_immutable_flag_does_not_leave_manifest_read_only(self):
        with tempfile.TemporaryDirectory() as root:
            manifest = os.path.join(root, "appmanifest_322170.acf")
            with open(manifest, "w") as stream:
                stream.write("manifest")
            manager = self.make_manager(manifest)

            with mock.patch("main.IS_MAC", True), \
                 mock.patch("main.subprocess.run", side_effect=subprocess.CalledProcessError(1, "chflags")), \
                 mock.patch("main.time.sleep"):
                with self.assertRaises(subprocess.CalledProcessError):
                    manager.set_manifest_locked(True)

            self.assertTrue(os.stat(manifest).st_mode & stat.S_IWRITE)

    def test_restore_does_not_start_steam_validation_if_unlock_fails(self):
        app = GeodeSyncApp.__new__(GeodeSyncApp)
        app.mgr = mock.Mock()
        app.mgr.set_manifest_locked.side_effect = PermissionError("manifest is immutable")
        app.log = mock.Mock()

        with mock.patch("main.messagebox.showerror") as showerror, \
             mock.patch("main.open_url_or_path") as open_url:
            app._run_upgrade()

        open_url.assert_not_called()
        showerror.assert_called_once()

    def test_rapid_downgrade_clicks_start_only_one_worker(self):
        app = GeodeSyncApp.__new__(GeodeSyncApp)
        app.is_downloading_depot = False
        app.mgr = mock.Mock()
        app.mgr.is_gd_process_running.return_value = False
        app.primary_btn = mock.Mock()
        app.log = mock.Mock()

        with mock.patch("main.threading.Thread") as thread:
            app.start_automated_downgrade()
            app.start_automated_downgrade()

        thread.assert_called_once()
        self.assertTrue(app.is_downloading_depot)


if __name__ == "__main__":
    unittest.main()

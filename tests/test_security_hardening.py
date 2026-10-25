import pathlib
import io
import os
import stat
import tempfile
import unittest
import zipfile
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from main import (
    decode_geometry_dash_save,
    encode_geometry_dash_save,
    extract_geode_package_safely,
    official_release_page,
    safe_zip_member_target,
    is_safe_geode_mod_id,
    validate_geode_package_zip,
    verify_release_asset_digest,
    select_app_update_asset,
    validate_app_update_zip,
    validate_app_update_tar,
    _apply_staged_update,
    download_verified_app_update,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]


@contextmanager
def tempfile_zip():
    with zipfile.ZipFile(io.BytesIO(), "w") as archive:
        yield archive


class SecurityHardeningTests(unittest.TestCase):
    def test_geometry_dash_save_wrapper_round_trips(self):
        xml = b"<?xml version='1.0'?><plist><dict><key>playerName</key></dict></plist>"
        self.assertEqual(decode_geometry_dash_save(encode_geometry_dash_save(xml)), xml)

    def test_update_link_is_pinned_to_official_repository(self):
        expected = "https://github.com/willmakesrandomshit/GeodeSync/releases"
        self.assertEqual(official_release_page(expected + "/latest"), expected + "/latest")
        for untrusted in (
            "https://example.com/releases",
            "https://github.com/attacker/GeodeSync/releases",
            "javascript:alert(1)",
        ):
            with self.subTest(url=untrusted):
                self.assertEqual(official_release_page(untrusted), expected)

    def test_build_and_update_sources_do_not_remove_os_download_warnings(self):
        sources = [
            ROOT / "main.py",
            ROOT / "GeodeSync.pyw",
            ROOT / "package_windows.ps1",
            ROOT / "build_macos.py",
        ]
        for path in sources:
            with self.subTest(file=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("Unblock-File", text)
                self.assertNotIn("xattr -cr", text)

    def test_update_action_downloads_verified_official_package(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        start = source.index("    def start_self_update(self, auto_install=False, release=None):")
        end = source.index("    def _finish_staged_app_update", start)
        update_action = source[start:end]
        self.assertIn("download_verified_app_update", update_action)
        self.assertIn("_launch_staged_app_update", update_action)
        self.assertIn("SHA-256", source)

    def test_windows_release_uses_portable_onedir_package(self):
        package_script = (ROOT / "package_windows.ps1").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/build-macos.yml").read_text(encoding="utf-8")
        self.assertIn("--onedir", package_script)
        self.assertNotIn("--onefile", package_script)
        self.assertIn("GeodeSync-Windows.zip", workflow)
        self.assertNotIn("GeodeSync-v*-Windows.zip", workflow)
        self.assertNotIn("            GeodeSync.exe\n", workflow)
        self.assertIn("Run regression suite on Windows", workflow)

    def test_discord_release_helper_uses_current_version_and_assets(self):
        source = (ROOT / "send_discord_update.py").read_text(encoding="utf-8")
        self.assertIn('version = version or current_version()', source)
        self.assertIn('"release_notes.md"', source)
        self.assertIn("releases/tag/v{version}", source)
        self.assertNotIn("GeodeSync.exe]", source)

    def test_python_gui_entry_points_stay_in_sync(self):
        self.assertEqual(
            (ROOT / "main.py").read_bytes(),
            (ROOT / "GeodeSync.pyw").read_bytes(),
        )

    def test_release_download_instructions_use_the_release_page_and_versioned_assets(self):
        workflow = (ROOT / ".github/workflows/build-macos.yml").read_text(encoding="utf-8")
        guide = (ROOT / "USER_GUIDE.md").read_text(encoding="utf-8")
        site = (ROOT / "docs/index.html").read_text(encoding="utf-8")
        self.assertIn("GeodeSync-Windows.zip", guide)
        self.assertIn("releases/latest/download/GeodeSync-Windows.zip", site)

    def test_geode_archive_rejects_traversal_before_writing_anything(self):
        with pathlib.Path(__file__).resolve().parents[1].joinpath(".test-sentinel").open("w") as marker:
            marker.write("unchanged")
        try:
            data = io.BytesIO()
            with zipfile.ZipFile(data, "w") as archive:
                archive.writestr("safe.dll", b"would be installed")
                archive.writestr("../.test-sentinel", b"overwritten")
            with zipfile.ZipFile(io.BytesIO(data.getvalue())) as archive:
                with self.assertRaises(ValueError):
                    validate_geode_package_zip(archive, str(ROOT))
                with self.assertRaises(ValueError):
                    extract_geode_package_safely(archive, str(ROOT))
            self.assertFalse((ROOT / "safe.dll").exists())
            self.assertEqual((ROOT / ".test-sentinel").read_text(), "unchanged")
        finally:
            (ROOT / ".test-sentinel").unlink(missing_ok=True)

    def test_geode_archive_rejects_symlinks_and_drive_paths(self):
        with tempfile_zip() as archive:
            link = zipfile.ZipInfo("link.dll")
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(link, "../../outside.dll")
            archive.writestr("C:/outside.dll", b"bad")
            with self.assertRaises(ValueError):
                validate_geode_package_zip(archive, str(ROOT))

    def test_geode_archive_rejects_symlinked_destination_parent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            outside = root / "outside"
            outside.mkdir()
            link = root / "linked"
            link.symlink_to(outside, target_is_directory=True)
            with tempfile_zip() as archive:
                archive.writestr("linked/payload.dll", b"bad")
                with self.assertRaises(ValueError):
                    validate_geode_package_zip(archive, str(root))

    def test_geode_install_replaces_files_and_rolls_back_partial_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            (root / "a.dll").write_bytes(b"old-a")
            (root / "b.dll").write_bytes(b"old-b")
            with tempfile_zip() as archive:
                archive.writestr("a.dll", b"new-a")
                archive.writestr("b.dll", b"new-b")
                real_replace = os.replace
                resolved_root = pathlib.Path(os.path.realpath(root))

                def replace_then_fail_second(source, destination):
                    if os.fspath(destination) == str(resolved_root / "b.dll") and "/incoming/" in os.fspath(source).replace("\\", "/"):
                        raise OSError("simulated write failure")
                    return real_replace(source, destination)

                with patch("main.os.replace", side_effect=replace_then_fail_second):
                    with self.assertRaises(OSError):
                        extract_geode_package_safely(archive, str(root))
            self.assertEqual((root / "a.dll").read_bytes(), b"old-a")
            self.assertEqual((root / "b.dll").read_bytes(), b"old-b")

    def test_geode_mod_ids_cannot_be_used_as_paths(self):
        self.assertTrue(is_safe_geode_mod_id("prevter.imageplus"))
        for mod_id in ("../../outside", "author..mod", "author/mod", "", "onepart"):
            with self.subTest(mod_id=mod_id):
                self.assertFalse(is_safe_geode_mod_id(mod_id))

    def test_geode_release_digest_is_checked(self):
        import hashlib
        payload = b"trusted fixture"
        asset = {"digest": "sha256:" + hashlib.sha256(payload).hexdigest()}
        verify_release_asset_digest(asset, payload, "fixture")
        with self.assertRaises(ValueError):
            verify_release_asset_digest(asset, b"tampered", "fixture")
        with self.assertRaises(ValueError):
            verify_release_asset_digest({}, payload, "fixture")

    def test_app_update_asset_must_be_exact_official_release_asset(self):
        release = {"tag_name": "v2.4.0", "published_at": "2026-10-25T00:00:00Z", "assets": [{
            "name": "GeodeSync-Windows.zip", "size": 10,
            "browser_download_url": "https://github.com/willmakesrandomshit/GeodeSync/releases/download/v2.4.0/GeodeSync-Windows.zip",
        }]}
        self.assertEqual(select_app_update_asset(release, "windows")["name"], "GeodeSync-Windows.zip")
        release["assets"][0]["browser_download_url"] = "https://evil.example/payload.zip"
        with self.assertRaises(ValueError):
            select_app_update_asset(release, "windows")

    def test_verified_update_download_checks_digest_and_extracts(self):
        import hashlib
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            archive.writestr("GeodeSync.exe", b"new-app")
            archive.writestr("_internal/runtime.dll", b"runtime")
        package = data.getvalue()
        url = "https://github.com/willmakesrandomshit/GeodeSync/releases/download/v2.4.0/GeodeSync-Windows.zip"
        release = {"tag_name": "v2.4.0", "published_at": "2026-10-25T00:00:00Z", "assets": [{
            "name": "GeodeSync-Windows.zip", "size": len(package),
            "digest": "sha256:" + hashlib.sha256(package).hexdigest(),
            "browser_download_url": url,
        }]}
        response = MagicMock()
        response.__enter__.return_value.read.return_value = package
        response.__enter__.return_value.geturl.return_value = url
        with tempfile.TemporaryDirectory() as destination, patch("main.urllib.request.urlopen", return_value=response):
            asset, payload = download_verified_app_update(release, destination, "windows")
            self.assertEqual(asset["name"], "GeodeSync-Windows.zip")
            self.assertEqual((pathlib.Path(payload) / "GeodeSync.exe").read_bytes(), b"new-app")

    def test_app_update_zip_rejects_traversal(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            archive.writestr("GeodeSync.exe", b"exe")
            archive.writestr("_internal/runtime.dll", b"dll")
            archive.writestr("../../outside", b"bad")
        with zipfile.ZipFile(io.BytesIO(data.getvalue())) as archive:
            with self.assertRaises(ValueError):
                validate_app_update_zip(archive, "windows")

    def test_linux_update_tar_rejects_symlink_and_traversal(self):
        import tarfile
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode="w:gz") as archive:
            info = tarfile.TarInfo("GeodeSync")
            payload = b"binary"
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
            link = tarfile.TarInfo("outside")
            link.type = tarfile.SYMTYPE
            link.linkname = "../../outside"
            archive.addfile(link)
        with tarfile.open(fileobj=io.BytesIO(data.getvalue()), mode="r:gz") as archive:
            with self.assertRaises(ValueError):
                validate_app_update_tar(archive)

    def test_staged_app_update_swaps_and_rolls_back(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            target = root / "GeodeSync"
            work = root / ".GeodeSync-update-test"
            payload = work / "payload"
            backup = work / "previous-install"
            (target / "_internal").mkdir(parents=True)
            (target / "GeodeSync.exe").write_bytes(b"old")
            (payload / "_internal").mkdir(parents=True)
            (payload / "GeodeSync.exe").write_bytes(b"new")
            with patch("main._wait_for_process_exit"), patch("main.subprocess.Popen"), patch("main.IS_WIN", True), patch("main.IS_MAC", False):
                _apply_staged_update(str(payload), str(target), str(backup), 123)
            self.assertEqual((target / "GeodeSync.exe").read_bytes(), b"new")
            self.assertFalse(backup.exists())

            failed_payload = work / "failed-payload"
            (failed_payload / "_internal").mkdir(parents=True)
            (failed_payload / "GeodeSync.exe").write_bytes(b"broken")
            with patch("main._wait_for_process_exit"), patch("main.subprocess.Popen", side_effect=OSError("launch failed")), patch("main.IS_WIN", True), patch("main.IS_MAC", False):
                with self.assertRaises(OSError):
                    _apply_staged_update(str(failed_payload), str(target), str(backup), 123)
            self.assertEqual((target / "GeodeSync.exe").read_bytes(), b"new")


if __name__ == "__main__":
    unittest.main()

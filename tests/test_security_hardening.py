import pathlib
import io
import os
import stat
import tempfile
import unittest
import zipfile
from contextlib import contextmanager
from unittest.mock import patch

from main import (
    decode_geometry_dash_save,
    encode_geometry_dash_save,
    extract_geode_package_safely,
    official_release_page,
    safe_zip_member_target,
    is_safe_geode_mod_id,
    validate_geode_package_zip,
    verify_release_asset_digest,
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

    def test_update_action_uses_manual_official_release_review(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        start = source.index("    def start_self_update(self):")
        end = source.index("    def _schedule_update_progress", start)
        update_action = source[start:end]
        self.assertIn("official_release_page", update_action)
        self.assertIn("webbrowser.open", update_action)
        self.assertNotIn("urlopen", update_action)
        self.assertNotIn("subprocess", update_action)

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


if __name__ == "__main__":
    unittest.main()

import io
import unittest
import zipfile

from main import (
    select_macos_update_asset,
    validate_macos_update_zip,
    verify_macos_update_digest,
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


if __name__ == "__main__":
    unittest.main()

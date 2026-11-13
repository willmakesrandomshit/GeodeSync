import os
import struct
import tempfile
import zlib

from geodesync.services.diagnostics import inspect_png_resource, scan_texture_resources
from geodesync.services.gd.assets import AssetsMixin


def png_bytes():
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data +
                struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00")) +
            chunk(b"IEND", b""))


class TextureManager(AssetsMixin):
    def __init__(self, path, running=False):
        self.gd_path = path
        self.running = running

    def is_gd_process_running(self):
        return self.running


def test_png_integrity_check_accepts_valid_and_rejects_corrupt_file():
    with tempfile.TemporaryDirectory() as root:
        valid = os.path.join(root, "valid.png")
        corrupt = os.path.join(root, "corrupt.png")
        data = png_bytes()
        open(valid, "wb").write(data)
        open(corrupt, "wb").write(data[:-5] + b"xxxxx")

        assert inspect_png_resource(valid) is None
        assert inspect_png_resource(corrupt)


def test_scan_finds_missing_textures_and_reports_clean_integrity():
    with tempfile.TemporaryDirectory() as root:
        resources = os.path.join(root, "Resources")
        backup = os.path.join(root, "Resources_Vanilla_Backup")
        os.makedirs(resources)
        os.makedirs(backup)
        open(os.path.join(resources, "present.png"), "wb").write(png_bytes())
        open(os.path.join(backup, "present.png"), "wb").write(png_bytes())
        open(os.path.join(backup, "missing.png"), "wb").write(png_bytes())

        finding = scan_texture_resources(root)[0]
        assert "damaged or missing" in finding["title"]
        assert "missing.png" in finding["detail"]

        os.remove(os.path.join(backup, "missing.png"))
        assert "passed" in scan_texture_resources(root)[0]["title"]


def test_restore_refuses_to_write_if_game_is_running():
    with tempfile.TemporaryDirectory() as root:
        resources = os.path.join(root, "Resources")
        backup = os.path.join(root, "Resources_Vanilla_Backup")
        os.makedirs(resources)
        os.makedirs(backup)
        original = os.path.join(resources, "sheet.png")
        open(original, "wb").write(b"custom")
        open(os.path.join(backup, "sheet.png"), "wb").write(png_bytes())

        ok, message = TextureManager(root, running=True).restore_vanilla_textures()

        assert not ok and "Close Geometry Dash" in message
        assert open(original, "rb").read() == b"custom"


def test_restore_validates_all_backup_pngs_before_writing():
    with tempfile.TemporaryDirectory() as root:
        resources = os.path.join(root, "Resources")
        backup = os.path.join(root, "Resources_Vanilla_Backup")
        os.makedirs(resources)
        os.makedirs(backup)
        original = os.path.join(resources, "sheet.png")
        open(original, "wb").write(b"custom")
        open(os.path.join(backup, "sheet.png"), "wb").write(png_bytes())
        open(os.path.join(backup, "broken.png"), "wb").write(b"bad")

        ok, message = TextureManager(root).restore_vanilla_textures()

        assert not ok and "No files were changed" in message
        assert open(original, "rb").read() == b"custom"

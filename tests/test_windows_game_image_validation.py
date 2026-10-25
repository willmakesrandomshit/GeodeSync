import os
import struct
import tempfile
import unittest

from main import (
    install_depot_transactionally,
    read_windows_pe_machine,
    validate_windows_game_images,
)


def write_pe(path, machine=0x8664, *, truncate=False):
    """Write a tiny structurally valid PE fixture without requiring Windows."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    optional_size = 0xE0 if machine == 0x014C else 0xF0
    image = bytearray(0x300)
    image[:2] = b"MZ"
    struct.pack_into("<I", image, 0x3C, 0x80)
    image[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", image, 0x84, machine, 1, 0, 0, 0, optional_size, 0x2022)
    optional_offset = 0x98
    struct.pack_into("<H", image, optional_offset, 0x10B if machine == 0x014C else 0x20B)
    section_offset = optional_offset + optional_size
    struct.pack_into("<8sIIIIIIHHI", image, section_offset, b".text", 0x100, 0x1000, 0x100, 0x200, 0, 0, 0, 0, 0)
    with open(path, "wb") as stream:
        stream.write(image[:0x100] if truncate else image)


def read_bytes(path):
    with open(path, "rb") as stream:
        return stream.read()


class WindowsGameImageValidationTests(unittest.TestCase):
    def test_reads_valid_x64_pe_and_accepts_matching_game_dlls(self):
        with tempfile.TemporaryDirectory() as root:
            write_pe(os.path.join(root, "GeometryDash.exe"))
            write_pe(os.path.join(root, "libcrypto-3-x64.dll"))
            self.assertEqual(read_windows_pe_machine(os.path.join(root, "GeometryDash.exe")), 0x8664)
            self.assertIsNone(validate_windows_game_images(root))

    def test_rejects_damaged_dll_and_explains_filename(self):
        with tempfile.TemporaryDirectory() as root:
            write_pe(os.path.join(root, "GeometryDash.exe"))
            with open(os.path.join(root, "libcrypto-3-x64.dll"), "wb") as stream:
                stream.write(b"not a windows library")
            problem = validate_windows_game_images(root)
            self.assertIn("libcrypto-3-x64.dll", problem)
            self.assertIn("damaged", problem)

    def test_rejects_wrong_architecture_dll(self):
        with tempfile.TemporaryDirectory() as root:
            write_pe(os.path.join(root, "GeometryDash.exe"), 0x8664)
            write_pe(os.path.join(root, "libcrypto-3-x64.dll"), 0x014C)
            problem = validate_windows_game_images(root)
            self.assertIn("is x86, but GeometryDash.exe is x64", problem)

    def test_rejects_wrong_depot_executable_size(self):
        with tempfile.TemporaryDirectory() as root:
            write_pe(os.path.join(root, "GeometryDash.exe"))
            self.assertIn("size does not match", validate_windows_game_images(root, expected_exe_size=123))

    def test_depot_repair_replaces_bad_existing_dll_before_commit(self):
        with tempfile.TemporaryDirectory() as root:
            source = os.path.join(root, "depot")
            destination = os.path.join(root, "game")
            os.makedirs(source)
            os.makedirs(destination)
            write_pe(os.path.join(source, "GeometryDash.exe"))
            write_pe(os.path.join(source, "libcrypto-3-x64.dll"))
            write_pe(os.path.join(destination, "GeometryDash.exe"))
            with open(os.path.join(destination, "libcrypto-3-x64.dll"), "wb") as stream:
                stream.write(b"broken old copy")

            validate = lambda path: validate_windows_game_images(path)
            install_depot_transactionally(
                source, destination, validator=validate, installed_validator=validate,
            )

            self.assertIsNone(validate_windows_game_images(destination))

    def test_bad_depot_dll_is_rejected_without_touching_installed_game(self):
        with tempfile.TemporaryDirectory() as root:
            source = os.path.join(root, "depot")
            destination = os.path.join(root, "game")
            os.makedirs(source)
            os.makedirs(destination)
            write_pe(os.path.join(source, "GeometryDash.exe"))
            with open(os.path.join(source, "libcrypto-3-x64.dll"), "wb") as stream:
                stream.write(b"bad download")
            write_pe(os.path.join(destination, "GeometryDash.exe"))
            old_exe = read_bytes(os.path.join(destination, "GeometryDash.exe"))

            with self.assertRaisesRegex(OSError, "libcrypto-3-x64.dll"):
                install_depot_transactionally(
                    source, destination,
                    validator=validate_windows_game_images,
                    installed_validator=validate_windows_game_images,
                )

            with open(os.path.join(destination, "GeometryDash.exe"), "rb") as stream:
                self.assertEqual(stream.read(), old_exe)
            self.assertFalse(os.path.exists(os.path.join(destination, "libcrypto-3-x64.dll")))

    def test_bad_untracked_existing_dll_rolls_back_game_swap(self):
        with tempfile.TemporaryDirectory() as root:
            source = os.path.join(root, "depot")
            destination = os.path.join(root, "game")
            os.makedirs(source)
            os.makedirs(destination)
            write_pe(os.path.join(source, "GeometryDash.exe"))
            write_pe(os.path.join(destination, "GeometryDash.exe"))
            with open(os.path.join(destination, "libcrypto-3-x64.dll"), "wb") as stream:
                stream.write(b"old invalid dll")
            old_exe = read_bytes(os.path.join(destination, "GeometryDash.exe"))

            with self.assertRaisesRegex(OSError, "installed game failed validation"):
                install_depot_transactionally(
                    source, destination,
                    validator=validate_windows_game_images,
                    installed_validator=validate_windows_game_images,
                )

            with open(os.path.join(destination, "GeometryDash.exe"), "rb") as stream:
                self.assertEqual(stream.read(), old_exe)
            with open(os.path.join(destination, "libcrypto-3-x64.dll"), "rb") as stream:
                self.assertEqual(stream.read(), b"old invalid dll")


if __name__ == "__main__":
    unittest.main()

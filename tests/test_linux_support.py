import io
import os
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import (
    discover_linux_steam_roots,
    discover_steam_game_folders,
    find_linux_geometry_dash_pids,
    get_app_data_dir,
    scan_installation_issues,
    validate_app_update_tar,
)


class LinuxSupportTests(unittest.TestCase):
    def test_detects_native_flatpak_and_custom_steam_roots(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            flatpak = home / ".var/app/com.valvesoftware.Steam/data/Steam"
            custom = home / "Games/Steam"
            (flatpak / "steamapps").mkdir(parents=True)
            (custom / "steamapps").mkdir(parents=True)
            roots = discover_linux_steam_roots(
                home=str(home),
                environ={"STEAM_DIR": str(custom)},
                which=lambda _name: None,
            )
            self.assertEqual(roots, [str(custom.resolve()), str(flatpak.resolve())])

    def test_finds_game_in_nondefault_steam_library(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            root = home / ".local/share/Steam"
            secondary = home / "External/SteamLibrary"
            game = secondary / "steamapps/common/Geometry Dash"
            game.mkdir(parents=True)
            (game / "GeometryDash.exe").write_bytes(b"proton game")
            (root / "steamapps").mkdir(parents=True)
            vdf_root = str(root).replace("\\", "\\\\")
            vdf_secondary = str(secondary).replace("\\", "\\\\")
            (root / "steamapps/libraryfolders.vdf").write_text(
                '"libraryfolders" { "0" { "path" "' + vdf_root + '" } '
                '"1" { "path" "' + vdf_secondary + '" } }',
                encoding="utf-8",
            )
            roots = discover_linux_steam_roots(
                home=str(home), environ={}, which=lambda _name: None
            )
            self.assertEqual(discover_steam_game_folders(roots), [str(game.resolve())])

    def test_app_data_obeys_xdg_config_home(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("main.IS_WIN", False), patch("main.IS_MAC", False), patch("main.IS_LINUX", True), patch.dict(os.environ, {"XDG_CONFIG_HOME": temp}):
                self.assertEqual(get_app_data_dir(), os.path.join(temp, "geodesync"))

    def test_linux_setup_check_explains_missing_proton_executable(self):
        with tempfile.TemporaryDirectory() as temp:
            steam = Path(temp)
            game = steam / "steamapps/common/Geometry Dash"
            game.mkdir(parents=True)
            findings = scan_installation_issues(
                type("Manager", (), {"steam_path": str(steam), "gd_path": str(game)})(),
                is_windows=False,
                is_macos=False,
                is_linux=True,
            )
            missing = next(item for item in findings if item["title"] == "The Proton game executable is missing")
            self.assertIn("Verify integrity", missing["steps"])
            self.assertTrue(any("Steam / Proton" in item["title"] for item in findings))

    def test_process_scan_matches_only_game_executable_argument(self):
        with tempfile.TemporaryDirectory() as temp:
            proc = Path(temp)
            for pid, argv in {
                "101": b"/usr/bin/wine\0C:\\Games\\GeometryDash.exe\0",
                "102": b"/usr/bin/python\0/home/user/GeodeSync\0",
                "103": b"/usr/bin/GeometryDash-helper\0",
            }.items():
                folder = proc / pid
                folder.mkdir()
                (folder / "cmdline").write_bytes(argv)
            self.assertEqual(find_linux_geometry_dash_pids(str(proc)), [101])

    def test_linux_update_tar_accepts_legacy_dot_prefix_and_requires_binary(self):
        with tempfile.TemporaryFile() as stream:
            with tarfile.open(fileobj=stream, mode="w:gz") as archive:
                root = tarfile.TarInfo("./")
                root.type = tarfile.DIRTYPE
                archive.addfile(root)
                binary = tarfile.TarInfo("./GeodeSync")
                binary.size = 4
                archive.addfile(binary, io.BytesIO(b"ELF!"))
            stream.seek(0)
            with tarfile.open(fileobj=stream, mode="r:gz") as archive:
                validate_app_update_tar(archive)

    def test_linux_update_tar_rejects_traversal_and_missing_binary(self):
        for name in ("../escape", "README.txt"):
            with self.subTest(name=name), tempfile.TemporaryFile() as stream:
                with tarfile.open(fileobj=stream, mode="w:gz") as archive:
                    info = tarfile.TarInfo(name)
                    info.size = 1
                    archive.addfile(info, io.BytesIO(b"x"))
                stream.seek(0)
                with tarfile.open(fileobj=stream, mode="r:gz") as archive:
                    with self.assertRaises(ValueError):
                        validate_app_update_tar(archive)


if __name__ == "__main__":
    unittest.main()

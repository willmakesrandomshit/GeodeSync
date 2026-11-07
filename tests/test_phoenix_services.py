"""Tests for Project Phoenix geodesync package services."""

import unittest
from unittest.mock import patch, MagicMock
from geodesync.services.update_service import UpdateService, parse_version_tuple, is_newer_version
from geodesync.services.game_service import GameService
from geodesync.services.save_service import SaveService, decode_gd_save, encode_gd_save
from geodesync.services.mod_service import ModService


class TestPhoenixServices(unittest.TestCase):

    def test_version_parsing(self):
        self.assertEqual(parse_version_tuple("v2.7.0"), (2, 7, 0))
        self.assertEqual(parse_version_tuple("2.6.0"), (2, 6, 0))
        self.assertTrue(is_newer_version("2.7.1", "2.7.0"))
        self.assertFalse(is_newer_version("2.7.0", "2.7.0"))
        self.assertFalse(is_newer_version("2.6.0", "2.7.0"))

    def test_save_encode_decode_roundtrip(self):
        sample_xml = b"<plist version=\"1.0\"><dict><key>test</key><true/></dict></plist>"
        encoded = encode_gd_save(sample_xml)
        decoded = decode_gd_save(encoded)
        self.assertEqual(decoded, sample_xml)

    @patch("geodesync.services.game_service.safe_run_command")
    def test_game_running_detection(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.stdout = "GeometryDash.exe   12345 Console   1   150,000 K"
        mock_run.return_value = mock_proc
        self.assertTrue(GameService.is_game_running())

        mock_proc.stdout = "INFO: No tasks running with specified criteria."
        self.assertFalse(GameService.is_game_running())


if __name__ == "__main__":
    unittest.main()

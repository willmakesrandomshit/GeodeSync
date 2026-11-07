import unittest
import os
import sys
import subprocess
from unittest.mock import patch, MagicMock

import main


class ProcessSafetyTests(unittest.TestCase):
    def test_silent_creationflags_includes_create_no_window_on_windows(self):
        with patch.object(main, "IS_WIN", True):
            flags = main.get_silent_creationflags()
            self.assertTrue(flags & 0x08000000, "CREATE_NO_WINDOW (0x08000000) must be set on Windows")

    def test_silent_startupinfo_sets_sw_hide(self):
        with patch.object(main, "IS_WIN", True):
            si = main.get_silent_startupinfo()
            self.assertIsNotNone(si)
            self.assertEqual(si.wShowWindow, 0)
            self.assertTrue(si.dwFlags & 1)

    @patch("subprocess.run")
    def test_safe_run_command_passes_silent_flags_on_windows(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        with patch.object(main, "IS_WIN", True):
            main.safe_run_command(["attrib.exe", "-U", "-P", "/s", "/d", "*"])
            self.assertTrue(mock_run.called)
            _args, kwargs = mock_run.call_args
            self.assertTrue(kwargs.get("creationflags", 0) & 0x08000000)
            self.assertEqual(kwargs.get("startupinfo").wShowWindow, 0)

    @patch("subprocess.Popen")
    def test_safe_popen_command_passes_silent_flags_on_windows(self, mock_popen):
        with patch.object(main, "IS_WIN", True):
            main.safe_popen_command(["wscript.exe", "//nologo", "test.vbs"])
            self.assertTrue(mock_popen.called)
            _args, kwargs = mock_popen.call_args
            self.assertTrue(kwargs.get("creationflags", 0) & 0x08000000)
            self.assertEqual(kwargs.get("startupinfo").wShowWindow, 0)

    def test_fetch_latest_published_release_raises_when_completely_offline(self):
        with patch("urllib.request.urlopen", side_effect=OSError("Network unreachable")):
            with self.assertRaisesRegex(ValueError, "Could not connect to GitHub"):
                main.fetch_latest_published_release(timeout=0.1)

    def test_fetch_latest_published_release_uses_atom_fallback_when_api_rate_limited(self):
        # When official API returns HTTP 403, atom feed should be parsed successfully
        atom_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <link href="https://github.com/willmakesrandomshit/GeodeSync/releases/tag/v2.6.0"/>
    <updated>2026-11-06T21:04:22Z</updated>
  </entry>
</feed>'''
        class MockResponse:
            def __init__(self, data):
                self.data = data
            def read(self):
                return self.data
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass

        def mock_urlopen(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if "api.github.com" in url:
                import urllib.error
                raise urllib.error.HTTPError(url, 403, "rate limit exceeded", {}, None)
            if "releases.atom" in url:
                return MockResponse(atom_xml)
            raise OSError("offline")

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            rel = main.fetch_latest_published_release(timeout=1)
            self.assertEqual(rel["tag_name"], "v2.6.0")


if __name__ == "__main__":
    unittest.main()

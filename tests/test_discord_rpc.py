import unittest
from unittest.mock import MagicMock, patch
import struct
import json
import main

class TestDiscordRPC(unittest.TestCase):
    def test_rpc_init_and_state(self):
        rpc = main.DiscordRPC(enabled=False)
        self.assertFalse(rpc.is_connected())
        rpc.set_enabled(True)
        self.assertTrue(rpc._enabled)
        rpc.set_enabled(False)
        self.assertFalse(rpc.is_connected())
        rpc.close()

    def test_handshake_formatting(self):
        rpc = main.DiscordRPC(enabled=False)
        mock_sock = MagicMock()
        
        # Prepare mock response for handshake
        mock_resp_body = b'{"cmd":"DISPATCH","data":{}}'
        mock_resp_hdr = struct.pack("<II", 1, len(mock_resp_body))
        mock_sock.read.side_effect = [mock_resp_hdr, mock_resp_body]
        
        success = rpc._perform_handshake(mock_sock)
        self.assertTrue(success)
        mock_sock.write.assert_called_once()
        sent_data = mock_sock.write.call_args[0][0]
        op, length = struct.unpack("<II", sent_data[:8])
        self.assertEqual(op, 0)
        payload = json.loads(sent_data[8:8+length].decode("utf-8"))
        self.assertEqual(payload["client_id"], main.DiscordRPC.CLIENT_ID)
        rpc.close()

    def test_update_presence_caching(self):
        rpc = main.DiscordRPC(enabled=False)
        rpc.update_presence("GD 2.2081", "Protected")
        self.assertEqual(rpc._current_details, "GD 2.2081")
        self.assertEqual(rpc._current_state, "Protected")
        rpc.close()

    def test_send_activity_payload(self):
        with patch("threading.Thread"):
            rpc = main.DiscordRPC(enabled=False)
        rpc._connected = True
        rpc._enabled = True
        mock_sock = MagicMock()
        mock_resp_body = b'{"cmd":"SET_ACTIVITY","data":{}}'
        mock_resp_hdr = struct.pack("<II", 1, len(mock_resp_body))
        mock_sock.read.side_effect = [mock_resp_hdr, mock_resp_body]
        rpc._sock = mock_sock

        rpc._send_activity()
        mock_sock.write.assert_called_once()
        sent_data = mock_sock.write.call_args[0][0]
        op, length = struct.unpack("<II", sent_data[:8])
        self.assertEqual(op, 1)
        payload = json.loads(sent_data[8:8+length].decode("utf-8"))
        self.assertEqual(payload["cmd"], "SET_ACTIVITY")
        activity = payload["args"]["activity"]
        self.assertIn("assets", activity)
        self.assertIn("buttons", activity)
        self.assertEqual(len(activity["buttons"]), 2)
        self.assertEqual(activity["buttons"][0]["label"], "View GitHub Repo")
        self.assertEqual(activity["buttons"][1]["label"], "Join Discord Server")
        self.assertIn("geodesync_rpc_icon", activity["assets"]["large_image"])
        self.assertIn("real_geode_logo.png", activity["assets"]["small_image"])
        rpc.close()

if __name__ == "__main__":
    unittest.main()

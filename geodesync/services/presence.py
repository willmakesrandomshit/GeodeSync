"""Discord Rich Presence over the local Discord IPC socket (moved verbatim from v2.8.0 main.py)."""

import os
import json
import time
import tempfile
import threading
import struct
from geodesync.core.config import APP_VERSION, GITHUB_REPO
from geodesync.platform.process_manager import IS_WIN



class DiscordRPC:
    CLIENT_ID = "1563607447384367195"
    PLAYING_DETAILS = "Playing Geometry Dash with GeodeSync"
    COMPANION_DETAILS = "GeodeSync · Geometry Dash Companion"

    def __init__(self, enabled=True):
        self._enabled = enabled
        self._sock = None
        self._connected = False
        self._lock = threading.RLock()
        self._start_time = int(time.time())
        self._current_details = self.COMPANION_DETAILS
        self._current_state = "Geode Mods Synced & Protected 🛡️"
        self._geode_ver = "v5.x"
        self._running = True
        self._wake = threading.Event()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def set_enabled(self, val):
        self._enabled = bool(val)
        if not self._enabled:
            self._close_socket()
        else:
            self._start_time = int(time.time())
        self._wake.set()

    def is_connected(self):
        return self._connected and self._enabled

    def _close_socket(self):
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None
            self._connected = False

    def _attempt_connect(self):
        if not self._enabled:
            return False
        if IS_WIN:
            for i in range(10):
                pipe_name = rf"\\.\pipe\discord-ipc-{i}"
                try:
                    sock = open(pipe_name, "r+b", buffering=0)
                    if self._perform_handshake(sock):
                        with self._lock:
                            self._sock = sock
                            self._connected = True
                        return True
                    else:
                        try:
                            sock.close()
                        except Exception:
                            pass
                except Exception:
                    continue
        else:
            sock_paths = [
                os.path.join(os.environ.get("XDG_RUNTIME_DIR", ""), "discord-ipc-0"),
                "/tmp/discord-ipc-0",
                f"{tempfile.gettempdir()}/discord-ipc-0",
            ]
            for p in sock_paths:
                if os.path.exists(p):
                    try:
                        import socket
                        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        sock.connect(p)
                        if self._perform_handshake(sock):
                            with self._lock:
                                self._sock = sock
                                self._connected = True
                            return True
                        else:
                            try:
                                sock.close()
                            except Exception:
                                pass
                    except Exception:
                        continue
        return False

    def _perform_handshake(self, sock):
        try:
            handshake = json.dumps({"v": 1, "client_id": self.CLIENT_ID}).encode("utf-8")
            header = struct.pack("<II", 0, len(handshake))
            if hasattr(sock, "write"):
                sock.write(header + handshake)
                resp_hdr = sock.read(8)
            else:
                sock.sendall(header + handshake)
                resp_hdr = sock.recv(8)
            if len(resp_hdr) == 8:
                op, length = struct.unpack("<II", resp_hdr)
                if hasattr(sock, "read"):
                    body = sock.read(length)
                else:
                    body = sock.recv(length)
                return op == 1
        except Exception:
            pass
        return False

    def _run_loop(self):
        while self._running:
            try:
                if self._enabled:
                    if not self._connected:
                        if self._attempt_connect():
                            self._send_activity()
                    else:
                        self._send_activity()
            except Exception:
                self._close_socket()
            self._wake.wait(4)
            self._wake.clear()

    def _send_activity(self):
        if not self._connected or not self._sock or not self._enabled:
            return
        with self._lock:
            try:
                frame = {
                    "cmd": "SET_ACTIVITY",
                    "args": {
                        "pid": os.getpid(),
                        "activity": {
                            "details": self._current_details,
                            "state": self._current_state,
                            "timestamps": {"start": self._start_time},
                            "assets": {
                                "large_image": f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/assets/geodesync-brand-2026.png",
                                "large_text": f"GeodeSync v{APP_VERSION} · Geometry Dash Mod Manager",
                                "small_image": f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/assets/geodesync-brand-2026.png",
                                "small_text": "GeodeSync"
                            },
                            "buttons": [
                                {"label": "View GitHub Repo", "url": f"https://github.com/{GITHUB_REPO}"},
                                {"label": "Join Discord Server", "url": "https://discord.gg/tyQG5xNGCx"}
                            ],
                            "metadata": {
                                "button_urls": [
                                    f"https://github.com/{GITHUB_REPO}",
                                    "https://discord.gg/tyQG5xNGCx"
                                ]
                            }
                        }
                    },
                    "nonce": str(time.time())
                }
                data = json.dumps(frame).encode("utf-8")
                header = struct.pack("<II", 1, len(data))
                payload = header + data
                if hasattr(self._sock, "write"):
                    self._sock.write(payload)
                    resp_hdr = self._sock.read(8)
                    if len(resp_hdr) == 8:
                        _, length = struct.unpack("<II", resp_hdr)
                        self._sock.read(length)
                    else:
                        self._connected = False
                elif hasattr(self._sock, "sendall"):
                    self._sock.sendall(payload)
                    resp_hdr = self._sock.recv(8)
                    if len(resp_hdr) == 8:
                        _, length = struct.unpack("<II", resp_hdr)
                        self._sock.recv(length)
                    else:
                        self._connected = False
            except Exception:
                self._connected = False

    def update_presence(self, details=None, state=None, reset_timer=False, geode_ver=None):
        changed = False
        if details is not None and details != self._current_details:
            self._current_details = str(details)
            changed = True
        if state is not None and state != self._current_state:
            self._current_state = str(state)
            changed = True
        if geode_ver is not None and str(geode_ver) != self._geode_ver:
            self._geode_ver = str(geode_ver)
            changed = True
        if reset_timer:
            self._start_time = int(time.time())
            changed = True
        if changed:
            self._wake.set()

    def clear_presence(self):
        if not self._connected or not self._sock:
            return
        with self._lock:
            try:
                frame = {
                    "cmd": "SET_ACTIVITY",
                    "args": {
                        "pid": os.getpid(),
                        "activity": None
                    },
                    "nonce": str(time.time())
                }
                data = json.dumps(frame).encode("utf-8")
                header = struct.pack("<II", 1, len(data))
                payload = header + data
                if hasattr(self._sock, "write"):
                    self._sock.write(payload)
                elif hasattr(self._sock, "sendall"):
                    self._sock.sendall(payload)
            except Exception:
                pass
        self._close_socket()

    def close(self):
        self._running = False
        self._wake.set()
        self.clear_presence()

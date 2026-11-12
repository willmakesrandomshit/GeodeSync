"""Centralized, platform-aware, windowless process management for GeodeSync."""

import os
import sys
import subprocess

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

SW_HIDE = 0
STARTF_USESHOWWINDOW = 1
CREATE_NO_WINDOW = 0x08000000


class _StartupInfoFallback:
    def __init__(self):
        self.dwFlags = 0
        self.wShowWindow = 0


def get_silent_startupinfo():
    """Return STARTUPINFO configured to hide console windows on Windows."""
    if IS_WIN:
        startupinfo_cls = getattr(subprocess, "STARTUPINFO", _StartupInfoFallback)
        si = startupinfo_cls()
        si.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", STARTF_USESHOWWINDOW)
        si.wShowWindow = getattr(subprocess, "SW_HIDE", SW_HIDE)
        return si
    return None


def get_silent_creationflags(extra_flags=0):
    """Ensure CREATE_NO_WINDOW is set on Windows subprocesses to eliminate cmd/conhost popups."""
    flags = int(extra_flags or 0)
    if IS_WIN:
        flags |= getattr(subprocess, "CREATE_NO_WINDOW", CREATE_NO_WINDOW)
    return flags


def safe_run_command(cmd, timeout=None, check=False, cwd=None, env=None, input=None, text=True):
    """Run a command with guaranteed windowless execution on Windows."""
    si = get_silent_startupinfo()
    flags = get_silent_creationflags()
    return subprocess.run(
        cmd,
        startupinfo=si,
        creationflags=flags,
        timeout=timeout,
        check=check,
        cwd=cwd,
        env=env,
        input=input,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
    )


def safe_check_output(cmd, timeout=None, cwd=None, env=None, text=True):
    """Check command output with guaranteed windowless execution on Windows."""
    si = get_silent_startupinfo()
    flags = get_silent_creationflags()
    res = subprocess.run(
        cmd,
        startupinfo=si,
        creationflags=flags,
        timeout=timeout,
        check=True,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
    )
    return res.stdout


def safe_popen_command(cmd, cwd=None, env=None, stdout=None, stderr=None, stdin=None, extra_flags=0, close_fds=True):
    """Launch a process asynchronously with guaranteed windowless execution on Windows."""
    si = get_silent_startupinfo()
    flags = get_silent_creationflags(extra_flags)
    return subprocess.Popen(
        cmd,
        startupinfo=si,
        creationflags=flags,
        cwd=cwd,
        env=env,
        stdout=stdout,
        stderr=stderr,
        stdin=stdin,
        close_fds=close_fds if not IS_WIN else False,
    )


def is_win_process_running(target_exe):
    """High-speed native Windows process search using Toolhelp32 snapshot (zero subprocesses, <5ms)."""
    if not IS_WIN:
        return False
    target = target_exe.lower()
    try:
        import ctypes
        from ctypes import wintypes
        TH32CS_SNAPPROCESS = 0x00000002

        class PROCESSENTRY32(ctypes.Structure):
            _fields_ = [
                ('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD),
                ('th32ProcessID', wintypes.DWORD), ('th32DefaultHeapID', ctypes.c_size_t),
                ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD),
                ('th32ParentProcessID', wintypes.DWORD), ('pcPriClassBase', wintypes.LONG),
                ('dwFlags', wintypes.DWORD), ('szExeFile', ctypes.c_char * 260)
            ]

        hSnap = ctypes.windll.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if hSnap == -1:
            return False
        pe = PROCESSENTRY32()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
        found = False
        if ctypes.windll.kernel32.Process32First(hSnap, ctypes.byref(pe)):
            while True:
                if pe.szExeFile.decode('utf-8', errors='ignore').lower() == target:
                    found = True
                    break
                if not ctypes.windll.kernel32.Process32Next(hSnap, ctypes.byref(pe)):
                    break
        ctypes.windll.kernel32.CloseHandle(hSnap)
        return found
    except Exception:
        return False

import os
import sys
import re
import json
import shutil
import stat
import time
import winreg
import urllib.request
import webbrowser
import threading
import subprocess
import winsound
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

# Enable DPI Awareness for high-res monitors
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

APP_VERSION = "1.1.2"
GITHUB_REPO = "willmakesrandomshit/GeodeSync"
CONFIG_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.json"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

APP_ID = "322170"
DEPOT_ID = "322171"
DEFAULT_MANIFEST = "3816559102876907245"
DEFAULT_TARGET_GD = "2.2081"

# Known version depot manifests
KNOWN_VERSIONS = {
    "2.2081 (Geode Compatible • Recommended)": {
        "manifest": "3816559102876907245",
        "ver": "2.2081",
        "size": 10700288
    },
    "2.2074 (Previous 2.2 Sub-update)": {
        "manifest": "4978051680517726588",
        "ver": "2.2074",
        "size": 10698752
    },
    "2.113 (Classic 2.11 Legacy)": {
        "manifest": "7938363717144760233",
        "ver": "2.113",
        "size": 7578624
    }
}

SIZE_22081 = 10700288
SIZE_2209 = 13178880
EXPECTED_DEPOT_BYTES = 204000000  # ~195 MB


def safe_copy_item(src, dst, max_retries=5):
    for i in range(max_retries):
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            return True
        except PermissionError:
            time.sleep(0.4)
        except Exception as e:
            if i == max_retries - 1:
                raise e
            time.sleep(0.4)
    return False


class GDManager:
    def __init__(self):
        self.steam_path = self.detect_steam_path()
        self.gd_path = self.detect_gd_path()
        self.manifest_path = self.get_manifest_path()
        self.target_manifest = DEFAULT_MANIFEST
        self.target_gd_version = DEFAULT_TARGET_GD

    def detect_steam_path(self):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
                val, _ = winreg.QueryValueEx(key, "SteamPath")
                if os.path.exists(val):
                    return os.path.abspath(val)
        except Exception:
            pass

        default = r"C:\Program Files (x86)\Steam"
        if os.path.exists(default):
            return default
        return None

    def get_steam_exe(self):
        if self.steam_path:
            exe = os.path.join(self.steam_path, "steam.exe")
            if os.path.exists(exe):
                return exe
        return None

    def is_steam_running(self):
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            output = subprocess.check_output(
                ["tasklist", "/FI", "IMAGENAME eq steam.exe", "/NH"],
                startupinfo=si,
                creationflags=0x08000000
            ).decode(errors="ignore")
            return "steam.exe" in output.lower()
        except Exception:
            return True

    def detect_gd_path(self):
        if not self.steam_path:
            return None

        default_gd = os.path.join(self.steam_path, "steamapps", "common", "Geometry Dash")
        if os.path.exists(default_gd):
            return default_gd

        vdf_path = os.path.join(self.steam_path, "steamapps", "libraryfolders.vdf")
        if os.path.exists(vdf_path):
            try:
                with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                matches = re.findall(r'"path"\s+"([^"]+)"', content, re.IGNORECASE)
                for lib_dir in matches:
                    clean_dir = lib_dir.replace(r"\\", "\\")
                    candidate = os.path.join(clean_dir, "steamapps", "common", "Geometry Dash")
                    if os.path.exists(candidate):
                        return candidate
            except Exception:
                pass

        return None

    def get_manifest_path(self):
        if self.gd_path:
            parent = os.path.dirname(os.path.dirname(self.gd_path))
            m_path = os.path.join(parent, f"appmanifest_{APP_ID}.acf")
            if os.path.exists(m_path):
                return m_path

        if self.steam_path:
            m_path = os.path.join(self.steam_path, "steamapps", f"appmanifest_{APP_ID}.acf")
            if os.path.exists(m_path):
                return m_path
        return None

    def get_depot_path(self):
        if self.steam_path:
            d_path = os.path.join(self.steam_path, "steamapps", "content", f"app_{APP_ID}", f"depot_{DEPOT_ID}")
            return d_path
        return None

    def get_depot_current_size(self):
        d_path = self.get_depot_path()
        if not d_path or not os.path.exists(d_path):
            return 0
        total = 0
        try:
            for root, dirs, files in os.walk(d_path):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        total += os.path.getsize(fp)
                    except Exception:
                        pass
        except Exception:
            pass
        return total

    def get_steam_console_log(self):
        if self.steam_path:
            log_p = os.path.join(self.steam_path, "logs", "console_log.txt")
            if os.path.exists(log_p):
                return log_p
        return None

    def get_save_data_dir(self):
        appdata = os.environ.get("LOCALAPPDATA")
        if appdata:
            gd_save = os.path.join(appdata, "GeometryDash")
            if os.path.exists(gd_save):
                return gd_save
        return None

    def get_crashlogs_dir(self):
        candidates = []
        if self.gd_path:
            candidates.append(os.path.join(self.gd_path, "geode", "crashlogs"))
        appdata = os.environ.get("LOCALAPPDATA")
        if appdata:
            candidates.append(os.path.join(appdata, "GeometryDash", "geode", "crashlogs"))
        for c in candidates:
            if os.path.exists(c):
                return c
        return candidates[0] if candidates else None

    def get_gd_version_info(self):
        if not self.gd_path:
            return "Not Installed", "#ef4444"

        exe_path = os.path.join(self.gd_path, "GeometryDash.exe")
        if not os.path.exists(exe_path):
            return "Missing Executable", "#ef4444"

        try:
            size = os.path.getsize(exe_path)
        except Exception:
            return "Inaccessible", "#ef4444"

        if size == SIZE_22081:
            return f"{self.target_gd_version} (Geode Compatible)", "#10b981"
        elif size == SIZE_2209:
            return "2.209 (Incompatible with Geode)", "#f59e0b"
        else:
            mb = round(size / (1024 * 1024), 2)
            return f"Custom Build ({mb} MB)", "#60a5fa"

    def is_current_gd_22081(self):
        if not self.gd_path:
            return False
        exe = os.path.join(self.gd_path, "GeometryDash.exe")
        if os.path.exists(exe):
            try:
                return os.path.getsize(exe) == SIZE_22081
            except Exception:
                return False
        return False

    def is_gd_process_running(self):
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            output = subprocess.check_output(
                ["tasklist", "/FI", "IMAGENAME eq GeometryDash.exe", "/NH"],
                startupinfo=si,
                creationflags=0x08000000
            ).decode(errors="ignore")
            return "geometrydash.exe" in output.lower()
        except Exception:
            return False

    def close_gd_process(self):
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(
                ["taskkill", "/F", "/IM", "GeometryDash.exe"],
                startupinfo=si,
                creationflags=0x08000000,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(1)
            return True
        except Exception:
            return False

    def is_manifest_locked(self):
        if not self.manifest_path or not os.path.exists(self.manifest_path):
            return False
        try:
            mode = os.stat(self.manifest_path).st_mode
            return not bool(mode & stat.S_IWRITE)
        except Exception:
            return False

    def set_manifest_locked(self, lock: bool):
        if not self.manifest_path or not os.path.exists(self.manifest_path):
            raise FileNotFoundError("appmanifest_322170.acf not found!")

        for attempt in range(5):
            try:
                if lock:
                    os.chmod(self.manifest_path, stat.S_IREAD)
                else:
                    os.chmod(self.manifest_path, stat.S_IWRITE | stat.S_IREAD)
                return
            except PermissionError:
                time.sleep(0.3)
            except Exception as e:
                if attempt == 4:
                    raise e
                time.sleep(0.3)

    def has_downloaded_depot(self):
        d_path = self.get_depot_path()
        if d_path and os.path.exists(d_path):
            exe = os.path.join(d_path, "GeometryDash.exe")
            try:
                return os.path.exists(exe) and os.path.getsize(exe) == SIZE_22081
            except Exception:
                return False
        return False

    def is_geode_installed(self):
        if not self.gd_path:
            return False
        dll = os.path.join(self.gd_path, "Geode.dll")
        proxy = os.path.join(self.gd_path, "XInput1_4.dll")
        geode_dir = os.path.join(self.gd_path, "geode")
        return (os.path.exists(dll) and os.path.exists(proxy)) or os.path.exists(geode_dir)


class ModernButton(tk.Canvas):
    def __init__(self, parent, text, command, bg="#8b5cf6", hover_bg="#7c3aed", fg="#ffffff", height=46, width=None, font=("Segoe UI", 11, "bold")):
        super().__init__(parent, height=height, bg=parent["bg"], highlightthickness=0)
        self.command = command
        self.normal_bg = bg
        self.hover_bg = hover_bg
        self.current_bg = bg
        self.fg = fg
        self.text = text
        self.font = font
        self.height = height
        self.btn_width = width
        self.enabled = True

        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        self.bind("<Configure>", self.draw)

    def draw(self, event=None):
        self.delete("all")
        w = self.winfo_width() if not self.btn_width else self.btn_width
        h = self.height
        r = 10

        if not self.enabled:
            fill = "#374151"
            text_color = "#9ca3af"
        else:
            fill = self.current_bg
            text_color = self.fg

        self.create_arc((0, 0, r * 2, r * 2), start=90, extent=90, fill=fill, outline="")
        self.create_arc((w - r * 2, 0, w, r * 2), start=0, extent=90, fill=fill, outline="")
        self.create_arc((0, h - r * 2, r * 2, h), start=180, extent=90, fill=fill, outline="")
        self.create_arc((w - r * 2, h - r * 2, w, h), start=270, extent=90, fill=fill, outline="")
        self.create_rectangle((r, 0, w - r, h), fill=fill, outline="")
        self.create_rectangle((0, r, w, h - r), fill=fill, outline="")

        self.create_text(w / 2, h / 2, text=self.text, fill=text_color, font=self.font)

    def on_enter(self, event):
        if self.enabled:
            self.current_bg = self.hover_bg
            self.draw()

    def on_leave(self, event):
        if self.enabled:
            self.current_bg = self.normal_bg
            self.draw()

    def on_click(self, event):
        if self.enabled and self.command:
            self.command()

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        self.draw()

    def set_config(self, text: str, bg: str, hover_bg: str, command=None):
        self.text = text
        self.normal_bg = bg
        self.hover_bg = hover_bg
        self.current_bg = bg
        if command:
            self.command = command
        self.draw()


class GeodeSyncApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"GeodeSync v{APP_VERSION} • 1-Click Geometry Dash Suite")
        self.geometry("780x790")
        self.minsize(720, 720)
        self.configure(bg="#0f141c")

        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"geodesync.switcher.v{APP_VERSION}")
        except Exception:
            pass

        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.mgr = GDManager()
        self.latest_release_url = None
        self.is_downloading_depot = False

        self.create_ui()
        self.refresh_status()

        threading.Thread(target=self.check_remote_updates, daemon=True).start()

    def create_ui(self):
        # Update Banner
        self.update_banner = tk.Frame(self, bg="#064e3b", padx=16, pady=8)
        self.update_label = tk.Label(self.update_banner, text="✨ New update available!", font=("Segoe UI", 9, "bold"), fg="#34d399", bg="#064e3b")
        self.update_label.pack(side="left")

        self.update_action_btn = tk.Button(self.update_banner, text="Update Now (1-Click)", command=self.open_update_link, font=("Segoe UI", 8, "bold"), bg="#10b981", fg="#ffffff", activebackground="#059669", activeforeground="#ffffff", relief="flat", padx=10, pady=2, cursor="hand2")
        self.update_action_btn.pack(side="right")

        # Header banner
        header = tk.Frame(self, bg="#161e2e", padx=24, pady=14)
        header.pack(fill="x")

        title_box = tk.Frame(header, bg="#161e2e")
        title_box.pack(side="left")

        title = tk.Label(title_box, text=f"⚡ GeodeSync  v{APP_VERSION}", font=("Segoe UI", 16, "bold"), fg="#ffffff", bg="#161e2e")
        title.pack(anchor="w")

        subtitle = tk.Label(title_box, text="1-Click Geometry Dash Mod Protector, Save Manager & Auto-Downgrader", font=("Segoe UI", 9), fg="#94a3b8", bg="#161e2e")
        subtitle.pack(anchor="w")

        badge_box = tk.Frame(header, bg="#161e2e")
        badge_box.pack(side="right")

        help_btn = tk.Button(badge_box, text="❓ How It Works", command=self.show_help_dialog, font=("Segoe UI", 9, "bold"), bg="#1e293b", fg="#38bdf8", activebackground="#334155", activeforeground="#ffffff", relief="flat", padx=10, pady=5, cursor="hand2")
        help_btn.pack(side="right", padx=6)

        # Main Body
        body = tk.Frame(self, bg="#0f141c", padx=24, pady=10)
        body.pack(fill="both", expand=True)

        # 1. SMART GUIDED NEXT STEP
        self.guide_card = tk.Frame(body, bg="#1e293b", padx=18, pady=12, highlightbackground="#3b82f6", highlightthickness=2)
        self.guide_card.pack(fill="x", pady=(0, 10))

        guide_top = tk.Frame(self.guide_card, bg="#1e293b")
        guide_top.pack(fill="x")

        self.guide_badge = tk.Label(guide_top, text="RECOMMENDED ACTION", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#0f172a", padx=8, pady=2)
        self.guide_badge.pack(side="left")

        self.guide_title = tk.Label(self.guide_card, text="Checking your installation...", font=("Segoe UI", 13, "bold"), fg="#ffffff", bg="#1e293b")
        self.guide_title.pack(anchor="w", pady=(6, 2))

        self.guide_desc = tk.Label(self.guide_card, text="Please wait while GeodeSync detects your game setup.", font=("Segoe UI", 9), fg="#94a3b8", bg="#1e293b", wraplength=680, justify="left")
        self.guide_desc.pack(anchor="w", pady=(0, 8))

        # Real-Time Progress Bar Frame (Hidden by default, shown during downloads/tasks)
        self.progress_frame = tk.Frame(self.guide_card, bg="#1e293b")
        self.progress_lbl = tk.Label(self.progress_frame, text="Downloading Steam Depot...", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#1e293b")
        self.progress_lbl.pack(anchor="w", pady=(0, 3))
        
        # Style ttk Progressbar
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Cyber.Horizontal.TProgressbar", background="#8b5cf6", troughcolor="#0f172a", bordercolor="#1e293b", lightcolor="#a855f7", darkcolor="#7c3aed")
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, style="Cyber.Horizontal.TProgressbar", orient="horizontal", mode="determinate", length=400)
        self.progress_bar.pack(fill="x", pady=(0, 6))

        # The One Primary Action Button
        self.primary_btn = ModernButton(
            self.guide_card,
            text="Checking...",
            command=None,
            bg="#3b82f6",
            hover_bg="#2563eb",
            height=44,
            font=("Segoe UI", 11, "bold")
        )
        self.primary_btn.pack(fill="x")

        # 2. STATUS SUMMARY CHIPS
        status_card = tk.Frame(body, bg="#1a2333", padx=16, pady=8, highlightbackground="#2d3748", highlightthickness=1)
        status_card.pack(fill="x", pady=(0, 8))

        st_title = tk.Label(status_card, text="SYSTEM DETECTION STATUS", font=("Segoe UI", 8, "bold"), fg="#64748b", bg="#1a2333")
        st_title.pack(anchor="w", pady=(0, 4))

        grid_chips = tk.Frame(status_card, bg="#1a2333")
        grid_chips.pack(fill="x")

        f_v = tk.Frame(grid_chips, bg="#1a2333")
        f_v.pack(side="left", expand=True, fill="x", padx=3)
        tk.Label(f_v, text="Geometry Dash", font=("Segoe UI", 8), fg="#94a3b8", bg="#1a2333").pack(anchor="w")
        self.ver_badge = tk.Label(f_v, text="Detecting...", font=("Segoe UI", 9, "bold"), fg="#10b981", bg="#132a24", padx=6, pady=2)
        self.ver_badge.pack(anchor="w", pady=(2, 0))

        f_g = tk.Frame(grid_chips, bg="#1a2333")
        f_g.pack(side="left", expand=True, fill="x", padx=3)
        tk.Label(f_g, text="Geode Mod Loader", font=("Segoe UI", 8), fg="#94a3b8", bg="#1a2333").pack(anchor="w")
        self.geode_badge = tk.Label(f_g, text="Detecting...", font=("Segoe UI", 9, "bold"), fg="#a855f7", bg="#2a163d", padx=6, pady=2)
        self.geode_badge.pack(anchor="w", pady=(2, 0))

        f_l = tk.Frame(grid_chips, bg="#1a2333")
        f_l.pack(side="left", expand=True, fill="x", padx=3)
        tk.Label(f_l, text="Auto-Update Lock", font=("Segoe UI", 8), fg="#94a3b8", bg="#1a2333").pack(anchor="w")
        self.lock_badge = tk.Label(f_l, text="Detecting...", font=("Segoe UI", 9, "bold"), fg="#f59e0b", bg="#332412", padx=6, pady=2)
        self.lock_badge.pack(anchor="w", pady=(2, 0))

        # 3. UTILITY TOOLBAR (Expanded with New v1.1.2 Power Tools)
        tools_card = tk.Frame(body, bg="#161e2e", padx=12, pady=8, highlightbackground="#2d3748", highlightthickness=1)
        tools_card.pack(fill="x", pady=(0, 8))

        row1 = tk.Frame(tools_card, bg="#161e2e")
        row1.pack(fill="x", pady=(0, 4))

        tk.Label(row1, text="Saves & Mods:", font=("Segoe UI", 8, "bold"), fg="#64748b", bg="#161e2e").pack(side="left", padx=(0, 6))

        backup_save_btn = tk.Button(row1, text="💾 Backup Saves", command=self.backup_saves, font=("Segoe UI", 8, "bold"), bg="#1e293b", fg="#38bdf8", activebackground="#334155", activeforeground="#ffffff", relief="flat", padx=8, pady=3, cursor="hand2")
        backup_save_btn.pack(side="left", padx=2)

        restore_save_btn = tk.Button(row1, text="♻️ Restore Saves", command=self.restore_saves, font=("Segoe UI", 8), bg="#1e293b", fg="#94a3b8", activebackground="#334155", activeforeground="#ffffff", relief="flat", padx=8, pady=3, cursor="hand2")
        restore_save_btn.pack(side="left", padx=2)

        open_mods_btn = tk.Button(row1, text="📂 Mods Folder", command=self.open_mods_folder, font=("Segoe UI", 8), bg="#1e293b", fg="#94a3b8", activebackground="#334155", activeforeground="#ffffff", relief="flat", padx=8, pady=3, cursor="hand2")
        open_mods_btn.pack(side="left", padx=2)

        self.restore_gd_btn = tk.Button(row1, text="🔄 Restore Latest GD", command=self.upgrade_clicked, font=("Segoe UI", 8), bg="#1e293b", fg="#f59e0b", activebackground="#334155", activeforeground="#ffffff", relief="flat", padx=8, pady=3, cursor="hand2")
        self.restore_gd_btn.pack(side="right")

        # Row 2: v1.1.2 Pro Power Tools
        row2 = tk.Frame(tools_card, bg="#161e2e")
        row2.pack(fill="x", pady=(2, 0))

        tk.Label(row2, text="Pro Optimizers:", font=("Segoe UI", 8, "bold"), fg="#64748b", bg="#161e2e").pack(side="left", padx=(0, 6))

        fix_audio_btn = tk.Button(row2, text="⚡ Fix Click Delay", command=self.fix_click_delay, font=("Segoe UI", 8, "bold"), bg="#1e293b", fg="#10b981", activebackground="#334155", activeforeground="#ffffff", relief="flat", padx=8, pady=3, cursor="hand2")
        fix_audio_btn.pack(side="left", padx=2)

        crash_doc_btn = tk.Button(row2, text="🩺 Crash Doctor", command=self.run_crash_doctor, font=("Segoe UI", 8, "bold"), bg="#1e293b", fg="#c084fc", activebackground="#334155", activeforeground="#ffffff", relief="flat", padx=8, pady=3, cursor="hand2")
        crash_doc_btn.pack(side="left", padx=2)

        version_sel_btn = tk.Button(row2, text="⚙️ Version Selector", command=self.open_version_selector, font=("Segoe UI", 8), bg="#1e293b", fg="#38bdf8", activebackground="#334155", activeforeground="#ffffff", relief="flat", padx=8, pady=3, cursor="hand2")
        version_sel_btn.pack(side="left", padx=2)

        # 4. ACTIVITY LOG
        log_card = tk.Frame(body, bg="#161e2e", padx=12, pady=6, highlightbackground="#2d3748", highlightthickness=1)
        log_card.pack(fill="both", expand=True)

        log_head = tk.Frame(log_card, bg="#161e2e")
        log_head.pack(fill="x", pady=(0, 3))

        log_title = tk.Label(log_head, text="ACTIVITY LOG", font=("Segoe UI", 8, "bold"), fg="#64748b", bg="#161e2e")
        log_title.pack(side="left")

        clear_btn = tk.Button(log_head, text="Clear", command=self.clear_log, font=("Segoe UI", 7), bg="#1e293b", fg="#94a3b8", relief="flat", padx=4, pady=0, cursor="hand2")
        clear_btn.pack(side="right")

        self.log_text = tk.Text(log_card, bg="#0d1117", fg="#c9d1d9", font=("Consolas", 8), relief="flat", wrap="word", height=5, padx=8, pady=6)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.config(state="disabled")

        # Footer
        footer = tk.Frame(self, bg="#0f141c", padx=24, pady=6)
        footer.pack(fill="x", side="bottom")

        self.path_lbl = tk.Label(footer, text=f"GD Path: {self.mgr.gd_path or 'Not Found'}", font=("Segoe UI", 8), fg="#64748b", bg="#0f141c")
        self.path_lbl.pack(side="left")

        repo_link = tk.Label(footer, text=f"GitHub: {GITHUB_REPO}", font=("Segoe UI", 8, "underline"), fg="#38bdf8", bg="#0f141c", cursor="hand2")
        repo_link.pack(side="left", padx=16)
        repo_link.bind("<Button-1>", lambda e: webbrowser.open(f"https://github.com/{GITHUB_REPO}"))

        choose_path_btn = tk.Button(footer, text="Browse GD Folder...", command=self.browse_gd_path, font=("Segoe UI", 7), bg="#1e293b", fg="#94a3b8", relief="flat", padx=6, cursor="hand2")
        choose_path_btn.pack(side="right")

    def log(self, message: str, level: str = "INFO"):
        self.log_text.config(state="normal")
        time_str = datetime.now().strftime("%H:%M:%S")
        color_prefix = {
            "INFO": "[INFO]",
            "SUCCESS": "[OK]",
            "WARN": "[WARN]",
            "ERROR": "[ERR]"
        }.get(level, "[INFO]")
        self.log_text.insert("end", f"[{time_str}] {color_prefix} {message}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def play_ding(self):
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

    def refresh_status(self):
        ver_text, ver_color = self.mgr.get_gd_version_info()
        self.ver_badge.config(text=ver_text, fg=ver_color)

        is_locked = self.mgr.is_manifest_locked()
        if is_locked:
            self.lock_badge.config(text="🔒 Locked (Safe)", fg="#34d399", bg="#064e3b")
        else:
            self.lock_badge.config(text="🔓 Unlocked", fg="#f59e0b", bg="#332412")

        has_geode = self.mgr.is_geode_installed()
        if has_geode:
            self.geode_badge.config(text="✓ Installed", fg="#c084fc", bg="#2a163d")
        else:
            self.geode_badge.config(text="❌ NOT INSTALLED", fg="#f87171", bg="#3b1111")

        self.path_lbl.config(text=f"GD Path: {self.mgr.gd_path or 'Not Found'}")

        if not self.is_downloading_depot:
            self.update_smart_guide(has_geode, is_locked)

    def update_smart_guide(self, has_geode: bool, is_locked: bool):
        is_22081 = self.mgr.is_current_gd_22081()

        if not has_geode:
            self.guide_card.config(highlightbackground="#ef4444")
            self.guide_badge.config(text="ACTION REQUIRED • GEODE NOT DETECTED", fg="#f87171", bg="#450a0a")
            self.guide_title.config(text="⚠️ Geode Mod Loader Not Installed")
            self.guide_desc.config(
                text="GeodeSync requires the Geode mod loader to run mods. "
                     "Click below to automatically download and launch the official Geode installer!"
            )
            self.primary_btn.set_config(
                text="📥 1-Click Install Geode (Auto-Download Official Setup)",
                bg="#ef4444",
                hover_bg="#dc2626",
                command=self.auto_install_geode
            )
            return

        if not is_22081:
            self.guide_card.config(highlightbackground="#8b5cf6")
            self.guide_badge.config(text="AUTOMATED 1-CLICK FIX READY", fg="#c084fc", bg="#3b0764")
            self.guide_title.config(text="⚡ Automatic Downgrade & Protect")
            self.guide_desc.config(
                text=f"Geometry Dash is on 2.209 which breaks mods. "
                     f"Click below to automatically download {self.mgr.target_gd_version} from Steam, install it, and protect your game from auto-updates!"
            )
            self.primary_btn.set_config(
                text=f"⚡ 1-Click Fix: Auto-Download & Downgrade to {self.mgr.target_gd_version}",
                bg="#8b5cf6",
                hover_bg="#7c3aed",
                command=self.start_automated_downgrade
            )
            return

        self.guide_card.config(highlightbackground="#10b981")
        self.guide_badge.config(text="ALL GOOD • READY TO PLAY", fg="#34d399", bg="#064e3b")
        self.guide_title.config(text="🎉 Everything is set! Your mods are ready.")
        self.guide_desc.config(
            text="Geometry Dash is running 2.2081 with Geode active, and Steam auto-updates are locked. You can safely launch the game and play with all your mods!"
        )
        self.primary_btn.set_config(
            text="▶ Launch Geometry Dash with Mods",
            bg="#10b981",
            hover_bg="#059669",
            command=self.launch_gd
        )

    # ==========================================
    # v1.1.2 FEATURE: AUTO-INSTALL GEODE (1-CLICK)
    # ==========================================
    def auto_install_geode(self):
        threading.Thread(target=self._run_auto_geode_install, daemon=True).start()

    def _run_auto_geode_install(self):
        self.log("Fetching latest official Geode release from GitHub...", "INFO")
        self.progress_frame.pack(fill="x", pady=(0, 8), before=self.primary_btn)
        self.progress_bar["value"] = 15
        self.progress_lbl.config(text="Contacting GitHub for official Geode installer...")
        self.primary_btn.set_enabled(False)

        try:
            req = urllib.request.Request("https://api.github.com/repos/geode-sdk/geode/releases/latest", headers={"User-Agent": "GeodeSync-Client"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                download_url = None
                installer_name = "geode-installer.exe"
                for asset in data.get("assets", []):
                    if asset.get("name", "").endswith(".exe") and "win" in asset.get("name", "").lower():
                        download_url = asset.get("browser_download_url")
                        installer_name = asset.get("name")
                        break

            if not download_url:
                raise Exception("Could not locate Windows installer asset in release.")

            dest_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), installer_name)
            self.log(f"Downloading {installer_name}...", "INFO")
            self.progress_lbl.config(text=f"Downloading {installer_name}...")
            self.progress_bar["value"] = 40

            urllib.request.urlretrieve(download_url, dest_path)
            self.progress_bar["value"] = 100
            self.log(f"Launching {installer_name}...", "SUCCESS")
            self.progress_frame.pack_forget()
            self.primary_btn.set_enabled(True)

            os.startfile(dest_path)
            messagebox.showinfo(
                "Geode Installer Launched",
                "The official Geode installer has started!\n\n"
                "Follow the on-screen steps to complete installation, then return to GeodeSync."
            )
            time.sleep(3)
            self.refresh_status()

        except Exception as e:
            self.log(f"Auto-install error: {e}. Opening geode-sdk.org instead...", "WARN")
            self.progress_frame.pack_forget()
            self.primary_btn.set_enabled(True)
            webbrowser.open("https://geode-sdk.org")
            self.refresh_status()

    # ==========================================
    # v1.1.2 FEATURE: REAL-TIME STEAM DOWNLOAD TRACKER
    # ==========================================
    def start_automated_downgrade(self):
        if self.is_downloading_depot:
            return

        if self.mgr.is_gd_process_running():
            res = messagebox.askyesno(
                "Geometry Dash Running",
                "Geometry Dash is currently open. It must be closed before game files can be replaced.\n\n"
                "Would you like GeodeSync to close GD automatically now?"
            )
            if res:
                self.mgr.close_gd_process()
            else:
                return

        threading.Thread(target=self._run_auto_downgrade, daemon=True).start()

    def _run_auto_downgrade(self):
        if not self.mgr.gd_path:
            self.log("Geometry Dash folder not detected.", "ERROR")
            messagebox.showerror("Error", "Geometry Dash installation directory not found.")
            return

        steam_exe = self.mgr.get_steam_exe()
        if not steam_exe:
            self.log("Steam executable not found.", "ERROR")
            messagebox.showerror("Error", "Steam.exe not found.")
            return

        if not self.mgr.is_steam_running():
            self.log("Steam is not currently running. Launching Steam...", "INFO")
            try:
                subprocess.Popen([steam_exe])
                time.sleep(5)
            except Exception as e:
                self.log(f"Warning launching Steam: {e}", "WARN")

        if self.mgr.has_downloaded_depot():
            self.log("2.2081 files already present on disk. Applying directly...", "INFO")
            self._apply_downgrade_files()
            return

        log_path = self.mgr.get_steam_console_log()
        initial_log_offset = 0
        if log_path and os.path.exists(log_path):
            try:
                initial_log_offset = os.path.getsize(log_path)
            except Exception:
                initial_log_offset = 0

        self.is_downloading_depot = True
        self.guide_title.config(text="⏳ Steam is downloading files in background...")
        self.guide_desc.config(text="Monitoring Steam depot progress in real time...")
        self.primary_btn.set_config(text="⏳ Downloading from Steam... (Please wait)", bg="#334155", hover_bg="#334155")
        self.primary_btn.set_enabled(False)

        # Show real-time progress bar
        self.progress_frame.pack(fill="x", pady=(0, 8), before=self.primary_btn)
        self.progress_bar["value"] = 5
        self.progress_lbl.config(text="Sending download command to Steam...")

        args = [steam_exe, "-console", "+download_depot", APP_ID, DEPOT_ID, str(self.mgr.target_manifest)]
        self.log("Sending automated download command to Steam...", "INFO")

        try:
            subprocess.Popen(args)
            self.log("Triggered Steam depot download! Monitoring live progress...", "SUCCESS")
        except Exception as e:
            self.log(f"Failed to execute Steam command: {e}", "ERROR")
            self.is_downloading_depot = False
            self.progress_frame.pack_forget()
            self.primary_btn.set_enabled(True)
            self.refresh_status()
            return

        start_time = time.time()
        download_finished = False

        while time.time() - start_time < 360:
            time.sleep(1.5)

            # Update live progress bar based on depot size
            cur_bytes = self.mgr.get_depot_current_size()
            cur_mb = round(cur_bytes / (1024 * 1024), 1)
            pct = min(96, int((cur_bytes / EXPECTED_DEPOT_BYTES) * 100))
            if pct > 5:
                self.progress_bar["value"] = pct
                self.progress_lbl.config(text=f"Downloading from Steam: {cur_mb} MB / ~195 MB ({pct}%)")

            # Check Steam console log for completion flag
            if log_path and os.path.exists(log_path):
                try:
                    current_size = os.path.getsize(log_path)
                    if current_size > initial_log_offset:
                        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                            f.seek(initial_log_offset)
                            new_content = f.read()
                            if "Depot download complete" in new_content and "depot_322171" in new_content:
                                download_finished = True
                                break
                except Exception:
                    pass

            if download_finished or self.mgr.has_downloaded_depot():
                download_finished = True
                break

        self.is_downloading_depot = False
        self.progress_bar["value"] = 100
        self.progress_lbl.config(text="Download complete! Applying files...")
        time.sleep(0.5)
        self.progress_frame.pack_forget()
        self.primary_btn.set_enabled(True)

        if download_finished or self.mgr.has_downloaded_depot():
            self.log("Steam depot download completed!", "SUCCESS")
            self._apply_downgrade_files()
        else:
            self.log("Steam download timed out or took longer than 6 mins.", "WARN")
            messagebox.showwarning("Download in Progress", "Steam is still downloading in the background. Check your Steam client and click again when ready!")
            self.refresh_status()

    def _apply_downgrade_files(self):
        depot = self.mgr.get_depot_path()
        if not depot or not os.path.exists(depot):
            self.log("Depot path not found.", "ERROR")
            return

        self.log("Backing up current files...", "INFO")
        backup_dir = os.path.join(self.mgr.gd_path, "backup_latest")
        try:
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir, exist_ok=True)
                for f in ["GeometryDash.exe", "libcocos2d.dll", "libExtensions.dll"]:
                    src_f = os.path.join(self.mgr.gd_path, f)
                    if os.path.exists(src_f):
                        safe_copy_item(src_f, os.path.join(backup_dir, f))
                self.log("Created backup of current files.", "INFO")
        except Exception as e:
            self.log(f"Backup warning: {e}", "WARN")

        self.log(f"Installing {self.mgr.target_gd_version} game files...", "INFO")
        try:
            for item in os.listdir(depot):
                s = os.path.join(depot, item)
                d = os.path.join(self.mgr.gd_path, item)
                safe_copy_item(s, d)
            self.log(f"Game files successfully replaced with {self.mgr.target_gd_version}!", "SUCCESS")
        except Exception as e:
            self.log(f"Failed to copy files: {e}", "ERROR")
            messagebox.showerror("Error", f"Failed to overwrite game files:\n{e}")
            self.refresh_status()
            return

        try:
            self.mgr.set_manifest_locked(True)
            self.log("Locked Steam appmanifest_322170.acf to Read-Only.", "SUCCESS")
        except Exception as e:
            self.log(f"Warning locking manifest: {e}", "WARN")

        self.refresh_status()
        self.play_ding()
        self.log(f"1-Click Fix Complete! Geometry Dash is now {self.mgr.target_gd_version}.", "SUCCESS")
        messagebox.showinfo("1-Click Fix Complete!", f"Geometry Dash has been successfully downgraded to {self.mgr.target_gd_version}!\n\nSteam auto-updates are locked. Geode and your mods are ready to play.")

    # ==========================================
    # v1.1.2 FEATURE: 1-CLICK AUDIO & CLICK DELAY OPTIMIZER
    # ==========================================
    def fix_click_delay(self):
        applied = []
        appdata = os.environ.get("LOCALAPPDATA")
        if not appdata:
            messagebox.showerror("Error", "Could not locate LocalAppData folder.")
            return

        # 1. FMOD Hacker low-latency configuration (~2.7ms)
        fmod_dir = os.path.join(appdata, "GeometryDash", "geode", "mods", "square3ang.fmod-hacker")
        try:
            os.makedirs(fmod_dir, exist_ok=True)
            fmod_settings = {
                "output-type": "WASAPI",
                "sample-rate": "48000",
                "buffer-size": "128",
                "master-volume": 100,
                "output-device": -1
            }
            with open(os.path.join(fmod_dir, "settings.json"), "w", encoding="utf-8") as f:
                json.dump(fmod_settings, f, indent=2)
            applied.append("✓ FMOD Audio Buffer set to 128 samples / WASAPI (slashes audio delay to ~2.7ms)")
        except Exception as e:
            self.log(f"FMOD optimizer note: {e}", "WARN")

        # 2. CBF Mouse Lag Fix
        cbf_dir = os.path.join(appdata, "GeometryDash", "geode", "mods", "syzzi.click_between_frames")
        cbf_file = os.path.join(cbf_dir, "settings.json")
        try:
            if os.path.exists(cbf_file):
                with open(cbf_file, "r", encoding="utf-8") as f:
                    cbf_data = json.load(f)
                cbf_data["mouse-fix"] = True
                with open(cbf_file, "w", encoding="utf-8") as f:
                    json.dump(cbf_data, f, indent=2)
                applied.append("✓ Click Between Frames (CBF) 'mouse-fix' enabled for high polling rate mice")
        except Exception:
            pass

        # 3. Click Sounds Queue Optimization
        cs_dir = os.path.join(appdata, "GeometryDash", "geode", "mods", "beat.click-sound")
        cs_file = os.path.join(cs_dir, "settings.json")
        try:
            if os.path.exists(cs_file):
                with open(cs_file, "r", encoding="utf-8") as f:
                    cs_data = json.load(f)
                cs_data["optimize-sounds"] = True
                with open(cs_file, "w", encoding="utf-8") as f:
                    json.dump(cs_data, f, indent=2)
                applied.append("✓ Click Sounds 'optimize-sounds' enabled to prevent audio queuing")
        except Exception:
            pass

        self.play_ding()
        self.log("Applied Low-Latency Audio & Click Optimizations!", "SUCCESS")
        summary_msg = "Successfully applied GD Audio & Input Optimizations:\n\n" + "\n".join(applied) + "\n\nRestart Geometry Dash to enjoy near-zero click delay!"
        messagebox.showinfo("⚡ Audio & Click Optimizer", summary_msg)

    # ==========================================
    # v1.1.2 FEATURE: CRASH DOCTOR (DIAGNOSE BROKEN MODS)
    # ==========================================
    def run_crash_doctor(self):
        crash_dir = self.mgr.get_crashlogs_dir()
        if not crash_dir or not os.path.exists(crash_dir):
            messagebox.showinfo("🩺 Crash Doctor", "No crash logs folder found! Your Geometry Dash installation looks clean.")
            return

        logs = [os.path.join(crash_dir, f) for f in os.listdir(crash_dir) if f.endswith(".log")]
        if not logs:
            messagebox.showinfo("🩺 Crash Doctor", "Great news! Zero crash logs were detected. No broken mods found!")
            return

        logs.sort(key=os.path.getmtime, reverse=True)
        latest_log = logs[0]

        culprit = None
        details = []
        try:
            with open(latest_log, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            for line in content.splitlines():
                if "Faulty Mod:" in line and "<Unknown>" not in line:
                    culprit = line.split("Faulty Mod:")[1].strip()
                    break
                if "Failed to load:" in line:
                    details.append(line.strip())

            if not culprit:
                # Scan stack trace for known mod id patterns
                matches = re.findall(r"([a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+)\.dll", content)
                if matches:
                    culprit = matches[0]

        except Exception as e:
            self.log(f"Crash Doctor scan error: {e}", "WARN")

        time_str = datetime.fromtimestamp(os.path.getmtime(latest_log)).strftime("%Y-%m-%d %H:%M:%S")

        if culprit:
            res = messagebox.askyesno(
                "🩺 Crash Doctor: Broken Mod Detected!",
                f"Most Recent Crash: {time_str}\n\n"
                f"⚠️ Suspected Problematic Mod:\n👉 {culprit}\n\n"
                "Would you like Crash Doctor to temporarily disable this mod so GD can launch cleanly?"
            )
            if res and self.mgr.gd_path:
                mod_path = os.path.join(self.mgr.gd_path, "geode", "mods", f"{culprit}.geode")
                if os.path.exists(mod_path):
                    try:
                        os.rename(mod_path, mod_path + ".disabled")
                        self.log(f"Disabled broken mod: {culprit}", "SUCCESS")
                        messagebox.showinfo("Mod Disabled", f"Disabled {culprit}!\n\nTry launching Geometry Dash now.")
                    except Exception as err:
                        messagebox.showerror("Error", f"Could not rename mod file: {err}")
                else:
                    messagebox.showinfo("Info", f"Mod file {culprit}.geode not found in mods folder (already removed?).")
        else:
            msg = f"Latest Crash Log: {os.path.basename(latest_log)} ({time_str})\n\n"
            msg += "No single specific mod was flagged as the culprit. This usually means a game version mismatch (e.g. 2.209 vs 2.2081).\n\n"
            msg += "Clicking '⚡ 1-Click Fix' to downgrade to 2.2081 will resolve most startup crashes!"
            messagebox.showinfo("🩺 Crash Doctor Report", msg)

    # ==========================================
    # v1.1.2 FEATURE: VERSION ARCHIVE SELECTOR
    # ==========================================
    def open_version_selector(self):
        dialog = tk.Toplevel(self)
        dialog.title("Select Target Geometry Dash Version")
        dialog.geometry("480x280")
        dialog.configure(bg="#161e2e")
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="⚙️ Choose Target Version", font=("Segoe UI", 12, "bold"), fg="#ffffff", bg="#161e2e").pack(anchor="w", padx=20, pady=(16, 4))
        tk.Label(dialog, text="Select which official Steam depot version to downgrade/switch to:", font=("Segoe UI", 9), fg="#94a3b8", bg="#161e2e").pack(anchor="w", padx=20, pady=(0, 12))

        selected_ver = tk.StringVar(value=list(KNOWN_VERSIONS.keys())[0])

        for name, data in KNOWN_VERSIONS.items():
            rb = tk.Radiobutton(
                dialog,
                text=name,
                variable=selected_ver,
                value=name,
                font=("Segoe UI", 9),
                fg="#e2e8f0",
                bg="#161e2e",
                selectcolor="#0f172a",
                activebackground="#161e2e",
                activeforeground="#38bdf8"
            )
            rb.pack(anchor="w", padx=24, pady=4)

        def apply_ver():
            choice = selected_ver.get()
            meta = KNOWN_VERSIONS[choice]
            self.mgr.target_manifest = meta["manifest"]
            self.mgr.target_gd_version = meta["ver"]
            self.log(f"Target GD version set to: {meta['ver']} (Manifest: {meta['manifest']})", "INFO")
            dialog.destroy()
            self.refresh_status()

        btn_box = tk.Frame(dialog, bg="#161e2e")
        btn_box.pack(fill="x", side="bottom", padx=20, pady=16)

        cancel_btn = tk.Button(btn_box, text="Cancel", command=dialog.destroy, font=("Segoe UI", 8), bg="#1e293b", fg="#94a3b8", relief="flat", padx=10, pady=4, cursor="hand2")
        cancel_btn.pack(side="left")

        apply_btn = tk.Button(btn_box, text="Set as Target Version", command=apply_ver, font=("Segoe UI", 8, "bold"), bg="#8b5cf6", fg="#ffffff", activebackground="#7c3aed", activeforeground="#ffffff", relief="flat", padx=14, pady=4, cursor="hand2")
        apply_btn.pack(side="right")

    def upgrade_clicked(self):
        res = messagebox.askyesno(
            "Restore to Latest GD",
            "This will unlock the Steam manifest and trigger Steam file verification to re-download the latest official version of Geometry Dash.\n\n"
            "Use this when Geode has officially updated to support the new version.\n\n"
            "Proceed?"
        )
        if not res:
            return

        threading.Thread(target=self._run_upgrade, daemon=True).start()

    def _run_upgrade(self):
        self.log("Unlocking Steam manifest...", "INFO")
        try:
            self.mgr.set_manifest_locked(False)
            self.log("Unlocked appmanifest_322170.acf.", "SUCCESS")
        except Exception as e:
            self.log(f"Warning unlocking manifest: {e}", "WARN")

        self.log("Triggering Steam file verification...", "INFO")
        try:
            os.startfile(f"steam://validate/{APP_ID}")
            self.log("Triggered steam://validate/322170. Steam is now updating GD.", "SUCCESS")
            self.play_ding()
            messagebox.showinfo(
                "Restoring Latest Version",
                "Steam is now verifying and updating your Geometry Dash files to the latest version!\n\n"
                "Watch your Steam Downloads tab for progress."
            )
        except Exception as e:
            self.log(f"Failed to trigger Steam validate: {e}", "ERROR")
            messagebox.showerror("Error", f"Failed to trigger Steam verification:\n{e}")

        self.refresh_status()

    def backup_saves(self):
        save_dir = self.mgr.get_save_data_dir()
        if not save_dir:
            messagebox.showerror("Error", "Could not locate Geometry Dash save folder in LocalAppData.")
            return

        backup_root = os.path.join(save_dir, "GeodeSync_Save_Backups")
        os.makedirs(backup_root, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        target_folder = os.path.join(backup_root, f"Backup_{timestamp}")
        os.makedirs(target_folder, exist_ok=True)

        copied = 0
        for f in os.listdir(save_dir):
            if f.endswith(".dat") or f.endswith(".dat.bak"):
                safe_copy_item(os.path.join(save_dir, f), os.path.join(target_folder, f))
                copied += 1

        self.play_ding()
        self.log(f"Backed up {copied} save files to: {target_folder}", "SUCCESS")
        messagebox.showinfo("Save Backup Complete", f"Successfully backed up {copied} save files!\n\nLocation: {target_folder}")

    def restore_saves(self):
        save_dir = self.mgr.get_save_data_dir()
        if not save_dir:
            messagebox.showerror("Error", "Could not locate Geometry Dash save folder.")
            return

        backup_root = os.path.join(save_dir, "GeodeSync_Save_Backups")
        if not os.path.exists(backup_root) or not os.listdir(backup_root):
            messagebox.showinfo("No Backups Found", "No GeodeSync save backups were found yet. Click 'Backup GD Saves' first!")
            return

        folders = [os.path.join(backup_root, d) for d in os.listdir(backup_root) if os.path.isdir(os.path.join(backup_root, d))]
        folders.sort(key=os.path.getmtime, reverse=True)
        latest_backup = folders[0]

        res = messagebox.askyesno(
            "Restore Save Files",
            f"Restore save files from latest backup?\n\nFolder: {os.path.basename(latest_backup)}\n\nThis will overwrite current save files with this backup."
        )
        if not res:
            return

        restored = 0
        for f in os.listdir(latest_backup):
            if f.endswith(".dat") or f.endswith(".dat.bak"):
                safe_copy_item(os.path.join(latest_backup, f), os.path.join(save_dir, f))
                restored += 1

        self.play_ding()
        self.log(f"Restored {restored} save files from: {os.path.basename(latest_backup)}", "SUCCESS")
        messagebox.showinfo("Saves Restored", f"Restored {restored} save files successfully!")

    def open_mods_folder(self):
        if self.mgr.gd_path:
            mods_dir = os.path.join(self.mgr.gd_path, "geode", "mods")
            os.makedirs(mods_dir, exist_ok=True)
            os.startfile(mods_dir)
        else:
            messagebox.showerror("Error", "Geometry Dash folder not found.")

    def browse_gd_path(self):
        selected = filedialog.askdirectory(title="Select Geometry Dash Folder")
        if selected:
            if os.path.exists(os.path.join(selected, "GeometryDash.exe")):
                self.mgr.gd_path = os.path.abspath(selected)
                self.mgr.manifest_path = self.mgr.get_manifest_path()
                self.log(f"Updated GD directory to: {self.mgr.gd_path}", "INFO")
                self.refresh_status()
            else:
                messagebox.showerror("Invalid Directory", "The selected folder does not contain GeometryDash.exe.")

    def launch_gd(self):
        self.log("Launching Geometry Dash...", "INFO")
        try:
            os.startfile(f"steam://run/{APP_ID}")
        except Exception:
            if self.mgr.gd_path:
                exe = os.path.join(self.mgr.gd_path, "GeometryDash.exe")
                if os.path.exists(exe):
                    os.startfile(exe)

    def check_remote_updates(self):
        try:
            req = urllib.request.Request(CONFIG_URL, headers={"User-Agent": "GeodeSync-Client"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode())
                if "target_manifest" in data and data["target_manifest"]:
                    self.mgr.target_manifest = data["target_manifest"]
                if "geode_target_gd" in data and data["geode_target_gd"]:
                    self.mgr.target_gd_version = data["geode_target_gd"]
        except Exception:
            pass

        try:
            req = urllib.request.Request(RELEASES_API, headers={"User-Agent": "GeodeSync-Client"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                rel = json.loads(resp.read().decode())
                tag = rel.get("tag_name", "").lstrip("v")
                if tag and tag != APP_VERSION:
                    self.latest_release_url = rel.get("html_url", f"https://github.com/{GITHUB_REPO}/releases")
                    self.show_update_banner(tag)
        except Exception:
            pass

    def show_update_banner(self, new_ver: str):
        self.update_label.config(text=f"🎉 Update available: v{new_ver}! (Current: v{APP_VERSION})")
        self.update_banner.pack(fill="x", before=self.children[list(self.children.keys())[0]])

    def open_update_link(self):
        url = self.latest_release_url or f"https://github.com/{GITHUB_REPO}/releases"
        webbrowser.open(url)

    def show_help_dialog(self):
        msg = (
            "HOW GEODESYNC WORKS (FAQ):\n\n"
            "1. Why do I need to downgrade?\n"
            "Whenever Geometry Dash updates (like to 2.209), Geode mods crash until developers update them. Downgrading to 2.2081 lets you keep playing with all your mods immediately.\n\n"
            "2. How does the 1-Click Fix work?\n"
            "You literally just click the button! GeodeSync signals Steam to download clean 2.2081 files in the background, swaps the files into your game, and locks Steam so it won't auto-update.\n\n"
            "3. What is Crash Doctor?\n"
            "Crash Doctor scans your Geode crash logs to detect which mod crashed your game, and lets you disable broken mods with 1 click.\n\n"
            "4. What is Fix Click Delay?\n"
            "Configures low-latency FMOD audio buffering (~2.7ms) and CBF mouse polling fix to eliminate sound lag when clicking in levels.\n\n"
            "5. Will I lose my icons or save data?\n"
            "No! Your save files are stored separately in AppData and are never touched. You can also click '💾 Backup Saves' for extra peace of mind!"
        )
        messagebox.showinfo("GeodeSync Guide & FAQ", msg)


if __name__ == "__main__":
    app = GeodeSyncApp()
    app.mainloop()

import os
import sys
import json
import shutil
import stat
import winreg
import urllib.request
import webbrowser
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

APP_VERSION = "1.0.0"
GITHUB_REPO = "willmakesrandomshit/GeodeSync"
CONFIG_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.json"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

APP_ID = "322170"
DEPOT_ID = "322171"
DEFAULT_MANIFEST = "3816559102876907245"
DEFAULT_TARGET_GD = "2.2081"

SIZE_22081 = 10700288
SIZE_2209 = 13178880

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

    def detect_gd_path(self):
        if not self.steam_path:
            return None

        # Check default common directory
        default_gd = os.path.join(self.steam_path, "steamapps", "common", "Geometry Dash")
        if os.path.exists(default_gd):
            return default_gd

        # Check libraryfolders.vdf for other drives
        vdf_path = os.path.join(self.steam_path, "steamapps", "libraryfolders.vdf")
        if os.path.exists(vdf_path):
            try:
                with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                for line in content.splitlines():
                    if '"path"' in line:
                        parts = line.split('"')
                        if len(parts) >= 4:
                            lib_dir = parts[3].replace(r"\\", "\\")
                            candidate = os.path.join(lib_dir, "steamapps", "common", "Geometry Dash")
                            if os.path.exists(candidate):
                                return candidate
            except Exception:
                pass

        return None

    def get_manifest_path(self):
        if self.gd_path:
            parent = os.path.dirname(os.path.dirname(self.gd_path)) # steamapps
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

    def get_gd_version_info(self):
        if not self.gd_path:
            return "Not Installed", "#ef4444"

        exe_path = os.path.join(self.gd_path, "GeometryDash.exe")
        if not os.path.exists(exe_path):
            return "Missing Executable", "#ef4444"

        size = os.path.getsize(exe_path)
        if size == SIZE_22081:
            return f"{self.target_gd_version} (Geode Compatible)", "#10b981"
        elif size == SIZE_2209:
            return "2.209 (Latest / Needs Geode Update)", "#f59e0b"
        else:
            mb = round(size / (1024 * 1024), 2)
            return f"Custom / Other ({mb} MB)", "#60a5fa"

    def is_manifest_locked(self):
        if not self.manifest_path or not os.path.exists(self.manifest_path):
            return False
        mode = os.stat(self.manifest_path).st_mode
        return not bool(mode & stat.S_IWRITE)

    def set_manifest_locked(self, lock: bool):
        if not self.manifest_path or not os.path.exists(self.manifest_path):
            raise FileNotFoundError("appmanifest_322170.acf not found!")

        if lock:
            os.chmod(self.manifest_path, stat.S_IREAD)
        else:
            os.chmod(self.manifest_path, stat.S_IWRITE | stat.S_IREAD)

    def has_downloaded_depot(self):
        d_path = self.get_depot_path()
        if d_path and os.path.exists(d_path):
            exe = os.path.join(d_path, "GeometryDash.exe")
            return os.path.exists(exe)
        return False

    def is_geode_installed(self):
        if not self.gd_path:
            return False
        dll = os.path.join(self.gd_path, "Geode.dll")
        proxy = os.path.join(self.gd_path, "XInput1_4.dll")
        return os.path.exists(dll) and os.path.exists(proxy)


class ModernButton(tk.Canvas):
    def __init__(self, parent, text, command, bg="#8b5cf6", hover_bg="#7c3aed", fg="#ffffff", height=38, width=None, font=("Segoe UI", 10, "bold")):
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
        r = 8  # corner radius

        if not self.enabled:
            fill = "#374151"
            text_color = "#9ca3af"
        else:
            fill = self.current_bg
            text_color = self.fg

        # Rounded rectangle
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

    def set_text(self, text: str):
        self.text = text
        self.draw()


class GeodeSyncApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"GeodeSync v{APP_VERSION} • Geometry Dash Mod & Version Switcher")
        self.geometry("740x690")
        self.minsize(680, 640)
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
        self.create_ui()
        self.refresh_status()

        # Check for remote updates in background thread
        threading.Thread(target=self.check_remote_updates, daemon=True).start()

    def create_ui(self):
        # Update Banner (hidden by default)
        self.update_banner = tk.Frame(self, bg="#064e3b", padx=16, pady=8)
        self.update_label = tk.Label(self.update_banner, text="✨ New update available!", font=("Segoe UI", 9, "bold"), fg="#34d399", bg="#064e3b")
        self.update_label.pack(side="left")

        self.update_action_btn = tk.Button(self.update_banner, text="Download Update", command=self.open_update_link, font=("Segoe UI", 8, "bold"), bg="#10b981", fg="#ffffff", activebackground="#059669", activeforeground="#ffffff", relief="flat", padx=8, pady=2, cursor="hand2")
        self.update_action_btn.pack(side="right")

        # Header banner
        header = tk.Frame(self, bg="#161e2e", padx=24, pady=16)
        header.pack(fill="x")

        title_box = tk.Frame(header, bg="#161e2e")
        title_box.pack(side="left")

        title = tk.Label(title_box, text=f"⚡ GeodeSync  v{APP_VERSION}", font=("Segoe UI", 16, "bold"), fg="#ffffff", bg="#161e2e")
        title.pack(anchor="w")

        subtitle = tk.Label(title_box, text="Seamless Geometry Dash Version Switcher & Geode Protector", font=("Segoe UI", 9), fg="#94a3b8", bg="#161e2e")
        subtitle.pack(anchor="w")

        badge_box = tk.Frame(header, bg="#161e2e")
        badge_box.pack(side="right")

        self.launch_btn = ModernButton(badge_box, "▶ Launch GD", self.launch_gd, bg="#2563eb", hover_bg="#1d4ed8", width=120, height=36)
        self.launch_btn.pack(side="right")

        # Main Scrollable / Stacked Container
        body = tk.Frame(self, bg="#0f141c", padx=24, pady=14)
        body.pack(fill="both", expand=True)

        # Status Cards Grid
        status_card = tk.Frame(body, bg="#1a2333", padx=16, pady=12, highlightbackground="#2d3748", highlightthickness=1)
        status_card.pack(fill="x", pady=(0, 12))

        st_title = tk.Label(status_card, text="CURRENT INSTALLATION STATUS", font=("Segoe UI", 8, "bold"), fg="#64748b", bg="#1a2333")
        st_title.pack(anchor="w", pady=(0, 8))

        # Row 1: GD Version & Lock Status
        r1 = tk.Frame(status_card, bg="#1a2333")
        r1.pack(fill="x", pady=2)

        lbl_v = tk.Label(r1, text="Geometry Dash Version:", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#1a2333", width=20, anchor="w")
        lbl_v.pack(side="left")

        self.ver_badge = tk.Label(r1, text="Detecting...", font=("Segoe UI", 9, "bold"), fg="#10b981", bg="#132a24", padx=8, pady=2)
        self.ver_badge.pack(side="left", padx=4)

        # Row 2: Steam Auto-Update Lock
        r2 = tk.Frame(status_card, bg="#1a2333")
        r2.pack(fill="x", pady=4)

        lbl_lock = tk.Label(r2, text="Steam Auto-Update Lock:", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#1a2333", width=20, anchor="w")
        lbl_lock.pack(side="left")

        self.lock_badge = tk.Label(r2, text="Detecting...", font=("Segoe UI", 9, "bold"), fg="#f59e0b", bg="#332412", padx=8, pady=2)
        self.lock_badge.pack(side="left", padx=4)

        self.toggle_lock_btn = tk.Button(r2, text="Toggle Lock", command=self.toggle_lock, font=("Segoe UI", 8, "bold"), bg="#2d3748", fg="#e2e8f0", activebackground="#4a5568", activeforeground="#ffffff", relief="flat", padx=6, pady=1, cursor="hand2")
        self.toggle_lock_btn.pack(side="left", padx=8)

        # Row 3: Geode Status
        r3 = tk.Frame(status_card, bg="#1a2333")
        r3.pack(fill="x", pady=2)

        lbl_geode = tk.Label(r3, text="Geode Mod Loader:", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#1a2333", width=20, anchor="w")
        lbl_geode.pack(side="left")

        self.geode_badge = tk.Label(r3, text="Detecting...", font=("Segoe UI", 9, "bold"), fg="#a855f7", bg="#2a163d", padx=8, pady=2)
        self.geode_badge.pack(side="left", padx=4)

        self.geode_site_btn = tk.Button(r3, text="Get Geode", command=lambda: webbrowser.open("https://geode-sdk.org"), font=("Segoe UI", 8), bg="#1e293b", fg="#94a3b8", activebackground="#334155", activeforeground="#ffffff", relief="flat", padx=6, pady=1, cursor="hand2")
        self.geode_site_btn.pack(side="left", padx=8)

        # Action Buttons Panel
        actions_card = tk.Frame(body, bg="#1a2333", padx=16, pady=12, highlightbackground="#2d3748", highlightthickness=1)
        actions_card.pack(fill="x", pady=(0, 12))

        act_title = tk.Label(actions_card, text="SWITCH VERSIONS", font=("Segoe UI", 8, "bold"), fg="#64748b", bg="#1a2333")
        act_title.pack(anchor="w", pady=(0, 10))

        btn_grid = tk.Frame(actions_card, bg="#1a2333")
        btn_grid.pack(fill="x")

        # Downgrade Button
        self.down_btn = ModernButton(
            btn_grid,
            text=f"🔻 Downgrade to {self.mgr.target_gd_version} (Geode Mode)",
            command=self.downgrade_clicked,
            bg="#8b5cf6",
            hover_bg="#7c3aed",
            height=40
        )
        self.down_btn.pack(fill="x", pady=(0, 8))

        # Upgrade Button
        self.up_btn = ModernButton(
            btn_grid,
            text="🔺 Restore / Update to Latest (Official)",
            command=self.upgrade_clicked,
            bg="#10b981",
            hover_bg="#059669",
            height=40
        )
        self.up_btn.pack(fill="x", pady=(0, 8))

        # Steam Console Quick Helper
        self.console_btn = ModernButton(
            btn_grid,
            text="📋 Open Steam Console & Copy Depot Command",
            command=self.open_console_and_copy,
            bg="#334155",
            hover_bg="#475569",
            height=34,
            font=("Segoe UI", 9)
        )
        self.console_btn.pack(fill="x")

        # Console / Activity Log Card
        log_card = tk.Frame(body, bg="#161e2e", padx=12, pady=10, highlightbackground="#2d3748", highlightthickness=1)
        log_card.pack(fill="both", expand=True)

        log_head = tk.Frame(log_card, bg="#161e2e")
        log_head.pack(fill="x", pady=(0, 4))

        log_title = tk.Label(log_head, text="ACTIVITY LOG", font=("Segoe UI", 8, "bold"), fg="#64748b", bg="#161e2e")
        log_title.pack(side="left")

        clear_btn = tk.Button(log_head, text="Clear", command=self.clear_log, font=("Segoe UI", 7), bg="#1e293b", fg="#94a3b8", relief="flat", padx=4, pady=0, cursor="hand2")
        clear_btn.pack(side="right")

        self.log_text = tk.Text(log_card, bg="#0d1117", fg="#c9d1d9", font=("Consolas", 8), relief="flat", wrap="word", height=6, padx=8, pady=6)
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

    def refresh_status(self):
        ver_text, ver_color = self.mgr.get_gd_version_info()
        self.ver_badge.config(text=ver_text, fg=ver_color)

        if self.mgr.is_manifest_locked():
            self.lock_badge.config(text="🔒 LOCKED (Read-Only)", fg="#34d399", bg="#064e3b")
        else:
            self.lock_badge.config(text="🔓 UNLOCKED (Steam can update)", fg="#f59e0b", bg="#332412")

        if self.mgr.is_geode_installed():
            self.geode_badge.config(text="✓ Installed & Active", fg="#c084fc", bg="#2a163d")
        else:
            self.geode_badge.config(text="Not Detected", fg="#94a3b8", bg="#1e293b")

        self.path_lbl.config(text=f"GD Path: {self.mgr.gd_path or 'Not Found'}")

    def check_remote_updates(self):
        # 1. Fetch remote version.json
        try:
            req = urllib.request.Request(CONFIG_URL, headers={"User-Agent": "GeodeSync-Client"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode())
                if "target_manifest" in data and data["target_manifest"]:
                    self.mgr.target_manifest = data["target_manifest"]
                if "geode_target_gd" in data and data["geode_target_gd"]:
                    self.mgr.target_gd_version = data["geode_target_gd"]
                    self.down_btn.set_text(f"🔻 Downgrade to {self.mgr.target_gd_version} (Geode Mode)")
                if "announcement" in data and data["announcement"]:
                    self.log(f"Server Announcement: {data['announcement']}", "INFO")
                self.log(f"Synced latest remote config (Target GD: {self.mgr.target_gd_version})", "SUCCESS")
        except Exception:
            pass  # Offline or repo not public yet, perfectly fine!

        # 2. Check GitHub Releases
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

    def toggle_lock(self):
        if not self.mgr.manifest_path:
            messagebox.showwarning("Warning", "appmanifest_322170.acf could not be found.")
            return

        currently_locked = self.mgr.is_manifest_locked()
        try:
            self.mgr.set_manifest_locked(not currently_locked)
            new_state = "LOCKED (Read-Only)" if not currently_locked else "UNLOCKED"
            self.log(f"Steam update manifest changed to: {new_state}", "SUCCESS")
            self.refresh_status()
        except Exception as e:
            self.log(f"Failed to toggle lock: {e}", "ERROR")
            messagebox.showerror("Error", f"Could not toggle manifest lock: {e}")

    def open_console_and_copy(self):
        cmd = f"download_depot {APP_ID} {DEPOT_ID} {self.mgr.target_manifest}"
        self.clipboard_clear()
        self.clipboard_append(cmd)
        self.update()

        try:
            os.startfile("steam://open/console")
            self.log("Opened Steam Console and copied command to clipboard!", "SUCCESS")
            messagebox.showinfo(
                "Command Copied!",
                f"The Steam depot download command has been copied to your clipboard:\n\n"
                f"{cmd}\n\n"
                "The Steam Console tab has been opened. Just click at the bottom, press Ctrl+V, and hit Enter."
            )
        except Exception as e:
            self.log(f"Failed to open Steam Console: {e}", "ERROR")
            messagebox.showerror("Error", f"Failed to open Steam Console:\n{e}")

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

    def downgrade_clicked(self):
        threading.Thread(target=self._run_downgrade, daemon=True).start()

    def _run_downgrade(self):
        if not self.mgr.gd_path:
            self.log("Cannot downgrade: Geometry Dash folder not detected.", "ERROR")
            messagebox.showerror("Error", "Geometry Dash installation directory not found.")
            return

        depot = self.mgr.get_depot_path()
        if not self.mgr.has_downloaded_depot():
            self.log(f"Downloaded {self.mgr.target_gd_version} depot files not found in steamapps/content.", "WARN")
            res = messagebox.askyesno(
                "Depot Files Needed",
                f"The {self.mgr.target_gd_version} depot files have not been downloaded yet.\n\n"
                "Would you like to open the Steam Console and copy the download command automatically now?"
            )
            if res:
                self.open_console_and_copy()
            return

        self.log(f"Starting downgrade to {self.mgr.target_gd_version}...", "INFO")

        # Backup current files
        backup_dir = os.path.join(self.mgr.gd_path, "backup_latest")
        try:
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir, exist_ok=True)
                for f in ["GeometryDash.exe", "libcocos2d.dll", "libExtensions.dll"]:
                    src_f = os.path.join(self.mgr.gd_path, f)
                    if os.path.exists(src_f):
                        shutil.copy2(src_f, os.path.join(backup_dir, f))
                self.log("Created backup of current files in 'backup_latest'.", "INFO")
        except Exception as e:
            self.log(f"Warning during backup: {e}", "WARN")

        # Copy depot files
        try:
            for item in os.listdir(depot):
                s = os.path.join(depot, item)
                d = os.path.join(self.mgr.gd_path, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
            self.log(f"Replaced game files with {self.mgr.target_gd_version} depot files.", "SUCCESS")
        except Exception as e:
            self.log(f"Failed to copy files: {e}", "ERROR")
            messagebox.showerror("Error", f"Failed to overwrite game files:\n{e}")
            return

        # Lock manifest
        try:
            self.mgr.set_manifest_locked(True)
            self.log("Locked appmanifest_322170.acf to Read-Only.", "SUCCESS")
        except Exception as e:
            self.log(f"Warning locking manifest: {e}", "WARN")

        self.refresh_status()
        self.log(f"Downgrade completed successfully! Geometry Dash is now {self.mgr.target_gd_version}.", "SUCCESS")
        messagebox.showinfo("Downgrade Complete!", f"Geometry Dash has been successfully downgraded to {self.mgr.target_gd_version}!\n\nSteam auto-updates have been locked. Geode and your mods are ready to play.")

    def upgrade_clicked(self):
        res = messagebox.askyesno(
            "Restore to Latest GD",
            "This will unlock the Steam manifest and trigger Steam file verification to re-download the latest official version of Geometry Dash.\n\n"
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
            messagebox.showinfo(
                "Restoring Latest Version",
                "Steam is now verifying and updating your Geometry Dash files to the latest version!\n\n"
                "Watch your Steam Downloads tab for progress."
            )
        except Exception as e:
            self.log(f"Failed to trigger Steam validate: {e}", "ERROR")
            messagebox.showerror("Error", f"Failed to trigger Steam verification:\n{e}")

        self.refresh_status()

    def launch_gd(self):
        self.log("Launching Geometry Dash...", "INFO")
        try:
            os.startfile(f"steam://run/{APP_ID}")
        except Exception:
            if self.mgr.gd_path:
                exe = os.path.join(self.mgr.gd_path, "GeometryDash.exe")
                if os.path.exists(exe):
                    os.startfile(exe)


if __name__ == "__main__":
    app = GeodeSyncApp()
    app.mainloop()

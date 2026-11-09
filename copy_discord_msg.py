import tkinter as tk

announcement = """# 🚀 GeodeSync v2.7.1 Update Released!

A high-reliability quality-of-life patch is now live for all Windows, macOS, and Linux players!

### 🌟 What's New in v2.7.1:
* 🛡️ **Real-Time Save Health Monitoring:** The dashboard now continuously checks `CCGameManager.dat` and `CCLocalLevels.dat` file size, encryption, and protection status so you know your progress, demons, and stars are 100% safe.
* 🌐 **Rate-Limit Immune Updates:** Completely revamped the update checking engine with 4 fallback tiers (including public RSS/Atom feeds and CDN manifests) to eliminate update check errors.
* ⚡ **Cross-Platform Engine Stability:** Native process detection on Windows (`tasklist`) and Linux/macOS (`pgrep`) with zero console window popups.
* 📦 **Verified Standalone Packages:** Built, verified, and signed with SHA-256 digests.

### 📥 Download Update (Windows / macOS / Linux):
👉 **https://github.com/willmakesrandomshit/GeodeSync/releases/tag/v2.7.1**

*(If you have GeoDeSync open, click Check for Updates or download the new GeodeSync.exe directly from your Downloads folder!)*
"""

try:
    r = tk.Tk()
    r.withdraw()
    r.clipboard_clear()
    r.clipboard_append(announcement)
    r.update()
    r.destroy()
    print("SUCCESS: v2.7.1 release announcement copied to clipboard!")
except Exception as e:
    print(f"Clipboard error: {e}")

import tkinter as tk

announcement = """# 🚀 GeodeSync v2.8.0 — The 100x Ultimate Upgrade Released!

A massive milestone update is now live for all Windows, macOS, and Linux Geometry Dash players!

### 🌟 What's New in v2.8.0:
* 🛡️ **Zero-Loss Game Exit Auto-Save:** GeodeSync automatically detects when you close Geometry Dash and silently creates an instant, atomic backup of your stars, demons, coins, and custom levels. Never lose progress again!
* 🚀 **Pre-Launch Guard & Performance Booster:** Automatically takes a safety snapshot before launch, while elevating GD to high CPU priority for ultra-low input latency.
* 📢 **Live In-App Cloud Announcements:** Instant cloud updates directly inside the app, with zero webhooks or rate limits.
* 🔒 **Ironclad Security Guardian:** Automated secret scanning and strict endpoint verification to keep the community 100% secure.

### 📥 Download Update (Windows / macOS / Linux):
👉 **https://github.com/willmakesrandomshit/GeodeSync/releases/tag/v2.8.0**

*(If you already have GeoDeSync open, click Check for Updates to install automatically!)*
"""

try:
    r = tk.Tk()
    r.withdraw()
    r.clipboard_clear()
    r.clipboard_append(announcement)
    r.update()
    r.destroy()
    print("SUCCESS: v2.8.0 release announcement copied to clipboard!")
except Exception as e:
    print(f"Clipboard error: {e}")

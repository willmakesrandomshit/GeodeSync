import tkinter as tk

announcement = """@everyone
# ⚡ GeodeSync v2.2.1 Update Released!

A critical update has just been deployed to fix the fatal **"GeometryDash.exe - Entry Point Not Found"** startup error that was crashing Geometry Dash!

### 🛠️ What Was Fixed:
* **Entry Point Crash Auto-Repair:** ImagePlus (`prevter.imageplus v1.1.1`) introduced a call to `loadRootSubDictFromCompressedFile` which does not exist in GD 2.2081, crashing Geometry Dash before reaching the title screen. GeodeSync now automatically detects this and repairs it to the clean, tested `v1.1.0` build with 0 user effort.
* **Pre-Launch Self-Healing:** Launching GD through GeodeSync automatically verifies all mod dependencies and heals incompatible files in the background.
* **Proactive Crash Doctor:** Proactively detects Windows DLL loader errors before checking crash dumps.

### 📥 Download Update (Windows / Mac / Linux):
👉 **https://github.com/willmakesrandomshit/GeodeSync/releases/latest**

*(If you already have GeodeSync open, click the update banner at the top to download directly!)*
"""

try:
    r = tk.Tk()
    r.withdraw()
    r.clipboard_clear()
    r.clipboard_append(announcement)
    r.update()
    print("Announcement copied to clipboard successfully!")
except Exception as e:
    print(f"Clipboard error: {e}")

# GeodeSync v2.0.8 • Sound Effects Fix & Audio Modernization

GeodeSync v2.0.8 replaces the harsh motherboard square-wave PC buzzer with smooth, modern Windows native chimes.

---

### 🌟 What's Fixed in v2.0.8:

* 🔇 **Fixed "Amber Alert" Sound Noise:**
  * Replaced the harsh low-level square-wave `winsound.Beep()` frequency sequence with smooth native Windows system notification chimes (`winsound.PlaySound("SystemNotification")` / `winsound.MessageBeep(winsound.MB_OK)`).
  * No more abrasive motherboard beeper sounds when performing actions, syncing versions, clicking buttons, or backing up saves!
  * Full toggle control via the `🔊 Sounds` tool button.

---

### 📥 Downloads:
* **Windows (Direct EXE):** `GeodeSync.exe`
* **Windows (ZIP + Unblocker):** `GeodeSync-v2.0.8-Windows.zip`
* **Linux / Steam Deck:** `GeodeSync-v2.0.8-Linux.tar.gz`
* **macOS (Apple Silicon & Intel):** `GeodeSync-macOS-arm64.zip` / `GeodeSync-macOS-x86_64.zip`

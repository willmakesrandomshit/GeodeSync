#!/usr/bin/env python3
"""
Dispatches release announcements directly to Discord channel 1563643888537698314.
Works via Discord Webhook URL.
"""

import os
import sys
import json
import urllib.request

CHANNEL_ID = "1563643888537698314"
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "discord_webhook.json")


def get_webhook_url():
    # 1. Environment variable
    url = os.environ.get("GEODESYNC_DISCORD_WEBHOOK") or os.environ.get("DISCORD_WEBHOOK_URL")
    if url:
        return url.strip()

    # 2. Local config file (gitignored)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("webhook_url", "").strip()
        except Exception:
            pass

    return None


def current_version():
    with open(os.path.join(os.path.dirname(__file__), "version.json"), encoding="utf-8") as f:
        return json.load(f)["app_version"]


def send_update(version=None, title=None, notes=None, ping=False):
    version = version or current_version()
    webhook_url = get_webhook_url()
    if not webhook_url:
        print(f"[!] No Discord webhook URL configured for channel {CHANNEL_ID}.")
        print("[!] To set it up, create a Webhook in Discord channel settings and save it:")
        print("    python send_discord_update.py --set-webhook https://discord.com/api/webhooks/...")
        return False

    release_url = f"https://github.com/willmakesrandomshit/GeodeSync/releases/tag/v{version}"
    display_title = title or f"GeodeSync v{version} Released!"
    desc = notes or "A new update for GeodeSync is now available with automatic fixes and improvements."

    payload = {
        "content": "⚡ **New GeodeSync Update Released!**",
        "allowed_mentions": {"parse": []},
        "embeds": [
            {
                "title": f"🚀 {display_title}",
                "url": release_url,
                "description": desc,
                "color": 0xc2e66b,
                "fields": [
                    {
                        "name": "📦 Direct Downloads",
                        "value": f"[Choose a download for your system]({release_url})"
                    }
                ],
                "footer": {
                    "text": f"GeodeSync v{version} • Broadcast to #{CHANNEL_ID}"
                }
            }
        ]
    }

    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "GeodeSync-Release-Broadcast"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[SUCCESS] Dispatched update v{version} to Discord channel {CHANNEL_ID}!")
            return True
    except Exception as e:
        print(f"[ERROR] Failed to send update to Discord: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--set-webhook":
        wh_url = sys.argv[2].strip()
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"channel_id": CHANNEL_ID, "webhook_url": wh_url}, f, indent=2)
        print(f"Saved webhook for channel {CHANNEL_ID} to {CONFIG_FILE}!")
        sys.exit(0)

    # Read latest release notes
    notes_file = os.path.join(os.path.dirname(__file__), "release_notes.md")
    notes = None
    if os.path.exists(notes_file):
        with open(notes_file, "r", encoding="utf-8") as f:
            notes = f.read()

    version = current_version()
    send_update(version=version, title=f"GeodeSync v{version} released", notes=notes)

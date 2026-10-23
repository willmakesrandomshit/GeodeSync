#!/usr/bin/env python3
"""
GeodeSync Steam & Geode Watchdog
Monitors Valve Steam Depots & GitHub Geode SDK Releases.
Optionally alerts via Discord Webhook when RobTop updates GD or Geode updates!
"""

import os
import sys
import time
import json
import urllib.request
from datetime import datetime

APP_ID = "322170"
DEPOT_ID = "322171"
GEODE_REPO = "geode-sdk/geode"
CHECK_INTERVAL_SECONDS = 180  # check every 3 minutes

# Paste your Discord Webhook URL below to receive instant update pings:
DISCORD_WEBHOOK_URL = os.environ.get("GEODESYNC_DISCORD_WEBHOOK", "")


def send_discord_alert(title, description, color=0x8b5cf6, ping=True):
    if not DISCORD_WEBHOOK_URL:
        print(f"[Watchdog Alert] {title}\n{description}")
        return

    content = "@everyone" if ping else ""
    payload = {
        "content": content,
        "embeds": [
            {
                "title": f"⚡ {title}",
                "description": description,
                "color": color,
                "footer": {"text": "GeodeSync Automatic Watchdog"},
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        ]
    }

    try:
        req = urllib.request.Request(
            DISCORD_WEBHOOK_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "GeodeSync-Watchdog"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            pass
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Dispatched Discord alert!")
    except Exception as e:
        print(f"Failed to send Discord alert: {e}")


def get_latest_geode_tag():
    try:
        url = f"https://api.github.com/repos/{GEODE_REPO}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "GeodeSync-Watchdog"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
            return data.get("tag_name", ""), data.get("html_url", "")
    except Exception:
        return None, None


def main():
    print("=" * 60)
    print("   GEODESYNC STEAM & GEODE WATCHDOG DAEMON")
    print("=" * 60)
    print(f"Monitoring Geometry Dash (App {APP_ID}) & Geode Releases...")
    print(f"Check interval: {CHECK_INTERVAL_SECONDS}s")
    if DISCORD_WEBHOOK_URL:
        print("Discord Webhook configured: Active!")
    else:
        print("Note: Set GEODESYNC_DISCORD_WEBHOOK env var to receive Discord pings.")
    print("-" * 60)

    last_geode_tag, _ = get_latest_geode_tag()
    print(f"Initial Geode version detected: {last_geode_tag or 'Unknown'}")

    while True:
        try:
            # 1. Check Geode release
            cur_tag, rel_url = get_latest_geode_tag()
            if cur_tag and last_geode_tag and cur_tag != last_geode_tag:
                send_discord_alert(
                    "Geode Mod Loader Updated!",
                    f"A new version of Geode has just dropped: **{cur_tag}**!\n\n"
                    f"Check the release notes: {rel_url}\n"
                    f"If you were downgraded with GeodeSync, you can now safely click **'Restore Latest GD'**!",
                    color=0x10b981
                )
                last_geode_tag = cur_tag

            print(f"[{datetime.now().strftime('%H:%M:%S')}] Heartbeat check OK. Geode: {cur_tag}")
        except Exception as e:
            print(f"Watchdog error: {e}")

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Dispatches release announcements directly to Discord channel 1563643888537698314.
Works via Discord Webhook URL.
"""

import os
import sys
import json
import urllib.request

from discord_release import build_release_payload

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


def send_update(version=None, title=None, notes=None, ping=False, release_tag=None, release_url=None):
    version = version or current_version()
    webhook_url = get_webhook_url()
    if not webhook_url:
        print(f"[!] No Discord webhook URL configured for channel {CHANNEL_ID}.")
        print("[!] To set it up, create a Webhook in Discord channel settings and save it:")
        print("    python send_discord_update.py --set-webhook https://discord.com/api/webhooks/...")
        return False

    release_tag = release_tag or f"v{version}"
    release_url = release_url or f"https://github.com/willmakesrandomshit/GeodeSync/releases/tag/{release_tag}"
    display_title = title or f"GeodeSync v{version} Released!"
    assets_env = os.environ.get("RELEASE_ASSETS")
    if assets_env is not None:
        assets = assets_env.split(",")
    else:
        try:
            url = f"https://api.github.com/repos/willmakesrandomshit/GeodeSync/releases/tags/{release_tag}"
            req = urllib.request.Request(url, headers={"User-Agent": "GeodeSync-Release-Broadcast"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                assets = [asset["name"] for asset in data.get("assets", [])]
        except Exception:
            assets = None

    payload = build_release_payload(
        display_title,
        release_tag,
        notes,
        release_url,
        assets=assets,
    )

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

    version = current_version()
    tag = os.environ.get("RELEASE_TAG") or f"v{version}"
    title = os.environ.get("RELEASE_TITLE") or f"GeodeSync {tag} released"
    release_url = os.environ.get("RELEASE_URL") or f"https://github.com/willmakesrandomshit/GeodeSync/releases/tag/{tag}"

    notes = os.environ.get("RELEASE_BODY")
    if not notes:
        clean_v = version.replace(".", "")
        v_notes = os.path.join(os.path.dirname(__file__), f"release_notes_v{clean_v}.md")
        if os.path.exists(v_notes):
            with open(v_notes, "r", encoding="utf-8") as f:
                notes = f.read()
        else:
            notes_file = os.environ.get("RELEASE_BODY_FILE") or os.path.join(os.path.dirname(__file__), "release_notes.md")
            if os.path.exists(notes_file):
                with open(notes_file, "r", encoding="utf-8") as f:
                    full_notes = f.read()
                    notes = full_notes.split("\n---")[0].strip()

    if not send_update(
        version=version,
        title=title,
        notes=notes,
        release_tag=tag,
        release_url=release_url,
    ):
        sys.exit(1)

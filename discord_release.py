"""Build the branded Discord payload used for GeodeSync release announcements."""

import re


REPOSITORY = "https://github.com/willmakesrandomshit/GeodeSync"
AVATAR_URL = "https://raw.githubusercontent.com/willmakesrandomshit/GeodeSync/refs/heads/main/assets/geodesync-brand-2026.png"
BRAND_COLOR = 0x7557E8


def _release_notes(body, release_url, limit=3500):
    body = (body or "A new GeodeSync update is available.").strip()
    if len(body) <= limit:
        return body
    suffix = f"… [Read the full changelog]({release_url})"
    return body[: limit - len(suffix) - 1].rstrip() + "\n" + suffix


def build_release_payload(title, tag, body, release_url, assets=None):
    """Return a Discord webhook payload with accurate, version-specific links."""
    tag = (tag or "latest").strip()
    version_tag = tag if tag.startswith("v") else f"v{tag}"
    asset_base = f"{REPOSITORY}/releases/download/{tag}"
    notes = _release_notes(body, release_url)
    # Keep the visible title compact; the full release title is still on GitHub.
    display_title = re.sub(r"\s+", " ", (title or f"GeodeSync {tag}")).strip()
    if len(display_title) > 240:
        display_title = display_title[:237].rstrip() + "…"

    if assets is None:
        assets = {
            "GeodeSync-Windows.zip",
            "GeodeSync-macOS-arm64.zip",
            "GeodeSync-macOS-x86_64.zip",
            f"GeodeSync-{version_tag}-Linux.tar.gz",
        }
    else:
        assets = set(assets)
    downloads = []
    for label, filename in (
        ("Windows", "GeodeSync-Windows.zip"),
        ("macOS · Apple silicon", "GeodeSync-macOS-arm64.zip"),
        ("macOS · Intel", "GeodeSync-macOS-x86_64.zip"),
        ("Linux", f"GeodeSync-{version_tag}-Linux.tar.gz"),
    ):
        if filename in assets:
            downloads.append(f"[{label}](<{asset_base}/{filename}>)")
    if not downloads:
        downloads.append(f"[Open the release page]({release_url})")

    return {
        "username": "GeodeSync Updates",
        "avatar_url": AVATAR_URL,
        "allowed_mentions": {"parse": []},
        "embeds": [
            {
                "author": {
                    "name": "GEODESYNC  •  OFFICIAL RELEASE",
                    "icon_url": AVATAR_URL,
                },
                "title": f"⚡ {display_title}",
                "url": release_url,
                "description": notes,
                "color": BRAND_COLOR,
                "fields": [
                    {
                        "name": "⬇️ Get GeodeSync",
                        "value": "  ·  ".join(downloads),
                        "inline": False,
                    },
                    {
                        "name": "🔎 Verify the download",
                        "value": f"[Release details, checksums, and source]({release_url})",
                        "inline": False,
                    },
                ],
                "thumbnail": {"url": AVATAR_URL},
                "footer": {"text": f"GeodeSync  /  {tag}"},
            }
        ],
    }

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from discord_release import AVATAR_URL, build_release_payload
import send_discord_update


class TestDiscordReleasePayload(unittest.TestCase):
    def test_payload_is_branded_and_disables_mentions(self):
        payload = build_release_payload(
            "GeodeSync v2.3.2", "v2.3.2", "Fixes and improvements", "https://example.test/release"
        )

        self.assertEqual(payload["username"], "GeodeSync Updates")
        self.assertEqual(payload["avatar_url"], AVATAR_URL)
        self.assertEqual(payload["allowed_mentions"], {"parse": []})
        embed = payload["embeds"][0]
        self.assertEqual(embed["author"]["icon_url"], AVATAR_URL)
        self.assertEqual(embed["url"], "https://example.test/release")
        self.assertIn("GeodeSync v2.3.2", embed["title"])

    def test_downloads_are_direct_and_match_release_tag(self):
        payload = build_release_payload(
            "Release", "v2.3.2", "Notes", "https://example.test/release"
        )
        links = payload["embeds"][0]["fields"][0]["value"]

        for asset in (
            "GeodeSync-Windows.zip",
            "GeodeSync-macOS-arm64.zip",
            "GeodeSync-macOS-x86_64.zip",
            "GeodeSync-v2.3.2-Linux.tar.gz",
        ):
            self.assertIn(f"/releases/download/v2.3.2/{asset}", links)
        self.assertNotIn("releases/latest/download", links)

    def test_long_release_notes_fit_discord_embed_description(self):
        payload = build_release_payload(
            "Release", "v2.3.2", "x" * 10_000, "https://example.test/release"
        )
        description = payload["embeds"][0]["description"]

        self.assertLessEqual(len(description), 3500)
        self.assertIn("Read the full changelog", description)
        self.assertIn("https://example.test/release", description)

    def test_announcement_only_links_to_assets_in_this_release(self):
        payload = build_release_payload(
            "Release", "v2.3.12", "Mac download withheld", "https://example.test/release",
            assets={"GeodeSync-Windows.zip", "GeodeSync-v2.3.12-Linux.tar.gz", "SHA256SUMS.txt"},
        )
        embed = payload["embeds"][0]
        downloads = next(field["value"] for field in embed["fields"] if field["name"] == "⬇️ Get GeodeSync")
        self.assertIn("GeodeSync-Windows.zip", downloads)
        self.assertIn("GeodeSync-v2.3.12-Linux.tar.gz", downloads)
        self.assertNotIn("macOS", downloads)

    @patch("send_discord_update.urllib.request.urlopen")
    @patch("send_discord_update.get_webhook_url", return_value="https://discord.com/api/webhooks/test")
    def test_sender_posts_the_shared_payload(self, _webhook, urlopen):
        response = MagicMock()
        response.__enter__.return_value.status = 204
        urlopen.return_value = response

        self.assertTrue(
            send_discord_update.send_update(
                version="2.3.2",
                title="GeodeSync v2.3.2",
                notes="Test notes",
            )
        )
        request = urlopen.call_args.args[0]
        payload = __import__("json").loads(request.data.decode("utf-8"))
        self.assertEqual(payload["username"], "GeodeSync Updates")
        self.assertIn("GeodeSync-Windows.zip", payload["embeds"][0]["fields"][0]["value"])

    def test_tag_build_sends_announcement_after_publishing_release(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/build-macos.yml").read_text(encoding="utf-8")
        release_step = workflow.index("uses: softprops/action-gh-release@v2")
        notify_step = workflow.index("name: Announce release in Discord")
        self.assertLess(release_step, notify_step)
        self.assertIn("if: startsWith(github.ref, 'refs/tags/v')", workflow[notify_step:])
        self.assertIn("python3 send_discord_update.py", workflow[notify_step:])
        self.assertIn("GEODESYNC_DISCORD_WEBHOOK: ${{ secrets.DISCORD_RELEASE_WEBHOOK }}", workflow[notify_step:])
        self.assertIn("RELEASE_ASSETS: ${{ steps.assets.outputs.asset_names }}", workflow[notify_step:])
        self.assertIn("RELEASE_BODY_FILE: release_notes_for_release.md", workflow[notify_step:])

    def test_notification_workflow_is_manual_retry_not_release_event(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/notify-discord-update.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("release_tag:", workflow)
        self.assertIn("announcement_body:", workflow)
        self.assertIn("ANNOUNCEMENT_BODY", workflow)
        self.assertNotIn("types: [published]", workflow)


if __name__ == "__main__":
    unittest.main()

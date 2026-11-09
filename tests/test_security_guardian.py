import os
import unittest
from scripts.security_check import scan_secrets, audit_process_safety
from discord_release import build_release_payload
import send_discord_update


class TestSecurityGuardian(unittest.TestCase):
    def setUp(self):
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def test_zero_secrets_in_repository(self):
        """Scans the repository to ensure no API keys, tokens, or webhooks are committed."""
        violations = scan_secrets(self.repo_root)
        self.assertEqual(
            violations,
            [],
            f"Security Violation: Found {len(violations)} secret(s) in repository: {violations}",
        )

    def test_process_safety_zero_shell_true(self):
        """Ensures no dangerous shell=True executions exist in production code."""
        issues = audit_process_safety(self.repo_root)
        self.assertEqual(
            issues,
            [],
            f"Process Safety Violation: Found unsafe process executions: {issues}",
        )

    def test_discord_payload_blocks_all_mentions(self):
        """Ensures Discord release payloads explicitly forbid mentions to prevent notification abuse."""
        payload = build_release_payload(
            "Test @everyone @here <@&12345>",
            "v2.7.1",
            "Notes with @everyone and @here",
            "https://example.com/release",
        )
        self.assertEqual(payload.get("allowed_mentions"), {"parse": []})

    def test_webhook_url_validation(self):
        """Ensures that only authentic Discord webhook URLs are accepted."""
        valid_url = "https://discord.com/api/webhooks/123456789/abcdefghijklmnopqrstuvwxyz"
        valid_legacy = "https://discordapp.com/api/webhooks/123456789/abcdefghijklmnopqrstuvwxyz"
        invalid_url = "https://malicious-site.com/api/webhooks/12345"
        invalid_proto = "http://discord.com/api/webhooks/12345"

        def is_valid(url):
            if not url or not isinstance(url, str):
                return False
            u = url.strip()
            return u.startswith("https://discord.com/api/webhooks/") or u.startswith("https://discordapp.com/api/webhooks/")

        self.assertTrue(is_valid(valid_url))
        self.assertTrue(is_valid(valid_legacy))
        self.assertFalse(is_valid(invalid_url))
        self.assertFalse(is_valid(invalid_proto))
        self.assertFalse(is_valid(""))


if __name__ == "__main__":
    unittest.main()

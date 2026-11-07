"""Centralized update management with resilient multi-tier fallbacks."""

import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any, List

from geodesync.core.config import GITHUB_REPO, RELEASES_API, CONFIG_URL, APP_VERSION


def parse_version_tuple(ver_str: str) -> tuple:
    """Parse version string into sortable tuple."""
    nums = []
    for part in ver_str.strip().lstrip("v").split("."):
        try:
            nums.append(int(part))
        except ValueError:
            nums.append(0)
    return tuple(nums)


def is_newer_version(candidate: str, current: str = APP_VERSION) -> bool:
    """Return True if candidate is strictly newer than current."""
    return parse_version_tuple(candidate) > parse_version_tuple(current)


class UpdateService:
    """Resilient update checker that bypasses GitHub API rate limits."""

    def __init__(self, repo: str = GITHUB_REPO):
        self.repo = repo
        self.headers = {"User-Agent": "GeodeSync-Client"}
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def check_for_update(self, timeout: float = 8.0) -> Optional[Dict[str, Any]]:
        """Fetch newest stable release with multi-tier fallback."""
        releases: List[Dict[str, Any]] = []

        # Tier 1: GitHub Releases API
        try:
            req = urllib.request.Request(RELEASES_API, headers=self.headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list):
                    releases = data
        except Exception:
            pass

        # Tier 1b: GitHub /releases/latest endpoint
        if not releases:
            try:
                latest_api = f"https://api.github.com/repos/{self.repo}/releases/latest"
                req = urllib.request.Request(latest_api, headers=self.headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if isinstance(data, dict) and data.get("tag_name"):
                        releases = [data]
            except Exception:
                pass

        # Tier 2: Public Atom Feed (Immune to API rate limits)
        if not releases:
            try:
                atom_url = f"https://github.com/{self.repo}/releases.atom"
                req = urllib.request.Request(atom_url, headers={"User-Agent": "GeodeSync-Client"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    root = ET.fromstring(resp.read().decode("utf-8", errors="replace"))
                    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
                        link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                        if link_el is not None and "href" in link_el.attrib:
                            href = link_el.attrib["href"]
                            tag = href.split("/")[-1].strip()
                            if tag:
                                releases.append({
                                    "tag_name": tag,
                                    "html_url": href,
                                    "published_at": "2026-01-01T00:00:00Z",
                                })
            except Exception:
                pass

        # Tier 3: version.json manifest
        if not releases:
            try:
                req = urllib.request.Request(CONFIG_URL, headers={"User-Agent": "GeodeSync-Client"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    cfg = json.loads(resp.read().decode("utf-8"))
                    app_v = str(cfg.get("app_version", "")).strip()
                    if app_v:
                        releases.append({
                            "tag_name": f"v{app_v.lstrip('v')}",
                            "html_url": f"https://github.com/{self.repo}/releases/tag/v{app_v.lstrip('v')}",
                            "published_at": "2026-01-01T00:00:00Z",
                        })
            except Exception:
                pass

        if not releases:
            return None

        # Sort and return latest
        def sort_key(rel):
            tag = str(rel.get("tag_name", "")).lstrip("v")
            return parse_version_tuple(tag)

        latest_rel = max(releases, key=sort_key)
        tag = str(latest_rel.get("tag_name", "")).lstrip("v")
        if is_newer_version(tag):
            return latest_rel
        return None

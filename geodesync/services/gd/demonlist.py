"""Pointercrate demon list and personal grind data. (GDManager mixin, moved verbatim from v2.8.0 main.py)."""

import os
import re
import json
import urllib.request
from geodesync.core.compat import decode_geometry_dash_save
from geodesync.core.config import APP_VERSION



class DemonlistMixin:
    """Pointercrate demon list and personal grind data."""

    def get_demon_and_grind_data(self):
        """
        Parses CCGameManager.dat to extract full progression stats, completed demons,
        and active hard grinds (levels with normal progress between 10% and 99%).
        """
        save_dir = self.get_save_data_dir()
        if not save_dir:
            return None
        gm_path = os.path.join(save_dir, "CCGameManager.dat")
        if not os.path.exists(gm_path):
            return None
        try:
            with open(gm_path, "rb") as f:
                raw = f.read()
            dec = decode_geometry_dash_save(raw).decode("utf-8", errors="ignore")

            name_m = re.search(r"<k>playerName</k><s>([^<]+)</s>", dec)
            player_name = name_m.group(1) if name_m else "Player"

            stats = {}
            gs_idx = dec.find("GS_value")
            if gs_idx != -1:
                chunk = dec[gs_idx : gs_idx + 4000]
                for m in re.finditer(r"<k>([0-9]+)</k><s>([0-9]+)</s>", chunk):
                    stats[int(m.group(1))] = int(m.group(2))

            grinds = []
            demons_completed = []

            k2_indices = [m.start() for m in re.finditer(r"<k>k2</k><s>", dec)]
            seen_names = set()

            for idx in k2_indices:
                sub = dec[idx : idx + 1200]
                dict_end = sub.find("</dict>")
                if dict_end != -1:
                    sub = sub[:dict_end]

                name_match = re.search(r"<k>k2</k><s>([^<]+)</s>", sub)
                if not name_match:
                    continue
                lvl_name = name_match.group(1).strip()
                if not lvl_name or lvl_name in seen_names:
                    continue
                seen_names.add(lvl_name)

                pct_match = re.search(r"<k>k19</k><i>([0-9]+)</i>", sub)
                if not pct_match:
                    continue
                percent = int(pct_match.group(1))

                auth_match = re.search(r"<k>k5</k><s>([^<]+)</s>", sub)
                author = auth_match.group(1).strip() if auth_match else "Unknown"

                prac_match = re.search(r"<k>k21</k><i>([0-9]+)</i>", sub)
                practice = int(prac_match.group(1)) if prac_match else 0

                att_match = re.search(r"<k>k18</k><i>([0-9]+)</i>", sub)
                attempts = int(att_match.group(1)) if att_match else 0

                is_demon = ("<k>k25</k><t/>" in sub) or ("<k>k25</k><t />" in sub)
                stars_match = re.search(r"<k>k26</k><i>([0-9]+)</i>", sub)
                stars = int(stars_match.group(1)) if stars_match else (10 if is_demon else 0)

                lvl_info = {
                    "name": lvl_name,
                    "author": author,
                    "percent": percent,
                    "practice": practice,
                    "attempts": attempts,
                    "is_demon": is_demon,
                    "stars": stars
                }

                if percent == 100:
                    if is_demon or stars >= 10:
                        demons_completed.append(lvl_info)
                elif percent >= 15:
                    grinds.append(lvl_info)

            grinds.sort(key=lambda x: (x["percent"], x["practice"]), reverse=True)
            demons_completed.sort(key=lambda x: x["name"].lower())

            return {
                "player_name": player_name,
                "stars": stats.get(6, 0),
                "demons": stats.get(5, len(demons_completed)),
                "diamonds": stats.get(13, 0),
                "coins": stats.get(8, 0),
                "user_coins": stats.get(12, 0),
                "orbs": stats.get(14, 0),
                "moons": stats.get(28, 0),
                "attempts": stats.get(2, 0),
                "jumps": stats.get(1, 0),
                "grinds": grinds[:30],
                "completed_demons": demons_completed[:50]
            }
        except Exception:
            return None

    def fetch_pointercrate_demons(self, limit=100):
        """
        Fetches the official Pointercrate Top Demonlist via public API.
        Returns (success: bool, demons_or_error: list|str).
        """
        import urllib.request
        url = f"https://pointercrate.com/api/v2/demons/listed/?limit={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": f"GeodeSync/{APP_VERSION}"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            demons = []
            for item in data:
                demons.append({
                    "position": item.get("position", 0),
                    "name": item.get("name", "Unknown"),
                    "requirement": item.get("requirement", 100),
                    "video": item.get("video", ""),
                    "publisher": item.get("publisher", {}).get("name", "Unknown") if isinstance(item.get("publisher"), dict) else "Unknown",
                    "verifier": item.get("verifier", {}).get("name", "Unknown") if isinstance(item.get("verifier"), dict) else "Unknown",
                })
            return True, demons
        except Exception as e:
            return False, str(e)

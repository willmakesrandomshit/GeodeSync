"""Game constants that are not release metadata (moved from v2.8.0 main.py)."""


from geodesync.platform.process_manager import IS_MAC



EXPECTED_DEPOT_BYTES = 230000000 if IS_MAC else 204000000


if IS_MAC:
    KNOWN_VERSIONS = {
        "2.2081 (Geode Compatible • macOS Recommended)": {
            "manifest": "8780295549609362522",
            "ver": "2.2081",
            "size": 0
        }
    }
else:
    KNOWN_VERSIONS = {
        "2.2081 (Geode Compatible • Recommended)": {
            "manifest": "3816559102876907245",
            "ver": "2.2081",
            "sizes": (10700288, 10698752),
            "size": 10698752
        },
        "2.113 (Classic 2.11 Legacy)": {
            "manifest": "7938363717144760233",
            "ver": "2.113",
            "size": 7578624
        }
    }


SIZES_22081 = (10700288, 10698752)


SIZE_2209 = 13178880

SIZE_22081 = 10698752

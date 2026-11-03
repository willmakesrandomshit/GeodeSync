# GeodeSync v2.4.2 — Hotfix & UI Stability Polish

## What's New in v2.4.2

### 🛡️ Critical Self-Repair & Tab Crash Resolution
- **Fixed `AttributeError: 'bool' object has no attribute 'get'` in Mod Store & Demonlist:**
  - Resolved tuple return handling from `fetch_geode_store_mods()` and `fetch_pointercrate_demons()`.
  - Added strict dictionary type validation (`isinstance(item, dict)`) across all store and demonlist rendering routines to guarantee zero UI freezes.
- **Fixed Custom Death SFX Status Inspection:**
  - Corrected dictionary unpacking for `get_custom_sfx_status()` in the Jukebox & SFX tab.
- **Rock-Solid Update Discovery & Asset Matching:**
  - `fetch_latest_published_release` now automatically prioritizes published releases that already contain verified packages for the current OS.
  - Safe exception trapping prevents false "verified package for this platform is not available yet" notifications during asset uploads.
- **100% Comprehensive Test Suite:**
  - All unit tests passing across all supported operating systems.

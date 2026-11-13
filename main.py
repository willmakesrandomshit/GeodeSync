"""GeodeSync v3 launcher.

All logic lives in the ``geodesync`` package (core, platform, services, ui). This file only:
  * installs the crash-log excepthook,
  * re-exports the public names the v2.8.0 tests and tools import from ``main``,
  * runs the app when executed (``python main.py``, the PyInstaller entry point and ``GeodeSync.pyw``).
"""
import os
import sys
import traceback

import re
import json
import shutil
import stat
import time
import tempfile
import urllib.request
import webbrowser
import threading
import subprocess
import base64
import hashlib
import platform
import posixpath
import zipfile
import tarfile
import zlib
import struct
import plistlib
from pathlib import PurePosixPath
from urllib.parse import urlparse
from xml.parsers.expat import ExpatError
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime

# Re-exports (compatibility with v2.8.0 imports; the code lives in the geodesync package).
from geodesync.platform.process_manager import IS_LINUX, IS_MAC, IS_WIN  # noqa: E402
from geodesync.services.diagnostics import (  # noqa: E402
    ensure_local_onedrive_files,
    check_vc_redist_installed,
    check_folder_writable_and_space,
    WINDOWS_PE_MACHINE_NAMES,
    read_windows_pe_machine,
    validate_windows_game_images,
    explain_error_text,
    scan_installation_issues,
)

if IS_WIN:
    import winreg
    import winsound
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
else:
    winreg = None
    winsound = None
# v3: GDManager, helpers and the Tk UI live in the geodesync package; main re-exports them for legacy tests.
from geodesync.platform.system import (  # noqa: E402
    open_url_or_path,
    inspect_macos_app_security,
    install_vc_redist,
    find_linux_geometry_dash_pids,
    desktop_exec_value,
    wait_for_process,
    get_app_data_dir,
)
from geodesync.services.geode_install import (  # noqa: E402
    fetch_latest_geode_release,
    install_or_update_geode,
    GEODE_PACKAGE_MAX_DOWNLOAD_BYTES,
    GEODE_PACKAGE_MAX_EXPANDED_BYTES,
    safe_zip_member_target,
    validate_geode_package_zip,
    extract_geode_package_safely,
    is_safe_geode_mod_id,
)
from geodesync.core.game_constants import (  # noqa: E402
    EXPECTED_DEPOT_BYTES,
    KNOWN_VERSIONS,
    SIZES_22081,
    SIZE_2209,
    SIZE_22081,
)
from geodesync.core.compat import (  # noqa: E402
    decode_geometry_dash_save,
    encode_geometry_dash_save,
    official_release_page,
)
from geodesync.core.crashlog import (  # noqa: E402
    _crash_log_path,
    _global_excepthook,
)
from geodesync.services.presence import (  # noqa: E402
    DiscordRPC,
)
from geodesync.ui.theme import (  # noqa: E402
    UI,
)
from geodesync.ui.components import (  # noqa: E402
    ModernButton,
    ScrollableFrame,
)
from geodesync.ui.app import (  # noqa: E402
    GeodeSyncApp,
)
from geodesync.services.gd.steam import (  # noqa: E402
    SteamMixin,
)
from geodesync.services.gd.game import (  # noqa: E402
    GameMixin,
)
from geodesync.services.gd.mods import (  # noqa: E402
    ModsMixin,
)
from geodesync.services.gd.assets import (  # noqa: E402
    AssetsMixin,
)
from geodesync.services.gd.saves import (  # noqa: E402
    SavesMixin,
)
from geodesync.services.gd.demonlist import (  # noqa: E402
    DemonlistMixin,
)
from geodesync.services.gd.manager import (  # noqa: E402
    GDManager,
)
from geodesync.core.config import (  # noqa: E402
    APP_VERSION,
    GITHUB_REPO,
    CONFIG_URL,
    RELEASES_API,
    GEODE_REPO,
    GEODE_API,
    DEPOT_ID,
    DEFAULT_MANIFEST,
    DEFAULT_TARGET_GD,
)

sys.excepthook = _global_excepthook

# v3: these live in the geodesync package; main re-exports them for the UI and legacy tests.
from geodesync.platform.process_manager import (  # noqa: E402
    SW_HIDE,
    STARTF_USESHOWWINDOW,
    CREATE_NO_WINDOW,
    _StartupInfoFallback,
    get_silent_startupinfo,
    get_silent_creationflags,
    safe_run_command,
    safe_check_output,
    is_win_process_running,
    safe_popen_command,
)
from geodesync.services.app_update import (  # noqa: E402
    MACOS_UPDATE_MAX_BYTES,
    APP_UPDATE_MAX_BYTES,
    is_newer_app_version,
    version_sort_key,
    _synthesize_release_for_tag,
    fetch_latest_published_release,
    verify_release_asset_digest,
    select_macos_update_asset,
    verify_macos_update_digest,
    select_app_update_asset,
    release_has_app_update,
    validate_app_update_zip,
    safe_extract_app_zip,
    download_verified_app_update,
    mark_windows_download,
    mark_macos_quarantine,
    _normalized_update_tar_name,
    validate_app_update_tar,
    _application_root,
    _wait_for_process_exit,
    _apply_staged_update,
    _schedule_windows_update_cleanup,
    _run_update_helper,
    validate_macos_update_zip,
)

# Re-exports (compatibility with v2.8.0 imports; the code lives in the geodesync package).
from geodesync.services.install_transaction import (  # noqa: E402
    _copy_directory_transactionally,
    safe_copy_item,
    atomic_write_json,
    _remove_path,
    _tree_size,
    _copy_file_with_retry,
    _safe_replace,
    _copy_entry,
    _rollback_install_transaction,
    recover_pending_install_transactions,
    install_depot_transactionally,
)
from geodesync.platform.steam import (  # noqa: E402
    APP_ID,
    should_apply_downloaded_depot,
    find_macos_game_app,
    validate_macos_game_app,
    reset_invalid_macos_depot_cache,
    is_steam_library_game_path,
    request_macos_steam_launch,
    discover_linux_steam_roots,
    discover_steam_game_folders,
)


if __name__ == "__main__":
    from geodesync.app import run

    run()

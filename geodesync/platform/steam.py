"""Steam and macOS game-app helpers (moved verbatim from v2.8.0 main.py): library discovery, depot gating, macOS app validation and Steam launch."""

import os
import re
import shutil
import subprocess
import plistlib
from xml.parsers.expat import ExpatError


APP_ID = "322170"


def should_apply_downloaded_depot(steam_reported_complete, depot_valid):
    """Only validated depot contents may be installed; logs are advisory."""
    return bool(depot_valid)


def find_macos_game_app(game_path):
    """Resolve either a Steam game folder or a selected .app bundle."""
    if not game_path:
        return None
    game_path = os.path.abspath(os.path.expanduser(str(game_path)))
    if game_path.lower().endswith(".app"):
        return game_path if os.path.isdir(game_path) else None
    for name in ("Geometry Dash.app", "GeometryDash.app"):
        candidate = os.path.join(game_path, name)
        if os.path.isdir(candidate):
            return candidate
    return None


def validate_macos_game_app(app_path):
    """Return a useful bundle validation error, or None when launchable structure exists."""
    if not app_path or not os.path.isdir(app_path):
        return "Geometry Dash.app was not found in the selected Steam library."
    plist_path = os.path.join(app_path, "Contents", "Info.plist")
    try:
        with open(plist_path, "rb") as stream:
            metadata = plistlib.load(stream)
    except (OSError, plistlib.InvalidFileException, ValueError, ExpatError, TypeError) as exc:
        return f"Geometry Dash.app has a missing or unreadable Info.plist ({exc})."

    executable_name = metadata.get("CFBundleExecutable")
    if not isinstance(executable_name, str) or not executable_name or os.path.basename(executable_name) != executable_name:
        return "Geometry Dash.app has an invalid CFBundleExecutable entry."
    executable = os.path.join(app_path, "Contents", "MacOS", executable_name)
    if not os.path.isfile(executable):
        return f"Geometry Dash.app is incomplete: its executable is missing ({executable_name})."
    if not os.access(executable, os.X_OK):
        return "Geometry Dash.app's main executable is not marked executable. Use Steam's Verify integrity action to restore it."
    return None


def reset_invalid_macos_depot_cache(depot_path, installed_game_path=None):
    """Remove only a malformed Geometry Dash Steam depot cache for a clean retry.

    The installed game is never a valid target: the path must be Steam's exact
    app_322170/depot_322172 content-cache directory, and the cached app bundle
    must exist but fail structural validation.
    """
    if not depot_path or os.path.islink(depot_path) or not os.path.isdir(depot_path):
        return False

    target = os.path.realpath(os.path.abspath(depot_path))
    normalized = os.path.normcase(target).replace("\\", "/").rstrip("/")
    expected_suffix = f"/steamapps/content/app_{APP_ID}/depot_322172"
    if not normalized.endswith(expected_suffix):
        raise ValueError("Refusing to reset a path that is not the Geometry Dash Steam depot cache.")

    installed = os.path.realpath(os.path.abspath(installed_game_path)) if installed_game_path else None
    if installed and (target == installed or target.startswith(installed + os.sep)):
        raise ValueError("Refusing to reset the installed Geometry Dash folder.")

    app_path = find_macos_game_app(target)
    if not app_path:
        return False
    problem = validate_macos_game_app(app_path)
    if not problem:
        return False

    # Do not follow a bundle symlink, even though the parent cache path was
    # checked above. Steam's cache contents are disposable; the live install
    # and save directory are outside this narrowly validated path.
    if os.path.islink(app_path):
        raise ValueError("Refusing to reset a symlinked Geometry Dash.app cache.")
    shutil.rmtree(target)
    return True


def is_steam_library_game_path(path):
    """Recognize a Geometry Dash folder inside any Steam library, including Windows paths."""
    parts = [part.casefold() for part in re.split(r"[/\\]+", str(path or "").strip()) if part]
    for index in range(max(0, len(parts) - 2)):
        if parts[index:index + 2] == ["steamapps", "common"]:
            folder = parts[index + 2]
            if folder in ("geometry dash", "geometrydash", "gd") or folder.startswith("geometry dash") or folder.startswith("geometrydash"):
                return True
    return False


def request_macos_steam_launch(game_path, runner=None):
    """Ask LaunchServices to route the game request through Steam; this is not proof the game started."""
    app_path = find_macos_game_app(game_path)
    validation_error = validate_macos_game_app(app_path)
    if validation_error:
        return False, validation_error

    runner = runner or subprocess.run
    try:
        result = runner(
            ["/usr/bin/open", f"steam://run/{APP_ID}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"macOS could not pass the launch request to Steam: {exc}"
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip()
        if details:
            details = f"\n\nmacOS reported: {details[:1200]}"
        return False, f"macOS rejected the Steam launch request (exit {result.returncode}).{details}"
    return True, "Steam accepted the Geometry Dash launch request. This confirms dispatch only; Steam must still start the game."


def discover_linux_steam_roots(home=None, environ=None, which=None):
    """Find common native/Flatpak Steam roots without assuming one install path."""
    home = os.path.expanduser(home or "~")
    environ = os.environ if environ is None else environ
    which = shutil.which if which is None else which
    xdg_data = environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    candidates = [
        environ.get("STEAM_COMPAT_CLIENT_INSTALL_PATH"),
        environ.get("STEAM_DIR"),
        os.path.join(xdg_data, "Steam"),
        os.path.join(home, ".steam", "steam"),
        os.path.join(home, ".steam", "root"),
        os.path.join(home, ".var", "app", "com.valvesoftware.Steam", "data", "Steam"),
    ]
    steam_command = which("steam") if which else None
    if steam_command:
        current = os.path.dirname(os.path.realpath(steam_command))
        for _ in range(5):
            if os.path.isdir(os.path.join(current, "steamapps")):
                candidates.append(current)
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent

    roots = []
    seen = set()
    for candidate in candidates:
        if not candidate:
            continue
        expanded = os.path.abspath(os.path.expanduser(os.path.expandvars(str(candidate))))
        if not os.path.isdir(expanded):
            continue
        canonical = os.path.realpath(expanded)
        if canonical not in seen:
            roots.append(canonical)
            seen.add(canonical)
    return roots


def discover_steam_game_folders(steam_roots):
    """Return Geometry Dash folders from each Steam root and its listed libraries."""
    folders = []
    seen = set()
    for root in steam_roots:
        libraries = [root]
        vdf_path = os.path.join(root, "steamapps", "libraryfolders.vdf")
        try:
            with open(vdf_path, "r", encoding="utf-8", errors="ignore") as stream:
                content = stream.read()
            libraries.extend(re.findall(r'"path"\s+"((?:\\\\.|[^"\\])*)"', content, re.IGNORECASE))
        except OSError:
            pass
        for library in libraries:
            library = library.replace(r"\\", "\\").replace(r'\"', '"')
            game = os.path.join(os.path.expanduser(library), "steamapps", "common", "Geometry Dash")
            canonical = os.path.realpath(game)
            if canonical not in seen and os.path.isdir(canonical):
                folders.append(canonical)
                seen.add(canonical)
    return folders

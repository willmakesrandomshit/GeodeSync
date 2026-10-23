"""Build a self-contained, windowed macOS GeodeSync app with PyInstaller."""

from __future__ import annotations

import argparse
import os
import plistlib
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
APP_NAME = "GeodeSync"
APP_IDENTIFIER = "com.willmakesrandomshit.geodesync"


def make_app_icon(destination: Path) -> None:
    """Create a standard .icns from the repo thumbnail using macOS tools."""
    iconset = ROOT / "build" / "GeodeSync.iconset"
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir(parents=True)
    source = ROOT / "assets" / "thumbnail_square.png"
    if not source.exists():
        raise FileNotFoundError(f"App icon source is missing: {source}")

    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            pixels = size * scale
            name = f"icon_{size}x{size}" + ("@2x" if scale == 2 else "") + ".png"
            subprocess.run(
                ["sips", "-s", "format", "png", "-z", str(pixels), str(pixels),
                 str(source), "--out", str(iconset / name)],
                check=True,
                stdout=subprocess.DEVNULL,
            )
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(destination)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", choices=("arm64", "x86_64", "universal2"), default="native")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()

    if sys.platform != "darwin":
        raise SystemExit("Build the macOS app on a macOS runner (GitHub Actions does this automatically).")
    try:
        import tkinter  # noqa: F401
    except ImportError as exc:
        raise SystemExit("This build Python has no Tk support; use the python.org macOS Python in CI.") from exc

    from PyInstaller.__main__ import run as pyinstaller_run

    args.output.mkdir(parents=True, exist_ok=True)
    output_dir = args.output.resolve()
    work_dir = output_dir.parent / ".GeodeSync-pyinstaller"
    work_dir.mkdir(parents=True, exist_ok=True)
    icon_path = ROOT / "build" / "GeodeSync.icns"
    make_app_icon(icon_path)
    arch = args.arch
    if arch == "native":
        arch = "arm64" if os.uname().machine == "arm64" else "x86_64"

    pyinstaller_run([
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onedir",
        "--name", APP_NAME,
        "--icon", str(icon_path),
        "--osx-bundle-identifier", APP_IDENTIFIER,
        "--target-architecture", arch,
        "--add-data", f"{ROOT / 'icon.ico'}:.",
        "--distpath", str(output_dir),
        "--workpath", str(work_dir),
        "--specpath", str(work_dir),
        str(ROOT / "main.py"),
    ])

    app = args.output.resolve() / f"{APP_NAME}.app"
    executable = app / "Contents" / "MacOS" / APP_NAME
    info_plist = app / "Contents" / "Info.plist"
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise SystemExit(f"PyInstaller did not produce a runnable app executable: {executable}")

    with info_plist.open("rb") as stream:
        metadata = plistlib.load(stream)
    version_match = re.search(
        r'^APP_VERSION\s*=\s*[\"\']([^\"\']+)',
        (ROOT / "main.py").read_text(),
        re.MULTILINE,
    )
    if not version_match:
        raise SystemExit("Could not read APP_VERSION from main.py")
    app_version = version_match.group(1)
    release_ref = os.environ.get("GITHUB_REF_NAME", "")
    if release_ref.startswith("v") and release_ref[1:] != app_version:
        raise SystemExit(
            f"Release tag {release_ref} does not match APP_VERSION {app_version}; "
            "update the app version before creating the release."
        )
    metadata["CFBundleShortVersionString"] = app_version
    metadata["CFBundleVersion"] = app_version
    metadata["LSMinimumSystemVersion"] = "11.0" if arch in ("arm64", "universal2") else "10.15"
    metadata["NSHighResolutionCapable"] = True
    with info_plist.open("wb") as stream:
        plistlib.dump(metadata, stream, sort_keys=False)

    # Images may inherit Finder metadata from the checked-out project. macOS
    # does not permit that metadata inside a signed app bundle.
    subprocess.run(["xattr", "-cr", str(app)], check=True)

    # Ad-hoc signing seals the bundle for local use. Distribution signing and
    # notarization require the owner's Apple Developer credentials.
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(app)], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
    print(f"Built self-contained {arch} app: {app}")


if __name__ == "__main__":
    main()

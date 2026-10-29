# Building GeodeSync

Build from a clean checkout of the official repository and inspect the source
before running it. Release builds should be made from a reviewed commit/tag.

## Windows

Use Windows with Python and the build requirements from this repository:

```powershell
python -m pip install -r requirements-windows-build.txt
./package_windows.ps1
```

The script produces an onedir app folder (`dist/GeodeSync`) and a portable ZIP
under `dist/`. Keep `GeodeSync.exe` and its `_internal` runtime directory together;
the onedir layout avoids PyInstaller's per-launch `_MEI...` extraction. It signs the executable
only if a code-signing certificate is already installed in the current user's
certificate store. An unsigned output is not signed by this process and should
not be described as publisher-verified.

## macOS

Use a supported macOS runner and install `requirements-macos-build.txt`, then run
`python build_macos.py --arch arm64` or `--arch x86_64`. The build seals the
finished bundle after editing `Info.plist` and verifies that seal before it can
be packaged. CI replaces the ad-hoc seal with a Developer ID signature and
notarizes/staples the app when the corresponding Apple secrets are configured.
An app that fails strict `codesign --verify --deep --strict` must not be
published. A structurally valid ad-hoc signature is still not the same as a
Developer ID signature or notarization.

## Linux

Build on Ubuntu 22.04 (glibc 2.35) with its matching system Python and Tk,
plus the pinned PyInstaller version. This older build baseline prevents bundled
Tcl/Tk from requiring a newer glibc than SteamOS on Steam Deck provides. Use
Ubuntu's Python so the venv can see the matching Tk runtime:

```sh
sudo apt-get install python3 python3-venv python3-tk xvfb xauth
python3 -m venv --system-site-packages .venv
.venv/bin/python -c "import tkinter; print(tkinter.TkVersion)"
.venv/bin/python -m pip install -r requirements-linux-build.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m PyInstaller --noconfirm --clean --onefile --windowed --name GeodeSync --add-data "icon.ico:." main.py
```

The Linux CI workflow asserts the glibc baseline, runs tests under Xvfb, and
launches the packaged app under Xvfb to catch missing runtime files or Tk
startup failures. Linux builds target Steam's Windows game files under Proton;
use Desktop Mode on Steam Deck. CI does not replace testing on a physical Deck.

## Checks

Run the repository regression suite with:

```sh
python -m unittest discover -s tests -v
```

The repository does not currently pin all build dependencies with hashes or
provide a reproducible-build attestation. A local build is useful for inspection,
but does not by itself prove that a published binary corresponds byte-for-byte to
the inspected source. Windows signing and macOS signing/notarization must be
verified on their respective platforms with real configured credentials.

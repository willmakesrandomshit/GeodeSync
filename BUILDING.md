# Building GeodeSync

Build from a clean checkout of the official repository and inspect the source
before running it. Release builds should be made from a reviewed commit/tag.

## Windows

Use Windows with Python and the build requirements from this repository:

```powershell
python -m pip install -r requirements-windows-build.txt
./package_windows.ps1
```

The script produces an executable and ZIP under `dist/`. It signs the executable
only if a code-signing certificate is already installed in the current user's
certificate store. An unsigned output is not signed by this process and should
not be described as publisher-verified.

## macOS

Use a supported macOS runner and install `requirements-macos-build.txt`, then run
`python build_macos.py --arch arm64` or `--arch x86_64`. The release workflow may
sign and notarize only when all corresponding Apple secrets are configured.

## Linux

Install Python, Tk, and PyInstaller, then follow the Linux packaging commands in
`.github/workflows/build-macos.yml`.

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

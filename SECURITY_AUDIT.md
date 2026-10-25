# GeodeSync security audit — 2026-10-24

## Scope and conclusion

Reviewed the application entry points (`main.py`, `GeodeSync.pyw`), Geode
installer and mod-update flows, Windows package script, macOS build/update flow,
GitHub Actions release workflow, Steam watchdog, configuration, and existing
tests. `main.py` and `GeodeSync.pyw` are kept byte-identical.

No evidence of Steam credential/token harvesting, hidden persistence, or
unauthorized upload of save files was found in the inspected code paths. This is
a source review, not a malware-scanner verdict or proof that a published binary
matches source.

## Findings and repairs

### High — ZIP path traversal in Geode installation — fixed

`install_or_update_geode` previously joined ZIP member names directly to the
Geometry Dash folder and wrote them without containment checks. A crafted Geode
archive could use `../` to target files outside the game directory. The installer
now validates every member before writing, rejects traversal, drive/ADS names,
symlinks, special files, symlinked destination parents, duplicate targets, and
oversized archives. Files are staged and replaced with rollback on failure.
Geode release downloads are restricted to the expected GitHub release path,
bounded by size, and checked against GitHub's published SHA-256 digest.

Evidence: `main.py` around `install_or_update_geode`, `safe_zip_member_target`,
`validate_geode_package_zip`, and `extract_geode_package_safely`; regression cases
are in `tests/test_security_hardening.py`.

### High — app self-update lacked independent publisher verification — mitigated

The previous Windows updater downloaded a release executable, generated a batch
file to replace the running executable, and ran `Unblock-File` on it. The Mac
updater checked the GitHub asset digest but accepted a missing or invalid code
signature and cleared extended attributes with `xattr -cr`. A checksum served by
the same GitHub release service is not independent publisher authentication.

Automatic binary replacement is removed. The update button is now **View
release** and opens only the canonical GeodeSync Releases page. Windows package
launch/install scripts no longer run `Unblock-File`, and Mac build/update code no
longer strips extended attributes. The Windows packager now fails if an attempted
Authenticode signature is not valid.

Evidence: `main.py` around `start_self_update`; `package_windows.ps1`;
`build_macos.py`; release workflow checksum-generation step.

### Medium — obfuscated save parsing — clarified

The five XOR/Base64 decode sites all parsed Geometry Dash save files; they did
not decode commands, endpoints, or executable payloads. They implement the
game's save wrapper (XOR `0x0B`, URL-safe Base64, zlib). The repeated transform is
now in named `decode_geometry_dash_save` and `encode_geometry_dash_save`
functions, with a round-trip regression test.

### Medium — locally supplied mod IDs used in paths — fixed

Mod IDs read from local `.geode` metadata were interpolated into an API URL and
an `unzipped` cache path that is later recursively removed. IDs are now checked
against Geode's dotted `author.mod` form before querying or deleting that cache.

## Network and local-data review

* Geometry Dash save files, mod metadata, Steam install paths, and selected game
  files are read locally. Game switching, mod installation, texture changes,
  backups, and selected save tools write to the chosen game/save directories.
* Steam discovery reads the current-user Steam path registry key on Windows. Game
  switching launches Steam with explicit depot arguments. No Steam credentials,
  session cookies, or tokens are read by the inspected code.
* The desktop Discord feature uses local Discord IPC to publish Rich Presence.
  The separate watchdog can send a version/release notice to a webhook explicitly
  supplied in `GEODESYNC_DISCORD_WEBHOOK`; the webhook URL is secret material.
* GitHub/Geode API traffic supports update checks and explicit release/mod
  installation. The NONG song feature also supports a direct URL explicitly
  entered by the user. The app does not enforce a global network host allowlist.

See [PRIVACY.md](PRIVACY.md) for the current endpoint inventory.

## Remaining risks and work

1. **Release publisher identity is not independently established.** No pinned
   signing key or Windows signing credential is configured in this checkout.
   The Windows CI build is unsigned; Mac signing/notarization is conditional on
   secrets. Checksums detect corruption but do not authenticate the publisher.
   Configure real signing credentials and a verifiable provenance/signature
   workflow before restoring automatic app updates.
2. **No complete SBOM or dependency vulnerability scan was generated.** The
   build requirements declare PyInstaller only, but the packaged Python/Tk
   runtime and transitive build components need a platform-specific SBOM. `pip-audit`,
   Bandit, and Gitleaks were not installed in this environment; a targeted
   repository secret-pattern scan found no matching credentials.
3. **Windows-only validation remains open.** This environment cannot run the
   PowerShell packager, inspect Authenticode results on Windows, or test the
   executable with Defender/SmartScreen. No antivirus scan was run.
4. **The latest Geode package checksum is sourced from GitHub's release API.**
   This guards transfer corruption but is not independent signing by the Geode
   project. Treat the official Geode release repository as the trust root.
5. **Some user-selected downloads remain broad.** In particular, the NONG audio
   feature accepts a URL entered by the user. Keep it user-initiated and avoid
   using it for executable content.
6. **GitHub Actions use version tags for third-party actions** (for example
   `actions/checkout@v4`); pinning reviewed immutable commit SHAs would reduce
   supply-chain exposure.

## Verification performed

* `python3 -m unittest discover -s tests -v` — 54 tests passed.
* `python3 -m py_compile main.py GeodeSync.pyw build_macos.py steam_watchdog.py` — passed.
* `git diff --check` — passed.
* Built an isolated arm64 macOS app from the modified source with PyInstaller
  6.22.3 / Python 3.14.3. Bundle ID, version `2.3.0`, and arm64 Mach-O executable
  checks passed. The app was not launched, signed by a Developer ID, or notarized.
* Windows build, Windows install, game launch, live Steam operations, antivirus
  scans, and live release publishing were not performed.

The project is safer and more auditable after these changes, but it is not ready
to claim independently verified releases until signing, provenance, SBOM, and
Windows validation gaps are closed.

## 2026-10-25 release audit addendum

The v2.3.2 release work addresses a reported Windows launch failure showing
PyInstaller unable to load `python314.dll` from a `_MEI...` temporary folder.
That error is consistent with a failed one-file extraction/runtime load, but the
screenshot does not identify the cause conclusively. The Windows build has been
changed from PyInstaller `--onefile` to `--onedir`, so the interpreter runtime
ships alongside the executable and is not extracted into a per-run `_MEI...`
directory. This reduces exposure to that failure mode; validation on Windows CI
and the affected PC is still needed before claiming the user's issue is fixed.

The release now packages Windows as a ZIP containing the app folder and `_internal`
runtime directory, and publishes stable `GeodeSync-Windows.zip` and
`GeodeSync-Linux.tar.gz` names for download links. Windows CI runs the regression
suite before packaging. The Discord release helper derives the version from
`version.json` and uses the current release notes and asset names.

Verification in this checkout: `python3 -m unittest discover -s tests -v` — 57
tests passed; `python3 -m py_compile main.py GeodeSync.pyw build_macos.py
steam_watchdog.py send_discord_update.py` — passed. `git diff --check` passes when
CRLF is treated as the repository's line ending (`core.whitespace=cr-at-eol`).
This Mac cannot run the PowerShell Windows packager or
exercise Windows Defender, SmartScreen, Steam, or the affected user's machine.
No antivirus scan or live game launch was performed.

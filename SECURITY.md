# Security

GeodeSync is an independent community project. It is not created, endorsed, or
distributed by the Geode SDK team or Valve.

## Reporting a security issue

Please report suspected vulnerabilities privately to the repository owner before
publishing exploit details. Include the affected version, operating system,
steps to reproduce, and relevant logs with personal paths and account data
removed. Do not attach Steam credentials, cookies, tokens, or unredacted save
files.

## Release authenticity

Official source and release downloads are hosted in this repository:

* Source: <https://github.com/willmakesrandomshit/GeodeSync>
* Releases: <https://github.com/willmakesrandomshit/GeodeSync/releases>

GeodeSync currently has no configured Windows Authenticode signing identity and
does not have a pinned release-signing key for independent artifact verification.
GitHub's asset SHA-256 digest detects transfer corruption, but it is served by the
same release service and is not a separate proof of publisher identity. The app
verifies the digest and stages stable release packages before asking to restart.
Do not bypass SmartScreen, Defender,
Gatekeeper, or quarantine warnings. If a release is unsigned or flagged, stop and
ask the maintainer for verifiable signing and scan evidence.

When a release includes `SHA256SUMS.txt`, verify the downloaded file from the
repository root with `shasum -a 256 -c SHA256SUMS.txt` on macOS/Linux, or compare
`(Get-FileHash .\GeodeSync-Windows.zip -Algorithm SHA256).Hash` in PowerShell with the
matching entry in the file. This confirms the bytes match the published checksum;
it does not prove who published them.

## What the app does

See [PRIVACY.md](PRIVACY.md) for network destinations and local data access and
[BUILDING.md](BUILDING.md) for source-build instructions and verification limits.

GeodeSync changes Geometry Dash installation files only after a user chooses a
game-management action. Such actions can prevent the game from launching if Steam
or Geode versions are incompatible. Back up saves before changing game files.

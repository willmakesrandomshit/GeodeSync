# GeodeSync v3.0.0 — Rebuilt foundation

v3.0.0 is the same GeodeSync you know, rebuilt on a cleaner foundation so it breaks less and is easier to fix. There are no new buttons in this release: the goal was to keep every v2.8.0 behaviour while making the code testable and safe to change.

## What changed under the hood
- `main.py` is now a small launcher. The 11,000-line single file is split into a `geodesync` package: `core` (pure logic), `platform` (OS and Steam adapters), `services` (game, Geode, mods, saves, assets, updates, diagnostics) and `ui` (the Tk window).
- The self-update engine, the transactional depot installer (journal and rollback), Steam discovery and the installation diagnostics are separate modules with their own tests, and none of them import the UI.
- `GDManager` is a thin facade over six domain services (Steam, game, mods, assets, saves, demon list).
- `GeodeSync.pyw` no longer keeps a hand-synced copy of the code; it just runs `main.py`.
- 185 automated tests pass, including parity tests against the v2.8.0 behaviour.

## What did not change
- Same trust model: official GitHub Releases only, digest-checked downloads, no OS-warning bypasses.
- Same Steam depot switching, Geode install, mod, save and texture features.
- macOS builds stay withheld until they are signed and notarised.

## Known limits
- The UI is still the v2.8.0 Tk window, moved as-is into `geodesync/ui/app.py`. A redesign is future work.
- The single-file build scripts and CI workflows still target `main.py` as the entry point.

# GeodeSync v3: architecture and rewrite plan

Written from a full read of v2.8.0 (`main.py` == `GeodeSync.pyw`, 11,937 lines). Everything below describes what the code does today, not what it was meant to do.

## 1. What v2.8.0 actually is

| Layer | Where (v2.8.0) | Size | What it does |
|---|---|---|---|
| Process/OS helpers | `main.py` 1-200, 1552-1760 | ~400 lines | Silent subprocess wrappers (no console windows on Windows), Windows process lookup, Linux `/proc` scan, Steam root discovery |
| Save codec | `main.py` 202-215 | 14 lines | GD save wrapper: XOR 0x0B, URL-safe Base64, zlib |
| Discord Rich Presence | `DiscordRPC` 225-478 | ~250 lines | Raw IPC to the local Discord client |
| Self-update engine | 480-1270 | ~800 lines | Multi-tier release lookup, verified download (GitHub sha256 digest), archive validation, staged swap, restart helper |
| Geode loader install | 638-860 | ~220 lines | Download Geode, validate ZIP, transactional extract with rollback |
| Install safety | 1619-2370 | ~750 lines | Transactional depot copy with journal + rollback, PE header checks, OneDrive/VC++ checks, error explanations, issue scanner |
| `GDManager` | 2371-4617 | ~2,250 lines, 63 methods | Everything about the game: find installs, Steam depot/manifest lock, Geode detection, mods (list/toggle/update/store), textures, audio (practice music, death SFX), saves (slots, bloat cleaner, bundles, resurrect), Pointercrate demonlist, presets |
| UI | `GeodeSyncApp` 4717-11937 | ~7,200 lines, 149 methods | Tkinter app: dashboard, notebook tabs (mods, library, tools, store, demonlist...), dialogs (29 `open_*`), health check, tray, tabs, banners, settings, shortcuts |
| Packaging/CI | `build_macos.py`, `package_windows.ps1`, workflows | | PyInstaller builds for Win/macOS/Linux, release notes, Discord announcements |

Facts that shape the rewrite:
- `main.py` and `GeodeSync.pyw` are byte-identical copies kept in sync by hand. That duplication is a standing bug risk.
- The code is security-conscious and much of it is good (path-traversal checks, transactional installs, digest verification). The right move is to **port and test it, not rewrite it from memory**.
- 161 regression tests exist and all pass on v2.8.0. They import `main`, so they pin behaviour.
- A `geodesync/` package already exists (588 lines: config, models, a few services). It duplicates logic in `main.py` rather than replacing it. v3 finishes that migration.
- The UI layer is 60% of the code and tightly coupled to `GDManager`, which is why changes keep breaking Linux Tk layouts.

## 2. v3 principles

1. **UI-agnostic core.** All game, mod, save, update and diagnostics logic lives in pure Python modules with no Tk imports, so it is unit-testable on any OS.
2. **One entry point.** `main.py` becomes a 20-line launcher; no duplicated `.pyw`.
3. **Ported, not rewritten.** Each module is moved from v2.8.0 with a parity test against the old implementation until the old copy is deleted.
4. **Never touch the user's game or saves without a snapshot and a rollback path.** Every destructive service takes a `Transaction`/journal.
5. **Honest status.** Services return typed results (`Ok`, `Warn`, `Fail` with a reason and a fix), never raw exceptions to the UI.
6. **Same trust model.** Official GitHub Releases only, digest-checked; no OS-warning bypasses; macOS builds stay withheld until signed and notarised.

## 3. Target layout

```
geodesync/
  core/        versioning, save_codec, integrity, archive_safety, config, models, errors, results      (pure, tested)
  platform/    process_manager, steam (discovery, depot, manifest), paths, autostart, tray, notify        (OS adapters)
  services/    game_service, geode_service, mod_service, save_service, texture_service, audio_service,
               demonlist_service, update_service, diagnostics_service, presence_service, announcements   (no UI)
  ui/          app.py, theme, components/, views/{home,mods,store,library,saves,tools,demonlist,settings}.py
tests/         one test module per service + parity tests while v2 code still exists
```

## 4. Migration order (each step ships green)

1. **Core primitives** (done on this branch): `versioning`, `save_codec`, `integrity`, `archive_safety` with parity tests against v2.8.0.
2. Update engine (`update_service`): release lookup tiers, asset selection, verified download, staged apply. Highest risk, best tested today.
3. Platform layer: Steam discovery, depot/manifest, process management.
4. Game/Geode/mod/save/texture/audio services out of `GDManager` (63 methods, grouped by domain).
5. Diagnostics: `explain_error_text`, `scan_installation_issues`, health check as `Result` objects.
6. UI shell on top of the services. Keep Tk for the first v3 release (proven on all three OSes in CI); evaluate a Qt or web-view UI only after the core is stable.
7. Delete `GeodeSync.pyw`, retire `GDManager`, cut v3.0.0.

## 5. Risks and how v3 handles them

| Risk | Mitigation |
|---|---|
| Regression in Steam depot switching, which can damage an install | Port the journal/rollback code unchanged; add a temp-dir fake-depot test suite before touching it |
| Windows/Linux/macOS behaviour differs and CI can't run a real Steam | Keep every OS call behind `platform/` adapters with fakes; real-machine smoke checklist per release |
| UI rewrite breaks Linux Tk (it did in v2.3.x) | Reuse one Tk grid for category switching; no stacked pages; CI launch check stays |
| Scope | v3.0 = same features, solid foundation, better dashboard; new features only after parity |

## 6. Status of this branch (`v3-rewrite`)

Done:
- Step 1: four core modules (`versioning`, `save_codec`, `integrity`, `archive_safety`) with parity tests.
- Step 2: the self-update engine (22 functions + size caps) moved verbatim to `geodesync/services/app_update.py`; the silent-process helpers now come from `geodesync/platform/process_manager.py` (which gained `is_win_process_running`). `main.py` re-exports both, so it shrank from 11,937 to ~11,290 lines with no behaviour change. `tests/test_v3_update_engine.py` pins one implementation (identity checks), constant parity with `geodesync.core.config`, and that the engine imports with Tk blocked.
- Step 7 (partial): `GeodeSync.pyw` is now a 14-line launcher that runs `main.py`, ending the hand-synced byte-identical copy.
- Verified: 175 tests pass; a PyInstaller arm64 macOS build bundles `geodesync.services.app_update` and launches.

- Step 3 (partial): Steam/macOS app helpers moved to `geodesync/platform/steam.py` and the transactional installer (journal, rollback, crash recovery) to `geodesync/services/install_transaction.py`; main re-exports both; 181 tests pass.

- Step 5: diagnostics (`explain_error_text`, `scan_installation_issues`, PE/image checks, disk/VC++/OneDrive checks) moved to `geodesync/services/diagnostics.py`; no Tk imports; 185 tests pass.

Not done: the GDManager split into game/Geode/mod/save services (step 4) and the UI shell (step 6) (Steam/depot platform layer, GDManager services, diagnostics, UI shell) and the remaining half of step 7. `geodesync/services/update_service.py` is an older parallel rewrite still used by `test_phoenix_services.py`; it should become a thin wrapper over `app_update` or be deleted. No release, tag or push has been made.

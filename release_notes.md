# GeodeSync v1.1.5.2 — macOS depot and downgrade hotfix

## macOS depot repair

- Resolve Steam's macOS console-download depot from the Steam.AppBundle location first, so a stale outer-folder cache cannot hide the depot Steam actually writes.
- Reuse a cached Mac game bundle only when its metadata and executable validate.
- Treat Steam's “depot download complete” log as a signal only; GeodeSync now installs only after the downloaded app bundle validates. If validation still fails, it leaves the installed game untouched and shows a recovery message.
- Catch malformed `Info.plist` XML and report it as an invalid bundle.

## Earlier fixes included

- Prevent overlapping downgrade clicks and replace the Mac game app transactionally with rollback.
- Stop Restore to Latest GD if Steam's manifest cannot be safely unlocked; verify manifest lock and unlock operations.
- Monitor Steam launches and distinguish request accepted from the game process actually starting.
- Compare numeric GeodeSync versions and refuse to offer or install older releases.
- Verify Mac updater architecture, bundle structure, and SHA-256 before replacement.

## Builds

- GitHub Actions builds and tests Windows, Apple silicon, and Intel Mac packages. Mac app builds include Python, Tcl, and Tk.
- Unsigned community builds may require Control-click → Open once in macOS.

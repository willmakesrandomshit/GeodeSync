# GeodeSync v3.0.1 — Workspace redesign and texture recovery

GeodeSync 3.0.1 brings the v3 desktop redesign to users and makes common texture problems easier to diagnose safely.

## What changed
- A persistent workspace sidebar keeps Overview, Mods, Library, and Tools & repair available from every section.
- Each section has clearer page context and repair tools are easier to find.
- Texture diagnostics identify missing or invalid Geometry Dash texture resources and route directly to the relevant tools.
- Texture restore now checks that the game is closed and validates the backup images before writing.
- Switching between compatibility routes no longer hides the active view.

## Verification
The release candidate passed 200 pytest tests and 340 subtests locally. Windows, Linux, macOS Intel, and Apple Silicon CI builds and regression tests passed for the v3 redesign.

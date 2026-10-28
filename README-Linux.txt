GeodeSync for Linux and Steam Deck (Desktop Mode)
=================================================

Download the GeodeSync Linux archive from the official GitHub Releases page.
Extract the whole archive into a folder your user can write to. Do not run the
app from inside the archive preview.

Start it from the extracted folder:

    ./run.sh

If your file manager blocks the launcher, open a terminal in the folder and
run `chmod +x run.sh && ./run.sh`. The package includes the application runtime;
you do not need to install Python or Tkinter separately.

What Linux support means
------------------------

Geometry Dash does not provide a native Linux build. GeodeSync manages Steam's
Windows Geometry Dash files as they are run through Proton. Steam and the game
must be installed through Steam. On Steam Deck, switch to Desktop Mode before
using the graphical app.

GeodeSync checks common native and Flatpak Steam locations and Steam library
folders. If your library is elsewhere, use Browse GD Folder and select the
Steam folder containing `GeometryDash.exe`. The save location is the Proton
prefix for the Steam library that contains the game.

Troubleshooting
---------------

* If the app does not open, start it with `./run.sh` in a terminal and copy the
  exact error into the GeodeSync support channel.
* If the game is not detected, use Steam → Geometry Dash → Properties →
  Installed Files → Browse, then select that folder in GeodeSync.
* If Steam cannot download a depot, sign into Steam, open its Console, and
  retry only after Steam has finished updating the game.
* Keep the complete extracted folder together so the bundled runtime remains
  beside the GeodeSync executable.

Official releases: https://github.com/willmakesrandomshit/GeodeSync/releases

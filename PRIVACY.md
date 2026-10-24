# Privacy and local data

GeodeSync does not require a GeodeSync account. The current desktop application
does not intentionally collect or upload Geometry Dash saves, Steam credentials,
Steam cookies, or account tokens.

## Local access

Depending on the feature used, the app reads the Geometry Dash installation,
selected Geode mod metadata, and local Geometry Dash save files. Save tools parse
the game's encoded save format locally. Backup, restore, game switching, mod
management, and texture operations can write to the selected Geometry Dash
folders. Settings, logs, crash reports, backups, and profiles are stored locally
in the operating system's application-support/configuration locations.

## Network destinations

The application contacts these services for the listed purposes:

* `api.github.com` and `github.com`: GeodeSync and Geode release/version metadata
  and user-selected downloads.
* `raw.githubusercontent.com`: the GeodeSync version manifest and Discord Rich
  Presence artwork.
* `api.geode-sdk.org`: Geode mod metadata and user-selected mod downloads.
* Discord's local IPC socket or named pipe: optional Rich Presence sent to a
  Discord desktop client running on the same computer. It is not a webhook.
* Steam client: launched with explicit Steam command-line arguments for a
  user-requested game depot operation. GeodeSync does not read Steam credentials.

The optional standalone `steam_watchdog.py` can POST update notices to a Discord
webhook URL supplied in `GEODESYNC_DISCORD_WEBHOOK`. The webhook receives only the
configured alert title, release description/link, timestamp, and embed formatting.
Treat webhook URLs as secrets; the watchdog does not need one to run.

Network access is not limited to these hosts at the operating-system level. The
list describes endpoints found in the current source and should be updated when
network features change.

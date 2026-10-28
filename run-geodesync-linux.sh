#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP="$APP_DIR/GeodeSync"

if [[ ! -f "$APP" ]]; then
  echo "GeodeSync executable is missing from: $APP_DIR" >&2
  echo "Extract the complete Linux archive, then run this launcher again." >&2
  exit 1
fi

if [[ ! -x "$APP" ]]; then
  chmod u+x "$APP" || {
    echo "GeodeSync could not mark its executable as runnable. Check folder permissions." >&2
    exit 1
  }
fi

if [[ -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
  echo "A graphical desktop session is required. On Steam Deck, switch to Desktop Mode." >&2
  exit 1
fi

cd "$APP_DIR"
exec "$APP" "$@"

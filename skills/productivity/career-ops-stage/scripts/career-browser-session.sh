#!/usr/bin/env bash
set -eu

PROFILE_DIR="${CAREER_BROWSER_PROFILE_DIR:-$HOME/.local/share/hermes/career-ops/chrome-profile}"
CHROME_BIN="${CAREER_BROWSER_CHROME_BIN:-/opt/google/chrome/chrome}"
DEBUG_PORT=9333

prepare_profile() {
  mkdir -p "$PROFILE_DIR"
  chmod 700 "$PROFILE_DIR"
  printf '%s\n' "$PROFILE_DIR"
}

port_is_listening() {
  ss -H -ltn "sport = :$DEBUG_PORT" 2>/dev/null | grep -q .
}

case "${1:-launch}" in
  profile-path)
    printf '%s\n' "$PROFILE_DIR"
    ;;
  prepare)
    prepare_profile
    ;;
  launch)
    prepare_profile >/dev/null
    if [ ! -x "$CHROME_BIN" ]; then
      printf 'career browser: Chrome is not executable: %s\n' "$CHROME_BIN" >&2
      exit 1
    fi
    if port_is_listening; then
      printf 'career browser: loopback CDP port %s is already in use; refusing an ambiguous attachment\n' "$DEBUG_PORT" >&2
      exit 2
    fi
    exec env -u WAYLAND_DISPLAY "$CHROME_BIN" \
      "--user-data-dir=$PROFILE_DIR" \
      --remote-debugging-address=127.0.0.1 \
      --remote-debugging-port=9333 \
      --force-renderer-accessibility \
      --ozone-platform=x11 \
      --window-size=1200,900 \
      --no-first-run \
      --no-default-browser-check \
      about:blank
    ;;
  *)
    printf 'usage: %s [prepare|profile-path|launch]\n' "$0" >&2
    exit 64
    ;;
esac

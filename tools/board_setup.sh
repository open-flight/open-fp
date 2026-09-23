#!/usr/bin/env bash
# One-time: install SSH key, sanity-check the board.
set -euo pipefail
HOST="${1:-open-fp.local}"
PUBKEY="${PUBKEY:-$HOME/.ssh/id_ed25519.pub}"
# Install the public key directly rather than via ssh-copy-id, which requires the private
# key on disk and fails when it lives in an agent (e.g. 1Password). Idempotent.
KEY="$(cat "${PUBKEY}")"
ssh "arduino@${HOST}" "mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys \
  && chmod 600 ~/.ssh/authorized_keys \
  && (grep -qxF '${KEY}' ~/.ssh/authorized_keys || echo '${KEY}' >> ~/.ssh/authorized_keys)"
ssh "arduino@${HOST}" '
  set -e
  uname -a
  which arduino-app-cli && arduino-app-cli --help | head -20
  systemctl status arduino-router --no-pager | head -5 || true
  mkdir -p ~/ArduinoApps
'

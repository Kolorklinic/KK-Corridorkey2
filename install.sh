#!/bin/bash
# ---------------------------------------------------------------------------
# CorridorKey 2 for Resolve - install the built plugin (asks for your password)
# From Creative Video Tips (CVT)  |  https://creativevideotips.com
# Licence: CC BY-NC-SA 4.0 with the CorridorKey additional terms (see LICENSE).
# Quit Resolve and Fusion Studio first.
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"
B=build/CorridorKey2.ofx.bundle
[ -d "$B" ] || { echo "Build it first: ./build.sh"; exit 1; }
if pgrep -xq "Resolve" || pgrep -xq "Fusion"; then
    echo "Quit DaVinci Resolve and Fusion Studio first."; exit 1
fi
sudo mkdir -p /Library/OFX/Plugins
sudo rm -rf /Library/OFX/Plugins/CorridorKey2.ofx.bundle
sudo cp -R "$B" /Library/OFX/Plugins/
echo "Installed CorridorKey 2 for Resolve $(defaults read "$PWD/$B/Contents/Info" CFBundleShortVersionString)."
echo "In Fusion: Effects > OpenFX > Creative Video Tips > CorridorKey 2."

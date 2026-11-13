#!/bin/bash
# CorridorKey 2 for Resolve - opens in Terminal from the node's Setup > Install Model.
# From Creative Video Tips (CVT)  |  https://creativevideotips.com
# Licence: CC BY-NC-SA 4.0 with the CorridorKey additional terms (see LICENSE).
clear
bash "$(dirname "$0")/ck2_setup.sh" "$@"
echo
read -n 1 -s -r -p "Press any key to close this window."

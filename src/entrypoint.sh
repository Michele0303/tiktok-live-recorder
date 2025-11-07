#!/bin/bash
set -e

# Check if SESSIONID_SS is set and not empty
if [[ -n "$SESSIONID_SS" ]]; then
  # Set TT_TARGET_IDC to default if not provided
  TT_TARGET_IDC_VALUE=${TT_TARGET_IDC:-useast2a}

  # Create cookies.json
  cat <<EOF > cookies.json
{
  "sessionid_ss": "$SESSIONID_SS",
  "tt-target-idc": "$TT_TARGET_IDC_VALUE"
}
EOF
fi

# Execute main.py with all passed arguments
exec python3 main.py -no-update-check "$@"

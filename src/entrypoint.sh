#!/bin/bash
set -e

# Create cookies.json only if SESSIONID_SS is set
if [[ -n "${SESSIONID_SS}" ]]; then
  cat <<EOF > /app/src/cookies.json
{
  "sessionid_ss": "${SESSIONID_SS}",
  "tt-target-idc": "useast2a"
}
EOF
fi

# Execute main.py with all passed arguments
# TODO: Skip update checks
#exec python3 main.py -no-update-check "$@"
exec python3 main.py "$@"

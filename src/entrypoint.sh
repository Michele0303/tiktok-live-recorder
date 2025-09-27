#!/bin/bash
set -e

# Execute main.py with all passed arguments
exec python3 main.py -no-update-check "$@"

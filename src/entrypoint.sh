#!/bin/bash
set -e

# If arguments are passed, forward to CLI mode (main.py)
if [ "$#" -gt 0 ]; then
    exec /app/.venv/bin/python main.py -no-update-check "$@"
else
    # Default: execute Telegram Watch Service mode (bot_main.py)
    exec /app/.venv/bin/python bot_main.py
fi

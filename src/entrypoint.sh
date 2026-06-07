#!/bin/bash
set -e

# Execute main.py with the prebuilt virtual environment.
exec /app/.venv/bin/python main.py -no-update-check "$@"

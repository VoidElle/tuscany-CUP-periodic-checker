#!/usr/bin/env bash
# Run the CUP checker from any directory, preferring the project venv.
set -euo pipefail
cd "$(dirname "$0")"
PYTHON=.venv/bin/python
[ -x "$PYTHON" ] || PYTHON=python3
exec "$PYTHON" main.py "$@"

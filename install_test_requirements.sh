#!/usr/bin/env bash
# Install dependencies required for running the test suite. Accepts an optional
# profile argument (``core`` or ``ai``) to control which extras to install.
set -euo pipefail

PROFILE="${1:-ai}"

python3 -m pip install --upgrade pip

case "$PROFILE" in
  core)
    pip install -e .[dev]
    ;;
  ai)
    export PIP_EXTRA_INDEX_URL="https://download.pytorch.org/whl/cpu"
    pip install -e .[dev,ai]
    ;;
  *)
    echo "Unknown profile: $PROFILE" >&2
    exit 1
    ;;
esac

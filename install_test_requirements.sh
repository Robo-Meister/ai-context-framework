#!/usr/bin/env bash
# Install dependencies required for running the full test suite, including tests that
# rely on optional PyTorch components.
set -e
python3 -m pip install --upgrade pip
export PIP_EXTRA_INDEX_URL="https://download.pytorch.org/whl/cpu"
pip install -r requirements.txt
pip install -e .

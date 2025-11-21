#!/bin/bash
# Generate requirements.lock.txt with hashes for STRICT=1 Docker builds

set -euo pipefail

echo "Refreshing requirements.lock.txt with hashes..."

# Create temporary virtual environment
TEMP_VENV=$(mktemp -d)
python -m venv "$TEMP_VENV"
source "$TEMP_VENV/bin/activate"

# Upgrade pip and install pip-tools
pip install --upgrade pip pip-tools

# Generate locked requirements with hashes
pip-compile --generate-hashes --output-file requirements.lock.txt requirements.in

# Clean up
deactivate
rm -rf "$TEMP_VENV"

echo "requirements.lock.txt updated with hashes"

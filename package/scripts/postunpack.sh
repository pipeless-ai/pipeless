#!/bin/bash

set -o errexit
set -o nounset
set -o pipefail
# set -o xtrace # Uncomment this line for debugging purposes

REQUIRED_DIRS=(
    "/.app"
    "/.cargo"
    "/.rustup"
    "/.pipeless"
    # Allow python to install packages as nonroot
    "/.local"
    "/.cache"
    # Some common Python packages like Matplotlib try to write into .config
    "/.config"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    mkdir -p "$dir"
    chmod g+rwX "$dir"
done

# Required to be modified by cargo
touch "/.profile"
chmod g+rwX "/.profile"

# Setup Python virtual environment
python3 -m venv "/.venv"
chmod -R g+rwX "/.venv"

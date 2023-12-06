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
    # Create a folder to store the Python virtual environment. Created at runtime
    # to allow the user mount a volume and avoid packages installation on every
    # start
    "/.venv"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    mkdir -p "$dir"
    chmod g+rwX "$dir"
done

# Required to be modified by cargo
touch "/.profile"
chmod g+rwX "/.profile"

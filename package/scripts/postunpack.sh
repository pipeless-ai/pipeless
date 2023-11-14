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
)

for dir in "${REQUIRED_DIRS[@]}"; do
    mkdir -p "$dir"
    chmod g+rwX "$dir"
done

# Required to be modified by cargo
touch "/.profile"
chmod g+rwX "/.profile"
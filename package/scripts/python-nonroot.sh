#!/bin/bash

set -o errexit
set -o nounset
set -o pipefail
# set -o xtrace # Uncomment this line for debugging purposes

dirs=(
    # Allow python to install packages as nonroot
    "/.local"
    "/.cache"
)
for dir in "${dirs[@]}"; do
    mkdir -p "$dir"
    chmod -R g+w "$dir"
done


#!/bin/bash

dirs=(
    # Allow python to install packages as nonroot
    "/.local"
    "/.cache"
)
for dir in "${dirs[@]}"; do
    mkdir -p "$dir"
    chmod -R g+w "$dir"
done


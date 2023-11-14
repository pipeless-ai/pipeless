#!/bin/bash

set -o errexit
set -o nounset
set -o pipefail
# set -o xtrace # Uncomment this line for debugging purposes

cargo_install() {
    wget -O /tmp/rustup-init.sh https://sh.rustup.rs
    chmod +x /tmp/rustup-init.sh
    /tmp/rustup-init.sh -y
}

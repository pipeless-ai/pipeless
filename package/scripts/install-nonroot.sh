#!/bin/bash

set -o errexit
set -o nounset
set -o pipefail
set -o xtrace # Uncomment this line for debugging purposes

. /scripts/libpipeless.sh
. /scripts/libcargo.sh

cargo_install

. "$HOME/.cargo/env"

pipeless_install

#!/bin/bash

set -o errexit
set -o nounset
set -o pipefail
# set -o xtrace # Uncomment this line for debugging purposes

. /scripts/libpipeless.sh

command="${1:-}"

# Activate Python venv
. "/.venv/bin/activate"

if [[ "$command" = "start" ]]; then
    pipeless_install_user_python_deps
fi

if [[ "$command" = "pipeless" ]]; then
    exec "$@"
else
    exec pipeless "$@"
fi

#!/bin/bash

set -o errexit
set -o nounset
set -o pipefail
# set -o xtrace # Uncomment this line for debugging purposes

. /libpipeless.sh

command="${1:-}"

if [[ "$command" = "run" && ( "${2:-}" = "worker" || "${2:-}" = "all" ) ]]; then
    pipeless_install_user_python_deps
fi

if [[ "$command" = "pipeless" ]]; then
    exec "$@"
else
    exec pipeless "$@"
fi

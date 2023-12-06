#!/bin/bash

set -o errexit
set -o nounset
set -o pipefail
# set -o xtrace # Uncomment this line for debugging purposes

. /scripts/libpipeless.sh

command="${1:-}"

# Setup Python virtual environment
# the user can mount a volume at /.venv and avoid the installation of the Python packages on every start
echo "Creating Python virtual env..."
python3 -m venv "/.venv"
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

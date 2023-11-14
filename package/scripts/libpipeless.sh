#!/bin/bash

set -o errexit
set -o nounset
set -o pipefail
# set -o xtrace # Uncomment this line for debugging purposes

########################
# Install Python dependencies required by the user code to run the worker
# Globals:
#   PIPELESS_*
# Arguments:
#   None
# Returns:
#   None
#########################
pipeless_install_user_python_deps() {
    [[ -z "${PIPELESS_USER_PYTHON_PACKAGES:-}" ]] && return

    local -a package_list
    read -r -a package_list <<< "$(tr ',;' ' ' <<< "${PIPELESS_USER_PYTHON_PACKAGES}")"
    if [[ "${#package_list[@]}" -le 0 ]]; then
        echo "No python packages specified by the user"
        return
    fi

    for package in "${package_list[@]}"; do
	pip install "$package"
    done
}

########################
# Install system packages required by the user code to run the worker
# These need to be installed at buildtime
# Globals:
#   PIPELESS_*
# Arguments:
#   None
# Returns:
#   None
#########################
pipeless_install_user_system_deps() {
    [[ -z "${PIPELESS_USER_SYSTEM_PACKAGES:-}" ]] && return

    local -a package_list
    read -r -a package_list <<< "$(tr ',;' ' ' <<< "${PIPELESS_USER_SYSTEM_PACKAGES}")"
    if [[ "${#package_list[@]}" -le 0 ]]; then
        echo "No system packages specified by the user"
        return
    fi

    for package in "${package_list[@]}"; do
	apt-get install "$package"
    done
}

########################
# Install pipeless
# These need to be installed at buildtime
# Globals:
#   PIPELESS_*
# Arguments:
#   None
# Returns:
#   None
#########################
pipeless_install() {
    (
        cd /tmp
        wget https://raw.githubusercontent.com/pipeless-ai/pipeless/main/install.sh
        chmod +x install.sh
        bash install.sh --build
    )
    # Cleanup
    rm -rf /tmp/*
    rm -rf /.rustup/*
    rm -rf /.cargo/*
}

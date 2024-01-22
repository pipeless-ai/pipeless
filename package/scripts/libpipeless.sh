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
# Globals:
#   PIPELESS_*
# Arguments:
#   None
# Returns:
#   None
#########################
pipeless_install() {
    ARCH=$(uname -m)
    if [[ "$ARCH" == "aarch64"  ]]; then
        pipeless_download_onnxruntime_arm
        # The cargo build command in the install script will use these to locate the onnxruntime library
        export ORT_STRATEGY="system"
        export ORT_LIB_LOCATION="${HOME}/.pipeless/"
    fi

    (
        cd /tmp
        wget https://raw.githubusercontent.com/pipeless-ai/pipeless/main/install.sh
        chmod +x install.sh
        # Build Pipeless to ensure it links to the Python version of the image
        bash install.sh --build
    )
    # Cleanup
    rm -f /tmp/rustup-init.sh /tmp/install.sh
    rm -rf /.rustup/*
    rm -rf /.cargo/*
}

########################
# Download onnxruntime libraries for arm from our own S3 bucket since microsoft does not provide gpu flavors for arm
# Globals:
#   PIPELESS_*
# Arguments:
#   None
# Returns:
#   None
#########################
pipeless_download_onnxruntime_arm() {
    local -r os_arch="linux-arm64"
    local -r version="1.16.3"
    wget -P "${HOME}/.pipeless" "https://pipeless-public.s3.eu-west-3.amazonaws.com/onnxruntime/${os_arch}/${version}/libonnxruntime.so.1.16.3"
    wget -P "${HOME}/.pipeless" "https://pipeless-public.s3.eu-west-3.amazonaws.com/onnxruntime/${os_arch}/${version}/libonnxruntime_providers_cuda.so"
    wget -P "${HOME}/.pipeless" "https://pipeless-public.s3.eu-west-3.amazonaws.com/onnxruntime/${os_arch}/${version}/libonnxruntime_providers_shared.so"
    wget -P "${HOME}/.pipeless" "https://pipeless-public.s3.eu-west-3.amazonaws.com/onnxruntime/${os_arch}/${version}/libonnxruntime_providers_tensorrt.so"
    wget -P "${HOME}/.pipeless" "https://pipeless-public.s3.eu-west-3.amazonaws.com/onnxruntime/${os_arch}/${version}/libonnxruntime.so"
}

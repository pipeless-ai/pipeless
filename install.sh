#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail
# set -o xtrace # Uncomment this line for debugging purposes

: ${BINARY_NAME:="pipeless"}
: ${FORCE_BUILD:="false"}
: ${DEBUG:="false"}
: ${VERIFY_CHECKSUM:="true"}
: ${VERIFY_SIGNATURES:="false"}
: ${PIPELESS_INSTALL_DIR:="${HOME}/.pipeless"}
: ${PIPELESS_LIB_INSTALL_DIR:="${HOME}/.pipeless"}
: ${GPG_PUBRING:="pubring.kbx"}

HAS_CURL="$(type "curl" &> /dev/null && echo true || echo false)"
HAS_WGET="$(type "wget" &> /dev/null && echo true || echo false)"
HAS_OPENSSL="$(type "openssl" &> /dev/null && echo true || echo false)"
HAS_GPG="$(type "gpg" &> /dev/null && echo true || echo false)"
HAS_GIT="$(type "git" &> /dev/null && echo true || echo false)"
HAS_CARGO="$(type "cargo" &> /dev/null && echo true || echo false)"
HAS_GSTREAMER="$(type "gst-launch-1.0" &> /dev/null && echo true || echo false)"
HAS_PYTHON="$(type "python3" &> /dev/null && echo true || echo false)"
HAS_PKG_CONFIG="$(type "pkg-config" &> /dev/null && echo true || echo false)"
HAS_UUIDGEN="$(type "uuidgen" &> /dev/null && echo true || echo false)"

# initArch discovers the architecture for this system.
initArch() {
  ARCH=$(uname -m)
  case $ARCH in
    armv5*) ARCH="armv5";;
    armv6*) ARCH="armv6";;
    armv7*) ARCH="arm";;
    aarch64) ARCH="arm64";;
    x86) ARCH="386";;
    x86_64) ARCH="amd64";;
    i686) ARCH="386";;
    i386) ARCH="386";;
  esac
}

# initOS discovers the operating system for this system.
initOS() {
  OS=$(echo `uname`|tr '[:upper:]' '[:lower:]')

  case "$OS" in
    # Minimalist GNU for Windows
    mingw*|cygwin*) OS='windows';;
  esac
}

# Create a uuid
create_device_id() {
  if [ "$HAS_UUIDGEN" != "true" ]; then
    return
  fi
  if [ ! -f "${PIPELESS_INSTALL_DIR}/device_id" ]; then
    mkdir -p "$PIPELESS_INSTALL_DIR"
    device_id="$(uuidgen | tr "[:upper:]" "[:lower:]")"
    echo "$device_id" > "${PIPELESS_INSTALL_DIR}/device_id"
  fi
}

setupPipelessEnv() {
  echo -e "\n\n"
  echo "✅ Pipeless installed successfully!"
  echo ""
  echo "Execute the following commands to load the Pipeless binary:"
  echo ""
  echo '    export PATH="${PATH}:${HOME}/.pipeless"'
  if [[ "$OS" == "darwin" ]]; then
    # In macOS we have to use the rpath instead of the library path
    install_name_tool -add_rpath @executable_path "${PIPELESS_INSTALL_DIR}/pipeless"
  else
    echo '    export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:${HOME}/.pipeless"'
  fi

  echo ""
  echo "💡 To automatically load the Pipeless binary in new sessions copy and paste the above commands into your shell configuration file. (~/.bashrc, ~/.zshrc, etc.)"
}

# create a totally anonymous report so we can know the most used OS and archs and if there are errors
create_report() {
  if [ "$HAS_UUIDGEN" != "true" ]; then
    return
  fi

  local -r device_id="$(cat "${PIPELESS_INSTALL_DIR}/device_id")"
  local -r status="${1:?missing status}"
  local -r msg="${2:-}"
  local -r report_url="https://www.pipeless.ai/api/install"
  payload="{ \"device_id\": \"$device_id\", \"os\": \"$OS\", \"arch\": \"$ARCH\", \"status\": \"$status\", \"message\": \"$msg\" }"
  if [ "${HAS_CURL}" == "true" ]; then
    curl -s -X POST -d "$payload" "$report_url" > /dev/null
  elif [ "${HAS_WGET}" == "true" ]; then
    wget -q --header="Content-Type: application/json" --post-data "$payload" "$report_url" > /dev/null
  fi
}

# verifySupported checks that the os/arch combination is supported for
# binary builds, as well whether or not necessary tools are present.
verifySupported() {
  if [ "${FORCE_BUILD}" == "true" ]; then
    echo "Force build is enabled, about to build Pipeless from source."
    return 1
  fi

  local supported="darwin-amd64\nlinux-amd64"
  if ! echo "${supported}" | grep -q "${OS}-${ARCH}"; then
    return 1
  fi

  if [ "${HAS_CURL}" != "true" ] && [ "${HAS_WGET}" != "true" ]; then
    echo "Either curl or wget is required"
    create_report "error" "Missing curl and wget" || true
    exit 1
  fi

  if [ "${VERIFY_CHECKSUM}" == "true" ] && [ "${HAS_OPENSSL}" != "true" ]; then
    echo "In order to verify checksum, openssl must first be installed."
    echo "Please install openssl or set VERIFY_CHECKSUM=false in your environment."
    create_report "error" "Missing openssl" || true
    exit 1
  fi

  if [ "${VERIFY_SIGNATURES}" == "true" ]; then
    if [ "${HAS_GPG}" != "true" ]; then
      echo "In order to verify signatures, gpg must first be installed."
      echo "Please install gpg or set VERIFY_SIGNATURES=false in your environment."
      create_report "error" "Missing gpg" || true
      exit 1
    fi
    if [ "${OS}" != "linux" ]; then
      echo "Signature verification is currently only supported on Linux."
      echo "Please set VERIFY_SIGNATURES=false or verify the signatures manually."
      create_report "error" "Verify signature enabled on non-linux device" || true
      exit 1
    fi
  fi

  return 0
}

# Build Pipeless from source
buildPipeless() {
  echo "No prebuilt binary for ${OS}-${ARCH}. Trying to build from source."
  if [ "${HAS_CARGO}" != "true" ]; then
    echo "In order to build pipeless for ${OS}-${ARCH} cargo must first be installed"
    echo "Please install cargo and run this script again."
    echo "You can install cargo with:"
    echo "  $ curl https://sh.rustup.rs -sSf | sh"
    create_report "error" "Missing cargo" || true
    exit 1
  fi

  if [ "${HAS_GIT}" != "true" ]; then
    echo "In order to build pipeless for ${OS}-${ARCH} git must first be installed"
    echo "Please install git and run this script again."
    echo "You can install git with:"
    if [[ "$OS" == "darwin" ]]; then
      echo "  $ brew install git"
    else
      echo "  $ sudo apt-get install git"
    fi
    create_report "error" "Missing git" || true
    exit 1
  fi

  if [ "${HAS_PKG_CONFIG}" != "true" ]; then
    echo "In order to build pipeless for ${OS}-${ARCH} pkg-config must first be installed"
    echo "Please install pkg-config and run this script again."
    echo "You can install pkg-config with:"
    if [[ "$OS" == "darwin" ]]; then
      echo "  $ brew install pkg-config"
    else
      echo "  $ sudo apt-get install pkg-config"
    fi
    create_report "error" "Missing pkg-config" || true
    exit 1
  fi

  BUILD_TMP_DIR="$(mktemp -d)"
  mkdir -p "$PIPELESS_INSTALL_DIR"
  echo "Cloning Pipeless repo into ${BUILD_TMP_DIR}"
  git clone https://github.com/pipeless-ai/pipeless.git "$BUILD_TMP_DIR"
  (
    cd "$BUILD_TMP_DIR"

    echo "Building pipeless for ${OS}-${ARCH} via cargo..."
    cargo build --all --release --manifest-path pipeless/Cargo.toml
    echo "Pipeless was properly built"

    mv pipeless/target/release/pipeless-ai pipeless/target/release/pipeless
    strip pipeless/target/release/pipeless
    mv pipeless/target/release/{pipeless,libonnxruntime*} "${PIPELESS_INSTALL_DIR}/"
  )

  # handle the above subshell failure
  if [ $? -ne 0 ]; then
    echo "❌ There was an error building Pipeless"
    echo ""
    echo "If the error is related to libonnxruntime not being found it is possible that Microsoft does not provide a pre-built onnx runtime for your target platform."
    echo "Please the following guide to install both Pipeless and ONNX Runtime from source: https://www.pipeless.ai/docs/v1/getting-started/installation#building-onnx-runtime-from-source"
    echo "If you need further help please contact us via a GitHub issue or our Discord server"

    create_report "error" "Error building from source" || true
    exit 1
  fi

}

checkGstreamer() {
  if [ "${HAS_GSTREAMER}" != "true" ]; then
    echo "GStreamer is not installed. Pipeless requires GStreamer to work"
    echo "Please install GStreamer before continuing. You can install GStreamer with:"
    if [ "${OS}" == "linux" ]; then
      echo "sudo apt-get install libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
libgstreamer-plugins-bad1.0-dev gstreamer1.0-plugins-base \
gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-tools \
gstreamer1.0-x gstreamer1.0-alsa gstreamer1.0-gl gstreamer1.0-gtk3 \
gstreamer1.0-qt5 gstreamer1.0-pulseaudio gstreamer1.0-rtsp"
    elif [ "${OS}" == "darwin" ]; then
      echo "brew install gstreamer"
    fi
    create_report "error" "Missing Gstreamer" || true
    exit 1
  fi
}

# verifyDependencies ensures the user has the required dependencies to run Pipeless.
verifyDependencies() {
  if [ "${HAS_PYTHON}" != "true" ]; then
    echo "Python is not installed."
    echo "Please install Python before continuing. You can install python with:"
    if [ "${OS}" == "linux" ]; then
      echo "sudo apt-get install python3-dev python3-pip"
      echo ""
      echo "Note pre-built binaries are linked to Python 3.10. If you install a different Python version provide the --build flag to this script"
    elif [ "${OS}" == "darwin" ]; then
      echo "brew install python"
      echo ""
      echo "Note pre-built binaries are linked to Python 3.12. If you install a different Python version provide the --build flag to this script"
    fi
    create_report "error" "Missing Python" || true
    exit 1
  fi

  checkGstreamer
}

# checkDesiredVersion checks if the desired version is available.
checkDesiredVersion() {
  if [ "x${DESIRED_VERSION:-}" == "x" ]; then
    # Get tag from release URL
    local latest_release_url="https://api.github.com/repos/pipeless-ai/pipeless/releases/latest"
    local latest_release_response=""
    if [ "${HAS_CURL}" == "true" ]; then
      latest_release_response=$( curl -L --silent --show-error --fail "$latest_release_url" 2>&1 || true )
    elif [ "${HAS_WGET}" == "true" ]; then
      latest_release_response=$( wget "$latest_release_url" -q -O - 2>&1 || true )
    fi
    TAG=$( echo "$latest_release_response" | grep -o '"tag_name": "v[0-9]\+\(\.[0-9]\+\)*"' | grep -o '[0-9]\+\(\.[0-9]\+\)*' )
    if [ "x$TAG" == "x" ]; then
      printf "Could not retrieve the latest release tag information from %s: %s\n" "${latest_release_url}" "${latest_release_response}"
      create_report "error" "Unable to get latest release tag info" || true
      exit 1
    fi
  else
    TAG=$DESIRED_VERSION
  fi
}

# checkPipelessInstalledVersion checks which version of pipeless is installed and
# if it needs to be changed.
checkPipelessInstalledVersion() {
  if [[ -f "${PIPELESS_INSTALL_DIR}/${BINARY_NAME}" ]]; then
    local version=$("${PIPELESS_INSTALL_DIR}/${BINARY_NAME}" --version | grep -o '[0-9]\+\(\.[0-9]\+\)*')
    if [[ "$version" == "$TAG" ]]; then
      echo "Pipeless ${version} is already ${DESIRED_VERSION:-latest}"
      return 0
    else
      echo "Pipeless ${TAG} is available. Changing from version ${version}."
      return 1
    fi
  else
    return 1
  fi
}

# downloadFile downloads the latest binary package and also the checksum
# for that binary.
downloadFile() {
  PIPELESS_DIST="pipeless-$TAG-$OS-$ARCH.tar.gz"
  DOWNLOAD_URL="https://github.com/pipeless-ai/pipeless/releases/download/v${TAG}/${PIPELESS_DIST}"
  CHECKSUM_URL="${DOWNLOAD_URL}.sha256"
  PIPELESS_TMP_ROOT="$(mktemp -dt pipeless-installer-XXXXXX)"
  PIPELESS_TMP_FILE="${PIPELESS_TMP_ROOT}/${PIPELESS_DIST}"
  PIPELESS_SUM_FILE="${PIPELESS_TMP_ROOT}/${PIPELESS_DIST}.sha256"
  echo "Downloading $DOWNLOAD_URL"
  if [ "${HAS_CURL}" == "true" ]; then
    curl -SsL "$CHECKSUM_URL" -o "$PIPELESS_SUM_FILE"
    curl -SsL "$DOWNLOAD_URL" -o "$PIPELESS_TMP_FILE"
  elif [ "${HAS_WGET}" == "true" ]; then
    wget -q -O "$PIPELESS_SUM_FILE" "$CHECKSUM_URL"
    wget -q -O "$PIPELESS_TMP_FILE" "$DOWNLOAD_URL"
  fi
}

# verifyFile verifies the SHA256 checksum of the binary package
# and the GPG signatures for both the package and checksum file
# (depending on settings in environment).
verifyFile() {
  if [ "${VERIFY_CHECKSUM}" == "true" ]; then
    verifyChecksum
  fi
  # TODO: uncomment once we sign the releases
  #if [ "${VERIFY_SIGNATURES}" == "true" ]; then
  #  verifySignatures
  #fi
}

# installFile installs the Pipeless binary and libraries.
installFile() {
  PIPELESS_TMP="$PIPELESS_TMP_ROOT"
  mkdir -p "$PIPELESS_TMP"
  tar xf "$PIPELESS_TMP_FILE" -C "$PIPELESS_TMP"
  PIPELESS_TMP_BIN="$PIPELESS_TMP/pipeless-${TAG}/pipeless"
  echo "Preparing to install $BINARY_NAME into ${PIPELESS_INSTALL_DIR}"
  mkdir -p "$PIPELESS_INSTALL_DIR"
  cp "$PIPELESS_TMP_BIN" "$PIPELESS_INSTALL_DIR/$BINARY_NAME"
  echo "$BINARY_NAME installed into $PIPELESS_INSTALL_DIR/$BINARY_NAME"
  echo "Adding inference runtime libraries to ${PIPELESS_LIB_INSTALL_DIR}"
  cp "${PIPELESS_TMP}/pipeless-${TAG}/libonnxruntime"* $PIPELESS_LIB_INSTALL_DIR
}

# verifyChecksum verifies the SHA256 checksum of the binary package.
verifyChecksum() {
  printf "Verifying checksum... "
  # The checksum in the release job used sha256sum which may not be available in macOS, so use openssl to compute it here
  local sum=$(openssl sha1 -sha256 ${PIPELESS_TMP_FILE} | awk '{print $2}')
  local expected_sum=$(cat ${PIPELESS_SUM_FILE} | awk '{print $1}')
  if [ "$sum" != "$expected_sum" ]; then
    echo "SHA sum of ${PIPELESS_TMP_FILE} does not match. Aborting."
    create_report "error" "Invalid checksum" || true
    exit 1
  fi
  echo "Done."
}

# verifySignatures obtains the latest KEYS file from GitHub main branch
# as well as the signature .asc files from the specific GitHub release,
# then verifies that the release artifacts were signed by a maintainer's key.
# TODO: uncomment once we sign the releases
#verifySignatures() {
#  printf "Verifying signatures... "
#  local keys_filename="KEYS"
#  local github_keys_url="https://raw.githubusercontent.com/pipeless-ai/pipeless/main/${keys_filename}"
#  if [ "${HAS_CURL}" == "true" ]; then
#    curl -SsL "${github_keys_url}" -o "${PIPELESS_TMP_ROOT}/${keys_filename}"
#  elif [ "${HAS_WGET}" == "true" ]; then
#    wget -q -O "${PIPELESS_TMP_ROOT}/${keys_filename}" "${github_keys_url}"
#  fi
#  local gpg_keyring="${PIPELESS_TMP_ROOT}/keyring.gpg"
#  local gpg_homedir="${PIPELESS_TMP_ROOT}/gnupg"
#  mkdir -p -m 0700 "${gpg_homedir}"
#  local gpg_stderr_device="/dev/null"
#  if [ "${DEBUG}" == "true" ]; then
#    gpg_stderr_device="/dev/stderr"
#  fi
#  gpg --batch --quiet --homedir="${gpg_homedir}" --import "${PIPELESS_TMP_ROOT}/${keys_filename}" 2> "${gpg_stderr_device}"
#  gpg --batch --no-default-keyring --keyring "${gpg_homedir}/${GPG_PUBRING}" --export > "${gpg_keyring}"
#  local github_release_url="https://github.com/pipeless-ai/pipeless/releases/download/${TAG}"
#  if [ "${HAS_CURL}" == "true" ]; then
#    curl -SsL "${github_release_url}/pipeless-${TAG}-${OS}-${ARCH}.tar.gz.sha256.asc" -o "${PIPELESS_TMP_ROOT}/pipeless-${TAG}-${OS}-${ARCH}.tar.gz.sha256.asc"
#    curl -SsL "${github_release_url}/pipeless-${TAG}-${OS}-${ARCH}.tar.gz.asc" -o "${PIPELESS_TMP_ROOT}/pipeless-${TAG}-${OS}-${ARCH}.tar.gz.asc"
#  elif [ "${HAS_WGET}" == "true" ]; then
#    wget -q -O "${PIPELESS_TMP_ROOT}/pipeless-${TAG}-${OS}-${ARCH}.tar.gz.sha256.asc" "${github_release_url}/pipeless-${TAG}-${OS}-${ARCH}.tar.gz.sha256.asc"
#    wget -q -O "${PIPELESS_TMP_ROOT}/pipeless-${TAG}-${OS}-${ARCH}.tar.gz.asc" "${github_release_url}/pipeless-${TAG}-${OS}-${ARCH}.tar.gz.asc"
#  fi
#  local error_text="If you think this might be a potential security issue,"
#  error_text="${error_text}\nplease see here: https://github.com/pipeless/community/blob/master/SECURITY.md"
#  local num_goodlines_sha=$(gpg --verify --keyring="${gpg_keyring}" --status-fd=1 "${PIPELESS_TMP_ROOT}/pipeless-${TAG}-${OS}-${ARCH}.tar.gz.sha256.asc" 2> "${gpg_stderr_device}" | grep -c -E '^\[GNUPG:\] (GOODSIG|VALIDSIG)')
#  if [[ ${num_goodlines_sha} -lt 2 ]]; then
#    echo "Unable to verify the signature of pipeless-${TAG}-${OS}-${ARCH}.tar.gz.sha256!"
#    echo -e "${error_text}"
#    exit 1
#  fi
#  local num_goodlines_tar=$(gpg --verify --keyring="${gpg_keyring}" --status-fd=1 "${PIPELESS_TMP_ROOT}/pipeless-${TAG}-${OS}-${ARCH}.tar.gz.asc" 2> "${gpg_stderr_device}" | grep -c -E '^\[GNUPG:\] (GOODSIG|VALIDSIG)')
#  if [[ ${num_goodlines_tar} -lt 2 ]]; then
#    echo "Unable to verify the signature of pipeless-${TAG}-${OS}-${ARCH}.tar.gz!"
#    echo -e "${error_text}"
#    exit 1
#  fi
#  echo "Done."
#}

# fail_trap is executed if an error occurs.
fail_trap() {
  result=$?
  if [ "$result" != "0" ]; then
    if [[ -n "$INPUT_ARGUMENTS" ]]; then
      echo "Failed to install $BINARY_NAME with the arguments provided: $INPUT_ARGUMENTS"
      help
    else
      echo "Failed to install $BINARY_NAME"
    fi
    echo -e "\tFor support, tell us the problem at the following link, we will usually reply in a few hours:"
    echo -e "\t\thttps://github.com/pipeless-ai/pipeless/issues/new?assignees=&labels=bug&projects=&template=bug_report.md&title=Installation%20error"
  fi
  cleanup
  exit $result
}

# help provides possible cli installation arguments
help () {
  echo "Accepted cli arguments are:"
  echo -e "\t[--help|-h ] ->> prints this help"
  echo -e "\t[--version|-v <desired_version>] . When not defined it fetches the latest release from GitHub"
  echo -e "\te.g. --version v1.0.0"
  echo -e "\t[--build]  ->> Force the build from source"
}

# cleanup temporary files
cleanup() {
  if [[ -d "${PIPELESS_TMP_ROOT:-}" ]]; then
    rm -rf "$PIPELESS_TMP_ROOT"
  fi
}

# Execution

#Stop execution on any error
trap "fail_trap" EXIT
set -e

# Set debug if desired
if [ "${DEBUG}" == "true" ]; then
  set -x
fi

# Parsing input arguments (if any)
export INPUT_ARGUMENTS="$@"
set -u
while [[ $# -gt 0 ]]; do
  case $1 in
    '--version'|-v)
       shift
       if [[ $# -ne 0 ]]; then
           export DESIRED_VERSION="${1}"
           if [[ "$1" != "v"* ]]; then
               echo "Expected version arg ('${DESIRED_VERSION}') to begin with 'v', fixing..."
               export DESIRED_VERSION="v${1}"
           fi
       else
           echo -e "Please provide the desired version. e.g. --version v3.0.0 or -v canary"
           exit 0
       fi
       ;;
    '--build')
       FORCE_BUILD="true"
       ;;

    '--help'|-h)
       help
       exit 0
       ;;
    *) exit 1
       ;;
  esac
  shift
done

initArch
initOS
create_device_id

checkDesiredVersion
if ! checkPipelessInstalledVersion; then
  if ! verifySupported; then
    verifyDependencies
    buildPipeless
  else
    verifyDependencies
    downloadFile
    verifyFile
    installFile
  fi
  setupPipelessEnv

  create_report "success"

  echo ""
  echo "Useful resources:"
  echo "* Getting started guide: https://www.pipeless.ai/docs/v1/getting-started"
  echo "* Step by step examples: https://www.pipeless.ai/docs/v1/examples"
fi
cleanup

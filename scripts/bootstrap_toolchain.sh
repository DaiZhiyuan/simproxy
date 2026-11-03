#!/usr/bin/env bash
# Fetch pinned DynamoRIO toolchains (host x86_64 + AArch64 target).
#
# Environment:
#   SIMPROXY_DR_VERSION  DynamoRIO cronbuild version (default: 11.91.20756)
#   SIMPROXY_TOOLS_DIR   destination directory (default: <repo>/.tools)
set -euo pipefail

VERSION="${SIMPROXY_DR_VERSION:-11.91.20756}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${SIMPROXY_TOOLS_DIR:-${REPO_ROOT}/.tools}"
BASE="https://github.com/DynamoRIO/dynamorio/releases/download/cronbuild-${VERSION}"

mkdir -p "${DEST}"

fetch() {
  local archive="$1"
  local dir="${DEST}/${archive%.tar.gz}"
  if [[ -d "${dir}" ]]; then
    echo "[skip] ${dir}"
    return
  fi
  echo "[get ] ${archive}"
  curl -fL --retry 3 --retry-delay 2 -o "${DEST}/${archive}" "${BASE}/${archive}"
  tar -xzf "${DEST}/${archive}" -C "${DEST}"
  rm -f "${DEST}/${archive}"
}

fetch "DynamoRIO-Linux-${VERSION}.tar.gz"
fetch "DynamoRIO-AArch64-Linux-${VERSION}.tar.gz"

HOST_HOME="${DEST}/DynamoRIO-Linux-${VERSION}"
AARCH64_HOME="${DEST}/DynamoRIO-AArch64-Linux-${VERSION}"

cat <<EOF

DynamoRIO toolchains ready in ${DEST}

  export DYNAMORIO_HOME=${HOST_HOME}
  export DYNAMORIO_AARCH64_HOME=${AARCH64_HOME}
  export PATH="\${DYNAMORIO_HOME}/bin64:\$PATH"

Notes:
  * Host x86_64 tools can profile x86_64 binaries on this machine.
  * AArch64 tools must run on an AArch64 host (or under qemu-aarch64 user mode
    with a matching sysroot). Cross-compile the client against
    \${DYNAMORIO_AARCH64_HOME}/cmake.
  * QEMU TCG plugins (libbbv/libcache/libhowvec) require a QEMU build with
    --enable-plugins; the distro qemu-user-static package often omits them.
EOF

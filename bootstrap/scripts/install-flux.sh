#!/usr/bin/env bash

set -euo pipefail

FLUX_VERSION="2.9.6"
ARCH="amd64"

BASE_URL="https://github.com/fluxcd/flux2/releases/download/v${FLUX_VERSION}"
ARCHIVE="flux_${FLUX_VERSION}_linux_${ARCH}.tar.gz"
CHECKSUMS="flux_${FLUX_VERSION}_checksums.txt"

TMP_DIR="$(mktemp -d)"

cleanup() {
    rm -rf "${TMP_DIR}"
}

trap cleanup EXIT

echo "Installing Flux v${FLUX_VERSION}..."

curl --fail --location --silent --show-error \
    "${BASE_URL}/${ARCHIVE}" \
    --output "${TMP_DIR}/${ARCHIVE}"

curl --fail --location --silent --show-error \
    "${BASE_URL}/${CHECKSUMS}" \
    --output "${TMP_DIR}/${CHECKSUMS}"

cd "${TMP_DIR}"

grep " ${ARCHIVE}$" "${CHECKSUMS}" | sha256sum --check

tar -xzf "${ARCHIVE}" flux

sudo install \
    --owner=root \
    --group=root \
    --mode=0755 \
    flux \
    /usr/local/bin/flux

echo
flux --version

echo
echo "Flux v${FLUX_VERSION} installed successfully."

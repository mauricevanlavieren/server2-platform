#!/usr/bin/env bash

set -euo pipefail

KUBECTL_VERSION="v1.36.4"
ARCH="amd64"

KUBECTL_URL="https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${ARCH}/kubectl"
CHECKSUM_URL="${KUBECTL_URL}.sha256"

TMP_DIR="$(mktemp -d)"

cleanup() {
    rm -rf "${TMP_DIR}"
}

trap cleanup EXIT

echo "Installing kubectl ${KUBECTL_VERSION}..."

curl --fail --location --silent --show-error \
    "${KUBECTL_URL}" \
    --output "${TMP_DIR}/kubectl"

curl --fail --location --silent --show-error \
    "${CHECKSUM_URL}" \
    --output "${TMP_DIR}/kubectl.sha256"

cd "${TMP_DIR}"

echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check

sudo install \
    --owner=root \
    --group=root \
    --mode=0755 \
    kubectl \
    /usr/local/bin/kubectl

echo
kubectl version --client

echo
echo "kubectl ${KUBECTL_VERSION} installed successfully."

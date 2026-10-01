#!/usr/bin/env bash

set -euo pipefail

SSH_HOST="server2"
SERVER_IP="192.168.0.162"
REMOTE_TEMP="/home/mau/k3s.yaml"
KUBE_DIR="${HOME}/.kube"
KUBE_CONFIG="${KUBE_DIR}/config"

echo "Preparing kubeconfig on ${SSH_HOST}..."

ssh -t "${SSH_HOST}" \
  "sudo cp /etc/rancher/k3s/k3s.yaml ${REMOTE_TEMP} &&
   sudo chown mau:mau ${REMOTE_TEMP} &&
   chmod 600 ${REMOTE_TEMP}"

mkdir -p "${KUBE_DIR}"
chmod 700 "${KUBE_DIR}"

echo "Copying kubeconfig..."

scp "${SSH_HOST}:${REMOTE_TEMP}" "${KUBE_CONFIG}"

chmod 600 "${KUBE_CONFIG}"

sed -i \
  "s#https://127\.0\.0\.1:6443#https://${SERVER_IP}:6443#" \
  "${KUBE_CONFIG}"

echo "Removing temporary kubeconfig from server..."

ssh "${SSH_HOST}" "rm -f ${REMOTE_TEMP}"

echo "Testing Kubernetes API access..."

kubectl --kubeconfig "${KUBE_CONFIG}" get nodes

echo
echo "Kubeconfig configured successfully."

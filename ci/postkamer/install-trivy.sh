#!/usr/bin/env bash
set -euo pipefail
: "${RUNNER_TEMP:?ephemeral runner temp required}"
: "${GITHUB_PATH:?GitHub path file required}"
tool_dir=$(mktemp -d "$RUNNER_TEMP/postkamer-trivy.XXXXXX")
curl --fail --silent --show-error --location https://github.com/aquasecurity/trivy/releases/download/v0.76.0/trivy_0.76.0_Linux-64bit.tar.gz --output "$tool_dir/trivy.tar.gz"
printf '%s  %s\n' e24b1c51293c1b15e4ba8d45bbc7891ba053f90278ec2698f3562c993e145fe7 "$tool_dir/trivy.tar.gz" | sha256sum --check --status
tar -xzf "$tool_dir/trivy.tar.gz" -C "$tool_dir" trivy
printf '%s\n' "$tool_dir" >> "$GITHUB_PATH"

#!/bin/sh
# No remote shell arguments are accepted; the helper validates bounded JSON stdin.
set -eu
case "${SSH_ORIGINAL_COMMAND-}" in
  server3-backup-control) exec /usr/bin/sudo -n /usr/local/sbin/server3-backup-control ;;
  *) exit 126 ;;
esac

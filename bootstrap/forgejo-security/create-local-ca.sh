#!/usr/bin/env bash
# Run only in the owner's own terminal after approved local bootstrap.
set -euo pipefail
umask 077
security_dir=/home/mau/.local/share/server2-security
profile_dir=/home/mau/server2-platform/bootstrap/forgejo-security
[[ -d "$security_dir" && ! -L "$security_dir" ]]
[[ "$(stat -c %a "$security_dir")" == 700 ]]
for name in ca.key.pem ca.crt.pem forgejo.key.pem forgejo.csr.pem forgejo.crt.pem ca.srl; do
  if [[ -e "$security_dir/$name" || -L "$security_dir/$name" ]]; then
    echo 'STOP: destination already exists; review partial/existing bootstrap first.' >&2
    exit 1
  fi
done
# Encrypted CA key: passphrase entered directly in this terminal, not arguments.
openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -aes-256-cbc \
  -out "$security_dir/ca.key.pem"
openssl req -new -x509 -sha256 -days 3650 -key "$security_dir/ca.key.pem" \
  -config "$profile_dir/ca.cnf" -out "$security_dir/ca.crt.pem"
openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 \
  -out "$security_dir/forgejo.key.pem"
openssl req -new -sha256 -key "$security_dir/forgejo.key.pem" \
  -config "$profile_dir/forgejo.cnf" -out "$security_dir/forgejo.csr.pem"
openssl x509 -req -sha256 -days 90 -in "$security_dir/forgejo.csr.pem" \
  -CA "$security_dir/ca.crt.pem" -CAkey "$security_dir/ca.key.pem" \
  -CAserial "$security_dir/ca.srl" -CAcreateserial \
  -extfile "$profile_dir/forgejo.cnf" -extensions leaf_extensions \
  -out "$security_dir/forgejo.crt.pem"
openssl verify -CAfile "$security_dir/ca.crt.pem" -purpose sslserver \
  -verify_hostname forgejo.home.arpa "$security_dir/forgejo.crt.pem"
echo 'Local CA and Forgejo certificate created and verified; no trust or cluster changes.'

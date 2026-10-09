#!/usr/bin/env bash
# Run only in the owner's terminal: generated password must never reach chat/logs.
set +x
set -euo pipefail
if [[ ! -t 0 || ! -t 1 ]]; then
  echo 'STOP: voer dit script rechtstreeks in je eigen interactieve terminal uit.' >&2
  exit 1
fi
kubectl --context server2 get nodes -o json | python3 -c 'import sys,json; n=json.load(sys.stdin)["items"]; assert len(n)==1 and n[0]["metadata"]["name"]=="mau2"; assert any(a["type"]=="InternalIP" and a["address"]=="192.168.0.162" for a in n[0]["status"]["addresses"])'
kubectl --context server2 -n forgejo wait --for=condition=Available deployment/forgejo --timeout=30s
read -r -p 'Nieuwe beheerdersgebruikersnaam: ' username
read -r -p 'E-mailadres: ' email
[[ "$username" =~ ^[A-Za-z0-9][A-Za-z0-9_-]{0,38}$ ]] || { echo 'Ongeldige gebruikersnaam'; exit 1; }
[[ "$email" == *@*.* && "$email" != -* && "$email" != *' '* ]] || { echo 'Ongeldig e-mailadres'; exit 1; }
echo 'Het tijdelijke wachtwoord verschijnt hieronder. Bewaar het direct in je wachtwoordmanager.'
echo 'Deel deze uitvoer niet in de chat. Log in via HTTPS en kies bij de eerste login een nieuw wachtwoord.'
kubectl --context server2 -n forgejo exec deployment/forgejo -c forgejo --   forgejo admin user create --work-path /var/lib/gitea   --config /var/lib/gitea/custom/conf/app.ini   --username "$username" --email "$email" --admin   --random-password --random-password-length 32 --must-change-password

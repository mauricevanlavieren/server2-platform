# Forgejo staging — DISABLED

Deze map is **READY** voor statische review, **DISABLED** en niet opgenomen in actieve Flux/Kustomizepaden. Deployment heeft daarnaast replicas=0. Geen Secretwaarden, adminwachtwoord of TLSprivatekey aanwezig; verplichte `forgejo-runtime` en `forgejo-tls` ontbreken bewust. Operationele werking **UNTESTED**, installatie **BLOCKED** op TLS/secrets/goedkeuring.

Architectuur, resourcebudget, versie/digest, afhankelijkheden, activatie en herstel: `../../../docs/server/forgejo-deployment-plan.md`. Encryptieadvies: `../../../docs/server/k3s-secrets-encryption-plan.md`.

Statische build: `kubectl kustomize kubernetes/apps/forgejo` (geen clusterapply). Gebruik geen `kubectl apply`. Publicatie van uitsluitend deze niet-gerefereerde stagingmap installeert niets; toevoegen aan `kubernetes/apps/kustomization.yaml`, activeren van een aparte Flux-Kustomization of replicas verhogen is een aparte live-impactvolle change.

ConfigMap is bron van niet-geheime app.ini. Initcontainer kopieert die naar de PVC bij iedere start; runtime gegenereerde appconfig mag geen enige bron van keys worden. Kritieke keyinstellingen verwijzen naar verplichte Secretbestanden. Image: officiële 15.0.9-rootless LTS, registrydigest gecontroleerd; containerstart, rootfsrechten, secret-URIinterpretatie en migratiehooks nog niet getest.

GitHub blijft onafhankelijke platformbron. Geen kritische repos/data zolang externe backups ontbreken. PVC/Namespace hebben Flux-prune-uitzondering, maar handmatige PVCdelete/SSDdefect blijft dataverliesrisico; local-path is geen harde 10GiB-quota.

Statische controles op 9 oktober 2026 geslaagd: YAML, standalone Kustomize-build (9 resources), selector/service/volume/secretref/probe/portcontroles, restricted-securityvelden, configparse, digestreferenties en credential-markerscan. Clusterroot/infrastructure/apps-builds bevatten geen Forgejoobject of reference; Fluxvoorbeeld suspend=true en Deployment replicas=0. Bestaande Dashywijzigingen en rapporten ongewijzigd, index leeg. Registry-indexdigest en amd64platform gecontroleerd; APIadmission, imagestart, certificaattrust, netwerkhandhaving en restore blijven UNTESTED. Helm-templatecheck niet van toepassing op gekozen gewone manifests.

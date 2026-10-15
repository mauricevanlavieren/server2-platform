# AI-startinstructies — server2-platform

Statusdatum: 2026-10-15. Fase 2 publiceert alleen de GitHub-basis en documentatie. Geen serverwijziging, deployment, applicatiemigratie of back-upactivatie. Gewenste vervolgstappen zijn geen uitgevoerde configuratie.

- Begin bij homelab-architecture/AGENTS.md, current-state.md en decisions.md; lees daarna de instructies van de beherende repository. Controleer branch, HEAD, remote en dirty-status. Een reviewbranch is geen actuele productiebron.
- Server1 nooit benaderen. Server2/3/4 niet wijzigen zonder afzonderlijk akkoord. Kubernetes alleen met expliciet --context server2 wanneer een latere opdracht dat toestaat. Geen secretwaarden, wachtwoorden of private sleutels uitlezen/publiceren.
- Eén configuratie-eigenaar: Server2-hostbeheer, Flux/Kubernetes en huidige applicatieconfiguratie. Toekomstige bronimports vereisen apart akkoord. Centrale documentatie verwijst, maar dupliceert geen beheerde manifests of inventory.
- Behoud lokale wijzigingen; geen reset/clean/stash/force-push. Backup v2 blijft op backup-v2-review, commit a0452266f8a58c7b9d8659fe8bab5c5ae6249c7d; niet mergen, herschrijven of activeren.
- Geen deployment, workflowactivatie, retentie, timers of shutdown zonder specifiek akkoord. Publicatie van documentatie is geen toestemming voor toekomstige implementaties.
- Markeer bewijs als live gecontroleerd, uit configuratie/documentatie, door eigenaar aangeleverd of onbekend. Historische server1-documentatie is geen live status.
- Handover bevat scope, bronnen/SHA/datum, dirty-status, tests, toestemming, blokkades, rollback en eerstvolgende veilige stap. Geen authenticatiegegevens.

# AI-instructies — Server2

**Lees eerst [centrale AI-overdracht](https://github.com/mauricevanlavieren/homelab-architecture/blob/main/docs/AI-HANDOVER.md)** en vervolgens deze README, relevante `docs/server/`-audits en applicatiedocumentatie. De server2-platform-repository is de **gewenste configuratie** voor Server2, niet automatisch bewijs van de actuele runtime.

- Werk in het Nederlands, compact, conceptueel en met één terminalcommando per stap; wacht op uitvoer. Bij leerwerk 🧠 KENNEN / 🔧 KUNNEN / 📖 OPZOEKEN.
- Server2: `mau2`, 192.168.0.162 volgens documentatie. Server1 nooit benaderen zonder aparte scope. Gebruik bij toegestane Kubernetes-controles uitsluitend expliciet `--context server2` of de geverifieerde `kubectl-server2`-wrapper.
- Begin read-only: Git-branch/HEAD/status, README, Flux-manifests, relevante docs en (indien geautoriseerd) live node/Flux/pods. Nooit standaard-kubectl-context vertrouwen.
- Git/Flux beheren de gewenste toestand. Geen directe permanente `kubectl edit/delete`, geen blind helm-upgrade, geen ongeautoriseerde CI, imagepush, PR-merge of deployment.
- Bescherm bestaande lokale wijzigingen; geen reset/clean/stash/force-push. Geen secrets, tokens, Restic-wachtwoorden of private sleutels in Git, Notion of antwoord.
- Applicatiebronnen: `applications/postkamer`, `applications/platform-status-api`, `applications/it-discovery`. Bronconsolidatie betekent niet dat alle live deployments of oude packageconsumers zijn gemigreerd.
- Postkamer: review fase 14 had P2-gaten in scanbewijs, productieguard-CI en bewaren van SBOM/rapporten; tijdelijke risico-uitzondering verloopt op 20 oktober 2026 17:19:30 UTC. Geen automatische verlenging of releaseacceptatie.
- Backup en restore: onderscheid testbackups, lokale hostbackups en onafhankelijke off-host herstelkopieën. Server3 had een gedegradeerd RAID en vervangende HDD was nog niet gevalideerd.
- Vraag toestemming voor risicovolle acties en documenteer diff, tests, status, rollback en hervatpunt. Raadpleeg Notion voor planning, Git voor gewenste configuratie en live host/cluster voor runtime.

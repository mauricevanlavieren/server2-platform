# Server2 backup preparation

Status: **READY** = configuratie/code lokaal voorbereid; **DISABLED** = alle timers en uitvoering bewust uit; **BLOCKED** = externe backupserver/credentials ontbreken; **UNTESTED** = deployment, backup, consistency onder belasting en restore niet getest. Statische checks zijn geen VERIFIED backupketen.

Geen software of units op server2 geïnstalleerd. Deze map bevat geen credentials of backupdata. Alleen na afzonderlijke toestemming deployen met `bootstrap/ansible/backup-prepare.yml`; het playbook vereist `backup_deployment_approved=true` en een geselecteerde `backup_restic_package_version`. Dat akkoord is nu niet gegeven. De role weigert `backup_enabled=true`, installeert bij toekomstige goedgekeurde uitvoering units maar houdt timers stopped/disabled. Er is bewust geen activatieplaybook.

## Componenten

- `../ansible/roles/backup/files/backup.py`: hostbackup via Python SQLite Online Backup API, WAL-aware clonecheck, matching token/TLS-set, geselecteerde hostconfig; Restic naar TLS REST backend.
- `../ansible/roles/backup/templates/`: private JSONconfig, backup/check/freshness-services en timers zonder `[Install]`-sectie.
- `examples/config.disabled.json`: veilige default, lege bestemming, geen secrets.
- `examples/future-backupserver.service`: alleen voorbeeld voor append-only TLS rest-server; account, binary, quota, firewall, auth en certificaten later reviewen. Quota 100 GiB is een placeholder, geen sizingbesluit.
- `examples/application-contract.example.yml`: contracttemplate; geen exporthooks of actieve PVC-jobs.

## Runtimevoorwaarden voor latere uitvoering

Vereist root op mau2, `enabled=true`, expliciete `rest:https://` bestemming, matching `destination_host`, gepinde 64-teken repository-ID, CA-cert en drie root-only systemd credentials: `repository-password`, `rest-user`, `rest-password`. De deploymentrole maakt deze niet aan. Geen credentials in URL of argumenten; foutoutput is geschoond. Bronhost/server1/loopback zijn geen toegestane bestemming; DNS-aliascontroles zijn extra guards, geen netwerksecurityvervanging. Bij transportwijziging alleen configuratie uitbreiden plus reviewed backendadapter; deze versie ondersteunt bewust uitsluitend TLS REST, geen generieke lokale fallback.

Backupservice krijgt een private begrensde `noswap` tmpfs via systemd; ontbrekende ondersteuning doet de service/runner falen. Alleen later goedgekeurde backupuitvoering creëert exports; cleanup raakt uitsluitend de nieuw aangemaakte generatie. Geen live raw `state.db`-kopie en geen oude WAL/SHM naast clone. `ProtectSystem=strict` beschermt bronconfig; SQLite read-only/WAL-toegang op de echte host moet nog worden getest. `--no-cache` voorkomt lokale backupcache. Status/lock bevatten uitsluitend IDs/tijd, geen dataset.

Export bevat token en TLS-bestanden plus geselecteerde `/etc`-config; checksums vóór/na detecteren overlappende keyrotatie. Rotatieprocedure moet later dezelfde maintenance-interlock respecteren. Toekomstige k3s secrets-encrypt keys buiten deze allowlist moeten expliciet worden toegevoegd vóór encryptieactivatie/backupvrijgave. Dit script is geen volledige hostimage of volledige credentialinventaris.

Een cluster-candidate telt pas mee na succesvolle Restic-exitcode en een aparte off-host receipt die het snapshot-ID en manifesthash aanwijst. Restoreselectie moet receipts volgen en de targetmanifesthash controleren; candidate-only/partial snapshots zijn geen herstelbewijs. Twee snapshots horen bij één generatie; retentie moet gekoppelde receipt/candidate samen bewaren. Geen automatische retries in deze eerste runner: bounded next-timer attempt, systemdtimeout en zichtbaar falen. Retrybackoff, geïntegreerde alerts, vertrouwde target-ontvangstregistratie en onderhoud zijn nog niet geïmplementeerd.

`check` doet repositorymetadata-integriteit, geen full-data/restorecheck. `status` geeft nonzero bij disabled/ontbrekende/stale backup en geeft geen notificatie: later koppelen aan gekozen monitor plus extern dead-man signaal. Status mag bij monitoring niet naar groen worden vertaald zolang backup DISABLED is.

## App/PVC en restore

Niet-lege `application_contracts` worden geweigerd: geen impliciete kopie van databases/PVCs. Eerst specifieke native exporter, schrijfstop/resume, PVC-UID/padmapping, consistente generatie en test ontwerpen; daarna runner gericht uitbreiden. Forgejo DB/repositories/attachments/LFS/config samen beschermen. Geen automatische restorecommando's voorbereid: destructive cutover vraagt afzonderlijke toestemming en een versiegebonden geteste procedure.

Toekomstige geïsoleerde end-to-end proef: lege VM → offline Git bundle/hostbootstrap → passende k3s/token/SQLite → PVmapping/data → appchecks → gecontroleerde Fluxvrijgave. Ook WAL-load, incomplete export, backend offline/full, TLSfout en append-only deleteweigering testen. Zie `../../docs/server/disaster-recovery-plan.md`.

## Statische validatie

Python AST/syntax, YAML/JSON en Ansible syntax-check; render templates in tijdelijke werkdirectory en `systemd-analyze verify` zonder installatie. Geen `ansible-playbook` run, `restic init`, backup, restore, service start of DBopen uitgevoerd tijdens voorbereiding. Schrijf de runner niet aanroepen voor checks op productie.

Uitgevoerd op 9 oktober 2026: YAMLwerkboom, voorbeeld-JSON, Python AST, Ansible `--syntax-check`, StrictUndefined-template-rendering, gerenderde systemd-unitvalidatie en bestaande shellscripts `bash -n` geslaagd. Voor unitvalidatie wees ExecStart uitsluitend naar een lokale tijdelijke kopie zodat de verifier het executablepad kon vinden; niets uitgevoerd. Kustomize-builds voor cluster/infrastructure/apps geslaagd. Disabled/lege defaults en ontbrekende Install-secties statisch gecontroleerd. Secret-marker/veldscan op tracked werkboom en nieuwe backupvoorbereiding vond geen private-keymarkers, bekende tokenpatronen, gevulde Kubernetes Secret-manifests of geselecteerde letterlijke secretvelden. Geen volledige entropy-, Gitgeschiedenis- of externe-hostscan. Operationele status blijft UNTESTED.

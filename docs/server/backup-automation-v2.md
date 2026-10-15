> Reviewbranch 15 oktober 2026: alleen codevoorbereiding. Niets op servers geïnstalleerd of geactiveerd. Zie `backup-v2-code-review.md` voor implementatiestatus en beperkingen.

# Server2/server3 — concreet back-upautomatiseringsontwerp

Datum: 15 oktober 2026. **ONTWERP, NIET GEÏMPLEMENTEERD OF GEACTIVEERD.** Fase 2 Postkamer is geslaagd; zie `postkamer-backup-verification.md`. Dit ontwerp is geen toestemming voor deployment, apponderbreking, retentie, nieuwe toegangsrechten of shutdown. Server1 is uitgesloten.

## 1. Uitgangspunt en beslissingen

Behoud Restic 0.16.4 en de bestaande SFTP-repository; geen upgrade of nieuwe repository nodig voor deze stap. Pin hostkey, repository-ID `00c5600469b3306c939434a0e232fb141e844a3931a307a1c0af58e5066fed68` en filesystem-UUID `67837227-f008-4257-822a-b4562efa2daa`. Herinitialiseer nooit automatisch een ontbrekende repository.

Server2 coördineert; server3 controleert zelf zijn mount/RAID en beheert een exclusieve lease. De laptop is na implementatie geen operationele afhankelijkheid. De huidige laptop-guard uit fase 2 is uitsluitend het geteste prototype.

Startvoorstel: één dagelijkse bundel om **03:30 UTC**, inclusief alle vier datasets, GitOps- en herstelmateriaal. Dat geeft alleen bij succesvolle uitvoering een beoogde RPO van maximaal 24 uur; alarm bij 26 uur zonder complete bundel. Een kortere RPO vereist een apart besluit over frequentie, energiegebruik en Forgejo-schrijfonderbreking. Geen RTO-garantie: nog meten bij een volledige herstelproef.

Standaarden: `enabled=false`, `allow_application_pause=false`, `retention_enabled=false`, `shutdown_enabled=false`. Geen automatische `unlock`, `forget`, `prune`, reparatie, DBmigratie of fallback naar een ongecontroleerd pad.

## 2. Volgorde per bundel

1. Neem een lokale exclusieve lock en maak één run-ID. Controleer configuratie, versies, vaste endpoints, ruimte en credentialsmetadata. Geen secretwaarden loggen.
2. Controleer server3 met hostkeyverificatie. Is hij al bereikbaar, leg boot-ID en reeds-aan-status vast; deze run mag hem later niet uitschakelen. Is hij onbereikbaar, stuur hoogstens drie WoL-pogingen naar de vooraf goedgekeurde LAN-broadcast met vaste MAC `20:cf:30:7f:56:f8`. Wacht begrensd, bijvoorbeeld vijf minuten, op geauthenticeerde SSH. Onbereikbaar is geen bewijs dat de machine uit stond.
3. Vraag via het beperkte controlaccount een lease op server3. Controleer hostname/IP, echte mountpoint /backup, UUID, ext4, juiste md-array, twee leden/degraded=0, beschikbare blokken/inodes, repositorypad zonder symlink en repository-ID. Controleer onderhoudsblokkade en aanwezige repositorylocks; bij conflict wachten binnen limiet of stoppen, nooit locks verwijderen.
4. De server3-controlhelper houdt het mountpoint open en vernieuwt een kortlopende lease. Controleer guard vóór iedere schrijfopdracht en tijdens langlopende Restic-processen. Bij lease-/SSH-/mountuitval: proces gecontroleerd stoppen, geen succesmelding, geen shutdown. Reeds opgeslagen snapshots behouden.
5. Exporteer datasets volgens de contracten hieronder, sequentieel in een begrensde private noswap-tmpfs. Bereken per export vooraf een bovengrens plus herstelruimte en minimaal 16 MiB marge. Houd minimaal 512 MiB MemAvailable over en reserveer niet meer dan 1/8 van het actuele beschikbare RAM; de uiteindelijke limiet moet op Forgejo-/k3s-datagrootte worden gedimensioneerd. Ontbrekende ruimte: stoppen. Geen onversleutelde diskfallback. Grote datasets vragen later expliciet goedgekeurde versleutelde scratchopslag of een gevalideerde andere methode.
6. Schrijf per dataset een nieuw candidate-snapshot met run-ID, dataset en contractversie. Gebruik stabiele exportpaden per dataset, geen steeds wisselende directory als retentiegroepering. Leg bron-PVC-UID/pad, image-digest, Gitrevision, toolversies, tijdvenster, checksums en aantallen vast in een versleuteld manifest.
7. Herstel de candidate naar een aparte testlocatie. Controleer inhoud én native integriteit. `check` zonder datalezen is onvoldoende. In de eerste kleine omgeving: volledige `restic check --read-data` per bundel; later kan dit na meting worden verdeeld in aantoonbaar volledige cycli plus maandelijkse volledige controle. Restoreproeven blijven nodig.
8. Schrijf pas daarna een apart versleuteld receipt-snapshot dat de exacte candidate-ID's en manifesthashes noemt. Een complete bundel bestaat alleen als alle vier datasets en het herstelpakket aantoonbaar zijn geverifieerd. Een deels geslaagde run heeft bruikbare afzonderlijke snapshots, maar blijft PARTIAL/nonzero en krijgt geen volledig-groen status.
9. Ruim uitsluitend de eigen tijdelijke exports/restores op, ontkoppel eigen tmpfs en sla niet-geheime status atomair op. Laat bij verificatiefouten gevoelige staging alleen root-only op noswap-tmpfs achter voor onderzoek; meld grootte/pad. Verifieer bij volgende run eerst de vorige toestand, hergebruik of wis die niet blind.
10. Publiceer resultaat/alarm, geef lease vrij en beoordeel eventueel de afzonderlijk goedgekeurde shutdownvoorwaarden. Een foutpad schakelt server3 nooit automatisch uit.

Geen bundel is een simultane snapshot van alle applicaties: elk contract heeft een eigen consistent tijdstip binnen het vastgelegde bundelvenster. Alleen afhankelijkheden die gezamenlijk consistent moeten zijn, worden samen bevroren/exporteerd.

## 3. Datasetcontracten

| Dataset | Methode | Verplichte herstelinhoud en bewijs |
|---|---|---|
| k3s SQLite | Read-only SQLite Online Backup API, met begrensde duur; geen live DB/WAL-bestandskopie | Consistente state.db plus bijpassende server-token, noodzakelijke TLS/credentialset, actieve configuratie en eventuele secrets-encryption-config. Controleer key/config-inventarishashes vóór en na export; geen sleutelrotatie/upgrades tijdens de bundel. SQLite-integriteit én afzonderlijke clusterherstelproef vereist. |
| Postkamer | In fase 2 bewezen Online Backup API | DB inclusief berichten, concepten en FTS-tabellen; SHA-256, integrity/foreign-keychecks, tabelaantallen, appimage en PVCmapping. Huidige enige PVC-file is demo.sqlite; nieuwe sidefiles veranderen het contract en blokkeren een stilzwijgende DB-only back-up. |
| Inventory | Online Backup API na inspectie van bestaande root-only runner en complete datainventaris | inventory.sqlite, passende bron-ConfigMap/Gitrevision/image, eventuele overige persistente bestanden. Inspecteer bestaande timer/script eerst; laatste succes bewijst geen volledige herstelketen. |
| Forgejo | Gevalideerde gezamenlijke backup van DB, Gitrepositories, attachments/andere files en runtimeconfig | Zolang geen bewezen hot-back-upmethode beschikbaar is, is een korte gecontroleerde schrijfpauze nodig. Een losse SQLite-export naast live Gitfiles is niet voldoende. `forgejo dump` wordt niet blind als consistentiegarantie gebruikt. |

**Forgejo-gate:** nu is geen applicatiestop toegestaan. Vraag vóór implementatie toestemming voor exact benoemde onderhoudsduur en GitOps-afstemming. Voorkeursontwerp is een expliciet goedgekeurd onderhoudscontract: oorspronkelijke Flux-/replicastatus vastleggen, alleen de Forgejo-reconciliation tijdelijk beheerst pauzeren, alle Forgejo-writers gecontroleerd stoppen, coherent volledige PVC met runtimeafhankelijkheden back-uppen, oorspronkelijke toestand herstellen en health/login/Git controleren. Ingress blokkeren alleen stopt geen achtergrondwriters. Geen gedeelde Flux-root pauzeren. Voeg een onafhankelijke resume-watchdog en een geteste herstelactie toe zodat een runnercrash de app niet stil achterlaat. De precieze commando's zijn pas uitvoeringsklaar na runtimevalidatie en goedkeuring. Tot dan is de volledige bundel geblokkeerd; nooit heimelijk stoppen of een inconsistente back-up groen noemen.

De officiële Forgejo-handleiding benadrukt de moeilijkheid van consistente DB/files-back-ups terwijl Forgejo draait. De geraadpleegde actuele handleiding betreft v17; de geïnstalleerde image is v15.0.9. Exact gedrag moet daarom tegen die gepinde versie worden getest: https://forgejo.org/docs/v17.0/admin/setup/backup/.

k3s vereist het bijpassende server-token voor herstel van zijn vertrouwelijke datastoregegevens: https://docs.k3s.io/datastore/backup-restore.

## 4. Herstelpakket buiten appdata

Versleuteld per bundel opnemen, na inventarisatie en expliciete scopecontrole:

- Actuele Git bundle van mauricevanlavieren/server2-platform met volledige commit-ID, alle gebruikte refs/submodules/LFS-objecten waar van toepassing. Maak deze vanuit een actuele geverifieerde bron; de huidige laptopclone loopt achter en bevat aparte lokale Dashywijzigingen.
- Gewenste manifests én benodigde werkelijke PVC/PV/node/UID/pad/ownership-inventaris; actuele Fluxrevisions, containerimages/digests, charts en broncode-ConfigMaps. Alleen Git dekt niet iedere live wijziging. Bewaar gepinde image-exports/OCI-artefacten en charts die anders door registryverlies onbereikbaar zijn, in versleutelde storage met hashes.
- k3s-config, service/drop-ins, token/TLS/credentialset en eventuele encryptieconfig als één passende set. Onderzoek ook /etc/rancher/node/password en registryconfig. Sla geen volledige willekeurige /etc-tree op zonder secrets-/scopebeleid.
- SOPS-age herstelidentiteit, noodzakelijke app/TLS-secrets, GHCR-pullcredential en Flux-bootstrapherstel. Geen plaintext Kubernetes Secret-export in Git of logs. Gebruik private staging en direct Restic-encryptie.
- Hostbootstrap: Ubuntu-/k3s-/Restic-versies, geverifieerde installatiemiddelen, package-/service-inventaris, Ansiblebasis, geselecteerde netwerk/storage/SSH/firewallconfig en server3 hostkeytrust. Nieuwe hardware kan andere NIC-/disknamen vereisen.
- Interne CA-public certificate; CA-private key en passphrase alleen in een apart expliciet goedgekeurd escrowproces, nooit als onversleutelde repo-inhoud.

**Onafhankelijke recoveryset:** Restic-wachtwoord en toegang tot server3 moeten buiten server2 én buiten uitsluitend deze Restic-repository beschikbaar zijn, bijvoorbeeld eigenaar-wachtwoordmanager plus een offline herstelkopie. CA-/age-/GitHubrecovery eveneens onafhankelijk bewaren. Het wachtwoord alleen in de repository back-uppen creëert een onoplosbare afhankelijkheid. Bestaande escrow is nog niet aangetoond.

## 5. Minimale server3-controltoegang

Behoud backupsvc en zijn SFTP-only beperkingen. Introduceer alleen na goedkeuring een afzonderlijk `backupctl`-account met een nieuwe afzonderlijke controlkey, vast bron-IP en gepinde hostkey; geen TTY, forwarding, agentforwarding of vrije shell.

Een root-owned forced-command-wrapper accepteert uitsluitend `check`, `lease-acquire`, `lease-renew`, `lease-release` en de later vrij te geven `poweroff-safe`. Requests bevatten strikt begrensde JSON, vaste repository, run-ID en boot-ID; geen vrije bestandspaden of shellfragmenten. Een kleine roothelper krijgt uitsluitend het vaste, argumentloze sudo-entrypoint; het sudoers-bestand moet met visudo worden gevalideerd. De helper valideert peer/caller, invoer en lease zelf en voert vaste argv-opdrachten uit. Geen algemene sudo-rechten.

Voor shutdown zijn ALLEN vereist: aparte toestemming; server3 niet reeds aan bij start; aantoonbaar toegestane powerownership in een exclusief backupvenster; identieke boot-ID; actuele eigen lease; alle datasets/receipts succesvol; geen andere leases, Resticlocks, schrijvers, actieve beheersessie, onderhoudsblokkade of RAID-resync/recovery/check; en een laatste mount-/RAIDcontrole. Alleen SSH-onbereikbaarheid vóór WoL bewijst geen powerownership. Bij twijfel blijft server3 aan. Geen shutdown vanuit een generieke systemd ExecStopPost of fouttrap. WoL moet eerst met eigenaar en fysieke terugvalmogelijkheid worden getest; PCI wakeup=enabled is geen bewijs dat magic-packet wake werkt.

## 6. Systemd, logging en foutafhandeling

Voorgestelde service: Type=oneshot, root, UMask=0077, begrensde looptijd (eerste voorstel 45 minuten), exclusieve lokale lock, PrivateTmp, ProtectSystem=strict, ProtectHome, NoNewPrivileges, LimitCORE=0, MemorySwapMax=0, CPU/IO-prioriteit laag en strikt afgebakende schrijf-/credentialpaden. Sandbox en WAL-read-only gedrag moeten eerst op de echte host worden getest; niet blind de oude REST-only unit kopiëren. LoadCredential kan bestaande root-only credentials gebruiken; SSHcommand verwijst naar credentialbestanden, nooit hun inhoud.

Timerontwerp: OnCalendar=`*-*-* 03:30:00 UTC`, Persistent=true, RandomizedDelaySec=300, AccuracySec=1min. Timer wordt bij eerste installatie disabled/stopped gehouden. Een gemiste run mag later inhalen, maar nooit een onderhoudsvenster voor apponderbreking omzeilen. Geen destructieve retry en geen eindeloze automatische herstart; maximaal drie begrensde verbindingspogingen, daarna zichtbaar falen tot volgende goedgekeurde run.

Journald en atomair status.json bevatten alleen run-ID, fase, dataset, begin/einde, exitcode, snapshot-ID's, bytes en niet-geheime verificatie-uitkomsten. Geen mailboxinhoud, SQLrecords, Secretwaarden, envdumps, private keys of ruwe foutoutput. Houd detailfouten intern geschoond; root-only logs met begrensde retentie. OnFailure levert een melding aan een nog te kiezen onafhankelijk kanaal. Afzonderlijke freshnesscontrole moet ook het volledig uitblijven van de timer detecteren; alleen een foutmail van de runner is onvoldoende. Na uitschakelen server3 kan het externe signaal niet uitsluitend daar draaien.

## 7. Retentie en bescherming tegen wissen

Nu: **niets verwijderen, geen forget/prune/unlock**. De bestaande vier bekende snapshots (k3s, Forgejo, Inventory, fase-2-Postkamer) vallen niet automatisch onder toekomstig retentiebeheer.

Later voorstel ter goedkeuring: 14 dagelijkse, 8 wekelijkse en 12 maandelijkse complete bundels, plus minimaal twee bewezen herstelpunten per dataset. Nooit de laatste geverifieerde bundel verwijderen. Kandidaten en receipts samen selecteren via manifest, niet losse tag-/padheuristiek. Eerst rapport/dry-run, dan onafhankelijke beoordeling; onderhoud vanaf server3 met aparte bevoegdheid en zonder actieve writers. Grootte en groei eerst meten. Geen geplande deletecode installeren zolang deze toestemming ontbreekt.

SFTP-only maakt de repository niet append-only: een schrijfaccount kan doorgaans ook verwijderen. Huidige bescherming tegen broncompromis is daarom niet bewezen. Ontwerpoptie is een onafhankelijke offline/off-site kopie met aparte beheercredentials. Backendmigratie naar append-only REST is een afzonderlijk besluit, niet onderdeel van deze stap. Zie https://restic.readthedocs.io/en/stable/060_forget.html.

## 8. Exact voorgestelde wijzigingen — nog niet gemaakt

Onder `/home/mau/server2-platform`, in een actuele afzonderlijke reviewbare wijziging; bestaande lokale Dashy- en auditwijzigingen niet meenemen:

| Nieuwe bronbestanden | Doel |
|---|---|
| bootstrap/ansible/backup-v2-prepare.yml | Alleen goedgekeurde voorbereiding deployen, standaard geen activering |
| bootstrap/ansible/roles/backup_v2/defaults/main.yml | Vaste IDs/UUID/hosts, disabled/pause/retentie/shutdown-false |
| bootstrap/ansible/roles/backup_v2/tasks/main.yml | Rechten, validatie, sandboxunits; geen automatische enable/start |
| bootstrap/ansible/roles/backup_v2/files/server2_backup.py | Orchestrator en vaste read-only exporters/restoreverificatie |
| bootstrap/ansible/roles/backup_v2/files/server3_backup_control.py | Beperkte mount-/lease-/powerhelper met standaard uitgeschakelde poweractie |
| bootstrap/ansible/roles/backup_v2/templates/config.json.j2 | Niet-geheime config met vaste identiteiten en contracten |
| bootstrap/ansible/roles/backup_v2/templates/server2-backup-v2.service.j2 | Beperkte oneshot-unit |
| bootstrap/ansible/roles/backup_v2/templates/server2-backup-v2.timer.j2 | Dagelijks schema, bij deployment disabled/stopped |
| bootstrap/ansible/roles/backup_v2/templates/server2-backup-v2-status.service.j2 | Freshnesscontrole zonder datasets te lezen |
| bootstrap/ansible/roles/backup_v2/templates/server2-backup-v2-status.timer.j2 | Statusschema, bij deployment disabled/stopped |
| bootstrap/ansible/roles/backup_v2/templates/server3-backup-control.sudoers.j2 | Eén vast helper-entrypoint; visudo vóór installatie |
| bootstrap/ansible/roles/backup_v2/templates/backupctl.authorized_keys.j2 | Uitsluitend publieke key en forced-commandrestricties |
| bootstrap/recovery/README.md en voorbereidingsscripts | Gevalideerde herstelgates; geen automatische productierestore |
| docs/server/backup-automation-v2.md, disaster-recovery-v2.md, postkamer-backup-verification.md | Dit ontwerp, herstelprocedure en bewijs; oude docs als historisch markeren |

Toekomstige runtimebestanden op server2: `/usr/local/sbin/server2-backup-v2`, `/etc/server2-backup-v2/config.json`, aparte controlkey/known_hosts onder `/etc/server2-backup-v2/ssh/`, `/var/lib/server2-backup-v2/status.json`, private `/run/server2-backup-v2/`, voorgenoemde units onder `/etc/systemd/system/`. Bestaande `/etc/restic/password` en backupkey blijven behouden; geen secretwaarden in Ansibledefaults/Git. Nieuwe controlkey en onafhankelijke escrow vragen expliciete scopegoedkeuring.

Op server3: account backupctl, root-owned `/usr/local/sbin/server3-backup-control`, beperkt sudoersbestand, publieke forced-command-key en `/run/server3-backup-control/` voor leases. Geen wijziging aan bestaande backupsvc-rechten of repository-inhoud buiten nieuwe snapshots.

De bestaande `it-discovery-backup.timer` blijft nu intact. Na geslaagde v2-handmatige bundel volgt een apart goedgekeurde overdracht: oude timer stoppen/disable, oude code behouden, overlap voorkomen en pas dan de nieuwe timer activeren. Geen twee schrijvers stilzwijgend naast elkaar laten lopen. Oude documentatie van 9 oktober is aantoonbaar achterhaald en mag niet als operationele waarheid worden gebruikt.

## 9. Vrijgavegates

1. Eigenaar keurt bron-/runtimebestanden, controltoegang en credentialescrow goed. Repositoryactualisering gebeurt zonder lokale wijzigingen te verliezen.
2. Root-only bestaande Inventory-code en alle herstelafhankelijkheden gecontroleerd; juiste k3s/config/keyset vastgesteld; exacte Forgejo-consistentiemethode en eventuele onderbreking apart goedgekeurd.
3. Code/sandbox/Ansible/unitvalidatie; fouttests: server3 uit, verkeerde UUID, ontbrekende mount, degraded RAID, lockconflict, disk/RAM vol, SSHhostkeyfout, exporttimeout en runnercrash tijdens eventueel onderhoud. Alle gevallen falen veilig, zonder retentie/shutdown of achtergelaten appstop.
4. Handmatige complete vier-datasetbundel en native restores; volledig defecte server2 simuleren in geïsoleerde omgeving en RPO/RTO meten. Geen test tegen productie-PVC's, geen server1.
5. Afzonderlijk akkoord voor timeractivatie en gecontroleerde overdracht van de Inventory-timer. Daarna pas optionele retentie en later shutdown elk apart goedkeuren.

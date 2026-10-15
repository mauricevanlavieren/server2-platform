# Backup v2 — lokale reviewvoorbereiding

Status 15 oktober 2026: code en synthetische tests aanwezig; **niet gedeployed en niet production-ready**. Alle enable/release/contract/WoL/overdracht/pause/retentie/powerflags staan false. Er bestaat geen activatieplaybook. Deze map wordt niet door Flux gerefereerd.

## Lokale validatie

Vanaf de repositoryroot, zonder SSH, sudo, installatie of echte credentials:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 bootstrap/backup-v2/validate_local.py
```

Dit vereist reeds aanwezige Python3 + PyYAML + Jinja2, Ansible, git, visudo en systemd-analyze. De validator installeert niets. Hij gebruikt uitsluitend tijdelijke synthetische SQLite-/Gitbestanden, een repositorytestdouble, renderoutput en syntaxchecks. `systemd-analyze verify` krijgt een tijdelijke ExecStart-verwijzing naar de lokale Python-interpreter omdat de productierunner niet geïnstalleerd is. Dat verifieert syntax, niet werking op server2. Sudoers wordt alleen geparseerd, niet geïnstalleerd. De synthetische Gitfixture is een lege bare repository; tests maken geen commits/pushes.

## Codeonderdelen

- `../ansible/roles/backup_v2/files/server2_backup.py`: disabled-first runner, vaste targetidentiteiten, beperkte WoL, persistent SSHcontrolkanaal, guard/leasebewaking, read-only SQLite-export, matching k3s-config/key-inventaris, sealed-exportconsumenten, native restorechecks, Restic-writes zonder delete-acties en complete bundelreceipts met readback.
- `server3_backup_control.py` in dezelfde filesmap: begrensde JSONrequests; vaste mount/UUID/RAID-/ruimtecheck, exclusieve sessionlock, boot-ID en monotone leasetermijn. De sessie houdt /backup als cwd vast. Geen shell/powercommando's. Alle controlacties zijn door disabled config geblokkeerd tot latere vrijgave.
- `server3_backup_forced.sh`: uitsluitend het vaste SSHcommandlabel wordt naar de argumentloze sudohelper geleid. De bijbehorende toegangs- en sudoerstemplates zijn **alleen reviewartefacten**, niet onderdeel van deploymenttasks.
- `../recovery/`: onafhankelijke recoveryset als ontwerp, offline manifestchecker en server4-oefenplan. Verzamelt/ontsleutelt geen credentials.

## Expliciete grenzen

Er is geen code die Forgejo schaalt/suspendeert, retentie uitvoert of server3 uitschakelt. True zetten van die flags wordt geweigerd, niet als impliciete autorisatie geïnterpreteerd. Een coherent Forgejo-export moet door een apart goedgekeurde producent met schrijffence en onafhankelijke resume-watchdog worden geleverd; die producent is nu niet geïmplementeerd of vrijgegeven. De runner consumeert alleen root-only sealed exports op een aparte private noswap-tmpfs onder /run/server2-sealed-exports. Een seal is een vertrouwde verklaring van die producent, geen zelfstandig bewijs dat writers werkelijk gestopt waren. Dit blijft een harde runtimevrijgavegate.

De recoveryproducent is eveneens een interface naar een apart goedgekeurde offline set; er worden nu geen geheime bestanden verzameld. K3s blokkeert totdat zijn complete recovery_paths, encryption-inventory en rotatie-interlock expliciet zijn geverifieerd. De oorspronkelijke TLSboom kan symlinks bevatten; die worden geweigerd tot een veilige canonicalisatie expliciet is ontworpen/gevalideerd.

Voor nieuwe productieuitvoering zijn minstens expliciete deployment-/runtime-/contract-/Inventory-overdrachtsakkoorden nodig, actuele bronconfig, gepinde hostkeys en echte credentials via lokale veilige provisioning. Bestaande Inventory-timer wordt door de code alleen read-only gecontroleerd; zolang die enabled/active is, weigert de v2-runner. Hij wijzigt die timer nooit zelf.

De unit bezit een private noswap-tmpfs. Bij service-exit verdwijnt die namespace en daarmee de vluchtige plaintext; mislukte exports worden nooit hergebruikt. Een handmatige run op een door de eigenaar gemounte tmpfs kan staging voor onderzoek behouden. Metadata blijft in status/journal; geen plaintextfallback. De runner houdt een globale lock buiten de private mountnamespace en schrijft pas verified status na receipt-readback én stagingcleanup. De volledige bundel verzamelt datasets binnen een tijdvenster en is geen gelijktijdige snapshot van alle apps.

## Nog niet bewezen

Geen echte WoL-test, server3-controlaccount, hostkey/keyprovisioning, service-sandbox/WAL-proef, Forgejo-fencing/watchdog, onafhankelijke recoveryset, alertbezorging of volledige server4-hersteltest. De lokale hersteltestdouble bewijst de beslislogica, niet SFTP-encryptie of echte snapshots. De fase-2-Postkamerproef is het afzonderlijke echte bewijs.

Zie `../../docs/server/backup-v2-code-review.md`, `backup-automation-v2.md` en `disaster-recovery-v2.md`. De lokale branch is bewust gebaseerd op bestaande lokale HEAD a960d16; hij is niet gefetcht, gemerged, gecommit of gepusht. Hij loopt achter op de tijdens inventarisatie waargenomen main 13fba60. Actualisering vraagt later een afzonderlijke review; bestaande werkboomwijzigingen blijven behouden.

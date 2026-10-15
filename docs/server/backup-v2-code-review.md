# Backup v2 — codevoorbereiding voor beoordeling

Datum: 15 oktober 2026. Branch: **backup-v2-review**. Basis-HEAD: **a960d165321e443b829f726133970ec9be74ef21**. Geen commit/push, fetch/merge of remote actie uitgevoerd in deze codevoorbereiding. Lokale main was ouder dan de in de eerdere inventarisatie waargenomen GitHub/Fluxrevision 13fba60; actualisering is een latere expliciete reviewstap.

## Scope en huidige status

24 nieuwe reviewbestanden; geen bestaande tracked bestanden aangepast door deze voorbereiding. Bestaande vijf Dashy-verwijderingen, wijziging van kubernetes/apps/kustomization.yaml en twee lokale auditdocumenten zijn behouden en niet gestaged. Git-index blijft leeg en HEAD is ongewijzigd.

Alle runtime-, deployment-, WoL-, contract-, Inventory-overdrachts-, pause-, retentie- en shutdownflags zijn standaard false. Ansible verzamelt zelfs geen hostfacts voordat expliciete deploymentgoedkeuring en exact doeladres zijn bevestigd. Er bestaat geen activeringsplaybook. Geen serverinstallatie, account-/keygeneratie, sudoersinstallatie, app-/Fluxwijziging of timerwijziging uitgevoerd. Alle controles in deze fase waren lokaal; server1/2/3/4 zijn niet benaderd.

## Volledige nieuwe bestandslijst

| Pad relatief aan repositoryroot | Functie |
|---|---|
| bootstrap/ansible/backup-v2-prepare.yml | Aparte fail-closed deploymentvoorbereiding, standaard geen hostverbinding |
| bootstrap/ansible/roles/backup_v2/defaults/main.yml | Uitgeschakelde flags en expliciete datasetcontracten |
| bootstrap/ansible/roles/backup_v2/tasks/main.yml | Alleen later goedgekeurde bestanden/config/units voorbereiden; geen accounts, keys of servicemanipulatie |
| bootstrap/ansible/roles/backup_v2/files/server2_backup.py | Backup-/guard-/restore-/receiptkern en disabled-first CLI |
| bootstrap/ansible/roles/backup_v2/files/server3_backup_control.py | Beperkte JSONcontrolsessie, vaste mount/UUID/RAID, boot-ID, lock en lease |
| bootstrap/ansible/roles/backup_v2/files/server3_backup_forced.sh | Forced-commandpoort; geen vrije remote shell |
| bootstrap/ansible/roles/backup_v2/templates/config.json.j2 | Niet-geheime server2-config, alle capabilities uit |
| bootstrap/ansible/roles/backup_v2/templates/server3-config.json.j2 | Niet-geheime server3-config, control en power uit |
| bootstrap/ansible/roles/backup_v2/templates/server2-backup-v2.service.j2 | Oneshotvoorstel met private bounded noswap-tmpfs en sandbox |
| bootstrap/ansible/roles/backup_v2/templates/server2-backup-v2.timer.j2 | 03:30 UTC-voorstel, geen Install-sectie/activering |
| bootstrap/ansible/roles/backup_v2/templates/server2-backup-v2-status.service.j2 | Niet-schrijfbare freshnesscontrole |
| bootstrap/ansible/roles/backup_v2/templates/server2-backup-v2-status.timer.j2 | Inactief hourly-statusvoorstel |
| bootstrap/ansible/roles/backup_v2/templates/server3-backup-control.sudoers.j2 | Alleen reviewtemplate, één argumentloos helper-entrypoint |
| bootstrap/ansible/roles/backup_v2/templates/backupctl.authorized_keys.j2 | Alleen reviewtemplate, geen key ingevuld of geïnstalleerd |
| bootstrap/backup-v2/README.md | Codegrenzen, lokale verificatie en vrijgavevoorwaarden |
| bootstrap/backup-v2/validate_local.py | Eén lokale validator zonder deployment/netwerk |
| bootstrap/backup-v2/tests/test_backup_v2.py | Synthetische veiligheids-/restore-/lease-/recoverytests |
| bootstrap/recovery/README.md | Onafhankelijke recoveryset en geïsoleerd server4-oefenplan |
| bootstrap/recovery/recovery-set.example.json | Leeg manifest met references/placeholders, geen geheimen |
| bootstrap/recovery/recovery_set.py | Offline plan-/artefactchecker; geen acquisitie/ontsleuteling/restore |
| docs/server/backup-automation-v2.md | Goedgekeurd ontwerp als reviewdocument, niet als runtimewaarheid |
| docs/server/disaster-recovery-v2.md | Volledig server2-verlies: schone herbouw en apart clusterstateherstel |
| docs/server/postkamer-backup-verification.md | Bestaand fase-2-bewijs snapshot f56bfb92; geen nieuwe snapshot gemaakt |
| docs/server/backup-v2-code-review.md | Dit overzicht en precieze beperkingen |

## Wat de code doet en wat nog ontbreekt

De core implementeert consistente SQLite-export, matching k3s-config-/keyinventaris vóór/na export, SFTP-Restic met vaste identiteiten, begrensde netwerk-/procesacties, afzonderlijke restores, inhoud-/native checks, full-data repositorycheck en complete vijf-datasetbundelreceipts met readback. Elke fout verhindert verified status; productie-CLI weigert defaultconfig vóór netwerk of brondata-access. SSHconfig wordt niet geërfd; target, hostkeys en credentialsbestanden zijn expliciet.

Forgejo- en recoveryadapters consumeren alleen een **apart voorbereide en root-only gesealde export** op noswap-tmpfs. Zij produceren die export niet zelf. De Forgejo-schrijffence/resume-watchdog en de goedgekeurde acquisitie/escrow van herstelmateriaal zijn **nog niet geïmplementeerd of runtimegevalideerd**: dit zijn expliciete review-/scopegates, geen verborgen hot-back-upclaim. Een seal is een verklaring van een vertrouwde producent. De restored Forgejo-tree krijgt eigen SQLite- en Git-fsckchecks; een recovery-tree krijgt artefact-/inventariscontrole. Dit bewijst geen volledige serverhersteltest.

K3s-recovery_paths staan leeg en de encryption-/rotatie-interlockflags false; de echte keyset en eventuele symlinkcanonicalisatie moeten eerst worden geïnventariseerd. De bestaande root-only Inventory-runner is nog niet opnieuw onderzocht. Automatische alarmbezorging, retentie en poweroff zijn niet aanwezig; freshnesscontrole levert alleen exitstatus. De code kan dus niet als volledig autonome productieketen worden vrijgegeven.

De globale runnerlock staat buiten zijn private tmpfs-namespace; incomplete runs overschrijven geen groen resultaat. De unit vernietigt vluchtige staging bij service-exit. Een operator-owned tmpfs buiten systemd kan op fout staging behouden voor onderzoek. Nooit onversleutelde diskfallback, blind hergebruik of snapshotverwijdering.

## Lokale validatie: geslaagd

Reproduceerbaar commando:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 bootstrap/backup-v2/validate_local.py
```

- **45 synthetische tests**: disabled-before-network, verkeerde bestemming/UUID, geen string-truthiness, verboden Resticacties, default WoL uit, read-only SQLite-export, consistente Online Backup tijdens WAL-writes, guardverlies, corrupte SQLite/restore/repository/receipt, ontbrekende dataset, geen groen bij disabled/stale/partial, sidefiles/symlinks, lease-eigenaar/expiry/bootwissel/lockconflict en offline recoveryartefacten.
- AST/syntax van Python, shellsyntax, YAML en StrictUndefined Jinja/JSON-rendering.
- Ansible `--syntax-check`; geen playbookrun, facts, SSH of check-mode tegen servers.
- `visudo -c -f` op uitsluitend een tijdelijk gerenderd bestand, geen installatie.
- `systemd-analyze verify` op tijdelijke units. Alleen de verifierkopie van ExecStart wijst naar de aanwezige Python-interpreter; de productieunit is niet geïnstalleerd of gestart. Geen daemon-reload.
- Alle gerenderde defaults false; unittemplates hebben geen Install-sectie; deploymenttasks bevatten geen account-, key-, sudoers-, apt- of systemdacties.
- Gitdiff-whitespacecheck en behoud van bestaande wijzigingslijst/HEAD/index gecontroleerd.

Tests werken in tijdelijke directories met synthetische data en een repositorytestdouble. Ze bewijzen geen echte SFTP-encryptie, RAID/WoL-/stroomgedrag, productie-sandbox, live Forgejo-fencing, credentialherstel of bare-metalrestore. De vroegere fase-2-test blijft het afzonderlijke echte Postkamerbewijs.

## Nodige afzonderlijke besluiten en vervolgstappen

1. Beoordeling van deze branch; afzonderlijk akkoord voor eventueel commit/push. Tot dan alles lokaal en unstaged.
2. Actuele remote bron veilig integreren zonder bestaande lokale wijzigingen te verliezen; geen oude manifests uit deze branch automatisch uitrollen.
3. Root-only Inventory- en k3s-herstelafhankelijkheden inventariseren; productiecontracten, secretacquisitie/escrow en source-metadata vastleggen. Geen sleutels/credentials aannemen uit placeholders.
4. Apart akkoord voor Forgejo-maintenance/fencing/watchdog en implementatie/validatie van die producent. Zonder dat akkoord geen pauze of valse consistente back-up.
5. Apart akkoord voor server3-account, controlkey, forced-command-/sudo-rechten, hostkeyprovisioning en deployment. Die templates zijn nu niet door Ansibletaken geactiveerd.
6. Server4-identiteit, IP, testdisk en netwerkisolatie bevestigen; onafhankelijke recoveryset aanleggen en een herstelproef zonder server2 ontwerpen/uitvoeren. Geen server4-installatie of wipe door huidige code.
7. Pas na handmatige volledige ketentest: Inventory-timeroverdracht, nieuw timerschema en onafhankelijk alarmkanaal apart goedkeuren. Shutdown en retentie vereisen later bovendien eigen implementatie/review en expliciete activeringstoestemming.

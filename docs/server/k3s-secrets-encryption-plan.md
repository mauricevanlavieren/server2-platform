# Server2 — k3s secrets-at-rest encryptieplan

Datum: 9 oktober 2026. **READY** ontwerp/configfragment; **DISABLED** niet uitgevoerd; **BLOCKED** externe consistente recovery-set, geteste rollback en actuele root-preflight ontbreken; **UNTESTED** uitvoering/herstel. Advies: **uitstellen**. Algemene dataverliesacceptatie autoriseert deze datastorewijziging niet.

## Feiten en onzekerheden

VERIFIED vandaag: mau2, k3s v1.36.4+k3s1, node Ready, circa 6,3GiB beschikbaar RAM en 210GiB vrije rootdisk, Flux Ready op commit 3573639. CLI-help bevat enable/rotate-keys/reencrypt. Eerdere audit bevestigde SQLite/Kine en `Disabled, no configuration file found`. De status is vandaag niet opnieuw geverifieerd: read-only `sudo -n ... status` vraagt wachtwoord. Geen sudoers toegevoegd en geen authenticatieomweg gebruikt.

Effectieve k3s flags/environment/configmerge zijn niet volledig secretvrij opnieuw vastgesteld; configfragment mag daarom nog niet deployed worden. Aanwezige CA/token/databasewaarden zijn niet gelezen. Voorffected Secret-inventory alleen metadata nodig, geen dumps van Secret-data. Alle core/v1 Secrets vallen onder de toekomstige k3s-provider, inclusief Flux Git-auth, Helm-release-secrets en later Forgejo-runtime/TLS/SOPScredentials. Exact actuele aantallen/namen zijn niet opnieuw opgevraagd.

## Ondersteunde procedure en versie

De actuele k3s-documentatie beschrijft enablement op een bestaand single-servercluster vanaf de maart-2026 releases. Deze omgeving is nieuwer; beschikbare CLI bevestigd. Voor productie alsnog exacte versieprocedure in geïsoleerde omgeving testen. Geen legacy prepare/rotate-serie mengen met de huidige procedure.

Volgorde na alle gates en **afzonderlijk uitvoeringsakkoord**:

1. Bevestig Disabled/no-configstatus en leg passende pre-change recovery-set extern vast.
2. Voer `k3s secrets-encrypt enable` uit.
3. Voeg `secrets-encryption: true` toe aan de gecontroleerde effectieve serverconfig; herstart k3s.
4. Verwacht tussenstatus Disabled, stage start, matching hashes; stop bij afwijking.
5. Voer `k3s secrets-encrypt rotate-keys` uit; wacht op voltooiing van reencryption.
6. Herstart opnieuw met dezelfde configuratie; eindstatus Enabled, reencrypt_finished en matching hashes.

Deze stap herschrijft ook bestaande Secrets; uitsluitend config activeren is onvoldoende om alle bestaande records beschermd te verklaren. Geen handmatige `kubectl get secrets | replace`-pipeline. [Officiële k3s-procedure](https://docs.k3s.io/cli/secrets-encrypt).

## Declaratieve voorbereiding via Ansible

`bootstrap/ansible/examples/k3s-encryption-config.yaml` is alleen een niet-gerefereerd fragment, bedoeld voor later gecontroleerd configdrop-in. Geen uitvoerbaar enablementplaybook voorbereid: huidige config en rollback zijn onvoldoende vastgesteld. De toekomstige role moet achter expliciete approval/recovery/testasserties de config mergen, twee gecontroleerde restarts doen en statusgates uitvoeren. Nooit volledige config.yaml overschrijven of k3s-installplaybook gebruiken als encryptieprocedure.

Behoud standaardprovider `aescbc`; geen providerwissel tegelijk met initieel enablement. K3s bewaart providerkeys in `/var/lib/rancher/k3s/server/cred/encryption-config.json`. Dit bestand niet in Git of logs en nooit hier uitlezen. [K3s encryptieconfig/provider](https://docs.k3s.io/security/secrets-encryption).

## Preflight — alle punten verplicht

- [ ] Juiste host/context/version; console/SSH-beheer buiten Kubernetes beschikbaar.
- [ ] Effectieve secretvrije flags/config/drop-ins veilig geverifieerd, geen conflicting CLIoverride.
- [ ] Actuele Disabled-status en Secret-metadata-inventory; geen secretvalues dump.
- [ ] Rootfilesystem en SQLite vrij van bekende fouten; voldoende ruimte voor rewrites/WAL en recovery. Vrije ruimte alleen bewijst geen diskgezondheid.
- [ ] Consistente pre-change SQLite + token + TLS/effectieve config extern versleuteld vastgelegd en integriteit gecontroleerd.
- [ ] Onafhankelijke toegang tot recoverykey/token/config plus exacte k3s-binary.
- [ ] Exact-version proef inclusief enablement, twee restarts, bestaande dummy-Secretmigratie, onderbroken operatie en restore geslaagd.
- [ ] Toekomstige backupallowlist uitgebreid met encryption-config en noodzakelijke rotatiemetadata; de huidige runner bevat niet de volledige server/cred-directory.
- [ ] Flux/secretproducerwijzigingen en keyrotaties gedurende change gecoördineerd; geen overlappende upgrades.
- [ ] Eigenaar keurt maintenancewindow, herstelpunten en dataverliesgrens expliciet goed.

Er is nu geen externe backup; deze checklist is dus niet voldaan. Een lokale kopie op dezelfde SSD is geen voldoende onafhankelijke terugweg.

## Downtime en risico's

Plan twee k3s-restarts. API/Flux/controllers zijn tijdens restart niet beschikbaar; single-node heeft geen failover. Bestaande containers kunnen deels blijven draaien, maar continuïteit van DNS/ingress/apps niet garanderen. Reserveer een onderhoudsvenster van 30–60min inclusief controles; echte outage per restart eerst meten, geen geteste RTOclaim.

Reencryption veroorzaakt databasewrites en WALgroei. SQLitecorruptie, verkeerde token/configgeneratie, stroomuitval of keyverlies kunnen API/Secrets ontoegankelijk maken; dit raakt Fluxauth en toekomstige appcredentials. Volume/appdatabases worden hierdoor niet versleuteld. SOPS beschermt Git, Restic beschermt backups, k3s-provider beschermt Kubernetes Secretrecords: afzonderlijke grenzen, geen bescherming tegen cluster-admin/root of plaintext APItoegang met rechten.

## Herstelmateriaal en rollback

Bewaar versleuteld en passend per generatie: SQLite-datastore, server token, CA/TLSmateriaal, effectieve k3sconfig/version en bij encryptie encryption-config/vereiste credentialmetadata. Token beschermt bootstrapdata; keyfiles/token mogen niet willekeurig uit andere checkpoints worden gecombineerd. K3s backupdocumentatie vereist database en matching token. [K3s backup/restore](https://docs.k3s.io/datastore/backup-restore).

Rollback is geen simpel verwijderen van `secrets-encryption` of een configdrop-in. Met gezonde API en behouden keys is ondersteund decrypt/disableherstel mogelijk; het vergt opnieuw rewrites/restart en moet vooraf getest zijn. Officiële disable/restart/`reencrypt --force --skip`-procedure niet als automatische noodactie uitvoeren. Zonder werkende API/keys: k3s stoppen en een volledige coherente, bewezen pre-change recovery-set in schone directories herstellen met oude effectieve config/version; huidige WAL/SHM niet mengen. Alle sinds checkpoint geschreven objecten kunnen verloren gaan.

Verloren decryptiesleutels zijn niet te herstellen door nieuwe keys te genereren. Na geslaagde enablement een nieuwe consistente externe recovery-set maken; vóór pruning/rotatie aantonen dat oude snapshots nog passende keys hebben. Configrollback alleen wordt niet als voldoende herstel geaccepteerd.

## Verificatie en stopcriteria

Status Enabled + reencrypt_finished + matching hashes, API/node/corepods/Flux gezond, bestaande Secretconsumerfunctionaliteit goed. Geen Secretwaarden tonen. Op geïsoleerde dummydata aantonen dat bestaande records daadwerkelijk zijn gemigreerd en restore na restart werkt; status alleen is geen bewijs voor alle records. Voor echte raw-datastoreverificatie is aparte scoped toestemming nodig; niet uitgevoerd.

Stop bij onverwachte stage, rewritefout, APIverlies, hashmismatch of ontbrekend recoverymateriaal; niet blind forceren/keys verwijderen. Huidig besluit: geen encryptie-uitvoering vragen voordat externe backup en testrollback beschikbaar zijn. Forgejo blijft uitsluitend niet-kritische testapp; een eventuele testinstallatie zonder datastoreencryptie vereist expliciete acceptatie van opgeslagen app/TLSsecrets op ongeëncrypteerde datastore.

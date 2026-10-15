# Onafhankelijke recoveryset en server4 — ontwerp

Alleen voorbereiding; geen geheimen verzameld, geen server4-IP verzonnen en geen restore uitgevoerd. De oorspronkelijke server2 en zijn DNS/Forgejo mogen geen noodzakelijke bootstrapbron zijn.

## Bestand en controles

`recovery-set.example.json` bevat uitsluitend verwijzingen/placeholders. Alle beschikbaarheids-/verificatieflags staan false; server4-identiteit en IP zijn nog onbekend. Kopieer het voorbeeld later naar een privé beheerde manifestlocatie, vul alleen niet-geheime inventaris/locatiereferenties in en wijs naar versleutelde artefacten. Zet geen wachtwoorden of sleutelwaarden in JSON.

```sh
python3 bootstrap/recovery/recovery_set.py plan bootstrap/recovery/recovery-set.example.json
```

Exitcode 2 is verwacht: de ontwerp-set is nog niet gereed. `verify` controleert na aparte voorbereiding lokale artefacthashes en padveiligheid; het opent geen netwerk en ontsleutelt geen secrets. Ook alle groene structurele checks bewijzen geen geslaagd disaster recovery.

## Buiten server2 beschikbaar maken, na afzonderlijke goedkeuring

| Onderdeel | Onafhankelijke plek en bewijs |
|---|---|
| Restic-decryptiesleutel | Eigenaar-wachtwoordmanager + afgescheiden offline herstelkopie; proef vanaf server4 zonder server2 |
| SFTP-hersteltoegang en server3-hostkey | Afzonderlijke read-only herstelidentiteit/veilige beheerroute; huidige backupsvc-key niet als enige kopie op server2 laten |
| Age/app-/registryherstel | Privé escrow, versleuteld pakket; noodzakelijke decryptie-/ontgrendeltoegang buiten alleen diezelfde repository |
| CA-herstel | Publiek certificaat + afzonderlijk versleutelde CA-key en onafhankelijk beschikbare passphrase; geen nieuwe keygeneratie nu |
| GitHubaccount/2FA | Eigenaar recoverycodes/manager; geen afhankelijkheid van Forgejo op server2 |
| Offline Gitbundle | Actuele volledige gewenste refs + eventuele submodule/LFSdata, hash en commit-ID; geen stil verlies van lokale wijzigingen |
| Hostbootstrap | Ubuntu-/k3s-/Resticversies en geverifieerde installatiemiddelen, gekozen Ansiblebasis, netwerk/storage/securityinventaris |
| OCI-images/charts/appbroncode | Gepinde digests, offline artefacten en hashes; bewijs dat pull zonder oorspronkelijke registry werkt |
| Datasetcontracten/receipts | Coherente snapshot-ID's, native checks, PVCmapping, modes/owners en rootconfig-/keyset |

Secretmateriaal wordt niet via Git of deze voorbeeldmanifesten verspreid. Een kopie alleen op server2 of alleen binnen een repository waarvan het wachtwoord verloren is, is geen onafhankelijke recoveryset. Een laptopkopie helpt bij serververlies maar is nog geen onafhankelijk bewijs bij gecombineerd laptop-/serververlies.

## Server4-proef: aparte toestemming vereist

1. Laat eigenaar hostname, IP, fysieke disk en beschikbare capaciteit expliciet bevestigen. Geen server1/2/3 als hersteldoel en geen dubbele mau2/.162-identiteit op het LAN. Wipe/install/boot-/netwerkwijzigingen vereisen expliciete toestemming; deze code voert die niet uit.
2. Gebruik een geïsoleerd VLAN/labsegment en een vooraf goedgekeurde aparte Kubernetes-context. Geen route naar productie-apps of webhooks/mailjobs; alleen noodzakelijke gecontroleerde read-only toegang tot server3. Geen test die productiecontext server2 automatisch hergebruikt.
3. Simuleer server2-onbeschikbaarheid via isolatie van het testpad, zonder server2 uit te schakelen of zijn firewall te wijzigen. Gebruik IP's en offline bundle/OCI-artefacten; schakel server2-DNS/Git/registryafhankelijkheden voor de test aantoonbaar uit.
4. Bewijs eerst onafhankelijke decryptie/toegang. Restore naar een eigen versleuteld testvolume; controleer UUID, hashes, DBs en Gitbestanden. Geen actieve productie-PVC overschrijven.
5. Voer de schone-herbouwroute uit `../../docs/server/disaster-recovery-v2.md` uit, met appwriters en Flux vooraf gegated. Herstel naar nieuwe PVC-UID-/padmapping en de bijbehorende appversies. Oude clusterstate is een afzonderlijke herstelmodus, niet eroverheen kopiëren.
6. Meet RPO/RTO vanaf de daadwerkelijke oefening. Controleer login en Git clone/push op uitsluitend synthetische testdata, Postkamer/Inventorynative integriteit, TLS/DNS/netwerkisolatie en een nieuwe geslaagde back-up-/restoretest.
7. Leg alleen bewijsmetadata vast. Test een foutalarm en een volledig uitblijvende run via een onafhankelijk kanaal. Cleanup van specifiek benoemde testdata/disks uitsluitend met goedkeuring; geen bestaande snapshots wissen.

Voor deze oefening is nog geen planning/timer, netwerktoegang, account, key of sudo-regel aangemaakt. Het voorbereidende Ansibleplaybook kent alleen server2/server3 en kan server4 niet installeren; daarvoor is later een eigen expliciet gereviewde procedure nodig.

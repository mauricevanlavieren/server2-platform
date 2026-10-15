> Reviewbranch 15 oktober 2026: alleen codevoorbereiding. Niets op servers geïnstalleerd of geactiveerd. Zie `backup-v2-code-review.md` voor implementatiestatus en beperkingen.

# Server2 volledig defect — herstelprocedure v2

Datum: 15 oktober 2026. **ONTWERP; volledige bare-metalherstelproef niet uitgevoerd.** Geen toestemming om nu een OS te installeren, services te stoppen of productiegegevens te overschrijven. Server1 blijft uitgesloten. Dit document vervangt bij toekomstige goedgekeurde publicatie de achterhaalde aannames uit het herstelplan van 9 oktober; dat bestaande bestand is nu niet gewijzigd.

## 1. Wat is bewezen en wat ontbreekt

| Materiaal | Bewijs nu | Beperking |
|---|---|---|
| Postkamer f56bfb92 | Verse read-only online export, Restic restore --verify, checksum, SQLite/foreign-keycontrole en aantallen geslaagd op 15 oktober | Geen volledige app-/serverherstelproef op nieuwe hardware |
| Forgejo 4de06f11 | Eerder herstel geslaagd volgens eigenaar; snapshotbestaan bevestigd | Consistentie-/inhoudscontract van die generatie nog niet onafhankelijk opnieuw onderzocht |
| Inventory c4313940 | Eerder herstel geslaagd volgens eigenaar; snapshotbestaan bevestigd | Bestaande root-only runner en volledige herstelset nog te beoordelen |
| k3s 6d82638e | Snapshotbestaan bevestigd; volledige repository-datacontrole tijdens fase 2 geslaagd | Matching token/config/keyset en werkend clusterherstel niet aangetoond |
| GitOps | Actuele GitHub-/Fluxrevision 13fba60f4ff8d3fa9fce58f392cd07d5cc05aa95 bij inventarisatie | Laptopclone ouder, lokale wijzigingen apart; offline bundle en image-escrow nog niet bewezen |
| Toegang en decryptie | Werken nu vanuit bestaande machines | Herstel zonder server2 én zonder oorspronkelijke laptop nog niet bewezen |

Een restic check bewijst geen applicatieconsistentie, compleet herstelpakket of afwezigheid van ongewenste bronwijzigingen. Back-ups van verschillende datasets hebben eigen consistente tijdstippen; kies passende versies, niet willekeurig de nieuwste vier snapshots.

## 2. Onafhankelijke recoveryset — eerst regelen

Buiten de defecte server en buiten alleen diens versleutelde repository beschikbaar houden:

1. Restic-wachtwoord in eigenaar-wachtwoordmanager plus gecontroleerde offline herstelkopie. Niet opnemen in dit document of een commandline.
2. Bereikbare beheer-/hersteltoegang tot server3 met gepinde SSHhostkey. Backupsvc is SFTP-only; herstel vereist geen vrije shell voor dat account, beheercontrole van mount/RAID wel een andere beperkte route.
3. Vaste repository-URL, verwachte repository-ID en filesystem-UUID; deze staan in het automatiseringsontwerp. Gebruik IP-adressen als DNS op server2 defect is.
4. Actuele Git bundle, herstelhandleiding en geverifieerde installatiemiddelen voor de vastgelegde Ubuntu-/k3s-/Restic-versies. Gepinde containerimages, noodzakelijke charts/broncode en checksums onafhankelijk van Forgejo op server2.
5. SOPS-age herstelidentiteit, appsecrets en GitHubaccount-/2FAherstel; CA-private key/passphrase alleen in een goedgekeurde onafhankelijke escrow. RootCA-publiccert kan geen servercertificaat vernieuwen zonder CA-private key.

Ontbrekende decryptiesleutel of back-uptoegang betekent **STOP/BLOCKED**, geen nieuwe lege repository initialiseren en geen dataherstel claimen.

## 3. Eerst incident en hersteldoel vastleggen

- Bevestig dat de oorspronkelijke server2 werkelijk uit of geïsoleerd is. Nooit twee hosts met hetzelfde mau2/.162-/clusteridentiteit tegelijk op het LAN.
- Leg incidenttijd, gekozen snapshots, hashes, versies en verwachte gegevens vast. Bewaar defecte disks ongewijzigd waar mogelijk; formatteren/overschrijven vraagt expliciet akkoord.
- Gebruik nieuwe passende hardware/disk of een vooraf goedgekeurde geïsoleerde herstelomgeving, nooit server1. De nieuwe productieomgeving krijgt pas na identiteitscontrole context server2; een testomgeving vraagt een afzonderlijk expliciet goedgekeurde context en netwerkisolatie.
- Controleer server3-identiteit, hostkey, echte /backup-mount, UUID en RAID voordat iets wordt geschreven. Bij degraded RAID of storagefout: geen automatische reparatie; een eventuele read-only recovery vanaf nog leesbare data vraagt een bewuste aparte incidentbeslissing.
- Selecteer exacte snapshot-ID's met manifest/receipt en contractversie. Gebruik niet blind `latest`. Oude eenmalige snapshots zonder receipt moeten eerst naar staging worden hersteld en handmatig als complete set worden beoordeeld.

## 4. Veilige staging en gegevenscontrole

1. Bereken de omvang van de volledige restore plus uitpak-/verificatiemarge. Gebruik een passende private noswap-tmpfs of een vooraf goedgekeurde versleutelde herstelvolume. De 64MiB-fase-2-tmpfs is alleen voor de kleine Postkamerproef, niet voor een volledige Forgejo-/hostrestore.
2. Stel Restic-wachtwoordfile/SSHkey root-only beschikbaar via de onafhankelijke recoveryset, met StrictHostKeyChecking. Geen secrets in shellgeschiedenis, URLs, envdumps, chat of logs; geen TLS-/hostkeybypass.
3. Open de bestaande repository read-only waar mogelijk, pin de repository-ID en controleer snapshot-/manifestidentiteit. Verwijder of repareer niets in de oorspronkelijke repository.
4. Restore geselecteerde datasets naar afzonderlijke lege testdirectories met `--verify`. Controleer manifesthashes en bestanden, SQLite-integriteit/foreign keys/aantallen, Gitrepository-integriteit en noodzakelijke appbestanden. Controleer juiste snapshotpaden; een restic restore behoudt de oorspronkelijke padhiërarchie onder het target.
5. Vergelijk ownership/modes, image-/schema-versies en secretverwijzingen zonder inhoud te tonen. Bij mismatch niet alvast apps starten of migreren.

Kies vervolgens precies één van de twee herstelmodi hieronder. Combineer geen nieuwe clusteridentiteit met een later eroverheen gekopieerde oude datastore.

## 5. Voorkeursroute: schone GitOps-herbouw met appdataherstel

Deze route vermijdt afhankelijkheid van het succesvol opstarten van de oude k3s-datastore. Hij vereist wel aantoonbaar complete declaratieve configuratie en herstelbare appsecrets.

1. Installeer Ubuntu 24.04 op de expliciet gekozen nieuwe disk. Stel boot/storage/netwerk/SSH in met de gereviewde Ansiblebasis en fysieke console als terugval. Controleer werkelijke NIC-/disknamen en vrije capaciteit. Geen upgrades als onderdeel van dataherstel.
2. Installeer de k3s-versie uit het herstelmanifest, oorspronkelijk v1.36.4+k3s1, en behoud vastgelegde cluster-/service-CIDR's, componentkeuzes en storagepaden. Begin met een nieuwe clusteridentiteit; herstel in deze route niet de oude state.db/token/nodepassword.
3. Bootstrap alleen corecomponenten en Fluxcontrollers. Installeer nog geen actieve GitOps-root die automatisch appwriters start. Maak een hersteloverlay met expliciete gates; de gewone apps-/Forgejo-/Postkamer-/Inventoryreconciliation blijft afwezig of suspend=true. Dit moet vooraf in de geïsoleerde oefening worden bewezen.
4. Haal de geverifieerde Gitrevision uit GitHub of de offline bundle. Herstel SOPS-age veilig via stdin en de noodzakelijke app-/registrysecrets via de gecontroleerde secrets-reconciliation. Installeer geen plaintext Secretbestanden in Git. Vernieuw Flux-deploycredentials via de eigenaar wanneer oude toegang ontbreekt.
5. Maak namespaces en lege PVC's zonder Deploymentwriters. Nieuwe PVC's krijgen nieuwe UIDs en local-pathdirectories. Leg de werkelijke PVmapping vast en herstel datasets naar die nieuwe paden. Kopieer geen oude UID-directory blind naar een ongebruikt pad.
6. Herstel Postkamer/Inventorydatabases uit hun geverifieerde export, Forgejo als coherente DB/repos/files/config-set. Controleer rootless UID/GID en modes (Forgejo 1000:1000 volgens huidige manifests), SQLite-integriteit en Gitbestanden. Geen oude WAL/SHM naast een schone online-exportdatabase leggen. Bewaar kritieke appkeys; regeneratie kan bestaande versleutelde appgegevens onleesbaar maken.
7. Zet apps vast op de image-/schemaversie uit de geselecteerde backup. Start eerst één app onder geïsoleerde toegang. Controleer health, tabellen en functionele lees-/schrijftests met uitsluitend synthetische testdata. Geen schema-upgrade tijdens deze stap.
8. Herstel infrastructure/DNS/Traefik en CAtrust, controleer certificaatgeldigheid/SAN en LAN-beperking. Controleer Postkamer- en Inventoryrecords zonder gevoelige inhoud te loggen; voor Forgejo login, private clone/push/fresh clone en repositoryintegriteit.
9. Geef Flux stapsgewijs vrij op de gekozen geverifieerde Gitrevision. Controleer vóór iedere vrijgave de diff en pruning; een recente main kan nieuwe manifests/images bevatten die niet bij de herstelde dataset passen. Pas daarna een afzonderlijk beoordeelde voorwaartse wijziging naar nieuwere desired state.
10. Maak en hersteltest een nieuwe complete back-upbundel. Verwijder oude backups of defecte disks niet als impliciete afronding.

## 6. Alternatief: bestaande k3s-clusteridentiteit herstellen

Alleen kiezen wanneer SQLite plus token/config/keyset én volledige PVinhoud als passende generatie zijn geverifieerd. Een cluster-DBrestore is niet nodig voor een enkel kapot appbestand.

1. Installeer passende Ubuntu en exact dezelfde k3s-versie met service nog gestopt. Gebruik de daadwerkelijke vastgelegde ExecStart/config, niet een willekeurige nieuwe installerdefault. Plaats nog geen actieve writers.
2. Herstel de consistente SQLite-back-up op de juiste datastorelocatie, bijbehorende server-token en vereiste TLS/config/credentials. Houd oude WAL-/SHM-/journalbestanden uit andere generaties weg. Neem, indien actief, de matching secrets-encryption-config mee. Geen echte tokenwaarden uitschrijven in instructies/logs.
3. Herstel ALLE refererende local-pathvolumes vooraf op hun bijbehorende node/pad/ownership. Controleer dat de cluster-back-up naar dezelfde image-/config-/Secretgeneraties verwijst als de appbackups. Bij ontbrekende set niet starten en uitwijken naar route 5 of extra onderzoek.
4. Behoud mau2-identiteit alleen als de oude host definitief geïsoleerd is. Behandel /etc/rancher/node/password en oude nodeauth expliciet; geen nodeobjecten verwijderen als automatische foutoplossing.
5. Houd externe Git-/registry-/jobroutes geblokkeerd tijdens eerste opstart. **Start k3s pas nadat alle appdata, sleutels, versies en paden vooraf zijn gecontroleerd:** herstelde Pods/Jobs/Fluxcontrollers kunnen onmiddellijk starten. Alleen een gepauzeerde Flux-root is geen betrouwbare blokkade voor bestaande controllers.
6. Als een veilige pre-startgate niet aantoonbaar uitvoerbaar is, is deze herstelroute geblokkeerd. Gebruik de schone route. Geen experimentele agentlessmodus als ongeteste standaardoplossing.
7. Na eerste APIbeschikbaarheid controleer/suspendeer de relevante herstelde reconciliations vóór externe bronvrijgave. Controleer corepods, volumegebruik en appstatus; sta daarna geselecteerde netwerk-/GitOpsroutes stapsgewijs toe en volg route 5 stap 7–10.

Het k3s-token is essentieel bij datastoreherstel; zie https://docs.k3s.io/datastore/backup-restore. Dit ontwerp bevat nog geen gevalideerde uitvoerbare clusterrestorecommandoset. Daarvoor is een geïsoleerde volledige oefening verplicht.

## 7. Slaagcriteria en meetpunten

- Herstel mogelijk zonder defecte server2 en zonder uitsluitend de oorspronkelijke laptop.
- Juiste node/API/corepods; alle bedoelde Flux-reconciliations Ready op de vrijgegeven revision.
- PVC-paden correct, geen lege herinitialisatie of onverwachte schema-/sleutelrotatie.
- Native DB-/files-/Gitchecks geslaagd, functionele apptransactie en login/clone/push bewezen, LAN/TLS/DNS correct.
- Verse volledige externe back-up met geslaagde hersteltest én aantoonbaar ontvangen alarmtest.
- Meet verloren tijdvenster (RPO), tijd tot core, tijd tot iedere app en totale technische hersteltijd. Hardwarelevering, downloads en credentialherstel apart benoemen; geen fictieve 1–2 uur garantie.
- Log bewijsmetadata zonder secrets. Wis alleen expliciet aangemaakte gevoelige staging na succesvolle verificatie en bewaar de resultaten.

## 8. Als server3 of de hele locatie verloren gaat

RAID1 beschermt niet tegen wissen, diefstal, brand, ransomware of verlies van beide servers. Zonder onafhankelijke tweede kopie is dat scenario niet afgedekt. Een toekomstige offline/off-site kopie en aparte delete-/herstelcredentials vragen een afzonderlijk besluit. Verander nu geen backend, retentie of bestaande snapshots.

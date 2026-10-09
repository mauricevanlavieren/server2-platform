# Server2 — Disaster Recovery voorbereiding

Datum: 9 oktober 2026. Status: **READY** runbook/codevoorbereiding; **DISABLED** backupuitvoering; **BLOCKED** externe backupserver; **UNTESTED** end-to-end herstel. Geen bewezen dataherstel. Eigenaar accepteert tijdelijk geen externe backups; laptop/cloud zijn geen verplichte bestemming. Server1 volledig buiten scope.

## 1. Wat is nu herstelbaar?

| Bron/status | Nu mogelijk | Niet gegarandeerd |
|---|---|---|
| GitHub main — VERIFIED repository/Fluxrevision | Gecommitte infrastructure/Flux/gateway-manifests en gedeeltelijke Ansible/scripts opnieuw verkrijgen | Geen volledige geteste OS/securitybootstrap; appdata, clusterstaat en secrets ontbreken. |
| Lokale werkboom — niet gepusht | Zolang laptop/repo intact: nieuwe backupvoorbereiding/docs en Dashyverwijdering beschikbaar | GitHub kent deze wijzigingen nog niet. Geen commit/push uitgevoerd. |
| Serverdisk | Nog aanwezige gegevens kunnen bij logisch incident mogelijk bruikbaar zijn | Geen externe herstelkopie; defect/verlies kan data definitief vernietigen. Geen recoverygarantie uit lokale files. |
| Toekomstig Restic | Na implementatie/backup: passende SQLite/token/config, later appdata | Nu geen repository/snapshots; geen uitvoerbare restorebron. |

Huidige GitHub/Fluxrevision: `53f9a8e05d15afa92e9ce175f46bfde6f0a43acb`, branch main, repository publiek. README bevat historische status/DNS; niet als actuele bootstrapwaarheid gebruiken. Zie `backup-architecture.md` voor reproduceerbaarheid A–D.

## 2. Onafhankelijk recoverypakket — nog te maken

| Materiaal | Functie | Onafhankelijk bewaren |
|---|---|---|
| GitHub login/2FA recovery en eventueel Git bundle | Configbron bij account/internetuitval | Niet alleen op server2 of in lokale Forgejo. Bundle nog niet automatisch gemaakt. |
| Targetadres/IP/TLStrust en read-only hersteltoegang | Backup bereiken zonder k8s-gateway | Buiten defecte server beschikbaar; target mag niet van server2-DNS afhankelijk zijn. |
| Restic decryptiesleutel | Data ontsleutelen | Passwordmanager/offline pakket buiten beide servers; geen inhoud in Git/docs. |
| Matching k3s token/CA/config-set | Bestaande clusterstate openen | Versleuteld bij dezelfde generatie; mogelijke toekomstige encryption-config expliciet inventariseren. |
| Versies/checksums en backupmanifest/receipt | Juiste k3s/DB/app-versie en snapshotselectie | Onafhankelijk herstel van toolbinaries/handleiding. |
| PVC/PV UID, node/path, ownership, appcontract | Datamapping en consistentie | In toekomstige backupmetadata, geen secretwaarden. |
| Ubuntu-medium, console/hostbeheer | Bare-metal basis | Niet afhankelijk van werkende Kubernetes/Flux/Forgejo. |

Verlies van beheer-laptop mag later niet betekenen dat decryptiesleutel of GitHub recovery verloren is. Nu is geen onafhankelijke keyescrow vastgesteld. Zelfstandig encryptiesleutelherstel moet in een oefening worden bewezen.

## 3. Herstelmodi en safeguards

Iedere echte restore/installatie/servicewijziging vraagt afzonderlijk uitvoeringsakkoord. Dit runbook is geen toestemming. Bevestig target `mau2`/.162 en bij Kubernetes iedere opdracht expliciet context `server2`. Testomgeving krijgt eigen expliciete context en geen productienetwerkconnectie; nooit server1.

Selecteer één coherente modus:

- **Bestaande clusterstaat:** exacte geteste k3s-versie, passende SQLite + token/keys/config, oude volume-UID/node/padmapping. K3s stoppen vóór directoryrestore; schone database-directory, geen WAL/SHM uit andere generatie. Apps/Fluxstart moet al vóór startup gecontroleerd geblokkeerd zijn: gerestaureerde controllers kunnen automatisch writers starten.
- **Schone Githerbouw:** nieuwe clusteridentiteit en PVC UIDs, gecontroleerde infrastructurebootstrap en nieuwe dataremapping. Niet daarna alsnog oude datastore overheen leggen. Apps pas vrijgeven wanneer data is gevuld en gecontroleerd; gate/overlay voor Flux moet vooraf zijn getest.

Geen nieuwste-versieupgrade tijdens herstel, geen blind rsync van hele rootfilesystem, SSHhostkeys/kubeconfig/nodepasswords niet zonder bewuste identiteitskeuze overzetten. Productiebron niet overschrijven voordat schaderisico en staged restore zijn beoordeeld. Herstelomgeving versleuteld of aantoonbaar private niet-swappende tmpfs; geen plaintext export/logs.

## 4. Scenario A — Applicatiedatabase of bestanden beschadigd

**Nu:** zonder externe backup geen gegarandeerde rollback. Inventariseer read-only scope, bewaar bestaande toestand waar mogelijk via afzonderlijk goedgekeurde actie; ga geen vermeende backup herstellen die niet bestaat.

**Later benodigd:** complete appgeneratie met native DB-export, coherent fileset, versie en PVCmapping, Restic-key. Appbackupcontract is nog niet geïmplementeerd; huidige clusterbackup dekt appdata niet.

Volgorde na akkoord: laatste gezonde generatie kiezen → appschrijvers/jobs/ingress gecontroleerd pauzeren met Fluxafstemming → restore naar aparte locatie → native DBimport plus passende fileset → DB-integriteit, bestanden/rechten en appchecks → cutover → schrijvers/reconciliation hervatten → nieuwe complete externe backup.

Risico: verschillende DB/files-momenten, dubbel uitgevoerde jobs of besmette herstelgeneratie. Cluster intact laten bij uitsluitend appincident.

## 5. Scenario B — PVC verwijderd

**Nu:** bij local-path Delete-reclaim kan directory al weg zijn; Git kan PVCdefinitie opnieuw aanmaken maar niet de inhoud terugbrengen. Geen databehoud aannemen.

**Later benodigd:** externe appbackup, PVC/PV/pad/ownerinventory en appcontract. Volgorde: writers/Fluxhercreatie blokkeren → goede backup selecteren → nieuwe PVC gecontroleerd aanmaken → nieuwe UID/node/directory vaststellen → data en matching DB naar nieuwe mapping herstellen → mount/rechten/appcheck → vrijgave.

Risico: oude UID-directory blind gebruiken, lege appinitialisatie of overschrijven van gezonde data. Retain is eventuele latere extra maatregel, geen externe backupvervanging; nu niet wijzigen.

## 6. Scenario C — k3s SQLite-datastore beschadigd

**Nu:** Git kan desired manifests reconstrueren, niet automatisch alle runtimeobjecten, secrets of historische clusterstaat. Zonder consistente backup/token kan exacte state verloren zijn. Stop niet automatisch k3s en voer geen live databasekopie uit.

**Later benodigd:** succesvolle cluster-candidate **met receipt**, manifesthash, standalone SQLite-clone, matching token/TLS/effectieve config, geteste k3s-versie, passende volumes.

Volgorde na onderhoudsakkoord:

1. Host/filesystemgezondheid en corruptiescope vaststellen; huidige toestand veilig behouden waar nuttig.
2. K3s stoppen en autostart/writers blokkeren via geautoriseerde procedure.
3. Receipt wijst een succesvol snapshot-ID aan; manifesthash en clonedatabase-integriteit in staging controleren. Geen candidate-only snapshot selecteren.
4. Passende recovery-set en schone datastore-directory herstellen. Clone uit Online Backup API krijgt **geen** originele WAL/SHM naast zich.
5. Volume/appstart- en Fluxinterlock voorbereiden; exact passende k3s starten.
6. API/node/corepods/PVmapping en appdata controleren, daarna writers/Flux vrijgeven en nieuwe backup.

Risico: token/DB-generatiemismatch, oude WAL, automatisch herstartende apps, appdata met ander consistentiepunt. Dit is SQLite, geen etcd-snapshotrestore. Online wrapper specifiek voor k3s moet eerst getest worden. [k3s backup en tokenvereiste](https://docs.k3s.io/datastore/backup-restore).

## 7. Scenario D — SSD defect

**Nu:** nieuwe SSD + Ubuntu + GitHub kunnen een gedeeltelijke infraherbouw ondersteunen. SQLite/secrets/PVC/appDB zonder externe backup verloren; handmatige SSH/UFW/resolver/accountbootstrap blijft nodig. Geen volledig automatisch of exact herstel claimen.

**Later:** SSD/Ubuntu-medium, hostbeheer, extern recoverypakket, gepinde Gitrevision/bundle, k3s/recovery/appbackups. Volgorde:

1. Defect bevestigen, nieuwe disk plaatsen, geteste Ubuntu/LVM/ext4basis installeren; hardwarebeschikbaarheid apart tellen.
2. Hostnetwerk/tijd/account/SSH/UFW vanuit gereviewde IaC plus nog gedocumenteerd handwerk. SSHfingerprint via console verifiëren.
3. Target onafhankelijk van cluster-DNS bereiken; GitHub of offline bundle verkrijgen, binaries/checksums verifiëren.
4. Eén herstelmodus kiezen; k3s/config/token en noodzakelijke volumes volgens die modus herstellen, writers vooraf blokkeren.
5. Infrastructure/DNS/Traefik en daarna apps/Flux gecontroleerd vrijgeven; integriteit, securitybaseline en eerste externe backup controleren.

Risico: onvolledige Ansiblebasis, onbeschikbare keys/installerbestanden en volumeidentiteit. Nieuwe backupcode in lokale werkboom is zonder commit/push niet op GitHub aanwezig.

## 8. Scenario E — Volledige server verloren / nieuwe hardware

**Nu:** dezelfde dataverliesgrens als D. Nieuwe hardware maakt aanwezige Gitconfig niet automatisch een complete serverbackup.

**Later:** procedure D plus hardware/capaciteit/architectuur en node/netwerkidentiteit controleren. Nieuwe NIC/disknamen niet blind overnemen. Bij andere nodenaam oude local-path mapping en k3s-nodeauth expliciet toetsen; waar passend schone Gitmodus met dataremapping gebruiken. Geen router-/IPwijziging zonder toestemming. Hardwarewachttijd niet verbergen in RTO.

Risico: enige toekomstige backupserver kan bij gedeelde locatie ook verloren gaan. Een tweede onafhankelijke off-site/offline kopie blijft een latere keuze; geen volledige disastercoverage met twee servers in hetzelfde gebouw claimen.

## 9. Scenario F — Backuprepository gecompromitteerd

**Nu:** externe repository bestaat niet; later één append-only target beschermt tegen brondelete, niet tegen target-rootcompromis of diskverlies.

Voor volledig herstel vereist: onafhankelijke gezonde kopie met aparte credentials/keys, niet verwijderbaar door gecompromitteerde accountlaag. Zonder die kopie scenario F **BLOCKED/ongedekt**.

Later volgorde: incident isoleren en retentie stoppen via akkoord → scope (bron/upload/admin/masterkey) bepalen → aantoonbaar schone onafhankelijke generatie kiezen → op schone beheeromgeving inhoud controleren → passende A/C/D/E procedure → credentials vervangen. Gestolen masterkey vraagt nieuwe repository/masterkey, niet alleen veranderd wachtwoord. Append-only en succesvolle `restic check` bewijzen geen schone brondata of veilige timestamps.

## 10. Verlies van GitHub-toegang

**Nu:** aanwezige lokale clone bevat committed Gitgeschiedenis zolang die disk beschikbaar is. Bestaande cluster kan blijven draaien; Flux kan bronupdates missen. Account/2FA recovery onafhankelijk bewaren. Zonder GitHub én lokale clone ontbreekt de gegarandeerde infrabron.

**Later:** getest offline Git bundle/mirror op backupserver herstellen, pinned revision kiezen en onafhankelijke authenticatie herstellen. Fluxdeploy-key via GitHubaccount opnieuw uitgeven als nodig. GitHubuitval verschilt van accountverlies; permanent alternate remote alleen via goedgekeurde GitOpschange. Geplande Forgejo op server2 mag niet de enige herstelbron voor server2 worden.

Een Git bundle dekt geen database, PVC, token of Kubernetes Secrets. Geen automatisch bundlemechanisme nu voorbereid/geactiveerd.

## 11. RPO/RTO

| Dataset | Nu | Toekomstig doel, pas na meting |
|---|---|---|
| Gecommitte/pushte config | Op GitHub aanwezig; lokale wijzigingen niet extern gegarandeerd | Source/material 30–60min; offline mirror ≤24uur achterstand. |
| Cluster SQLite + recoverykeys | Geen gegarandeerde RPO/RTO | ≤4uur RPO, 1–2uur state-restore na beschikbaarheid host/tools. |
| Appfiles | Geen externe bescherming | ≤24uur RPO; 1–4uur kleine apprestore. |
| Appdatabase | Geen externe bescherming | ≤1uur indien native export/appcontract haalbaar; 1–4uur restore. |
| Forgejo gekoppelde DB/files | Nog niet geïnstalleerd/beschermd | ≤4uur coherent RPO; 2–4uur kleine dataset; schrijfpauze nog besluiten. |
| Volledige host | Alleen gedeeltelijke Gitbasis | 4–8uur werk vanaf beschikbare hardware/backups; aankoop/download/datavolume apart. |

Doelen zijn geen SLA en geen VERIFIED. Single-node heeft volledige uitval tijdens herstel; backups bieden geen HA. Hardwarelevering kan dagen toevoegen. Meet transfer + decryptie + DBimport + provisioning + controles samen.

## 12. Verificatie en end-to-end restoretest

Geen productiebackup, restore of destructieve test in deze voorbereidingsopdracht. Toekomstige tests pas met aparte toestemming, geïsoleerde VM/hardware, eigen context en geen productie-schrijfroutes/webhooks/mailjobs. Geen server1. Bewijsdatum, versions, generation/receipt-ID, datasetgrootte en gemeten RPO/RTO noteren, zonder secrets.

Testvolgorde:

1. Gecontroleerde eerste externe backup, token/keyescrow aantoonbaar onafhankelijk bereikbaar.
2. WAL-schrijfbelasting en cloneintegriteit; matching version/token k3s-restore.
3. Lege testdisk → Git bundle met gesimuleerde GitHubuitval → hostbasis → gekozen k3smodus → volume/apprestore → gecontroleerde Fluxvrijgave.
4. A/B met testdatabase/files/PVC, nieuwe UID/padmapping en native integritychecks. Forgejo later testrepo clone/commit en attachments/LFS verifiëren.
5. Backend offline/full, TLSfout, ontbrekende credentials, exporttimeout en gedeeltelijke Resticrun: duidelijke fout, geen successupdate, geen plaintextfallback; cleanup en appresume bewijzen.
6. Append-only brondelete weigeren, targetonderhoud met correcte receipt/candidate-retentie, stale/failurealarm bij onafhankelijke ontvanger.
7. Scenario F pas na tweede-kopievoorziening testen met primaire repository onbereikbaar en afgescheiden delete/recoverycredentials.

Slaagcriteria: herstel zonder oorspronkelijke laptop/servergeheugenkennis, goede data/rechten/volumes, k3s/API/node/corepods healthy, juiste Gitrevision/reconciliation, DNS/Traefik/TLS goed, apptransactie/integriteit correct, nieuwe complete externe backup en ontvangen alarmtest. Metadata-check alleen is onvoldoende; geen VERIFIED vóór deze concrete uitvoering.

## 13. Vrijgave en stop

Nu geaccepteerd: geen externe dataherstelbescherming. Voor toekomstige activatie: target + credentials/escrow + versie/selectie + volledige tests + retentie/monitoring + expliciet activeringsakkoord. Overige hosthardening en GitHubprivacyafwijkingen eerst rapporteren, niet stilzwijgend corrigeren. Geen live wijziging, commit of push in deze opdracht.

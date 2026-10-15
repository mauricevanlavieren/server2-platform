> Reviewbranch 15 oktober 2026: alleen codevoorbereiding. Niets op servers geïnstalleerd of geactiveerd. Zie `backup-v2-code-review.md` voor implementatiestatus en beperkingen.

# Server2 — Postkamer-back-up en hersteltest

Datum: 15 oktober 2026. Status: **VERIFIED voor de uitgevoerde Postkamer-test**. Geen bewijs van volledig hostherstel of geactiveerde automatisering.

## Uitvoeringsbewijs

De eigenaar heeft `run-postkamer-phase2.py` in de eigen laptopterminal uitgevoerd en sudo rechtstreeks daar geauthenticeerd. Het lokale JSON-resultaat is gelezen en bevestigd:

- Snapshot: `f56bfb925acfe117e0c082e1d3513529c2c6fc47b52764c355d0a5e3b82cf695`.
- Repository: `sftp:backupsvc@192.168.0.186:/backup/restic`.
- Repository-ID: `00c5600469b3306c939434a0e232fb141e844a3931a307a1c0af58e5066fed68`.
- Verwachte /backup-filesystem-UUID: `67837227-f008-4257-822a-b4562efa2daa`.
- Brondataset: Postkamer SQLite, `94208` bytes; bron-PVC `postkamer/postkamer-data`, UID `d2c93712-37bf-42e9-aa68-92105f40d028`.
- Exportmethode: SQLite Online Backup API, bron alleen-lezen geopend; geen applicatiestop.
- SHA-256 van export én herstelde database: `410b347416b00363e06fc6143f5d5e558e47246e23b7fbe3be0bfc1cd4e1ae87`.
- Afzonderlijke restore met `--verify`: geslaagd; manifest identiek.
- SQLite `integrity_check`, foreign-keycontrole en vergelijking van tabelaantallen: geslaagd.
- `restic check --read-data`: geslaagd voor de op dat moment aanwezige repositorydata. Dit bewijst technische leesbaarheid/integriteit, niet automatisch logische volledigheid van alle applicatieback-ups.
- Alle vooraf aangetroffen snapshots na afloop nog aanwezig.
- Tijdelijke gevoelige exports/restores verwijderd, tmpfs ontkoppeld en de runspecifieke stagingdirectory verwijderd.

## Randvoorwaarden en nacontrole

64 MiB begrensde tmpfs met `noswap`, `nodev`, `nosuid`, `noexec` en root-only rechten. Circa 6 GiB RAM beschikbaar vóór uitvoering; bron- en herstelruimte tijdens uitvoering opnieuw gecontroleerd. Geen plaintextfallback naar disk.

Laptop bewaakte tijdens de uitvoering server3-identiteit, mountpoint, UUID, RAID1 met twee gezonde leden en vrije ruimte. De controle hield een werkdirectory op /backup open; server2 accepteerde alleen verse guardberichten. Uitval van de bewaking leidt tot veilig stoppen. Dit is een **handmatige laptop-gecoördineerde proef**, geen laptop-onafhankelijke automatisering.

Nacontrole door agent: dezelfde Postkamer-pod Running/Ready met hetzelfde aantal herstarts (vier; laatste vóór deze proef), PVC Bound, Inventory-back-uptimer actief en laatste service-uitvoering succesvol. /backup nog op /dev/md0 met verwachte UUID; RAID degraded=0, state=clean.

## Wat niet is uitgevoerd

Geen snapshotverwijdering, retentie, appstop, overschrijving van productiegegevens, Gitcommit/push, wijziging van Flux, WoL-proef, shutdown of automatische taakactivering. Server1 niet benaderd.

Niet-gevoelige resultaatmetadata blijft behouden als auditbewijs. De twee tijdelijke helpers en guardmetadata kunnen nog in de runspecifieke gebruikerscache staan; zij bevatten geen credentials of database-inhoud. Het resultaatbestand op /run is metadata en overleeft een reboot niet; de laptopkopie staat in dezelfde outputsmap. Restic-data is versleuteld; de herstelbaarheid blijft afhankelijk van onafhankelijk beschikbare toegang en decryptiesleutel.

Forgejo- en Inventory-hersteltests zijn door de eigenaar als eerder geslaagd gemeld; tijdens deze fase zijn hun applicatierestores niet opnieuw uitgevoerd. De k3s-snapshot is aangetroffen, maar een volledig hersteld cluster is niet getest.

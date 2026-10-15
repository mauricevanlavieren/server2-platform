# Postkamer — lokale demo en containerkandidaat

40 volledig synthetische Nederlandstalige e-mails, SQLite/FTS5, zoeken/filteren, samenvattingen en bewerkbare concepten. Alle voorstellen zijn deterministische voorbeelden, geen echte AI. Geen verzendfunctie, mailconnector naar buiten, API-sleutels of externe runtimepackages.

## Lokaal zonder container

Python met SQLite/FTS5; `.python-version` pint de container/CI-versie 3.13.16. De volledige suite is ook met de aanwezige Python 3.12.3 getest. Node.js is uitsluitend nodig voor de UI-regressiesuite, zonder npm-packages.

```bash
python3 -B -m maildemo
python3 -B -m unittest discover -s tests -v
```

Standaard alleen `http://127.0.0.1:8765`, database `.local/demo.sqlite`. Gebruik `--port 8766` wanneer de bestaande fase-1.1-demo draait. De oorspronkelijke fase-1.1-code en database zijn niet naar dit pakket verhuisd; lokale concepten zijn niet meegekopieerd.

## Configuratie

| Variabele | Lokale standaard | Containerstandaard |
|---|---|---|
| POSTKAMER_BIND | 127.0.0.1 | 0.0.0.0 (alleen IPv4) |
| POSTKAMER_PORT | 8765 | 8765 |
| POSTKAMER_DB | .local/demo.sqlite | /data/demo.sqlite |
| POSTKAMER_ALLOWED_HOSTS | 127.0.0.1:8765,localhost:8765 | hetzelfde |

Binding is uitsluitend loopback of alle IPv4-interfaces. De Host-allowlist staat uitsluitend expliciete loopback-authorities met poort toe, geen wildcard/remote hostname. PATCH vereist dezelfde HTTP Origin. Een afwijkende lokale forwardpoort moet expliciet in de allowlist worden opgenomen. CLI `--port` heeft voorrang en stelt de bijbehorende lokale authorities in; CLI `--db` heeft voorrang op het databasepad. Ongeldige configuratie stopt veilig, zonder waarden of inhoud te loggen.

## Container — uitsluitend lokale fase-10-remediatiekandidaat

Deze lokale branch gebruikt officiële `library/python:3.13.16-alpine3.23`, gepind op de linux/amd64-manifestdigest. Python blijft 3.13.16; libc verandert naar musl en SQLite naar 3.53.4. Zlib 1.3.2-r1 en libseccomp 2.6.1-r0 worden als native stabiele APKs op checksum vastgepind en door apk met de bestaande vertrouwde Alpine-sleutels geverifieerd. Geen `allow-untrusted`, distrovermenging of verwijderde package-inventaris. Buildstappen werken zonder netwerk; Docker kan wel de gepinde base ophalen. Pip/ensurepip blijven verwijderd.

Appcode, synthetische brondata, gebruiker/groep10001, poort8765 en healthcheck blijven gelijk. De bestaande extra IPv6/seccomp-guard uit de platformconfiguratie is ongewijzigd lokaal getest; libseccomp is daarvoor expliciet behouden. Functionele tests, containerchecks en synthetische database-roundtrip naar de oude SQLiteversie slagen. De ongewijzigde securitygate geeft lokaal PASS; dit is geen toestemming voor publicatie of deployment. Zie [lokaal remediatieverslag](../../docs/security/postkamer-remediation-20261015.md).

Alleen lokaal bouwen/testen met een nieuwe eigen tag:

```bash
python3 -B tools/fetch_security_update.py
docker build --platform linux/amd64 --network none -t postkamer-local-remediation:candidate .
python3 -B tools/container_smoke.py postkamer-local-remediation:candidate
```

De smoke-test maakt uitsluitend eigen unieke Docker-containers en een eigen wegwerpvolume, zonder netwerk/poorten, onder 250m CPU en 256Mi. Hij verwijdert deze resources in `finally`; geforceerd doden van het testproces of engine-uitval kan handmatige cleanup van de gerapporteerde eigen namen vereisen. Dit is geen bewakingsframework of Kubernetes-runner.

Voor een later afzonderlijk goedgekeurde lokale bedienbare demo: persistent named volume op `/data`, read-only rootfs, cap-drop ALL, no-new-privileges, 250m/256Mi en uitsluitend een loopback-publicatie zoals `127.0.0.1:8766:8765`; voeg dan `127.0.0.1:8766,localhost:8766` toe aan POSTKAMER_ALLOWED_HOSTS, naast de interne health-authority `127.0.0.1:8765`. Een Docker-bridge verleent normaal egress; voor gegarandeerd egressloos interactief gebruik is aanvullende gecontroleerde lokale netwerkconfiguratie nodig. De geautomatiseerde test gebruikt daarom `--network none`.

## Gegevens en herstart

`data/messages.json` is de reproduceerbare synthetische bron; deze blijft onveranderlijk. De schrijfbare SQLite-database bevat geïmporteerde berichten, zoekindex en bewerkte concepten. Herimport is idempotent en behoudt concepten. **Altijd expliciet opslag op /data mounten wanneer conceptbehoud nodig is.** Een container zonder volume verliest concepten bij containervervanging; een Kubernetes emptyDir verliest ze bij podvervanging. Geen stilzwijgende resetknop of databaseverwijdering.

Stop de applicatie vóór een consistente SQLite-backup; kopieer uitsluitend het eigen databasebestand naar een beveiligde backup. Een lokale named volume of single-node local-path PVC is geen backup. Geen meerdere replicas/writers; Kubernetes gebruikt Recreate. Schema-migratie en backwards compatibility moeten vóór latere upgrades afzonderlijk beoordeeld worden.

## CI en security

De geneste `.github/workflows`-bestanden zijn historische bronprovenance en activeren geen CI vanuit deze applicatiemap. Het nieuwe Postkamer-ontwerp in server2-platform/PR #5 staat nog uit en is in fase10 niet gewijzigd of gemerged. De oude publicatieketen blijft intact. Lokaal is Trivy0.76.0 met dezelfde verse database op origineel en kandidaat gebruikt: 45 blokkerende matches versus0; volledige package-inventaris en ongewijzigde gate behouden. Geen ignore-unfixed, suppression, nieuwe risicoacceptatie, registrylogin, push of deployment. Een lokale groene scan is geen uitputtend bewijs van afwezigheid van kwetsbaarheden of productieacceptatie.

## Deploymentgrens

Fase10 wijzigt geen server, manifest, Flux-resource, bestaande deployment of gepinde registrydigest. Deze nieuwe kandidaat staat uitsluitend lokaal, is niet gepubliceerd en heeft geen nieuwe GHCR-digest. Afzonderlijke toestemming en review zijn nodig vóór enige publicatie, merge of productieactie. Tests gebruikten uitsluitend synthetische data en eigen tijdelijke lokale containers/volumes; geen productiedatabase of credentials. Bestaande dataherstel- en toegangsprocedures blijven afzonderlijk van deze image-remediatie.

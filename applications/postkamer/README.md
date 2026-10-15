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

## Container — voorbereide kandidaat, securitygate nog FAIL

De Dockerfile gebruikt officiële `library/python:3.13.16-slim-trixie` met een geverifieerde **amd64-manifestdigest**. Geen apt/pip-installatie, externe runtimepackages of downloads tijdens buildstappen. Docker haalt wel de gepinde base op. Bron en fixture zijn expliciet gekopieerd; `.dockerignore` sluit overige bestanden standaard uit. Gebruiker/groep 10001, containerpoort 8765. SIGTERM stopt de applicatie gecontroleerd. Healthcheck: `python -B -m maildemo.healthcheck` controleert SQLite/FTS5, 40 berichten en uitgeschakeld verzenden/externe AI. De healthcheck gebruikt uitsluitend loopback en negeert proxy-environmentconfiguratie.

Alleen lokaal bouwen/testen:

```bash
docker build --platform linux/amd64 --network none -t postkamer:phase2 .
python3 -B tools/container_smoke.py postkamer:phase2
```

De smoke-test maakt uitsluitend eigen unieke Docker-containers en een eigen wegwerpvolume, zonder netwerk/poorten, onder 250m CPU en 256Mi. Hij verwijdert deze resources in `finally`; geforceerd doden van het testproces of engine-uitval kan handmatige cleanup van de gerapporteerde eigen namen vereisen. Dit is geen bewakingsframework of Kubernetes-runner.

Voor een later afzonderlijk goedgekeurde lokale bedienbare demo: persistent named volume op `/data`, read-only rootfs, cap-drop ALL, no-new-privileges, 250m/256Mi en uitsluitend een loopback-publicatie zoals `127.0.0.1:8766:8765`; voeg dan `127.0.0.1:8766,localhost:8766` toe aan POSTKAMER_ALLOWED_HOSTS, naast de interne health-authority `127.0.0.1:8765`. Een Docker-bridge verleent normaal egress; voor gegarandeerd egressloos interactief gebruik is aanvullende gecontroleerde lokale netwerkconfiguratie nodig. De geautomatiseerde test gebruikt daarom `--network none`.

## Gegevens en herstart

`data/messages.json` is de reproduceerbare synthetische bron; deze blijft onveranderlijk. De schrijfbare SQLite-database bevat geïmporteerde berichten, zoekindex en bewerkte concepten. Herimport is idempotent en behoudt concepten. **Altijd expliciet opslag op /data mounten wanneer conceptbehoud nodig is.** Een container zonder volume verliest concepten bij containervervanging; een Kubernetes emptyDir verliest ze bij podvervanging. Geen stilzwijgende resetknop of databaseverwijdering.

Stop de applicatie vóór een consistente SQLite-backup; kopieer uitsluitend het eigen databasebestand naar een beveiligde backup. Een lokale named volume of single-node local-path PVC is geen backup. Geen meerdere replicas/writers; Kubernetes gebruikt Recreate. Schema-migratie en backwards compatibility moeten vóór latere upgrades afzonderlijk beoordeeld worden.

## CI en security

`.github/workflows/ci.yml`: gepinde Actions-commits, Python/Node-tests, amd64-build, geïsoleerde container-smoke-test, checksumgeverifieerde Trivy 0.75.0, secretscan, kwetsbaarheidsscan en afgeleid CycloneDX-SBOM. High/Critical/Unknown en ontbrekend scanbewijs blokkeren. Geen `ignore-unfixed`, registrylogin, push of deployment. De bekende kandidaatbevindingen laten deze CI momenteel terecht falen. GitHub-hosted uitvoering en workflowintegratie zijn nog niet bewezen.

## Deploymentgrens

Het aparte platformvoorstel volgt server2-platform/Flux en blijft gesuspendeerd. De final-image is **niet gepubliceerd**: er is dus geen registrydigest om te pinnen. De stagingmanifestwaarde `IMAGE_DIGEST_REQUIRED` is bewust niet deploybaar. Eerst securitygate afronden, publication afzonderlijk goedkeuren, registrydigest verifiëren, manifests renderen en daarna apart toestemming voor deployment vragen.

Geen authenticatie: uitsluitend één vertrouwde lokale operator via een toekomstige `kubectl port-forward --address 127.0.0.1`; geen Ingress, NodePort of publieke URL. Vóór multi-user-/publieke toegang zijn authenticatie, autorisatie en aanvullend serverhardening noodzakelijk. De stdlib-webserver is een begrensde demokandidaat, geen productiegarantie.

## GitHub-staging

Deployment blijft NO-GO; zie SECURITY-STAGING.md. Bevestig eerst de private doelrepository. Geen automatische repositorycreatie, push, imagepublicatie of Flux-activering. Gegenereerde evidence en lokale databases horen niet in broncommits.

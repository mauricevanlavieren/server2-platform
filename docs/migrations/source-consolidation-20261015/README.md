# Broncodeconsolidatie — fase 3, 2026-10-15

Alleen een reviewimport, geen omschakeling. Gebaseerd op server2-platform/main `13fba60f4ff8d3fa9fce58f392cd07d5cc05aa95`, op branch `review/source-consolidation-20261015`. Main, Flux, GHCR, oorspronkelijke repositories en Backup v2 zijn niet aangepast. Geen PR of merge en geen workflowactivatie.

## Bronherkomst

| Repository | Geïmporteerde main-commit | Bronbestanden | Commits in herstelbundle |
|---|---|---|---|
| postkamer | `27654aa482a8cf949ce6c0098dfbbe9b5b4401ec` | 30 | 4 |
| platform-status-api | `b280f48a9f36fb551805b852d4a30654a86d375c` | 9 | 10 |
| git-lab | `3051d06add79a02e544be47c13d6ce994f7607e4` | 3 | 11 |

Alle op het exportmoment geadverteerde refs en bereikbare historische objecten zijn in onafhankelijke age-versleutelde Git-bundles buiten repositories bewaard. Decryptie, bundle verify, verse mirrorrestore, fsck en exact gelijke refs/objectsets zijn lokaal getest. Broncommits zijn niet herschreven; deze reviewbranch bevat een snapshotimport. Alle oorspronkelijke historie staat in de herstelbundles, niet als toegevoegde server2-ancestry. Bundles, sleutels en operatorlocaties staan niet in deze repo. De operator bewaart de beveiligde locatie in de lokale uitvoeringsrapportage. Kopieën staan op de beheerlaptop: verlies van laptop plus key blijft een risico zonder tweede onafhankelijke kopie.

`file-manifest.json` bevat voor elk van de 42 geïmporteerde bestanden bronrepo/commit/pad/gitblob/mode, oud/nieuw SHA256 en eventuele verandering. Alle lockfiles, Dockerfiles, tests, tools, static assets, requirements en synthetische fixtures uit de drie main-trees zijn meegenomen. De lokale gewijzigde status-api-Dockerfile is uitdrukkelijk niet geïmporteerd; alleen de remote-main-versie.

## Bewaarde andere branches

- postkamer: `main` = `27654aa482a8cf949ce6c0098dfbbe9b5b4401ec`
- platform-status-api: `experiment/failing-test` = `465341c93f602034cab6f3e619c89ecc405bbc5d`, `experiment/quality-gate` = `daceef3ac40144f2b7c43bfb016eb082db7d7e7d`, `main` = `b280f48a9f36fb551805b852d4a30654a86d375c`
- git-lab: `main` = `3051d06add79a02e544be47c13d6ce994f7607e4`

Postkamer-publicatieworkflow gebruikt broncommit `3490406fc55c7e914fa2ea548db2251dae1e656a`; deze is in de bundle aanwezig. Vergelijking met geïmporteerde main toont uitsluitend een verschil in `.github/workflows/test-publication.yml`; runtime/appcode is gelijk vóór de hier beschreven testadreswijziging. Dit is bronvergelijking, geen nieuwe registry-provenance- of productiecontrole.

De uitsluitend lokale git-lab-branch `ci-test` is aanvullend opgenomen en met gelijke refs/objectsets hersteld; deze wijst naar dezelfde commit als bron-main. Er is niets naar de oude bronrepo gepusht.

## Inhoud en publicatiegrens

- Postkamer gaat van een private bronrepo naar deze momenteel publieke reviewbranch zoals in deze fase gevraagd. Alleen gecontroleerde source en expliciet synthetische fixtures, geen echte e-mails of databases. De 40 berichten zijn door README/connector als demo gedeclareerd, hashes/tenant en `.test`-adressen worden in de tests gecontroleerd. Geen lokale concepten, runtimeconfig, credentials of herstelbundles meegenomen.
- Eén intentional verschil: een bestaand intern netwerkadres in een negatieve configuratietest is vervangen door een neutraal documentatieadres. Het testdoel blijft het weigeren van niet-toegestane bindings; de volledige suite blijft slagen. Het oorspronkelijke testbestand blijft terugleesbaar in de versleutelde bundle.
- `.github/workflows` binnen de applicatiemappen bevat uitsluitend originele, niet-actieve bronreferenties. Er wordt geen bestand onder root `.github/workflows` toegevoegd of gewijzigd. Workflows zijn niet aangepast voor monorepopaden of publicatie; niet kopiëren/aanzetten zonder aparte review.
- VIERBACH valt volledig buiten deze consolidatie. Geen bron, workflow of providerinstelling geïmporteerd of gewijzigd.
- Git-bundles zijn Git-herstel, geen complete app/data/LFS/registry/GitHub-issues-backup. De drie bron-trees bevatten geen Git LFS pointers of submodules bij deze controle; externe containerimages en builddownloads hebben een eigen recoverybehoefte.

## Lokale validatie

- Postkamer: Python 3.12.3, 54 unittests geslaagd; daarin de Node UI-regressieharness met 9 cases. Geen live systemen gebruikt.
- Status API: lockfile-installatie met npm ci, lifecycle scripts uitgeschakeld; Node 24.21.0, 2 tests geslaagd. npm audit --audit-level=high: 0 bevindingen op controlemoment. Dit bewijst geen kwetsbaarheidsvrije container.
- Beide Dockerfiles lokaal gebouwd. Postkamer-base gepind; Debian liblzma5-buildinput door bestaande fetchtool op de vaste SHA256 gecontroleerd. Het gegenereerde vendorbestand blijft genegeerd en is geen broncommit.
- Postkamer-container-smoketest: 11 controles geslaagd, waaronder health, non-root, read-only root, resourcegrenzen en conceptbehoud over herstart/vervanging; uitsluitend eigen tijdelijke lokale containers/volume, zonder netwerk/hostpoorten. Geen imagepush of deployment.
- Bronhistories en staged nieuwe bestanden patroonmatig gecontroleerd op keys/tokens/credential-URLs en niet-demo-e-mailadressen. Geen matches in broncontrole. Geen volledige DLP- of kwetsbaarheidsgarantie.

De standaard Git-whitespacecontrole signaleert reeds aanwezige CRLF-regels in de advisories-CSV en lege eindregels in twee status-api-bronbestanden. Deze bytes zijn bewust exact behouden; de snapshotcontrole met CRLF/lege-eindregelherkenning slaagt. Geen bronformattering tijdens deze consolidatie.

## Grenzen en vervolgafhankelijkheden

1. Postkamer-reguliere containersecuritygate was eerder rood; succesvolle unittests/build/smoke zijn geen groen licht voor imagepublicatie of deployment. Geen nieuwe Trivy-vulnerabilityscan/SBOM gemaakt in deze fase; bestaande advisories/securitygate en vaste publicatieworkflow zijn ongewijzigd als bronreferentie meegenomen.
2. De geïmporteerde README/SECURITY-STAGING zijn oorspronkelijke momentopnamen met mogelijk achterhaalde publicatie/deploymentclaims. Lees deze migratienotitie en de actuele canonieke platformconfiguratie; geen oude staginginstructie automatisch uitvoeren. Bestaande consistente SQLite-back-upmethode blijft leidend, niet een oude README-instructie om de applicatie te stoppen.
3. Postkamer-build vereist de vaste officiële Debian-download plus Docker Hub-base; de fetchtool en SHA256 zijn meegekomen, het binaire pakket niet. Onafhankelijke escrow van buildinputs/images blijft vervolgwerk.
4. Status-api Dockerfile gebruikt nog node:24-alpine als veranderlijke tag. Niet in deze import aanpassen; digestpinning en runtimegebruik/consumeranalyse apart beoordelen. Lockfile maakt de npm-dependencies reproduceerbaar, niet de volledige containerbase.
5. CI-working-directories/buildcontexts, package-rechten en eventuele consumeromschakeling zijn nog niet aangepast. Alle bronrepos blijven bestaan; niets mergen, verwijderen of private maken zonder nieuw akkoord.
6. Backup v2 blijft op `a0452266f8a58c7b9d8659fe8bab5c5ae6249c7d`. Server2/main en alle bestaande GitOps-manifests blijven bytegelijk; geen applicatie- of serverwijziging.

# Fase 10 — Postkamer Security Remediation, lokale validatie

Datum: 2026-10-15. Volledige fase-9-rapportage en securitytriage vooraf gelezen. **De nieuwe lokale kandidaat heeft 0 door Trivy gevonden kwetsbaarheden; de bestaande ongewijzigde gate geeft PASS. Productie en de oude image zijn ongewijzigd.** Geen publicatie, Git-commit, push, PR-wijziging, merge, packagegrant, deployment of serveractie uitgevoerd.

## Oorspronkelijk versus kandidaat

| Maatstaf | Originele gepinde image | Eerste Alpine-kandidaat | Definitieve kandidaat |
|---|---:|---:|---:|
| HIGH | 44 | 0 | 0 |
| UNKNOWN | 1 | 0 | 0 |
| CRITICAL | 0 | 0 | 0 |
| MEDIUM | 58 | 1 | 0 |
| LOW | 61 | 0 | 0 |
| Blokkerende pakketmatches | 45 | 0 | 0 |
| Unieke blokkerende advisories | 9 | 0 | 0 |
| Ongewijzigde gate | FAIL/exit1 | PASS/exit0 | PASS/exit0 |

Origineel opnieuw gescand op registrydigest a693c575a290dec1cd857e750c07a6752afd8558de2351e2920e24be37b92773. Alle scans gebruiken Trivy0.76.0 met dezelfde geldige database en zonder ignorefile/status-/severityfilters; database bijgewerkt 2026-10-15T07:10:08Z. Elke scan heeft volledige OS-package-inventaris. Kandidaat heeft30 OS-package-records; APK-database blijft intact. Geen kwetsbaarheden onderdrukt, geen gateversoepeling of nieuwe risicoacceptatie. SBOM lokaal gegenereerd uit het volledige kandidaatrapport.

Lokale definitieve tag: `homelab-phase10-postkamer-guarded:20261015`; Docker-ID `sha256:a94defeb56f180c573eba2e7db4e04e2c66549dc3572c6c2e8777d5297b61206`. Alleen linux/amd64 getest. **Nul gevonden is geen garantie van nul kwetsbaarheden:** distro-advisorydekking, onbekende CVE's en componentbereikbaarheid hebben grenzen. Daarom zijn alle oorspronkelijke negen advisories ook afzonderlijk tegen vendorinformatie, packageversies en werkelijk aanwezige code beoordeeld.

## Gekozen remediatie en behoud

Officiële Docker Library Python3.13.16-alpine3.23, amd64-manifest a237388397d835ba00539990f15487187eacf17d160c21aaa9e951818344f0dd. Python blijft3.13.16; libc verandert van glibc naar musl en SQLite van3.46.1 naar3.53.4. Geen runtime-Python/npm-dependencies toegevoegd. Alleen native stabiele Alpine-packages, geen Debian/unstable-mix.

De eerste kandidaat miste libseccomp die de bestaande productie-entrypoint nodig heeft. Deze regressie is gevonden vóór aanbeveling en in de definitieve kandidaat opgelost met libseccomp2.6.1-r0. De eerste kandidaat had daarnaast zlib CVE-2026-85091 (MEDIUM), opgelost met1.3.2-r1. Beide APKs zijn gepind op versie/URL/SHA256 en door apk tegen de bestaande officiële Alpine-sleutels geverifieerd; geen allow-untrusted, nieuwe trustkeys of netwerk tijdens buildstappen.

Appcode, fixtures, tests, security_gate.py, huidige IPv6-guard, Kubernetes/Flux en workflows zijn ongewijzigd. UID/GID10001, poort8765, Host/Origin-controles, read-only rootfs, cap-drop ALL, no-new-privileges, harde limieten, healthcheck en graceful shutdown behouden. Pip/ensurepip en ongebruikte directe privilegecommando's blijven verwijderd. BusyBox blijft als native Alpine-component aanwezig zonder setuidrechten; dit is een andere implementatie dan de getroffen util-linux-tools. Geen productieconfig aangepast om de kandidaat werkend te krijgen.

## Alle negen advisories afzonderlijk

Een scanner vergelijkt distribueringsadvisories verschillend. De afwezigheid van een Alpine-match alleen bewijst geen reparatie; onderstaande aanvullende onderbouwing voorkomt dat een groene status enkel door een distroverschil ontstaat.

| Advisory / oorspronkelijke matches | Werkelijke remediatie of eliminatie in kandidaat |
|---|---|
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) / 9 | Alpine util-linux-source2.41.6-r1: vendor noemt fix vanaf2.41.6-r0. Alleen libuuid uit die source aanwezig; het getroffen util-linux mount-programma ontbreekt. |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) / 9 | Alpine vendor noemt fix vanaf2.41.6-r1, de aanwezige libuuid-sourceversie. Getroffen nsenter-programma ontbreekt bovendien. |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) / 9 | Geen fixclaim uit de geraadpleegde Alpine-secdb. Het getroffen util-linux mount/subdir-programma en libmount zijn niet in deze runtime aanwezig; alleen libuuid. Kwetsbaar pad dus geëlimineerd door runtimekeuze, geen suppression. |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) / 9 | Alpine vendor noemt fix vanaf2.41.6-r0; aanwezige source2.41.6-r1. Het getroffen mount-programma ontbreekt bovendien. |
| [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369) / 1 | Getroffen libacl/source acl daadwerkelijk niet aanwezig in pakketinventaris of gecontroleerde librarypaden. Python/app gebruikt deze dependency niet. |
| [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) / 4 | Kwetsbaarheid zit in CLI infocmp (progs/infocmp.c); infocmp ontbreekt. Ncurses-libraries6.5_p20251123 blijven voor Pythoncompatibiliteit aanwezig. Niet beweren dat alle ncurses-code gepatcht is; het specifieke getroffen CLI-component is afwezig. |
| [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742) / 2 | Geen systemd-sourcepakketten/libsystemd/libudev of systemd-homed in de runtime. Het homed-privilegepad is daadwerkelijk afwezig. |
| [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538) / 1 | Geen Perl/source perl of Archive::Tar in de runtime; betreffende parser niet meegeleverd. |
| [CVE-2026-82560](https://security-tracker.debian.org/tracker/CVE-2026-82560) / 1 | Geen Perl/source perl of Pod::Text in de runtime. UNKNOWN niet geaccepteerd of genegeerd; getroffen component niet meegeleverd. |

Primaire aanvullende vendorbron: [Alpine3.23 main securitydatabase](https://secdb.alpinelinux.org/v3.23/main.json), lokaal bewaard als alpine-vendor-secfixes.json. Die bevestigt ook zlib1.3.2-r1 voor CVE-2026-85091. Debian blijft voor de oorspronkelijke sourceversies getroffen; het oorspronkelijke image is niet gerepareerd of vervangen. Componenteliminatie in de kandidaat is geen retroactieve false-positiveclaim voor de oorspronkelijke image. Er zijn geen eigen VEX-uitzonderingen of nieuwe acceptaties ingevoerd.

## Alternatieven vergeleken

| Optie | Veiligheid / compatibiliteit | Onderhoudbaarheid | Grootte / besluit |
|---|---|---|---|
| Debian-stable package-/base-update | Minste ABI-wijziging, maar officiële huidige Python3.13.16-slim-trixie resolveert nog naar dezelfde base en vendorstatus verhelpt niet alle negen advisories | Vertrouwd, maar blokkades blijven; geen sid/unstable-pakketten mengen | Origineel hieronder gemeten; niet gekozen als volledige oplossing |
| Zelf samengestelde minimale glibc-runtime / multi-stage | Potentieel bruikbaar; vraagt correcte ELF-/stdlib-/cert-/locale-closure en eerlijke package-inventaris. Geen inventory weglaten om groen te worden | Meer eigen onderhoud en kans op gemiste dependency; niet nodig gebleken | Niet gebouwd; geen grootte- of veiligheidspass geclaimd |
| Bestaand lokaal Chainguard Pythonalternatief | Read-only probe: Python3.15.0, SQLite3.54.0 en FTS5. Grotere interpreterversiesprong; geen volledige appvalidatie of nieuwe image-securityclaim | Afhankelijkheid van ander imagebeleid/versionering | Alleen base bekeken, geen vergelijkbare appimagegrootte; niet gekozen |
| Officiële Alpine3.23 + twee native pinned APKs | Zelfde Python; musl-/SQLitewijziging expliciet getest. Volledige inventaris, originele guard hersteld,0 findings | Reguliere ondersteunde base; twee vaste buildinputs periodiek herbeoordelen | Gekozen als lokale remediatiekandidaat; nog geen releaseacceptatie |

[Officiële Python-image](https://hub.docker.com/_/python) en [bijbehorende Alpine-Dockerfile](https://github.com/docker-library/python/blob/master/3.13/alpine3.23/Dockerfile) bevestigen herkomst en Pythonversie. Alpine gebruikt musl; een toekomstige native Python-dependency vraagt passende wheels/nieuwe compatibiliteitstests.

## Imagegrootte, vergelijkbaar gemeten

Docker-engine gerapporteerde bytes verschillen mogelijk per opslag-/manifestformaat. Daarom zijn beide roots met dezelfde exportmethode, zonder containerstart, gemeten. Dit zijn samengevouwen rootfs-maten, geen belofte over registry-laagtransfer of layerhistorie:

| Meting | Origineel | Definitief |
|---|---:|---:|
| Inhoud reguliere bestanden | 106,687,521 | 38,109,547 |
| Rootfs-tar bytes | 110,347,264 | 39,951,872 |
| Rootfs-gzip bytes, zelfde instellingen | 38,475,808 | 13,112,624 |

Reguliere bestandsinhoud circa 64.3% kleiner. Bestaande images/tags niet verwijderd of overschreven. Eigen tijdelijke meetcontainers/-archives zijn opgeruimd.

## Tests en regressies

- Volledige host-suite54 tests geslaagd, inclusief9 Node UI-controllercases. Geen nieuwe visuele browser-/E2E-claim.
-53 functionele/security/storage Python-tests op de werkelijke Python3.13.16-kandidaat geslaagd; alleen de aparte Node-harness draait op de host, zonder Node in de productie-image te installeren.
- Ongewijzigde11 containerchecks slagen: health, non-root, pip/ensurepip afwezig, read-only root, IPv4-bind, limieten, SIGTERM zonder OOM, draftbehoud bij restart/vervanging, geen egress/gepubliceerde poorten, healthcheck.
- Exacte bestaande IPv6-guard getest: seccompfilterteller1→2; IPv6-socket EAFNOSUPPORT/errno97, IPv4-loopback werkt; capabilities0 en no-new-privileges1 blijven gelijk.
- Exacte productie-entrypoint `/usr/local/bin/python -I -B /guard/ipv4_guard.py` en guarded healthcheck lokaal geslaagd; graceful exit0.
- Synthetische DB-roundtrip: oude SQLite3.46.1 maakt40 berichten/draft; nieuwe3.53.4 leest, zoekt/FTS5 en wijzigt draft; oude3.46.1 leest kandidaatwijziging correct terug. Integriteit en foreign keys OK. Geen productiedata gebruikt.
- TLS/CA-bundle geladen (121 roots), FTS5 aanwezig, uid/gid10001. Geen externe TLS/DNS-dienst of productielast getest.
- Buildinputs: twee geldige pinned payloads geaccepteerd; twee bitflips en oversized input afgewezen. Packagehandtekeningen/versies door apk gecontroleerd tijdens netwerkloze build.
- Secretcontrole0; volledige OS-package-inventaris30, volledige scanrapporten en CycloneDX-SBOM lokaal. Gatecode exact ongewijzigd.

Gevonden en herstelde lokale regressie: ontbrekende libseccomp in de eerste Alpine-kandidaat. Eerste beperkte sandboxrun van tests kon geen loopbacksockets openen; dezelfde ongewijzigde suite daarna in de toegestane lokale testcontext volledig geslaagd. Geen onopgeloste regressie waargenomen in deze tests. Dit vervangt geen geïsoleerde volledige platformherstel-/productieacceptatietest.

## Lokale wijzigingen en grenzen

Alleen een eigen lokale clone zonder remote, nieuwe branch `local/postkamer-security-remediation-main-20261015` vanaf main09168ce8d51017ea223c625f282aa914e70a1a64. Geen commit. Gewijzigd: Dockerfile, .dockerignore, fetch_security_update.py en relevante README-secties; dit verslag ook als lokaal reviewdocument. Appcode, tests, fixtures, securitygate, guard, workflows en manifests ongewijzigd. PR #5 open en ongewijzigd op19572f0a99e0a05283dcb42f4f2f167dff719114. De kandidaatbranch neemt die ongerelateerde workflowvoorbereiding niet over.

Geen GitHub-/architectuurdocumentatie gepubliceerd; geen registry-push, merge, server/Kubernetes/Flux/prodconfig-/package-/visibilitywijziging. Alle bestaande lokale branches en staged/unstaged/untracked wijzigingen behouden. Oude runtime blijft op de oude image. Toekomstige packagegrants, publisherimplementatie/cutover en tweede fysieke herstelkopie uit fase9 blijven open.

## Aanbevolen veilige vervolgstap en toestemming

Beoordeel eerst deze concrete lokale kandidaat en de musl-/SQLiteovergang. Daarna uitsluitend met nieuw expliciet akkoord code/documentatie op een afzonderlijke reviewbranch/PR publiceren; nog geen merge of imagepush. Vervolgens zijn apart goedgekeurde CI-validatie en een geïsoleerde platform-/datahersteltest verstandig vóór enige release/deployment. Geen nieuwe risicoacceptatie nodig voor een overgebleven scanmatch in deze kandidaat: er zijn geen gevonden matches, maar bekende scan-/testgrenzen blijven.

**Toestemming gevraagd: mag uitsluitend deze lokale remediatiecode met verslag als aparte review-PR worden gepubliceerd, zonder merge, registry-push of productieactie?** Tot antwoord stopt fase10.

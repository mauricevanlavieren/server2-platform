# Traefik voor uitsluitend SSH-toegang — gerichte beoordeling

Kandidaat: officiële release v3.7.14; amd64 `docker.io/library/traefik@sha256:5902d68e00708015736416b62faa49d23a2e1d4415649e5831d20b79ba301508`. Binaire Go-versie 1.26.8, x/net 0.59.0, x/crypto 0.57.0. Scan:4 High-matches / 3 unieke advisories, 7 Unknown-matches / 5 unieke advisories; 0 Critical. Deze telling is geen bewijs dat alle codepaden bereikbaar zijn. De scannerresultaten blijven ongewijzigd; geen allowlist/thresholdwijziging of risico-uitzondering.

| Advisory | Bevinding en relevantie | Beoordeling voor dit ontwerp |
|---|---|---|
| CVE-2026-78669 / GO-2026-6611 | HTTP/2 SETTINGS kunnen CPU uitputten; zowel server als client. Twee matches: stdlib en x/net. | PARTIAL: HTTPS kan HTTP/2 onderhandelen en Kubernetes-client gebruikt mogelijk HTTP/2. ALPN alleen HTTP/1.1 plus controle van uitgaande HTTP/2 is een mogelijke mitigatie, nog niet end-to-end bewezen. Loopback/SSH beperkt de aanvallerskring maar verhelpt dit niet. |
| CVE-2026-78667 / GO-2026-6609 | DoS in Go ServeContent/ServeFile/FileServer bij veel Range-segmenten. | PARTIAL: dashboard/API en bestandsserver ontbreken in het tunnelontwerp; Kompasbestanden komen uit Python. Daarmee lijkt het kwetsbare Go-bestandspad ongebruikt. Volledige binaire bereikbaarheid niet bewezen. Range-strippen is aanvullend voorstel, geen patch of testbewijs. |
| CVE-2026-97031 / GO-2026-6607 | Geheugenuitputting bij reconstrueren van ECH inner ClientHello. | PARTIAL: Go 1.26.8 roept decodeInnerClientHello pas na een pad met ECH-decryptiesleutels aan; zonder echKeys retourneert het eerder. Het ontwerp configureert geen ECH-sleutels. Dit is sterke broncode-indicatie, geen bewezen runtimeconfiguratie van de nieuwe proxy. |
| CVE-2026-78659 / GO-2026-6603 | HTTP/2 Trailer-geheugenuitputting; upstream verklaart HTTP/1 niet toepasbaar. | PARTIAL: voorkomen van HTTP/2 is concreet te testen, maar nog niet bewezen voor alle relevante transports. |
| CVE-2026-78660 / GO-2026-6610 | Malformed HTTP/2-responseheaders kunnen bij omzetting naar HTTP/1 response-smuggling geven. | PARTIAL: Kompasbackend is HTTP/1; geen h2c gepland. Andere transports/Kubernetes-client niet als volledig onderzocht presenteren. |
| CVE-2026-94440 / GO-2026-6608 | Multipart/MIME-parsing kan geheugenlimieten omzeilen. | PARTIAL: ontwerp streamt requestbodies zonder buffering/formparser. Geen aangetoonde toepassing, maar geen compleet binair callgraphbewijs. |
| CVE-2026-97030 / GO-2026-6600 | html/template-escaping van yield. | PARTIAL: geen vertrouwde gebruikers-HTML-templatefunctionaliteit in de gekozen proxyroute; compiled stdlib-aanwezigheid bewijst toepassing niet. |
| GO-2026-5932 | Ononderhouden OpenPGP in x/crypto; modulematch bewijst niet dat OpenPGP gelinkt/gebruikt is. | UNKNOWN: TLS/X509 gebruikt geen OpenPGP; plugins/ACME zijn uit. Niet als formeel niet-toepasbaar afmelden zonder aanvullend bereikbaarheidsonderzoek. |

Upstream fixes: Go 1.26.9/1.27.2 voor de betreffende stdlib-advisories, x/net 0.60.0 voor de betreffende HTTP/2-advisories. De huidige gepinde binary krijgt geen Go-librarypatch door enkel Alpine-packages te updaten. Nieuwste officiële GitHub-release opnieuw gecontroleerd: v3.7.14 van 6 oktober 2026. Geen veiliger ondersteund publiek artifact geverifieerd. Chainguard/traefik is niet toegankelijk (registry403); geen toegang of kwaliteit geclaimd. Geen custom build gemaakt.

## Besluit
NO-GO voor de nieuwe proxy/HTTPS-activering zolang de High-codepaden niet afdoende uitgesloten of gepatcht zijn. Alle High-bevindingen zijn inhoudelijk beoordeeld; ontbrekend bereikbaarheid-/mitigatiebewijs wordt niet als PASS behandeld. Minimale veilige voortzetting: bestaande localhostfallback automatisch herstartbaar houden; wachten op een officiële gepatchte build of eerst een apart concreet, bewezen mitigatievoorstel laten beoordelen. Geen bestaande Traefik, globale entrypoints, firewall of andere workloads aanpassen.

Primaire bronnen:
- https://pkg.go.dev/vuln/GO-2026-6611
- https://pkg.go.dev/vuln/GO-2026-6609
- https://pkg.go.dev/vuln/GO-2026-6607
- https://pkg.go.dev/vuln/GO-2026-6603
- https://pkg.go.dev/vuln/GO-2026-6610
- https://pkg.go.dev/vuln/GO-2026-6608
- https://pkg.go.dev/vuln/GO-2026-6600
- https://pkg.go.dev/vuln/GO-2026-5932
- https://github.com/golang/go/blob/go1.26.8/src/crypto/tls/ech.go
- https://github.com/traefik/traefik/releases/tag/v3.7.14

## Uitgevoerde reparatie en certificaatuitgifte
14 oktober 2026: localhost8780 had geen listener; Kompas en Flux waren gezond. Managed laptopuser-service kompas-fallback is enabled/active en bindt uitsluitend 127.0.0.1:8780. Gecontroleerd beëindigen van alleen deze eigen forward leidde automatisch tot nieuw proces en health HTTP200. Geen echte SSH-tunnel geactiveerd; dit blijft kubectlport-forward via bestaande geauthenticeerde Kubernetes-API. Installatie: python3 -I -B operations/it-discovery-access/install-fallback.py. Status/start/stop: systemctl --user status/start/stop kompas-fallback.service; definitief uitschakelen met disable --now. Geen sudo, wachtwoordopslag of clusterresourcewijzigingen.

Eigenaar heeft bestaande CA-passphrase verborgen gebruikt voor één nieuwe Kompas-leaf; CA-bootstrap is NIET opnieuw uitgevoerd. Het publieke certificaat valideert voor kompas.home.arpa, serverAuth en bestaande vertrouwde CA. Geldig 14 oktober 2026 10:52:03UTC tot 12 januari 2027 10:52:03UTC. FingerprintSHA256 4B:8E:B3:1D:AC:A4:50:29:59:C8:66:F8:C7:6B:88:0B:90:4E:05:BE:4A:F0:FE:E9:CE:1F:A5:8D:F5:53:4B:67. CA/private leafkey blijven buiten Git onder de bestaande beveiligde lokale directory. Geen Secret geïmporteerd, bestaande certificaten gewijzigd of nieuwe trust geïnstalleerd. Renewal vooraf door eigenaar; helper weigert bestaande doelbestanden. Geen automatische overschrijving.

HTTPS/DNS/SSH/Ingress blijven BLOCKED/PENDING totdat runtimebesluit en isolatieproeven voldoende zijn. Afzonderlijke loopbackproxy met eigen classannotatie is een inactief concept, geen geleverde productiearchitectuur. Dashy ongewijzigd. Geen globale firewall/Traefik/SSH-wijzigingen. Postkamer ongewijzigd; einde uitzondering 20 oktober 2026 17:19:30UTC.

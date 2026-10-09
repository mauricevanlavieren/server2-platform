# Forgejo — activatie en verificatie

Datum: 9 oktober 2026. Scope uitsluitend server2 (`mau2`, `192.168.0.162`, Kubernetes-context `server2`). De eigenaar gaf breed akkoord voor Forgejo-activering, noodzakelijke Gitwijzigingen/publicatie en Flux-reconciliation. Server1 niet benaderd. Backups, k3s-encryptie, upgrades en firewall/routerwijzigingen niet uitgevoerd.

## Uitgevoerd en gecontroleerd

- Forgejo via aparte Flux-Kustomization geactiveerd, afhankelijk van infrastructure en forgejo-secrets. Eén replica, Recreate; PVC behouden via prune-uitzondering.
- Alle vijf Flux-Kustomizations Ready; node Ready. Rootless Forgejo-pod Running/Ready, geen containerherstarts na de correctie.
- PVC forgejo-data Bound, 10Gi local-path; SQLite-bestand aanwezig. Data-directory schrijfbaar als UID/GID1000. Secretbestanden leesbaar, rootfilesystem niet schrijfbaar. Geen secretwaarden getoond.
- Publieke CA-keten/hostname gecontroleerd; servercertificaat geldig tot 7 januari 2027 12:17:33 UTC. Laptop-systeemtrust werkt. Normale laptop-DNS resolveert forgejo.home.arpa naar 192.168.0.162; gatewayquery eveneens juist.
- HTTPS /api/healthz en /user/login geven 200, TLS-verificatie geslaagd zonder bypass. HTTP geeft 404 en biedt geen Forgejo-login. Registratiepagina meldt dat registratie is uitgeschakeld en bevat geen wachtwoordformulier.
- Traefik-service stond op externalTrafficPolicy Cluster: LAN-aanvragen kregen 403. Declaratieve HelmChartConfig stelt nu Local in, zodat de LAN-allowlist werkt zonder uitbreiding van sourceRange. Dit is een wijziging aan de gedeelde Traefik-service. Traefik blijft Ready zonder nieuwe podherstart; bestaande host/poortinstellingen behouden. Bestaande Dashy HTTP-route opnieuw gecontroleerd: 200.
- Niet-Traefik source-controller → rechtstreeks Forgejo-pod: verbinding geweigerd. Forgejo → extern IP op TCP80: verbinding geweigerd. Controleprobes slagen: dezelfde externe TCP80-bestemming is bereikbaar vanuit source-controller, en Forgejo-localhost health geeft succes. Dit onderbouwt de NetworkPolicy-werking voor deze geteste paden. Geen volledige policy-/firewalltestmatrix; geen bewijs dat elk verboden netwerkpad afzonderlijk getest is.
- Initconfig en JWT Secret-URI gecontroleerd. Eerste JWT was standaard Base64, terwijl Forgejo RawURLEncoding vereist; Forgejo genereerde daardoor een conflicterende inline JWT_SECRET. JWT naar correct URL-veilig formaat zonder padding vervangen vóór gebruikersbootstrap. Overige runtimekeys ongewijzigd; SOPS-roundtrip gecontroleerd. Declaratieve podvervanging verwijderde het conflict. Beheer-CLI nu succesvol; geen beheerdersaccounts aangetroffen.

## Nog niet vastgesteld of uitgevoerd

- Browsertrust, eerste login, beheerdersaccount en authenticated repository clone/push. Eigenaarbootstrap nodig; gebruik bootstrap/forgejo-security/create-admin.sh in eigen interactieve terminal. Willekeurig tijdelijk wachtwoord verschijnt uitsluitend daar en moet bij eerste login worden vervangen. Niet delen in chat of rapporten.
- Volledige denied-path-/client-IP-test vanaf een onafhankelijk netwerk buiten LAN, formele NetworkPolicy-regelinspectie en uitgebreide belastingtest.
- Restore/disaster recovery: niet uitgevoerd. Backups blijven inactief; SSD-/hostverlies kan Forgejo-data onherstelbaar vernietigen. GitHub blijft platformbron. Alleen niet-kritische gegevens gebruiken.
- k3s-datastore-encryptie: uitgesteld. Kubernetes Secrets zijn voor cluster-admin leesbaar; SOPS beschermt Git.
- Onafhankelijke sleutelherstelkopie ontbreekt. Ageidentity en CA-private key herstelmateriaal blijven op laptop; sops-age bestaat daarnaast in het cluster en is geen onafhankelijke recoverykopie.
- Local-path 10Gi is aangevraagde capaciteit, geen harde gebruiksquota. Certificaatvernieuwing vóór bovengenoemde vervaldatum vereist; geen renewalautomation geïnstalleerd.

## Git en grenzen

Appactivering b3fff1a; bron-IP-correctie 1971c88; JWT-correctie fa8127f. Alleen gerichte Forgejo-/Traefik-bestanden gepubliceerd. Lokale Dashy-verwijdering en auditrapporten niet meegenomen. Geen algemene opruiming, geen normale sudo-/SSH-rechten gewijzigd.

Bronnen: [Kubernetes client source IP](https://kubernetes.io/docs/tutorials/services/source-ip/), [k3s ServiceLB](https://docs.k3s.io/networking/networking-services), [Forgejo v15.0.9 JWT decode](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.9/modules/generate/generate.go).

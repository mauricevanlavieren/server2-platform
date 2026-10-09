# Server2 — Forgejo via Flux: ontwerp en deploymentplan

Actuele status: Forgejo is later met eigenaarakkoord geactiveerd. Dit document bewaart het oorspronkelijke ontwerp; zie `forgejo-activation-verification.md` voor uitgevoerde controles en resterende beperkingen.

Datum: 9 oktober 2026. Scope alleen server2. **READY** lokale voorbereiding; **DISABLED** niet gerefereerde manifests, replicas=0 en gesuspendeerd Fluxvoorbeeld; **BLOCKED** TLS, secretbootstrap, runtimeproef en installatiegoedkeuring; **UNTESTED** werkelijke deployment/restore. Geen critical data. Dit oorspronkelijke ontwerp is later aangevuld met lokale TLS/SOPS-voorbereiding; zie de actuele status hieronder. Geen live installatie uitgevoerd.

## 1. Actuele platformbasis

VERIFIED via read-only SSH en Kubernetes-context server2: mau2/.162, v1.36.4+k3s1, node/Flux/coredeployments Ready op 3573639. CPU circa 8%, nodegeheugen circa 27%, host circa 6,3GiB available, root circa 210GiB beschikbaar. Momentopname, geen prestatiegarantie.

Traefik ServiceLB op 80/443, Ubuntu SSH22, API6443 en gateway UDP/TCP53 plus bestaande NodePorts. Geen namespace/PVC voor Forgejo; local-path default, Delete/WaitForFirstConsumer/geen expansion. Gateway kijkt naar Ingress binnen home.arpa; geen nieuwe DNScontroller nodig. Traefik websecure/TLS actief en Middleware-CRD aanwezig, maar geen vertrouwde Forgejocertificaatketen vastgesteld. Geen certificate/issuer/external-secrets/sealed-secrets CRD aangetroffen en geen SOPS-decryption in huidige drie Flux-Kustomizations. Geen Secretwaarden bekeken.

Laatste bevestigde k3s encryptiestatus Disabled komt uit eerdere audit; vandaag sudo-auth geblokkeerd. Zie `k3s-secrets-encryption-plan.md`: advies uitstel totdat externe recovery en testrollback bestaan. De backupvoorbereiding is gecommit, maar niet geïnstalleerd/actief.

## 2. Architectuurkeuze

| Optie | Voordeel | Afweging |
|---|---|---|
| Onderhouden Forgejo Helm-chart | Flux HelmRelease, veel configuratie/initfunctionaliteit | Project `forgejo-helm/forgejo-helm`; laatste release bij onderzoek v17.2.0, releasebron appVersion15.0.9. Extra chart/commondependencies en initdefaults moeten worden gereviewd; geen voordeel van DBsubcluster nodig. |
| Gewone Kubernetes-manifests | Kleine zichtbare resourceset, geen chartdefaults/dependencies; direct Kustomize/Flux | Init/config en upgrades zelf beheren/testen. **Gekozen voor één kleine SQLite-testinstance.** |

Primaire chartbron: [Forgejo Helm repository](https://code.forgejo.org/forgejo-helm/forgejo-helm), [release API](https://code.forgejo.org/api/v1/repos/forgejo-helm/forgejo-helm/releases?limit=3). Geen HelmRelease/OCIbron nodig voor gekozen manifests. Helm-templatevalidatie niet van toepassing; Helm niet aanwezig en niet geïnstalleerd.

| Onderdeel | Keuze |
|---|---|
| Namespace | forgejo, Pod Security restricted gepind op v1.36 |
| Workload | Deployment, later één replica, Recreate; nu nul. StatefulSet levert hier weinig extra. |
| Image | `codeberg.org/forgejo/forgejo:15.0.9-rootless@sha256:caf1bca332f95cdcf124227a4bfa3b49bbbfbbc8a5e4a97406921cb581165413` |
| Database | SQLite/WAL op dezelfde PVC; geen apart databaseaccount/server |
| Persistent disk | Eén 10GiB RWO local-path PVC; request is geen filesystemquota |
| Service | ClusterIP3000; geen hostPort/hostNetwork/NodePort/LoadBalancer |
| Web/Git | https://forgejo.home.arpa via Traefik websecure |
| SSH Git | DISABLED in eerste fase; geen poort22conflict of extra exposure |
| Health | startup/readiness `/api/healthz`, ruime startupwindow; TCP liveness voor proceslistener |
| Security | UID/GID/fsGroup1000, no privilege escalation, capdrop ALL, read-only rootfs, seccomp RuntimeDefault, geen serviceaccounttoken |
| Network | Alleen Traefikpods in kube-system naar TCP3000; egress alleen CoreDNS. LANallowlist via Traefik Middleware. |

De officiële rootlessbron bevestigt UID1000, datapad `/var/lib/gitea` en interne SSH2222; tag/indexdigest en amd64platform via public registrymetadata gecontroleerd. Geen imagelayers gedownload, container gestart, signature/vulnerabilityscan of runtimecertificering gedaan. [Forgejo rootless installatie](https://forgejo.org/docs/v15.0/admin/installation/docker/), [getagde Dockerfile](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.9/Dockerfile.rootless).

## 3. SQLite versus PostgreSQL

| Aspect | SQLite — gekozen | PostgreSQL |
|---|---|---|
| RAM/operatie | Geen DBdaemon; goed voor weinig gebruikers en één schrijverinstance | Eigen resources, account/secrets, lifecycle en volumes |
| Gelijktijdigheid | WAL verbetert leesconcurrency; writecontention blijft mogelijk | Geschikter bij meer gelijktijdige writers/groei |
| Herstel | Coherente SQLite export én bijbehorende repos/files | Native DBdump/restore én coherente repos/files |
| Uitval | Dezelfde SSD; geen HA | Eén Postgres op dezelfde node geeft evenmin hardware-HA |
| Besluit | Klein testgebruik, minder moving parts | Pas heroverwegen bij gemeten lock/performance- of schaalproblemen |

Geen PostgreSQLcluster/Redis/runner toevoegen. Filesystemrechten en SQLite-integriteit blijven echte operationele tests; containerrestart is geen datacorruptieherstel.

## 4. Resources, start en security

Apprequests100mCPU/256MiRAM; limits2CPU/1GiRAM; ephemeral100Mi request/1Gi limit, tmp emptyDir256Mi. Initrequests50m/64Mi, limits500m/128Mi. Init/app niet tegelijk; geplande footprint past in huidige momentopname, maar representative clones/pushes en memorypressure moeten worden gemeten. PVC10Gi is slechts beginbudget; local-path dwingt dit niet als harde quota af, geen expansion beloofd. Alarmen op root/PV-groei later noodzakelijk.

Initcontainer kopieert non-secret app.ini naar de PVC; stock rootlessentrypoint kan die runtimeconfig beheren. Elke start zet declaratieve instellingen opnieuw neer. Kritieke keys verwijzen naar verplichte `forgejo-runtime` bestanden; ConfigMap bevat geen waarden. Podstart vereist ook een bestaande `forgejo-tls` Secret via een mount van uitsluitend public cert. Een aanwezig certificaat is geen bewijs van trust/expiry; afzonderlijke TLSpreflight blijft verplicht.

Voor v15 rootless containerdefaults is reverseproxytrust extra aandachtspunt: config zet expliciete proxyCIDRs, geen wildcardtrust, en header-auth/auto-registration uit. NetworkPolicy beperkt appingress tot de geverifieerde Traefikselector. Registratie en installwizard uit, private repos standaard, customhooks/webhooks/Actions/OAuth/mail/LFS/metrics uit. Geen impliciete admincredentials. [Forgejo v15 containersecuritynote](https://forgejo.org/docs/v15.0/admin/installation/docker/#security-note-for-v15-lts-deployments), [configreferentie](https://forgejo.org/docs/v15.0/admin/config-cheat-sheet/).

## 5. TLS, DNS en exposure

Gebruik interne CA met leafcertificaat SAN forgejo.home.arpa, beheerlaptop/Gitclients vertrouwen de CA. Bestaande onafhankelijke CA heeft voorkeur; als die niet bestaat, apart goedgekeurde CA/leafcreatie en keyescrow. CAprivatekey nooit in appnamespace/Git; alleen leafkey in versleutelde Secret. Geen publieke ACMEverwachting voor home.arpa, geen nieuwe cert-manager tenzij renewalbehoefte dat rechtvaardigt.

Ingress uitsluitend websecure/TLS en secretName forgejo-tls. Geen Forgejo HTTProuter; geen insecure TLSbypass, browserexception of `git sslVerify=false`. Backend Traefik→pod is intern HTTP, begrensd met NetworkPolicy; geen end-to-end TLSclaim. Clients krijgen alleen HTTPS. [Traefik ingress/TLS](https://doc.traefik.io/traefik/reference/routing-configuration/kubernetes/ingress/).

Gateway vindt de nieuwe Ingress na geautoriseerde activering; naam → bestaande .162 ingressendpoint. Geen router/public DNSwijziging. Geen Forgejohost/NodePort of nieuwe listenpoort toegevoegd. Middleware LANallowlist is defensief, maar bron-NAT kan origineel clientadres verbergen; controleer vanaf beoogde LANclient en afgewezen bron, vertrouw niet uitsluitend op een allowlist voor WANisolatie. Router/WANexposure is niet onderzocht en wordt niet benaderd; eigenaar moet afwezigheid van ongewenste forwards bevestigen vóór bereikbare logininterface. DNSbootstrap/selfdependency blijft bestaand auditpunt.

SSHlater: rootless builtinserver2222 kan via dedicated niet-conflicterende LANpoort/TCProute worden ontsloten, met afzonderlijke exposure/firewall/hostkeychecks en goedkeuring. Die route is nu niet voorbereid of actief; Git via HTTPS voldoet aan eerste fase.

## 6. Secrets: duurzame keuze en bootstrap

| Optie | Oordeel |
|---|---|
| SOPS + age + Flux | **Voorkeur:** encrypted Gitmanifests, declaratieve refs en gecontroleerde wijzigingen; ageprivatekey/CAkeys onafhankelijk bewaren. |
| Kubernetes Secrets buiten Git | Eenvoudig tijdelijk, maar handmatige bootstrap/drift en herstel; alleen bij expliciete uitzonderingsbeslissing. |
| Sealed Secrets / External Secrets / Vault | Extra controller/backend/keybeheer zonder beschikbare externe dienst; nu geen meerwaarde. |

Update 9 oktober 2026: ageidentity en CA/leafmateriaal zijn lokaal aangemaakt na akkoord. De eigenaar heeft systeemtrust op de laptop geïnstalleerd; OpenSSL-verificatie geslaagd, browsertrust niet vastgesteld. Publieke `.sops.yaml` met werkelijke recipient en encrypted runtime/TLS-Secrets zijn lokaal voorbereid, niet gepubliceerd of live toegepast. Sleutels blijven uitsluitend op de laptop; eigenaar accepteert verliesrisico. Decryption in memory, chain/hostname/serverAuth en key/cert-match zijn gecontroleerd. Toekomstige minimale resources: namespaceforgejo; encrypted `forgejo-runtime` met secret_key/internal_token/oauth2_jwt_secret, encrypted TLS Secret forgejo-tls; ageprivatekey in flux-system/sops-age buiten Git; publieke recipients/rules in Git. TLSprivatekey wordt niet aan Forgejocontainer gemount. [Flux SOPS/age](https://fluxcd.io/flux/guides/mozilla-sops/).

Adminaccount: geen standaardnaam/wachtwoord of adminSecret in huidige manifests. Na apart geautoriseerde secret/bootstrapfase eigenaar initieel adminaccount creëren via ondersteunde CLI vanuit veilige eigen terminal, zonder output in agentsessie/logs. `--random-password` met voldoende lengte en must-change kan commandline-wachtwoord vermijden; owner bewaart de gegenereerde waarde direct en wijzigt via geverifieerd HTTPS. Geen accesstoken mee genereren. Dit is een toekomstige, afzonderlijk goedgekeurde handeling; CLI schrijft database en genereert credential. Voor volledige automatisering later reviewed ephemeralbootstrap met extern secretinput, no_log en geen shellhistory; niet nu. [Forgejo admin CLI](https://forgejo.org/docs/v15.0/admin/command-line/).

SOPS beschermt Git; k3s-encryptie staat laatstbekend uit. Live API/cluster-admin kunnen appsecrets lezen. Voor niet-kritische testdeployment eventuele resterende datastorebeschermingsrisico expliciet accepteren; geen productiegebruik vóór afgesproken security/recoverygates.

## 7. Staging en precieze toekomstige deployment

Actief apps-root behoudt bestaande lokale Dashyverwijdering en verwijst **niet** naar forgejo. De live Gitversie heeft Dashy nog. Stagingmap pushen zonder referencewijziging installeert geen Forgejo. Voorbeeld `bootstrap/gitops/forgejo.kustomization.example.yaml` staat buiten clusterroot, suspend=true en decryption=sops; het wordt nergens ontdekt/toegepast. Geen `kubectl apply`.

Toekomstige stappen, telkens binnen afzonderlijke toestemming:

1. Eigenaar keurt ontwerp/non-critical scope goed; review exacte stagingcommitbestanden, scan en push alleen na apart akkoord. Dashy/verouderde audits buiten die commit houden.
2. TLS/age/escrow/bootstrapplan goedkeuren; secrets buiten logs genereren, CAtrust installeren op juiste clients, publieke ageconfig en encrypted Secrets gereviewd voorbereiden. Geen schema/placeholderSecret live toepassen.
3. Maak een afzonderlijke Flux-bootstrapchange voor namespace en encrypted Secretdecryption, zonder appwriters. Age-bootstrapkey in flux-system vraagt eigen gecontroleerde bootstrapactie; geen algemene GitOpsomzeiling.
4. Test rootless/app.ini/URI/fsGroup/probes/security en healthroute op geïsoleerde omgeving met eigen context; verwacht correcte init en verifieer tag/digest opnieuw vóór deployment. Geen productiereadiness claim zonder deze proef.
5. Verifieer TLS SAN/trust/expiry, runtimeSecretkeyset, repositorysource, local-path/ruimte, Traefikselectors/policy en LANexposure. Missing TLS/credentials blijft BLOCKED.
6. Bereid aparte Flux-Kustomization voor forgejo, path naar staging, decryption=sops, dependsOn infrastructure én forgejo-secrets, wait en prune. Namespace/PVC prune-uitzonderingen behouden. Activeer alleen via goedgekeurde clusterroot/Gitcommit; apps-root/Dashy niet meenemen. Rekening houden met Secret/namespace bootstrapvolgorde.
7. Na deploymentakkoord replicas naar één en suspend naar false via Git. Flux maakt geselecteerde resources/PVC aan; writers starten pas nadat dependencies aanwezig zijn. Geen `kubectl scale` of handmatige appapply.
8. Controleer pod/health/TLS/DNS, adminbootstrap via eigenaar, testlogin/private repo clone/push over geverifieerd HTTPS, rootruimte en denied-netwerkpaden. Geen internetmigration/webhooks/SSHroutes openen.
9. Stop bij onverwachte pruning, FailedMount, Secret/TLSfout of initloop. Via vooraf gereviewde Gitrollback writers stoppen (replicas0/suspend), PVC behouden. Geen automatische databaseversiedowngrade.

Deze stappen zijn procedure, geen uitgevoerde changes. Nieuwe encryptieconfig wordt niet noodzakelijk tegelijk uitgerold; encryptie blijft eigen risicovolle change met externe herstelgate.

## 8. Upgrades, backups en restore

Exacte image/digest via gereviewde Gitcommit wijzigen, geen imageautomation/latest. Recreate voorkomt twee writers op dezelfde SQLite/PVC; downtime hoort bij upgrade. Majorupgrade alleen ondersteunde versievolgorde, releasenotes, compatibiliteitstest en consistent herstelpunt. Zonder externe backup uitsluitend wegwerpdata; upgrade kan onomkeerbare schemas wijzigen. Terugzetten van oude image alleen is geen databaserollback.

Lokale SSD bevat SQLite incl.WAL, Gitrepos, issues/users/accessconfig, attachments/avatars/packages indien gebruikt, app.ini en eventuele runtimepersistentkeys. Secretobjects bevatten interne/TLSkeys. Bij SSDdefect of hostverlies kan alles verloren gaan; GitHub herbouwt manifests, geen gebruikers/repositoriesdata. GitHub blijft platformsource, Forgejo wordt geen bootstrapdependency.

Later coherent backupcontract: blokkeer alle appwriters/jobs met Fluxafstemming → native SQLite Online Backup API/dump op stabiel consistentiemoment plus repositories/files/config/keyset → Restic extern met receipt → gegarandeerde resume ook bij fout. Geen live raw dbkopie; geen aparte ongerelateerde DB/files-momenten. Forgejodump SQLrestore niet blind vertrouwen. [Forgejo backup/upgrade](https://forgejo.org/docs/v15.0/admin/upgrade/).

Restoreproef: geïsoleerde instance met gepinde versie; PVC remappen naar nieuwe UID/pad; matching DB/files/secrets restore, integriteitscheck en git fsck/known commit, attachment/userrechten/login testen. Webhooks/mail/jobs uit, geen productienetwerkroute. Meet RPO/RTO; encryptiekeyherstel en volledige nieuwe backup aantonen. Backupvoorbereiding weigert nu appcontracts omdat exporters nog ontbreken.

## 9. Validatie en open gates

Statische controles: YAML en Kustomize, resource/selectormatching, probe/port/secretrefs, vaste digest, securityvelden, namespacepolicy, geen plaintext Secretdata en geen activering via actief buildpad. APIadmission/runtime/policyhandhaving, netwerkclient-IPgedrag, certificate trust, poddiskrechten, healthendpointbehavior en restore blijven UNTESTED. Geen server-side dry-run/apply, Helmdeployment of imagestart.

Eerste benodigde akkoord: ontwerp en eventueel apart commit/push van **uitsluitend niet-actieve voorbereiding**. TLS/age/admincredentialbootstrap, Fluxactivering, encryptie en applicatiestart hebben afzonderlijke toestemming nodig. Securityafhankelijkheden en runtimeproef moeten vóór start zijn opgelost; backups blijven DISABLED/BLOCKED.

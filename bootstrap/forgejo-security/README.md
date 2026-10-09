# Forgejo TLS/SOPS bootstrap — preparation only

9 oktober 2026. Lokaal gereed: age v1.3.2, SOPS v3.13.3, ageidentity, encrypted CA-private key, publieke CA en Forgejo-leafcertificaat. Officiële assetdigests en SOPS-checksumlijst gecontroleerd; signatures/proofs niet geverifieerd. Certificaatketen, hostname, serverAuth en key/cert-match gecontroleerd. Runtime- en TLS-Secrets staan als SOPS-ciphertext in de repository; decrypt-roundtrip in memory geslaagd zonder plaintextoutput. De eigenaar heeft de publieke CA in de systeemtrust van de laptop geïnstalleerd; OpenSSL-validatie geslaagd. Browsertrust niet vastgesteld. De lokale voorbereiding is daarna gepubliceerd en op server2 geactiveerd met afzonderlijk eigenaarakkoord. Zie docs/server/forgejo-activation-verification.md voor de actuele status. Volledige TLS/deployment/herstelketen niet getest.

## Eigenaarbesluiten

Nieuwe interne CA voorbereiden. CAprivatekey en ageherstelsleutel voorlopig uitsluitend op beheer-laptop; eigenaar accepteert verliesrisico. Dit vervangt geen onafhankelijke recoverykopie. Bij laptopverlies kan de CA opnieuw nodig zijn en kunnen encrypted Gitsecrets niet meer ontsleuteld worden. Verloren Forgejo secret_key kan reeds encrypted appgegevens zoals 2FA onherstelbaar maken. Geen sleutelescrow als gerealiseerd rapporteren.

## Concrete lokale bootstrap na akkoord

1. Installeer gecontroleerde gepinde age/SOPS-binaries alleen op de laptop: voorstel age v1.3.2 en SOPS v3.13.3, officiële releases geraadpleegd op 9 oktober 2026. Verifieer officiële releasechecksums/signatures waar beschikbaar vóór uitvoering. OpenSSL is al aanwezig. Geen software op server2 nodig voor Fluxdecryption.
2. Private materiaal in `/home/mau/.local/share/server2-security/` (directory0700, bestanden0600), buiten repository en Git. Eerst symlink-/bestaande-bestandguards; niets overschrijven. Root CA EC P-256, encrypted privatekey met eigenaarpassphrase, rootvaliditeit10jaar; leaf EC P-256 voor forgejo.home.arpa, 90dagen. Root key tekenen via veilige eigenaarterminal; wachtwoord nooit in chat/argumenten/logs. Geen rootkey in Kubernetes.
3. Eén ageidentity voor dit platform; public recipient in definitieve SOPSrules, privateidentity uitsluitend lokale beveiligde directory en later flux-system/sops-age. Geen fake recipients publiceren. Herstelrisico van alleen-laptopopslag blijft expliciet.
4. Forgejo-runtime keys volgens ondersteunde Forgejoformaten, TLSleaf/privatekey en ageidentity alleen na afzonderlijk key/credentialakkoord genereren. Direct veilige verwerking zonder stdout/plaintext tijdelijk diskbestand: gecontroleerde pipeline of bewezen noswaptmpfs naar SOPS. Geen actieve onversleutelde Secretmanifests in Git of outputs.
5. Public CAcert en fingerprint mogen apart beschikbaar; trustinstallatie in laptop/browser/Git is een afzonderlijke lokale systeemwijziging. Geen trust toevoegen voordat subject/SAN/issuer/expiry en fingerprint gecontroleerd zijn. Geen TLSexceptions of sslVerify=false.
6. Statistische en cryptografische checks: chain/hostname/eku, privatekey-certmatch zonder keyoutput, SOPSroundtrip zonder plaintextoutput, scans en correcte permissions. Daarna pas encrypted Gitbestanden ter commitreview tonen.

Gemaakte CA/leafbestanden: `ca.key.pem`, `ca.crt.pem`, `forgejo.key.pem`, `forgejo.crt.pem`. CApubliccert bevat geen privatekey. CApassphrase door eigenaar rechtstreeks in eigen terminal invoeren; de agent vraagt deze nooit in chat. Leafprivatekey moet voor unattended Traefik kunnen worden gebruikt, daarom beschermd via SOPS en Kubernetesrechten.

Actuele bestanden buiten Git onder `/home/mau/.local/share/server2-security/`: ageidentity en publieke recipient, encrypted runtime/TLS-manifests, CA-private key, publiek CA-certificaat, leaf-private key, CSR, leafcertificaat en CA-serienummer. Private directory0700 en bestanden0600. De repository bevat uitsluitend publieke profielen/rules en encrypted Secrets. Het CA-script weigert bestaande doelbestanden/symlinks; niet opnieuw uitvoeren over bestaande materiaal. Bij gedeeltelijk falen niets automatisch opruimen of overschrijven.

## Clusterbootstrap later: afzonderlijk live akkoord

- `sops-age` is de enige onvermijdelijke decryption-trustbootstrap buiten encrypted Git: zorgvuldig alleen expliciete context server2 en namespaceflux-system. Geen kubectlapply van appresources.
- Nieuwe aparte Flux-Kustomization voor `kubernetes/secrets/forgejo`, met SOPSdecryption, eerst alleen namespace+encrypted secrets. Die map en een gesuspendeerd Fluxvoorbeeld zijn lokaal voorbereid; geen actief clusterpad verwijst ernaar. Deze secrets-bootstrap beheert de namespace. Het appvoorbeeld hangt af van forgejo-secrets en infrastructure. Geen app-Deployment/PVC/Ingress in deze bootstrapfase.
- Forgejo-runtime en forgejo-tls gereconcileerd en decryption bevestigd zonder Secretwaarden op te vragen. Certvalidatie door publieke TLSdata, metadata/podstatus voor permissions en Secretconsumer.
- Bestaande niet-gerefereerde Forgejo-Kustomization blijft suspend=true en Deploymentreplicas0. Geen Dashywijziging meepushen.
- CAtrust/HTTPS/netwerk/runtimeproef en eigenaarakkoord vereist voordat Forgejo gestart wordt. Tot die tijd geen logininterface activeren, geen DNS/firewall/routerchange.

RootCA 10jaar versus leaf90dagen vereist tijdige renewal. Zonder nieuwe service nu handmatig goedgekeurde leafrenewal met vooraf waarschuwing, later declaratieve certificaatautomatisering beoordelen. Geen actieve timer/cert-manager/cron gemaakt. De CA blijft gescheiden van k3s-CA; k3s secrets-encryptie blijft uitgesteld en backups inactief.

## Scope en goedkeuringsmomenten

Eerst lokale tooling en key/certcreatie, vervolgens aparte trustinstallatie en clusterbootstrap, dan eigen commit/push en Forgejoactivatie. Een akkoord voor lokale generatie autoriseert geen live Kuberneteswijzigingen, appstart of Gitpush. Deze voorbeelden voegen niets toe aan actieve Kustomizepaden.

Primaire bronnen: [SOPS v3.13.3](https://github.com/getsops/sops/releases/tag/v3.13.3), [age v1.3.2](https://github.com/FiloSottile/age/releases/tag/v1.3.2), [Flux SOPS/age bootstrap](https://fluxcd.io/flux/guides/mozilla-sops/).

## Eerste beheerder

Voer `bash /home/mau/server2-platform/bootstrap/forgejo-security/create-admin.sh` alleen in je eigen terminal uit. Het script vraagt username/email en laat Forgejo een tijdelijk wachtwoord genereren, zonder wachtwoord in CLI-argumenten. Bewaar dit in je wachtwoordmanager, deel de uitvoer niet in chat en wijzig het bij eerste login. Geen beheerder aangemaakt door de agent; login/clone/push nog niet getest.

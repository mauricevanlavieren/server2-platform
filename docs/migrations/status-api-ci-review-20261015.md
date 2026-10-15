# Status API CI — uitgeschakeld reviewvoorstel

Fase 6, 2026-10-15. Alleen de Status API-workflow uit de acht lokaal beoordeelde fase-5-bestanden is overgenomen. Postkamer-workflows en publicatiebeleid blijven uitsluitend lokaal en buiten deze PR.

Deze workflow valideert uitsluitend applications/platform-status-api: npm ci met lockfile en zonder lifecycle-scripts, npm test en npm audit op niveau high. Elke runstap gebruikt die werkdirectory. Checkout/setup zijn ondersteunend; geen Kubernetes/Flux/Backup v2-/applicatiebronwijziging, deployment of imagepublicatie.

Veiligheidsgrenzen: uitsluitend workflow_dispatch, job onvoorwaardelijk if: false, contents:read en checkout zonder bewaarde credentials; actions op volledige SHA. Geen push-/PR-/scheduletrigger. Deze PR activeert geen CI; later inschakelen vereist eigen akkoord en review.

Lokale controles: de oorspronkelijke acht drafts slagen voor 77 checks en 14 policytests; dit voorstel krijgt aparte YAML-, shellsyntax-, pad-, rechten-, SHA- en diffcontroles. Actionlint is niet geïnstalleerd; geen GitHub-workflow uitgevoerd. Applicatietests worden afzonderlijk gerapporteerd, niet geïmpliceerd door YAML-validatie.

Na beoordeling: afzonderlijk akkoord voor merge, vervolgens expliciet akkoord voor activatie en validatierun. Oude platform-status-api-CI en repository blijven bestaan. Geen omschakeling van Postkamer/GHCR. Backup v2 blijft a0452266f8a58c7b9d8659fe8bab5c5ae6249c7d.

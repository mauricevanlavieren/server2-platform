# Status API CI — activatievoorstel fase 7

2026-10-15. PR #2 bevat uitsluitend deze documentatie en de Status API-workflow. Fase 7 autoriseert activering, echte CI-validatie en merge na geslaagde controles. Oude Status API-repository en CI blijven behouden.

Eigenaar van de nieuwe CI is server2-platform. Automatische pull_request naar main en push naar main, met padfilters applications/platform-status-api/** en het eigen workflowbestand. De extra workflowpadfilter zorgt dat aanpassingen aan de CI zelf getest worden. Handmatige workflow_dispatch blijft beschikbaar. Geen pull_request_target, schedule of andere brede trigger.

Alle runstappen werken uitsluitend in applications/platform-status-api: lockfile-installatie zonder lifecycle-scripts, npm test en npm audit --audit-level=high. contents:read; checkout zonder bewaarde credentials; actions op volledige SHA; Node 24, Ubuntu 24.04 runner. Geen secrets nodig, package-write, imagebuild/publicatie, deployment of servercommando's. Standaard PR-checkout test de GitHub merge-ref.

Geen wijzigingen aan Kubernetes/Flux, Backup v2, Postkamer of applicatiedeployments. Broncode en lockfile blijven ongewijzigd. Lokale en echte GitHub-resultaten worden apart vastgelegd; een succesvolle YAML-controle alleen is geen bewijs van uitgevoerde CI.

Na deze merge wordt een afzonderlijke niet-functionele README-wijziging binnen het applicatiepad gebruikt voor een echte PR-triggercontrole. Een aparte documentatiewijziging buiten applicatie-/workflowpaden test negatieve filtering. Test-PR's worden niet automatisch gemerged. Afbouw van de oude repository blijft een afzonderlijk expliciet besluit.

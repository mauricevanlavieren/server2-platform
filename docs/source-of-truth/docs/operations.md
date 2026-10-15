# Beheer

Statusdatum: 2026-10-15. Fase 2 publiceert alleen de GitHub-basis en documentatie. Geen serverwijziging, deployment, applicatiemigratie of back-upactivatie. Gewenste vervolgstappen zijn geen uitgevoerde configuratie.

Controleer vóór elke handeling toestemming, repository, branch, SHA en lokale wijzigingen. Doe alleen benodigde niet-geheime controles. Wijzig uitsluitend de beheerde bron van de eigenaar.

Server1- en server2-documentatie staat in een afzonderlijke docs/source-of-truth-20261015-branch; geen pull request of merge in deze fase. Bestaande root-README/AGENTS, manifests en workflows blijven intact. Een push naar main kan CI of Flux starten; reviewbranches niet zonder analyse samenvoegen. Nieuwe repositories bevatten geen workflows.

Na elke toegestane wijziging naam, visibility, branches en verwachte configuratie controleren. Bij conflict of onverwachte afhankelijkheid stoppen. Geen automatische privacyrollback naar public, geen verwijderingen of force-push.
